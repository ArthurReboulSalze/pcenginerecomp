#include "pce/runtime.hpp"
#include <algorithm>
#include <limits>

namespace pce {
void Bus::configure_system_card(SystemCardProfile profile,std::span<const std::uint8_t> rom,
                                std::uint8_t ram_fill) {
    if(profile!=SystemCardProfile::standard && profile!=SystemCardProfile::super)
        throw Fault("System Card setup requires standard or super hardware");
    if(rom.size()!=262144) throw Fault("System Card ROM must be a raw 256 KiB image");
    if(system_card!=SystemCardProfile::none || system_card_powered || hucard || arcade_card ||
       hucard_powered || hucard_rom_bytes ||
       hucard_profile!=HuCardProfile::none || hucard_mapper_latch || !hucard_mapper_rom.empty() ||
       std::any_of(hucard_banks.begin(),hucard_banks.end(),[](auto b){return b!=0;}) || work_ram_mirrors ||
       cd.enabled || vdc.enabled || vce.enabled || psg.enabled || adpcm.enabled ||
       pcm.enabled || joypad.enabled || irq.enabled || io_latch ||
       std::any_of(kind.begin(),kind.end(),[](auto k){return k!=BankKind::unmapped;}) ||
       std::any_of(generation.begin(),generation.end(),[](auto g){return g!=0;}) ||
       std::any_of(bytes->begin(),bytes->end(),[](auto b){return b!=0;}))
        throw Fault("System Card setup requires a pristine bus");
    system_card=profile;
    for(unsigned bank=0;bank<0x80;++bank) kind[bank]=BankKind::rom;
    if(profile==SystemCardProfile::super)
        for(unsigned bank=0x68;bank<=0x7F;++bank) kind[bank]=BankKind::ram;
    for(unsigned bank=0x80;bank<=0x87;++bank) kind[bank]=BankKind::ram;
    kind[0xF7]=BankKind::bram;
    enable_work_ram_mirrors();
    kind[0xFF]=BankKind::io;
    load(0,rom.data(),rom.size());
    for(unsigned bank=0;bank<256;++bank) {
        if(kind[bank]!=BankKind::ram) continue;
        const auto address=backing_address(bank<<13);
        std::fill_n(bytes->begin()+address,8192,ram_fill);
        generation[bank]=1;
    }
    io_latch=0xFF;
}
void Bus::power_on_cpu(Cpu& cpu,std::uint8_t register_fill,std::uint8_t mpr_fill) {
    if(system_card==SystemCardProfile::none && !hucard)
        throw Fault("CPU power-on requires an explicit System Card or HuCard memory profile");
    if(system_card_powered || hucard_powered) throw Fault("CPU power-on has already initialized this bus");
    if(hucard_profile==HuCardProfile::sf2 && hucard_mapper_latch)
        throw Fault("SF2 CPU power-on requires the untouched zero mapper latch");
    if(vdc.raster.master_ticks || vdc.raster.frames || irq.master_ticks ||
       cd.scsi.master_ticks || cd.audio.sample_clock_ticks || cd.audio.sample_ticks ||
       psg.clock_ticks || adpcm.master_ticks || pcm.master_ticks)
        throw Fault("CPU power-on requires devices at their initial clock phase");
    // Validate before touching CPU, latches or interrupt state. The vector
    // must be driven by the selected ROM, not by RAM, MMIO or an absent bank.
    if(kind[0]!=BankKind::rom) throw Fault(hucard ? "HuCard reset vector requires ROM bank 00":"System Card reset vector requires ROM bank 00");
    const auto low=peek(0x1FFE),high=peek(0x1FFF);
    if(!low || !high) throw Fault(hucard ? "HuCard reset vector is unreadable":"System Card reset vector is unreadable");
    Cpu fresh;
    fresh.a=fresh.x=fresh.y=fresh.sp=register_fill;
    fresh.p=static_cast<std::uint8_t>((register_fill&~(T|D|B))|I);
    fresh.mpr.fill(mpr_fill); fresh.mpr[7]=0;
    fresh.pc=static_cast<std::uint16_t>(*low|(unsigned(*high)<<8));
    fresh.clock_divisor=12;
    cpu=fresh;
    io_latch=0xFF;
    if(vdc.enabled) vdc.read_buffer=0xFFFF;
    const bool irq_enabled=irq.enabled;
    irq=Interrupts{};irq.enabled=irq_enabled;
    if(hucard) hucard_powered=true;
    else system_card_powered=true;
}
void Bus::enable_work_ram_mirrors() {
    if(work_ram_mirrors) return;
    // Do not silently discard an independently populated sandbox bank.
    for(unsigned bank=0xF9;bank<=0xFB;++bank)
        if(kind[bank]!=BankKind::unmapped ||
           std::any_of(bytes->begin()+(bank<<13),bytes->begin()+((bank+1)<<13),[](auto x){return x!=0;}))
            throw Fault("WRAM mirror setup requires unoccupied alias banks");
    if(kind[0xF8]!=BankKind::unmapped && kind[0xF8]!=BankKind::ram)
        throw Fault("WRAM mirror setup requires unmapped or RAM bank F8");
    for(unsigned bank=0xF8;bank<=0xFB;++bank) kind[bank]=BankKind::ram;
    work_ram_mirrors=true;
}
void Bus::enable_adpcm() {
    if(hucard) throw Fault("Base HuCard profile does not attach ADPCM/CD hardware");
    if(!cd.scsi.enabled) enable_cd_transport();
    adpcm=Adpcm{};adpcm.enabled=true;cd.audio_enabled=true;
}
void Bus::enable_psg() {psg=Psg{};psg.enabled=true;kind[255]=BankKind::io;}
void Bus::enable_cd_control() {
    if(hucard) throw Fault("Base HuCard profile does not attach CD hardware");
    cd=CdControl{}; cd.enabled=true;
    kind[0xFF]=BankKind::io; kind[0xF7]=BankKind::bram;
}
std::uint8_t Bus::read(Cpu& cpu, std::uint16_t address) {
    sync(cpu);
    const auto pa=physical(cpu,address), bank=pa>>13, offset=pa&8191;
    if(arcade_card) {
        if(bank>=0x40 && bank<=0x43) return arcade_card->read_data(bank-0x40);
        if(bank==0xFF && kind[bank]==BankKind::io && offset>=0x1A00 && offset<0x1C00)
            return arcade_card->read_register(static_cast<std::uint16_t>(offset));
    }
    if(hucard && bank==0xFF && kind[bank]==BankKind::io && offset>=0x1800)return 0xFF;
    if(bank==0xFF && kind[bank]==BankKind::io && offset>=0x1C00 &&
       system_card!=SystemCardProfile::none) return 0xFF; // Undecoded ordinary expansion window.
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x1000 && joypad.enabled)
        return io_latch=joypad.read();
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x800 && psg.enabled)
        return io_latch;
    if(kind[bank]==BankKind::io && bank==255 && irq.enabled) {
        if((offset&0x1C00)==0x1400) {
            ++irq.reads;
            if((offset&3)==2) io_latch=static_cast<std::uint8_t>((io_latch&0xF8)|irq.mask);
            else if((offset&3)==3) io_latch=static_cast<std::uint8_t>((io_latch&0xF8)|irq_requests());
            return io_latch;
        }
        if((offset&0x1C00)==0xC00) {
            ++irq.reads;
            const auto phase=irq.timer_enabled ? irq.timer_deadline-cpu.ticks:irq.timer_frozen_phase;
            const auto counter=irq.timer_counter==0 && phase<=15 ? 127:irq.timer_counter;
            return io_latch=static_cast<std::uint8_t>((io_latch&128)|counter);
        }
    }
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x400 && vce.enabled) {
        const auto value=vce.read(offset);
        ++cpu.cycles;cpu.ticks+=cpu.clock_divisor;
        if(irq.enabled) {sync(cpu);sample_interrupt(cpu);}
        return value;
    }
    if(kind[bank]==BankKind::io && bank==255 && offset<1024 && vdc.enabled) {
        if(vdc.raster.enabled && vdc.queued_cpu_accesses) {
            // The mapped read's fixed wait precedes the port observation.
            clock_cpu(cpu,1);
            wait_vdc(cpu,offset&3,false);
            return vdc.read(offset);
        }
        const auto value=vdc.read(offset);
        ++cpu.cycles; cpu.ticks+=cpu.clock_divisor;
        if(irq.enabled) {sync(cpu);sample_interrupt(cpu);} // Fixed memory-mapped VDC wait.
        return value;
    }
    if(kind[bank]==BankKind::bram && bank==0xF7 && cd.enabled)
        return cd.bram_unlocked && offset<2048 ? (*bytes)[pa]:0xFF;
    if(kind[bank]==BankKind::io && bank==255 && cd.audio_enabled && offset==0x180F) {++cd.reads;return cd.audio.fader;}
    if(kind[bank]==BankKind::io && bank==255 && adpcm.enabled && offset>=0x1809 && offset<=0x180E) {
        ++cd.reads;return adpcm.read(offset&15);
    }
    if(kind[bank]==BankKind::io && bank==0xFF && cd.enabled) {
        if(system_card!=SystemCardProfile::none && offset>=0x18C0 && offset<=0x18C3) {
            constexpr std::uint8_t signature[]{0x00,0xAA,0x55,0x03};
            ++cd.reads;
            return system_card==SystemCardProfile::super ? signature[offset&3]:0xFF;
        }
        std::uint8_t value;
        switch(offset) {
        case 0x1800: case 0x1801: case 0x1808:
            if(!cd.scsi.enabled) throw Fault("CD transport profile is not enabled");
            value=cd.transport_read(offset&15); break;
        case 0x1802: value=static_cast<std::uint8_t>(cd.interrupt_enable | (cd.ack ? 0x80:0)); break;
        case 0x1803: cd.bram_unlocked=false; value=static_cast<std::uint8_t>(cd.interrupt_active | 0x10 | (cd.audio.sample_right ? 0:2)); break;
        case 0x1804: value=cd.reset; break;
        case 0x1805: value=static_cast<std::uint8_t>(cd.audio.sample_latch); break;
        case 0x1806: value=static_cast<std::uint8_t>(cd.audio.sample_latch>>8); break;
        case 0x1807: value=cd.bram_unlocked ? 0x80:0; break;
        default:
            // Standalone standard CD hardware decodes a 1 KiB window. Its
            // unassigned registers read pull-ups in Gear and Mesen. Known
            // disabled ADPCM ports still require their semantics.
            if(offset>=0x1800 && offset<0x1C00 &&
               !(offset>=0x1809 && offset<=0x180F)) value=0xFF;
            else throw Fault("unsupported CD/I/O read at physical " + std::to_string(pa));
            break;
        }
        ++cd.reads; return value;
    }
    if((system_card!=SystemCardProfile::none || hucard) && kind[bank]==BankKind::unmapped) return 0xFF;
    auto result=peek(pa);
    if(!result) throw Fault("unimplemented I/O or unmapped read at logical " + std::to_string(address));
    return *result;
}
unsigned Bus::write_timed(Cpu& cpu, std::uint16_t address, std::uint8_t value,
                          unsigned remaining_base) {
    const auto pa=physical(cpu,address);
    // HuC6280 PSG writes flush the current instruction's pending base clocks.
    // Resolve the actual MPR and device profile; a logical $0800 alone is not I/O.
    if((pa>>13)==255 && kind[255]==BankKind::io && (pa&0x1C00)==0x0800 && psg.enabled) {
        clock_cpu(cpu,remaining_base);
        remaining_base=0;
    }
    write(cpu,address,value);
    return remaining_base;
}
void Bus::write(Cpu& cpu, std::uint16_t address, std::uint8_t value) {
    sync(cpu);
    const auto pa=physical(cpu,address);
    const auto bank=pa>>13, offset=pa&8191;
    if(arcade_card) {
        if(bank>=0x40 && bank<=0x43) {arcade_card->write_data(bank-0x40,value);return;}
        if(bank==0xFF && kind[bank]==BankKind::io && offset>=0x1A00 && offset<0x1C00) {
            arcade_card->write_register(static_cast<std::uint16_t>(offset),value);return;
        }
    }
    if(hucard_profile==HuCardProfile::sf2 && bank==0 && offset>=0x1FF0 && kind[bank]==BankKind::rom) {
        select_hucard_bank(static_cast<std::uint8_t>(offset));return;
    }
    if(hucard && bank==0xFF && kind[bank]==BankKind::io && offset>=0x1800)return;
    if(bank==0xFF && kind[bank]==BankKind::io && offset>=0x1C00 &&
       system_card!=SystemCardProfile::none) return; // No device drives this ordinary expansion window.
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x1000 && joypad.enabled) {
        joypad.write(value); io_latch=value; return;
    }
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x800 && psg.enabled) {
        if(pcm.enabled)psg.advance_to(cpu.ticks);
        psg.write(offset,value);io_latch=value;return;
    }
    if(kind[bank]==BankKind::io && bank==255 && irq.enabled) {
        if((offset&0x1C00)==0x1400) {
            ++irq.writes; io_latch=value;
            if((offset&3)==2) irq.mask=value&7;
            else if((offset&3)==3) {irq.timer_pending=false;irq.external&=static_cast<std::uint8_t>(~4);}
            return;
        }
        if((offset&0x1C00)==0xC00) {
            ++irq.writes;io_latch=value;
            if(offset&1) {
                const bool enabled=(value&1)!=0;
                if(enabled!=irq.timer_enabled) {
                    irq.timer_enabled=enabled;
                    irq.timer_frozen_phase=3072;
                    if(enabled) {
                        irq.timer_counter=irq.timer_reload;
                        if(cpu.ticks>std::numeric_limits<std::uint64_t>::max()-3072) throw Fault("timer clock overflow");
                        irq.timer_deadline=cpu.ticks+3072;
                    } else irq.timer_deadline=0;
                }
            } else irq.timer_reload=value&127;
            return;
        }
    }
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x400 && vce.enabled) {
        if(!(offset&7)) vdc.write_vce_control(value);
        vce.write(offset,value);
        ++cpu.cycles;cpu.ticks+=cpu.clock_divisor;
        if(irq.enabled) {sync(cpu);sample_interrupt(cpu);}
        return;
    }
    if(kind[bank]==BankKind::io && bank==255 && (offset&0x1C00)==0x400 && !(offset&7) && vdc.raster.enabled) {
        vdc.write_vce_control(value);
        ++cpu.cycles; cpu.ticks+=cpu.clock_divisor;
        if(irq.enabled) {sync(cpu);sample_interrupt(cpu);}
        return;
    }
    if(kind[bank]==BankKind::io && bank==255 && offset<1024 && vdc.enabled) {
        if(vdc.raster.enabled && vdc.queued_cpu_accesses) {
            wait_vdc(cpu,offset&3,true);
            vdc.write(offset,value);
            clock_cpu(cpu,1); // A mapped write injects its fixed cycle after the port.
            return;
        }
        vdc.write(offset,value);
        ++cpu.cycles; cpu.ticks+=cpu.clock_divisor;
        if(irq.enabled) {sync(cpu);sample_interrupt(cpu);}
        return;
    }
    if(kind[bank]==BankKind::bram && bank==0xF7 && cd.enabled) {
        if(cd.bram_unlocked && offset<2048 && (*bytes)[pa]!=value) { (*bytes)[pa]=value; ++generation[bank]; }
        return;
    }
    if(kind[bank]==BankKind::io && bank==255 && cd.audio_enabled && offset==0x180F) {cd.write_fader(value);++cd.writes;return;}
    if(kind[bank]==BankKind::io && bank==255 && adpcm.enabled && offset>=0x1808 && offset<=0x180E) {
        adpcm.write(offset&15,value,&cd);
        if(pcm.enabled && (adpcm.control&128))pcm.reset_adpcm_filter();
        ++cd.writes;return;
    }
    if(kind[bank]==BankKind::io && bank==0xFF && cd.enabled) {
        if(system_card!=SystemCardProfile::none && offset>=0x18C0 && offset<=0x18C3) {
            ++cd.writes;return; // Read-only System Card identification pins.
        }
        switch(offset) {
        case 0x1800: case 0x1801:
            if(!cd.scsi.enabled) throw Fault("CD transport profile is not enabled");
            if(offset==0x1801 && cd.scsi.phase==3 && cd.scsi.command_size==0) {
                cd.pending_origin=CommandOrigin{};
                cd.pending_origin.valid=true;cd.pending_origin.pc=cpu.pc;
                cd.pending_origin.ticks=cpu.ticks;cd.pending_origin.mpr=cpu.mpr;
                for(unsigned i=0;i<7;++i) {
                    const auto byte=peek(physical(cpu,static_cast<std::uint16_t>(cpu.pc+i)));
                    if(byte) {cd.pending_origin.fetch[i]=*byte;cd.pending_origin.readable|=static_cast<std::uint8_t>(1u<<i);}
                }
            }
            cd.transport_write(offset&15,value); break;
        case 0x1802:
            if(cd.scsi.enabled) cd.transport_write(2,value);
            else { cd.ack=(value&0x80)!=0 && !(cd.reset&2); cd.interrupt_enable=value&0x7F; }
            break;
        case 0x1803: break; // Read-only status: writes do not lock BRAM.
        case 0x1804:
            if(cd.scsi.enabled) cd.transport_write(4,value);
            else {
                cd.reset=value&15;
                if(value&2) {cd.interrupt_active &= 0x8F;cd.ack=false;}
            }
            break;
        case 0x1807: cd.bram_unlocked=(value&0x80)!=0; break;
        case 0x1805: cd.audio.latch_sample(cpu.ticks); break;
        case 0x1806: break; // Hardware accepts the write without latching.
        default:
            // The CD decoder covers this 1 KiB window. Its unassigned
            // registers accept writes without driving other device/latch
            // state. Known ADPCM/fader ports still require their profiles;
            // this branch must not absorb disabled hardware elsewhere.
            if(offset>=0x1800 && offset<0x1C00 &&
               !(offset>=0x1808 && offset<=0x180F)) break;
            throw Fault("unsupported CD/I/O write at physical " + std::to_string(pa));
        }
        ++cd.writes; return;
    }
    if((system_card!=SystemCardProfile::none || hucard) &&
       (kind[bank]==BankKind::rom || kind[bank]==BankKind::unmapped)) return;
    if(kind[pa >> 13] != BankKind::ram) throw Fault("write to ROM, unimplemented I/O, or unmapped bank");
    const auto backing=backing_address(pa);
    if((*bytes)[backing] != value) {
        (*bytes)[backing]=value;
        if(work_ram_mirrors && (backing>>13)==0xF8)
            for(unsigned alias=0xF8;alias<=0xFB;++alias) ++generation[alias];
        else if(hucard_profile==HuCardProfile::populous && bank>=0x40 && bank<=0x5F)
            for(unsigned alias=0x40+(bank&3);alias<=0x5F;alias+=4)++generation[alias];
        else ++generation[pa>>13];
    }
}
void Bus::load(std::uint32_t address, const std::uint8_t* source, std::size_t count) {
    if(address > bytes->size() || count > bytes->size()-address) throw Fault("load exceeds physical address space");
    if(arcade_card && count && address<0x88000 && address+count>0x80000)
        throw Fault("Loader writes cannot target side-effecting Arcade Card windows");
    if(!work_ram_mirrors) std::copy_n(source,count,bytes->begin()+address);
    else for(std::size_t i=0;i<count;++i) {
        const auto physical=static_cast<std::uint32_t>(address+i);
        (*bytes)[backing_address(physical)]=source[i];
        if(hucard_profile==HuCardProfile::sf2 && physical<0x100000 && kind[physical>>13]==BankKind::rom) {
            const auto file_offset=physical<0x80000 ? physical:physical+(hucard_mapper_latch&3)*0x80000;
            hucard_mapper_rom[file_offset]=source[i];
        }
    }
    if(count) {
        std::array<bool,256> touched{};
        for(std::size_t bank=address>>13;bank<=(address+count-1)>>13;++bank) {
            if(work_ram_mirrors && bank>=0xF8 && bank<=0xFB)
                for(unsigned alias=0xF8;alias<=0xFB;++alias) touched[alias]=true;
            else if(hucard_profile==HuCardProfile::populous && bank>=0x40 && bank<=0x5F)
                for(unsigned alias=0x40+(static_cast<unsigned>(bank)&3);alias<=0x5F;alias+=4)touched[alias]=true;
            else if(hucard && bank<0x80 && kind[bank]==BankKind::rom) {
                for(unsigned alias=0;alias<0x80;++alias)
                    if(kind[alias]==BankKind::rom && hucard_banks[alias]==hucard_banks[bank])touched[alias]=true;
            }
            else if(system_card!=SystemCardProfile::none && bank<0x80 && kind[bank]==BankKind::rom) {
                for(unsigned alias=static_cast<unsigned>(bank)&31;alias<0x80;alias+=32)
                    if(kind[alias]==BankKind::rom) touched[alias]=true;
            }
            else touched[bank]=true;
        }
        for(unsigned bank=0;bank<256;++bank) if(touched[bank]) ++generation[bank];
    }
}
void push(Bus& bus, Cpu& cpu, std::uint8_t value) { bus.write(cpu,0x2100|cpu.sp,value); --cpu.sp; }
std::uint8_t pop(Bus& bus, Cpu& cpu) { ++cpu.sp; return bus.read(cpu,0x2100|cpu.sp); }

namespace {
enum class DataOp { none, ora, and_, eor, adc, sta, lda, cmp, sbc,
                    ldx, ldy, stx, sty, stz, cpx, cpy };
enum class Mode { immediate, zp, zpx, zpy, absolute, absx, absy, indx, indy, indirect };
struct DataInstruction { DataOp op=DataOp::none; Mode mode=Mode::immediate; };

DataInstruction data_instruction(std::uint8_t opcode) {
    // Eight regular instruction families, plus the irregular X/Y/zero forms.
    const auto low=opcode&31;
    Mode mode;
    switch(low) {
    case 1: mode=Mode::indx; break; case 5: mode=Mode::zp; break;
    case 9: mode=Mode::immediate; break; case 13: mode=Mode::absolute; break;
    case 17: mode=Mode::indy; break; case 18: mode=Mode::indirect; break;
    case 21: mode=Mode::zpx; break; case 25: mode=Mode::absy; break;
    case 29: mode=Mode::absx; break;
    default: goto irregular;
    }
    if(opcode!=0x89) {
        constexpr DataOp families[]={DataOp::ora,DataOp::and_,DataOp::eor,DataOp::adc,
                                    DataOp::sta,DataOp::lda,DataOp::cmp,DataOp::sbc};
        return {families[opcode>>5],mode};
    }
irregular:
    switch(opcode) {
    case 0xA2: return {DataOp::ldx,Mode::immediate};
    case 0xA6: return {DataOp::ldx,Mode::zp};
    case 0xB6: return {DataOp::ldx,Mode::zpy};
    case 0xAE: return {DataOp::ldx,Mode::absolute};
    case 0xBE: return {DataOp::ldx,Mode::absy};
    case 0xA0: return {DataOp::ldy,Mode::immediate};
    case 0xA4: return {DataOp::ldy,Mode::zp};
    case 0xB4: return {DataOp::ldy,Mode::zpx};
    case 0xAC: return {DataOp::ldy,Mode::absolute};
    case 0xBC: return {DataOp::ldy,Mode::absx};
    case 0x86: return {DataOp::stx,Mode::zp}; case 0x96: return {DataOp::stx,Mode::zpy};
    case 0x8E: return {DataOp::stx,Mode::absolute};
    case 0x84: return {DataOp::sty,Mode::zp}; case 0x94: return {DataOp::sty,Mode::zpx};
    case 0x8C: return {DataOp::sty,Mode::absolute};
    case 0x64: return {DataOp::stz,Mode::zp}; case 0x74: return {DataOp::stz,Mode::zpx};
    case 0x9C: return {DataOp::stz,Mode::absolute}; case 0x9E: return {DataOp::stz,Mode::absx};
    case 0xE0: return {DataOp::cpx,Mode::immediate}; case 0xE4: return {DataOp::cpx,Mode::zp};
    case 0xEC: return {DataOp::cpx,Mode::absolute};
    case 0xC0: return {DataOp::cpy,Mode::immediate}; case 0xC4: return {DataOp::cpy,Mode::zp};
    case 0xCC: return {DataOp::cpy,Mode::absolute};
    default: return {};
    }
}
unsigned data_size(Mode mode) {
    return mode==Mode::absolute || mode==Mode::absx || mode==Mode::absy ? 3 : 2;
}
void execute_data(Bus& bus, Cpu& s, DataInstruction ins, std::uint8_t lo,
                  std::uint16_t word, unsigned& cycles) {
    std::uint16_t address=0;
    cycles=4;
    switch(ins.mode) {
    case Mode::immediate: cycles=2; break;
    case Mode::zp: address=0x2000|lo; break;
    case Mode::zpx: address=0x2000|((lo+s.x)&255); break;
    case Mode::zpy: address=0x2000|((lo+s.y)&255); break;
    case Mode::absolute: address=word; cycles=5; break;
    case Mode::absx: address=static_cast<std::uint16_t>(word+s.x); cycles=5; break;
    case Mode::absy: address=static_cast<std::uint16_t>(word+s.y); cycles=5; break;
    default: {
        unsigned pointer=lo;
        if(ins.mode==Mode::indx) pointer=(pointer+s.x)&255;
        const auto low=bus.read(s,static_cast<std::uint16_t>(0x2000|pointer));
        const auto high=bus.read(s,static_cast<std::uint16_t>(0x2000|((pointer+1)&255)));
        address=static_cast<std::uint16_t>(low+256*high+(ins.mode==Mode::indy ? s.y:0));
        cycles=7; break;
    }
    }
    switch(ins.op) {
    case DataOp::sta: cycles=bus.write_timed(s,address,s.a,cycles); return;
    case DataOp::stx: cycles=bus.write_timed(s,address,s.x,cycles); return;
    case DataOp::sty: cycles=bus.write_timed(s,address,s.y,cycles); return;
    case DataOp::stz: cycles=bus.write_timed(s,address,0,cycles); return;
    default: break;
    }
    const auto operand=ins.mode==Mode::immediate ? lo:bus.read(s,address);
    switch(ins.op) {
    case DataOp::lda: s.a=operand; s.nz(s.a); return;
    case DataOp::ldx: s.x=operand; s.nz(s.x); return;
    case DataOp::ldy: s.y=operand; s.nz(s.y); return;
    case DataOp::cmp: case DataOp::cpx: case DataOp::cpy: {
        const auto reg=ins.op==DataOp::cmp ? s.a:ins.op==DataOp::cpx ? s.x:s.y;
        s.p=static_cast<std::uint8_t>((s.p&~C)|(reg>=operand ? C:0));
        s.nz(static_cast<std::uint8_t>(reg-operand)); return;
    }
    default: break;
    }
    const bool transfer=(s.p&T) && ins.op!=DataOp::sbc;
    const auto destination=static_cast<std::uint16_t>(0x2000|s.x);
    const auto left=transfer ? bus.read(s,destination):s.a;
    if(transfer) cycles+=3;
    std::uint8_t result;
    switch(ins.op) {
    case DataOp::ora: result=left|operand; break;
    case DataOp::and_: result=left&operand; break;
    case DataOp::eor: result=left^operand; break;
    default: {
        const bool subtract=ins.op==DataOp::sbc;
        const unsigned right=subtract ? operand^255U:operand;
        int sum=left+right+(s.p&C);
        if(s.p&D) {
            ++cycles;
            int low=(left%16)+(right%16)+(s.p&C);
            if(subtract) { if(low<16) low-=6; }
            else if(low>9) low+=6;
            sum=(left&0xF0)+(right&0xF0)+(low>15 ? 16:0)+(low&15);
            if(subtract) { if(sum<256) sum-=96; }
            else if(sum>159) sum+=96;
        } else {
            const bool overflow=(~(left^right)&(left^sum)&0x80)!=0;
            s.p=static_cast<std::uint8_t>((s.p&~V)|(overflow ? V:0));
        }
        s.p=static_cast<std::uint8_t>((s.p&~C)|(sum>255 ? C:0));
        result=static_cast<std::uint8_t>(sum); break;
    }
    }
    if(transfer) bus.write(s,destination,result); else s.a=result;
    s.nz(result);
}
enum class RmwOp { none, asl, rol, lsr, ror, inc, dec };
struct RmwInstruction { RmwOp op=RmwOp::none; unsigned size=1; bool indexed=false; };
RmwInstruction rmw_instruction(std::uint8_t opcode) {
    switch(opcode) {
    case 0x0A: return {RmwOp::asl}; case 0x2A: return {RmwOp::rol};
    case 0x4A: return {RmwOp::lsr}; case 0x6A: return {RmwOp::ror};
    case 0x1A: return {RmwOp::inc}; case 0x3A: return {RmwOp::dec};
    default: break;
    }
    const unsigned form=opcode&31;
    if(form!=6 && form!=14 && form!=22 && form!=30) return {};
    RmwOp operation;
    switch(opcode>>5) {
    case 0: operation=RmwOp::asl; break; case 1: operation=RmwOp::rol; break;
    case 2: operation=RmwOp::lsr; break; case 3: operation=RmwOp::ror; break;
    case 6: operation=RmwOp::dec; break; case 7: operation=RmwOp::inc; break;
    default: return {};
    }
    return {operation,(form&8) ? 3U:2U,(form&16)!=0};
}
void execute_rmw(Bus& bus, Cpu& s, RmwInstruction ins, std::uint8_t lo,
                 std::uint16_t word, unsigned& cycles) {
    const bool accumulator=ins.size==1;
    const unsigned index=ins.indexed ? s.x:0;
    const auto address=static_cast<std::uint16_t>(ins.size==2 ? 0x2000|((lo+index)&255):word+index);
    const unsigned value=accumulator ? s.a:bus.read(s,address);
    unsigned result=value;
    switch(ins.op) {
    case RmwOp::asl: result=value<<1; break;
    case RmwOp::rol: result=(value<<1)|(s.p&C); break;
    case RmwOp::lsr: result=value>>1; break;
    case RmwOp::ror: result=(value>>1)|((s.p&C)<<7); break;
    case RmwOp::inc: result=value+1; break;
    case RmwOp::dec: result=value-1; break;
    default: throw Fault("invalid internal RMW operation");
    }
    const auto byte=static_cast<std::uint8_t>(result);
    cycles=accumulator ? 2:ins.size==2 ? 6:7;
    if(accumulator) s.a=byte; else cycles=bus.write_timed(s,address,byte,cycles);
    if(ins.op!=RmwOp::inc && ins.op!=RmwOp::dec) {
        const bool carry=ins.op==RmwOp::asl || ins.op==RmwOp::rol ? (value&128)!=0:(value&1)!=0;
        s.p=static_cast<std::uint8_t>((s.p&~C)|(carry ? C:0));
    }
    s.nz(byte);
}
unsigned test_size(std::uint8_t op) {
    if((op&15)==15) return 3;
    switch(op) {
    case 0x89: case 0x24: case 0x34: case 0x04: case 0x14: return 2;
    case 0x2C: case 0x3C: case 0x0C: case 0x1C: case 0x83: case 0xA3: return 3;
    case 0x93: case 0xB3: return 4;
    default: return 0;
    }
}
void execute_test(Bus& bus, Cpu& s, std::uint8_t op, std::uint8_t lo,
                  std::uint16_t word, std::uint8_t last, std::uint16_t& next, unsigned& cycles) {
    if((op&15)==15) {
        const bool bit=(bus.read(s,0x2000|lo)&(1U<<((op>>4)&7)))!=0;
        const bool take=bit==((op&128)!=0);
        if(take) next=static_cast<std::uint16_t>(next+static_cast<std::int8_t>(word>>8));
        cycles=take ? 8:6; return;
    }
    const bool tst=(op&0xCF)==0x83;
    const bool modify=op==0x04 || op==0x14 || op==0x0C || op==0x1C;
    std::uint16_t address=word;
    if(tst) {
        const auto operand=word>>8;
        address=op&16 ? static_cast<std::uint16_t>(operand+256*last+(op&32 ? s.x:0)):
                       static_cast<std::uint16_t>(0x2000|((operand+(op&32 ? s.x:0))&255));
        cycles=op&16 ? 8:7;
    } else if(op!=0x89) {
        address=op&8 ? static_cast<std::uint16_t>(word+(op==0x3C ? s.x:0)):
                       static_cast<std::uint16_t>(0x2000|((lo+(op==0x34 ? s.x:0))&255));
        cycles=(op&8 ? 5:4)+(modify ? 2:0);
    }
    const auto value=op==0x89 ? lo:bus.read(s,address);
    const auto mask=tst ? lo:s.a;
    std::uint8_t result=static_cast<std::uint8_t>(value&mask);
    if(modify) {
        result=static_cast<std::uint8_t>(op&16 ? value&~s.a:value|s.a);
        cycles=bus.write_timed(s,address,result,cycles);
    }
    s.p=static_cast<std::uint8_t>((s.p&~(N|V|Z))|(value&0xC0)|(result==0 ? Z:0));
}
} // namespace

Exit interpret_step(Bus& bus, Cpu& s, std::uint64_t deadline) {
    if(s.ticks >= deadline) return Exit::budget;
    bus.begin_instruction(s);
    const auto op=bus.read(s,s.pc);
    if(op==0x73 || op==0xC3 || op==0xD3 || op==0xE3 || op==0xF3) {
        interpret_block(bus,s,op); return Exit::executed;
    }
    if(op==0x00) {
        // Skip the signature without reading it. In particular it must not
        // poll an MMIO device merely because the encoding crosses a page.
        const auto resume=static_cast<std::uint16_t>(s.pc+2);
        push(bus,s,static_cast<std::uint8_t>(resume>>8));
        push(bus,s,static_cast<std::uint8_t>(resume));
        push(bus,s,static_cast<std::uint8_t>((s.p|B)&~T));
        s.p=static_cast<std::uint8_t>((s.p|I)&~(D|T));
        const auto low=bus.read(s,0xFFF6),high=bus.read(s,0xFFF7);
        s.pc=static_cast<std::uint16_t>(low|(unsigned(high)<<8));
        bus.retire(s,8,false);
        return Exit::executed;
    }
    // Fetch all operands before touching guest state. Unsupported opcodes
    // return without fetching speculative operands or mutating the machine.
    unsigned size=1, cycles=2;
    const auto data=data_instruction(op);
    const auto rmw=rmw_instruction(op);
    const auto test_bytes=test_size(op);
    if(data.op!=DataOp::none) size=data_size(data.mode);
    else if(rmw.op!=RmwOp::none) size=rmw.size;
    else if(test_bytes) size=test_bytes;
    else switch(op) {
    case 0x03: case 0x13: case 0x23:
    case 0x53: case 0x43: case 0x44:
    case 0x07: case 0x17: case 0x27: case 0x37: case 0x47: case 0x57: case 0x67: case 0x77:
    case 0x87: case 0x97: case 0xA7: case 0xB7: case 0xC7: case 0xD7: case 0xE7: case 0xF7:
    case 0x80: case 0x10: case 0x30: case 0x50: case 0x70: case 0x90: case 0xB0: case 0xD0: case 0xF0:
        size=2; break;
    case 0x4C: case 0x20: case 0x6C: case 0x7C: size=3; break;
    case 0xEA: case 0xE8: case 0xCA: case 0xC8: case 0x88: case 0xAA: case 0xA8:
    case 0x8A: case 0x98: case 0xBA: case 0x9A: case 0x18: case 0x38: case 0x58:
    case 0x78: case 0xD8: case 0xF8: case 0xB8: case 0xF4: case 0x62: case 0x82:
    case 0x40: case 0xC2: case 0x02: case 0x22: case 0x42: case 0x60: case 0x54: case 0xD4: break;
    case 0x08: case 0x28: case 0x48: case 0x68: case 0x5A: case 0x7A: case 0xDA: case 0xFA: break;
    default: return Exit::unsupported;
    }
    const std::uint8_t lo=size>1 ? bus.read(s,static_cast<std::uint16_t>(s.pc+1)) : 0;
    const std::uint16_t word=size>2 ? lo | (bus.read(s,static_cast<std::uint16_t>(s.pc+2)) << 8) : lo;
    const std::uint8_t last=size>3 ? bus.read(s,static_cast<std::uint16_t>(s.pc+3)):0;
    std::uint16_t next=static_cast<std::uint16_t>(s.pc+size);
    if(data.op!=DataOp::none) execute_data(bus,s,data,lo,word,cycles);
    else if(rmw.op!=RmwOp::none) execute_rmw(bus,s,rmw,lo,word,cycles);
    else if(test_bytes) execute_test(bus,s,op,lo,word,last,next,cycles);
    else switch(op) {
    case 0x03: case 0x13: case 0x23:
        cycles=bus.write_vdc(s,op==3 ? 0:op==0x13 ? 2:3,lo); break;
    case 0x07: case 0x17: case 0x27: case 0x37: case 0x47: case 0x57: case 0x67: case 0x77:
    case 0x87: case 0x97: case 0xA7: case 0xB7: case 0xC7: case 0xD7: case 0xE7: case 0xF7: {
        const auto address=static_cast<std::uint16_t>(0x2000|lo);
        const auto value=bus.read(s,address);
        const auto mask=1U << ((op >> 4) & 7);
        bus.write(s,address,static_cast<std::uint8_t>(op & 0x80 ? value | mask : value & ~mask));
        cycles=7; break;
    }
    case 0x48: push(bus,s,s.a); cycles=3; break;
    case 0xDA: push(bus,s,s.x); cycles=3; break;
    case 0x5A: push(bus,s,s.y); cycles=3; break;
    case 0x08:
        // T is cleared before the status copy; the saved B bit is always set.
        push(bus,s,static_cast<std::uint8_t>((s.p | B) & ~T)); cycles=3; break;
    case 0x68: s.a=pop(bus,s); s.nz(s.a); cycles=4; break;
    case 0xFA: s.x=pop(bus,s); s.nz(s.x); cycles=4; break;
    case 0x7A: s.y=pop(bus,s); s.nz(s.y); cycles=4; break;
    case 0x28:
        // PLP restores T. Do not run the ordinary end-of-instruction clear.
        // B is a stack-status marker, not a persistent restored flag.
        s.p=static_cast<std::uint8_t>(pop(bus,s) & ~B); cycles=4; break;
    case 0xE8: ++s.x; s.nz(s.x); break;
    case 0xCA: --s.x; s.nz(s.x); break;
    case 0xC8: ++s.y; s.nz(s.y); break;
    case 0x88: --s.y; s.nz(s.y); break;
    case 0xAA: s.x=s.a; s.nz(s.x); break;
    case 0xA8: s.y=s.a; s.nz(s.y); break;
    case 0x8A: s.a=s.x; s.nz(s.a); break;
    case 0x98: s.a=s.y; s.nz(s.a); break;
    case 0xBA: s.x=s.sp; s.nz(s.x); break;
    case 0x9A: s.sp=s.x; break;
    case 0x18: s.p &= ~C; break;
    case 0x38: s.p |= C; break;
    case 0x58: s.p &= ~I; break;
    case 0x78: s.p |= I; break;
    case 0xD8: s.p &= ~D; break;
    case 0xF8: s.p |= D; break;
    case 0xB8: s.p &= ~V; break;
    case 0x62: s.a=0; break;
    case 0x82: s.x=0; break;
    case 0xC2: s.y=0; break;
    case 0x02: std::swap(s.x,s.y); cycles=3; break;
    case 0x22: std::swap(s.a,s.x); cycles=3; break;
    case 0x42: std::swap(s.a,s.y); cycles=3; break;
    case 0x53:
        for(unsigned bit=0; bit<8; ++bit) if(lo & (1U << bit)) s.mpr[bit]=s.a;
        if(lo) s.mpr_latch=s.a;
        cycles=5; break;
    case 0x43:
        if(lo) {
            unsigned combined=0;
            for(unsigned bit=0; bit<8; ++bit) if(lo & (1U << bit)) combined |= s.mpr[bit];
            s.mpr_latch=static_cast<std::uint8_t>(combined);
        }
        s.a=s.mpr_latch; cycles=4; break;
    case 0x4C: next=word; cycles=4; break;
    case 0x6C: case 0x7C: {
        const auto pointer=static_cast<std::uint16_t>(word+(op==0x7C ? s.x:0));
        const auto low=bus.read(s,pointer);
        const auto high=bus.read(s,static_cast<std::uint16_t>(pointer+1));
        next=static_cast<std::uint16_t>(low+256*high); cycles=7; break;
    }
    case 0x20:
        push(bus,s,static_cast<std::uint8_t>((next-1) >> 8));
        push(bus,s,static_cast<std::uint8_t>(next-1)); next=word; cycles=7; break;
    case 0x44:
        push(bus,s,static_cast<std::uint8_t>((next-1)>>8));
        push(bus,s,static_cast<std::uint8_t>(next-1));
        next=static_cast<std::uint16_t>(next+static_cast<std::int8_t>(lo)); cycles=8; break;
    case 0x40: {
        s.p=static_cast<std::uint8_t>(pop(bus,s)&~B);
        const auto low=pop(bus,s); const auto high=pop(bus,s);
        next=static_cast<std::uint16_t>(low|(unsigned(high)<<8)); cycles=7; ++s.rti_steps; break;
    }
    case 0x60: { auto low=pop(bus,s); next=static_cast<std::uint16_t>((low | (pop(bus,s) << 8))+1); cycles=7; break; }
    case 0x54: case 0xD4: cycles=3; break;
    case 0xEA: case 0xF4: break;
    default: {
        bool take=op==0x80;
        if(op==0x10) take=!(s.p&N); if(op==0x30) take=s.p&N;
        if(op==0x50) take=!(s.p&V); if(op==0x70) take=s.p&V;
        if(op==0x90) take=!(s.p&C); if(op==0xB0) take=s.p&C;
        if(op==0xD0) take=!(s.p&Z); if(op==0xF0) take=s.p&Z;
        if(take) { next=static_cast<std::uint16_t>(next+static_cast<std::int8_t>(lo)); cycles=4; }
    }
    }
    if(op==0xF4) s.p |= T; else if(op!=0x28 && op!=0x40) s.p &= ~T;
    s.pc=next;
    if(op==0x54 || op==0xD4) bus.retire_speed(s,op==0x54 ? 12:3,false);
    else bus.retire(s,cycles,false);
    return Exit::executed;
}

Exit step(Bus& bus, Cpu& s, std::uint64_t deadline, ExecutionPolicy policy) {
    switch(policy) {
    case ExecutionPolicy::interpreter_only: return interpret_step(bus,s,deadline);
    case ExecutionPolicy::native_only: case ExecutionPolicy::hybrid: break;
    default: throw Fault("invalid execution policy");
    }
    auto result=generated_step(bus,s,deadline);
    if(result==Exit::miss) {
        ++s.guard_misses;
        if(policy==ExecutionPolicy::hybrid) return interpret_step(bus,s,deadline);
    }
    return result;
}
Exit step(Bus& bus, Cpu& s, std::uint64_t deadline, bool allow_interpreter) {
    return step(bus,s,deadline,allow_interpreter ? ExecutionPolicy::hybrid:ExecutionPolicy::native_only);
}
const char* exit_name(Exit status) {
    switch(status) {
    case Exit::executed: return "executed";
    case Exit::miss: return "guard_miss";
    case Exit::unsupported: return "unsupported_instruction";
    case Exit::budget: return "budget";
    }
    return "invalid";
}
} // namespace pce
