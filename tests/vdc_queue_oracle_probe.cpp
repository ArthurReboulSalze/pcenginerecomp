#include "pce/runtime.hpp"
#include "pce/code_capture.hpp"
#include "pce/checkpoint.hpp"
#include "vdc_queue_probe_support.hpp"
#include <memory>
#include <tuple>
struct Adapter {
    std::unique_ptr<pce::Bus> bus;pce::Cpu c;const std::vector<std::uint8_t>& rom;pce::CodeCapture* capture;
    unsigned guards=0;bool guarded=false;
    void reset(unsigned fast,unsigned control){guarded=false;bus=std::make_unique<pce::Bus>();bus->configure_hucard(pce::HuCardProfile::base,rom);bus->enable_continuous_video();bus->power_on_cpu(c);c.clock_divisor=fast?3:12;bus->vdc.write_vce_control(control);bus->vce.write(0,control);for(unsigned i=0;i<32768;++i)(*bus->vdc.vram)[i]=queue_probe::pattern(i);bus->vdc.write(0,1);bus->vdc.write(2,0);bus->vdc.write(3,0);c.ticks=48;bus->sync(c);bus->vdc.write(0,0);if(bus->vdc.has_pending_vram())throw std::runtime_error("authored initial prefetch did not complete");}
    void phase(const queue_probe::Phase& p){auto& v=bus->vdc;v.raster.hclock=p.hclock;v.raster.v_state=p.vstate;v.raster.h_state=p.hstate;v.raster.vdc_line=20;v.sprite_burst=p.burst!=0;v.sprite_mode=p.mode;v.sprite_control=p.control;v.sprite_count=p.sprites;v.load_bg_start_clock=p.start;v.load_bg_end_clock=p.end;v.hsync_start_clock=p.hsync;}
    void write(unsigned port,unsigned value){bus->vdc.write(port,value);}
    unsigned read(unsigned port){return bus->vdc.read(port);}
    void queue(unsigned type){auto& v=bus->vdc;if(type&1){v.pending_vram_read=true;v.vram_transfer_delay=v.raster.divider==2?15:24;}if(type&2){v.pending_vram_write=true;v.vram_transfer_delay=v.raster.divider==4?21:v.raster.divider==3?18:12;}v.status|=64;}
    void service(unsigned ticks){bus->vdc.process_cpu_vram_accesses(ticks);}
    void advance(unsigned ticks){bus->vdc.advance(ticks,&bus->vce);}
    unsigned slot(unsigned elapsed){return bus->vdc.cpu_vram_slot_available(elapsed);}
    void cpu_entry(unsigned address){c.pc=address;c.mpr[0]=255;c.mpr[1]=248;c.mpr[2]=255;}
    void pending_guards(){if(!bus->vdc.vram_dma_pending || !bus->vdc.has_pending_vram())throw std::runtime_error("guest race must retain genuine DMA-held CPU work");guarded=false;}
    void seed(unsigned address,unsigned value){(*bus->vdc.vram)[address]=static_cast<std::uint16_t>(value);}
    std::vector<std::uint64_t> device()const{const auto& v=bus->vdc;std::vector<std::uint64_t> out{v.raster.master_ticks,v.raster.hclock,v.raster.vdc_line,v.raster.v_state,v.raster.h_state,v.pending_vram_read,v.pending_vram_write,static_cast<unsigned>(v.vram_transfer_delay),v.vram_cpu_cycles,v.status,v.read_buffer,v.vram_bus_latch,v.selected,v.satb_pending,v.vram_dma_pending};for(auto r:v.reg)out.push_back(r);out.push_back(reset_probe::hash(v.vram->data(),32768));out.push_back(reset_probe::hash(v.satb.data(),256));return out;}
    std::vector<std::uint64_t> cpu()const{std::vector<std::uint64_t> out{c.pc,c.a,c.x,c.y,c.sp,c.p,c.clock_divisor,c.ticks};for(auto m:c.mpr)out.push_back(m);return out;}
    std::vector<std::uint64_t> ram()const{auto p=bus->bytes->data()+0x1F0000;return {p,p+64};}
    void instruction(){
#ifdef PCE_QUEUE_NATIVE_ONLY
        if(!guarded){auto snapshot=[&]{return std::tuple{pce::encode_checkpoint(*bus,c),bus->generation,bus->vdc.reads,bus->vdc.writes};};auto before=snapshot();auto pa=pce::Bus::physical(c,c.pc);auto old=(*bus->bytes)[pa];(*bus->bytes)[pa]^=255;auto result=pce::generated_step(*bus,c,100000000);(*bus->bytes)[pa]=old;if(result!=pce::Exit::miss||snapshot()!=before)throw std::runtime_error("source guard advanced pending queue");++guards;c.mpr[3]^=1;result=pce::generated_step(*bus,c,100000000);c.mpr[3]^=1;if(result!=pce::Exit::miss||snapshot()!=before)throw std::runtime_error("MPR guard advanced pending queue");++guards;guarded=true;}
#endif
        pce::CodeCapture::Pending pending;if(capture)pending=capture->before(*bus,c);
#ifdef PCE_QUEUE_NATIVE_ONLY
        if(pce::generated_step(*bus,c,100000000)!=pce::Exit::executed)throw std::runtime_error("native miss; fallback forbidden");
#else
        if(pce::interpret_step(*bus,c,100000000)!=pce::Exit::executed)throw std::runtime_error("interpreter refused");
#endif
        if(capture)capture->after(pending,c);
    }
};
int main(int argc,char** argv){try{if(argc!=3&&argc!=5)throw std::runtime_error("usage: queue-probe PLAN AUTHORED_ROM [--capture NEW]");auto rom=reset_probe::rom(argv[2]);std::unique_ptr<pce::CodeCapture> capture;if(argc==5){if(std::string(argv[3])!="--capture")throw std::runtime_error("capture option");capture=std::make_unique<pce::CodeCapture>(argv[4],65536);}Adapter a{nullptr,{},rom,capture.get()};queue_probe::execute(a,argv[1]);if(capture)capture->finish();std::cerr<<"PCE_QUEUE_GUARDS="<<a.guards<<'\n';return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
