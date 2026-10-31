// Authored adapter; the original Gear device implementation is separately compiled.
#define main prior_authored_gear_sense_main
#include "geargrafx_sense_probe.cpp"
#undef main
#include "cd_unknown_probe_support.hpp"
int main(int argc,char** argv) {
    try {
        if(argc!=4)throw std::runtime_error("usage: gear-unknown PLAN AUTHORED_ROM AUTHORED_CUE");
        const auto rom=reset_probe::rom(argv[2]);std::ifstream plan(argv[1]);if(!plan)throw std::runtime_error("missing plan");
        Adapter a{nullptr,rom,argv[3]};std::string op;bool first=true;std::cout<<'[';
        while(plan>>op)if(!cd_unknown_probe::operation(a,plan,op,first))throw std::runtime_error("unknown operation");
        std::cout<<"]\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
