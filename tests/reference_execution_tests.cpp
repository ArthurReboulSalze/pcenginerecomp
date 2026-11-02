// Authored execution-policy fixtures. No retail data or generated game source.
// Direct-interpreter agreement checks dispatch plumbing, not an independent CPU.
#include "pce/checkpoint.hpp"
#include "pce/native_span.hpp"
#include <algorithm>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <vector>

namespace {
unsigned checks=0,generated_calls=0,span_calls=0;
enum class GeneratedMode { trap, miss, nop };
GeneratedMode mode=GeneratedMode::trap;
constexpr auto forever=std::numeric_limits<std::uint64_t>::max();
constexpr auto reference=pce::ExecutionPolicy::interpreter_only;
void require(bool value,const char* why) {++checks;if(!value)throw std::runtime_error(why);}
struct Machine {pce::Bus bus;pce::Cpu cpu;};
void place(Machine& m,unsigned pc,std::initializer_list<unsigned> bytes) {
    for(auto value:bytes)(*m.bus.bytes)[pce::Bus::physical(m.cpu,static_cast<std::uint16_t>(pc++))]=static_cast<std::uint8_t>(value);
}
std::unique_ptr<Machine> configured() {
    auto m=std::make_unique<Machine>();
    std::vector<std::uint8_t> rom(262144,0xEA);
    rom[0x1FF8]=0;rom[0x1FF9]=0x46;
    m->bus.configure_system_card(pce::SystemCardProfile::super,rom);
    m->cpu.pc=0x4000;
    return m;
}
void imported(Machine& m) {
    m.cpu.native_steps=110;m.cpu.interpreter_steps=17;m.cpu.guard_misses=9;
    m.cpu.native_block_steps=3;m.cpu.interpreter_block_steps=2;m.cpu.block_bytes=41;
    m.cpu.cycles=300;m.cpu.ticks=900;m.bus.sync(m.cpu);
}
void unchanged_imports(const pce::Cpu& c,unsigned interpreted,unsigned blocks=0,unsigned bytes=0) {
    require(c.native_steps==110 && c.interpreter_steps==17+interpreted && c.guard_misses==9,
            "reference changed imported native/interpreter/guard accounting");
    require(c.native_block_steps==3 && c.interpreter_block_steps==2+blocks && c.block_bytes==41+bytes,
            "reference changed imported block accounting");
}
pce::Exit generated_trap(pce::Bus&,pce::Cpu&,std::uint64_t,pce::NativeSpan&) {
    ++span_calls;throw pce::Fault("generated span invoked");
}
struct Hooks {
    unsigned before=0,after=0,stop_after=0;
    bool before_throws=false,after_throws=false,advance_before=false,advance_after=false;
    bool saw_abort=false;
    pce::NativeSpan* span=nullptr;
    static bool pre(void* opaque,pce::Bus&,pce::Cpu& c) {
        auto& h=*static_cast<Hooks*>(opaque);++h.before;
        if(h.before_throws)throw pce::Fault("authored before failure");
        if(h.advance_before)++c.ticks;
        return !h.stop_after || h.after<h.stop_after;
    }
    static void post(void* opaque,pce::Bus&,pce::Cpu& c) {
        auto& h=*static_cast<Hooks*>(opaque);++h.after;
        h.saw_abort=h.span&&h.span->aborting;
        if(h.advance_after)++c.interpreter_steps;
        if(h.after_throws)throw pce::Fault("authored after failure");
    }
    pce::SpanHooks get(){return {this,pre,post};}
};
void bypass_and_legacy() {
    auto m=configured();imported(*m);place(*m,0x4000,{0xA9,0x7E,0xE8});
    const auto n=generated_calls;
    require(pce::step(m->bus,m->cpu,forever,reference)==pce::Exit::executed,
            "scalar reference did not execute");
    require(generated_calls==n && m->cpu.a==0x7E && m->cpu.pc==0x4002 && m->cpu.ticks==906,
            "scalar reference called generated entry or altered LDA timing");
    unchanged_imports(m->cpu,1);
    Hooks hooks;pce::NativeSpan span(1,hooks.get());hooks.span=&span;
    require(pce::dispatch_span(m->bus,m->cpu,forever,reference,span,generated_trap)==pce::Exit::executed,
            "reference span did not execute");
    require(!span_calls && !span.generated_calls && !span.local_continuations &&
            span.completed==1 && !span.native_completed && span.interpreted_completed==1 &&
            hooks.before==1 && hooks.after==1 && m->cpu.x==1 && m->cpu.pc==0x4003,
            "reference span used generated dispatch or lost per-op observations");
    unchanged_imports(m->cpu,2);
    place(*m,0x4003,{0xEA});pce::NativeSpan null_span(1);
    require(pce::dispatch_span(m->bus,m->cpu,forever,reference,null_span,nullptr)==pce::Exit::executed,
            "reference requires unused generated span entry");
    unchanged_imports(m->cpu,3);
    mode=GeneratedMode::miss;
    for(bool allow:{false,true}) {
        auto a=configured();place(*a,0x4000,{0xEA});
        const auto before=generated_calls;
        const auto result=pce::step(a->bus,a->cpu,forever,allow);
        require(generated_calls==before+1 && a->cpu.guard_misses==1 && !a->cpu.native_steps &&
                a->cpu.interpreter_steps==unsigned(allow) &&
                result==(allow?pce::Exit::executed:pce::Exit::miss),"legacy bool dispatch changed");
    }
    mode=GeneratedMode::nop;
    auto native=configured();place(*native,0x4000,{0xEA});
    require(pce::step(native->bus,native->cpu,forever,pce::ExecutionPolicy::native_only)==pce::Exit::executed &&
            native->cpu.native_steps==1 && !native->cpu.interpreter_steps,"native policy bypassed native entry");
    mode=GeneratedMode::trap;
}
void refusals() {
    for(bool span_mode:{false,true})for(unsigned kind=0;kind<4;++kind) {
        auto m=configured();place(*m,0x4000,{kind==1?0x0BU:0xEAU});
        // A disabled I/O bank faults; console unmapped reads are defined pull-ups.
        if(kind==2)m->bus.kind[0x80]=pce::BankKind::io;
        const auto before=pce::encode_checkpoint(m->bus,m->cpu);const auto calls=generated_calls;
        Hooks hooks;pce::NativeSpan span(3,hooks.get());hooks.span=&span;
        const auto policy=kind==3?static_cast<pce::ExecutionPolicy>(99):reference;
        pce::Exit result=pce::Exit::executed;bool threw=false;
        try {
            result=span_mode?pce::dispatch_span(m->bus,m->cpu,kind?forever:0,policy,span,generated_trap):
                             pce::step(m->bus,m->cpu,kind?forever:0,policy);
        }catch(const pce::Fault&){threw=true;}
        require(kind>=2?threw:result==(kind?pce::Exit::unsupported:pce::Exit::budget),
                "reference refusal type changed");
        require(!m->cpu.native_steps && !m->cpu.interpreter_steps && !m->cpu.guard_misses &&
                generated_calls==calls && !span_calls,"reference refusal attempted native execution");
        require(pce::encode_checkpoint(m->bus,m->cpu)==before,"reference pre-retirement refusal changed guest state");
        if(span_mode)require(hooks.before==unsigned(kind!=3) && hooks.after==unsigned(kind!=3) &&
            !span.completed && !span.pending(),"span refusal hook boundary differs");
    }
    for(auto policy:{pce::ExecutionPolicy::native_only,pce::ExecutionPolicy::hybrid}) {
        auto m=configured();pce::NativeSpan span(1);bool refused=false;
        try {pce::dispatch_span(m->bus,m->cpu,forever,policy,span,nullptr);}catch(const pce::Fault&){refused=true;}
        require(refused && !m->cpu.ticks,"native span accepted missing entry");
    }
}
void callbacks_and_faults() {
    for(unsigned kind=0;kind<4;++kind) {
        auto m=configured();place(*m,0x4000,{0xEA,0xEA});Hooks hooks;
        hooks.before_throws=kind==0;hooks.after_throws=kind==1;
        hooks.advance_before=kind==2;hooks.advance_after=kind==3;
        pce::NativeSpan span(2,hooks.get());hooks.span=&span;std::string message;
        try {pce::dispatch_span(m->bus,m->cpu,forever,reference,span,nullptr);}
        catch(const pce::Fault& e){message=e.what();}
        require(!message.empty() && !span.pending() && span.stopped,"callback violation did not stop span");
        require(hooks.before==1 && hooks.after==unsigned(kind==1||kind==3),"callback ran more than once");
        if(kind<2)require(message==(kind?"authored after failure":"authored before failure"),
                          "callback original exception was replaced");
    }
    auto m=configured();place(*m,0x4000,{0xEA,0xEA});Hooks hooks;hooks.stop_after=1;
    pce::NativeSpan stopped(4,hooks.get());hooks.span=&stopped;
    require(pce::dispatch_span(m->bus,m->cpu,forever,reference,stopped,nullptr)==pce::Exit::executed &&
            hooks.before==2 && hooks.after==1 && stopped.completed==1 && m->cpu.pc==0x4001,
            "observer stop opened an extra instruction");
    // The opcode retires before IRQ entry faults on a disabled I/O stack bank.
    m=configured();m->bus.enable_interrupts();m->bus.irq.external=2;m->cpu.p=0;
    m->bus.kind[0xF8]=pce::BankKind::io;place(*m,0x4000,{0xEA});
    Hooks irq_hooks;pce::NativeSpan irq_span(2,irq_hooks.get());irq_hooks.span=&irq_span;
    bool threw=false;
    try {pce::dispatch_span(m->bus,m->cpu,forever,reference,irq_span,nullptr);}catch(const pce::Fault&){threw=true;}
    require(threw && irq_span.completed==1 && irq_span.interpreted_completed==1 &&
            irq_hooks.after==1 && irq_hooks.saw_abort && m->cpu.interpreter_steps==1 &&
            !m->cpu.native_steps && m->cpu.ticks==6,"retired opcode before IRQ fault was not closed exactly once");
}
void equivalence_and_checkpoint() {
    for(unsigned scenario=0;scenario<5;++scenario)for(unsigned count:{1U,2U,7U}) {
        auto a=configured();imported(*a);
        place(*a,0x4000,{0xEA,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA});
        unsigned blocks=0,bytes=0;
        if(scenario==0)place(*a,0x4000,{0xF8,0xA9,0x19,0x18,0x69,0x27,0x54,0xEA,0xD4});
        if(scenario==1) {
            place(*a,0x4000,{0x73,0,0x48,0,0x49,2,0,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA});
            place(*a,0x4800,{0x72,0xA4});blocks=1;bytes=2;
        }
        if(scenario==2) {
            a->bus.enable_interrupts();a->bus.irq.external=2;a->cpu.p=pce::I;
            place(*a,0x4000,{0x58,0xEA,0xEA});place(*a,0x4600,{0x40});a->bus.sync(a->cpu);
        }
        if(scenario==3) {
            a->bus.enable_continuous_video();a->bus.enable_psg();
            a->bus.enable_audio_output(pce::AudioProfile::raw);a->bus.sync(a->cpu);
            place(*a,0x4000,{0xAD,2,0,0xEA,0xEA,0xEA,0xEA,0xEA,0xEA});
            auto& v=a->bus.vdc;v.reg[1]=7;(*v.vram)[7]=0x9B62;
            v.selected=2;v.pending_vram_read=true;v.vram_transfer_delay=24;v.status|=64;
        }
        if(scenario==4) {
            a->bus.enable_psg();a->bus.enable_audio_output(pce::AudioProfile::raw);a->bus.sync(a->cpu);
            place(*a,0x4000,{0xA9,0xFF,0x8D,1,8,0x54,0xEA,0xD4,0xEA,0xEA});
        }
        const auto saved=pce::encode_checkpoint(a->bus,a->cpu);
        auto b=configured();
        // Reinitialize the same configured devices before restoring exact state.
        if(scenario==2)b->bus.enable_interrupts();
        if(scenario==3)b->bus.enable_continuous_video();
        if(scenario>=3){b->bus.enable_psg();b->bus.enable_audio_output(pce::AudioProfile::raw);}
        pce::restore_checkpoint(b->bus,b->cpu,saved);
        require(pce::encode_checkpoint(b->bus,b->cpu)==saved,"same-build checkpoint fork changed bytes");
        for(unsigned i=0;i<count;++i)
            require(pce::interpret_step(a->bus,a->cpu,forever)==pce::Exit::executed,"direct reference fixture left coverage");
        Hooks hooks;pce::NativeSpan span(count,hooks.get());hooks.span=&span;
        require(pce::dispatch_span(b->bus,b->cpu,forever,reference,span,generated_trap)==pce::Exit::executed,
                "checkpoint reference span left coverage");
        require(pce::encode_checkpoint(a->bus,a->cpu)==pce::encode_checkpoint(b->bus,b->cpu),
                "reference span diverged from interpreter CPU/device/scheduler state");
        require(hooks.before==count && hooks.after==count && !span.generated_calls && !span.local_continuations &&
                span.completed==count && span.interpreted_completed==count && !span.native_completed,
                "checkpoint reference span accounting differs");
        unchanged_imports(b->cpu,count,blocks,bytes);
        if(scenario==0 && count==7)require(b->cpu.a==0x46 && b->cpu.clock_divisor==3,
                "authored decimal/speed endpoint differs");
        if(scenario==1)require((*b->bus.bytes)[0x100900]==0x72 && (*b->bus.bytes)[0x100901]==0xA4,
                "authored block copy endpoint differs");
        if(scenario==2 && count>=2)require(b->cpu.irq_entries>=1,"reference omitted pending IRQ");
        if(scenario==3)require(b->cpu.a==0x62 && b->cpu.vdc_wait_ticks>0 && b->bus.pcm.master_ticks==b->cpu.ticks,
                "reference omitted VRAM wait or audio clock advancement");
    }
    // Same guest outcome across native and reference paths; only tier counters
    // differ, and the checkpoint format itself remains unchanged.
    auto a=configured(),b=configured();imported(*a);imported(*b);place(*a,0x4000,{0xEA});place(*b,0x4000,{0xEA});
    mode=GeneratedMode::nop;
    require(pce::step(a->bus,a->cpu,forever,pce::ExecutionPolicy::native_only)==pce::Exit::executed &&
            pce::step(b->bus,b->cpu,forever,reference)==pce::Exit::executed,"fork NOP did not execute");
    require(a->cpu.native_steps==111 && a->cpu.interpreter_steps==17 && b->cpu.native_steps==110 &&
            b->cpu.interpreter_steps==18,"fork tiers were relabeled");
    auto normalized=a->cpu;normalized.native_steps=b->cpu.native_steps;normalized.interpreter_steps=b->cpu.interpreter_steps;
    require(pce::encode_checkpoint(a->bus,normalized)==pce::encode_checkpoint(b->bus,b->cpu),
            "same guest state differs beyond declared execution-tier counters");
    mode=GeneratedMode::trap;
}
} // namespace

namespace pce {
Exit generated_step(Bus& bus,Cpu& cpu,std::uint64_t deadline) {
    ++generated_calls;
    if(mode==GeneratedMode::trap)throw Fault("generated scalar invoked");
    if(cpu.ticks>=deadline)return Exit::budget;
    if(mode==GeneratedMode::miss)return Exit::miss;
    bus.begin_instruction(cpu);++cpu.pc;cpu.p&=~T;bus.retire(cpu,2,true);return Exit::executed;
}
} // namespace pce
int main() {
    try {
        bypass_and_legacy();refusals();callbacks_and_faults();equivalence_and_checkpoint();
        std::cout<<"reference execution checks: "<<checks<<"; generated span calls: "<<span_calls<<'\n';
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
