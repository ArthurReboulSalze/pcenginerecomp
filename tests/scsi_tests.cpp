#include "pce/runtime.hpp"
#include "scsi_fixture.hpp"
#include <fstream>
#include <iostream>
#include <limits>
#include <tuple>
#include <vector>

static constexpr auto forever=std::numeric_limits<std::uint64_t>::max();
static void require(bool value,const char* why) { if(!value) throw std::runtime_error(why); }
static unsigned site(unsigned op,unsigned address=0) {
    for(auto c:scsi_cases) if(c.op==op && c.address==address) return c.pc;
    throw std::runtime_error("missing authored CD transport instruction");
}
static auto cpu_state(const pce::Cpu& s) {
    return std::tuple{s.a,s.x,s.y,s.sp,s.p,s.pc,s.mpr,s.mpr_latch,s.cycles,s.ticks,s.clock_divisor};
}
static void initialize(pce::Bus& b,unsigned seed=0) {
    b.enable_cd_transport();b.kind[0xF8]=pce::BankKind::ram;
    for(unsigned i=0;i<8192;++i) (*b.bytes)[0x1F0000+i]=static_cast<std::uint8_t>(i*37+seed*17);
    for(unsigned i=0;i<2048;++i) (*b.bytes)[0x1EE000+i]=static_cast<std::uint8_t>(i*13+seed*7);
    for(auto [pa,value]:scsi_program) (*b.bytes)[pa]=value;
    b.generation.fill(0);
}
static pce::CdToc authored_toc(bool reference=false) {
    pce::CdToc toc;
    if(reference) {
        toc.track_count=12;toc.leadout_lba=1032;
        for(unsigned i=0;i<12;++i)toc.tracks[i]={i*86,static_cast<std::uint8_t>(i==0 || i==11?4:0)};
    } else {
        toc.track_count=3;toc.leadout_lba=34567;
        toc.tracks[0]={0,4};toc.tracks[1]={12345,0};toc.tracks[2]={23456,4};
    }
    return toc;
}
static void execute(pce::Bus& b,pce::Cpu& s,bool native) {
    require((native?pce::generated_step(b,s,forever):pce::interpret_step(b,s,forever))==pce::Exit::executed,
            "CD transport fixture instruction did not execute");
}
static void instruction(pce::Bus& b,pce::Cpu& s,bool native,unsigned op,unsigned address,unsigned value=0) {
    s.pc=static_cast<std::uint16_t>(site(op,address));s.a=static_cast<std::uint8_t>(value);execute(b,s,native);
}
static void settle(pce::Bus& b,pce::Cpu& s,bool native,unsigned count) {
    const auto pc=s.pc;
    for(unsigned n=0;n<count;++n) {s.pc=static_cast<std::uint16_t>(site(0xEA));execute(b,s,native);}
    s.pc=pc;
}
static void print_cpu(const pce::Cpu& s) {
    std::cout<<"{\"pc\":"<<s.pc<<",\"a\":"<<unsigned(s.a)<<",\"x\":"<<unsigned(s.x)
             <<",\"y\":"<<unsigned(s.y)<<",\"sp\":"<<unsigned(s.sp)<<",\"p\":"<<unsigned(s.p)<<",\"mpr\":[";
    for(unsigned i=0;i<8;++i)std::cout<<(i?",":"")<<unsigned(s.mpr[i]);
    std::cout<<"]}";
}
static void print_cd(const pce::CdControl& c) {
    const auto signals=c.scsi.signals;
    std::cout<<"{\"bram_unlocked\":"<<(c.bram_unlocked?"true":"false")
        <<",\"ack\":"<<(c.ack?"true":"false")<<",\"irq_enable\":"<<unsigned(c.interrupt_enable)
        <<",\"irq_active\":"<<unsigned(c.interrupt_active)<<",\"reset\":"<<unsigned(c.reset)
        <<",\"irq2\":"<<(c.irq2()?"true":"false")<<",\"phase\":"<<c.scsi.phase
        <<",\"bsy\":"<<((signals&0x80)?"true":"false")<<",\"req\":"<<((signals&0x40)?"true":"false")
        <<",\"msg\":"<<((signals&0x20)?"true":"false")<<",\"cd\":"<<((signals&0x10)?"true":"false")
        <<",\"io\":"<<((signals&8)?"true":"false")<<",\"data\":"<<unsigned(c.scsi.data)<<'}';
}
static void print_memory(const pce::Bus& b,unsigned start,unsigned count) {
    constexpr char h[]="0123456789abcdef";
    for(unsigned n=0;n<count;++n) {const auto v=(*b.bytes)[start+n];std::cout<<h[v>>4]<<h[v&15];}
}
static int probe(const char* path,const std::string& tier,bool toc=false,bool unknown=false) {
    if(tier!="native" && tier!="interpreter")return 2;
    std::ifstream input(path);unsigned seed,a,x,y,sp,p,count;
    if(!(input>>seed>>a>>x>>y>>sp>>p>>count) || seed>255 || a>255 || x>255 || y>255 || sp>255 || p>255 || count<1 || count>256)return 2;
    struct Action {unsigned pc;int value;unsigned nops;};
    std::vector<Action> actions;std::uint64_t total_nops=0;
    for(unsigned i=0;i<count;++i) {
        Action action;
        if(!(input>>action.pc>>action.value>>action.nops) || action.pc>65535 || action.value < -1 || action.value>255 || action.nops>100000)return 2;
        total_nops+=action.nops;if(total_nops>1000000)return 2;actions.push_back(action);
    }
    std::string trailing;if(input>>trailing)return 2;
    pce::Bus b;initialize(b,seed);if(toc)b.cd.set_toc(authored_toc(true));
    b.cd.unknown_policy=unknown ? pce::CdUnknownPolicy::gear_good:pce::CdUnknownPolicy::fault;
    pce::Cpu s;s.mpr=scsi_mpr;s.a=a;s.x=x;s.y=y;s.sp=sp;s.p=p;
    std::cout<<"{\"states\":[";
    for(unsigned i=0;i<count;++i) {
        const auto action=actions[i];s.pc=static_cast<std::uint16_t>(action.pc);
        if(action.value>=0)s.a=static_cast<std::uint8_t>(action.value);
        execute(b,s,tier=="native");settle(b,s,tier=="native",action.nops);
        if(i)std::cout<<',';
        std::cout<<"{\"cpu\":";print_cpu(s);std::cout<<",\"cd\":";print_cd(b.cd);std::cout<<'}';
    }
    std::cout<<"],\"ram\":\"";print_memory(b,0x1F0000,8192);std::cout<<"\",\"bram\":\"";print_memory(b,0x1EE000,2048);
    std::cout<<"\",\"native_steps\":"<<s.native_steps<<",\"interpreter_steps\":"<<s.interpreter_steps<<"}\n";return 0;
}

// Device expectations below are literal protocol observations, independent of
// the emitted implementation. No disc bytes, firmware code or owner saves.
static unsigned expectations(pce::Bus& b) {
    unsigned checks=0;
    for(bool native:{false,true})for(unsigned divisor:{3U,12U})
    for(unsigned flags:{4U,0x55U,0xAEU,0xFFU})for(unsigned value=0;value<256;++value) {
        initialize(b);pce::Cpu s;s.mpr=scsi_mpr;s.p=flags;s.clock_divisor=divisor;
        s.x=0x71;s.y=0x93;s.sp=0xE7;
        const auto generation=b.generation;
        instruction(b,s,native,0x8D,0x1801,value);
        require(s.a==value && s.p==(flags&~32U),"output-latch store CPU flags/value");
        require(b.read(s,0xB801)==value && b.read(s,0x1808)==value,
                "idle command/data latch or automatic-ACK read alias");
        require(!b.cd.ack,"idle data read raised automatic ACK");
        instruction(b,s,native,0xAD,0xB801);
        const auto expected_p=(flags&0x5D)|(value&128)|(value==0?2:0);
        require(s.a==value && s.p==expected_p,"data-latch load NZ/T semantics");
        instruction(b,s,native,0x8D,0xB802,value);
        require(b.read(s,0x1802)==value && b.cd.interrupt_enable==(value&127) && b.cd.ack==(value>=128),
                "ACK/control mask byte sweep");
        require(b.read(s,0x1800)==0 && !b.cd.irq2(),"idle control created a SCSI phase/IRQ");
        require(s.cycles==15 && s.ticks==15*divisor && b.generation==generation,
                "command data/control timing or executable-memory mutation");
        require(s.native_steps==(native?3U:0U) && s.interpreter_steps==(native?0U:3U),
                "transport byte sweep execution tier");
        ++checks;
    }
    for(bool native:{false,true})for(unsigned op:{0x0CU,0x1CU})
    for(unsigned value=0;value<256;++value)for(unsigned mask:{0U,1U,0x80U,0xFFU}) {
        initialize(b);pce::Cpu s;s.mpr=scsi_mpr;s.p=0xAD;
        b.write(s,0x1802,static_cast<std::uint8_t>(value));
        instruction(b,s,native,op,0x1802,mask);
        const unsigned expected=(op==0x0C ? value|mask:value&(~mask&255));
        require(b.read(s,0xB802)==expected && b.cd.ack==(expected>=128) && b.cd.interrupt_enable==(expected&127),
                "RMW ACK/control read-modify-write semantics");
        require(s.p==((0xAD&0x1D)|(value&0xC0)|(expected==0?2:0)) && s.cycles==7 && s.ticks==21,
                "RMW ACK/control flags or timing");
        ++checks;
    }
    // Exact guest-master-clock boundaries are intentionally separate from
    // CPU bus-phase placement: these direct bus writes occur at known times.
    for(unsigned select_value:{0U,1U,0x7FU,0x80U,0xFFU}) {
        initialize(b);pce::Cpu s;s.mpr=scsi_mpr;
        auto advance=[&](unsigned ticks) {s.ticks+=ticks;b.sync(s);};
        auto status=[&](unsigned expected,const char* message) {
            require(b.read(s,0x1800)==expected,message);++checks;
        };
        b.write(s,0xB800,static_cast<std::uint8_t>(select_value));
        advance(74999);status(0,"selection fired before 75000 master ticks");
        advance(1);status(0xD0,"selection did not enter command request at 75000 ticks");
        for(unsigned byte=0;byte<6;++byte) {
            b.write(s,0x1801,0);b.write(s,0x1802,0xA0);
            status(0x90,"ACK rise did not consume command request");
            // Raising ACK again must neither append another byte nor advance.
            b.write(s,0xB802,0xA0);status(0x90,"held ACK consumed a second command byte");
            b.write(s,0x1802,0x20);
            if(byte<5) {
                advance(2999);status(0x90,"next command request fired early");
                advance(1);status(0xD0,"next command request missing at 3000 ticks");
            }
        }
        advance(449999);status(0x90,"TUR status fired before 450000 ticks");
        advance(1);status(0xD8,"TUR did not produce GOOD status");
        require(b.cd.interrupt_active==0x20 && b.cd.irq2(),"status request did not assert enabled IRQ2 source");
        require(b.read(s,0x1801)==0 && b.read(s,0x1808)==0 && !b.cd.ack,
                "status byte or data-only automatic ACK gating");
        b.write(s,0x1802,0xA0);status(0x98,"status ACK did not clear REQ");
        require(!b.cd.irq2() && b.cd.interrupt_active==0,"status ACK did not clear source IRQ");
        b.write(s,0x1802,0x20);advance(1499);status(0x98,"message phase fired early");
        advance(1);status(0xF8,"message phase missing at 1500 ticks");
        require(b.read(s,0xB801)==0 && b.cd.irq2(),"message byte/source IRQ mismatch");
        b.write(s,0xB802,0xA0);status(0xB8,"message ACK did not clear REQ");
        b.write(s,0xB802,0x20);advance(1499);status(0xB8,"bus-free transition fired early");
        advance(1);status(0,"message completion did not release bus");
        require(!b.cd.irq2() && b.cd.interrupt_active==0,"bus-free phase retained source IRQ");
    }
    for(bool native:{false,true}) {
        initialize(b);pce::Cpu s;s.mpr=scsi_mpr;s.a=0x31;s.pc=site(0x8D,0x1801);
        const auto before=cpu_state(s);const auto writes=b.cd.writes;
        require((native?pce::generated_step(b,s,0):pce::interpret_step(b,s,0))==pce::Exit::budget && cpu_state(s)==before && b.cd.writes==writes,
                "deadline allowed transport side effects");
        s.pc=site(0xAD,0x1901);b.io_latch=0x5A;
        const auto reads=b.cd.reads;
        const auto transport=std::tuple{b.cd.scsi.phase,b.cd.scsi.signals,b.cd.scsi.latch,b.cd.scsi.data,
            b.cd.scsi.command_size,b.cd.scsi.event,b.cd.scsi.deadline,b.cd.ack,b.cd.interrupt_active,b.cd.bram_unlocked};
        execute(b,s,native);
        require(s.a==255 && (s.p&(pce::N|pce::Z))==pce::N && s.pc==site(0xAD,0x1901)+3 &&
                b.cd.reads==reads+1 && b.cd.writes==writes && b.io_latch==0x5A &&
                transport==std::tuple{b.cd.scsi.phase,b.cd.scsi.signals,b.cd.scsi.latch,b.cd.scsi.data,
                    b.cd.scsi.command_size,b.cd.scsi.event,b.cd.scsi.deadline,b.cd.ack,b.cd.interrupt_active,b.cd.bram_unlocked},
                "decoded unused CD read changed transport/latch or failed to return FF");++checks;
        s.pc=site(0x8D,0x1811);auto expected=s;expected.pc+=3;expected.p&=static_cast<std::uint8_t>(~pce::T);expected.cycles+=5;expected.ticks+=5*expected.clock_divisor;
        const auto generation=b.generation;const auto native_before=s.native_steps,interpreted_before=s.interpreter_steps;
        execute(b,s,native);
        require(cpu_state(s)==cpu_state(expected) && b.cd.writes==writes+1 && b.io_latch==0x5A && b.generation==generation &&
                s.native_steps==native_before+(native?1:0) && s.interpreter_steps==interpreted_before+(native?0:1) &&
                transport==std::tuple{b.cd.scsi.phase,b.cd.scsi.signals,b.cd.scsi.latch,b.cd.scsi.data,
                    b.cd.scsi.command_size,b.cd.scsi.event,b.cd.scsi.deadline,b.cd.ack,b.cd.interrupt_active,b.cd.bram_unlocked},
                "decoded hole write changed SCSI/latch/storage or did not retire normally");++checks;
        // Reset must cancel both selection and a pending command request.
        b.write(s,0x1800,0);s.ticks+=75000;b.sync(s);
        b.write(s,0x1801,0);b.write(s,0x1802,0x80);b.write(s,0x1802,0);
        b.write(s,0x1804,2);s.ticks+=500000;b.sync(s);
        require(b.read(s,0x1800)==0 && !b.cd.ack && !b.cd.irq2(),"reset failed to cancel pending command transport");
        b.write(s,0x1802,0xFF);require(!b.cd.ack && b.cd.interrupt_enable==127,"reset held did not suppress ACK");
        b.write(s,0x1804,0);b.write(s,0x1800,255);s.ticks+=75000;b.sync(s);
        require(b.read(s,0x1800)==0xD0,"reset release prevented fresh selection");++checks;
    }
    initialize(b);pce::Cpu held;held.mpr=scsi_mpr;
    b.write(held,0x1801,0);b.write(held,0x1802,128);b.write(held,0x1800,0);
    held.ticks+=75000;b.sync(held);
    require(b.read(held,0x1800)==0x90 && b.cd.scsi.command_size==1,
            "held ACK at selection did not accept exactly one latched byte");
    held.ticks+=30000;b.sync(held);b.write(held,0x1802,128);
    require(b.cd.scsi.command_size==1,"held ACK accepted duplicate command bytes");
    b.write(held,0x1802,0);held.ticks+=3000;b.sync(held);
    require(b.read(held,0x1800)==0xD0,"held ACK release did not schedule another request");
    b.write(held,0x1800,1);held.ticks+=75000;b.sync(held);
    require(b.read(held,0x1800)==0xD0 && b.cd.scsi.command_size==1,
            "selection during COMMAND discarded the existing command buffer");++checks;
    initialize(b);held=pce::Cpu{};held.mpr=scsi_mpr;
    b.write(held,0x1800,0);held.ticks+=75000;b.sync(held);
    b.write(held,0x1801,0);b.write(held,0x1802,128);b.write(held,0x1802,0);
    b.write(held,0x1800,0);held.ticks+=75000;b.sync(held);
    require(b.read(held,0x1800)==0x90 && b.cd.scsi.command_size==1,
            "same-phase selection manufactured a new command REQ");
    held.ticks+=3000;b.sync(held);
    require(b.read(held,0x1800)==0x90 && b.cd.scsi.command_size==1,
            "same-phase selection spuriously rescheduled the canceled command request");++checks;
    initialize(b);held=pce::Cpu{};held.mpr=scsi_mpr;
    b.write(held,0x1800,0);held.ticks+=75000;b.sync(held);
    for(unsigned i=0;i<6;++i) {
        b.write(held,0x1801,0);b.write(held,0x1802,128);b.write(held,0x1802,0);
        if(i<5){held.ticks+=3000;b.sync(held);}
    }
    held.ticks+=450000;b.sync(held);b.write(held,0x1802,128);b.write(held,0x1802,0);
    held.ticks+=500;b.sync(held);b.write(held,0x1802,128);b.write(held,0x1802,0);
    held.ticks+=999;b.sync(held);require(b.read(held,0x1800)==0x98,"duplicate status ACK advanced the message phase");
    held.ticks+=1;b.sync(held);require(b.read(held,0x1800)==0xF8,"duplicate status ACK postponed the existing message deadline");++checks;
    initialize(b);held=pce::Cpu{};held.mpr=scsi_mpr;held.ticks=100;b.sync(held);
    held.ticks=99;bool clock_fault=false;try {b.sync(held);}catch(const pce::Fault&){clock_fault=true;}
    require(clock_fault && b.cd.scsi.master_ticks==100,"CD clock regression was accepted or changed device time");++checks;
    held.ticks=forever;b.sync(held);clock_fault=false;
    try {b.write(held,0x1800,0);}catch(const pce::Fault&){clock_fault=true;}
    require(clock_fault,"CD event scheduling overflow wrapped its guest timestamp");++checks;
    initialize(b);held=pce::Cpu{};held.mpr=scsi_mpr;
    b.write(held,0x1804,2);b.write(held,0x1801,0xAA);b.write(held,0x1804,2);
    require(b.read(held,0x1801)==0xAA,"unchanged asserted RST discarded a subsequently written host latch");++checks;
    b.write(held,0x1802,0);require(b.read(held,0x1801)==0xAA,"unchanged ACK-low while RST held reset the host latch");++checks;
    b.write(held,0x1802,128);require(b.read(held,0x1801)==0 && !b.cd.ack,"ACK rise while RST held failed to repeat the transport reset");
    b.write(held,0x1801,0xBB);b.write(held,0x1804,0);
    require(b.read(held,0x1801)==0xBB,"RST release discarded a host latch written during reset");++checks;
    for(bool native:{false,true}) {
        initialize(b);pce::Cpu s;s.mpr=scsi_mpr;
        b.write(s,0x1800,0);s.ticks+=75000;b.sync(s);
        for(unsigned i=0;i<6;++i) {
            b.write(s,0x1801,static_cast<std::uint8_t>(i==0?3:0));b.write(s,0x1802,128);
            b.write(s,0x1802,0);
            require(b.cd.sense_commands==unsigned(i==5),"REQUEST SENSE dispatched before its complete six-byte CDB");
            if(i<5) {s.ticks+=3000;b.sync(s);}
        }
        require(b.read(s,0x1800)==0xC8 && b.read(s,0x1801)==0x70 && b.cd.scsi.response_size==18,
                "Complete REQUEST SENSE did not enter bounded DATA IN with NEC header");
        initialize(b);s=pce::Cpu{};s.mpr=scsi_mpr;
        b.write(s,0x1800,0);s.ticks+=75000;b.sync(s);
        for(unsigned i=0;i<6;++i) {
            b.write(s,0x1801,0);b.write(s,0x1802,0xA0);b.write(s,0x1802,0x20);
            if(i<5){s.ticks+=3000;b.sync(s);}
        }
        s.ticks+=450000;b.sync(s);require(b.cd.irq2(),"IRQ refusal setup did not assert IRQ2");
        s.pc=site(0xEA);s.p=0;const auto cpu_before=cpu_state(s);const auto writes=b.cd.writes;
        bool refused=false;try {execute(b,s,native);}catch(const pce::Fault&){refused=true;}
        require(refused && cpu_state(s)==cpu_before && b.cd.writes==writes,
                "unimplemented CPU IRQ2 delivery was silently ignored or retired");
        s.p=4;execute(b,s,native);require(s.native_steps==unsigned(native) && s.interpreter_steps==unsigned(!native),
                "masked IRQ2 incorrectly blocked CPU execution");++checks;
    }
    initialize(b);pce::Cpu s;s.mpr=scsi_mpr;s.pc=site(0x8D,0x1801);s.a=0xA5;
    (*b.bytes)[pce::Bus::physical(s,s.pc)+1]=2;const auto before=cpu_state(s);
    require(pce::generated_step(b,s,forever)==pce::Exit::miss && cpu_state(s)==before && b.cd.writes==0,
            "mutated native transport operand caused a device write");
    require(pce::step(b,s,forever)==pce::Exit::executed && b.read(s,0x1802)==0xA5 && b.read(s,0x1801)==0,
            "mutated transport fallback used original data-latch target");
    pce::Bus strict;strict.enable_cd_control();s=pce::Cpu{};s.mpr=scsi_mpr;
    bool fault=false;try {strict.write(s,0x1801,1);}catch(const pce::Fault&){fault=true;}
    require(fault,"idle CD profile silently enabled command transport");++checks;
    return checks;
}

static void advance(pce::Bus& b,pce::Cpu& s,std::uint64_t ticks) {s.ticks+=ticks;b.sync(s);}
static void direct_de(pce::Bus& b,pce::Cpu& s,unsigned mode,unsigned track=0) {
    b.write(s,0x1800,0);advance(b,s,75000);
    for(unsigned i=0;i<10;++i) {
        const unsigned value=i==0?0xDE:i==1?mode:i==2?track:0;
        b.write(s,0x1801,static_cast<std::uint8_t>(value));b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);
        if(i<9)advance(b,s,3000);
    }
}
static void cpu_de(pce::Bus& b,pce::Cpu& s,bool native,unsigned mode,unsigned track=0) {
    instruction(b,s,native,0x8D,0xB800,0);settle(b,s,native,(75000+2*s.clock_divisor-1)/(2*s.clock_divisor));
    for(unsigned i=0;i<10;++i) {
        const unsigned value=i==0?0xDE:i==1?mode:i==2?track:0;
        instruction(b,s,native,0x8D,0x1801,value);instruction(b,s,native,0x8D,0xB802,0xE0);
        instruction(b,s,native,0x8D,0x1802,0x60);
        if(i<9)settle(b,s,native,(3000+2*s.clock_divisor-1)/(2*s.clock_divisor));
    }
    settle(b,s,native,(9000+2*s.clock_divisor-1)/(2*s.clock_divisor));
}
static unsigned toc_expectations(pce::Bus& b) {
    unsigned checks=0;
    struct Response {unsigned mode,track;std::array<unsigned,4> bytes;};
    constexpr Response responses[]={
        {0,0,{1,3,0,0}}, {1,0,{7,0x42,0x67,0}},
        {2,0,{0,2,0,4}}, {2,1,{0,2,0,4}}, {2,2,{2,0x46,0x45,0}},
        {2,3,{5,0x14,0x56,4}}, {2,4,{7,0x42,0x67,0}}, {2,0x99,{7,0x42,0x67,0}},
        {2,0xAA,{7,0x42,0x67,0}} // Explicit leadout sentinel, rather than an invalid BCD track.
    };
    for(bool native:{false,true})for(unsigned divisor:{3U,12U})for(bool automatic:{false,true})for(const auto& response:responses) {
        initialize(b);b.cd.set_toc(authored_toc());pce::Cpu s;s.mpr=scsi_mpr;s.clock_divisor=divisor;s.p=0xA5;
        cpu_de(b,s,native,response.mode,response.track);
        require(b.read(s,0x1800)==0xC8 && b.cd.interrupt_active==0x40 && b.cd.irq2(),"TOC DATA IN phase/IRQ40");
        for(unsigned index=0;index<4;++index) {
            const auto flags=s.p;
            instruction(b,s,native,0xAD,automatic?0xB808:0x1801);
            require(s.a==response.bytes[index] && s.p==((flags&0x5D)|(response.bytes[index]&128)|(response.bytes[index]==0?2:0)),
                    "TOC CPU data byte or NZ/T flags");
            if(!automatic) {
                require(b.read(s,0xB801)==response.bytes[index] && !b.cd.ack && b.read(s,0x1800)==0xC8,
                        "ordinary DATA IN read consumed or acknowledged a byte");
                instruction(b,s,native,0x8D,0x1802,0xE0);instruction(b,s,native,0x8D,0xB802,0x60);
            }
            settle(b,s,native,(4000+2*divisor-1)/(2*divisor));++checks;
        }
        require(b.read(s,0x1800)==0xD8 && b.read(s,0x1801)==0 && b.cd.interrupt_active==0x20,
                "TOC final data ACK did not reach GOOD status/IRQ20");
        instruction(b,s,native,0x8D,0x1802,0xE0);instruction(b,s,native,0x8D,0x1802,0x60);
        settle(b,s,native,(1500+2*divisor-1)/(2*divisor));
        require(b.read(s,0x1800)==0xF8,"TOC status did not enter MESSAGE IN");
        instruction(b,s,native,0x8D,0x1802,0xE0);instruction(b,s,native,0x8D,0x1802,0x60);
        settle(b,s,native,(1500+2*divisor-1)/(2*divisor));
        require(b.read(s,0x1800)==0 && !b.cd.irq2(),"TOC message did not release bus");
        require(native ? s.interpreter_steps==0:s.native_steps==0,"TOC operation or settling used the wrong tier");++checks;
    }
    // Literal master-clock edges, independent of CPU access phase placement.
    initialize(b);b.cd.set_toc(authored_toc());pce::Cpu s;s.mpr=scsi_mpr;direct_de(b,s,0);
    advance(b,s,8999);require(b.read(s,0x1800)==0x90,"TOC response fired before 9000 ticks");
    advance(b,s,1);require(b.read(s,0x1800)==0xC8 && b.read(s,0x1801)==1,"TOC first DATA IN byte/REQ missing at 9000 ticks");++checks;
    b.write(s,0x1802,0xE0);require(b.read(s,0x1800)==0x88 && !b.cd.irq2(),"manual DATA IN ACK rise failed to drop REQ/IRQ40");
    b.write(s,0x1802,0x60);require(b.read(s,0x1801)==3,"next DATA IN byte not presented on ACK fall");
    advance(b,s,899);require(b.read(s,0x1800)==0x88,"next TOC REQ fired before 900 ticks");
    advance(b,s,1);require(b.read(s,0x1800)==0xC8 && b.cd.irq2(),"next TOC REQ missing at 900 ticks");++checks;
    require(b.read(s,0xB808)==3 && b.cd.ack && b.read(s,0x1800)==0x88,"automatic ACK read did not latch the current byte/drop REQ");
    advance(b,s,10);require(b.read(s,0x1808)==3,"early automatic ACK read changed the current byte");
    advance(b,s,10);require(b.cd.ack,"automatic ACK released before 21 ticks");
    advance(b,s,1);require(!b.cd.ack && b.read(s,0x1801)==0 && b.read(s,0x1800)==0x88,
            "automatic ACK did not release at 21 ticks or load the next byte");++checks;
    advance(b,s,899);require(b.read(s,0x1800)==0x88,"automatic ACK next REQ fired early");
    advance(b,s,1);require(b.read(s,0x1800)==0xC8,"automatic ACK next REQ did not arrive at 900 ticks");++checks;
    // Held ACK must consume a delayed REQ once, without allowing an extra byte.
    b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);b.write(s,0x1802,0xE0);
    advance(b,s,900);require(b.read(s,0x1800)==0x88 && b.cd.ack && b.read(s,0x1801)==0,
            "held ACK did not consume a delayed final TOC REQ");
    advance(b,s,1000);require(b.read(s,0x1800)==0x88,"held ACK advanced past the final DATA IN byte");
    b.write(s,0x1802,0x60);advance(b,s,2999);require(b.read(s,0x1800)==0x88,"GOOD status fired before final DATA IN ACK plus 3000 ticks");
    advance(b,s,1);require(b.read(s,0x1800)==0xD8,"GOOD status missing after final DATA IN ACK plus 3000 ticks");++checks;
    // Response reset cancels both auto-ACK and pending byte events but keeps
    // the explicitly attached disc metadata available for the next command.
    for(unsigned point:{0U,1U,2U}) {
        initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);
        if(point==1)b.read(s,0x1808);
        if(point==2){b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);}
        b.write(s,0x1804,2);advance(b,s,10000);require(b.read(s,0x1800)==0 && !b.cd.ack && !b.cd.irq2(),"reset left a DATA IN response or auto-ACK event active");
        b.write(s,0x1804,0);direct_de(b,s,0);advance(b,s,9000);
        require(b.read(s,0x1801)==1,"reset discarded attached TOC metadata");++checks;
    }
    initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);
    b.write(s,0x1802,0xE0);advance(b,s,9000);
    require(b.read(s,0x1800)==0x88 && b.cd.ack && !b.cd.irq2(),"held ACK at DATA IN entry manufactured a first-byte REQ");
    b.write(s,0x1802,0x60);require(b.read(s,0x1800)==0xC8 && b.read(s,0x1801)==1,
            "ACK release at DATA IN entry did not present the first response byte");++checks;
    b.write(s,0x1800,0);require(b.read(s,0x1800)==0xD8 && b.read(s,0x1801)==0 && b.cd.interrupt_active==0x60,
            "selection during DATA IN did not start its eight-byte GOOD status");
    b.write(s,0x1802,0x40);
    require(b.cd.irq2() && b.cd.interrupt_active==0x60,"DATA IN reselection discarded the retained IRQ40 source while STATUS REQ remained asserted");
    b.write(s,0x1802,0x60);++checks;
    // Acknowledging this special status presents eight bytes at 1500 ticks
    // each before MESSAGE IN, rather than treating the first byte as complete.
    for(unsigned i=0;i<8;++i) {
        require(b.read(s,0x1800)==0xD8 && b.read(s,0x1801)==0,"DATA IN reselection GOOD status byte missing");
        b.write(s,0x1802,0xE0);
        require(b.cd.interrupt_active==0 && !b.cd.irq2(),"reselection STATUS ACK rise did not clear both IRQ20 and retained IRQ40");
        b.write(s,0x1802,0x60);advance(b,s,1499);
        require(b.read(s,0x1800)==0x98,"reselection status response arrived before 1500 ticks");
        advance(b,s,1);require(b.read(s,0x1800)==(i==7?0xF8:0xD8),"reselection eight-byte status length/REQ timing");++checks;
    }
    initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);b.write(s,0x1800,0);
    advance(b,s,899999);require(b.read(s,0x1800)==0xD8,"DATA IN reselection command phase fired before 900000 ticks");
    advance(b,s,1);require(b.read(s,0x1800)==0xD0,"DATA IN reselection command phase missing at 900000 ticks");++checks;
    for(unsigned mode:{0U,1U,2U}) {
        initialize(b);s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,mode,1);
        require(b.read(s,0x1800)==0xD8 && b.read(s,0x1801)==2 && b.cd.interrupt_active==0x20,
                "TOC without attached media did not report CHECK CONDITION");
        b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);advance(b,s,1500);
        require(b.read(s,0x1800)==0xF8 && b.read(s,0x1801)==2,"CHECK CONDITION message did not preserve the reference data bus");++checks;
    }
    for(auto request:std::array<std::pair<unsigned,unsigned>,4>{{{3,0},{255,0},{2,0x1A},{2,255}}}) {
        initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;
        bool fault=false;try {direct_de(b,s,request.first,request.second);}catch(const pce::Fault&){fault=true;}
        require(fault && b.cd.scsi.last_command_size==10 && b.cd.scsi.last_command[0]==0xDE,
                "unsupported TOC mode or malformed BCD did not fault with its complete CDB");++checks;
    }
    for(unsigned opcode:{8U,0xD8U,0xD9U,0xDAU,0xDDU}) {
        initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;
        b.write(s,0x1800,0);advance(b,s,75000);const unsigned length=opcode==8?6:10;
        for(unsigned i=0;i<length;++i) {
            b.write(s,0x1801,static_cast<std::uint8_t>(i==0?opcode:0));b.write(s,0x1802,128);
            bool fault=false;try {b.write(s,0x1802,0);}catch(const pce::Fault&){fault=true;}
            require(fault==(i==length-1),"attaching TOC metadata silently enabled unsupported sector/audio/subchannel semantics");
            if(i<length-1)advance(b,s,3000);
        }
        require(b.cd.scsi.last_command_size==length && b.cd.scsi.last_command[0]==opcode,
                "unsupported sector/audio/subchannel command did not retain its complete CDB");++checks;
    }
    for(unsigned variant=0;variant<10;++variant) {
        initialize(b);const auto original=authored_toc();b.cd.set_toc(original);auto invalid=original;
        switch(variant) {
        case 0:invalid.track_count=0;break;case 1:invalid.track_count=100;break;
        case 2:invalid.tracks[1].index1_lba=0;break;case 3:invalid.tracks[2].index1_lba=100;break;
        case 4:invalid.leadout_lba=23456;break;case 5:invalid.leadout_lba=449850;break;
        case 6:invalid.tracks[1].type=1;break;case 7:invalid.image_sha256="invalid";break;
        case 8:invalid.image_sha256=std::string(64,'A');break;case 9:invalid.leadout_lba=0;break;
        }
        bool fault=false;try {b.cd.set_toc(invalid);}catch(const pce::Fault&){fault=true;}
        require(fault,"invalid attached TOC was accepted");
        s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);
        require(b.read(s,0x1801)==1,"rejected TOC damaged the previous metadata");
        b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);advance(b,s,900);
        require(b.read(s,0x1801)==3,"rejected TOC replaced the previous track count");++checks;
    }
    for(unsigned tracks:{1U,9U,10U,12U,42U,99U}) {
        constexpr unsigned counts[]={0,1,0,0,0,0,0,0,0,9,0x10,0,0x12};
        const unsigned expected=tracks<13?counts[tracks]:tracks==42?0x42:0x99;
        initialize(b);pce::CdToc toc;toc.track_count=tracks;toc.leadout_lba=449849;
        for(unsigned i=0;i<tracks;++i)toc.tracks[i]={i*75,4};b.cd.set_toc(toc);
        s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);
        b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);advance(b,s,900);
        require(b.read(s,0x1801)==expected,"TOC track count did not use packed decimal");++checks;
    }
    initialize(b);auto maximum=authored_toc();maximum.leadout_lba=449849;b.cd.set_toc(maximum);
    s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,1);advance(b,s,9000);
    for(unsigned expected:{0x99U,0x59U,0x74U,0U}) {
        require(b.read(s,0x1801)==expected,"maximum representable TOC leadout MSF");
        b.write(s,0x1802,0xE0);b.write(s,0x1802,0x60);advance(b,s,900);++checks;
    }
    for(unsigned point:{0U,1U,2U}) {
        initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;
        if(point==0)b.write(s,0x1800,0);
        if(point==1){b.write(s,0x1802,128);}
        if(point==2){direct_de(b,s,0);advance(b,s,9000);b.read(s,0x1808);}
        bool fault=false;try {b.cd.set_toc(authored_toc(true));}catch(const pce::Fault&){fault=true;}
        require(fault,"TOC attachment changed metadata during an active bus/event/auto-ACK");++checks;
    }
    for(bool native:{false,true}) {
        initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);
        s.pc=site(0xEA);s.p=0;const auto before=cpu_state(s);bool fault=false;
        try {execute(b,s,native);}catch(const pce::Fault&){fault=true;}
        require(fault && cpu_state(s)==before && b.cd.interrupt_active==0x40,"DATA IN IRQ40 did not refuse unimplemented CPU interrupt delivery");++checks;
    }
    initialize(b);b.cd.set_toc(authored_toc());s=pce::Cpu{};s.mpr=scsi_mpr;direct_de(b,s,0);advance(b,s,9000);
    s.pc=site(0xAD,0x1808);auto before=cpu_state(s);const auto reads=b.cd.reads;
    require(pce::generated_step(b,s,s.ticks)==pce::Exit::budget && cpu_state(s)==before && !b.cd.ack && b.cd.reads==reads,
            "deadline produced an automatic ACK read side effect");
    (*b.bytes)[pce::Bus::physical(s,s.pc)+1]=1;
    require(pce::generated_step(b,s,forever)==pce::Exit::miss && cpu_state(s)==before && !b.cd.ack && b.cd.reads==reads,
            "stale native auto-ACK operand consumed response state");
    require(pce::step(b,s,forever)==pce::Exit::executed && s.a==1 && !b.cd.ack && b.read(s,0x1800)==0xC8,
            "mutated auto-ACK read fallback used its original side-effecting target");++checks;
    pce::CdControl disabled;bool disabled_fault=false;
    try {disabled.set_toc(authored_toc());}catch(const pce::Fault&){disabled_fault=true;}
    require(disabled_fault,"metadata attachment silently enabled a disabled CD transport");++checks;
    return checks;
}

int main(int argc,char** argv) {
    try {
        if(argc==4 && (std::string(argv[1])=="--probe" || std::string(argv[1])=="--probe-toc" || std::string(argv[1])=="--probe-unknown"))
            return probe(argv[2],argv[3],std::string(argv[1])=="--probe-toc",std::string(argv[1])=="--probe-unknown");
        if(argc!=1)return 2;
        pce::Bus b;const auto count=expectations(b);const auto toc_count=toc_expectations(b);
        std::cout<<count<<" independently expected CD command/data transport checks passed; both execution tiers, handshake timing, aliases, reset and guards\n";
        std::cout<<toc_count<<" independently expected TOC DATA IN groups passed; manual/automatic ACK, both tiers and speeds\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
