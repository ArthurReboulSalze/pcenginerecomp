// Authored CDB, handshake and state fixtures. No firmware or disc excerpts.
#include "pce/checkpoint.hpp"
#include "pce/checkpoint_audio.hpp"
#include "pce/checkpoint_archive.hpp"
#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <memory>
#include <vector>

namespace {
using Policy=pce::CdUnknownPolicy;
unsigned checks=0, checkpoint_cuts=0;
void require(bool value,const char* why) {++checks;if(!value)throw std::runtime_error(why);}
template<class F> void refuses(F operation) {
    bool caught=false;try {operation();}catch(const std::exception&) {caught=true;}
    require(caught,"unsupported or invalid CD state was accepted");
}
bool known(unsigned op) {
    return op==0 || op==3 || op==8 || op==0xD8 || op==0xD9 || op==0xDA || op==0xDD || op==0xDE;
}
unsigned length(unsigned op) {
    // Independent literal protocol expectations, grouped by operation range.
    if(op<0x20)return 6;
    if(op>=0xA0 && op<0xC0)return 12;
    return 10;
}
std::vector<std::uint8_t> packet(unsigned op) {
    std::vector<std::uint8_t> bytes(length(op));bytes[0]=static_cast<std::uint8_t>(op);
    for(unsigned i=1;i<bytes.size();++i)bytes[i]=static_cast<std::uint8_t>(i*37+op);
    return bytes;
}
pce::CdControl prepare(Policy policy) {
    pce::CdControl cd;cd.enabled=cd.scsi.enabled=true;cd.unknown_policy=policy;return cd;
}
void later(pce::CdControl& cd,std::uint64_t delta) {cd.advance_to(cd.scsi.master_ticks+delta);}
void select(pce::CdControl& cd) {
    cd.transport_write(0,0);later(cd,75000);
    require(cd.scsi.phase==3 && cd.scsi.signals==0xD0,"selection did not request a CDB");
}
void high(pce::CdControl& cd) {cd.transport_write(2,0xE0);}
void low(pce::CdControl& cd) {cd.transport_write(2,0x60);}
void byte(pce::CdControl& cd,std::uint8_t value) {
    require(cd.scsi.phase==3 && (cd.scsi.signals&0x40),"CDB byte without requested command phase");
    const auto before=cd.scsi.command_size;
    cd.transport_write(1,value);high(cd);
    require(cd.scsi.command_size==before+1 && !(cd.scsi.signals&0x40),"CDB byte was not captured once");
    high(cd);require(cd.scsi.command_size==before+1,"held ACK captured an extra byte");low(cd);
}
void send(pce::CdControl& cd,std::span<const std::uint8_t> raw) {
    select(cd);
    for(unsigned i=0;i<raw.size();++i) {byte(cd,raw[i]);if(i+1<raw.size())later(cd,3000);}
}
void status(pce::CdControl& cd,unsigned expected) {
    require(cd.scsi.phase==7 && cd.transport_read(0)==0xD8 && cd.transport_read(1)==expected &&
            cd.irq2() && cd.interrupt_active==0x20,"status, IRQ or bus byte differs");
    high(cd);require(!cd.irq2() && !(cd.scsi.signals&0x40),"status ACK did not clear request/IRQ");
    low(cd);later(cd,1500);
    require(cd.scsi.phase==6 && cd.transport_read(0)==0xF8 && cd.transport_read(1)==expected && cd.irq2(),
            "message-in completion differs from the existing toolkit wire profile");
    high(cd);low(cd);later(cd,1500);
    require(cd.scsi.phase==0 && !cd.scsi.signals && !cd.irq2(),"completion did not release the bus");
}
std::array<std::uint8_t,18> sense(pce::CdControl& cd,bool automatic=false) {
    const std::array<std::uint8_t,6> cdb={3,0,0,0,0,0};send(cd,cdb);
    require(cd.scsi.response_size==18 && cd.pending_sense.key==0 && cd.pending_sense.asc==0,
            "REQUEST SENSE did not snapshot and consume pending context");
    std::array<std::uint8_t,18> result{};
    for(unsigned i=0;i<result.size();++i) {
        require(cd.transport_read(0)==0xC8 && cd.irq2(),"sense byte lacks DATA IN request/IRQ");
        result[i]=cd.transport_read(1);
        require(cd.transport_read(1)==result[i],"ordinary DATA IN read acknowledged a byte");
        if(automatic) {require(cd.transport_read(8)==result[i],"auto-ACK sampled a different byte");later(cd,21);}
        else {high(cd);require(!cd.irq2(),"sense ACK retained data IRQ");low(cd);}
        later(cd,i+1==result.size()?3000:900);
    }
    status(cd,0);return result;
}
std::array<std::uint8_t,18> expected_sense(bool error) {
    std::array<std::uint8_t,18> bytes{};bytes[0]=0x70;bytes[7]=10;
    if(error) {bytes[2]=5;bytes[12]=0x20;}return bytes;
}
std::array<std::uint8_t,18> replacement_sense() {
    auto bytes=expected_sense(false);bytes[2]=3;bytes[12]=0x11;bytes[13]=5;return bytes;
}
void ready(pce::CdControl& cd) {
    const std::array<std::uint8_t,6> cdb{};send(cd,cdb);later(cd,450000);status(cd,0);
}
void exhaustive() {
    for(unsigned op=0;op<256;++op)if(!known(op)) {
        for(auto policy:{Policy::fault,Policy::gear_good,Policy::nec_invalid}) {
            auto cd=prepare(policy);select(cd);
            cd.pending_origin.valid=true;cd.pending_origin.pc=0x4567;cd.pending_origin.ticks=cd.scsi.master_ticks;
            cd.pending_origin.mpr.fill(0xA5);cd.pending_origin.fetch={0x8D,1,0x18};cd.pending_origin.readable=7;
            const auto origin=cd.pending_origin;
            const auto raw=packet(op);const unsigned count=policy==Policy::nec_invalid?unsigned(raw.size()):1;
            for(unsigned i=0;i<count;++i) {
                cd.transport_write(1,raw[i]);high(cd);
                require(cd.scsi.command_size==i+1 && cd.unknown_opcodes[op]==0 && !cd.invalid_commands && !cd.unknown_commands,
                        "unknown CDB dispatched before ACK falling edge");
                high(cd);require(cd.scsi.command_size==i+1,"held unknown ACK captured an extra byte");
                if(policy==Policy::fault) {refuses([&]{low(cd);});break;}
                low(cd);
                if(i+1<count) {
                    require(cd.scsi.phase==3 && !cd.unknown_opcodes[op] && !cd.sense_errors && !cd.invalid_commands,
                            "partial NEC CDB was dispatched early");
                    later(cd,2999);require(!(cd.scsi.signals&0x40),"next byte requested before declared aggregate delay");
                    later(cd,1);require((cd.scsi.signals&0x40) && cd.scsi.command_size==i+1,"partial CDB was lost");
                }
            }
            require(cd.unknown_opcodes[op]==1 && cd.last_unknown_size==count && cd.scsi.last_command_size==count,
                    "unknown diagnostic count or complete CDB extent differs");
            require(std::equal(raw.begin(),raw.begin()+count,cd.last_unknown_command.begin()) &&
                    std::equal(raw.begin(),raw.begin()+count,cd.scsi.last_command.begin()),"captured CDB bytes differ");
            require(cd.last_unknown_origin.valid && cd.last_unknown_origin.pc==origin.pc && cd.last_unknown_origin.ticks==origin.ticks &&
                    cd.last_unknown_origin.mpr==origin.mpr && cd.last_unknown_origin.fetch==origin.fetch &&
                    cd.last_unknown_origin.readable==origin.readable && !cd.pending_origin.valid,"unknown origin was not preserved");
            if(policy==Policy::fault) {require(!cd.unknown_commands && !cd.invalid_commands && !cd.sense_errors,"fault fabricated a response");continue;}
            require(cd.scsi.command_size==0,"completed unknown command retained a partial buffer");
            const bool invalid=policy==Policy::nec_invalid;
            require(cd.unknown_commands==unsigned(!invalid) && cd.invalid_commands==unsigned(invalid) && cd.sense_errors==unsigned(invalid),
                    "response counters changed meaning");
            require(cd.pending_sense.key==(invalid?5:0) && cd.pending_sense.asc==(invalid?0x20:0),"unknown response sense class differs");
            low(cd);require(cd.unknown_opcodes[op]==1,"unchanged low ACK dispatched twice");
            status(cd,invalid?2:0);ready(cd);
            require(cd.pending_sense.key==(invalid?5:0),"successful command discarded unconsumed sense");
            require(sense(cd,op&1)==expected_sense(invalid),"unknown REQUEST SENSE bytes differ");
            require(sense(cd)==expected_sense(false),"REQUEST SENSE replayed consumed context");
            require(cd.unknown_opcodes[op]==1,"known follow-up was counted as an unknown command");
        }
    }
}
void unavailable_known_commands() {
    for(auto policy:{Policy::fault,Policy::gear_good,Policy::nec_invalid}) {
        auto cd=prepare(policy);std::array<std::uint8_t,10> cdb{};cdb[0]=0xD8;
        refuses([&]{send(cd,cdb);});
        require(cd.scsi.last_command_size==10 && !cd.unknown_opcodes[0xD8] && !cd.invalid_commands && !cd.unknown_commands,
                "known unavailable semantics were converted to an unknown response");
    }
}
void overflows_and_policy_bounds() {
    constexpr auto maximum=std::numeric_limits<std::uint64_t>::max();
    for(unsigned which=0;which<4;++which) {
        auto cd=prepare(which==1?Policy::gear_good:Policy::nec_invalid);
        if(which==0)cd.unknown_opcodes[0xFF]=maximum;
        if(which==1)cd.unknown_commands=maximum;
        if(which==2)cd.invalid_commands=maximum;
        if(which==3)cd.sense_errors=maximum;
        const auto raw=packet(0xFF);const auto count=which==1?1u:unsigned(raw.size());
        select(cd);
        for(unsigned i=0;i<count;++i) {
            cd.transport_write(1,raw[i]);high(cd);
            if(i+1==count)refuses([&]{low(cd);});else {low(cd);later(cd,3000);}
        }
        require(cd.unknown_opcodes[0xFF]==(which==0?maximum:0) && cd.unknown_commands==(which==1?maximum:0) &&
                cd.invalid_commands==(which==2?maximum:0) && cd.sense_errors==(which==3?maximum:0),
                "overflow check wrapped or partially counted a response");
    }
    auto invalid=prepare(static_cast<Policy>(3));
    refuses([&]{invalid.transport_write(0,0);});refuses([&]{invalid.transport_read(0);});refuses([&]{invalid.advance_to(1);});
    require(invalid.scsi.master_ticks==0 && !invalid.scsi.event,"invalid policy advanced the device");
}
std::array<std::uint8_t,18> finish(pce::CdControl& cd,const std::vector<std::uint8_t>& raw) {
    if(cd.ack)low(cd);
    while(cd.scsi.phase==3) {
        if(cd.scsi.event)cd.advance_to(cd.scsi.deadline);
        const auto index=cd.scsi.command_size;require(index<raw.size(),"continuation lost CDB position");
        byte(cd,raw[index]);
    }
    for(unsigned n=0;cd.scsi.phase!=0;++n) {
        require(n<8,"unknown status continuation did not free the bus");
        if(cd.scsi.event)cd.advance_to(cd.scsi.deadline);
        if(cd.scsi.phase==0)break;
        require((cd.scsi.phase==7 || cd.scsi.phase==6) && (cd.scsi.signals&0x40) && cd.transport_read(1)==2,
                "restored negative status/message byte differs");
        high(cd);low(cd);
    }
    return sense(cd,true);
}
template<class F> void checkpoint_state(const pce::CdControl& cd,F continuation) {
    ++checkpoint_cuts;
    auto source=std::make_unique<pce::Bus>();source->enable_cd_transport();source->cd=cd;
    pce::Cpu cpu;cpu.ticks=cd.scsi.master_ticks;
    const auto saved=pce::encode_checkpoint(*source,cpu);
    auto configured=std::make_unique<pce::Bus>();configured->enable_cd_transport();configured->cd.unknown_policy=Policy::nec_invalid;
    auto restored=pce::decode_checkpoint(saved,*configured);
    require(pce::encode_checkpoint(restored->bus,restored->cpu)==saved,"partial unknown state did not round-trip exactly");
    continuation(source->cd);continuation(restored->bus.cd);
    cpu.ticks=source->cd.scsi.master_ticks;restored->cpu.ticks=restored->bus.cd.scsi.master_ticks;
    require(pce::encode_checkpoint(*source,cpu)==pce::encode_checkpoint(restored->bus,restored->cpu),
            "full continued machine checkpoint differs");
    configured->cd.unknown_policy=Policy::gear_good;
    refuses([&]{pce::decode_checkpoint(saved,*configured);});
}
void checkpoint_cut(const pce::CdControl& cd,const std::vector<std::uint8_t>& raw) {
    checkpoint_state(cd,[&](pce::CdControl& current) {
        require(finish(current,raw)==expected_sense(true),"restored unknown completion or sense payload differs");
    });
}
void remaining_sense(pce::CdControl& cd,const std::array<std::uint8_t,18>& snapshot,std::uint64_t ack_origin) {
    // ACKed bytes are already consumed by the modeled drive. A pending pulse
    // completes at its retained guest deadline rather than being shortened.
    for(unsigned n=0;cd.scsi.phase==4;++n) {
        require(n<60,"active sense continuation did not complete");
        if(cd.ack) {
            if(cd.scsi.auto_ack_deadline)cd.advance_to(cd.scsi.auto_ack_deadline);
            else low(cd);
        } else if(cd.scsi.event)cd.advance_to(cd.scsi.deadline);
        else {
            const auto index=cd.data_bytes_acked-ack_origin;
            require(index<snapshot.size() && (cd.scsi.signals&0x40) && cd.transport_read(1)==snapshot[index],
                    "restored active SENSE snapshot byte changed");
            high(cd);low(cd);
        }
    }
    require(cd.data_bytes_acked-ack_origin==18,"sense continuation lost or repeated a byte");status(cd,0);
}
void checkpoint_sense(const pce::CdControl& cd,std::uint64_t ack_origin) {
    checkpoint_state(cd,[&](pce::CdControl& current) {
        remaining_sense(current,expected_sense(true),ack_origin);
        require(current.pending_sense.key==3 && current.pending_sense.asc==0x11 && current.pending_sense.ascq==5 &&
                current.pending_sense.failed_lba==0x1234,"active SENSE consumed a newer pending error");
        require(sense(current,true)==replacement_sense(),"new pending error was not preserved independently of active response");
        require(sense(current)==expected_sense(false),"replacement error was not consumed once");
    });
}
void checkpoints_and_reset() {
    for(unsigned op:{0x10u,0xFFu,0xA0u}) {
        const auto raw=packet(op);auto cd=prepare(Policy::nec_invalid);select(cd);
        cd.pending_origin.valid=true;cd.pending_origin.pc=0x4321;cd.pending_origin.ticks=cd.scsi.master_ticks;
        checkpoint_cut(cd,raw);
        for(unsigned i=0;i<raw.size();++i) {
            cd.transport_write(1,raw[i]);high(cd);checkpoint_cut(cd,raw);low(cd);
            if(i+1<raw.size()) {checkpoint_cut(cd,raw);later(cd,3000);checkpoint_cut(cd,raw);}
            else checkpoint_cut(cd,raw);
        }
        high(cd);checkpoint_cut(cd,raw);high(cd);checkpoint_cut(cd,raw);
        low(cd);checkpoint_cut(cd,raw);later(cd,1499);checkpoint_cut(cd,raw);
        later(cd,1);checkpoint_cut(cd,raw);
        high(cd);checkpoint_cut(cd,raw);low(cd);checkpoint_cut(cd,raw);
        later(cd,1499);checkpoint_cut(cd,raw);later(cd,1);checkpoint_cut(cd,raw);
        // Reset aborts only the pending transport; diagnostic/error history is
        // retained by the existing warm-reset profile and SENSE consumes it.
        cd.transport_write(4,2);cd.transport_write(4,0);
        require(!cd.scsi.command_size && !cd.pending_origin.valid && cd.scsi.phase==0 &&
                cd.invalid_commands==1 && cd.pending_sense.key==5,"warm reset altered completed error history");
        require(sense(cd)==expected_sense(true),"warm reset lost pending invalid-command context");
        auto partial=prepare(Policy::nec_invalid);select(partial);byte(partial,raw[0]);
        partial.transport_write(4,2);partial.transport_write(4,0);
        require(!partial.scsi.command_size && !partial.invalid_commands && !partial.unknown_opcodes[op] && !partial.sense_errors,
                "reset of a partial CDB fabricated a command response");ready(partial);
    }
    auto active=prepare(Policy::nec_invalid);send(active,packet(0xFF));status(active,2);
    const std::array<std::uint8_t,6> request={3,0,0,0,255,0};send(active,request);
    const auto ack_origin=active.data_bytes_acked;
    // Supervised independent-field fixture, not a claim that a second guest
    // command can raise an error without aborting an active DATA IN transfer.
    active.pending_sense={3,0x11,5,0,0x1234};++active.sense_errors;
    checkpoint_sense(active,ack_origin);
    for(unsigned i=0;i<18;++i) {
        require(active.transport_read(1)==expected_sense(true)[i],"SENSE snapshot was overwritten by newer pending context");
        if(i%2) {
            active.transport_read(8);checkpoint_sense(active,ack_origin);
            later(active,20);checkpoint_sense(active,ack_origin);later(active,1);
        } else {
            high(active);checkpoint_sense(active,ack_origin);high(active);checkpoint_sense(active,ack_origin);low(active);
        }
        if(i+1<18) {
            checkpoint_sense(active,ack_origin);later(active,899);checkpoint_sense(active,ack_origin);
            later(active,1);checkpoint_sense(active,ack_origin);
        } else later(active,3000);
    }
    status(active,0);require(sense(active)==replacement_sense(),"new pending context changed after active response drained");
    auto reset=prepare(Policy::nec_invalid);send(reset,packet(0xFF));status(reset,2);send(reset,request);
    reset.pending_sense={3,0x11,5,0,0x1234};++reset.sense_errors;
    reset.transport_write(4,2);
    checkpoint_state(reset,[&](pce::CdControl& current) {
        require(current.scsi.signals==0x100 && !current.scsi.response_size && !current.ack,
                "held reset retained a response or ACK");
        current.transport_write(4,0);
        require(sense(current)==replacement_sense(),"warm reset lost newer pending context");
    });
    auto bus=std::make_unique<pce::Bus>();bus->enable_cd_transport();
    pce::checkpoint::Writer writer;pce::checkpoint::write_audio(writer,*bus);
    // The policy follows the fixed CD fields and absent failed-LBA token.
    constexpr unsigned policy_offset=93;
    auto corrupt=writer.data;require(corrupt.size()>policy_offset && corrupt[policy_offset]==0,"authored codec policy offset changed");
    corrupt[policy_offset]=3;
    refuses([&]{pce::checkpoint::Reader reader(corrupt);pce::checkpoint::read_audio(reader,*bus);});
    bus->cd.unknown_policy=static_cast<Policy>(255);
    refuses([&]{pce::checkpoint::Writer out;pce::checkpoint::write_audio(out,*bus);});
}
}
int main() {try {
    exhaustive();unavailable_known_commands();overflows_and_policy_bounds();checkpoints_and_reset();
    std::cout<<checks<<" authored unknown-CD checks, "<<checkpoint_cuts<<" full checkpoint cuts passed\n";
}catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}}
