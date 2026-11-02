// Authored device-level adapter matching the independent original-core plan.
#include "pce/runtime.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <memory>
struct Medium final:pce::SectorProvider {
    pce::CdToc table{};pce::SubchannelSector raw{};
    Medium(){table.track_count=1;table.tracks[0]={0,4};table.leadout_lba=2;}
    pce::Sector read(std::uint32_t)override{return {};}
    bool has_subchannel()const override{return true;}
    std::optional<pce::SubchannelSector> read_subchannel(std::uint32_t)override{return raw;}
    const pce::CdToc&toc()const override{return table;}
};
template<class T> void values(const T&v){for(auto b:v)std::cout<<','<<unsigned(b);}
int main(int argc,char**argv) {
    try {
        if(argc!=2)throw std::runtime_error("usage: toolkit-subchannel PLAN");
        std::ifstream in(argv[1]);if(!in)throw std::runtime_error("missing plan");
        auto medium=std::make_shared<Medium>();auto cd=std::make_unique<pce::CdControl>();
        auto reset=[&]{cd=std::make_unique<pce::CdControl>();cd->enabled=cd->scsi.enabled=true;
            cd->set_sector_provider(medium);cd->set_subchannel_profile(pce::CdSubchannelProfile::captured_q);};
        reset();std::string op;bool first=true;std::cout<<'[';
        while(in>>op) {
            if(op=="r"){reset();continue;}
            if(op!="q")throw std::runtime_error("unknown authored operation");
            unsigned status;if(!(in>>status)||status>2)throw std::runtime_error("status bound");
            for(auto&b:medium->raw){unsigned v;if(!(in>>v)||v>255)throw std::runtime_error("raw96 extent");b=v;}
            std::array<std::uint8_t,12> decoded{};
            for(unsigned i=0;i<96;++i)decoded[i/8]|=((medium->raw[i]>>6)&1)<<(7-i%8);
            cd->sample_subchannel(0);cd->audio.state=status==0?3:status==1?2:0;
            cd->scsi.command.fill(0);cd->scsi.command[0]=0xDD;cd->audio_command();
            if(cd->scsi.response_size!=10)throw std::runtime_error("DD extent");
            std::array<std::uint8_t,10> response{};std::copy_n(cd->scsi.response.begin(),10,response.begin());
            if(!first)std::cout<<',';first=false;std::cout<<'['<<int(pce::cd_subq_crc_valid(decoded));
            values(decoded);values(cd->subchannel.last);values(cd->subchannel.position);values(response);std::cout<<']';
        }
        std::cout<<"]\n";return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
