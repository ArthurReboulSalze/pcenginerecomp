#pragma once
// Authored protocol/observation helpers. No emulated operations live here.
#include "reset_probe_support.hpp"
#include <sstream>
namespace queue_probe {
inline std::uint16_t pattern(unsigned i){return static_cast<std::uint16_t>((i*73)^(i>>3)^0xA53C);}
struct Phase {unsigned hclock,vstate,hstate,burst,mode,control,sprites,start,end,hsync;};
template<class Adapter> void execute(Adapter& a,const char* plan) {
    std::ifstream input(plan);if(!input)throw std::runtime_error("plan open");
    bool first=true;std::cout<<'[';char op;
    while(input>>op){unsigned x=0,y=0;
        switch(op){
        case 'r': input>>x>>y;a.reset(x,y);break;
        case 'f': {Phase p{};input>>p.hclock>>p.vstate>>p.hstate>>p.burst>>p.mode>>p.control>>p.sprites>>p.start>>p.end>>p.hsync;a.phase(p);break;}
        case 'w': input>>x>>y;a.write(x,y);break;
        case 'p': input>>x;reset_probe::record(first,"byte",{x,a.read(x)});break;
        case 'k': input>>x;a.service(x);break;
        case 'a': input>>x;a.advance(x);break;
        case 'j': input>>x;reset_probe::record(first,"slot",{a.slot(x)});break;
        case 's': reset_probe::record(first,"device",a.device());break;
        case 'm': reset_probe::record(first,"ram",a.ram());break;
        case 't': input>>x>>y;a.seed(x,y);break;
        case 'q': input>>x;a.queue(x);break;
        case 'x': input>>x;a.cpu_entry(x);break;
        case 'g': a.pending_guards();reset_probe::record(first,"guard-window",a.device());break;
        case 'i': input>>x;while(x--){a.instruction();reset_probe::record(first,"cpu",a.cpu());reset_probe::record(first,"device",a.device());}break;
        default:throw std::runtime_error("unknown queue fixture operation");
        }
        if(!input)throw std::runtime_error("truncated queue fixture operation");
    }
    std::cout<<"]\n";
}
}
