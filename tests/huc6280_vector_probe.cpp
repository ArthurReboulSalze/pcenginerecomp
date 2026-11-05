// Test-only adapter: SingleStepTests/huc6280 vectors against the interpreter and
// against actual emitted/compiled native code. No runtime, CPU or ABI change.
//
//   probe selftest                 authored vectors only, no corpus: checks the comparison and its negative cases
//   probe interp DIR [ops] [limit] every vector of DIR/XX.json.bin through pce::interpret_step
//   probe native CASES             remapped cases (see docs/HUC6280_VECTORS.md) through pce::generated_step
//                                  of the module linked into this executable, and through the interpreter
//
// Output is one JSON object per line. Results are reported in separate classes:
// architectural state (registers, flags, PC, MPRs, sparse physical memory) and the CPU
// cycle total. Bus-event order, dummy accesses and master ticks are not observed by
// this adapter and are never inferred. Corpus limits stay visible: vectors cut by the
// generator cap (500 cycles or 500 RAM pairs) have no comparable final state.
#include "pce/runtime.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr std::size_t generator_cap = 500;        // README of the corpus: 500 RAM pairs, 500 cycles
constexpr std::size_t max_file_bytes = 64u << 20; // protocol bounds for one corpus file
constexpr std::uint32_t max_vectors = 100000;
constexpr std::uint32_t max_pairs = 4096;

struct State {
    std::uint8_t a=0, x=0, y=0, s=0, p=0;
    std::uint16_t pc=0;
    std::array<std::uint8_t,8> mpr{};
    std::vector<std::pair<std::uint32_t,std::uint8_t>> ram;
};
struct Vector {
    std::string name;
    unsigned opcode=0;
    State init, fin;
    unsigned num_cycles=0;
    std::size_t stored_cycles=0;
    bool truncated() const { return stored_cycles>=generator_cap || init.ram.size()>=generator_cap || fin.ram.size()>=generator_cap; }
};

struct Reader {
    const std::vector<char>& b;
    std::size_t p=0;
    template<class T> T get() {
        if(p+sizeof(T)>b.size()) throw std::runtime_error("corpus file ends inside a record");
        T v; std::memcpy(&v,&b[p],sizeof(T)); p+=sizeof(T); return v;
    }
};

State read_state(Reader& r) {
    State s;
    r.get<std::int32_t>(); // record size; fields are read sequentially, the size is not trusted
    s.a=r.get<std::uint8_t>(); s.x=r.get<std::uint8_t>(); s.y=r.get<std::uint8_t>();
    s.s=r.get<std::uint8_t>(); s.p=r.get<std::uint8_t>();
    s.pc=r.get<std::uint16_t>();
    for(auto& m:s.mpr) m=r.get<std::uint8_t>();
    const auto n=r.get<std::int32_t>();
    if(n<0 || static_cast<std::uint32_t>(n)>max_pairs) throw std::runtime_error("RAM pair count out of range");
    for(int i=0;i<n;++i) {
        const auto address=r.get<std::uint32_t>();
        if(address>=0x200000) throw std::runtime_error("RAM address outside the 21-bit space");
        s.ram.emplace_back(address,r.get<std::uint8_t>());
    }
    return s;
}

// Format of the corpus (README and transcode_json.py of SingleStepTests/huc6280).
std::vector<Vector> parse_corpus(const std::vector<char>& data) {
    if(data.size()>max_file_bytes) throw std::runtime_error("corpus file exceeds the 64 MiB bound");
    Reader r{data};
    const auto count=r.get<std::uint32_t>();
    if(count>max_vectors) throw std::runtime_error("vector count out of range");
    std::vector<Vector> out; out.reserve(count);
    for(std::uint32_t i=0;i<count;++i) {
        Vector v;
        r.get<std::int32_t>();
        char name[51]={};
        if(r.p+50>data.size()) throw std::runtime_error("corpus file ends inside a record");
        std::memcpy(name,&data[r.p],50); r.p+=50;
        v.name=name;
        while(!v.name.empty() && (v.name.back()==' ')) v.name.pop_back();
        v.opcode=r.get<std::uint32_t>();
        v.init=read_state(r); v.fin=read_state(r);
        v.num_cycles=r.get<std::uint32_t>();
        const auto stored=r.get<std::uint32_t>();
        if(stored>max_pairs) throw std::runtime_error("cycle record count out of range");
        v.stored_cycles=stored;
        for(std::uint32_t k=0;k<stored;++k) r.get<std::uint32_t>(); // bus cycles: kept in the corpus, not observable here
        out.push_back(std::move(v));
    }
    return out;
}

std::vector<Vector> read_corpus_file(const std::string& path) {
    std::ifstream f(path,std::ios::binary);
    if(!f) throw std::runtime_error("cannot open "+path);
    return parse_corpus(std::vector<char>((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>()));
}

enum Diff : unsigned { registers=1, flags=2, pc=4, mpr=8, memory=16 };
struct Verdict {
    bool refused=false, faulted=false, truncated=false;
    unsigned diff=0;
    bool cycles_equal=false;
    unsigned cycles=0;
    State got;
    std::vector<std::uint8_t> cells; // final value of every listed final cell, for native-versus-interpreter comparison
};

enum class Tier { interpreter, native };

std::unique_ptr<pce::Bus> make_bus() {
    auto bus=std::make_unique<pce::Bus>();
    bus->enable_vdc();                           // ST0/ST1/ST2 need the functional VDC profile to execute
    for(auto& k:bus->kind) k=pce::BankKind::ram; // after it: the corpus is flat 2 MiB with MPR translation only, no I/O page
    return bus;
}

Verdict play(pce::Bus& bus,const Vector& v,Tier tier,const std::array<std::uint8_t,8>* frame=nullptr) {
    Verdict out;
    pce::Cpu cpu;
    cpu.a=v.init.a; cpu.x=v.init.x; cpu.y=v.init.y; cpu.sp=v.init.s; cpu.p=v.init.p; cpu.pc=v.init.pc;
    cpu.mpr=frame ? *frame : v.init.mpr;
    cpu.clock_divisor=3; cpu.mpr_latch=0;
    for(const auto& cell:v.init.ram) (*bus.bytes)[cell.first]=cell.second;
    pce::Exit exit=pce::Exit::unsupported;
    try {
        exit=tier==Tier::native ? pce::generated_step(bus,cpu,UINT64_MAX) : pce::interpret_step(bus,cpu,UINT64_MAX);
    } catch(const std::exception&) { out.faulted=true; }
    if(!out.faulted) {
        if(exit==pce::Exit::miss) out.faulted=true;                       // a native guard miss is reported as a fault
        else if(exit!=pce::Exit::executed) out.refused=true;
    }
    out.truncated=v.truncated();
    if(!out.faulted && !out.refused) {
        out.cycles=static_cast<unsigned>(cpu.cycles);
        out.cycles_equal=cpu.cycles==v.num_cycles;
        out.got.a=cpu.a; out.got.x=cpu.x; out.got.y=cpu.y; out.got.s=cpu.sp; out.got.p=cpu.p; out.got.pc=cpu.pc; out.got.mpr=cpu.mpr;
        if(!out.truncated) {
            if(cpu.a!=v.fin.a||cpu.x!=v.fin.x||cpu.y!=v.fin.y||cpu.sp!=v.fin.s) out.diff|=registers;
            if(cpu.p!=v.fin.p) out.diff|=flags;
            if(cpu.pc!=v.fin.pc) out.diff|=pc;
            const auto expected_mpr=frame ? *frame : v.fin.mpr;
            if(cpu.mpr!=expected_mpr) out.diff|=mpr;
            for(const auto& cell:v.fin.ram) if((*bus.bytes)[cell.first]!=cell.second) { out.diff|=memory; break; }
        }
    }
    if(!out.faulted && !out.refused) for(const auto& cell:v.fin.ram) out.cells.push_back((*bus.bytes)[cell.first]);
    for(const auto& cell:v.init.ram) (*bus.bytes)[cell.first]=0;
    for(const auto& cell:v.fin.ram) (*bus.bytes)[cell.first]=0;
    return out;
}

struct Tally {
    unsigned vectors=0, executed=0, refused=0, faulted=0, truncated=0;
    unsigned state_equal=0, state_different=0, cycles_equal=0, cycles_different=0, both_equal=0;
    unsigned by_class[5]={};
    bool have_first=false;
    std::string first_name;
    unsigned first_diff=0, first_cycles_expected=0, first_cycles_got=0;
    State first_expected, first_got;
    void add(const Vector& v,const Verdict& d) {
        ++vectors;
        if(d.faulted) { ++faulted; return; }
        if(d.refused) { ++refused; return; }
        ++executed;
        if(d.truncated) ++truncated;
        else if(d.diff) ++state_different; else ++state_equal;
        if(d.cycles_equal) ++cycles_equal; else ++cycles_different;
        if(!d.truncated && !d.diff && d.cycles_equal) ++both_equal;
        for(int c=0;c<5;++c) if(d.diff&(1u<<c)) ++by_class[c];
        if(!have_first && (d.diff || !d.cycles_equal)) {
            have_first=true; first_name=v.name; first_diff=d.diff;
            first_cycles_expected=v.num_cycles; first_cycles_got=d.cycles;
            first_expected=v.fin; first_got=d.got;
        }
    }
};

std::string json_escape(const std::string& s) {
    std::string o;
    for(char c:s) { if(c=='"'||c=='\\') o+='\\'; if(static_cast<unsigned char>(c)>=32) o+=c; }
    return o;
}

void print_state(const char* key,const State& s) {
    std::printf(",\"%s\":{\"a\":%u,\"x\":%u,\"y\":%u,\"s\":%u,\"p\":%u,\"pc\":%u}",key,s.a,s.x,s.y,s.s,s.p,s.pc);
}

void print_tally(const char* tier,unsigned opcode,const Tally& t) {
    std::printf("{\"tier\":\"%s\",\"opcode\":\"%02X\",\"vectors\":%u,\"executed\":%u,\"refused\":%u,\"faulted\":%u,\"state_not_comparable\":%u,"
                "\"state_equal\":%u,\"state_different\":%u,\"cycles_equal\":%u,\"cycles_different\":%u,\"both_equal\":%u,"
                "\"classes\":{\"registers\":%u,\"flags\":%u,\"pc\":%u,\"mpr\":%u,\"memory\":%u}",
                tier,opcode,t.vectors,t.executed,t.refused,t.faulted,t.truncated,t.state_equal,t.state_different,
                t.cycles_equal,t.cycles_different,t.both_equal,t.by_class[0],t.by_class[1],t.by_class[2],t.by_class[3],t.by_class[4]);
    if(t.have_first) {
        std::printf(",\"first_difference\":{\"vector\":\"%s\",\"classes_mask\":%u,\"cycles_expected\":%u,\"cycles_got\":%u",
                    json_escape(t.first_name).c_str(),t.first_diff,t.first_cycles_expected,t.first_cycles_got);
        print_state("expected",t.first_expected); print_state("got",t.first_got);
        std::printf("}");
    }
    std::printf("}\n");
}

// Native cases: header "PCE-HUC6280-NATIVE-CASES 1", "MPR m0..m7", then per case lines
// "T name opcode cycles A X Y S P PC", "F A X Y S P PC", "I n addr value ...", "O n addr value ...".
std::vector<Vector> read_cases(const std::string& path,std::array<std::uint8_t,8>& frame) {
    std::ifstream f(path);
    if(!f) throw std::runtime_error("cannot open "+path);
    std::string line;
    std::getline(f,line);
    if(line!="PCE-HUC6280-NATIVE-CASES 1") throw std::runtime_error("unknown native case file");
    std::getline(f,line);
    { std::istringstream is(line); std::string tag; is>>tag; if(tag!="MPR") throw std::runtime_error("MPR line missing");
      for(auto& m:frame) { unsigned v; if(!(is>>v)||v>255) throw std::runtime_error("bad MPR"); m=static_cast<std::uint8_t>(v); } }
    std::vector<Vector> out; Vector v;
    while(std::getline(f,line)) {
        std::istringstream is(line); std::string tag; is>>tag;
        if(tag=="T") {
            v=Vector(); unsigned a,x,y,s,p,pcv;
            is>>v.name>>v.opcode>>v.num_cycles>>a>>x>>y>>s>>p>>pcv;
            v.init.a=a; v.init.x=x; v.init.y=y; v.init.s=s; v.init.p=p; v.init.pc=pcv; v.init.mpr=frame; v.fin.mpr=frame;
        } else if(tag=="F") {
            unsigned a,x,y,s,p,pcv; is>>a>>x>>y>>s>>p>>pcv;
            v.fin.a=a; v.fin.x=x; v.fin.y=y; v.fin.s=s; v.fin.p=p; v.fin.pc=pcv;
        } else if(tag=="I"||tag=="O") {
            std::size_t n; is>>n;
            if(n>=generator_cap) throw std::runtime_error("native case exceeds the generator cap");
            auto& cells=tag=="I" ? v.init.ram : v.fin.ram;
            for(std::size_t i=0;i<n;++i) { unsigned address,value; is>>address>>value; if(address>=0x200000||value>255) throw std::runtime_error("bad cell"); cells.emplace_back(address,static_cast<std::uint8_t>(value)); }
            if(tag=="O") out.push_back(v);
        }
        if(out.size()>max_vectors) throw std::runtime_error("native case count out of range");
    }
    return out;
}

int run_interp(const std::string& dir,const std::vector<unsigned>& only,unsigned limit) {
    auto bus=make_bus();
    for(unsigned op=0;op<256;++op) {
        if(!only.empty() && std::find(only.begin(),only.end(),op)==only.end()) continue;
        char name[16]; std::snprintf(name,sizeof name,"%02x.json.bin",op);
        auto vectors=read_corpus_file(dir+"/"+name);
        Tally t;
        for(const auto& v:vectors) {
            if(limit && t.vectors>=limit) break;
            if(v.opcode!=op) throw std::runtime_error("vector opcode does not match its file");
            t.add(v,play(*bus,v,Tier::interpreter));
        }
        print_tally("interpreter",op,t);
    }
    return 0;
}

int run_native(const std::string& path) {
    std::array<std::uint8_t,8> frame{};
    const auto cases=read_cases(path,frame);
    auto bus=make_bus();
    std::vector<Tally> native(256), interp(256);
    unsigned native_vs_interpreter_different=0;
    for(const auto& v:cases) {
        const auto n=play(*bus,v,Tier::native,&frame);
        const auto i=play(*bus,v,Tier::interpreter,&frame);
        native[v.opcode].add(v,n); interp[v.opcode].add(v,i);
        const bool same=n.faulted==i.faulted && n.refused==i.refused && n.cycles==i.cycles &&
            n.got.a==i.got.a && n.got.x==i.got.x && n.got.y==i.got.y && n.got.s==i.got.s && n.got.p==i.got.p && n.got.pc==i.got.pc && n.cells==i.cells;
        if(!same) ++native_vs_interpreter_different;
    }
    for(unsigned op=0;op<256;++op) if(native[op].vectors) { print_tally("native",op,native[op]); print_tally("interpreter-on-native-cases",op,interp[op]); }
    std::printf("{\"native_vs_interpreter_different\":%u,\"cases\":%zu}\n",native_vs_interpreter_different,cases.size());
    return 0;
}

// ---- authored self-test: expectations written by hand from the instruction definitions ----
Vector authored(const char* name,unsigned opcode,std::vector<std::uint8_t> bytes,State init,State fin,unsigned cycles) {
    Vector v; v.name=name; v.opcode=opcode; v.num_cycles=cycles; v.stored_cycles=cycles;
    init.mpr={0xFF,0xF8,0x80,0x81,0x82,0x83,0x84,0x00}; fin.mpr=init.mpr;
    for(std::size_t i=0;i<bytes.size();++i) init.ram.emplace_back(static_cast<std::uint32_t>(0x4000u+i),bytes[i]); // MPR2 = page $80 -> logical $4000 = physical $100000
    for(auto& c:init.ram) c.first+=0x100000-0x4000;
    fin.ram=init.ram;
    v.init=init; v.fin=fin;
    return v;
}

int selftest() {
    int failures=0;
    auto bus=make_bus();
    auto expect=[&](bool ok,const char* what){ if(!ok) { std::fprintf(stderr,"selftest failed: %s\n",what); ++failures; } };
    // LDA #$80: A=$80, N set, 2 cycles, PC+2. Initial P=$04 (I).
    State i, f;
    i.a=0; i.p=0x04; i.pc=0x4000; f=i; f.a=0x80; f.p=0x84; f.pc=0x4002;
    const Vector lda=authored("authored LDA #$80",0xA9,{0xA9,0x80},i,f,2);
    auto d=play(*bus,lda,Tier::interpreter);
    expect(!d.refused && !d.faulted && d.diff==0 && d.cycles_equal,"authored LDA vector must agree with the interpreter");
    // ADC #$01 with A=$FF, C=0: A=$00, C and Z set, 2 cycles.
    i=State(); i.a=0xFF; i.p=0x00; i.pc=0x4000; f=i; f.a=0; f.p=0x03; f.pc=0x4002;
    const Vector adc=authored("authored ADC #$01",0x69,{0x69,0x01},i,f,2);
    d=play(*bus,adc,Tier::interpreter);
    expect(d.diff==0 && d.cycles_equal,"authored ADC vector must agree with the interpreter");
    // Negative 1: one register of the expectation altered -> registers class reported, cycles unaffected.
    Vector bad=lda; bad.fin.a^=1;
    d=play(*bus,bad,Tier::interpreter);
    expect((d.diff&registers) && d.cycles_equal,"a wrong register must be reported as a register difference only");
    // Negative 2: one flag altered -> flags class.
    bad=lda; bad.fin.p^=0x40;
    d=play(*bus,bad,Tier::interpreter);
    expect(d.diff==flags,"a wrong flag must be reported as a flags difference only");
    // Negative 3: PC altered.
    bad=lda; bad.fin.pc+=1;
    d=play(*bus,bad,Tier::interpreter);
    expect(d.diff==pc,"a wrong PC must be reported as a PC difference only");
    // Negative 4: one final RAM cell altered -> memory class.
    bad=lda; bad.fin.ram[0].second^=0x10;
    d=play(*bus,bad,Tier::interpreter);
    expect(d.diff==memory,"a wrong RAM cell must be reported as a memory difference only");
    // Negative 5: cycle total altered -> cycles differ while the state still agrees.
    bad=lda; bad.num_cycles=3;
    d=play(*bus,bad,Tier::interpreter);
    expect(d.diff==0 && !d.cycles_equal,"a wrong cycle total must be reported separately from the state");
    // Negative 6: a vector cut by the generator cap has no comparable state, even if the expectation is wrong.
    bad=lda; bad.fin.a^=1; bad.stored_cycles=generator_cap;
    d=play(*bus,bad,Tier::interpreter);
    expect(d.truncated && d.diff==0,"a vector cut at the cap must be not comparable, never a pass or a state failure");
    Tally t; t.add(bad,d);
    expect(t.truncated==1 && t.state_equal==0 && t.state_different==0,"a cut vector must not count as equal or different");
    // Negative 7: a reserved opcode is refused and listed, not skipped.
    Vector reserved=lda; reserved.opcode=0x0B; reserved.init.ram[0].second=0x0B;
    d=play(*bus,reserved,Tier::interpreter);
    expect(d.refused,"the interpreter refuses reserved opcode $0B and the adapter must list it as refused");
    // Corpus parsing refuses a file that ends inside a record.
    bool refused=false;
    try { parse_corpus(std::vector<char>{1,0,0,0}); } catch(const std::exception&) { refused=true; }
    expect(refused,"a truncated corpus file must be refused");
    std::printf("huc6280 vector probe selftest: %d failure(s)\n",failures);
    return failures ? 1 : 0;
}
} // namespace

int main(int argc,char** argv) {
    try {
        if(argc>=2 && std::string(argv[1])=="selftest") return selftest();
        if(argc>=3 && std::string(argv[1])=="interp") {
            std::vector<unsigned> only;
            if(argc>=4 && std::string(argv[3])!="all") { std::istringstream is(argv[3]); std::string tok; while(std::getline(is,tok,',')) only.push_back(std::stoul(tok,nullptr,16)); }
            const unsigned limit=argc>=5 ? static_cast<unsigned>(std::stoul(argv[4])) : 0;
            return run_interp(argv[2],only,limit);
        }
        if(argc>=3 && std::string(argv[1])=="native") return run_native(argv[2]);
        std::fprintf(stderr,"usage: probe selftest | interp DIR [OPS|all] [LIMIT] | native CASES\n");
        return 2;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"huc6280 vector probe: %s\n",e.what());
        return 2;
    }
}
