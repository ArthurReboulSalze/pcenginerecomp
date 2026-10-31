// Authored adapter; no third-party source body is copied into this repository.
#define main prior_authored_beetle_sense_main
#define Adapter PriorBeetleAdapter
#include "beetle_sense_probe.cpp"
#undef Adapter
#undef main
#include "cd_unknown_probe_support.hpp"
struct Adapter:PriorBeetleAdapter {unsigned buffered()const{return cd.command_buffer_pos;}};
int main(int argc,char** argv) {
    try {
        if(argc!=2)throw std::runtime_error("usage: beetle-unknown PLAN");
        std::ifstream plan(argv[1]);if(!plan)throw std::runtime_error("missing plan");
        Adapter a;std::string op;bool first=true;std::cout<<'[';
        while(plan>>op)if(!cd_unknown_probe::operation(a,plan,op,first))throw std::runtime_error("unknown operation");
        std::cout<<"]\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
