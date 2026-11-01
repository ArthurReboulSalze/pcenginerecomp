// Authored bounded register supervisor, shared by isolated reference executables.
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#ifndef PCE_TIMING_GEAR
#include "pce/runtime.hpp"
#include "pce/sector.hpp"
#include "pce/code_capture.hpp"
#include "pce/checkpoint.hpp"
#include "pce/cd_timing.hpp"
#include "scsi_fixture.hpp"
#include "sense_probe_support.hpp"
struct TimingAdapter {
    std::unique_ptr<pce::Bus> bus; pce::Cpu cpu;
    const std::vector<std::uint8_t>& rom;const char* cue;bool native;unsigned divisor;
    pce::CodeCapture capture;std::uint64_t calls=0;unsigned checkpoints=0;
    TimingAdapter(const std::vector<std::uint8_t>& r,const char* c,const std::string& tier,unsigned speed,const char* cap):rom(r),cue(c),native(tier=="native"),divisor(speed),capture(cap,128){}
    void reset(bool distance){bus=std::make_unique<pce::Bus>();bus->configure_system_card(pce::SystemCardProfile::super,rom);
        bus->enable_cd_transport();bus->enable_adpcm();bus->enable_video();bus->enable_interrupts();bus->enable_psg();
        bus->cd.timing_profile=distance?pce::CdTimingProfile::gear_distance:pce::CdTimingProfile::fixed;
        bus->cd.set_sector_provider(pce::open_sector_provider(cue));for(auto [address,value]:scsi_program)(*bus->bytes)[address]=value;
        cpu=pce::Cpu{};cpu.mpr=scsi_mpr;cpu.clock_divisor=divisor;cpu.p=pce::I;}
    void execute(unsigned opcode,unsigned address=0,int value=-1){
        bool found=false;for(auto item:scsi_cases)if(item.op==opcode&&item.address==address){cpu.pc=item.pc;found=true;break;}
        if(!found)throw std::runtime_error("Unknown authored timing port site");if(value>=0)cpu.a=std::uint8_t(value);
        const auto pending=capture.before(*bus,cpu);const auto status=native?pce::generated_step(*bus,cpu,UINT64_MAX):pce::interpret_step(*bus,cpu,UINT64_MAX);
        if(status!=pce::Exit::executed)throw std::runtime_error("Timing opcode did not execute directly");capture.after(pending,cpu);++calls;}
    void write(unsigned address,unsigned value){execute(0x8D,address,value);}
    unsigned read(bool automatic){execute(0xAD,automatic?0x1808:0x1801);return cpu.a;}
    unsigned read_port(unsigned address){execute(0xAD,address);return cpu.a;}
    void auto_finish(){execute(0xEA);execute(0xEA);advance(21);}
    void advance(std::uint64_t ticks){while(ticks){auto n=std::min<std::uint64_t>(ticks,4096);cpu.ticks+=n;bus->sync(cpu);ticks-=n;}}
    std::uint64_t now()const{return cpu.ticks;} unsigned phase()const{return bus->cd.scsi.phase;}unsigned signals()const{return bus->cd.scsi.signals;}
    unsigned head()const{return bus->cd.scsi.current_lba;}
    std::uint64_t deadline(const std::string& field)const{const auto&a=bus->cd.audio;const auto&s=bus->cd.scsi;
        if(field=="seek")return a.seek_deadline;if(field=="play")return a.playback_deadline;if(field=="sector")return a.sector_deadline;if(field=="load")return s.load_deadline;throw std::runtime_error("Unknown timing deadline");}
    std::vector<std::uint64_t> logical()const{const auto&a=bus->cd.audio;return {a.state,a.start_lba,a.current_lba,a.stop_lba,a.seek_start_lba,a.stop_mode,head(),a.sectors_played,bus->cd.scsi.load_lba,bus->cd.scsi.load_remaining,bus->cd.read_retries};}
    unsigned math(unsigned from,unsigned to)const{return static_cast<unsigned>(pce::cd_seek_ticks(pce::CdTimingProfile::gear_distance,from,to));}
    bool checkpoint(){auto raw=pce::encode_checkpoint(*bus,cpu);auto saved=pce::decode_checkpoint(raw,*bus);if(pce::encode_checkpoint(saved->bus,saved->cpu)!=raw)throw std::runtime_error("Complete timing checkpoint roundtrip differs");bus=std::make_unique<pce::Bus>(std::move(saved->bus));cpu=saved->cpu;++checkpoints;return true;}
    void finish(){capture.finish();}
};
#else
struct TimingAdapter:TimingGearBase {
    unsigned divisor;std::uint64_t calls=0;unsigned checkpoints=0;
    TimingAdapter(const std::vector<std::uint8_t>& r,const char*c,const std::string&,unsigned speed,const char*):TimingGearBase{nullptr,r,c},divisor(speed){}
    void reset(bool){TimingGearBase::reset(1);core->GetAudio()->Reset(true);}
    void write(unsigned address,unsigned value){core->GetCDROM()->WriteRegister(address,value);++calls;advance(5*divisor);}
    unsigned read(bool automatic){const auto value=core->GetCDROM()->ReadRegister(automatic?0x1808:0x1801);++calls;advance(5*divisor);return value;}
    unsigned read_port(unsigned address){const auto value=core->GetCDROM()->ReadRegister(address);++calls;advance(5*divisor);return value;}
    void auto_finish(){calls+=2;advance(4*divisor+21);}
    void advance(std::uint64_t ticks){while(ticks){auto n=unsigned(std::min<std::uint64_t>(ticks,4096));TimingGearBase::advance(n);ticks-=n;}}
    std::uint64_t now()const{return core->GetMasterClockCycles();}unsigned phase()const{return unsigned(*core->GetScsiController()->GetState()->PHASE);}
    unsigned head()const{return core->GetCDROMMedia()->GetCurrentSector();}
    std::uint64_t deadline(const std::string& field)const{auto*a=core->GetCDROMAudio()->GetState();auto*s=core->GetScsiController()->GetState();
        const auto seek=*a->SEEK_CYCLES,play=*a->PLAYBACK_DELAY_CYCLES;
        if(field=="seek")return seek>0?now()+unsigned(seek):0;
        if(field=="play")return play>0?now()+unsigned(std::max(seek,0))+unsigned(play):0;
        if(field=="load"){auto n=*s->NEXT_LOAD_CYCLES;return n>0?now()+unsigned(n):0;}
        if(field=="sector")return 0;throw std::runtime_error("Unknown original timing deadline");}
    std::vector<std::uint64_t> logical()const{auto*a=core->GetCDROMAudio()->GetState();auto*s=core->GetScsiController()->GetState();
        return {unsigned(*a->CURRENT_STATE),*a->START_LBA,*a->CURRENT_LBA,*a->STOP_LBA,core->GetCDROMAudio()->*member(TimingSeekStart{}),unsigned(*a->STOP_EVENT),head(),0,*s->LOAD_SECTOR,*s->LOAD_SECTOR_COUNT,0};}
    unsigned math(unsigned from,unsigned to)const{CdRomMedia media;return media.SeekTime(from,to)*21477273ULL/1000;}
    bool checkpoint(){return false;}void finish(){}
};
#endif
namespace {
void need(bool value,const char* text){if(!value)throw std::runtime_error(text);}
void wait_command(TimingAdapter&a){for(unsigned n=0;n<20000;++n){if(a.phase()==3&&(a.signals()&64))return;a.advance(1000);}throw std::runtime_error("Timing command wait exceeded");}
void start(TimingAdapter&a,unsigned op,unsigned mode,unsigned lba,unsigned count){a.write(0x1800,0);wait_command(a);
    const std::vector<unsigned> bytes=op==8?std::vector<unsigned>{8,(lba>>16)&31,(lba>>8)&255,lba&255,count,0}:std::vector<unsigned>{op,mode,0,(lba>>16)&255,(lba>>8)&255,lba&255,0,0,0,0};
    std::uint64_t last=0;unsigned head=0,index=0;
    for(auto v:bytes){wait_command(a);a.write(0x1801,v);a.write(0x1802,128);a.advance(1);if(++index==bytes.size()){last=a.now();head=a.head();}a.write(0x1802,0);a.advance(1);}
    std::cout<<"{\"kind\":\"admission\",\"op\":"<<op<<",\"mode\":"<<mode<<",\"lba\":"<<lba<<",\"count\":"<<count<<",\"head_before\":"<<head<<",\"ack_entry\":"<<last<<",\"after\":"<<a.now()<<"}\n";}
void drain(TimingAdapter&a,unsigned automatic){unsigned status=999,message=999,data=0;std::uint64_t sum=0;std::vector<unsigned> payload;
    for(unsigned n=0;n<100000;++n){if(!(a.signals()&128)){need(status<=255&&message<=255,"Missing timing completion");std::cout<<"{\"kind\":\"reply\",\"status\":"<<status<<",\"message\":"<<message<<",\"bytes\":"<<data<<",\"sum\":"<<sum<<",\"data\":[";for(unsigned i=0;i<payload.size();++i)std::cout<<(i?",":"")<<payload[i];std::cout<<"]}\n";return;}
        if(!(a.signals()&64)){a.advance(1000);continue;}need(a.signals()&8,"Timing reply direction");bool is_data=!(a.signals()&16),is_message=a.signals()&32;unsigned v=a.read(automatic&&is_data);
        if(is_data){need(data<8192,"Timing payload bound");++data;sum+=v;payload.push_back(v);}else if(is_message)message=v;else status=v;
        if(automatic&&is_data)a.auto_finish();else{a.write(0x1802,128);a.advance(1);a.write(0x1802,0);a.advance(1);}}
    throw std::runtime_error("Timing reply wait exceeded");}
void observe(const std::string&label,const TimingAdapter&a){std::cout<<"{\"kind\":\"state\",\"label\":\""<<label<<"\",\"ticks\":"<<a.now()<<",\"phase\":"<<a.phase()<<",\"signals\":"<<a.signals()<<",\"seek\":"<<a.deadline("seek")<<",\"play\":"<<a.deadline("play")<<",\"load\":"<<a.deadline("load")<<",\"logical\":[";
    const auto values=a.logical();for(unsigned i=0;i<values.size();++i)std::cout<<(i?",":"")<<values[i];std::cout<<"]}\n";}
}
int main(int argc,char**argv){try{
#ifdef PCE_TIMING_GEAR
    if(argc==2&&std::string(argv[1])=="--math"){unsigned from,to;CdRomMedia media;while(std::cin>>from>>to){auto ms=media.SeekTime(from,to);std::cout<<from<<' '<<to<<' '<<ms<<' '<<std::uint64_t(ms)*21477273/1000<<'\n';}need(std::cin.eof(),"Malformed seek vector");return 0;}
#else
    if(argc==2&&std::string(argv[1])=="--math"){unsigned from,to;while(std::cin>>from>>to)std::cout<<from<<' '<<to<<" -1 "<<pce::cd_seek_ticks(pce::CdTimingProfile::gear_distance,from,to)<<'\n';need(std::cin.eof(),"Malformed seek vector");return 0;}
#endif
    need(argc==8,"timing PLAN ROM CUE TIER DIVISOR CAPTURE REPORT");const auto rom=reset_probe::rom(argv[2]);const std::string tier=argv[4];const unsigned divisor=std::stoul(argv[5]);need(divisor==3||divisor==12,"Timing speed");
#ifdef PCE_TIMING_GEAR
    need(tier=="gear","Original Gear execution tier required");
#else
    need(tier=="native"||tier=="interpreter","Explicit toolkit execution tier required");
#endif
    TimingAdapter a(rom,argv[3],tier,divisor,argv[6]);std::ifstream plan(argv[1]);need(bool(plan),"Timing plan missing");std::string op,id;unsigned cases=0,records=0;std::uint64_t last_strobe=0;
    while(plan>>op){need(op=="R"||cases,"Timing operation before reset");if(op=="R"){std::string profile;plan>>id>>profile;need(profile=="fixed"||profile=="gear-distance","Timing profile");a.reset(profile=="gear-distance");last_strobe=0;std::cout<<"{\"kind\":\"case\",\"id\":\""<<id<<"\",\"profile\":\""<<profile<<"\"}\n";++cases;}
        else if(op=="S"){unsigned code,mode,lba,count;plan>>code>>mode>>lba>>count;start(a,code,mode,lba,count);}
        else if(op=="D"){unsigned automatic;plan>>automatic;need(automatic<=1,"ACK profile");drain(a,automatic);}
        else if(op=="P"){std::string label;plan>>label;observe(label,a);++records;}
        else if(op=="E"){std::string field;int offset;plan>>field>>offset;need(offset>=-1&&offset<=1,"Timing edge offset");auto edge=a.deadline(field);need(edge&&edge+offset>=a.now(),"Missing or past timing edge");a.advance(edge+offset-a.now());}
        else if(op=="A"){unsigned n;plan>>n;need(n<=60000000,"Timing bounded wait");a.advance(n);}
        else if(op=="W"){a.write(0x1804,2);a.advance(1);a.write(0x1804,0);a.advance(1);}
        else if(op=="K"){std::cout<<"{\"kind\":\"checkpoint\",\"whole_core_roundtrip\":"<<(a.checkpoint()?"true":"false")<<"}\n";}
        else if(op=="L"){std::string label;plan>>label;const auto strobe=a.now(),interval=strobe-last_strobe;need(interval>=700,"Authored latch strobe violates700tick interval");a.write(0x1805,0);last_strobe=strobe;const auto lo=a.read_port(0x1805),hi=a.read_port(0x1806);std::cout<<"{\"kind\":\"latch\",\"label\":\""<<label<<"\",\"ticks\":"<<a.now()<<",\"strobe_ticks\":"<<strobe<<",\"interval_ticks\":"<<interval<<",\"value\":"<<(lo|(hi<<8))<<"}\n";}
        else throw std::runtime_error("Unknown authored timing operation");need(bool(plan),"Malformed timing operation");}
    a.finish();need(!std::filesystem::exists(argv[7]),"New timing report required");std::ofstream report(argv[7]);report<<"{\"schema\":1,\"tier\":\""<<tier<<"\",\"divisor\":"<<divisor<<",\"cases\":"<<cases<<",\"states\":"<<records<<",\"calls\":"<<a.calls<<",\"checkpoints\":"<<a.checkpoints<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
