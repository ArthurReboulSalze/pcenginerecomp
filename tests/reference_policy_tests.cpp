// Independent authored tier forks; no retail bytes or generated-source excerpts.
#include "pce/runtime.hpp"
#include "pce/checkpoint.hpp"
#include "pce/code_capture.hpp"
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace {
unsigned checks=0, generated_calls=0;
bool forbid_generated=false;
void require(bool ok,const char* reason) {++checks;if(!ok)throw std::runtime_error(reason);}
constexpr std::array<std::uint8_t,11> authored={0xA9,0x27,0xA2,0x03,0x85,0x10,0xE8,0x49,0x55,0x80,0xF9};
struct Machine {pce::Bus bus;pce::Cpu cpu;};
std::unique_ptr<Machine> configured() {
    auto m=std::make_unique<Machine>();auto& b=m->bus;auto& c=m->cpu;
    b.kind[0x80]=pce::BankKind::rom;b.kind[0xF8]=pce::BankKind::ram;b.kind[0xFF]=pce::BankKind::io;
    std::copy(authored.begin(),authored.end(),b.bytes->begin()+0x100000);
    c.pc=0x4000;c.native_steps=53;c.interpreter_steps=19;c.guard_misses=7;
    c.native_block_steps=2;c.interpreter_block_steps=3;c.block_bytes=17;
    b.enable_continuous_video();b.vce.palette[0]=0x1FF;
    b.enable_audio_output(pce::AudioProfile::filtered,48000,pce::AudioTiming::gear);
    b.psg.main_volume=0xFF;
    auto& ch=b.psg.channels[0];ch.frequency=97;ch.control=0x9F;ch.balance=0xFF;
    for(unsigned i=0;i<32;++i)ch.waveform[i]=static_cast<std::uint8_t>(i);
    return m;
}
std::vector<std::uint8_t> comparable(const Machine& m) {
    auto cpu=m.cpu;
    // Explicitly declared tier bookkeeping only; guest timing, device state,
    // RAM/ROM, palette, queues, back/front RGB and guard diagnostics stay exact.
    cpu.native_steps=cpu.interpreter_steps=0;
    cpu.native_block_steps=cpu.interpreter_block_steps=0;
    return pce::encode_checkpoint(m.bus,cpu);
}
void expect_fault(auto&& action) {
    bool caught=false;try {action();}catch(const pce::Fault&){caught=true;}
    require(caught,"expected explicit execution-policy fault");
}
struct PrivateDirectory {
    std::filesystem::path path=std::filesystem::temp_directory_path()/
        ("pce-authored-reference-policy-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    PrivateDirectory(){require(std::filesystem::create_directory(path),"exclusive authored capture directory");}
    ~PrivateDirectory(){std::error_code ignored;std::filesystem::remove_all(path,ignored);}
};
}
namespace pce {
// Hand-authored direct translations for this fixture only. There is no call
// into interpret_step; the scalar reference policy must bypass this entry.
Exit generated_step(Bus& bus,Cpu& s,std::uint64_t deadline) {
    ++generated_calls;
    if(forbid_generated)throw Fault("reference path entered authored native dispatcher");
    if(s.ticks>=deadline)return Exit::budget;
    if(s.p&T || s.mpr!=Cpu{}.mpr)return Exit::miss;
    unsigned offset,length;
    switch(s.pc) {
    case 0x4000:offset=0;length=2;break;
    case 0x4002:offset=2;length=2;break;
    case 0x4004:offset=4;length=2;break;
    case 0x4006:offset=6;length=1;break;
    case 0x4007:offset=7;length=2;break;
    case 0x4009:offset=9;length=2;break;
    default:return Exit::miss;
    }
    for(unsigned i=0;i<length;++i) {
        auto value=bus.peek(Bus::physical(s,static_cast<std::uint16_t>(s.pc+i)));
        if(!value || *value!=authored[offset+i])return Exit::miss;
    }
    bus.begin_instruction(s);unsigned cycles=2;
    switch(s.pc) {
    case 0x4000:s.a=0x27;s.nz(s.a);s.pc=0x4002;break;
    case 0x4002:s.x=3;s.nz(s.x);s.pc=0x4004;break;
    case 0x4004:cycles=bus.write_timed(s,0x2010,s.a,4);s.pc=0x4006;break;
    case 0x4006:++s.x;s.nz(s.x);s.pc=0x4007;break;
    case 0x4007:s.a^=0x55;s.nz(s.a);s.pc=0x4009;break;
    case 0x4009:s.pc=0x4004;cycles=4;break;
    }
    s.p&=static_cast<std::uint8_t>(~T);bus.retire(s,cycles,true);return Exit::executed;
}
}
namespace {
void full_forks() {
    PrivateDirectory output;auto origin=configured();const auto saved=pce::encode_checkpoint(origin->bus,origin->cpu);
    auto native=configured(),reference=configured();
    pce::restore_checkpoint(native->bus,native->cpu,saved);pce::restore_checkpoint(reference->bus,reference->cpu,saved);
    require(pce::encode_checkpoint(native->bus,native->cpu)==saved,"native fork exact whole canonical restore");
    require(pce::encode_checkpoint(reference->bus,reference->cpu)==saved,"reference fork exact whole canonical restore");
    pce::CodeCapture nc(output.path/"native.json",32),ic(output.path/"reference.json",32);
    constexpr unsigned count=70000;const auto initial_calls=generated_calls;
    for(unsigned n=0;n<count;++n) {
        auto pending=nc.before(native->bus,native->cpu);
        require(pce::step(native->bus,native->cpu,10000000,pce::ExecutionPolicy::native_only)==pce::Exit::executed,"direct authored native retirement");
        nc.after(pending,native->cpu);
        pending=ic.before(reference->bus,reference->cpu);forbid_generated=true;
        const auto result=pce::step(reference->bus,reference->cpu,10000000,pce::ExecutionPolicy::interpreter_only);
        forbid_generated=false;require(result==pce::Exit::executed,"honest reference retirement");ic.after(pending,reference->cpu);
    }
    require(generated_calls-initial_calls==count,"exact native calls and zero reference calls");
    require(native->cpu.native_steps==53+count && native->cpu.interpreter_steps==19,"native fork preserves imported interpreted count");
    require(reference->cpu.native_steps==53 && reference->cpu.interpreter_steps==19+count,"reference fork preserves imported native count");
    require(native->cpu.guard_misses==7 && reference->cpu.guard_misses==7,"reference does not manufacture guard misses");
    require(native->cpu.native_block_steps==2 && native->cpu.interpreter_block_steps==3 && reference->cpu.native_block_steps==2 && reference->cpu.interpreter_block_steps==3,"imported block tier counters exact");
    require(native->cpu.pc==0x4007 && native->cpu.a==0x72 && native->cpu.x==95 && native->cpu.p==pce::I,"independently counted authored loop endpoint");
    require(native->cpu.cycles==209998 && native->cpu.ticks==629994,"independent cycle and master-clock literals");
    require((*native->bus.bytes)[0x1F0010]==0x72,"independent authored RAM result");
    require(pce::encode_checkpoint(native->bus,native->cpu)!=pce::encode_checkpoint(reference->bus,reference->cpu),"honest tier counts keep unmodified checkpoint bytes distinct");
    require(comparable(*native)==comparable(*reference),"entire canonical state identical except four declared tier counters");
    require(native->bus.vdc.video.sequence()>0 && native->bus.vdc.video.sequence()==reference->bus.vdc.video.sequence(),"actual completed guest video frames");
    require(!native->bus.vdc.video.completed().rgb.empty() && native->bus.vdc.video.completed().rgb==reference->bus.vdc.video.completed().rgb,"complete guest RGB parity");
    require(native->bus.pcm.queued_frames()>0 && native->bus.pcm.queued_frames()==reference->bus.pcm.queued_frames(),"actual queued filtered PCM");
    require(native->bus.pcm.drain()==reference->bus.pcm.drain(),"whole signed PCM parity");
    require(comparable(*native)==comparable(*reference),"draining identical PCM preserves entire state equality");
    const auto ns=nc.summary_json(),is=ic.summary_json();
    require(ns.find("\"native_instructions\":70000,")!=std::string::npos && ns.find("\"interpreted_instructions\":0,")!=std::string::npos,"capture native suffix only");
    require(is.find("\"native_instructions\":0,")!=std::string::npos && is.find("\"interpreted_instructions\":70000,")!=std::string::npos,"capture interpreted suffix only");
    nc.finish();ic.finish();
}
void capture_policy_refusals() {
    PrivateDirectory output;auto machine=configured();
    pce::CodeCapture enabled(output.path/"selected.json",16);
    enabled.set_execution_policy(false,"hybrid",64);
    auto summary=enabled.summary_json();
    require(summary.find("\"reference_enabled\":true,\"selected\":false")!=std::string::npos && summary.find("\"effective_native_span\":64")!=std::string::npos,"configured capture policy before selection");
    enabled.set_execution_policy(true,"hybrid",64);summary=enabled.summary_json();
    require(summary.find("\"selected\":true")!=std::string::npos && summary.find("\"effective_policy\":\"interpreter\",\"effective_native_span\":0")!=std::string::npos,"reference capture policy has zero effective native span");
    expect_fault([&]{enabled.set_execution_policy(false,"hybrid",64);});
    expect_fault([&]{enabled.set_execution_policy(true,"hybrid",64);});
    require(enabled.summary_json()==summary,"failed policy reselection cannot alter metadata");
    const auto pending=enabled.before(machine->bus,machine->cpu);
    // Host-authored invalid accounting sample only, not a guest retirement.
    auto impossible=machine->cpu;++impossible.native_steps;
    expect_fault([&]{enabled.after(pending,impossible);});
    require(enabled.summary_json()==summary,"native accounting refusal does not become captured work");
    enabled.finish();expect_fault([&]{enabled.set_execution_policy(false,"hybrid",64);});
    pce::CodeCapture invalid(output.path/"invalid.json",16);
    for(const auto& tier: {std::string("interpreter"),std::string("unknown"),std::string("native\"injected")})
        expect_fault([&]{invalid.set_execution_policy(false,tier,1);});
    for(unsigned span: {0u,257u})expect_fault([&]{invalid.set_execution_policy(false,"native",span);});
    require(invalid.summary_json().find("\"execution_policy\"")==std::string::npos,"invalid setters leave legacy capture schema untouched");
    invalid.set_execution_policy(false,"native",1);(void)invalid.before(machine->bus,machine->cpu);
    expect_fault([&]{invalid.set_execution_policy(true,"native",1);});
    invalid.finish();
}
void source_guard_and_policy_refusals() {
    auto m=configured();auto& b=m->bus;auto& c=m->cpu;
    (*b.bytes)[0x100001]=0x38;const auto before=pce::encode_checkpoint(b,c);
    require(pce::step(b,c,100,pce::ExecutionPolicy::native_only)==pce::Exit::miss,"changed operand cannot use native literal");
    require(c.native_steps==53 && c.interpreter_steps==19 && c.guard_misses==8,"native miss remains a diagnostic not retirement");
    forbid_generated=true;const auto calls=generated_calls;
    require(pce::step(b,c,100,pce::ExecutionPolicy::interpreter_only)==pce::Exit::executed,"reference reads changed authored operand");forbid_generated=false;
    require(c.a==0x38 && c.pc==0x4002 && c.native_steps==53 && c.interpreter_steps==20 && c.guard_misses==8,"reference actual operand and preserved origin");require(generated_calls==calls,"reference never probes cached native source");
    const auto stable=pce::encode_checkpoint(b,c);expect_fault([&]{(void)pce::step(b,c,100,static_cast<pce::ExecutionPolicy>(-3));});require(pce::encode_checkpoint(b,c)==stable,"invalid enum refuses without machine mutation");
    forbid_generated=true;require(pce::step(b,c,c.ticks,pce::ExecutionPolicy::interpreter_only)==pce::Exit::budget,"reference deadline refuses");forbid_generated=false;require(pce::encode_checkpoint(b,c)==stable,"reference budget preserves full state");
    auto corrupt=before;corrupt.pop_back();expect_fault([&]{pce::restore_checkpoint(b,c,corrupt);});require(pce::encode_checkpoint(b,c)==stable,"invalid restore remains transactional with policy API");
}
}
int main() {
    try {full_forks();capture_policy_refusals();source_guard_and_policy_refusals();std::cout<<checks<<" independent authored native/reference policy checks; 70000 native + 70000 interpreted fork retirements plus 1 interpreted source-change continuation; normalized whole-state/RGB/PCM parity; no retail/original-core claim\n";return 0;}
    catch(const std::exception& e){std::cerr<<"reference policy: "<<e.what()<<'\n';return 1;}
}
