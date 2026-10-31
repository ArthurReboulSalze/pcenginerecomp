// Authored direct-device and autonomous guest probes; separate evidence domains.
#define main prior_authored_tool_sense_main
#include "sense_oracle_probe.cpp"
#undef main
#include "cd_unknown_probe_support.hpp"
struct UnknownAdapter:Adapter {
    pce::CdUnknownPolicy policy;
    UnknownAdapter(const std::vector<std::uint8_t>& rom,pce::CdUnknownPolicy p):Adapter{nullptr,{},rom},policy(p){}
    void reset(unsigned mode){Adapter::reset(mode);bus->cd.unknown_policy=policy;}
    unsigned buffered()const{return bus->cd.scsi.command_size;}
};
int main(int argc,char** argv) {
    try {
        if(argc!=4&&argc!=6)throw std::runtime_error("usage: cd-unknown-probe PLAN AUTHORED_ROM nec-invalid|gear-good [--capture NEW]");
        const std::string profile=argv[3];if(profile!="nec-invalid"&&profile!="gear-good")throw std::runtime_error("unknown response profile");
        const auto rom=reset_probe::rom(argv[2]);std::ifstream plan(argv[1]);if(!plan)throw std::runtime_error("missing plan");
        UnknownAdapter a(rom,profile=="nec-invalid"?pce::CdUnknownPolicy::nec_invalid:pce::CdUnknownPolicy::gear_good);
        std::unique_ptr<pce::CodeCapture> capture;if(argc==6){if(std::string(argv[4])!="--capture")throw std::runtime_error("capture option");capture=std::make_unique<pce::CodeCapture>(argv[5],65536);}
        std::string op;bool first=true;std::cout<<'[';
        while(plan>>op) {
            if(cd_unknown_probe::operation(a,plan,op,first))continue;
            if(op=="k"){unsigned offset;if(!(plan>>offset)||offset>8191)throw std::runtime_error("RAM bound");reset_probe::record(first,"ram",{offset,(*a.bus->bytes)[(0xF8<<13)|offset]});continue;}
            if(op=="g") {
                unsigned end;if(!(plan>>end)||end<0xE100||end>0xFF00)throw std::runtime_error("guest bound");unsigned retired=0;
                do {
                    if(++retired>200000)throw std::runtime_error("authored guest instruction bound");pce::CodeCapture::Pending pending;if(capture)pending=capture->before(*a.bus,a.cpu);
#ifdef PCE_CD_UNKNOWN_NATIVE_ONLY
                    if(pce::generated_step(*a.bus,a.cpu,100000000)!=pce::Exit::executed)throw std::runtime_error("native miss; fallback forbidden");
#else
                    if(pce::interpret_step(*a.bus,a.cpu,100000000)!=pce::Exit::executed)throw std::runtime_error("interpreter refused");
#endif
                    if(capture)capture->after(pending,a.cpu);
                }while(a.cpu.pc!=end);
                std::vector<std::uint64_t> state{a.cpu.pc,a.cpu.a,a.cpu.x,a.cpu.y,a.cpu.sp,a.cpu.p,a.cpu.clock_divisor,a.cpu.ticks};
                for(auto m:a.cpu.mpr)state.push_back(m);state.push_back(retired);state.push_back(a.bus->cd.sense_commands);state.push_back(a.bus->cd.sense_errors);state.push_back(a.bus->cd.invalid_commands);state.push_back(a.bus->cd.unknown_commands);reset_probe::record(first,"guest",state);continue;
            }
            throw std::runtime_error("unknown operation");
        }
        std::cout<<"]\n";if(capture)capture->finish();return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
