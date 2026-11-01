// Authored geometry, source bytes and independently calculated literal clocks.
// Direct-device tests; these do not count guest instruction retirements.
#include "pce/runtime.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <tuple>

namespace {
unsigned checks=0;
void require(bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);}
template<class F>void refuses(F operation) {
    bool failed=false;try{operation();}catch(const pce::Fault&){failed=true;}
    require(failed,"Expected unsupported timing or overflowing deadline refusal");
}
constexpr auto distance=pce::CdTimingProfile::gear_distance;
constexpr auto fixed=pce::CdTimingProfile::fixed;
struct Vector {unsigned from,to;std::uint64_t ticks,busy;};
// Independent decimal/rational expectations at all branch thresholds, both
// ends of the calibrated disc and both directions across a geometry boundary.
constexpr std::array<Vector,18> vectors{{
    {0,0,3221590,3221590},{0,1,3221590,3221590},
    {0,2,4639090,4639090},{0,4,4639090,4639090},
    {0,5,7860681,3049772},{0,809,7860681,3049772},
    {0,810,9278181,4467272},{0,1609,9278181,4467272},
    {0,1610,9278181,4467272},{0,6449,11447386,6636477},
    {0,6450,17181818,12370909},{0,12572,18298636,13487727},
    {12572,12573,3221590,3221590},{12573,12572,3221590,3221590},
    {0,333012,53865000,49054091},{333012,0,53865000,49054091},
    {330669,333012,11146704,6335795},{333012,330669,11146704,6335795}
}};
struct Media final:pce::SectorProvider {
    pce::CdToc geometry;
    unsigned reads=0;
    bool fail=false,gap=false;
    Media(){geometry.track_count=1;geometry.leadout_lba=400000;geometry.tracks[0]={0,4};}
    const pce::CdToc& toc()const override{return geometry;}
    pce::ProgramTrackLookup program_track(std::uint32_t lba)const override {
        return gap && lba==77 ? pce::ProgramTrackLookup{true,{}}:pce::ProgramTrackLookup{true,0};
    }
    pce::Sector read(std::uint32_t lba)override {
        ++reads;
        if(fail)throw pce::SectorReadError(pce::SectorReadReason::media_data_error,lba,"authored media fault");
        pce::Sector result{};for(unsigned i=0;i<result.size();++i)result[i]=std::uint8_t(lba+i);return result;
    }
    bool audio_playable(std::uint32_t lba)const override{return lba<geometry.leadout_lba;}
    pce::AudioSector read_audio(std::uint32_t)override {
        pce::AudioSector result{};for(unsigned i=0;i<588;++i){result[i*2]=1000;result[i*2+1]=-1000;}return result;
    }
};
pce::CdControl setup(const std::shared_ptr<Media>& media,pce::CdTimingProfile profile=distance) {
    pce::CdControl cd;cd.enabled=cd.scsi.enabled=cd.audio_enabled=true;
    cd.timing_profile=profile;cd.set_sector_provider(media);return cd;
}
void command(pce::CdControl& cd,unsigned op,unsigned mode=0,unsigned lba=0) {
    cd.scsi.command.fill(0);cd.scsi.command[0]=std::uint8_t(op);cd.scsi.command[1]=std::uint8_t(mode);
    cd.scsi.command[3]=std::uint8_t(lba>>16);cd.scsi.command[4]=std::uint8_t(lba>>8);cd.scsi.command[5]=std::uint8_t(lba);
    cd.audio_command();
}
void read(pce::CdControl& cd,unsigned lba,unsigned count=1) {
    // Public port handshake, with a bounded event wait for every genuine REQ.
    // This supervisor seeds only initial command selection, not read deadlines.
    cd.scsi.phase=3;cd.scsi.signals=0xD0;cd.scsi.event=0;cd.scsi.deadline=0;
    cd.scsi.command_size=0;cd.ack=false;
    const std::array<unsigned,6> cdb{8,(lba>>16)&31,(lba>>8)&255,lba&255,count,0};
    for(auto byte:cdb) {
        require((cd.scsi.signals&0x40)!=0,"Missing command REQ");
        cd.transport_write(1,std::uint8_t(byte));cd.transport_write(2,0x80);cd.transport_write(2,0);
        if(cd.scsi.command_size)cd.advance_to(cd.scsi.deadline);
    }
}
auto timeline(const pce::CdControl& cd) {
    const auto& a=cd.audio;const auto& s=cd.scsi;
    return std::make_tuple(a.state,a.start_lba,a.current_lba,a.stop_lba,a.seek_start_lba,
        a.deadline,a.seek_deadline,a.sector_deadline,a.playback_deadline,a.commands,
        a.source_cursor.frame,a.source_cursor.active,a.sample_raw,a.sample_latch,
        s.current_lba,s.load_deadline,s.load_lba,s.load_remaining,s.read_active,
        cd.read_commands,cd.read_errors);
}
void pure_vectors() {
    for(const auto& v:vectors) {
        require(pce::cd_seek_ticks(distance,v.from,v.to)==v.ticks,"Independent distance seek literal differs");
        require(pce::cd_seek_ticks(fixed,v.from,v.to)==3221590,"Fixed seek default changed");
    }
    // Two-sector gaps isolate the destination rotation period in every zone.
    constexpr std::array<unsigned,14> starts{0,12573,30245,49524,70409,92901,116999,142704,170015,198933,229457,261588,295325,330669};
    constexpr std::array<unsigned,14> milliseconds{216,223,230,236,243,250,256,263,270,276,283,290,296,303};
    for(unsigned i=0;i<starts.size();++i) {
        const auto expected=std::uint64_t(milliseconds[i])*21477273/1000;
        require(pce::cd_seek_ticks(distance,starts[i],starts[i]+2)==expected,"Zone rotation lookup differs");
        require(pce::cd_seek_ticks(distance,starts[i]+2,starts[i])==expected,"Reverse same-zone rotation differs");
    }
    require(pce::cd_seek_ticks(distance,12571,12573)==4789431,"Cross-zone destination rotation differs");
    require(pce::cd_seek_ticks(distance,12573,12571)==4639090,"Reverse destination rotation differs");
    require(pce::cd_seek_ticks(distance,333012,333012)==3221590,"Inclusive calibrated endpoint refused");
    for(unsigned invalid:{333013u,std::numeric_limits<unsigned>::max()}) {
        refuses([&]{pce::cd_seek_ticks(distance,invalid,0);});
        refuses([&]{pce::cd_seek_ticks(distance,0,invalid);});
        require(pce::cd_seek_ticks(fixed,invalid,invalid)==3221590,"Fixed profile inherited distance bounds");
    }
    refuses([]{pce::cd_seek_ticks(static_cast<pce::CdTimingProfile>(255),0,0);});
}
void audio_vectors() {
    for(const auto& v:vectors)for(auto profile:{fixed,distance})for(unsigned mode:{0u,1u,255u}) {
        auto cd=setup(std::make_shared<Media>(),profile);cd.scsi.master_ticks=1000;cd.scsi.current_lba=v.from;
        command(cd,0xD8,mode,v.to);
        const auto busy=profile==fixed?3221590:v.busy;
        const auto total=profile==fixed?3221590:v.ticks;
        const auto playback=mode && total>busy ? 1000+total:0;
        require(cd.audio.seek_start_lba==v.from && cd.scsi.current_lba==v.to && cd.audio.current_lba==v.to,"D8 retained/supplied head differs");
        require(cd.audio.seek_deadline==1000+busy && cd.audio.playback_deadline==playback && cd.scsi.phase==8,"D8 split/unsplit admission differs");
        cd.advance_to(1000+busy-1);require(cd.scsi.phase==8,"D8 completed seek early");
        cd.advance_to(1000+busy);require(cd.scsi.phase==7 && cd.scsi.data==0 && cd.audio.seek_deadline==0,"D8 seek did not complete with GOOD");
        if(!mode)require(!cd.audio.playback_deadline && !cd.audio.sector_deadline && cd.audio.state==2,"Paused D8 started playback");
        else if(playback) {
            require(!cd.audio.sector_deadline && cd.audio.playback_deadline==playback,"Split seek started sectors before playback delay");
            cd.advance_to(playback-1);require(!cd.audio.sector_deadline,"Playback delay ended early");
            cd.advance_to(playback);require(cd.audio.sector_deadline==playback+286363 && !cd.audio.playback_deadline,"Playback delay failed to start sector clock");
        } else require(cd.audio.sector_deadline==1000+total+286363,"Short unsplit seek added a playback delay");
    }
}
void read_vectors() {
    for(const auto& v:vectors)for(auto profile:{fixed,distance}) {
        auto media=std::make_shared<Media>();auto cd=setup(media,profile);cd.scsi.current_lba=v.from;
        read(cd,v.to,2);const auto at=cd.scsi.master_ticks;
        const auto delay=(profile==fixed?3221590:v.ticks)+286363;
        require(cd.scsi.load_deadline==at+delay && cd.audio.state==1 && cd.scsi.current_lba==v.from,"READ seek, sector period or retained head differs");
        cd.advance_to(at+delay-1);require(!media->reads && !cd.sectors_read,"READ loaded before actual deadline");
        cd.advance_to(at+delay);require(media->reads==1 && cd.sectors_read==1 && cd.scsi.current_lba==v.to+1,"Successful READ head advance differs");
        require(cd.scsi.load_deadline==at+delay+286363,"Later sector cadence inherited seek model");
        cd.advance_to(at+delay+286363);require(cd.read_retries==1 && media->reads==1 && cd.scsi.current_lba==v.to+1,"Occupied response retried/moved head incorrectly");
        require(cd.scsi.load_deadline==at+delay+286363+6228408,"Occupied retry latency changed");
    }
    auto media=std::make_shared<Media>();media->fail=true;auto cd=setup(media);cd.scsi.current_lba=12573;
    read(cd,12571);const auto deadline=cd.scsi.load_deadline;cd.advance_to(deadline);
    require(cd.scsi.current_lba==12573 && cd.sectors_read==0 && cd.read_errors==1 && cd.pending_sense.asc==0x11,"Failed load moved head or lost sense");
}
void interruption_and_resume() {
    auto media=std::make_shared<Media>();auto cd=setup(media);
    command(cd,0xD8,1,333012);
    read(cd,333010);const auto at=cd.scsi.master_ticks;
    require(cd.scsi.load_deadline==at+6793976 && cd.scsi.current_lba==333012,"READ during seek did not use immediate target head");
    require(!cd.audio.seek_deadline && !cd.audio.playback_deadline && !cd.audio.sector_deadline && cd.audio.state==1,"READ did not cancel every audio deadline");
    cd.advance_to(cd.scsi.load_deadline);require(cd.scsi.current_lba==333011,"READ-during-seek loaded wrong head");
    for(bool after_seek:{false,true}) {
        auto c=setup(std::make_shared<Media>());command(c,0xD8,0,333012);
        if(after_seek)c.advance_to(50000000);
        command(c,0xD9,3,333012);
        const std::uint64_t ready=after_seek?54810909:53865000;
        require(c.audio.playback_deadline==ready,"Paused D9 resume did not follow remaining seek");
        c.advance_to(ready-1);require(!c.audio.sector_deadline,"D9 resumed early");
        c.advance_to(ready);require(c.audio.sector_deadline==ready+286363,"D9 failed to resume after delay");
    }
    for(unsigned stop:{0xDAu,0xD9u}) {
        auto c=setup(std::make_shared<Media>());command(c,0xD8,1,333012);command(c,stop,0);
        require(c.audio.seek_deadline==49054091 && !c.audio.playback_deadline && !c.audio.sector_deadline,"Pause/stop changed retained physical seek");
        require(c.audio.state==(stop==0xDA?2u:3u),"Pause/stop state differs");
        c.advance_to(49054091);require(!c.audio.sector_deadline && c.scsi.phase==7,"Retained seek restart after pause/stop");
    }
    auto reset=setup(std::make_shared<Media>());command(reset,0xD8,1,333012);reset.transport_write(4,2);
    require(!reset.audio.deadline && !reset.audio.seek_deadline && !reset.audio.playback_deadline && reset.timing_profile==distance,"Bus reset did not cancel seek or changed selected timing");
    auto gapmedia=std::make_shared<Media>();gapmedia->gap=true;auto gap=setup(gapmedia);command(gap,0xD8,1,333012);
    const auto before=timeline(gap);command(gap,0xD8,1,77);require(timeline(gap)==before,"Ignored gap D8 changed distance timeline");
}
void source_gates() {
    // The canonical DAC and both existing presentation paths must wait for
    // both phases. Drain incrementally so this is not a queue-overflow test.
    for(unsigned output:{0u,1u,2u}) {
        auto bus=std::make_unique<pce::Bus>();pce::Cpu cpu;bus->enable_cd_transport();bus->cd.audio_enabled=true;
        auto media=std::make_shared<Media>();media->geometry.tracks[0].type=0;bus->cd.set_sector_provider(media);
        bus->cd.timing_profile=distance;
        if(output)bus->enable_audio_output(pce::AudioProfile::raw,44100,output==1?pce::AudioTiming::gear:pce::AudioTiming::legacy);
        command(bus->cd,0xD8,1,333012);
        const auto clock=[&](std::uint64_t target) {
            while(cpu.ticks<target) {
                cpu.ticks=std::min(target,cpu.ticks+286363);bus->sync(cpu);
                if(output)bus->pcm.drain();
            }
        };
        clock(49054091);require(bus->cd.audio.sample_raw==std::array<std::int16_t,2>{0,0} && !bus->cd.audio.sector_deadline,"Seek completion emitted audio before playback delay");
        clock(53864999);require(bus->cd.audio.sample_raw==std::array<std::int16_t,2>{0,0},"Pending playback delay leaked canonical samples");
        // First sample edge strictly after total seek completion.
        const auto ordinal=std::uint64_t(53865000)*44100/21477273+1;
        const auto edge=(ordinal*21477273+44099)/44100;
        clock(edge);require(bus->cd.audio.sample_raw==std::array<std::int16_t,2>{1000,-1000},"Ready distance seek did not emit first authored sample");
        if(output)require(bus->pcm.discarded_frames==0 && bus->pcm.cdda_nonzero>0,"Audio presentation path lost or omitted new source samples");
    }
}
void refusals() {
    for(unsigned head:{0u,333013u}) {
        auto cd=setup(std::make_shared<Media>());cd.scsi.current_lba=head;
        cd.audio.state=0;cd.audio.current_lba=17;cd.audio.seek_deadline=100000000;cd.audio.playback_deadline=200000000;cd.audio.reschedule();
        const auto before=timeline(cd);
        refuses([&]{command(cd,0xD8,1,head?0:333013);});require(timeline(cd)==before,"Unsupported seek changed active audio/head");
        refuses([&]{read(cd,head?0:333013);});require(timeline(cd)==before,"Unsupported READ changed active audio/head");
    }
    for(bool paused:{false,true}) {
        auto cd=setup(std::make_shared<Media>());cd.scsi.master_ticks=std::numeric_limits<std::uint64_t>::max()-50000000;
        cd.audio.state=0;cd.audio.current_lba=19;cd.audio.commands=12;
        const auto before=timeline(cd);
        // Paused long seek only needs the reduced physical deadline, which
        // fits at this epoch. The playing path must also fit total playback.
        if(paused) {
            command(cd,0xD8,0,333012);
            require(cd.audio.seek_deadline==cd.scsi.master_ticks+49054091 && !cd.audio.playback_deadline,"Paused seek incorrectly required unused playback deadline");
        } else {
            refuses([&]{command(cd,0xD8,1,333012);});
            require(timeline(cd)==before,"Overflowing D8 changed old timeline");
        }
    }
    auto read_overflow=setup(std::make_shared<Media>());read_overflow.scsi.master_ticks=std::numeric_limits<std::uint64_t>::max()-20000;
    read_overflow.audio.state=0;read_overflow.audio.current_lba=19;const auto old=timeline(read_overflow);
    refuses([&]{read(read_overflow,0);});require(timeline(read_overflow)==old,"Overflowing READ cancelled prior audio/head");
    auto resume=setup(std::make_shared<Media>());resume.scsi.master_ticks=std::numeric_limits<std::uint64_t>::max()-100;
    resume.audio.state=2;resume.audio.current_lba=19;const auto oldresume=timeline(resume);
    refuses([&]{command(resume,0xD9,3,19);});require(timeline(resume)==oldresume,"Overflowing resume changed prior end/state");
    auto fixed_cd=setup(std::make_shared<Media>(),fixed);command(fixed_cd,0xD8,1,333013);
    require(fixed_cd.audio.seek_deadline==3221590 && fixed_cd.scsi.current_lba==333013,"Fixed D8 incorrectly acquired calibrated limit");
}
}
int main() {
    try {pure_vectors();audio_vectors();read_vectors();interruption_and_resume();source_gates();refusals();
        std::cout<<checks<<" authored CD timing checks passed; zero guest retirements\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
