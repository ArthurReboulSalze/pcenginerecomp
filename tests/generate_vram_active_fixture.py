"""Authored active-display programs and an independent steady-raster oracle.

CPU prefixes, register latches and scheduling targets come from software and
integer equations. No captured beam position or runtime code supplies goldens.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from generate_irq_device_fixture import Program,encode,source,LITERAL_COLUMNS

ROOT=Path(__file__).resolve().parent.parent
LINE=1365
FRAME=262*LINE
HSR,HDR,VPR,VDW,VCR=0x0202,0x7F1D,0x0F02,239,2
DATA,DEST,SAT=0x6000,0x6100,0x7000
PAYLOAD,SECOND,TAIL=0xA65C,0x5AA5,0x0F3E


def definitions():
    result=[]
    for speed,label in((12,'low'),(3,'high')):
        for divider in(4,3,2):
            for mode in range(4):
                for access in('read','write','rmw'):
                    result.append(dict(id=f'bg-m{mode}-{access}-{label}-vce{divider}',
                        family='bg',access=access,speed=speed,divider=divider,mwr=mode,cr=128,cells=0))
            for mode in range(4):
                for cells in(1,4):
                    result.append(dict(id=f'sprite-m{mode}-c{cells}-{label}-vce{divider}',
                        family='sprite',access='read',speed=speed,divider=divider,mwr=mode<<2,cr=64,cells=cells))
            for cells in(1,4,16):
                result.append(dict(id=f'end-dual-c{cells}-{label}-vce{divider}',family='boundary',
                    access='dual',speed=speed,divider=divider,mwr=15,cr=64,cells=cells))
    for case in result:
        case['sp']=255;case['queued_accesses']=True
        case['wide']=case['cells']>1
        case['sat_sprites']=case['cells']//2 if case['wide']else case['cells']
        case['acc']=0xA6 if case['access']in('write','dual')else 1
        case['vce_control']={4:0,3:1,2:2}[case['divider']]
    return result


def cpu_clock(case,operations,profile):
    ticks=0;divisor=12;a=0;mapping=[0]*8;sources=[];rows=[]
    for pc,op in operations:
        entry=ticks;name=op[0];cycles=2;sources.append(source(pc,mapping,op))
        if name=='lda':a=op[1]
        elif name=='tam':
            cycles=5
            for page in range(8):
                if op[1]&(1<<page):mapping[page]=a
        elif name=='tii':cycles=17+6*op[3]
        elif name=='load':cycles=5
        elif name=='sta':cycles=5+int(op[1]<0x800)
        elif name=='csh':
            ticks+=2*divisor+3 if profile=='runtime'else 9;divisor=3;cycles=3
        if name!='csh':ticks+=cycles*divisor
        rows.append(dict(pc=pc,entry_ticks=entry,after_ticks=ticks,clock_divisor=divisor,cycles=cycles))
    return dict(ticks=ticks,mapping=mapping,sources=sources,clocks=rows)


def write_word(p,address,value):
    p.register(0,address);p.register(2,value);p.delay(100)


def pad(p,cycles):
    """WRAM-only transfers plus ordinary 2/5-cycle ops; never seed a clock."""
    while cycles>36050:p.delay(6000);cycles-=36017
    if cycles>=23:
        for length in range(min(6000,(cycles-17)//6),0,-1):
            rest=cycles-(17+6*length)
            if rest%2==0 or rest>=5:
                p.delay(length);cycles=rest;break
    if cycles%2:
        if cycles<5:raise ValueError('Unrepresentable authored padding')
        p.add('load',0x2200);cycles-=5
    for _ in range(cycles//2):p.add('nop')


def make_program(case):
    p=Program(0xE000)
    for op in[('sei',),('lda',0),('tam',0xFD),('lda',248),('tam',2),('lda',0),
              ('sta',0x2000),('tii',0x2000,0x2001,8191),('lda',255),('tam',1)]:p.add(*op)
    if case['speed']==3:p.add('csh')
    p.add('lda',7);p.add('sta',0x1402)
    p.add('lda',case['vce_control']);p.add('sta',0x400)
    for register,value in((5,0),(9,0),(10,HSR),(11,HDR),(12,VPR),(13,VDW),(14,VCR),(15,0)):
        p.register(register,value)
    # Transparent/offscreen sprites still consume the admitted 16px cells.
    for index in range(case['sat_sprites']):
        for offset,value in enumerate((64,0,0,0x2000|(256 if case['wide']else 0))):
            write_word(p,SAT+4*index+offset,value)
    for address,value in((DATA,PAYLOAD),(DATA+1,SECOND),(DATA+2,TAIL)):write_word(p,address,value)
    p.register(1,DATA);p.delay(100)
    p.register(0,DEST);p.register(9,case['mwr']);p.register(5,case['cr'])
    # Arm SATB last: ordinary data setup never waits on this later DMA.
    p.register(19,SAT);p.add('lda',2);p.add('sta',0)
    for _ in range(8):p.delay(6000)
    before_padding=cpu_clock(case,list(p.ops.items()),'runtime')['ticks']
    end=(296 if case['divider']==3 else 288)*case['divider']
    hpos=306 if case['family']=='bg'else end+24 if case['family']=='sprite'else end-324
    frame=before_padding//FRAME+2
    while True:
        target=frame*FRAME+64*LINE+hpos
        delta=target-before_padding-33*case['speed']
        if delta>0 and delta%case['speed']==0:break
        frame+=1
    pad(p,delta//case['speed'])
    for op in[('lda',0),('sta',0x2100),('sta',0x21FF),('sta',0x21FE),('ldx',255),('txs',),
              ('clx',),('cly',),('cld',),('clv',),('clc',),('lda',case['acc'])]:p.add(*op)
    marker=p.pc;primer=list(p.ops.items())
    if case['access']=='write':p.add('sta',3);p.add('sta',2)
    elif case['access']=='dual':p.add('sta',3);p.add('load',3);p.add('load',2)
    else:p.add('load',3);p.add('inc',3)if case['access']=='rmw'else p.add('load',2)
    for _ in range(2):p.add('nop')
    terminal=p.pc;p.add('bra',terminal)
    if p.pc>=0xFFF6:raise ValueError('Authored code overlaps vectors')
    rom=bytearray([0xEA]*262144)
    rom[p.start&8191:(p.start&8191)+len(p.code)]=p.code
    rom[8190:8192]=p.start.to_bytes(2,'little')
    clocks={profile:cpu_clock(case,primer,profile)for profile in('runtime','gear')}
    assert clocks['runtime']['ticks']==target
    planner=dict(target_ticks=target,target_frame=frame,target_line=64,target_hpos=hpos,
        prefix_ticks=before_padding,tail_cycles=33,padding_cycles=delta//case['speed'])
    return bytes(rom),dict(p.ops),primer,marker,terminal,clocks,planner


class ActiveSlots:
    """Sparse VRAM plus source-independent equations for the chosen steady area."""
    def __init__(self,case,ticks):
        self.case=case;self.t=ticks;self.d=case['divider'];self.marr=DATA+1
        self.mawr=DEST;self.vwr=TAIL;self.buffer=PAYLOAD
        self.read_pending=self.write_pending=False;self.delay=self.carry=0;self.wait_ticks=0
        self.memory=bytearray(65536)
        for index in range(case['sat_sprites']):
            for offset,value in enumerate((64,0,0,0x2000|(256 if case['wide']else 0))):
                self.put(SAT+index*4+offset,value)
        for address,value in((DATA,PAYLOAD),(DATA+1,SECOND),(DATA+2,TAIL)):self.put(address,value)
        self.candidates=[];self.grants=[]
    def put(self,address,value):self.memory[2*address:2*address+2]=(value&65535).to_bytes(2,'little')
    def get(self,address):return int.from_bytes(self.memory[2*address:2*address+2],'little')
    def geometry(self,t):
        h=t%LINE;vpos=(t//LINE)%262
        if not 32<=vpos<80:raise ValueError('Measured active oracle left its declared steady SAT interval')
        forced=32 if self.d==3 else 24
        display=forced+24;start=(display-16)*self.d;end=(display+240)*self.d
        state=3 if h<forced*self.d else 0 if h<display*self.d else 1 if h<end else 2
        return h,vpos,state,start,end
    def slot(self,t):
        h,_,state,start,end=self.geometry(t);mode=self.case['mwr']
        if start<=h<end:
            relative=(h-start)//self.d-1
            allowed=relative>=0 and ((relative&1)==0 if mode&3==0 else
                (relative&7)in(2,3)if mode&3 in(1,2)else False)
            if not allowed:return False,'background'
        else:
            if self.case['cr']&64 and self.case['cells']:
                elapsed=h-end if h>end else LINE-end+h
                cost=self.case['cells']*(4,4,8,16)[(mode>>2)&3]
                if elapsed//self.d<cost:return False,'sprite'
            if(h//self.d)&1:return False,'parity'
        if state==3 and(h+3)%LINE<8*self.d:return False,'hsync'
        return True,'grant'
    def advance(self,end,context='clock'):
        if end<self.t:raise ValueError('Active clock regression')
        while self.t<end:
            before=self.t;pending=self.read_pending or self.write_pending
            step=min(3,end-before)if pending else end-before
            if pending:
                self.carry+=step
                while(self.read_pending or self.write_pending)and self.carry>=3:
                    self.carry-=3;old_delay=self.delay;self.delay=max(0,self.delay-3)
                    if self.delay:continue
                    allowed,reason=self.slot(before);kind='read'if self.read_pending else'write'
                    record=dict(ticks=before,visible_ticks=before+step,context=context,kind=kind,
                        hclock=before%LINE,delay_before=old_delay,read_pending=int(self.read_pending),
                        write_pending=int(self.write_pending),allowed=allowed,reason=reason)
                    self.candidates.append(record)
                    if not allowed:continue
                    if self.read_pending:
                        self.buffer=self.get(self.marr);self.marr=(self.marr+1)&65535;self.read_pending=False
                    else:
                        self.put(self.mawr,self.vwr);self.mawr=(self.mawr+1)&65535;self.write_pending=False
                    self.grants.append(dict(record,marr=self.marr,mawr=self.mawr,read_buffer=self.buffer,vwr=self.vwr))
                    if not(self.read_pending or self.write_pending):self.carry=0
            self.t+=step
    def read(self,port):
        value=(self.buffer>>8)if port==3 else self.buffer&255
        if port==3:
            self.read_pending=True;self.delay=15 if self.d==2 else 24
        return value
    def write(self,port,value):
        self.vwr=(self.vwr&255)|(value<<8)if port==3 else(self.vwr&0xFF00)|value
        if port==3:
            self.write_pending=True;self.delay={4:21,3:18,2:12}[self.d]
    def hash(self):return hashlib.sha256(self.memory).hexdigest()
    def snapshot(self):
        h,vpos,hstate,start,end=self.geometry(self.t)
        return dict(ticks=self.t,divider=self.d,hclock=h,dma_pending=0,
            read_pending=int(self.read_pending),write_pending=int(self.write_pending),vram_delay=self.delay,
            vram_carry=self.carry,marr=self.marr,mawr=self.mawr,vwr=self.vwr,read_buffer=self.buffer,
            irq_requests=0,vdc_status=64 if self.read_pending or self.write_pending else 0,
            cd_enabled=0,cd_active=0,scsi_signals=0,scsi_phase=0,scsi_data=0,response_index=0,
            vpos=vpos,hstate=hstate,vstate=1,bg_start=start,bg_end=end,hsync_start=0,
            burst=0,latched_cr=self.case['cr'],latched_mwr=self.case['mwr'],
            sprite_count=self.case['cells'],sat_pending=0)


def literals(case,program,marker,terminal,clock,profile):
    k=ActiveSlots(case,clock['ticks']);origin=k.t;ram=bytearray(8192)
    pc=marker;a=case['acc'];p=4|(a&128)|(2 if not a else 0);mpr=clock['mapping'];rows=[];sources=[]
    def nz(value):
        nonlocal p
        p=(p&~130)|(value&128)|(2 if value==0 else 0)
    def row(ordinal,before=None,partition=None,stages=None):
        digest=hashlib.sha256(ram).hexdigest();snapshot=k.snapshot()
        values=[pc,a,0,0,255,p,case['speed'],k.t-origin,*mpr,255,0,0,0,0,7,0,0,0,0,
            0,snapshot['vdc_status'],0,0,0,0,0,0,0,0,int(k.read_pending),int(k.write_pending),k.wait_ticks]
        assert len(values)==39
        state=dict(pc=pc,a=a,x=0,y=0,sp=255,p=p,mpr=list(mpr),mpr_latch=255,
            physical_pc=(mpr[pc>>13]<<13)|(pc&8191),clock_divisor=case['speed'],ticks=k.t-origin,wram_sha256=digest)
        part=partition or dict(prefix=[],wait_runs=[],suffix=[],drain=0)
        extra=3*sum(part['wait_runs']);internal=sum(part['prefix'])+extra+sum(part['suffix'])
        return dict(ordinal=ordinal,values=values,state=state,wram_sha256=digest,vram_sha256=k.hash(),
            irq_count=0,irq_vector=None,irq_return_pc=None,extra_ticks=extra,internal_clocked_ticks=internal,
            fixed_wait_count=len(part['prefix'])+len(part['suffix']),clock_partition=part,
            kernel_entry=before or snapshot,kernel_final=snapshot,mmio_stages=stages or [])
    initial=row(0)
    for ordinal in range(1,49):
        before=k.snapshot();entry=k.t;op=program[pc];name=op[0];sources.append(source(pc,mpr,op))
        pc=(pc+len(encode(op,pc)))&65535;cycles=2;prefix=[];suffix=[];runs=[];stages=[];inline=0
        def fixed(destination):
            nonlocal inline
            destination.append(case['speed']);k.advance(k.t+case['speed'],'fixed');inline+=1
        def wait(enabled):
            nonlocal inline
            count=0
            if enabled:
                while k.read_pending or k.write_pending:
                    if count>10000:raise ValueError('Finite active access did not grant')
                    k.advance(k.t+3,'dynamic');k.wait_ticks+=3;count+=1;inline+=1
            runs.append(count)
        def port(kind,port,value=None):
            old=k.snapshot()
            if kind.startswith('read'):value=k.read(port)
            else:k.write(port,value)
            stages.append(dict(kind=kind,span_index=inline,before=old,after=k.snapshot(),value=value))
            return value
        if name=='load':
            cycles=5;fixed(prefix);wait(k.read_pending);a=port('read-high'if op[1]==3 else'read-low',op[1]);nz(a)
        elif name=='sta':
            cycles=5;wait(k.read_pending or k.write_pending)
            port('write-high'if op[1]==3 else'write-low',op[1],a);fixed(suffix)
        elif name=='inc':
            cycles=7;fixed(prefix);wait(k.read_pending);value=port('read-high',3)
            result=(value+1)&255;wait(k.read_pending or k.write_pending);port('write-high',3,result);fixed(suffix);nz(result)
        elif name=='bra':cycles=4;pc=op[1]
        elif name!='nop':raise ValueError('Unauthored measured active opcode')
        drain=cycles*case['speed'];k.advance(k.t+drain,'wrapper')
        part=dict(prefix=prefix,wait_runs=runs,suffix=suffix,drain=drain)
        result=row(ordinal,before,part,stages)
        assert result['internal_clocked_ticks']+drain==k.t-entry
        rows.append(result)
    assert pc==terminal
    denied=[item for item in k.candidates if not item['allowed']and item['reason']in('background','sprite')]
    extra=sum(item['extra_ticks']for item in rows)
    coverage='arbitration-denied'if denied else'latency-only'if extra else'zero-wait'
    if case['family']=='boundary':
        end=initial['kernel_final']['bg_end'];absolute=origin-origin%LINE+end
        witnesses=[next((item for item in k.candidates if item['ticks']==absolute+offset),None)for offset in(-3,0,3)]
        assert all(witnesses),('Missing boundary candidates',case['id'],profile)
        assert not witnesses[0]['allowed']and witnesses[1]['allowed']and not witnesses[2]['allowed']
        assert witnesses[1]['kind']=='read'and witnesses[1]['write_pending']==1
    else:witnesses=[]
    witness=dict(absolute_primer_ticks=origin,primer_clocks=clock['clocks'],candidates=k.candidates,grants=k.grants,
        boundary_candidates=witnesses,coverage=coverage,positive_wait=bool(extra),arbitration_denials=len(denied),
        geometry=dict(hsr=HSR,hdr=HDR,vpr=VPR,vdw=VDW,vcr=VCR,line_master_ticks=LINE,frame_lines=262,
            hds_dots=24,hdw_dots=240,hde_dots=1024,hsw_dots=24,line_reset_hsw_dots=32 if case['divider']==3 else 24),
        kernel_scope='Guest-established steady active raster, physical lines 32..79. Integer slot equations and complete guest prefix; no captured phase or runtime code supplies expectations.',
        carry_scope='All guest CPU clocks are multiples of three; carry zero only. Fractional host schedules are outside this suite.')
    return initial,rows,sources,witness


def authored_fixture():
    cases=[];images={};all_sources={}
    for definition in definitions():
        case=dict(definition);rom,program,primer,marker,terminal,clocks,planner=make_program(case)
        case.update(rom=case['id']+'.pce',entry=0xE000,marker=marker,end_pc=terminal,steps=48,
            primer_steps=len(primer),initial_mpr=[0]*8,block_steps=sum(op[0]=='tii'for _,op in primer),
            rom_sha256=hashlib.sha256(rom).hexdigest(),planner=planner)
        for profile in('runtime','gear'):
            clock=clocks[profile];initial,rows,measured,witness=literals(case,program,marker,terminal,clock,profile)
            case['expected_initial_'+profile]=initial;case['expected_'+profile]=rows
            case['kernel_'+profile]=witness;case['measured_mpr']=clock['mapping']
            counts=Counter();records={}
            for item in clock['sources']+measured:
                assert[rom[i]for i in item['physical']]==item['data']
                key=(item['pc'],tuple(item['mpr']),tuple(item['data']));counts[key]+=1;records[key]=item
            case['source_hits_'+profile]=[dict(records[key],hits=counts[key])for key in sorted(counts)]
            for key,item in records.items():all_sources[key]=dict(item,native_hits=0,interpreted_hits=1)
        case['initial']=case['expected_initial_runtime'];case['source_hits']=case['source_hits_runtime']
        cases.append(case);images[case['id']]=rom
    return cases,images,list(all_sources.values())


def generate(out,emit_module=True):
    from pcerecomp.abi import ABI
    out=Path(out);out.mkdir(parents=True,exist_ok=True);cases,images,sources=authored_fixture()
    (out/'authored.bin').write_bytes(bytes(16*2048))
    (out/'authored.cue').write_text('FILE "authored.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n',encoding='ascii')
    for case in cases:(out/case['rom']).write_bytes(images[case['id']])
    if emit_module:
        from pcerecomp.emitter import emit_capture
        capture=dict(schema=1,runtime_abi=ABI,capacity=len(sources),dropped_instructions=0,unreadable_instructions=0,
            retired_instructions=len(sources),complete=True,observations=sources)
        with TemporaryDirectory(prefix='vram-active-authored-',dir=out)as stage:
            target=Path(stage)/'module';emit_capture(capture,target,single_unit=True)
            for path in target.iterdir():(out/path.name).write_bytes(path.read_bytes())
    header=['#pragma once','#include <array>','#include <cstdint>','#include <string>','#include <stdexcept>','#include <vector>',
        'struct VramActiveLiteral { std::array<std::uint64_t,39> values; const char* wram_sha256; const char* vram_sha256; unsigned irq_count,irq_vector; };',
        'struct VramActiveCase { const char* id; const char* rom; unsigned entry,primer_steps,steps,marker,end_pc; VramActiveLiteral initial,gear_initial; const VramActiveLiteral* runtime_rows; const VramActiveLiteral* gear_rows; bool queued_accesses; unsigned block_steps; };']
    def literal(row):
        return '{{'+','.join(map(str,row['values']))+'},"'+row['wram_sha256']+'","'+row['vram_sha256']+'",0,0}'
    for index,case in enumerate(cases):
        for profile in('runtime','gear'):
            header.append(f'inline constexpr VramActiveLiteral vram_active_{index}_{profile}[]'+'{'+','.join(literal(row)for row in case['expected_'+profile])+'};')
    header.append('inline constexpr VramActiveCase vram_active_cases[]{')
    for index,case in enumerate(cases):
        header.append('{"'+case['id']+'","'+case['rom']+'",'+','.join(str(case[key])for key in('entry','primer_steps','steps','marker','end_pc'))+','+literal(case['initial'])+','+literal(case['expected_initial_gear'])+f',vram_active_{index}_runtime,vram_active_{index}_gear,true,'+str(case['block_steps'])+'},')
    header.extend(['};','inline const VramActiveCase& vram_active_case(const std::string& name){for(const auto& item:vram_active_cases)if(name==item.id)return item;throw std::runtime_error("Unknown authored active case");}',
        'inline std::vector<std::uint8_t> vram_active_rom(const VramActiveCase& item){std::vector<std::uint8_t> rom(262144,0xEA);'])
    for case in cases:
        changed=[(i,value)for i,value in enumerate(images[case['id']])if value!=0xEA]
        header.append('if(std::string(item.id)=="'+case['id']+'"){'+''.join(f'rom[{i}]={value};'for i,value in changed)+'return rom;}')
    header.append('throw std::runtime_error("Unknown authored BIOS");}')
    (out/'vram_active_fixture.hpp').write_text('\n'.join(header),encoding='utf-8')
    metadata=dict(schema=1,runtime_abi=ABI,cases=cases,cue='authored.cue',literal_columns=LITERAL_COLUMNS,
        media_files=[dict(path=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),bytes=(out/name).stat().st_size)for name in('authored.cue','authored.bin')],
        vram_encoding='32768 words serialized low-byte then high-byte; 65536 bytes',
        source_plan='Authored finite CPU and active-display slot ledger; no execution values supply expectations.',
        kernel_field_map=dict(ticks='state.ticks',hclock='hpos',irq_requests='irr'),transport_end='Idle CD transport; no command sent.')
    (out/'fixture.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8');return metadata


if __name__=='__main__':generate(sys.argv[1])
