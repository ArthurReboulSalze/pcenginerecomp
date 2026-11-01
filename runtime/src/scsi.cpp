#include "pce/runtime.hpp"
#include "pce/sector.hpp"
#include <limits>
#include <sstream>
#include <iomanip>
#include <algorithm>

namespace pce {
namespace {
constexpr unsigned bsy=0x80, req=0x40, msg=0x20, cd=0x10, io=8, ack_bit=2, rst=0x100;
constexpr unsigned free_phase=0, command_phase=3, data_phase=4, message_phase=6, status_phase=7;
unsigned command_length(unsigned op) {
    switch(op) {
    case 0: case 3: case 8: return 6;
    case 0xD8: case 0xD9: case 0xDA: case 0xDD: case 0xDE: return 10;
    default: return 0;
    }
}
unsigned invalid_command_length(unsigned op) {
    // NEC reference framing uses the operation-code group before dispatch.
    // The bounded table is protocol data; no command operation is invented.
    constexpr std::array<unsigned,16> lengths={6,6,10,10,10,10,10,10,10,10,12,12,10,10,10,10};
    return lengths[op>>4];
}
void validate_unknown_policy(CdUnknownPolicy policy) {
    if(policy!=CdUnknownPolicy::fault && policy!=CdUnknownPolicy::gear_good && policy!=CdUnknownPolicy::nec_invalid)
        throw Fault("invalid CD unknown-command policy");
}
unsigned bcd(unsigned value) { return value/10*16+value%10; }
}
void CdToc::validate() const {
    const auto& value=*this;
    if(!value.track_count || value.track_count>99 || value.leadout_lba>449849)
        throw Fault("TOC count/leadout exceeds the supported CD/BCD range");
    for(unsigned i=0;i<value.track_count;++i) {
        const auto& track=value.tracks[i];
        if((track.type!=0 && track.type!=4) || track.index1_lba>=value.leadout_lba ||
           (i && track.index1_lba<=value.tracks[i-1].index1_lba))
            throw Fault("invalid TOC track type, order or INDEX 01 LBA");
    }
    if(!value.image_sha256.empty() && (value.image_sha256.size()!=64 ||
       value.image_sha256.find_first_not_of("0123456789abcdef")!=std::string::npos))
        throw Fault("invalid TOC source SHA256");
}
void Bus::enable_cd_transport() { enable_cd_control(); cd.scsi.enabled=true; }
void CdControl::set_toc(const CdToc& value) {
    value.validate();
    if(provider) throw Fault("TOC replacement requires a new unattached CD transport");
    if(!scsi.enabled || scsi.phase!=free_phase || scsi.event || scsi.auto_ack_deadline || ack)
        throw Fault("TOC attachment requires an idle enabled CD transport");
    toc=value;
}
void CdControl::set_sector_provider(std::shared_ptr<SectorProvider> value) {
    if(!value) throw Fault("null CD sector provider");
    const auto& geometry=value->toc(); geometry.validate();
    if(toc) {
        if(toc->track_count!=geometry.track_count || toc->leadout_lba!=geometry.leadout_lba ||
           toc->image_sha256!=geometry.image_sha256) throw Fault("CD provider/TOC identity mismatch");
        for(unsigned i=0;i<geometry.track_count;++i)
            if(toc->tracks[i].index1_lba!=geometry.tracks[i].index1_lba || toc->tracks[i].type!=geometry.tracks[i].type)
                throw Fault("CD provider/TOC geometry mismatch");
    }
    set_toc(geometry); provider=std::move(value);
}
void CdControl::schedule_load(std::uint64_t delay) {
    if(delay>std::numeric_limits<std::uint64_t>::max()-scsi.master_ticks)
        throw Fault("CD sector clock overflow");
    scsi.load_deadline=scsi.master_ticks+delay;
}
void CdControl::read_sectors() {
    if(!provider) throw Fault("CD READ $08 requires a read-only sector provider");
    const auto lba=(std::uint32_t(scsi.command[1]&31)<<16)|(unsigned(scsi.command[2])<<8)|scsi.command[3];
    if(lba>=provider->toc().leadout_lba) { ++read_commands; ++read_errors; check_condition(5,0x25,0,lba); return; }
    const auto& geometry=provider->toc();
    unsigned track=0;
    while(track<geometry.track_count && geometry.tracks[track].index1_lba<=lba)++track;
    if(!track) {++read_commands;++read_errors;check_condition(5,0x25,0,lba);return;}
    if(geometry.tracks[track-1].type!=4) {++read_commands;++read_errors;check_condition(3,0x1D,0,lba);return;}
    // Sample the retained head before READ cancels audio. Refuse unsupported
    // geometry or clock overflow before modifying that active timeline.
    const auto delay=cd_seek_ticks(timing_profile,scsi.current_lba,lba)+286363;
    if(delay>std::numeric_limits<std::uint64_t>::max()-scsi.master_ticks)
        throw Fault("CD sector clock overflow");
    ++read_commands;
    scsi.load_lba=lba; scsi.load_remaining=scsi.command[4] ? scsi.command[4]:256;
    audio.stop(true);scsi.read_active=true; scsi.response_size=0; scsi.response_index=0;
    // One sector at 1x follows the separately selected seek model.
    schedule_load(delay); phase(data_phase);
}
void CdControl::load_sector() {
    if(scsi.response_index<scsi.response_size) {
        ++read_retries; schedule_load(6228408); return; // 290 ms at 1x.
    }
    try {
        if(!provider) throw Fault("CD READ lost its read-only sector provider");
        if(scsi.load_lba>=provider->toc().leadout_lba)
            throw SectorReadError(SectorReadReason::out_of_range,scsi.load_lba,"CD sector past leadout");
        // Read into a temporary: a failed provider cannot expose a partial sector.
        const auto sector=provider->read(scsi.load_lba);
        scsi.response=sector;
    } catch(const SectorReadError& error) {
        if(error.lba!=scsi.load_lba) throw Fault("CD provider error does not identify the requested LBA");
        std::uint8_t key=0,asc=0,ascq=0;
        switch(error.reason) {
        case SectorReadReason::out_of_range:key=5;asc=0x25;break;
        case SectorReadReason::wrong_data_track:key=3;asc=0x1D;break;
        case SectorReadReason::unrecoverable_data:key=5;break;
        case SectorReadReason::media_data_error:key=3;asc=0x11;ascq=5;break;
        }
        if(!key) throw Fault("CD provider returned an unknown sector error category");
        ++read_errors; scsi.load_remaining=0; scsi.read_active=false;
        scsi.response_size=0; scsi.response_index=0;scsi.load_deadline=0;
        check_condition(key,asc,ascq,error.lba); handshake(); return;
    }
    // The retained drive head points past a successful load, clamped to the
    // final disc sector in the Gear profile. Pending/unacknowledged data and
    // the next queued load retain their separate addresses. Failed loads and
    // occupied-buffer retries return above without moving this head.
    scsi.current_lba=std::min(scsi.load_lba+1,provider->toc().leadout_lba-1);
    scsi.load_lba=(scsi.load_lba+1)&0x1FFFFF;
    --scsi.load_remaining; ++sectors_read;
    scsi.response_size=2048; scsi.response_index=0;
    if(scsi.load_remaining) schedule_load(286363); // floor(master_clock / 75).
    handshake();
}
void CdControl::start_status(std::uint8_t value,unsigned length) {
    if(!length || length>scsi.response.size()) throw Fault("CD status buffer overflow");
    scsi.response.fill(value); scsi.response_size=length; scsi.response_index=0;
    scsi.data=value; scsi.status_pending=true; scsi.read_active=false; phase(status_phase);
}
void CdControl::check_condition(std::uint8_t key,std::uint8_t asc,std::uint8_t ascq,
                                std::optional<std::uint32_t> failed_lba) {
    if(sense_errors==std::numeric_limits<std::uint64_t>::max()) throw Fault("CD sense error counter overflow");
    pending_sense={key,asc,ascq,0,failed_lba};++sense_errors;
    start_status(2); // Preserve the existing Gear-compatible status/message bus profile.
}
void CdControl::request_sense() {
    if(sense_commands==std::numeric_limits<std::uint64_t>::max()) throw Fault("CD sense command counter overflow");
    ++sense_commands;
    // NEC's fixed response ignores allocation length and never marks the
    // information field valid. Keep host failure addresses out of these bytes.
    scsi.response.fill(0);scsi.response_size=18;scsi.response_index=0;
    scsi.response[0]=0x70;scsi.response[2]=pending_sense.key;scsi.response[7]=0x0A;
    scsi.response[12]=pending_sense.asc;scsi.response[13]=pending_sense.ascq;scsi.response[14]=pending_sense.fru;
    pending_sense=CdSense{};
    phase(data_phase);
    // Settle the first DATA IN byte in the existing aggregate handshake.
    // This supplies no electrical bus-phase or drive-latency guarantee.
    handshake();
}
void CdControl::read_directory() {
    if(!toc) { check_condition(2,0x0B); return; } // No fabricated metadata medium.
    const auto mode=scsi.command[1];
    unsigned lba=toc->leadout_lba;
    unsigned type=0;
    scsi.response.fill(0); scsi.response_size=4; scsi.response_index=0;
    if(mode==0) {
        scsi.response[0]=1; scsi.response[1]=static_cast<std::uint8_t>(bcd(toc->track_count));
    } else if(mode==1 || mode==2) {
        if(mode==2) {
            const auto encoded=scsi.command[2];
            if(encoded!=0xAA && ((encoded&15)>9 || (encoded>>4)>9)) throw Fault("invalid BCD CD directory track");
            // $AA is the explicit leadout selector, also recognized by Beetle.
            unsigned track=encoded==0xAA ? 100:(encoded>>4)*10+(encoded&15);
            if(!track) track=1;
            if(track<=toc->track_count) {
                lba=toc->tracks[track-1].index1_lba; type=toc->tracks[track-1].type;
            }
        }
        const auto absolute=lba+150;
        scsi.response[0]=static_cast<std::uint8_t>(bcd(absolute/4500));
        scsi.response[1]=static_cast<std::uint8_t>(bcd(absolute/75%60));
        scsi.response[2]=static_cast<std::uint8_t>(bcd(absolute%75));
        scsi.response[3]=static_cast<std::uint8_t>(type);
    } else throw Fault("unsupported CD directory mode");
    schedule(6,9000);
    ++toc_replies;
}
void CdControl::update_irq() {
    // The reference sets the selected source without clearing its peer while
    // REQ remains asserted. DATA IN reselection can therefore expose $60 until
    // ACK drops REQ; preserve this observable reference-profile behavior.
    if((scsi.signals&(bsy|io|req))==(bsy|io|req))
        interrupt_active |= (scsi.signals&cd) ? 0x20:0x40;
    else interrupt_active &= static_cast<std::uint8_t>(~0x60);
}
void CdControl::schedule(unsigned event,std::uint64_t delay) {
    if(delay>std::numeric_limits<std::uint64_t>::max()-scsi.master_ticks)
        throw Fault("CD transport clock overflow");
    scsi.event=event; scsi.deadline=scsi.master_ticks+delay;
}
void CdControl::phase(unsigned value) {
    if(scsi.phase==value) return; // Reselection does not discard a partial CDB.
    scsi.phase=value;
    scsi.signals &= static_cast<std::uint16_t>(~(bsy|req|msg|cd|io));
    switch(value) {
    case command_phase:
        pending_origin=CommandOrigin{};
        scsi.response_size=0; scsi.response_index=0; scsi.status_pending=false;
        scsi.load_deadline=0; scsi.load_remaining=0; scsi.read_active=false;
        scsi.signals|=bsy|cd|req; break;
    case data_phase: scsi.signals|=bsy|io; break;
    case status_phase: scsi.signals|=bsy|cd|io|req; break;
    case 8: scsi.signals|=bsy; break;
    case message_phase: scsi.signals|=bsy|cd|io|msg|req; break;
    default: break;
    }
}
void CdControl::handshake() {
    if(reset&2) {
        const auto ticks=scsi.master_ticks;
        audio.stop();scsi=Scsi{}; scsi.enabled=true; scsi.master_ticks=ticks; scsi.signals=rst;
        pending_origin=CommandOrigin{};
        ack=false; update_irq(); return;
    }
    const bool request=(scsi.signals&req)!=0;
    if(scsi.phase==command_phase) {
        if(request && ack) {
            if(scsi.command_size==scsi.command.size()) throw Fault("CD command buffer overflow");
            scsi.command[scsi.command_size++]=scsi.latch;
            scsi.signals &= static_cast<std::uint16_t>(~req);
        } else if(!request && !ack && scsi.command_size) {
            const auto known_length=command_length(scsi.command[0]);
            const auto length=known_length ? known_length:
                unknown_policy==CdUnknownPolicy::nec_invalid ? invalid_command_length(scsi.command[0]):0;
            if(!length || scsi.command_size>=length) {
                scsi.last_command=scsi.command; scsi.last_command_size=scsi.command_size;
                if(!known_length) {
                    auto& attempts=unknown_opcodes[scsi.command[0]];
                    if(attempts==std::numeric_limits<std::uint64_t>::max())
                        throw Fault("CD unknown-command diagnostic counter overflow");
                    if(unknown_policy==CdUnknownPolicy::gear_good && unknown_commands==std::numeric_limits<std::uint64_t>::max())
                        throw Fault("CD unknown-command response counter overflow");
                    if(unknown_policy==CdUnknownPolicy::nec_invalid &&
                       (invalid_commands==std::numeric_limits<std::uint64_t>::max() || sense_errors==std::numeric_limits<std::uint64_t>::max()))
                        throw Fault("CD invalid-command response counter overflow");
                    ++attempts;last_unknown_command=scsi.command;
                    last_unknown_size=scsi.command_size;last_unknown_origin=pending_origin;
                }
                pending_origin=CommandOrigin{};
                if(!known_length && unknown_policy==CdUnknownPolicy::gear_good) {
                    // A selected emulator-reference protocol quirk, not an
                    // implementation of an unknown command's operation. Known
                    // commands with unsupported semantics retain their fault.
                    ++unknown_commands;start_status(0);scsi.command_size=0;
                    update_irq();return;
                }
                if(!known_length && unknown_policy==CdUnknownPolicy::nec_invalid) {
                    ++invalid_commands;check_condition(5,0x20);scsi.command_size=0;
                    update_irq();return;
                }
                if(scsi.command[0]!=0 && scsi.command[0]!=3 && scsi.command[0]!=0xDE && scsi.command[0]!=8 &&
                   !(audio_enabled && (scsi.command[0]==0xD8 || scsi.command[0]==0xD9 || scsi.command[0]==0xDA || scsi.command[0]==0xDD))) {
                    std::ostringstream message;
                    message<<"unsupported CD command $"<<std::hex<<std::uppercase<<std::setw(2)
                           <<std::setfill('0')<<unsigned(scsi.command[0])<<" (captured "
                           <<std::dec<<scsi.command_size<<" bytes; unsupported command semantics)";
                    throw Fault(message.str());
                }
                if(scsi.command[0]==3) request_sense();
                else if(scsi.command[0]==0xDE) read_directory();
                else if(scsi.command[0]==8) read_sectors();
                else if(scsi.command[0]>=0xD8 && scsi.command[0]<=0xDD) audio_command();
                else schedule(3,450000); // Reference-emulator TUR latency, not drive-ready evidence.
                scsi.command_size=0;
            } else schedule(2,3000);
        }
    } else if(scsi.phase==data_phase) {
        if(request && ack) { scsi.signals &= static_cast<std::uint16_t>(~req); ++data_bytes_acked; }
        else if(!request && !ack) {
            if(scsi.response_index<scsi.response_size) {
                scsi.data=scsi.response[scsi.response_index++];
                if(scsi.response_size==2048 || scsi.response_index==1) scsi.signals|=req;
                else schedule(7,900);
            } else if(!scsi.load_remaining) schedule(3,3000);
        }
    } else if(scsi.phase==status_phase || scsi.phase==message_phase) {
        if(request && ack) scsi.signals &= static_cast<std::uint16_t>(~req);
        else if(!request && !ack) {
            if(scsi.phase==message_phase) schedule(5,1500);
            else if(scsi.status_pending) {
                scsi.data=scsi.response[scsi.response_index++];
                if(scsi.response_index==scsi.response_size) {
                    scsi.status_pending=false; schedule(4,1500);
                } else schedule(7,1500);
            }
        }
    }
    update_irq();
}
void CdControl::advance_to(std::uint64_t ticks) {
    validate_unknown_policy(unknown_policy);
    if(!scsi.enabled) return;
    if(ticks<scsi.master_ticks) throw Fault("CPU/CD clock regression");
    // Process events at their guest timestamp, including a held ACK at REQ.
    // No host timers and no per-tick polling or unbounded response buffers.
    unsigned event_budget=0;
    for(;;) {
        auto next=ticks;
        bool pending=false;
        for(const auto when:{scsi.event?scsi.deadline:0,scsi.load_deadline,scsi.auto_ack_deadline,audio_enabled?audio.deadline:0})
            if(when && when<=ticks && (!pending || when<next)) {next=when;pending=true;}
        if(!pending) break;
        if(++event_budget>1000000) throw Fault("CD event budget exceeded for one clock advance");
        scsi.master_ticks=next;
        const auto old_signals=scsi.signals;
        if(scsi.event && scsi.deadline==next) {
            const auto event=scsi.event;scsi.event=0;scsi.deadline=0;
            switch(event) {
            case 1:phase(command_phase);break;
            case 2:case 7:scsi.signals|=req;break;
            case 3:start_status(0);break;
            case 4:phase(message_phase);break;
            case 5:phase(free_phase);break;
            case 6:phase(data_phase);break;
            default:throw Fault("invalid CD transport event");
            }
            if(old_signals!=scsi.signals) handshake();
        } else if(scsi.load_deadline==next) {
            scsi.load_deadline=0;load_sector();
        } else if(scsi.auto_ack_deadline==next) {
            scsi.auto_ack_deadline=0;
            if(ack) {ack=false;scsi.signals&=static_cast<std::uint16_t>(~ack_bit);handshake();}
        } else {
            audio_event();if(old_signals!=scsi.signals)handshake();
        }
    }
    scsi.master_ticks=ticks;
}
std::uint8_t CdControl::transport_read(unsigned port) {
    validate_unknown_policy(unknown_policy);
    if(port==0) return static_cast<std::uint8_t>(scsi.signals&0xF8);
    const auto value=scsi.phase==data_phase || scsi.phase==status_phase || scsi.phase==message_phase ? scsi.data:scsi.latch;
    // Sample the old byte before raising ACK; only a requested DATA IN byte
    // arms the 1us reference pulse. STATUS/MESSAGE must not be consumed here.
    if(port==8 && (scsi.signals&(req|io|cd))==(req|io)) {
        if(scsi.master_ticks>std::numeric_limits<std::uint64_t>::max()-21)
            throw Fault("CD automatic ACK clock overflow");
        scsi.auto_ack_deadline=scsi.master_ticks+21;
        if(!ack) { ack=true; scsi.signals|=ack_bit; handshake(); }
    }
    return value;
}
void CdControl::transport_write(unsigned port,std::uint8_t value) {
    validate_unknown_policy(unknown_policy);
    switch(port) {
    case 0:
        if(scsi.phase==data_phase) { start_status(0,8); schedule(1,900000); handshake(); }
        else schedule(1,75000);
        return;
    case 1: scsi.latch=value; return;
    case 2: {
        interrupt_enable=value&0x7F;
        // A new ACK assertion while RST is held clocks another reset. Merely
        // rewriting an unchanged low ACK does not clear a newly written latch.
        if((reset&2) && (value&0x80)) { handshake(); return; }
        const bool next=(value&0x80) && !(reset&2);
        if(next==ack) return; // Only an edge, or a later REQ event, clocks a byte.
        ack=next;
        if(ack) scsi.signals|=ack_bit; else scsi.signals &= static_cast<std::uint16_t>(~ack_bit);
        handshake(); return;
    }
    case 4: {
        const bool was_reset=(reset&2)!=0;
        reset=value&15;
        if(reset&2) { interrupt_active &= 0x8F; if(!was_reset) handshake(); }
        else scsi.signals &= static_cast<std::uint16_t>(~rst);
        return;
    }
    default: throw Fault("invalid CD transport port");
    }
}
} // namespace pce
