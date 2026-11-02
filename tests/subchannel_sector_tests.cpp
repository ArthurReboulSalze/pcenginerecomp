// Independently authored decoded-hunk fixtures; no original disc bytes.
// The shared ABI double reads these bytes as data, not actual CHD compression.
#include "pce/sector.hpp"
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {
namespace fs=std::filesystem;
unsigned checks=0;
void require(bool value,const char* message) {++checks;if(!value)throw std::runtime_error(message);}
template<class F> void refuses(F operation,const char* text) {
    bool failed=false;
    try {operation();}catch(const pce::Fault& error){failed=std::string(error.what()).find(text)!=std::string::npos;}
    require(failed,"Expected fatal subchannel refusal missing");
}
struct Files {
    fs::path dir=fs::temp_directory_path()/("pce-subchannel-tests-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::vector<fs::path> owned;
    Files(){if(!fs::create_directory(dir))throw std::runtime_error("Cannot create subchannel fixture directory");}
    ~Files(){std::error_code error;for(const auto& path:owned)fs::remove(path,error);fs::remove(dir,error);}
    std::string write(const std::string& name,const std::vector<std::uint8_t>& bytes) {
        const auto path=dir/name;
        if(std::find(owned.begin(),owned.end(),path)==owned.end())owned.push_back(path);
        std::ofstream output(path,std::ios::binary|std::ios::trunc);
        output.write(reinterpret_cast<const char*>(bytes.data()),bytes.size());
        if(!output)throw std::runtime_error("Cannot write authored subchannel fixture");
        return path.string();
    }
};
void be(std::vector<std::uint8_t>& bytes,unsigned at,std::uint64_t value,unsigned count) {
    for(unsigned i=0;i<count;++i)bytes[at+count-1-i]=static_cast<std::uint8_t>(value>>(8*i));
}
struct Record {std::string text;unsigned frames;};
std::vector<std::uint8_t> image(const std::vector<Record>& records,bool old=false) {
    unsigned frames=0;for(const auto& record:records)frames+=(record.frames+3)/4*4;
    std::vector<std::uint8_t> bytes(4096+frames*2448,0xED);
    std::fill_n(bytes.begin(),4096,0);
    std::copy_n("MComprHD",8,bytes.begin());
    be(bytes,8,124,4);be(bytes,12,5,4);be(bytes,32,frames*2448,8);be(bytes,48,124,8);
    be(bytes,56,4*2448,4);be(bytes,60,2448,4);
    unsigned at=124;
    for(unsigned i=0;i<records.size();++i) {
        const auto& text=records[i].text;
        std::copy_n(old?"CHTR":"CHT2",4,bytes.begin()+at);
        be(bytes,at+4,text.size()+1,4);be(bytes,at+8,i+1==records.size()?0:at+17+text.size(),8);
        std::copy(text.begin(),text.end(),bytes.begin()+at+16);at+=17+static_cast<unsigned>(text.size());
    }
    require(at<4096,"Authored fixture metadata exceeds reserved prefix");return bytes;
}
pce::SubchannelSector symbols(unsigned seed) {
    pce::SubchannelSector result{};
    // All eight lanes and first/last symbols differ. This is a storage-order
    // fixture, not an assumed valid Q packet; CRC validation belongs to drive.
    for(unsigned i=0;i<result.size();++i)result[i]=static_cast<std::uint8_t>((seed*61+i*13)^(1U<<(i%8)));
    return result;
}
void place(std::vector<std::uint8_t>& bytes,unsigned frame,unsigned offset,const pce::SubchannelSector& value) {
    std::copy(value.begin(),value.end(),bytes.begin()+4096+frame*2448+offset);
}
void present(pce::SectorProvider& provider,unsigned lba,const pce::SubchannelSector& expected) {
    const auto actual=provider.read_subchannel(lba);
    require(actual.has_value(),"Stored raw symbols reported absent");
    require(*actual==expected,"Original P-W symbols/offset/frame order changed");
}
void absence(Files& files,const std::string& library) {
    auto iso=pce::open_sector_provider(files.write("empty-sub.iso",std::vector<std::uint8_t>(2048,0x33)));
    require(!iso->has_subchannel(),"ISO invented captured capability");
    for(unsigned lba:{0U,1U,0xffffffffU})require(!iso->read_subchannel(lba),"ISO invented captured symbols");
    auto bytes=image({{"TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:0 PGTYPE:AUDIO PGSUB:NONE POSTGAP:0",3}});
    // Deliberately populated tail: NONE metadata must override arbitrary bytes.
    place(bytes,0,2352,symbols(7));
    auto none=pce::open_sector_provider(files.write("none.chd",bytes),library);
    require(!none->has_subchannel(),"NONE invented captured capability");
    for(unsigned lba:{0U,2U,3U,0xffffffffU})require(!none->read_subchannel(lba),"NONE/padding invented original symbols");
    // NONE reads cannot invoke even a decoder that always fails.
    bytes[16]=0xEE;auto no_decode=pce::open_sector_provider(files.write("none-refuse.chd",bytes),library);
    require(!no_decode->read_subchannel(0),"Absent metadata decoded or synthesized symbols");
    const std::string cue="FILE \"empty-sub.iso\" BINARY\n TRACK 01 MODE1/2048\n INDEX 01 00:00:00\n";
    auto cue_provider=pce::open_sector_provider(files.write("absent.cue",std::vector<std::uint8_t>(cue.begin(),cue.end())));
    require(!cue_provider->has_subchannel()&&!cue_provider->read_subchannel(0),"CUE invented captured symbols");
}
void mapping(Files& files,const std::string& library) {
    auto bytes=image({
        {"TRACK:1 TYPE:MODE1 SUBTYPE:RW_RAW FRAMES:3 PREGAP:0 PGTYPE:MODE1 PGSUB:NONE POSTGAP:1",3},
        {"TRACK:2 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:5 PREGAP:2 PGTYPE:VAUDIO PGSUB:RW_RAW POSTGAP:0",5},
        {"TRACK:3 TYPE:MODE1_RAW SUBTYPE:RW_RAW FRAMES:2 PREGAP:2 PGTYPE:MODE1_RAW PGSUB:RW_RAW POSTGAP:0",2}});
    // Physical frames: T1=0..2,pad3; storedT2PG4..5,T2program6..8,pad9..11;
    // T3virtualPG has no frames,T3program12..13. Disc T1=0..2,post3;
    // T2PG=4..5,T2program6..8,T3virtualPG9..10,T3program11..12.
    for(unsigned frame:{0U,1U,2U})place(bytes,frame,2048,symbols(frame));
    for(unsigned frame:{4U,5U,6U,7U,8U,12U,13U})place(bytes,frame,2352,symbols(frame));
    auto provider=pce::open_sector_provider(files.write("mapping.chd",bytes),library);
    require(provider->has_subchannel(),"Raw extent missing captured capability");
    for(unsigned lba:{2U,0U,1U,4U,5U,6U,8U,7U,11U,12U,0U,8U}) {
        const unsigned frame=lba<9?lba:lba+1;
        present(*provider,lba,symbols(frame));
    }
    for(unsigned lba:{3U,9U,10U,13U,0xffffffffU})require(!provider->read_subchannel(lba),"Gap/padding/outside leaked symbols");
    // Raw/cooked packet validity is not a media-provider responsibility.
    std::fill_n(bytes.begin()+4096+2352,96,0); // unrelated MODE1 padding remains unused
    place(bytes,0,2048,{});
    auto zero=pce::open_sector_provider(files.write("zero.chd",bytes),library);
    present(*zero,0,{});
    auto changed=bytes;changed.push_back(0);files.write("mapping.chd",changed);
    refuses([&]{provider->has_subchannel();},"changed");
    for(unsigned lba:{0U,3U,0xffffffffU})refuses([&]{provider->read_subchannel(lba);},"changed");
}
void pregaps(Files& files,const std::string& library) {
    // Program and stored pregap subtypes remain independent. Different
    // declared types are allowed only when their payload byte sizes agree.
    auto bytes=image({{"TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:5 PREGAP:2 PGTYPE:VMODE1_RAW PGSUB:RW_RAW POSTGAP:0",5}});
    place(bytes,0,2352,symbols(90));place(bytes,1,2352,symbols(91));
    auto provider=pce::open_sector_provider(files.write("pg-only.chd",bytes),library);
    require(provider->has_subchannel(),"Stored raw pregap did not enable capability");
    present(*provider,0,symbols(90));present(*provider,1,symbols(91));
    for(unsigned lba:{2U,4U,5U})require(!provider->read_subchannel(lba),"NONE program inherited captured pregap");
    bytes=image({{"TRACK:1 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:5 PREGAP:2 PGTYPE:VMODE1 PGSUB:NONE POSTGAP:0",5}});
    place(bytes,2,2352,symbols(12));provider=pce::open_sector_provider(files.write("program-only.chd",bytes),library);
    require(provider->has_subchannel(),"Program raw capability missing");present(*provider,2,symbols(12));
    require(!provider->read_subchannel(0)&&!provider->read_subchannel(1),"NONE pregap inherited captured program");
    bytes=image({{"TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:2 PGTYPE:MODE1 PGSUB:RW_RAW POSTGAP:0",3}});
    provider=pce::open_sector_provider(files.write("virtual-only.chd",bytes),library);
    require(!provider->has_subchannel()&&!provider->read_subchannel(0),"Virtual pregap invented stored capture");
}
void malformed(Files& files,const std::string& library) {
    for(const auto& record:{
        "TRACK:1 TYPE:AUDIO SUBTYPE:ALIEN FRAMES:3 PREGAP:0 PGTYPE:AUDIO PGSUB:NONE POSTGAP:0",
        "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:0 PGTYPE:AUDIO PGSUB:ALIEN POSTGAP:0",
        "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:V PGSUB:RW_RAW POSTGAP:0",
        "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VMODE2 PGSUB:RW_RAW POSTGAP:0",
        "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VMODE1 PGSUB:RW_RAW POSTGAP:0",
        "TRACK:1 TYPE:MODE1 SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VAUDIO PGSUB:RW_RAW POSTGAP:0",
        "TRACK:1 TYPE:AUDIO SUBTYPE:NONE SUBTYPE:RW_RAW FRAMES:3",
        "TRACK:1 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:3 garbage",
        "TRACK:1 TYPE:AUDIO SUBTYPE: FRAMES:3"}) {
        auto path=files.write("bad.chd",image({{record,3}}));refuses([&]{pce::open_sector_provider(path,library);},"");
    }
    auto bytes=image({{"TRACK:1 TYPE:MODE1 SUBTYPE:RW FRAMES:3 PREGAP:0 PGTYPE:MODE1 PGSUB:NONE POSTGAP:0",3}});
    auto provider=pce::open_sector_provider(files.write("cooked.chd",bytes),library);
    require(!provider->has_subchannel(),"Cooked R-W advertised original P-W capability");
    require(provider->read(0)[0]==0xED,"Cooked R-W broke ordinary user-data access");
    refuses([&]{provider->read_subchannel(0);},"Cooked");
    // CHTR has no pregap fields; raw program sectors remain supported.
    bytes=image({{"TRACK:1 TYPE:MODE1 SUBTYPE:RW_RAW FRAMES:3",3}},true);
    place(bytes,1,2048,symbols(33));provider=pce::open_sector_provider(files.write("old.chd",bytes),library);
    present(*provider,1,symbols(33));
}
void decode_failure(Files& files,const std::string& library) {
    auto bytes=image({{"TRACK:1 TYPE:MODE1 SUBTYPE:RW_RAW FRAMES:9 PREGAP:0 PGTYPE:MODE1 PGSUB:NONE POSTGAP:0",9}});
    place(bytes,0,2048,symbols(50));place(bytes,4,2048,symbols(51));place(bytes,8,2048,symbols(52));
    bytes[17]=0xFD;bytes[18]=1;
    auto provider=pce::open_sector_provider(files.write("partial.chd",bytes),library);
    present(*provider,0,symbols(50));
    refuses([&]{provider->read_subchannel(4);},"decode failed");
    present(*provider,0,symbols(50)); // partially overwritten old hunk must reload
    present(*provider,4,symbols(51));present(*provider,8,symbols(52));
    bytes[16]=0xEE;provider=pce::open_sector_provider(files.write("decoder-error.chd",bytes),library);
    refuses([&]{provider->read_subchannel(0);},"decode failed");
    bytes[16]=0;bytes.resize(4096+2448);
    provider=pce::open_sector_provider(files.write("truncated.chd",bytes),library);
    refuses([&]{provider->read_subchannel(0);},"decode failed");
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=2)throw std::runtime_error("Subchannel provider tests require authored decoder ABI double");
        Files files;absence(files,argv[1]);mapping(files,argv[1]);pregaps(files,argv[1]);malformed(files,argv[1]);decode_failure(files,argv[1]);
        std::cout<<"captured-subchannel-provider: "<<checks<<" authored checks (original PW, MODE1/raw offsets, gaps, decoder/source failures)\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
