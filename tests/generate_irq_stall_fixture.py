"""Authored long-DMA IRQ programs and an independent blank-slot timing ledger.

The oracle uses integer dot counts and explicitly declared scheduling rules.
It neither imports runtime code nor obtains golden values from executions.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from generate_irq_device_fixture import Program, encode, source, LITERAL_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
HSR, HDR = 0x7F1F, 0x7F7F
PAYLOAD, TAIL, DMA_DEST = 0xA65C, 0x5AA5, 0x2000
HANDLERS = {2:0xF840, 1:0xF880}


def definitions():
    cases=[]
    for speed,label in ((12,'low'),(3,'high')):
        for divider in (4,3,2):
            for kind,mask,sources in (
                ('read-mask0',0,3),('read-mask1',1,3),('read-mask2',2,3),('read-mask3',3,3),
                ('irq1-only',0,2),('irq2-only',0,1),('I-masked',0,3),
                ('write-mask0',0,3),('write-mask2',2,3),('rmw',0,3),
                ('read-high',0,3),('mapped-wrap',0,3)):
                cases.append(dict(id=f'{kind}-{label}-vce{divider}',kind=kind,speed=speed,
                    divider=divider,mask=mask,sources=sources,words=256,first_phase=False))
            cases.append(dict(id=f'first-DE-phase-{label}-vce{divider}',kind='first-DE-phase',
                speed=speed,divider=divider,mask=0,sources=3,words=2048,first_phase=True))
    for case in cases:
        case['sp']=1 if case['kind']=='mapped-wrap'else 255
        case['remap']=case['kind']=='mapped-wrap'
        case['queued_accesses']=True
        case['vce_control']={4:0,3:1,2:2}[case['divider']]
    return cases


def make_program(case):
    p=Program(0xE000)
    for op in [('sei',),('lda',0),('tam',0xFD),('lda',248),('tam',2),
               ('lda',0),('sta',0x2000),('tii',0x2000,0x2001,8191),('lda',255),('tam',1)]:p.add(*op)
    if case['speed']==3:p.add('csh')
    p.add('lda',7);p.add('sta',0x1402)
    p.add('lda',case['vce_control']);p.add('sta',0x0400)
    for register,value in ((5,0),(10,HSR),(11,HDR),(15,0)):p.register(register,value)
    # Known first/last source words make both read data and final DMA effects
    # independently distinguishable from a reset-filled VRAM image.
    for address,value in ((0,PAYLOAD),(case['words']-1,TAIL)):
        p.register(0,address);p.register(2,value);p.delay(100)
    # Establish the old prefetch buffer through software as well: the measured
    # queued MARR0 access must replace TAIL with PAYLOAD, never use stale data.
    p.register(1,case['words']-1);p.delay(100)
    # A full frame under CR0 establishes the declared blank/burst conditions.
    for _ in range(4):p.delay(6000)
    p.add('lda',0);p.add('sta',0x1802);p.add('sta',0x1800);p.delay(5000)
    for index,byte in enumerate([0xDE]+[0]*9):
        for op in [('lda',byte),('sta',0x1801),('lda',0x80),('sta',0x1802),('lda',0),('sta',0x1802)]:p.add(*op)
        if index<9 or not case['first_phase']:p.delay(200)
    if not case['first_phase']:
        p.delay(1000);p.add('lda',0xC0);p.add('sta',0x1802)
    else:p.add('lda',0x40);p.add('sta',0x1802)
    # No block delay occurs after launching the DMA below.
    p.add('lda',0)
    for address in (0x2100,0x21FF,0x21FE):p.add('sta',address)
    p.add('lda',case['mask']);p.add('sta',0x1402)
    if case['remap']:p.add('lda',1);p.add('tam',128)
    for op in [('ldx',case['sp']),('txs',),('clx',),('cly',),('cld',),('clv',),('clc',)]:p.add(*op)
    for register,value in ((15,2 if case['sources']&2 else 0),(16,0),(17,DMA_DEST),(18,case['words']-1),(1,0)):
        p.register(register,value)
    p.add('lda',2);p.add('sta',0);p.add('lda',0x40)
    marker=p.pc;primer=list(p.ops.items())
    p.add('nop'if case['kind']=='I-masked'else'cli')
    release=not case['first_phase']and bool(case['sources']&1)
    p.add(*(('sta',0x1802)if release else('nop',)))
    if case['kind'].startswith('write'):target=('sta',2)
    elif case['kind']=='rmw':target=('inc',2)
    else:target=('load',3 if case['kind']=='read-high'else 2)
    stall_pc=p.add(*target)
    for _ in range(3):p.add('nop')
    terminal=p.pc;p.add('bra',terminal)
    programs=dict(p.ops);segments=[(p.start,bytes(p.code))]
    for bit,target_pc in HANDLERS.items():
        for remap in(False,True):
            h=Program(target_pc+(0x100 if remap else 0))
            if bit==2:h.add('load',0)
            else:
                for op in [('lda',0xC0),('sta',0x1802),('lda',0x80),('sta',0x1802)]:h.add(*op)
            h.add('inc',0x2011 if bit==2 else 0x2012);h.add('rti')
            programs.update(h.ops);segments.append((h.start,bytes(h.code)))
    rom=bytearray([0xEA]*262144)
    for address,raw in segments:rom[address&8191:(address&8191)+len(raw)]=raw
    for bit,vector in ((1,0xFFF6),(2,0xFFF8)):
        rom[vector&8191:(vector&8191)+2]=HANDLERS[bit].to_bytes(2,'little')
    rom[8190:8192]=(0xE000).to_bytes(2,'little');rom[8192:16384]=rom[:8192]
    for bit,vector in ((1,0xFFF6),(2,0xFFF8)):
        rom[8192+(vector&8191):8192+(vector&8191)+2]=(HANDLERS[bit]+0x100).to_bytes(2,'little')
    return bytes(rom),programs,primer,marker,terminal,stall_pc


def primer_clock(case,primer,profile):
    """Authored CPU cycle ledger; operands, not observed traces, identify events."""
    ticks=0;divisor=12;a=0;mapping=[0]*8;selected=0;registers=[0]*20
    sources=[];clocks=[];commands=0;last_de_arm=None;dma_start=prefetch_issue=None
    for pc,op in primer:
        name=op[0];entry=ticks;sources.append(source(pc,mapping,op));cycles=2
        if name=='lda':a=op[1]
        elif name=='tam':
            cycles=5
            for page in range(8):
                if op[1]&(1<<page):mapping[page]=a
        elif name=='tii':cycles=17+6*op[3]
        elif name=='csh':
            ticks+=2*divisor+3 if profile=='runtime'else 9;divisor=3;cycles=0
        elif name=='sta':
            cycles=5;address=op[1]
            if address<0x400:
                cycles+=1
                if address==0:selected=a&31
                elif address in(2,3):
                    old=registers[selected]
                    registers[selected]=(old&255)|(a<<8)if address==3 else(old&0xFF00)|a
                    if address==3 and selected==18:dma_start=entry
                    if address==3 and selected==1:prefetch_issue=entry
            elif address==0x400:cycles+=1
            elif address==0x1801:commands+=1
            elif address==0x1802 and commands==10 and a==0 and last_de_arm is None:
                # No CPU VRAM request is outstanding while this final CDB
                # ACK is processed. Original Gear clocks its bus at STA end.
                last_de_arm=entry+(5*divisor if profile=='gear'else 0)
        ticks+=cycles*divisor
        clocks.append(dict(pc=pc,entry_ticks=entry,after_ticks=ticks,cycles=cycles,clock_divisor=divisor))
    assert dma_start is not None and prefetch_issue is not None and last_de_arm is not None
    return dict(ticks=ticks,mapping=mapping,sources=sources,clocks=clocks,
        dma_start=dma_start,prefetch_issue=prefetch_issue,first_de_arm=last_de_arm)


class BlankSlots:
    """Integer specification for the authored blank geometry and one DMA.

    A line has 1365 master ticks and floor(1365/divider) completed dots.
    DMA consumes four dots/word. A queued CPU access tests the preceding
    geometry before the next three-tick VCE slice, including HSW lookahead.
    """
    def __init__(self,case,clock,profile):
        self.case=case;self.profile=profile;self.d=case['divider'];self.n=case['words']
        self.dma_start=clock['dma_start'];self.start_dot=self.dots(self.dma_start)
        lo=self.dma_start;hi=lo+8*self.n*self.d+1365
        while lo<hi:
            mid=(lo+hi)//2
            if self.dots(mid)-self.start_dot>=4*self.n:hi=mid
            else:lo=mid+1
        self.dma_dot_end=lo;self.t=clock['prefetch_issue'];self.marr=0;self.buffer=TAIL
        self.pending=True;self.delay=15 if self.d==2 else 24;self.carry=0
        self.irq1=False;self.done_seen=False;self.status=0;self.wait_ticks=0
        self.cd_enable=64;self.cd_active=0;self.ack=not case['first_phase']
        self.signals=0x90 if case['first_phase']else 0x8A
        self.phase=3 if case['first_phase']else 4;self.db=0 if case['first_phase']else 1
        self.offset=0 if case['first_phase']else 1
        self.cd_deadline=clock['first_de_arm']+9000 if case['first_phase']else None
        self.bus_action=None;self.events=[dict(kind='dma-start',ticks=self.dma_start,words=self.n),
            dict(kind='prefetch-issued',ticks=self.t,marr=0,delay=self.delay)];self.grants=[]
        if case['first_phase']:
            self.events.append(dict(kind='cd-first-armed',ticks=clock['first_de_arm'],deadline=self.cd_deadline))
        self.advance(clock['ticks'])
        assert self.pending and self.dma_pending()>0 and not self.irq1 and not self.cd_active
    def dots(self,t):return(t//1365)*(1365//self.d)+(t%1365)//self.d
    def dma_pending(self,t=None):
        return max(0,4*self.n-(self.dots(self.t if t is None else t)-self.start_dot))
    def slot(self,t):
        h=t%1365;initial_hsw=32 if self.d==3 else 24
        if(h//self.d)&1:return False
        # HDS=(127+1)*8=1024 dots, longer than every authored line. After
        # the reset HSW there is no second HSW/fetch window in this line.
        if h<initial_hsw*self.d and(h+3)%1365<8*self.d:return False
        return True
    def read_word(self,address):
        if address==0:return PAYLOAD
        if address==self.n-1:return TAIL
        completed=(4*self.n-self.dma_pending())//4
        if address==DMA_DEST and completed:return PAYLOAD
        if address==DMA_DEST+self.n-1 and completed==self.n:return TAIL
        return 0
    def _cd_action(self,ack,when):
        if ack:
            if self.cd_active:
                self.events.append(dict(kind='cd-source-clear',ticks=when,active=self.cd_active,
                    enabled=self.cd_enable))
            self.signals&=~0x40;self.cd_active=0
        else:
            self.db=1;self.offset=2;self.cd_deadline=when+900
            self.events.append(dict(kind='cd-next-armed',ticks=when,deadline=self.cd_deadline))
    def write_cd(self,value):
        self.events.append(dict(kind='cd-enable-write',ticks=self.t,value=value,
            active=self.cd_active,enabled=value&127))
        self.cd_enable=value&127;ack=bool(value&128)
        if ack==self.ack:return
        self.ack=ack;self.signals=(self.signals|2)if ack else self.signals&~2
        if self.profile=='runtime':self._cd_action(ack,self.t)
        else:self.bus_action=ack
    def advance(self,end):
        assert end>=self.t
        while self.t<end:
            before=self.t;step=min(3,end-before)if self.pending else end-before
            if self.pending:
                self.carry+=step
                while self.pending and self.carry>=3:
                    self.carry-=3
                    if self.delay>0:self.delay-=3
                    if self.delay>0:continue
                    self.delay=0
                    if self.dma_pending(before)or not self.slot(before):continue
                    self.buffer=self.read_word(self.marr);self.marr=(self.marr+1)&65535
                    self.pending=False;self.carry=0
                    self.grants.append(dict(test_ticks=before,visible_ticks=before+step,marr=self.marr,read_buffer=self.buffer))
            self.t+=step
            if not self.done_seen and self.t>=self.dma_dot_end:
                self.done_seen=True;self.irq1=bool(self.case['sources']&2)
                if self.irq1:self.status|=16
                self.events.append(dict(kind='dma-complete',ticks=self.t,dot_ticks=self.dma_dot_end))
            if self.cd_deadline is not None and self.cd_deadline<=self.t:
                deadline=self.cd_deadline;self.cd_deadline=None
                if self.case['first_phase']and self.phase==3:
                    self.phase=4;self.signals=0xC8;self.db=1;self.offset=1
                else:self.signals|=0x40
                self.cd_active=64
                self.events.append(dict(kind='cd-request',ticks=deadline if self.profile=='runtime'else self.t,deadline=deadline))
            if self.bus_action is not None:
                action=self.bus_action;self.bus_action=None;self._cd_action(action,self.t)
    def requests(self):return(2 if self.irq1 else 0)|(1 if self.cd_active&self.cd_enable else 0)
    def status_read(self):
        value=self.status|(64 if self.pending else 0)
        self.events.append(dict(kind='vdc-status-ack',ticks=self.t,value=value,irq1=int(self.irq1)))
        self.status=0;self.irq1=False;return value
    def queue_read(self):self.pending=True;self.delay=15 if self.d==2 else 24;self.carry=0
    def vram_hash(self):
        raw=bytearray(65536)
        for address in(0,self.n-1,DMA_DEST,DMA_DEST+self.n-1):
            value=self.read_word(address);raw[2*address:2*address+2]=value.to_bytes(2,'little')
        return hashlib.sha256(raw).hexdigest()
    def snapshot(self):
        return dict(ticks=self.t,divider=self.d,hclock=self.t%1365,
            dma_pending=self.dma_pending(),read_pending=int(self.pending),write_pending=0,
            vram_delay=self.delay,vram_carry=self.carry,marr=self.marr,read_buffer=self.buffer,
            irq_requests=self.requests(),vdc_status=self.status|(64 if self.pending else 0),
            cd_enabled=self.cd_enable,cd_active=self.cd_active,scsi_signals=self.signals,
            scsi_phase=self.phase,scsi_data=self.db,response_index=self.offset)


def literals(case,program,marker,terminal,clock,profile):
    k=BlankSlots(case,clock,profile);origin=k.t;ram=bytearray(8192)
    pc=marker;a=64;x=y=0;sp=case['sp'];p=4;entries=vector=rti=0
    mpr=list(clock['mapping']);latch=1 if case['remap']else 255
    rows=[];sources=[]
    def push(value):
        nonlocal sp
        ram[0x100+sp]=value&255;sp=(sp-1)&255
    def pop():
        nonlocal sp
        sp=(sp+1)&255;return ram[0x100+sp]
    def nz(value):
        nonlocal p
        p=(p&~130)|(value&128)|(2 if value==0 else 0)
    def row(ordinal,delivered=0,return_pc=None,entry_kernel=None,partition=None):
        digest=hashlib.sha256(ram).hexdigest()
        values=[pc,a,x,y,sp,p,case['speed'],k.t-origin,*mpr,latch,entries,vector,rti,
                0,case['mask'],0,ram[0x10],ram[0x11],ram[0x12],k.requests(),
                k.status|(64 if k.pending else 0),k.cd_enable,k.cd_active,int(k.ack),
                k.signals,k.phase,k.db,k.offset,k.dma_pending(),int(k.pending),0,k.wait_ticks]
        state=dict(pc=pc,a=a,x=x,y=y,sp=sp,p=p,mpr=list(mpr),mpr_latch=latch,
            physical_pc=(mpr[pc>>13]<<13)|(pc&8191),clock_divisor=case['speed'],
            ticks=k.t-origin,wram_sha256=digest)
        part=partition or dict(prefix=[],stall_count=0,suffix=[],drain=0)
        extra=3*part['stall_count'];internal=sum(part['prefix'])+extra+sum(part['suffix'])
        return dict(ordinal=ordinal,values=values,state=state,wram_sha256=digest,
            vram_sha256=k.vram_hash(),irq_count=int(bool(delivered)),irq_vector=delivered or None,
            irq_return_pc=return_pc,extra_ticks=extra,internal_clocked_ticks=internal,
            fixed_wait_count=len(part['prefix'])+len(part['suffix']),clock_partition=part,
            kernel_entry=entry_kernel or k.snapshot(),kernel_final=k.snapshot())
    initial=row(0)
    for ordinal in range(1,49):
        before=k.snapshot();entry_ticks=k.t;op=program[pc];name=op[0]
        sources.append(source(pc,mpr,op));pc=(pc+len(encode(op,pc)))&65535
        sampled=0 if p&4 else k.requests()&~case['mask'];cycles=2
        prefix=[];suffix=[];stall_count=0
        def fixed(count,destination):
            nonlocal sampled
            ticks=count*case['speed'];destination.append(ticks);k.advance(k.t+ticks)
            sampled=0 if p&4 else k.requests()&~case['mask']
        def wait():
            nonlocal sampled,stall_count
            while k.pending:
                if stall_count>100000:raise ValueError('Authored finite DMA did not grant CPU access')
                k.advance(k.t+3);k.wait_ticks+=3;stall_count+=1
                sampled=0 if p&4 else k.requests()&~case['mask']
        if name=='lda':a=op[1];nz(a)
        elif name=='cli':p&=~4
        elif name=='load':
            cycles=5;address=op[1]
            if address<4:
                fixed(1,prefix)
                if address>=2:wait();a=(k.buffer>>8)if address==3 else k.buffer&255
                else:a=k.status_read()
                if address==3:k.queue_read()
            else:a=ram[address&8191]
            nz(a)
        elif name=='sta':
            cycles=5
            if op[1]==0x1802:k.write_cd(a)
            elif op[1]==2:wait();fixed(1,suffix)
            else:raise ValueError('Unauthored measured store')
        elif name=='inc':
            cycles=7
            if op[1]==2:
                fixed(1,prefix);wait();value=(k.buffer+1)&255;fixed(1,suffix);nz(value)
            else:
                address=op[1]&8191;ram[address]=(ram[address]+1)&255;nz(ram[address])
        elif name=='rti':p=pop()&~16;low=pop();pc=low|(pop()<<8);cycles=7;rti+=1
        elif name=='bra':pc=op[1];cycles=4
        elif name!='nop':raise ValueError('Unauthored measured opcode')
        p&=~32;eligible=sampled&3;bit=2 if eligible&2 else 1 if eligible&1 else 0
        delivered={2:0xFFF8,1:0xFFF6,0:0}[bit];return_pc=pc if bit else None
        if bit:
            push(pc>>8);push(pc);push(p&~16);p=(p|4)&~40
            pc=HANDLERS[bit]+(0x100 if case['remap']else 0);entries+=1;vector=delivered
        drain=(cycles+(8 if bit else 0))*case['speed'];k.advance(k.t+drain)
        part=dict(prefix=prefix,stall_count=stall_count,suffix=suffix,drain=drain)
        result=row(ordinal,delivered,return_pc,before,part)
        assert result['internal_clocked_ticks']+drain==k.t-entry_ticks
        rows.append(result)
    assert pc==terminal
    stall=rows[2];assert stall['extra_ticks']>0
    dynamic_start=stall['kernel_entry']['ticks']+sum(stall['clock_partition']['prefix'])
    dynamic_end=dynamic_start+stall['extra_ticks']
    for event in k.events:
        if event['kind']=='dma-complete'and case['sources']&2:
            assert dynamic_start<event['ticks']<dynamic_end
        if event['kind']=='cd-request'and case['sources']&1:
            assert dynamic_start<event['ticks']<dynamic_end
    witness=dict(absolute_primer_ticks=origin,primer_clocks=clock['clocks'],
        dma_start_ticks=clock['dma_start'],dma_dot_completion_ticks=k.dma_dot_end,
        prefetch_issue_ticks=clock['prefetch_issue'],first_de_arm_ticks=clock['first_de_arm'],
        geometry=dict(hsr=HSR,hdr=HDR,hds_dots=1024,hdw_dots=1024,hde_dots=1024,hsw_dots=256,
            line_reset_hsw_dots=32 if case['divider']==3 else 24,line_master_ticks=1365),
        events=sorted(k.events,key=lambda event:event['ticks']),grants=k.grants,
        dynamic_start_ticks=dynamic_start,dynamic_end_ticks=dynamic_end,
        kernel_scope='Explicit blank geometry after guest frame warmup; integer DMA dots, pre-raster CPU slots, selected CD handshake scheduler. No runtime or captured values used.')
    return initial,rows,sources,witness


def authored_fixture():
    cases=[];images={};all_sources={}
    for definition in definitions():
        case=dict(definition);rom,program,primer,marker,terminal,stall_pc=make_program(case)
        case.update(rom=case['id']+'.pce',entry=0xE000,marker=marker,end_pc=terminal,
            stall_pc=stall_pc,steps=48,primer_steps=len(primer),initial_mpr=[0]*8,
            block_steps=sum(op[0]=='tii'for _,op in primer),rom_sha256=hashlib.sha256(rom).hexdigest())
        for profile in('runtime','gear'):
            clock=primer_clock(case,primer,profile)
            initial,rows,measured,witness=literals(case,program,marker,terminal,clock,profile)
            case['expected_initial_'+profile]=initial;case['expected_'+profile]=rows
            case['kernel_'+profile]=witness;case['measured_mpr']=clock['mapping']
            counts=Counter();records={}
            for item in clock['sources']+measured:
                assert[rom[i]for i in item['physical']]==item['data']
                key=(item['pc'],tuple(item['mpr']),tuple(item['data']))
                counts[key]+=1;records[key]=item
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
        capture=dict(schema=1,runtime_abi=ABI,capacity=len(sources),dropped_instructions=0,
            unreadable_instructions=0,retired_instructions=len(sources),complete=True,observations=sources)
        with TemporaryDirectory(prefix='irq-stall-authored-',dir=out)as stage:
            target=Path(stage)/'module';emit_capture(capture,target,single_unit=True)
            for path in target.iterdir():(out/path.name).write_bytes(path.read_bytes())
    header=['#pragma once','#include <array>','#include <cstdint>','#include <string>','#include <stdexcept>','#include <vector>',
        'struct IrqStallLiteral { std::array<std::uint64_t,39> values; const char* wram_sha256; const char* vram_sha256; unsigned irq_count,irq_vector; };',
        'struct IrqStallCase { const char* id; const char* rom; unsigned entry,primer_steps,steps,marker,end_pc; IrqStallLiteral initial,gear_initial; const IrqStallLiteral* runtime_rows; const IrqStallLiteral* gear_rows; bool queued_accesses; unsigned block_steps; };']
    def literal(row):
        return '{{'+','.join(map(str,row['values']))+'},"'+row['wram_sha256']+'","'+row['vram_sha256']+'",'+str(row['irq_count'])+','+str(row['irq_vector']or 0)+'}'
    for index,case in enumerate(cases):
        for profile in('runtime','gear'):
            header.append(f'inline constexpr IrqStallLiteral irq_stall_{index}_{profile}[]'+'{'+','.join(literal(row)for row in case['expected_'+profile])+'};')
    header.append('inline constexpr IrqStallCase irq_stall_cases[]{')
    for index,case in enumerate(cases):
        header.append('{"'+case['id']+'","'+case['rom']+'",'+','.join(str(case[key])for key in('entry','primer_steps','steps','marker','end_pc'))+','+literal(case['initial'])+','+literal(case['expected_initial_gear'])+f',irq_stall_{index}_runtime,irq_stall_{index}_gear,true,'+str(case['block_steps'])+'},')
    header.extend(['};','inline const IrqStallCase& irq_stall_case(const std::string& name){for(const auto& item:irq_stall_cases)if(name==item.id)return item;throw std::runtime_error("Unknown authored stall case");}',
        'inline std::vector<std::uint8_t> irq_stall_rom(const IrqStallCase& item){std::vector<std::uint8_t> rom(262144,0xEA);'])
    for case in cases:
        changed=[(i,value)for i,value in enumerate(images[case['id']])if value!=0xEA]
        header.append('if(std::string(item.id)=="'+case['id']+'"){'+''.join(f'rom[{i}]={value};'for i,value in changed)+'return rom;}')
    header.append('throw std::runtime_error("Unknown authored BIOS");}')
    (out/'irq_stall_fixture.hpp').write_text('\n'.join(header),encoding='utf-8')
    metadata=dict(schema=1,runtime_abi=ABI,cases=cases,cue='authored.cue',literal_columns=LITERAL_COLUMNS,
        media_files=[dict(path=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest(),bytes=(out/name).stat().st_size)for name in('authored.cue','authored.bin')],
        vram_encoding='32768 words serialized low-byte then high-byte; 65536 bytes',
        source_plan='Authored finite CPU and integer blank-slot timing ledger; no captured or runtime values supply expectations.',
        kernel_field_map=dict(ticks='state.ticks',hclock='hpos',irq_requests='irr'),
        transport_end='Current DATA IN byte consumed and IRQ2 masked with ACK held; no idle/full-command completion claim.')
    (out/'fixture.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8');return metadata


if __name__=='__main__':generate(sys.argv[1])
