// Authored direct-device complete-machine checkpoint cuts. No guest opcodes,
// firmware, images or retail state. Fresh provider instances own each branch.
#include "pce/checkpoint.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <array>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
unsigned checks=0,cases=0;
constexpr auto fixed=pce::CdTimingProfile::fixed,distance=pce::CdTimingProfile::gear_distance;
void require(bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);}
template<class F>void refuses(F operation,const char* why) {
    bool caught=false;try{operation();}catch(const std::exception&){caught=true;}
    require(caught,why);
}
std::uint8_t pattern(unsigned lba,unsigned byte){return std::uint8_t(lba*29+byte*11+0x73);}
struct Media final:pce::SectorProvider {
    pce::CdToc geometry;
    std::vector<unsigned> data_reads,audio_reads;
    Media(){geometry.track_count=2;geometry.tracks[0]={0,4};geometry.tracks[1]={5000,0};geometry.leadout_lba=7000;geometry.image_sha256=std::string(64,'c');}
    const pce::CdToc& toc()const override{return geometry;}
    pce::ProgramTrackLookup program_track(std::uint32_t lba)const override {
        if(lba>=7000 || lba==77)return {true,{}};
        return {true,lba<5000?0u:1u};
    }
    pce::Sector read(std::uint32_t lba)override {
        require(lba<5000,"Unexpected authored data address");data_reads.push_back(lba);
        pce::Sector result{};for(unsigned i=0;i<result.size();++i)result[i]=pattern(lba,i);return result;
    }
    bool audio_playable(std::uint32_t lba)const override{return lba>=5000 && lba<7000;}
    pce::AudioSector read_audio(std::uint32_t lba)override {
        require(audio_playable(lba),"Unexpected authored audio address");audio_reads.push_back(lba);
        pce::AudioSector result{};for(unsigned i=0;i<588;++i){const auto v=std::int16_t(1000+(lba-5000)*3+i);result[i*2]=v;result[i*2+1]=-v;}return result;
    }
};
struct Machine {
    pce::Bus bus;pce::Cpu cpu;std::shared_ptr<Media> media=std::make_shared<Media>();
    pce::CdTimingProfile profile;bool output;
    Machine(pce::CdTimingProfile timing,unsigned divisor,bool pcm):profile(timing),output(pcm) {
        cpu.clock_divisor=divisor;cpu.mpr[1]=0xF8;bus.kind[0xF8]=pce::BankKind::ram;
        (*bus.bytes)[0x1F0000]=0xA7;bus.enable_cd_transport();bus.cd.audio_enabled=true;
        bus.cd.timing_profile=timing;bus.cd.set_sector_provider(media);bus.enable_adpcm();
        bus.adpcm.ram[0]=0xC7;
        if(output) {
            bus.enable_audio_output(pce::AudioProfile::filtered,48000,pce::AudioTiming::gear);
            bus.psg.main_volume=0xFF;auto& ch=bus.psg.channels[0];ch.control=0x9F;ch.balance=0xFF;ch.frequency=53;
            for(unsigned i=0;i<32;++i)ch.waveform[i]=std::uint8_t((i*7+3)&31);
        }
    }
    void clock(std::uint64_t target) {
        require(target>=cpu.ticks,"Authored clock regression");
        while(cpu.ticks<target) {
            cpu.ticks=std::min(target,cpu.ticks+286363);bus.sync(cpu);
            // Preserve the final pending queue for checkpoint qualification.
            if(output && cpu.ticks<target)bus.pcm.drain();
        }
    }
    void audio(unsigned op,unsigned mode=0,unsigned lba=0) {
        auto& s=bus.cd.scsi;s.command.fill(0);s.command[0]=std::uint8_t(op);s.command[1]=std::uint8_t(mode);
        s.command[3]=std::uint8_t(lba>>16);s.command[4]=std::uint8_t(lba>>8);s.command[5]=std::uint8_t(lba);
        bus.cd.audio_command();bus.sync(cpu);
    }
    void ack(){bus.cd.transport_write(2,0xE0);bus.cd.transport_write(2,0x60);}
    void read() {
        auto& cd=bus.cd;cd.transport_write(0,0);clock(75000);
        const unsigned cdb[]{8,0,3,0xE8,2,0}; // Authored data LBA1000, two sectors.
        for(unsigned i=0;i<6;++i) {
            require(cd.transport_read(0)==0xD0,"Actual READ command REQ missing");cd.transport_write(1,std::uint8_t(cdb[i]));ack();
            if(i<5)clock(cpu.ticks+3000);
        }
        bus.sync(cpu);
        require(cpu.ticks==90000 && cd.scsi.load_deadline==90000+(profile==fixed?3507953:9564544),"Literal initial READ deadline differs");
    }
    void pending_adpcm() {
        bus.adpcm.write(10,0x5A,&bus.cd);(void)bus.adpcm.read(10);
        require(bus.adpcm.read_deadline>cpu.ticks && bus.adpcm.write_deadline>cpu.ticks,"Cut does not contain pending ADPCM I/O");
    }
};
enum class Cut {read_before,read_after,read_retry,seek_before,seek_after,ready_before,ready_after,paused_before,paused_after,resume,pause,stop,reset};
constexpr std::array<Cut,13> cuts{Cut::read_before,Cut::read_after,Cut::read_retry,Cut::seek_before,Cut::seek_after,Cut::ready_before,Cut::ready_after,Cut::paused_before,Cut::paused_after,Cut::resume,Cut::pause,Cut::stop,Cut::reset};
std::uint64_t busy(const Machine& m){return m.profile==fixed?3221590:12370909;}
std::uint64_t total(const Machine& m){return m.profile==fixed?3221590:17181818;}
bool reading(Cut cut){return cut==Cut::read_before || cut==Cut::read_after || cut==Cut::read_retry;}
void prepare(Machine& m,Cut cut) {
    if(reading(cut)) {
        m.read();const auto load=m.bus.cd.scsi.load_deadline;
        m.clock(cut==Cut::read_before?load-1:cut==Cut::read_after?load:load+286363);
        require(m.bus.cd.sectors_read==(cut==Cut::read_before?0u:1u),"READ cut first-load count differs");
        require(m.bus.cd.read_retries==(cut==Cut::read_retry?1u:0u),"READ cut retry count differs");
    } else {
        const bool paused=cut==Cut::paused_before || cut==Cut::paused_after || cut==Cut::resume;
        m.audio(0xD8,paused?0:1,6450);
        require(m.bus.cd.scsi.current_lba==6450 && m.bus.cd.audio.seek_start_lba==0,"Audio cut source/head differs");
        switch(cut) {
        case Cut::seek_before:m.clock(busy(m)-1);break;
        case Cut::seek_after:m.clock(busy(m));break;
        case Cut::ready_before:m.clock(total(m)-1);break;
        case Cut::ready_after:m.clock(total(m));break;
        case Cut::paused_before:m.clock(busy(m)-1);break;
        case Cut::paused_after:m.clock(busy(m));break;
        case Cut::resume:
            m.clock(1000);m.audio(0xD9,3,6800);m.clock(busy(m)+1000);
            require(m.bus.cd.audio.playback_deadline==busy(m)+4810909 && !m.bus.cd.audio.seek_deadline,"Paused D9 cut did not retain224ms delay");break;
        case Cut::pause:case Cut::stop:
            m.clock(1000);m.audio(cut==Cut::pause?0xDA:0xD9,0);m.clock(busy(m)-1);
            require(m.bus.cd.audio.seek_deadline==busy(m) && !m.bus.cd.audio.playback_deadline,"Pause/stop failed to retain physical seek");break;
        case Cut::reset:
            m.clock(1000);m.bus.cd.transport_write(4,2);m.clock(2000);
            require(!m.bus.cd.audio.deadline && !m.bus.cd.scsi.load_deadline && m.bus.cd.reset==2,"Reset cut retained scheduled work");break;
        default:throw std::runtime_error("Unrecognized authored cut");
        }
        if(cut==Cut::seek_after && m.profile==distance)
            require(m.bus.cd.audio.seek_deadline==0 && m.bus.cd.audio.playback_deadline==17181818 && !m.bus.cd.audio.sector_deadline,"Seek/playback gap is absent at checkpoint");
    }
    m.pending_adpcm();
    if(m.output)require(m.bus.pcm.queued_frames()>0 && m.bus.pcm.processing_stats().source_frames>0,"PCM cut lacks queue/filter history");
}
std::size_t profile_offset() {
    Machine a(fixed,3,false),b(distance,3,false);const auto x=pce::encode_checkpoint(a.bus,a.cpu),y=pce::encode_checkpoint(b.bus,b.cpu);
    require(x.size()==y.size(),"Timing selector changed checkpoint extent");
    std::size_t offset=0,count=0;
    for(std::size_t i=0;i<x.size();++i)if(x[i]!=y[i]){offset=i;++count;}
    require(count==1 && x[offset]==0 && y[offset]==1,"Profile must be one distinct, typed checkpoint byte");return offset;
}
void equal(Machine& a,Machine& b) {
    require(pce::encode_checkpoint(a.bus,a.cpu)==pce::encode_checkpoint(b.bus,b.cpu),"Complete canonical checkpoint continuation differs");
    require(a.cpu.native_steps==0 && a.cpu.interpreter_steps==0 && b.cpu.native_steps==0 && b.cpu.interpreter_steps==0,"Direct supervisor work was counted as guest retirement");
    if(a.output) {
        require(a.bus.pcm.drain()==b.bus.pcm.drain(),"Restored pending/generated signed PCM differs");
        require(a.bus.pcm.discarded_frames==0 && b.bus.pcm.discarded_frames==0,"Checkpoint suffix overflowed PCM queue");
    }
}
std::unique_ptr<Machine> roundtrip(Machine& a,std::size_t selector) {
    const auto data_reads=a.media->data_reads,audio_reads=a.media->audio_reads;
    const auto saved=pce::encode_checkpoint(a.bus,a.cpu);
    require(saved==pce::encode_checkpoint(a.bus,a.cpu) && a.media->data_reads==data_reads && a.media->audio_reads==audio_reads,"Saving changed machine or accessed media");
    auto b=std::make_unique<Machine>(a.profile,a.cpu.clock_divisor,a.output);
    auto decoded=pce::decode_checkpoint(saved,b->bus);
    require(decoded->bus.cd.provider.get()==b->media.get() && decoded->bus.cd.provider.get()!=a.media.get(),"Decoded source did not bind fresh destination provider");
    require(pce::encode_checkpoint(decoded->bus,decoded->cpu)==saved && b->media->data_reads.empty() && b->media->audio_reads.empty(),"Pure decode accessed media or changed payload");
    pce::restore_checkpoint(b->bus,b->cpu,saved);
    require(b->bus.cd.provider.get()==b->media.get() && b->media.get()!=a.media.get(),"Restore copied original provider ownership");
    require(pce::encode_checkpoint(b->bus,b->cpu)==saved && b->media->data_reads.empty() && b->media->audio_reads.empty(),"Restore accessed media or changed canonical bytes");
    for(unsigned mutation=0;mutation<4;++mutation) {
        auto invalid=saved;
        if(mutation==0)invalid.pop_back();
        if(mutation==1)invalid.resize(12);
        if(mutation==2)invalid[selector]=2;
        if(mutation==3)invalid[selector]=255;
        const auto unchanged=pce::encode_checkpoint(b->bus,b->cpu);
        refuses([&]{pce::restore_checkpoint(b->bus,b->cpu,invalid);},"Malformed enum/truncated checkpoint accepted");
        require(unchanged==pce::encode_checkpoint(b->bus,b->cpu) && b->media->data_reads.empty() && b->media->audio_reads.empty(),"Rejected checkpoint changed destination or read media");
    }
    Machine wrong(a.profile==fixed?distance:fixed,a.cpu.clock_divisor,a.output);
    const auto unchanged=pce::encode_checkpoint(wrong.bus,wrong.cpu);
    refuses([&]{pce::restore_checkpoint(wrong.bus,wrong.cpu,saved);},"Cross-profile checkpoint accepted");
    require(unchanged==pce::encode_checkpoint(wrong.bus,wrong.cpu) && wrong.media->data_reads.empty() && wrong.media->audio_reads.empty(),"Profile mismatch mutated destination or media");
    equal(a,*b);return b;
}
void paired_clock(Machine& a,Machine& b,std::uint64_t target) {
    // Compare at each bounded output chunk so neither branch loses PCM to a
    // host-sized catch-up interval. Whole payload equality includes both DSPs.
    while(a.cpu.ticks<target) {
        const auto next=std::min(target,a.cpu.ticks+286363);a.clock(next);b.clock(next);equal(a,b);
    }
}
void finish_read(Machine& a,Machine& b) {
    for(unsigned sector=0;sector<2;++sector) {
        if(a.bus.cd.scsi.load_deadline && a.bus.cd.sectors_read<=sector)paired_clock(a,b,a.bus.cd.scsi.load_deadline);
        for(unsigned byte=0;byte<2048;++byte)for(auto* m:{&a,&b}) {
            require(m->bus.cd.transport_read(0)==0xC8,"Restored DATA IN REQ missing");
            require(m->bus.cd.transport_read(1)==pattern(1000+sector,byte),"Restored READ buffer/provider payload differs");m->ack();
        }
        equal(a,b);
    }
    for(auto wait:{3000u,1500u,1500u}) {
        paired_clock(a,b,a.cpu.ticks+wait);
        if(wait!=1500 || a.bus.cd.scsi.phase!=0) {a.ack();b.ack();equal(a,b);}
    }
    require(a.bus.cd.scsi.phase==0 && a.bus.cd.sectors_read==2 && a.bus.cd.scsi.current_lba==1002,"READ suffix did not complete at literal head");
}
void suffix(Machine& a,Machine& b,Cut cut) {
    const auto a_data=a.media->data_reads.size(),a_audio=a.media->audio_reads.size();
    if(reading(cut))finish_read(a,b);
    else {
        if(cut==Cut::paused_before || cut==Cut::paused_after || cut==Cut::pause) {
            a.audio(0xD9,3,6800);b.audio(0xD9,3,6800);equal(a,b);
        } else if(cut==Cut::reset) {
            a.bus.cd.transport_write(4,0);b.bus.cd.transport_write(4,0);equal(a,b);
            a.audio(0xD8,1,6450);b.audio(0xD8,1,6450);equal(a,b);
        }
        for(unsigned i=0;i<4;++i) {
            auto next=a.bus.cd.audio.deadline;
            if(!next)next=a.cpu.ticks+1000;
            paired_clock(a,b,next);paired_clock(a,b,a.cpu.ticks+1);
        }
        if(cut!=Cut::stop)require(a.bus.cd.audio.state==0 && !a.bus.cd.audio.seek_deadline && !a.bus.cd.audio.playback_deadline,"Audio suffix did not pass both readiness phases");
        else require(a.bus.cd.audio.state==3 && !a.bus.cd.audio.deadline,"Stopped suffix restarted audio");
    }
    require(a.bus.adpcm.ram[0]==0x5A && !a.bus.adpcm.read_deadline && !a.bus.adpcm.write_deadline,"Pending ADPCM I/O did not continue after restore");
    require(std::vector<unsigned>(a.media->data_reads.begin()+a_data,a.media->data_reads.end())==b.media->data_reads,"Fresh data provider continuation differs");
    require(std::vector<unsigned>(a.media->audio_reads.begin()+a_audio,a.media->audio_reads.end())==b.media->audio_reads,"Fresh audio provider continuation differs");
    equal(a,b);
}
void matrix() {
    const auto selector=profile_offset();
    for(auto profile:{fixed,distance})for(unsigned divisor:{3u,12u})for(auto cut:cuts)for(bool output:{false,true}) {
        // The main matrix spans all timing cuts. Three extra PCM cuts retain
        // real pending queues/filter state rather than multiplying every cut.
        if(output && cut!=Cut::seek_after && cut!=Cut::resume && cut!=Cut::reset)continue;
        ++cases;auto a=std::make_unique<Machine>(profile,divisor,output);prepare(*a,cut);
        auto b=roundtrip(*a,selector);suffix(*a,*b,cut);
    }
}
}
int main() {
    try {matrix();std::cout<<cases<<" CD timing checkpoint cases; "<<checks<<" authored checks; zero guest retirements\n";return 0;}
    catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
