// Authored adapter; the unmodified GPL reference TU stays a private input.
// No reference implementation is embedded here or linked to the toolkit.
#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#define private public
#include "cdrom_mmi_image.h"
#undef private
#include "cdrom_mmi_image.cpp"
bool g_mcp_stdio_mode=false;
int main(int argc,char**argv) {
    try {
        if(argc!=2)throw std::runtime_error("usage: gear-subchannel PLAN");
        std::ifstream in(argv[1]);if(!in)throw std::runtime_error("missing plan");
        std::string op;bool first=true;std::cout<<'[';
        while(in>>op) {
            if(op=="r")continue;
            if(op!="q")throw std::runtime_error("unknown authored operation");
            unsigned status; if(!(in>>status)||status>2)throw std::runtime_error("status bound");
            std::array<u8,96> raw{};for(auto&b:raw){unsigned v;if(!(in>>v)||v>255)throw std::runtime_error("raw96 extent");b=v;}
            std::array<u8,12> q{};const bool valid=CdRomMmiImage::DecodeSubchannelQ(raw.data(),q.data());
            if(!first)std::cout<<',';first=false;std::cout<<'['<<int(valid);
            if(valid)for(auto b:q)std::cout<<','<<unsigned(b);
            std::cout<<']';
        }
        std::cout<<"]\n";return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
