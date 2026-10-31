#include "pce/runtime.hpp"
#include "pce/cdda.hpp"
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
std::uint64_t checks=0;
void require(bool condition) {
    ++checks;if(!condition) throw std::runtime_error("CD audio expectation failed at "+std::to_string(checks));
}
template<class F> void fault(F&& fn) {
    bool caught=false;try {fn();}catch(const pce::Fault&){caught=true;}require(caught);
}
pce::CdControl prepare() {
    pce::CdControl cd;cd.enabled=cd.scsi.enabled=cd.audio_enabled=true;
    pce::CdToc toc;toc.track_count=3;toc.leadout_lba=450;
    toc.tracks[0]={0,0};toc.tracks[1]={100,4};toc.tracks[2]={200,0};
    cd.set_toc(toc);return cd;
}
void command(pce::CdControl& cd,unsigned op,unsigned mode=0,unsigned lba=0,unsigned address_mode=0) {
    cd.scsi.command.fill(0);cd.scsi.command[0]=static_cast<std::uint8_t>(op);
    cd.scsi.command[1]=static_cast<std::uint8_t>(mode);
    cd.scsi.command[3]=static_cast<std::uint8_t>(lba>>16);
    cd.scsi.command[4]=static_cast<std::uint8_t>(lba>>8);
    cd.scsi.command[5]=static_cast<std::uint8_t>(lba);
    cd.scsi.command[9]=static_cast<std::uint8_t>(address_mode);
    cd.scsi.phase=3;cd.scsi.signals=0xD0;cd.scsi.event=0;cd.scsi.deadline=0;
    cd.scsi.response_index=cd.scsi.response_size=0;
}
void start_and_positions() {
    for(unsigned mode=0;mode<256;++mode) {
        auto cd=prepare();cd.scsi.current_lba=110;
        command(cd,0xD8,mode,200);cd.audio_command();
        require(cd.audio.state==(mode==0 ? 2u:0u) && cd.audio.start_lba==200);
        require(cd.audio.seek_start_lba==110 && cd.scsi.phase==8 && cd.scsi.signals==0x80);
        require(cd.audio.deadline==3221590 && cd.audio.seek_deadline==3221590);
        cd.advance_to(3221589);require(cd.scsi.phase==8);
        cd.advance_to(3221590);require(cd.scsi.phase==7 && cd.scsi.data==0 && !cd.audio.seek_deadline);
        require(bool(cd.audio.sector_deadline)==(mode!=0));
    }
    auto cd=prepare();cd.scsi.current_lba=110;
    command(cd,0xD8,1,200);cd.audio_command();
    command(cd,0xDD);cd.audio_command();cd.advance_to(3000);
    constexpr std::array<unsigned,10> seeking={2,0x41,2,1,0,0,0x10,0,3,0x35};
    for(unsigned i=0;i<10;++i) require(cd.scsi.response[i]==seeking[i]);
    cd.advance_to(3221590);
    command(cd,0xDD);cd.audio_command();cd.advance_to(cd.scsi.master_ticks+3000);
    constexpr std::array<unsigned,10> playing={0,1,3,1,0,0,0,0,4,0x50};
    for(unsigned i=0;i<10;++i) require(cd.scsi.response[i]==playing[i]);
    // Three addressing forms select the same authored track start.
    for(unsigned form:{0,64,128}) {
        auto c=prepare();command(c,0xD8,0,200,form);
        if(form==64) {c.scsi.command[2]=0;c.scsi.command[3]=4;c.scsi.command[4]=0x50;}
        if(form==128) c.scsi.command[2]=3;
        c.audio_command();require(c.audio.start_lba==200 && c.audio.state==2);
    }
}
void playback() {
    auto cd=prepare();command(cd,0xD8,1,0);cd.audio_command();cd.advance_to(3221590);
    cd.advance_to(3221590+21477273);
    require(cd.audio.current_lba==75 && cd.audio.sectors_played==75);
    require(cd.audio.sector_fraction==48);
    command(cd,0xDA);cd.audio_command();
    require(cd.audio.state==2 && cd.audio.deadline==0 && cd.scsi.data==0);
    cd.advance_to(cd.scsi.master_ticks+21477273);require(cd.audio.current_lba==75);
    // Resume delay is real timeline state; playback cannot advance through it.
    command(cd,0xD9,3,76);cd.audio_command();
    const auto resume=cd.audio.playback_deadline;
    require(resume==cd.scsi.master_ticks+4810909 && cd.scsi.phase==7);
    cd.advance_to(resume-1);require(cd.audio.current_lba==75 && !cd.audio.sector_deadline);
    cd.advance_to(resume);require(cd.audio.sector_deadline>resume);
    cd.advance_to(cd.audio.sector_deadline);require(cd.audio.current_lba==76 && cd.audio.state==0);
    cd.advance_to(cd.audio.sector_deadline);require(cd.audio.current_lba==77 && cd.audio.state==3);
    // IRQ completion uses the standard SCSI status/IRQ line, not an invented audio IRQ bit.
    auto irq=prepare();command(irq,0xD8,1,10);irq.audio_command();irq.advance_to(3221590);
    command(irq,0xD9,2,10);irq.audio_command();require(irq.scsi.phase==8);
    irq.advance_to(irq.audio.sector_deadline);
    require(irq.audio.state==3 && irq.scsi.phase==7 && irq.scsi.data==0 && (irq.interrupt_active&0x20));
    auto loop=prepare();command(loop,0xD8,1,10);loop.audio_command();loop.advance_to(3221590);
    command(loop,0xD9,1,10);loop.audio_command();
    for(unsigned i=0;i<5;++i) {loop.advance_to(loop.audio.sector_deadline);require(loop.audio.current_lba==10 && loop.audio.state==0 && loop.scsi.phase==8);}
    command(loop,0xD9,0,0);loop.audio_command();require(loop.audio.state==3 && loop.audio.deadline==0);
}
void fader_and_failures() {
    for(unsigned value=0;value<256;++value) for(bool adpcm:{false,true}) {
        auto cd=prepare();cd.scsi.master_ticks=100;cd.write_fader(static_cast<std::uint8_t>(value));
        require(cd.audio.fader==value && cd.audio.fade_start==100);
        require(cd.audio.fade_duration==((value&4) ? 53693182u:139602274u));
        require(cd.fader_gain(adpcm)==1.0);
        const bool fades=(value&8) && bool(value&2)==adpcm;
        cd.scsi.master_ticks=100+cd.audio.fade_duration;
        require(cd.fader_gain(adpcm)==(fades ? 0.0:1.0));
        cd.scsi.master_ticks=100+cd.audio.fade_duration/2;
        require(std::abs(cd.fader_gain(adpcm)-(fades ? 0.5:1.0))<0.00000002);
    }
    auto cd=prepare();command(cd,0xD8,1,450);cd.audio_command();require(cd.scsi.data==2 && cd.audio.deadline==0);
    command(cd,0xD8,1,0,192);fault([&]{cd.audio_command();});
    command(cd,0xD8,1,0,128);cd.scsi.command[2]=0xFA;fault([&]{cd.audio_command();});
    command(cd,0xD8,1,0,64);cd.scsi.command[3]=0x60;fault([&]{cd.audio_command();});
    command(cd,0xD8,1,0,64);cd.scsi.command[3]=1;cd.scsi.command[4]=0x74;fault([&]{cd.audio_command();});
    command(cd,0xD9,4,0);fault([&]{cd.audio_command();});
    command(cd,0xD8,1,0);cd.scsi.master_ticks=std::numeric_limits<std::uint64_t>::max()-1;fault([&]{cd.audio_command();});
    pce::CdControl missing;missing.enabled=missing.scsi.enabled=true;command(missing,0xD8,1,0);missing.audio_command();require(missing.scsi.data==2);
}
void reference_unknown_response() {
    for(unsigned opcode=0;opcode<256;++opcode) {
        if(opcode==0 || opcode==3 || opcode==8 || opcode==0xD8 || opcode==0xD9 || opcode==0xDA || opcode==0xDD || opcode==0xDE)continue;
        for(bool selected:{false,true}) {
            auto cd=prepare();cd.unknown_policy=selected ? pce::CdUnknownPolicy::gear_good:pce::CdUnknownPolicy::fault;
            cd.audio.state=0;cd.audio.seek_deadline=9999999;cd.audio.reschedule();
            cd.transport_write(0,0);cd.advance_to(75000);
            cd.transport_write(1,static_cast<std::uint8_t>(opcode));cd.transport_write(2,0xE0);
            require(cd.scsi.command_size==1 && cd.scsi.signals==0x92 && !cd.unknown_commands);
            bool caught=false;try{cd.transport_write(2,0x60);}catch(const pce::Fault&){caught=true;}
            require(caught==!selected && cd.scsi.last_command_size==1 && cd.scsi.last_command[0]==opcode);
            require(cd.audio.state==0 && cd.audio.seek_deadline==9999999 && !cd.audio.commands);
            if(!selected){require(cd.unknown_commands==0 && cd.scsi.phase==3 && cd.scsi.command_size==1);continue;}
            require(cd.unknown_commands==1 && !cd.scsi.command_size && cd.scsi.phase==7 && cd.scsi.signals==0xD8 &&
                    cd.scsi.data==0 && cd.scsi.response_size==1 && cd.interrupt_active==0x20);
            cd.transport_write(2,0x60);require(cd.unknown_commands==1 && cd.scsi.signals==0xD8);
            cd.transport_write(2,0xE0);cd.transport_write(2,0x60);cd.advance_to(76500);
            require(cd.scsi.phase==6 && cd.scsi.signals==0xF8 && cd.scsi.data==0);
            cd.transport_write(2,0xE0);cd.transport_write(2,0x60);cd.advance_to(78000);
            require(cd.scsi.phase==0 && cd.scsi.signals==0 && cd.unknown_commands==1 && cd.audio.state==0);
            // A new selection accepts the next real CDB; the unknown byte
            // cannot remain at the start of its command buffer.
            cd.transport_write(0,0);cd.advance_to(153000);
            for(unsigned n=0;n<6;++n){
                cd.transport_write(1,0);cd.transport_write(2,0x80);cd.transport_write(2,0);
                if(n<5)cd.advance_to(cd.scsi.master_ticks+3000);
            }
            require(cd.scsi.last_command_size==6 && cd.scsi.last_command[0]==0 && cd.scsi.command_size==0 && cd.unknown_commands==1);
        }
    }
    // REQUEST SENSE is a genuine known command in either unknown-opcode
    // policy. Its fixed response and completion do not count as a quirk use.
    constexpr std::array<unsigned,18> no_error={0x70,0,0,0,0,0,0,0x0A,0,0,0,0,0,0,0,0,0,0};
    for(bool selected:{false,true}){
        auto cd=prepare();cd.unknown_policy=selected ? pce::CdUnknownPolicy::gear_good:pce::CdUnknownPolicy::fault;cd.transport_write(0,0);cd.advance_to(75000);
        for(unsigned n=0;n<6;++n){
            cd.transport_write(1,n==0?3:0);cd.transport_write(2,0x80);
            cd.transport_write(2,0);
            require(cd.sense_commands==unsigned(n==5));if(n<5)cd.advance_to(cd.scsi.master_ticks+3000);
        }
        require(cd.scsi.last_command_size==6 && cd.scsi.last_command[0]==3 && !cd.unknown_commands);
        cd.transport_write(2,0x60);
        require(cd.scsi.response_size==18 && cd.irq2() && (cd.interrupt_active&0x40));
        for(unsigned i=0;i<no_error.size();++i){
            require(cd.transport_read(0)==0xC8 && cd.transport_read(1)==no_error[i]);
            cd.transport_write(2,0xE0);require(!cd.irq2());cd.transport_write(2,0x60);
            cd.advance_to(cd.scsi.master_ticks+(i+1==no_error.size()?3000:900));
        }
        require(cd.data_bytes_acked==18 && cd.transport_read(0)==0xD8 && cd.transport_read(1)==0 && cd.irq2());
        cd.transport_write(2,0xE0);cd.transport_write(2,0x60);cd.advance_to(cd.scsi.master_ticks+1500);
        require(cd.transport_read(0)==0xF8 && cd.transport_read(1)==0);
        cd.transport_write(2,0xE0);cd.transport_write(2,0x60);cd.advance_to(cd.scsi.master_ticks+1500);
        require(cd.transport_read(0)==0 && !cd.irq2() && !cd.unknown_commands && !cd.sense_errors);
    }
}
}
int main() {
    try {start_and_positions();playback();fader_and_failures();reference_unknown_response();std::cout<<"CD audio checks: "<<checks<<"\n";return 0;}
    catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
