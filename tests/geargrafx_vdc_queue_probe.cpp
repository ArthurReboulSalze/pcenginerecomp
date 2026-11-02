// Authored adapter around the original Gear CPU, queue and scheduler bodies.
#include "geargrafx_core.h"
#include "huc6280.h"
#include "huc6270.h"
#include "huc6260.h"
#include "media.h"
#include "memory.h"
#include "vdc_queue_probe_support.hpp"
#include <memory>
bool g_mcp_stdio_mode=true;
template<class T,typename T::type M>struct Access{friend typename T::type member(T){return M;}};
#define FIELD(N,T,F) struct N{using type=T HuC6270::*;friend type member(N);};template struct Access<N,&HuC6270::F>;
#define METHOD(N,T,F) struct N{using type=T;friend type member(N);};template struct Access<N,&HuC6270::F>;
FIELD(ReadPending,bool,m_pending_memory_read) FIELD(WritePending,bool,m_pending_memory_write)
FIELD(Delay,s32,m_transfer_delay) FIELD(Carry,u32,m_cpu_vram_cycles) FIELD(Latch,u16,m_vram_openbus)
FIELD(BgStart,s32,m_load_bg_start_clock) FIELD(BgEnd,s32,m_load_bg_end_clock) FIELD(Hsync,s32,m_hsync_start_clock)
FIELD(Burst,bool,m_burst_mode) FIELD(Mode,u16,m_latched_mwr) FIELD(Control,u16,m_latched_cr) FIELD(Sprites,int,m_sprite_count)
FIELD(SatPending,u16,m_sat_transfer_pending) FIELD(VramPending,u32,m_vram_transfer_pending)
METHOD(Slot,bool(HuC6270::*)(s32),IsCpuVramSlotAvailable)
METHOD(QueueRead,void(HuC6270::*)(),QueueMemoryRead) METHOD(QueueWrite,void(HuC6270::*)(),QueueMemoryWrite)
struct Transfer{using type=u32 HuC6280::*;friend type member(Transfer);};template struct Access<Transfer,&HuC6280::m_transfer_state>;
struct Clock{using type=bool(GeargrafxCore::*)(u32);friend type member(Clock);};template struct Access<Clock,&GeargrafxCore::ClockHardware<false,false,false>>;
static void clock_cpu(void* context,u32 ticks){auto* c=static_cast<GeargrafxCore*>(context);(c->*member(Clock{}))(ticks);}
struct Adapter {
    std::unique_ptr<GeargrafxCore> core;const std::vector<std::uint8_t>& rom;
    HuC6270& v()const{return *core->GetHuC6270_1();}
    void reset(unsigned fast,unsigned divider){core=std::make_unique<GeargrafxCore>();core->Init(nullptr);core->GetMedia()->SetConsoleType(GG_CONSOLE_PCE);core->GetHuC6280()->SetResetValue(0);core->GetMemory()->SetResetValues(0,0,0,0);core->GetHuC6260()->SetResetValue(0);v().SetSafeDefaults(false);if(!core->LoadHuCardFromBuffer(rom.data(),rom.size(),"authored-queue.pce"))throw std::runtime_error("ROM load");*core->GetHuC6280()->GetState()->SPEED=fast?1:0;core->GetHuC6280()->SetHardwareClock(clock_cpu,core.get());core->GetHuC6260()->WriteRegister(0,divider);for(unsigned i=0;i<32768;++i)v().GetVRAM()[i]=queue_probe::pattern(i);v().WriteRegister(0,1);v().WriteRegister(2,0);v().WriteRegister(3,0);clock_cpu(core.get(),48);v().WriteRegister(0,0);if(v().*member(ReadPending{}))throw std::runtime_error("authored initial prefetch did not complete");}
    void phase(const queue_probe::Phase& p){auto* s=v().GetState();*core->GetHuC6260()->GetState()->HPOS=p.hclock;*s->V_STATE=p.vstate;*s->H_STATE=p.hstate;*s->VPOS=20;v().*member(Burst{})=p.burst!=0;v().*member(Mode{})=p.mode;v().*member(Control{})=p.control;v().*member(Sprites{})=p.sprites;v().*member(BgStart{})=p.start;v().*member(BgEnd{})=p.end;v().*member(Hsync{})=p.hsync;}
    void write(unsigned p,unsigned value){v().WriteRegister(p,value);}
    unsigned read(unsigned p){return v().ReadRegister(p);}
    void queue(unsigned type){if(type&1)(v().*member(QueueRead{}))();if(type&2)(v().*member(QueueWrite{}))();}
    void service(unsigned ticks){v().ProcessCpuVramAccesses(ticks);}
    void advance(unsigned ticks){clock_cpu(core.get(),ticks);}
    unsigned slot(unsigned elapsed){return (v().*member(Slot{}))(elapsed);}
    void cpu_entry(unsigned address){core->GetHuC6280()->GetState()->PC->SetValue(address);core->GetMemory()->SetMpr(0,255);core->GetMemory()->SetMpr(1,248);core->GetMemory()->SetMpr(2,255);}
    void pending_guards(){if(!(v().*member(VramPending{})) || !((v().*member(ReadPending{}))||(v().*member(WritePending{}))))throw std::runtime_error("guest race must retain genuine DMA-held CPU work");}
    void seed(unsigned address,unsigned value){v().GetVRAM()[address]=static_cast<u16>(value);}
    std::vector<std::uint64_t> device()const{auto* s=v().GetState();std::vector<std::uint64_t> out{core->GetMasterClockCycles(),unsigned(*core->GetHuC6260()->GetState()->HPOS),unsigned(*s->VPOS),unsigned(*s->V_STATE),unsigned(*s->H_STATE),v().*member(ReadPending{}),v().*member(WritePending{}),static_cast<unsigned>(v().*member(Delay{})),v().*member(Carry{}),unsigned(*s->SR),*s->READ_BUFFER,v().*member(Latch{}),*s->AR,v().*member(SatPending{}),v().*member(VramPending{})};for(unsigned i=0;i<20;++i)out.push_back(s->R[i]);out.push_back(reset_probe::hash(v().GetVRAM(),32768));out.push_back(reset_probe::hash(v().GetSAT(),256));return out;}
    std::vector<std::uint64_t> cpu()const{auto* s=core->GetHuC6280()->GetState();std::vector<std::uint64_t> out{s->PC->GetValue(),s->A->GetValue(),s->X->GetValue(),s->Y->GetValue(),s->S->GetValue(),s->P->GetValue(),*s->SPEED?3U:12U,core->GetMasterClockCycles()};for(unsigned i=0;i<8;++i)out.push_back(core->GetMemory()->GetMpr(i));return out;}
    std::vector<std::uint64_t> ram()const{auto* p=core->GetMemory()->GetWorkingRAM();return {p,p+64};}
    void instruction(){auto* c=core->GetHuC6280();do{auto ticks=c->RunInstruction(),done=c->GetClockedMasterCycles();if(ticks>done)clock_cpu(core.get(),ticks-done);}while(c->*member(Transfer{}));}
};
int main(int argc,char** argv){try{if(argc!=3)throw std::runtime_error("usage: gear-queue PLAN AUTHORED_ROM");auto rom=reset_probe::rom(argv[2]);Adapter a{nullptr,rom};queue_probe::execute(a,argv[1]);return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
