// Authored P-W packets, payloads and direct-device supervisors. Literal Q CRCs
// were independently calculated with Python's binascii.crc_hqx(data,0)^0xffff.
// This suite does not count supervisor operations as guest retirements.
#include "pce/checkpoint.hpp"
#include "pce/checkpoint_archive.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
unsigned checks=0;
using Q=std::array<std::uint8_t,12>;
constexpr Q position={0x41,1,1,0,0,0,0,0,2,0,0x28,0x32};
constexpr Q index0={1,2,0,0,1,2,0,0,3,4,0x42,0x29};
constexpr Q adr2={2,0x0A,0x23,1,2,3,4,5,6,7,0x5B,0x43};
constexpr Q adr3={3,0,1,2,3,4,5,6,7,8,0x38,0x9C};
constexpr Q adr5={5,8,9,6,5,4,3,2,1,0,0xE0,0xD6};
constexpr Q leadout={0x41,0xAA,1,0,0,0,0,0x99,0x59,0,0,0x2A};
void require(bool value,const char* why) {++checks;if(!value)throw std::runtime_error(why);}
template<class F>void refuses(F operation,const char* why) {
    bool caught=false;try{operation();}catch(const pce::Fault&){caught=true;}
    catch(const pce::checkpoint::ArchiveError&){caught=true;}
    require(caught,why);
}
pce::SubchannelSector symbols(const Q& q,unsigned noise=0) {
    pce::SubchannelSector raw{};
    for(unsigned i=0;i<96;++i)
        raw[i]=std::uint8_t((noise ? (i*37+noise)&0xBF:0)|(((q[i/8]>>(7-i%8))&1)<<6));
    return raw;
}
struct Media final:pce::SectorProvider {
    pce::CdToc geometry;
    std::map<unsigned,pce::SubchannelSector> captured;
    std::vector<unsigned> sub_reads,data_reads;
    bool capable=true,fail=false,wrong_error=false;
    Media() {
        geometry.track_count=2;geometry.tracks[0]={0,4};geometry.tracks[1]={4,0};
        geometry.leadout_lba=16;geometry.image_sha256=std::string(64,'c');
        captured[0]=symbols(position);captured[1]=symbols(adr2);
        captured[4]=symbols(position);captured[5]=symbols(index0);captured[6]=symbols(adr3);
    }
    pce::Sector read(std::uint32_t lba)override {
        data_reads.push_back(lba);pce::Sector result{};
        for(unsigned i=0;i<result.size();++i)result[i]=std::uint8_t(i*13+lba*7);return result;
    }
    pce::AudioSector read_audio(std::uint32_t)override{return {};}
    bool audio_playable(std::uint32_t lba)const override{return lba>=4 && lba<16;}
    pce::ProgramTrackLookup program_track(std::uint32_t lba)const override {
        return lba<16 ? pce::ProgramTrackLookup{true,lba<4 ? 0u:1u}:pce::ProgramTrackLookup{true,{}};
    }
    bool has_subchannel()const override{return capable;}
    std::optional<pce::SubchannelSector> read_subchannel(std::uint32_t lba)override {
        sub_reads.push_back(lba);if(fail)throw pce::Fault("authored subchannel I/O failure");
        if(wrong_error)throw pce::SectorReadError(pce::SectorReadReason::out_of_range,lba,"authored contract violation");
        const auto it=captured.find(lba);if(it==captured.end())return {};return it->second;
    }
    const pce::CdToc& toc()const override{return geometry;}
};
pce::CdControl prepare(const std::shared_ptr<Media>& media,bool captured=true) {
    pce::CdControl cd;cd.enabled=cd.scsi.enabled=cd.audio_enabled=true;cd.set_sector_provider(media);
    if(captured)cd.set_subchannel_profile(pce::CdSubchannelProfile::captured_q);return cd;
}
void command(pce::CdControl& cd,unsigned op,unsigned mode=0,unsigned lba=0) {
    auto& s=cd.scsi;s.command.fill(0);s.command[0]=std::uint8_t(op);s.command[1]=std::uint8_t(mode);
    s.command[3]=std::uint8_t(lba>>16);s.command[4]=std::uint8_t(lba>>8);s.command[5]=std::uint8_t(lba);
    s.phase=3;s.signals=0xD0;s.event=0;s.deadline=0;s.response_index=s.response_size=0;
}
void packet_checks() {
    for(const auto& q:{position,index0,adr2,adr3,adr5,leadout})require(pce::cd_subq_crc_valid(q),"Independent literal CRC refused");
    for(unsigned bit=0;bit<96;++bit) {
        auto bad=position;bad[bit/8]^=std::uint8_t(1u<<(bit%8));
        require(!pce::cd_subq_crc_valid(bad),"Single-bit Q corruption admitted");
    }
    require(!pce::cd_subq_crc_valid(Q{}),"Zero Q is not a valid captured packet");
    auto media=std::make_shared<Media>();auto cd=prepare(media);
    command(cd,0xDD);cd.audio_command();
    constexpr std::array<unsigned,10> unknown{3,0,0,0,0,0,0,0,0,0};
    for(unsigned i=0;i<10;++i)require(cd.scsi.response[i]==unknown[i],"Unacquired Q was fabricated from TOC");
    require(media->sub_reads.empty(),"DD queried media rather than retained Q");
    for(unsigned noise:{0u,1u,31u,255u}) {
        media->captured[2]=symbols(position,noise);cd.sample_subchannel(2);
        require(cd.subchannel.last==position && cd.subchannel.position==position,"P/R-W lanes altered Q extraction");
    }
    for(const auto& q:{adr2,adr3,adr5}) {
        media->captured[2]=symbols(q);cd.sample_subchannel(2);
        require(cd.subchannel.last==q && cd.subchannel.position==position,"Non-position ADR overwrote retained ADR1");
    }
    auto corrupt=symbols(index0);corrupt[29]^=0x40;media->captured[2]=corrupt;
    cd.sample_subchannel(2);cd.sample_subchannel(3);
    require(cd.subchannel.last==adr5 && cd.subchannel.position==position &&
            cd.subchannel.samples==9 && cd.subchannel.crc_errors==1 && cd.subchannel.missing==1,
            "Bad CRC or absent capture changed Q/diagnostics");
    media->captured[2]=symbols(index0);cd.sample_subchannel(2);
    require(cd.subchannel.position==index0,"Captured index00 was replaced with synthesized index01");
    const auto reads=media->sub_reads;
    for(unsigned state:{0u,1u,2u,3u}) {
        cd.audio.state=state;command(cd,0xDD);cd.audio_command();
        constexpr std::array<unsigned,9> fields{0,2,0,0,1,2,0,3,4};
        require(cd.scsi.response[0]==(state==0 ? 0:state==2 ? 2:3),"Captured DD state differs");
        for(unsigned i=0;i<9;++i)require(cd.scsi.response[1+i]==fields[i],"Captured DD fields/control differ");
    }
    require(media->sub_reads==reads,"Repeated position queries reacquired Q");
    media->captured[2]=symbols(leadout);cd.sample_subchannel(2);
    require(cd.subchannel.position==leadout,"Captured AA track was replaced or decoded as ordinary BCD");
}
void selection_and_failure() {
    pce::CdControl absent;absent.set_subchannel_profile(pce::CdSubchannelProfile::synthesized);
    refuses([&]{absent.set_subchannel_profile(pce::CdSubchannelProfile::captured_q);},"No-provider captured selection accepted");
    auto media=std::make_shared<Media>();media->capable=false;auto cd=prepare(media,false);
    refuses([&]{cd.set_subchannel_profile(pce::CdSubchannelProfile::captured_q);},"Absent captured capability accepted");
    refuses([&]{cd.set_subchannel_profile(static_cast<pce::CdSubchannelProfile>(2));},"Unknown subchannel profile accepted");
    media->capable=true;cd.set_subchannel_profile(pce::CdSubchannelProfile::captured_q);
    media->fail=true;
    refuses([&]{cd.sample_subchannel(0);},"Subchannel decoder failure was hidden");
    require(cd.subchannel.samples==0 && !cd.subchannel.sampled_lba,"Failed read committed acquisition state");
    media->fail=false;media->wrong_error=true;
    bool contract_refused=false;
    try {cd.sample_subchannel(0);}catch(const pce::SectorReadError&){throw std::runtime_error("Subchannel error retained recoverable user-data category");}
    catch(const pce::Fault&){contract_refused=true;}
    require(contract_refused && cd.subchannel.samples==0,"Subchannel provider-contract error was not fatal");
    media->wrong_error=false;
    media->fail=false;cd.sample_subchannel(0);const auto old=cd.subchannel;
    refuses([&]{cd.set_subchannel_profile(pce::CdSubchannelProfile::synthesized);},"Live profile switch accepted");
    refuses([&]{cd.sample_subchannel(16);},"Past-disc acquisition accepted");
    require(cd.subchannel.samples==old.samples && cd.subchannel.last==old.last,"Refusal changed retained Q");
    auto synth=prepare(media,false);synth.sample_subchannel(0);
    require(!synth.subchannel.samples,"Default profile consumed captured media");
    command(synth,0xDD);synth.audio_command();
    require(synth.scsi.response[0]==1 && synth.scsi.response[1]==0x41 && synth.scsi.response[2]==1,
            "Default synthesized response changed");
    cd.subchannel.samples=std::numeric_limits<std::uint64_t>::max();
    refuses([&]{cd.sample_subchannel(0);},"Subchannel sample counter wrapped");
}
void ack(pce::CdControl& cd) {cd.transport_write(2,0x80);cd.transport_write(2,0);}
void read_and_audio() {
    auto media=std::make_shared<Media>();auto cd=prepare(media);
    cd.transport_write(0,0);cd.advance_to(75000);
    constexpr unsigned cdb[]{8,0,0,0,2,0};
    for(unsigned i=0;i<6;++i) {
        cd.transport_write(1,std::uint8_t(cdb[i]));ack(cd);if(i<5)cd.advance_to(cd.scsi.master_ticks+3000);
    }
    require(media->sub_reads.empty(),"READ acquired Q before sector load");
    cd.advance_to(cd.scsi.load_deadline);
    require(media->sub_reads==std::vector<unsigned>{0} && cd.subchannel.position==position && cd.scsi.current_lba==1,
            "READ sampled advanced head instead of successfully loaded sector");
    const auto initial_samples=cd.subchannel.samples;
    cd.advance_to(cd.scsi.load_deadline);
    require(cd.read_retries==1 && cd.subchannel.samples==initial_samples,"Occupied READ retry reacquired Q");
    for(unsigned i=0;i<2048;++i)ack(cd);
    cd.advance_to(cd.scsi.load_deadline);
    require(media->sub_reads==std::vector<unsigned>({0,1}) && cd.subchannel.last==adr2 &&
            cd.subchannel.position==position,"Second successful READ did not retain ADR1 independently");
    media=std::make_shared<Media>();cd=prepare(media);
    command(cd,0xD8,1,4);cd.audio_command();
    cd.advance_to(cd.audio.seek_deadline-1);require(media->sub_reads.empty(),"Seek acquired Q before playback readiness");
    cd.advance_to(cd.audio.seek_deadline);
    require(media->sub_reads==std::vector<unsigned>{4},"First playback sector was skipped");
    cd.advance_to(cd.audio.sector_deadline);
    require(media->sub_reads==std::vector<unsigned>({4,5}) && cd.subchannel.position==index0,"Playback advance acquired wrong sector");
    command(cd,0xDA);cd.audio_command();const auto count=cd.subchannel.samples;
    cd.advance_to(cd.scsi.master_ticks+1000000);require(cd.subchannel.samples==count,"Pause acquired new Q");
    command(cd,0xD9,3,8);cd.audio_command();cd.advance_to(cd.audio.playback_deadline);
    require(media->sub_reads==std::vector<unsigned>({4,5,5}),"Paused resume did not reacquire current sector");
    command(cd,0xD9,0);cd.audio_command();
    command(cd,0xD9,3,8);cd.audio_command();
    require(media->sub_reads==std::vector<unsigned>({4,5,5,5}),"Stopped D9 start skipped its first current sector");
    cd.transport_write(4,2);
    require(cd.subchannel.position==index0,"Bus reset discarded retained captured Q");
}
struct Machine {
    pce::Bus bus;pce::Cpu cpu;std::shared_ptr<Media> media=std::make_shared<Media>();
    explicit Machine(bool capture=true) {
        bus.enable_cd_transport();bus.cd.audio_enabled=true;bus.cd.set_sector_provider(media);
        if(capture)bus.cd.set_subchannel_profile(pce::CdSubchannelProfile::captured_q);
    }
    void clock(std::uint64_t ticks) {cpu.ticks=ticks;bus.sync(cpu);}
};
void checkpoint_checks() {
    for(unsigned cut=0;cut<10;++cut) {
        auto a=std::make_unique<Machine>();a->bus.cd.sample_subchannel(0);
        a->media->captured[2]=symbols(adr2);a->bus.cd.sample_subchannel(2);
        command(a->bus.cd,0xDD);a->bus.cd.audio_command();a->clock(3000);
        for(unsigned i=0;i<cut;++i) {ack(a->bus.cd);a->clock(a->cpu.ticks+900);}
        const auto saved=pce::encode_checkpoint(a->bus,a->cpu);const auto reads=a->media->sub_reads;
        auto b=std::make_unique<Machine>();pce::restore_checkpoint(b->bus,b->cpu,saved);
        require(pce::encode_checkpoint(b->bus,b->cpu)==saved && b->media->sub_reads.empty() && a->media->sub_reads==reads,
                "Partial captured-DD checkpoint changed bytes or read media");
        for(unsigned i=cut;i<10;++i) {
            require(a->bus.cd.transport_read(1)==b->bus.cd.transport_read(1),"Restored captured-DD response diverged");
            ack(a->bus.cd);ack(b->bus.cd);
            a->clock(a->cpu.ticks+900);b->clock(b->cpu.ticks+900);
            require(pce::encode_checkpoint(a->bus,a->cpu)==pce::encode_checkpoint(b->bus,b->cpu),"Continued captured-DD CORE differs");
        }
        auto wrong=std::make_unique<Machine>(false);const auto before=pce::encode_checkpoint(wrong->bus,wrong->cpu);
        refuses([&]{pce::restore_checkpoint(wrong->bus,wrong->cpu,saved);},"Cross-profile checkpoint accepted");
        require(pce::encode_checkpoint(wrong->bus,wrong->cpu)==before && wrong->media->sub_reads.empty(),"Rejected restore mutated live machine");
    }
    auto m=std::make_unique<Machine>();m->bus.cd.sample_subchannel(0);
    const auto saved=pce::encode_checkpoint(m->bus,m->cpu);
    m->bus.cd.subchannel.position[10]^=1;
    refuses([&]{pce::encode_checkpoint(m->bus,m->cpu);},"Corrupt retained Q CRC serialized");
    pce::restore_checkpoint(m->bus,m->cpu,saved);m->bus.cd.subchannel.crc_errors=2;
    refuses([&]{pce::encode_checkpoint(m->bus,m->cpu);},"Impossible Q diagnostics serialized");
    pce::restore_checkpoint(m->bus,m->cpu,saved);m->bus.cd.subchannel.position_valid=false;
    refuses([&]{pce::encode_checkpoint(m->bus,m->cpu);},"Hidden retained position bytes serialized");
    pce::restore_checkpoint(m->bus,m->cpu,saved);m->bus.cd.subchannel_profile=static_cast<pce::CdSubchannelProfile>(255);
    refuses([&]{pce::encode_checkpoint(m->bus,m->cpu);},"Invalid Q profile serialized");
}
}
int main() {
    try {packet_checks();selection_and_failure();read_and_audio();checkpoint_checks();std::cout<<"Captured subchannel checks: "<<checks<<"\n";return 0;}
    catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
