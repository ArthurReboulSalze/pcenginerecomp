#include "pce/sector.hpp"
#include "sector_internal.hpp"

#include <algorithm>
#include <bit>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <vector>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace pce {
namespace {
namespace fs = std::filesystem;
constexpr std::uint64_t max_file_bytes = 8ULL*1024*1024*1024;
fs::path path_of(const std::string& text) {
    return fs::path(std::u8string(reinterpret_cast<const char8_t*>(text.data()),text.size()));
}
struct Stamp {
    std::uintmax_t size;
    fs::file_time_type time;
    bool operator==(const Stamp&) const = default;
};
Stamp stamp(const fs::path& path) {
    std::error_code error;
    if (!fs::is_regular_file(path,error) || error) throw Fault("Sector image must be a regular file");
    auto size=fs::file_size(path,error);
    if(error || size>max_file_bytes) throw Fault("Sector image size exceeds supported bound");
    auto time=fs::last_write_time(path,error);
    if(error) throw Fault("Cannot inspect sector image timestamp");
    return {size,time};
}
void same(const fs::path& path,const Stamp& initial) {
    if(!(stamp(path)==initial)) throw Fault("Sector image changed after identity verification");
}
void exact(std::ifstream& input,std::uint64_t offset,void* bytes,std::size_t size) {
    input.clear();
    input.seekg(static_cast<std::streamoff>(offset));
    input.read(static_cast<char*>(bytes),static_cast<std::streamsize>(size));
    if(!input || static_cast<std::size_t>(input.gcount())!=size) throw Fault("Short sector image read");
}
std::uint32_t be32(const std::uint8_t* p) {
    return (std::uint32_t(p[0])<<24)|(std::uint32_t(p[1])<<16)|(std::uint32_t(p[2])<<8)|p[3];
}
std::uint64_t be64(const std::uint8_t* p) { return (std::uint64_t(be32(p))<<32)|be32(p+4); }

// SHA-256 compression and padding specified by FIPS 180-4. Constant memory,
// authored here rather than depending on a platform cryptography installation.
class Sha256 {
    std::array<std::uint32_t,8> h{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    std::array<std::uint8_t,64> block{};
    std::uint64_t count=0;
    unsigned used=0;
    void compress() {
        constexpr std::uint32_t k[]={
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        std::array<std::uint32_t,64> w{};
        for(unsigned i=0;i<16;++i) w[i]=be32(block.data()+4*i);
        for(unsigned i=16;i<64;++i) {
            auto a=w[i-15],b=w[i-2];
            w[i]=w[i-16]+(std::rotr(a,7)^std::rotr(a,18)^(a>>3))+w[i-7]
                +(std::rotr(b,17)^std::rotr(b,19)^(b>>10));
        }
        auto a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],j=h[7];
        for(unsigned i=0;i<64;++i) {
            auto t1=j+(std::rotr(e,6)^std::rotr(e,11)^std::rotr(e,25))+((e&f)^(~e&g))+k[i]+w[i];
            auto t2=(std::rotr(a,2)^std::rotr(a,13)^std::rotr(a,22))+((a&b)^(a&c)^(b&c));
            j=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=j;
    }
public:
    void add(const std::uint8_t* bytes,std::size_t size) {
        count+=size;
        while(size) {
            auto n=std::min<std::size_t>(size,64-used);
            std::copy_n(bytes,n,block.data()+used);bytes+=n;size-=n;used+=static_cast<unsigned>(n);
            if(used==64) {compress();used=0;}
        }
    }
    std::string finish() {
        auto bits=count*8;
        const std::uint8_t one=0x80,zero=0;
        add(&one,1);
        while(used!=56) add(&zero,1);
        std::array<std::uint8_t,8> length{};
        for(unsigned i=0;i<8;++i) length[7-i]=static_cast<std::uint8_t>(bits>>(8*i));
        add(length.data(),8);
        constexpr char digits[]="0123456789abcdef";
        std::string text; text.reserve(64);
        for(auto value:h) for(int shift=28;shift>=0;shift-=4) text+=digits[(value>>shift)&15];
        return text;
    }
};

class ImageProvider final : public SectorProvider {
    enum class Subtype { none, raw, cooked };
    struct Track {
        std::uint32_t start,count;
        std::uint64_t frame;
        bool raw,audio;
        std::uint32_t stored_pregap=0;
        Subtype sub=Subtype::none,pgsub=Subtype::none;
        unsigned pregap_data_bytes=0;
    };
    fs::path path;
    Stamp initial;
    std::ifstream input;
    CdToc table;
    std::vector<Track> tracks;
    std::uint32_t hunk_bytes=0,cached_hunk=std::numeric_limits<std::uint32_t>::max();
    std::vector<std::uint8_t> cache;
    struct Decoder {
#ifdef _WIN32
        HMODULE library=nullptr;
#else
        void* library=nullptr;
#endif
        void* handle=nullptr;
        int (*open)(const char*,int,void*,void**)=nullptr;
        int (*read)(void*,std::uint32_t,void*)=nullptr;
        void (*close)(void*)=nullptr;
        ~Decoder() {
            if(handle && close) close(handle);
#ifdef _WIN32
            if(library) FreeLibrary(library);
#else
            if(library) dlclose(library);
#endif
        }
        void* symbol(const char* name) {
#ifdef _WIN32
            return reinterpret_cast<void*>(GetProcAddress(library,name));
#else
            return dlsym(library,name);
#endif
        }
        void load(const std::string& selected,const std::string& image) {
            if(selected.empty()) throw Fault("CHD sectors require an explicit libchdr shared library path");
            auto absolute=fs::absolute(path_of(selected));
#ifdef _WIN32
            library=LoadLibraryExW(absolute.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
#else
            library=dlopen(absolute.c_str(),RTLD_NOW|RTLD_LOCAL);
#endif
            if(!library) throw Fault("Cannot load selected libchdr shared library");
            open=reinterpret_cast<decltype(open)>(symbol("chd_open"));
            read=reinterpret_cast<decltype(read)>(symbol("chd_read"));
            close=reinterpret_cast<decltype(close)>(symbol("chd_close"));
            if(!open || !read || !close) throw Fault("Selected library lacks required libchdr symbols");
            if(open(image.c_str(),1,nullptr,&handle)!=0 || !handle) throw Fault("libchdr refused read-only CHD open");
        }
    } decoder;

    static std::uint32_t number(const std::string& text) {
        if(text.empty() || text.size()>10) throw Fault("Invalid CHD track numeric metadata");
        std::uint64_t value=0;
        for(char c:text) {if(c<'0'||c>'9') throw Fault("Invalid CHD track numeric metadata");value=value*10+unsigned(c-'0');}
        if(value>449850) throw Fault("CHD track metadata exceeds CD geometry bound");
        return static_cast<std::uint32_t>(value);
    }
    static Subtype subtype(const std::string& text) {
        if(text=="NONE") return Subtype::none;
        if(text=="RW_RAW") return Subtype::raw;
        if(text=="RW") return Subtype::cooked;
        throw Fault("Unsupported CHD subchannel metadata representation");
    }
    void chd_metadata() {
        std::array<std::uint8_t,124> header{};
        exact(input,0,header.data(),header.size());
        if(!std::equal(header.begin(),header.begin()+8,reinterpret_cast<const std::uint8_t*>("MComprHD"))
            || be32(header.data()+8)!=124 || be32(header.data()+12)!=5)
            throw Fault("Sector provider requires complete CHDv5 header");
        if(std::any_of(header.begin()+104,header.end(),[](auto x){return x!=0;})) throw Fault("Parent CHDs are unsupported");
        auto logical=be64(header.data()+32),offset=be64(header.data()+48);
        hunk_bytes=be32(header.data()+56);
        if(!hunk_bytes || hunk_bytes>524288 || hunk_bytes%2448 || be32(header.data()+60)!=2448 || !logical || logical%2448)
            throw Fault("Unsupported CHD CD hunk/unit geometry");
        std::set<std::uint64_t> seen;
        std::uint64_t storage=0,disc=0,metadata_bytes=0;
        while(offset) {
            if(offset<124 || initial.size<16 || offset>initial.size-16 || seen.size()>=1024 || !seen.insert(offset).second)
                throw Fault("Invalid, excessive or cyclic CHD metadata");
            std::array<std::uint8_t,16> record{};exact(input,offset,record.data(),record.size());
            auto length=be32(record.data()+4)&0xffffff;
            metadata_bytes+=length;
            if(length>65536 || metadata_bytes>1024*1024 || length>initial.size-offset-16) throw Fault("CHD metadata exceeds bounds");
            std::string tag(reinterpret_cast<const char*>(record.data()),4);
            if(tag=="CHT2" || tag=="CHTR") {
                std::string text(length,'\0');exact(input,offset+16,text.data(),text.size());
                auto nul=text.find('\0');if(nul!=std::string::npos) text.resize(nul);
                std::istringstream fields(text);std::string token;
                std::map<std::string,std::string> values;
                while(fields>>token) {
                    auto colon=token.find(':');
                    if(colon==std::string::npos || !colon || colon+1==token.size() || !values.emplace(token.substr(0,colon),token.substr(colon+1)).second)
                        throw Fault("Malformed CHD track metadata");
                }
                if(!values.contains("TRACK") || !values.contains("FRAMES") || !values.contains("TYPE")) throw Fault("Missing CHD track metadata");
                auto frames=number(values["FRAMES"]),pregap=number(values.contains("PREGAP")?values["PREGAP"]:"0");
                auto postgap=number(values.contains("POSTGAP")?values["POSTGAP"]:"0");
                bool stored=values.contains("PGTYPE") && values["PGTYPE"].starts_with("V");
                auto type=values["TYPE"];
                const auto sub=subtype(values.contains("SUBTYPE")?values["SUBTYPE"]:"NONE");
                const auto pgsub=subtype(values.contains("PGSUB")?values["PGSUB"]:"NONE");
                unsigned pregap_data_bytes=0;
                if(stored && pregap && pgsub!=Subtype::none) {
                    const auto pgtype=values["PGTYPE"].substr(1);
                    if(pgtype=="MODE1") pregap_data_bytes=2048;
                    else if(pgtype=="MODE1_RAW" || pgtype=="AUDIO") pregap_data_bytes=2352;
                    else throw Fault("Captured CHD pregap requires a supported explicit PGTYPE");
                    // CHDMAN's stored-frame writer and MAME read_subcode use
                    // the program track payload size for the whole extent.
                    // A differing pregap size has no qualified byte layout.
                    if(pregap_data_bytes!=(type=="MODE1"?2048U:2352U))
                        throw Fault("Captured CHD pregap payload size differs from program track");
                }
                if(tracks.size()>=99 || number(values["TRACK"])!=tracks.size()+1 || !frames || (stored && pregap>=frames)
                    || (type!="MODE1" && type!="MODE1_RAW" && type!="AUDIO")) throw Fault("Unsupported CHD track geometry or format");
                auto start=disc+pregap;
                auto count=frames-(stored?pregap:0);
                if(start+count>449850) throw Fault("CHD disc geometry exceeds supported bound");
                tracks.push_back({static_cast<std::uint32_t>(start),count,storage+(stored?pregap:0),type=="MODE1_RAW",type=="AUDIO",
                                  stored ? pregap:0,sub,pgsub,pregap_data_bytes});
                table.tracks[table.track_count++]={static_cast<std::uint32_t>(start),static_cast<std::uint8_t>(type=="AUDIO"?0:4)};
                storage+=(std::uint64_t(frames)+3)/4*4;
                disc+=frames+postgap+(stored?0:pregap);
            } else if(tag=="CHCD" || tag=="CHGT" || tag=="CHGD") throw Fault("Legacy/GD-ROM CHD metadata is unsupported");
            offset=be64(record.data()+8);
        }
        if(tracks.empty() || storage*2448!=logical) throw Fault("CHD track metadata disagrees with logical size");
        table.leadout_lba=tracks.back().start+tracks.back().count;
        cache.resize(hunk_bytes);
    }
public:
    ImageProvider(const std::string& image,const std::string& library)
        :path(path_of(image)),initial(stamp(path)),input(path,std::ios::binary) {
        if(!input) throw Fault("Cannot open read-only sector image");
        auto extension=path.extension().string();
        std::transform(extension.begin(),extension.end(),extension.begin(),[](unsigned char c){return char(std::tolower(c));});
        if(extension==".iso") {
            if(!initial.size || initial.size%2048 || initial.size/2048>449849) throw Fault("ISO requires bounded complete 2048-byte sectors");
            table.track_count=1;table.leadout_lba=static_cast<std::uint32_t>(initial.size/2048);
            table.tracks[0]={0,4};
        } else if(extension==".chd") chd_metadata();
        else throw Fault("Sector provider accepts ISO or CHD images only");
        table.validate();
        table.image_sha256=image_sha256(image);
        same(path,initial);
        if(hunk_bytes) decoder.load(library,image);
        same(path,initial);
    }
    const CdToc& toc() const override {return table;}
    bool has_subchannel() const override {
        same(path,initial);
        const bool result=std::any_of(tracks.begin(),tracks.end(),[](const auto& track){
            return track.sub==Subtype::raw || (track.stored_pregap && track.pgsub==Subtype::raw);
        });
        same(path,initial);return result;
    }
    std::optional<SubchannelSector> read_subchannel(std::uint32_t lba) override {
        same(path,initial);
        if(!hunk_bytes || lba>=table.leadout_lba) return std::nullopt;
        for(const auto& track:tracks) {
            const bool program=lba>=track.start && lba-track.start<track.count;
            const bool pregap=lba<track.start && track.start-lba<=track.stored_pregap;
            if(!program && !pregap) continue;
            const auto representation=program?track.sub:track.pgsub;
            if(representation==Subtype::none) {same(path,initial);return std::nullopt;}
            // Cooked R-W does not establish original P/Q or raw symbol order.
            // Preserve data/audio compatibility but refuse this opt-in access.
            if(representation!=Subtype::raw) throw Fault("Cooked CHD RW subchannels are unsupported; original RW_RAW P-W is required");
            const auto frame=program?track.frame+(lba-track.start):track.frame-(track.start-lba);
            const auto position=frame*2448;
            const auto hunk=static_cast<std::uint32_t>(position/hunk_bytes);
            const auto within=static_cast<std::size_t>(position%hunk_bytes);
            if(cached_hunk!=hunk) {
                // A failed decoder can partially overwrite the previous hunk.
                cached_hunk=std::numeric_limits<std::uint32_t>::max();
                if(decoder.read(decoder.handle,hunk,cache.data())!=0) throw Fault("libchdr subchannel hunk decode failed");
                cached_hunk=hunk;
            }
            // CHDMAN appends subcode directly after the declared payload, then
            // pads the whole unit to 2448; MODE1 subcode starts at 2048.
            const auto offset=program?(track.raw||track.audio?2352U:2048U):track.pregap_data_bytes;
            SubchannelSector result{};
            std::copy_n(cache.data()+within+offset,result.size(),result.begin());
            same(path,initial);return result;
        }
        same(path,initial);return std::nullopt;
    }
    ProgramTrackLookup program_track(std::uint32_t lba) const override {
        same(path,initial);
        ProgramTrackLookup result{true,{}};
        if(lba<table.leadout_lba) {
            if(!hunk_bytes) result.index=0;
            else for(unsigned i=0;i<tracks.size();++i) {
                const auto& track=tracks[i];
                if(lba>=track.start && lba-track.start<track.count) {result.index=i;break;}
            }
        }
        same(path,initial);return result;
    }
    bool audio_playable(std::uint32_t lba) const override {
        same(path,initial);
        if(!hunk_bytes || lba>=table.leadout_lba) return false;
        for(std::size_t i=0;i<tracks.size();++i) {
            const auto& track=tracks[i];
            if(lba>=track.start && lba-track.start<track.count) return track.audio;
            if(lba<track.start && track.start-lba<=track.stored_pregap)
                return track.audio && i>0 && tracks[i-1].audio;
        }
        return false;
    }
    AudioSector read_audio(std::uint32_t lba) override {
        same(path,initial);
        if(!hunk_bytes) throw Fault("ISO data sectors cannot be read as audio");
        auto it=std::find_if(tracks.begin(),tracks.end(),[lba](const auto& t){
            return (lba>=t.start && lba-t.start<t.count) ||
                   (t.audio && lba<t.start && t.start-lba<=t.stored_pregap);
        });
        if(it==tracks.end()) throw Fault("Audio LBA falls in CHD gap or outside disc");
        if(lba>=it->start && !it->audio) throw Fault("MODE1 data sectors cannot be read as audio");
        const auto frame_number=lba>=it->start ? it->frame+(lba-it->start) : it->frame-(it->start-lba);
        const auto position=frame_number*2448;
        const auto hunk=static_cast<std::uint32_t>(position/hunk_bytes);
        const auto within=static_cast<std::size_t>(position%hunk_bytes);
        if(cached_hunk!=hunk) {
            // A decoder may partially overwrite its destination on failure.
            // Never leave that storage tagged as a previously valid hunk.
            cached_hunk=std::numeric_limits<std::uint32_t>::max();
            if(decoder.read(decoder.handle,hunk,cache.data())!=0) throw Fault("libchdr audio hunk decode failed");
            cached_hunk=hunk;
        }
        AudioSector samples{};
        // CHD CD-DA payload is big-endian, including libchdr's decoded CD
        // FLAC hunks. Explicit conversion avoids host-endian assumptions.
        for(unsigned i=0;i<samples.size();++i) {
            const unsigned value=(unsigned(cache[within+2*i])<<8)|cache[within+2*i+1];
            samples[i]=static_cast<std::int16_t>(value<32768 ? int(value):int(value)-65536);
        }
        same(path,initial);
        return samples;
    }
    Sector read(std::uint32_t lba) override {
        same(path,initial);
        Sector sector{};
        try {
            if(!hunk_bytes) {
                if(lba>=table.leadout_lba) throw SectorReadError(SectorReadReason::out_of_range,lba,"Sector LBA outside ISO");
                exact(input,std::uint64_t(lba)*2048,sector.data(),sector.size());
            } else {
                if(lba>=table.leadout_lba) throw SectorReadError(SectorReadReason::out_of_range,lba,"Sector LBA falls in CHD gap or outside disc");
                auto it=std::find_if(tracks.begin(),tracks.end(),[lba](const auto& t){return lba>=t.start && lba-t.start<t.count;});
                if(it==tracks.end()) throw SectorReadError(SectorReadReason::unrecoverable_data,lba,"Sector LBA falls in CHD gap or outside disc");
                if(it->audio) throw SectorReadError(SectorReadReason::wrong_data_track,lba,"Audio sectors cannot be read as MODE1 user data");
                auto position=(it->frame+lba-it->start)*2448;
                auto hunk=static_cast<std::uint32_t>(position/hunk_bytes);
                auto within=static_cast<std::size_t>(position%hunk_bytes);
                if(cached_hunk!=hunk) {
                    cached_hunk=std::numeric_limits<std::uint32_t>::max();
                    if(decoder.read(decoder.handle,hunk,cache.data())!=0) throw Fault("libchdr sector hunk decode failed");
                    cached_hunk=hunk;
                }
                auto frame=cache.data()+within;
                if(it->raw) {
                    if(frame[0]!=0 || frame[11]!=0 || frame[15]!=1 || !std::all_of(frame+1,frame+11,[](auto c){return c==255;}))
                        throw SectorReadError(SectorReadReason::media_data_error,lba,"Invalid CHD MODE1 raw sector header");
                    frame+=16;
                }
                std::copy_n(frame,sector.size(),sector.begin());
            }
        } catch(const SectorReadError&) {
            // Identity drift is fatal even when the requested sector itself
            // would otherwise be a recoverable guest-visible media failure.
            same(path,initial);throw;
        }
        same(path,initial);
        return sector;
    }
};
} // namespace

std::string detail::file_sha256(const std::string& image) {
    auto path=path_of(image);auto initial=stamp(path);
    std::ifstream input(path,std::ios::binary);if(!input) throw Fault("Cannot hash sector image");
    Sha256 hash;std::array<std::uint8_t,65536> buffer{};
    std::uint64_t remaining=initial.size;
    while(remaining) {
        auto count=static_cast<std::size_t>(std::min<std::uint64_t>(remaining,buffer.size()));
        input.read(reinterpret_cast<char*>(buffer.data()),static_cast<std::streamsize>(count));
        if(static_cast<std::size_t>(input.gcount())!=count) throw Fault("Short sector image hash read");
        hash.add(buffer.data(),count);remaining-=count;
    }
    same(path,initial);return hash.finish();
}
std::string detail::text_sha256(std::string_view bytes) {
    Sha256 hash;
    hash.add(reinterpret_cast<const std::uint8_t*>(bytes.data()),bytes.size());
    return hash.finish();
}
std::string image_sha256(const std::string& image) {
    auto extension=path_of(image).extension().string();
    std::transform(extension.begin(),extension.end(),extension.begin(),[](unsigned char c){return char(std::tolower(c));});
    return extension==".cue" ? detail::cue_sha256(image):detail::file_sha256(image);
}
std::shared_ptr<SectorProvider> open_sector_provider(const std::string& image,const std::string& libchdr) {
    auto extension=path_of(image).extension().string();
    std::transform(extension.begin(),extension.end(),extension.begin(),[](unsigned char c){return char(std::tolower(c));});
    if(extension==".cue") return detail::open_cue_provider(image);
    return std::make_shared<ImageProvider>(image,libchdr);
}
} // namespace pce
