#pragma once
// Optional module capability. The existing generated_step ABI remains single-op.
#include "pce/runtime.hpp"
#include <exception>

namespace pce {
struct SpanHooks {
    void* context=nullptr;
    bool (*before)(void*,Bus&,Cpu&)=nullptr;
    void (*after)(void*,Bus&,Cpu&)=nullptr;
};

class NativeSpan {
    SpanHooks hooks_;
    bool pending_=false, local_=false;
    std::uint64_t native_before_=0, interpreted_before_=0, local_completed_=0;
public:
    static constexpr unsigned maximum=256;
    unsigned limit;
    std::uint64_t completed=0, native_completed=0, interpreted_completed=0;
    std::uint64_t generated_calls=0, local_continuations=0;
    bool stopped=false, aborting=false;
    Exit status=Exit::executed;

    explicit NativeSpan(unsigned count,SpanHooks hooks={}):hooks_(hooks),limit(count) {
        if(!count || count>maximum) throw Fault("native span limit requires 1..256");
    }
    bool pending() const { return pending_; }
    void begin_dispatch() { ++generated_calls;local_=false; }
    void begin_local() { local_=true;local_completed_=0; }

    // Opens an attempted instruction, not a promised retirement. It stays open
    // across a pure context/page redispatch or native miss -> interpreter path.
    bool prepare(Bus& bus,Cpu& cpu,std::uint64_t deadline) {
        if(pending_) return true;
        if(stopped) return false;
        if(completed>=limit) {stopped=true;return false;}
        if(hooks_.before) {
            const auto n=cpu.native_steps,i=cpu.interpreter_steps,t=cpu.ticks,c=cpu.cycles;
            const bool proceed=hooks_.before(hooks_.context,bus,cpu);
            if(cpu.native_steps!=n || cpu.interpreter_steps!=i || cpu.ticks!=t || cpu.cycles!=c)
                throw Fault("native span before callback advanced guest execution");
            if(!proceed) {stopped=true;return false;}
        }
        native_before_=cpu.native_steps;interpreted_before_=cpu.interpreter_steps;pending_=true;
        // Match single-step host ordering: before/after also surround a budget
        // refusal, but reaching the count limit opens no extra attempt.
        if(cpu.ticks>=deadline) {finish(bus,cpu);stopped=true;status=Exit::budget;return false;}
        return true;
    }

private:
    template<bool Native> void finish_impl(Bus& bus,Cpu& cpu) {
        if(!pending_) throw Fault("native span has no open instruction");
        pending_=false; // An after callback that throws must never run twice.
        std::uint64_t n=1,i=0;
        if constexpr(Native) {
            if(cpu.native_steps<=native_before_ || cpu.native_steps-native_before_!=1 ||
               cpu.interpreter_steps!=interpreted_before_)
                throw Fault("generated span did not retire exactly one native instruction");
        } else {
            if(cpu.native_steps<native_before_ || cpu.interpreter_steps<interpreted_before_)
                throw Fault("native span retirement counter regression");
            n=cpu.native_steps-native_before_;i=cpu.interpreter_steps-interpreted_before_;
            if(n>1 || i>1 || n+i>1) throw Fault("native span requires per-instruction retirement boundaries");
        }
        completed+=n+i;native_completed+=n;interpreted_completed+=i;
        if(n && local_) {if(local_completed_)++local_continuations;++local_completed_;}
        if(hooks_.after) {
            const auto t=cpu.ticks,c=cpu.cycles;
            hooks_.after(hooks_.context,bus,cpu);
            if(cpu.native_steps!=native_before_+n || cpu.interpreter_steps!=interpreted_before_+i ||
               cpu.ticks!=t || cpu.cycles!=c)
                throw Fault("native span after callback advanced guest execution");
        }
    }

public:
    void finish(Bus& bus,Cpu& cpu) {finish_impl<false>(bus,cpu);}
    bool commit(Bus& bus,Cpu& cpu,std::uint64_t deadline) {
        finish_impl<true>(bus,cpu);
        return prepare(bus,cpu,deadline);
    }

    // Called only while propagating an original execution exception. Capturing
    // a completed opcode before a later IRQ-entry fault matches legacy step.
    void abort(Bus& bus,Cpu& cpu) {
        aborting=true;
        if(pending_) finish(bus,cpu);
        stopped=true;
    }
};

using GeneratedSpan=Exit (*)(Bus&,Cpu&,std::uint64_t,NativeSpan&);
// Only modules declaring the optional per_instruction_v1 capability define it.
Exit generated_span(Bus&,Cpu&,std::uint64_t deadline,NativeSpan&);

inline Exit dispatch_span(Bus& bus,Cpu& cpu,std::uint64_t deadline,
                          ExecutionPolicy policy,NativeSpan& span,GeneratedSpan generated) {
    switch(policy) {
    case ExecutionPolicy::native_only: case ExecutionPolicy::hybrid: case ExecutionPolicy::interpreter_only: break;
    default: throw Fault("invalid execution policy");
    }
    if(policy!=ExecutionPolicy::interpreter_only && !generated)
        throw Fault("native span requires an explicit generated entry");
    try {
        while(span.prepare(bus,cpu,deadline)) {
            if(policy==ExecutionPolicy::interpreter_only) {
                auto result=interpret_step(bus,cpu,deadline);
                span.finish(bus,cpu);
                if(result==Exit::executed) continue;
                span.stopped=true;span.status=result;return result;
            }
            const auto completed=span.completed;
            span.begin_dispatch();
            auto result=generated(bus,cpu,deadline,span);
            if(result==Exit::miss) {
                if(!span.pending()) throw Fault("native span miss has no open instruction");
                ++cpu.guard_misses;
                if(policy==ExecutionPolicy::hybrid) result=interpret_step(bus,cpu,deadline);
                span.finish(bus,cpu);
                if(result==Exit::executed) continue;
            } else if(result!=Exit::executed) {
                if(span.pending()) span.finish(bus,cpu);
            } else if(!span.stopped && span.completed==completed) {
                throw Fault("generated span made no retirement progress");
            }
            if(result!=Exit::executed) {span.stopped=true;span.status=result;return result;}
        }
        return span.status;
    } catch(...) {
        const auto original=std::current_exception();
        try {span.abort(bus,cpu);} catch(...) {} // Preserve original fault/callback exception.
        std::rethrow_exception(original);
    }
}
inline Exit dispatch_span(Bus& bus,Cpu& cpu,std::uint64_t deadline,
                          bool allow_interpreter,NativeSpan& span,GeneratedSpan generated) {
    return dispatch_span(bus,cpu,deadline,
        allow_interpreter ? ExecutionPolicy::hybrid:ExecutionPolicy::native_only,span,generated);
}
} // namespace pce
