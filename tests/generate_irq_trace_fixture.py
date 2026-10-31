"""Authored software-only IRQ primer, finite instruction ledgers and literals.

All cases use one instruction pool. Per-case images differ only in reset-vector
bytes. The source-plan capture used for static emission is authored metadata,
not a claim that a guest has already executed it.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
INITIAL_MPR=(0,)*8
FINAL_MPR=(255,248,0,0,0,0,0,0)
TIMER_HANDLER=0xF800
BRK_HANDLER=0xF820
REMAPPED_HANDLER=0xF840
IRQ1_HANDLER=0xF860
ENC={'sei':0x78,'cli':0x58,'cld':0xD8,'clv':0xB8,'clc':0x18,'clx':0x82,
     'cly':0xC2,'cla':0x62,'nop':0xEA,'set':0xF4,'pha':0x48,'plp':0x28,
     'rti':0x40,'txs':0x9A,'dex':0xCA,'csl':0x54,'csh':0xD4}


def encode(op,pc=0):
    name=op[0]
    if name in ENC:return bytes((ENC[name],))
    if name in ('lda','ldx','tam'):return bytes(({'lda':0xA9,'ldx':0xA2,'tam':0x53}[name],op[1]))
    if name in ('sta','inc'):return bytes((0x8D if name=='sta' else 0xEE,op[1]&255,op[1]>>8))
    if name=='brk':return bytes((0,0xA5))
    if name=='bne':return bytes((0xD0,(op[1]-pc-2)&255))
    if name=='tii':return bytes.fromhex('73 00 20 01 20 FF 1F')
    raise ValueError('Unknown authored operation '+name)


def definitions():
    return [
        dict(id='timer-cli-low',speed=12,sp=255,kind='cli'),
        dict(id='timer-cli-high',speed=3,sp=255,kind='cli'),
        dict(id='timer-cli-wrap',speed=3,sp=1,kind='cli'),
        dict(id='timer-pending-sei',speed=3,sp=255,kind='sei'),
        dict(id='timer-decimal-SET-stack',speed=3,sp=255,kind='decimal'),
        dict(id='timer-PLP-delay',speed=3,sp=1,kind='plp'),
        dict(id='timer-RTI-held-line',speed=3,sp=255,kind='rti'),
        dict(id='timer-mask-during-STA',speed=3,sp=255,kind='mask',acc=4),
        dict(id='timer-unmask-during-STA',speed=3,sp=255,kind='unmask',mask=4,acc=0),
        dict(id='timer-pending-BRK',speed=3,sp=1,kind='brk'),
        dict(id='PLP-raw-B-representation',speed=3,sp=255,kind='saved-b',mask=4),
        dict(id='timer-CSL-transition',speed=3,sp=255,kind='csl'),
        dict(id='timer-CSH-transition',speed=12,sp=255,kind='csh'),
        dict(id='timer-I-masked',speed=3,sp=255,kind='masked'),
        dict(id='timer-remapped-vector',speed=3,sp=1,kind='remap'),
    ]


def bootstrap(entry,case):
    code=bytearray();executed=[];mapping=list(INITIAL_MPR);a=0
    def add(op):
        nonlocal a
        pc=entry+len(code);raw=encode(op,pc)
        executed.append(dict(pc=pc,mpr=list(mapping),data=list(raw)))
        code.extend(raw)
        if op[0]=='lda':a=op[1]
        elif op[0]=='tam':
            for page in range(8):
                if op[1]&(1<<page):mapping[page]=a
        return pc
    for op in [('sei',),('lda',0),('tam',0xFD),('lda',248),('tam',2),
               ('lda',0),('sta',0x2000),('tii',),('lda',255),('tam',1)]:add(op)
    if case['speed']==3:add(('csh',))
    for op in [('lda',0),('sta',0x0C00),('lda',case.get('mask',0)),('sta',0x1402),
               ('lda',1),('sta',0x0C01),('ldx',0)]:add(op)
    loop=entry+len(code);loop_entries=[]
    for op in [('nop',),('dex',),('bne',loop)]:
        add(op);loop_entries.append(executed[-1])
    executed.extend(dict(item) for _ in range(255) for item in loop_entries)
    for op in [('lda',0),('sta',0x0C01),('ldx',case['sp']),('txs',),('clx',),('cly',),
               ('cld',),('clv',),('clc',),('lda',1)]:add(op)
    if case.get('acc')==0:add(('cla',))
    elif case.get('acc')==4:add(('lda',4))
    if len(code)>128:raise ValueError('Authored primer overlaps case region')
    assert tuple(mapping)==FINAL_MPR
    return bytes(code),executed


def measured(marker,kind):
    if kind=='cli':ops=[('cli',),('nop',)]
    elif kind=='sei':ops=[('cli',),('sei',)]
    elif kind=='decimal':ops=[('sed',),('cli',),('set',)]
    elif kind=='plp':ops=[('lda',0x28),('pha',),('plp',),('nop',)]
    elif kind=='rti':ops=[('lda',0),('pha',),('lda',0),('pha',),('lda',0x28),('pha',),('rti',),('nop',)]
    elif kind in ('mask','unmask'):ops=[('cli',),('sta',0x1402)]+([('nop',)] if kind=='unmask' else [])
    elif kind=='brk':ops=[('cli',),('brk',)]
    elif kind=='saved-b':ops=[('lda',0x14),('pha',),('plp',)]
    elif kind in ('csl','csh'):ops=[('cli',),(kind,)]
    elif kind=='masked':ops=[('nop',),('sei',)]
    elif kind=='remap':ops=[('lda',1),('tam',128),('cli',),('nop',)]
    else:raise ValueError('Unknown authored case')
    ops.append(('sentinel',))
    if kind=='rti':
        target=marker+sum(len(encode(op)) for op in ops[:6])+1
        ops[0]=('lda',target>>8);ops[2]=('lda',target&255)
    program={};code=bytearray()
    for op in ops:
        pc=marker+len(code);program[pc]=op
        code.extend(bytes((0xF8,)) if op[0]=='sed' else bytes((0xEA,)) if op[0]=='sentinel' else encode(op,pc))
    return bytes(code)+bytes.fromhex('80 FE'),program,marker+len(code)


def handler(target,cell):
    operations=[('lda',0),('sta',0x0C01),('sta',0x1403),('inc',cell),('rti',)]
    code=bytearray();program={}
    for op in operations:
        pc=target+len(code);program[pc]=op;code.extend(encode(op,pc))
    return bytes(code),program


def literals(case,program,end,rom,profile):
    """Finite authored instruction ledger; no general decoder or CPU core."""
    ram=bytearray(8192);mpr=list(FINAL_MPR)
    pc=case['marker'];a=case.get('acc',1);x=y=0;sp=case['sp'];p=4;divisor=case['speed'];ticks=0
    latch=255;pending=True;mask=case.get('mask',0);entries=vector=rti=0;rows=[];sources=[]
    def push(value):
        nonlocal sp
        ram[0x100+sp]=value&255;sp=(sp-1)&255
    def pop():
        nonlocal sp
        sp=(sp+1)&255;return ram[0x100+sp]
    def nz(value):
        nonlocal p
        p=(p&~130)|(value&128)|(2 if value==0 else 0)
    def row(ordinal,irq):
        values=[pc,a,x,y,sp,p,divisor,ticks,*mpr,latch,entries,vector,rti,int(pending),mask,0,ram[0x10],ram[0x11],ram[0x12]]
        digest=hashlib.sha256(ram).hexdigest()
        state=dict(pc=pc,a=a,x=x,y=y,sp=sp,p=p,mpr=list(mpr),mpr_latch=latch,
            physical_pc=(mpr[pc>>13]<<13)|(pc&8191),clock_divisor=divisor,ticks=ticks,wram_sha256=digest)
        return dict(ordinal=ordinal,values=values,state=state,wram_sha256=digest,irq_count=int(irq),irq_vector=0xFFFA if irq else None)
    initial=row(0,False)
    while pc!=end:
        if len(rows)>=64:raise ValueError('Authored ledger did not reach its sentinel')
        entry=pc;op=program[pc];name=op[0]
        raw=bytes((0xF8,)) if name=='sed' else bytes((0xEA,)) if name=='sentinel' else encode(op,pc)
        source=dict(pc=pc,mpr=list(mpr),data=list(raw));sources.append(source)
        sampled=not(p&4) and not(mask&4) and pending
        pc=(pc+len(raw))&65535;cycles=2
        if name=='lda':a=op[1];nz(a)
        elif name=='sta':
            cycles=5
            if op[1]==0x1402:mask=a&7
            elif op[1]==0x1403:pending=False
            elif op[1]!=0x0C01:raise ValueError('Unauthored store')
        elif name=='inc':
            cycles=7;offset=op[1]&8191;ram[offset]=(ram[offset]+1)&255;nz(ram[offset])
        elif name=='pha':push(a);cycles=3
        elif name=='plp':p=pop()&~16;cycles=4
        elif name=='rti':
            p=pop()&~16;low=pop();pc=low|(pop()<<8);cycles=7;rti+=1
        elif name=='brk':
            push(pc>>8);push(pc);push((p|16)&~32);p=(p|4)&~40;pc=BRK_HANDLER;cycles=8
        elif name=='cli':p &=~4
        elif name=='sei':p |=4
        elif name=='sed':p |=8
        elif name=='set':p |=32
        elif name=='tam':
            for page in range(8):
                if op[1]&(1<<page):mpr[page]=a
            latch=a;cycles=5
        elif name in ('csl','csh'):
            next_divisor=12 if name=='csl' else 3
            ticks+=2*divisor+next_divisor if profile=='runtime' else 3*next_divisor
            divisor=next_divisor;cycles=0
        elif name not in ('nop','sentinel'):raise ValueError('Unauthored ledger operation')
        if name not in ('set','plp','rti'):p &=~32
        ticks+=cycles*divisor
        accepted=sampled and pending
        if accepted:
            push(pc>>8);push(pc);push(p&~16);p=(p|4)&~40
            pc=REMAPPED_HANDLER if mpr[7]==1 else TIMER_HANDLER
            ticks+=8*divisor;entries+=1;vector=0xFFFA
        rows.append(row(len(rows)+1,accepted))
    return initial,rows,sources


def authored_fixture():
    pool=bytearray([0xEA]*262144);programs={};cases=[];all_sources=[]
    for target,cell in ((TIMER_HANDLER,0x2010),(BRK_HANDLER,0x2011),(REMAPPED_HANDLER,0x2012),(IRQ1_HANDLER,0x2013)):
        code,program=handler(target,cell);pool[target&8191:(target&8191)+len(code)]=code;programs.update(program)
    for index,definition in enumerate(definitions()):
        case=dict(definition);entry=0xE000+index*256;boot,executed=bootstrap(entry,case)
        case.update(entry=entry,marker=entry+len(boot),primer_steps=len(executed),rom=case['id']+'.pce')
        code,program,end=measured(case['marker'],case['kind']);case['end_pc']=end
        pool[entry&8191:(entry&8191)+len(boot)]=boot;pool[case['marker']&8191:(case['marker']&8191)+len(code)]=code
        programs.update(program);case['primer_sources']=executed;cases.append(case)
    for vector,target in ((0xFFF6,BRK_HANDLER),(0xFFF8,IRQ1_HANDLER),(0xFFFA,TIMER_HANDLER)):
        pool[vector&8191:(vector&8191)+2]=target.to_bytes(2,'little')
    pool[8192:16384]=pool[:8192]
    pool[8192+(0xFFFA&8191):8192+(0xFFFA&8191)+2]=REMAPPED_HANDLER.to_bytes(2,'little')
    for case in cases:
        for profile in ('runtime','gear'):
            initial,rows,sources=literals(case,programs,case['end_pc'],pool,profile)
            case['initial']=initial;case['expected_initial_'+profile]=initial;case['expected_'+profile]=rows
            if profile=='runtime':case['steps']=len(rows);case['measured_sources']=sources
        case['known_beetle_difference']=dict(
            rti=dict(ordinal=7,field='pc',value=TIMER_HANDLER,first_field='irq_count',first_expected=0,first_actual=1,
                     reason='Original RTI samples restored I at LastCycle; selected Gear profile samples entry I.'),
            mask=dict(ordinal=2,field='pc',
                      value=case['measured_sources'][1]['pc']+len(case['measured_sources'][1]['data']),
                      first_field='irq_count',first_expected=1,first_actual=0,
                      reason='Original timer delivery rechecks the live timer mask.'),
            unmask=dict(ordinal=2,field='pc',value=TIMER_HANDLER,first_field='irq_count',first_expected=0,first_actual=1,
                        reason='Original timer delivery rechecks the live timer mask.'),
            brk=dict(ordinal=2,field='pc',value=BRK_HANDLER,first_field='irq_count',first_expected=1,first_actual=0,
                     reason='Original BRK sets I before LastCycle and suppresses a second sampled hardware entry.'),
            **{'saved-b':dict(ordinal=3,field='p',value=case['expected_runtime'][2]['state']['p']|16,
                             first_field='state.p',first_expected=case['expected_runtime'][2]['state']['p'],
                             first_actual=case['expected_runtime'][2]['state']['p']|16,
                             reason='Original POP restores raw B; Gear profile represents live B as zero.')}
        ).get(case['kind'])
        counts=Counter()
        records={}
        for source in case['primer_sources']+case['measured_sources']:
            pc=source['pc'];mapping=source['mpr'];physical=[(mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191) for i in range(len(source['data']))]
            if list(pool[address] for address in physical)!=source['data']:raise ValueError('Authored source identity conflicts')
            key=(pc,tuple(mapping),tuple(physical),tuple(source['data']));counts[key]+=1;records[key]=dict(source,physical=physical)
        case['source_hits']=[dict(records[key],hits=counts[key]) for key in sorted(counts)]
        all_sources.extend(dict(records[key],native_hits=0,interpreted_hits=1) for key in sorted(counts))
    unique={(row['pc'],tuple(row['mpr']),tuple(row['physical']),tuple(row['data'])):row for row in all_sources}
    return pool,cases,list(unique.values())


def generate(out,emit_module=True):
    from pcerecomp.abi import ABI
    out=Path(out);out.mkdir(parents=True,exist_ok=True);pool,cases,sources=authored_fixture()
    for case in cases:
        rom=bytearray(pool);rom[8190:8192]=case['entry'].to_bytes(2,'little')
        (out/case['rom']).write_bytes(rom);case['rom_sha256']=hashlib.sha256(rom).hexdigest()
    if emit_module:
        from pcerecomp.emitter import emit_capture
        capture=dict(schema=1,runtime_abi=ABI,capacity=len(sources),dropped_instructions=0,unreadable_instructions=0,
                     retired_instructions=len(sources),complete=True,observations=sources)
        with TemporaryDirectory(prefix='irq-authored-',dir=out) as stage:
            target=Path(stage)/'module';emit_capture(capture,target,single_unit=True)
            for path in target.iterdir():(out/path.name).write_bytes(path.read_bytes())
    header=['#pragma once','#include <array>','#include <cstdint>','#include <string>','#include <stdexcept>','#include <vector>','#include <utility>',
        'struct IrqLiteral { std::array<std::uint64_t,26> values; const char* wram_sha256; unsigned irq_count; unsigned irq_vector; };',
        'struct IrqCase { const char* id; const char* rom; unsigned entry,primer_steps,steps,marker,end_pc; IrqLiteral initial; const IrqLiteral* runtime_rows; const IrqLiteral* gear_rows; };']
    def literal(row):return '{{'+','.join(map(str,row['values']))+'},"'+row['wram_sha256']+'",'+str(row['irq_count'])+','+str(row['irq_vector'] or 0)+'}'
    for index,case in enumerate(cases):
        for profile in ('runtime','gear'):
            header.append(f'inline constexpr IrqLiteral irq_{index}_{profile}[]'+'{'+','.join(literal(row) for row in case['expected_'+profile])+'};')
    header.append('inline constexpr IrqCase irq_cases[]{')
    for index,case in enumerate(cases):
        header.append('{"'+case['id']+'","'+case['rom']+'",'+','.join(str(case[key]) for key in ('entry','primer_steps','steps','marker','end_pc'))+','+literal(case['initial'])+f',irq_{index}_runtime,irq_{index}_gear'+'},')
    header += ['};','inline const IrqCase& irq_case(const std::string& name){for(const auto& item:irq_cases)if(name==item.id)return item;throw std::runtime_error("Unknown authored IRQ case");}',
        'inline std::vector<std::uint8_t> irq_rom(const IrqCase& item){std::vector<std::uint8_t> rom(262144,0xEA);',
        'static constexpr std::pair<std::uint32_t,std::uint8_t> bytes[]{'+','.join('{'+str(i)+','+str(value)+'}' for i,value in enumerate(pool) if value!=0xEA)+'};',
        'for(auto [physical,value]:bytes)rom[physical]=value;rom[8190]=item.entry&255;rom[8191]=item.entry>>8;return rom;}','']
    (out/'irq_boundary_fixture.hpp').write_text('\n'.join(header),encoding='utf-8')
    metadata=dict(schema=1,runtime_abi=ABI,cases=cases,initial_mpr=list(INITIAL_MPR),measured_mpr=list(FINAL_MPR),
        initialization='Only guest opcodes: SEI, MPR writes, full WRAM clear via TII, real timer start/delay/disable preserving pending request, explicit SP/A/X/Y/P. No host CPU, RAM, MPR, IRQ or timer seeds.',
        literal_clock='Elapsed ticks from actual post-primer marker; raw trace timestamps are never rewritten.',
        scope='Finite timer-only IRQ instruction boundaries. IRQ1/IRQ2 source priority and VDC acknowledge phases are not qualified. Native source plan is authored static metadata, not an execution capture.')
    (out/'fixture.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':generate(Path(sys.argv[1]))
