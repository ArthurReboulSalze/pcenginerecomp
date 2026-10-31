"""Guest-generated IRQ1/IRQ2 delivery inside dynamic VRAM-stall reference checks.

Compile original Gear separately. Guest software establishes every compared
CPU/device state; original calls, clocks and source identities remain bound.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import mapper_reference as infrastructure
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as reference
from scripts import irq_boundary_reference as previous
sha=reference.sha


def require(value,label):
    if not value:raise ValueError(label)


def integer(value,maximum=2**64-1,minimum=0):
    require(type(value)is int and minimum<=value<=maximum,'Typed bounded journal integer required')
    return value


def typed_equal(actual,expected):
    if type(actual)is not type(expected):return False
    if type(expected)is dict:
        return actual.keys()==expected.keys()and all(typed_equal(actual[k],v)for k,v in expected.items())
    if type(expected)is list:
        return len(actual)==len(expected)and all(typed_equal(a,b)for a,b in zip(actual,expected))
    return actual==expected


def strict_rows(path):
    """New dynamic-span protocol; the old device journal bounds stay intact."""
    from pcerecomp.reference_trace import _json
    path=Path(path)
    require(path.stat().st_size<=256*1024*1024,'Original stall journal exceeds protocol bound')
    rows=[]
    with path.open('rb')as stream:
        while raw:=stream.readline(32*1024*1024+1):
            require(len(raw)<=32*1024*1024 and len(rows)<100000,'Original stall record bound')
            rows.append(_json(raw))
    return rows


def ledger(rows):
    result={}
    for row in rows:
        key=(row['pc'],tuple(row['mpr']),tuple(row['physical']),tuple(row['data']))
        require(key not in result,'Independent source ledger contains duplicate identity')
        result[key]=integer(row['hits'],minimum=1)
    return result


def check_values(values,state,origin):
    require(type(values)is list and len(values)==39,'Complete 39-column device observation required')
    for value in values:integer(value)
    expected=[state[k]for k in('pc','a','x','y','sp','p','clock_divisor')]
    expected += [state['ticks']-origin,*state['mpr'],state['mpr_latch']]
    require(values[:17]==expected,'Actual device row CPU/mapping/clock association differs')


def qualify_trace(trace,case,profile):
    require(len(trace.instructions)==case['steps']==len(case['expected_'+profile]),'Exact measured extent required')
    require(trace.initial['ticks']==case['kernel_'+profile]['absolute_primer_ticks'],
            profile+' independent complete-primer clock differs')
    checks=0
    rows=[dict(state=trace.initial,irq_count=0,irq_vector=None),*trace.instructions]
    literals=[case['expected_initial_'+profile],*case['expected_'+profile]]
    for actual,wanted in zip(rows,literals):
        for field,value in wanted['state'].items():
            observed=actual['state'][field]
            if field=='ticks':observed-=trace.initial['ticks']
            require(type(observed)is type(value) and observed==value,
                    profile+' independent '+field+' at '+str(wanted['ordinal']))
            checks+=1
        for field in('irq_count','irq_vector'):
            require(actual[field]==wanted[field],profile+' independent delivery '+field)
            checks+=1
    return checks


def qualify_case(case,traces,captures,work):
    checks=sum(qualify_trace(traces[tier],case,profile)for tier,profile in
               (('native','runtime'),('interpreter','runtime'),('gear','gear')))
    total=case['primer_steps']+case['steps'];expected_sources=ledger(case['source_hits_runtime'])
    require(sum(expected_sources.values())==total,'Independent runtime source extent differs')
    fields={'schema','case','tier','primer_steps','measured_steps','native_steps','interpreter_steps',
            'block_steps','pure_guards','raw_initial_ticks','literal_rows','initial_vram_sha256',
            'initial_kernel','vram_hashes','kernel_rows'}
    for tier in('native','interpreter'):
        capture=captures[tier]
        require(capture['runtime_abi']==ABI and capture['complete']is True and
                capture['retired_instructions']==total and not capture['dropped_instructions']and
                not capture['unreadable_instructions'],f'Actual complete ABI{ABI} source capture required')
        require(previous.source_counts(capture,tier)==expected_sources,'Full independent PC/MPR/physical/byte source hits differ')
        other='interpreted_hits'if tier=='native'else'native_hits'
        require(all(row[other]==0 for row in capture['observations']),'Unexpected execution tier in source capture')
        actual=work[tier]
        require(type(actual)is dict and set(actual)==fields,'Strict actual execution receipt required')
        expected=dict(schema=1,case=case['id'],tier=tier,primer_steps=case['primer_steps'],
            measured_steps=case['steps'],native_steps=total if tier=='native'else 0,
            interpreter_steps=total if tier=='interpreter'else 0,block_steps=case['block_steps'],
            pure_guards=4 if tier=='native'else 0,raw_initial_ticks=traces[tier].initial['ticks'])
        for field,value in expected.items():
            require(type(actual[field])is type(value)and actual[field]==value,'Actual execution '+field+' differs')
        require(actual['initial_vram_sha256']==case['expected_initial_runtime']['vram_sha256'],
                'Independent initial runtime VRAM differs')
        kernels=[actual['initial_kernel'],*actual['kernel_rows']]
        hashes=[actual['initial_vram_sha256'],*actual['vram_hashes']]
        wanted_rows=[case['expected_initial_runtime'],*case['expected_runtime']]
        require(len(kernels)==len(hashes)==case['steps']+1,'Complete runtime kernel/VRAM extent required')
        for kernel,digest,wanted in zip(kernels,hashes,wanted_rows):
            require(type(kernel)is dict and set(kernel)==set(wanted['kernel_final']),
                    'Strict complete runtime blank-slot kernel required')
            for name,value in kernel.items():
                integer(value,minimum=-2**31 if name=='vram_delay'else 0)
                require(value==wanted['kernel_final'][name],'Independent runtime '+name+' kernel differs')
            require(digest==wanted['vram_sha256'],'Independent full runtime VRAM hash differs')
        rows=actual['literal_rows']
        require(type(rows)is list and len(rows)==case['steps'],'Device literal row extent differs')
        for row,wanted,group in zip(rows,case['expected_runtime'],traces[tier].instructions):
            check_values(row,group['state'],traces[tier].initial['ticks'])
            require(row==wanted['values'],'Independent 39-column device literal differs')
            checks+=39
    return dict(scalar_checks=checks,actual_retirements_per_tier=total,
                measured_retirements=case['steps'],source_identities=len(expected_sources))


def callback_shape(event):
    require(type(event)is dict,'Original callback must be an object')
    common={'cycle','type'}
    fields={
        'cpu':{'pc','bank','a','x','y','sp','p','bytes'},
        'TRACE_CPU_IRQ':{'pc','vector','mask'},
        'vdc':{'event','chip','reg','raw','msb','value','value2','value3','param'},
        'cdrom':{'event','irq_type','active','enabled','state','lba','param'},
        'scsi':{'event','command','phase','status','param','data'}}
    kind=event.get('type')
    require(type(kind)is str and kind in fields and set(event)==common|fields[kind],
            'Strict supported original callback fields required')
    integer(event['cycle'])
    for key in fields[kind]-{'bytes','data'}:
        integer(event[key],2**32-1,-2**31 if key=='lba'else 0)
    if kind=='cpu':
        integer(event['pc'],65535)
        for field in('bank','a','x','y','sp','p'):integer(event[field],255)
        require(type(event['bytes'])is list and 1<=len(event['bytes'])<=7,'Original fetched bytes required')
        for value in event['bytes']:integer(value,255)
    elif kind=='TRACE_CPU_IRQ':
        require(event['vector']in(0xFFF6,0xFFF8,0xFFFA),'Original IRQ vector invalid')
        integer(event['pc'],65535);integer(event['mask'],7)
    elif kind=='vdc':
        integer(event['event'],12);integer(event['chip'],0);integer(event['reg'],255)
        integer(event['raw'],255);integer(event['msb'],1)
        for field in('value','value2','value3'):integer(event[field],65535)
    elif kind=='cdrom':
        integer(event['event'],10)
        for field in('irq_type','active','enabled','state'):integer(event[field],255)
    else:
        integer(event['event'],7)
        for field in('command','phase','status'):integer(event[field],255)
        require(type(event['data'])is list and len(event['data'])<=16,'Bounded original SCSI callback bytes required')
        for value in event['data']:integer(value,255)


KERNEL_FIELDS=set('cpu_extra cpu_clocked cpu_p cpu_mask irr cpu_pending vdc_status dma_pending read_pending write_pending vram_carry vram_delay marr mawr dcr sour desr lenr read_buffer vram_bus divider burst latched_cr latched_mwr hpos vpos hstate vstate bg_start bg_end hsync_start cd_enabled cd_active scsi_signals scsi_phase scsi_data response_index'.split())
SIGNED_FIELDS=set('cpu_pending vram_delay hpos vpos hstate vstate bg_start bg_end hsync_start'.split())
PARTITION_FIELDS=set('before requested after context extra_before clocked_before pending_before p_before mask_before'.split())
FULL_FIELDS=PARTITION_FIELDS|set('source_before source_after pending_after_inside_callback after_phase'.split())
BLOCKS=(0x73,0xC3,0xD3,0xE3,0xF3)


def kernel_shape(value):
    require(type(value)is dict and set(value)==KERNEL_FIELDS,'Strict original stall kernel required')
    for name,item in value.items():
        integer(item,2**31-1 if name in SIGNED_FIELDS else 2**32-1,
                -2**31 if name in SIGNED_FIELDS else 0)
    for name in('cpu_p','cpu_mask','irr','vdc_status','cd_enabled','cd_active','scsi_data'):
        integer(value[name],255)
    for name in('read_pending','write_pending','burst'):integer(value[name],1)
    for name in('cpu_mask','irr','cpu_pending'):integer(value[name],7)
    require(value['divider']in(2,3,4),'Original VCE divisor invalid')


def qualify_spans(row,wanted=None):
    """Identify waits by original extra-counter increments, never length alone.

    A fast fixed memory wait is also three ticks. Only an inline callback
    with a three-tick increase in the original extra counter is dynamic.
    Hardware callback exit precedes the CPU's CheckIRQs invocation.
    """
    spans=row['clocks'];detail=row['clock_detail'];entry=row['entry'];after=row['state']
    require(type(spans)is list and 1<=len(spans)<=200000,'Bounded original stall clock callbacks required')
    require(detail in('partition-only','full-kernel'),'Original clock detail invalid')
    cursor=entry['ticks'];clocked=extra=0;dynamic=[];fixed=[];wrapper=[];edges=[]
    previous_inline=None
    for index,span in enumerate(spans):
        require(type(span)is dict and set(span)==(FULL_FIELDS if detail=='full-kernel'else PARTITION_FIELDS),
                'Strict original stall clock partition required')
        for field in PARTITION_FIELDS-{'context'}:integer(span[field],minimum=-2**31 if field=='pending_before'else 0)
        context=span['context'];require(context in('inline','wrapper'),'Original clock context invalid')
        require(span['before']==cursor and span['requested']>0 and span['after']==cursor+span['requested'],
                'Original stall clock chain differs')
        cursor=span['after']
        if detail=='full-kernel':
            before,finish=span['source_before'],span['source_after']
            kernel_shape(before);kernel_shape(finish)
            for short,long in(('extra_before','cpu_extra'),('clocked_before','cpu_clocked'),
                               ('pending_before','cpu_pending'),('p_before','cpu_p'),('mask_before','cpu_mask')):
                require(span[short]==before[long],'Original clock scalar/kernel association differs')
            require(span['after_phase']==('before-cpu-resample'if context=='inline'else'no-cpu-resample'),
                    'Original callback sampling phase differs')
            require(span['pending_after_inside_callback']==finish['cpu_pending']==before['cpu_pending'] and
                    finish['cpu_extra']==before['cpu_extra'] and finish['cpu_clocked']==before['cpu_clocked'],
                    'Hardware callback falsely attributed CPU resampling or counter updates')
        if context=='wrapper':
            require(index==len(spans)-1 and span['clocked_before']==row['internal_clocked_ticks'] and
                    span['extra_before']==row['extra_ticks'],'Original wrapper drain placement differs')
            wrapper.append(span['requested']);continue
        require(not wrapper and span['clocked_before']==clocked,'Original inline clocked counter differs')
        difference=span['extra_before']-extra
        require(difference in(0,3),'Original dynamic wait counter increment differs')
        if difference:
            require(span['requested']==3,'Dynamic wait must clock exactly three master ticks')
            dynamic.append(index)
            if detail=='full-kernel':
                require(before['read_pending']or before['write_pending'],'Dynamic wait lacks an actual pending VRAM access')
                if len(dynamic)>1 and dynamic[-2]==index-1:
                    prior=previous_inline['source_after']
                    sampled=0 if prior['cpu_p']&4 else prior['irr']&~prior['cpu_mask']
                    require(span['pending_before']==sampled,'Original next dynamic callback does not witness CPU IRQ resampling')
                    stable=KERNEL_FIELDS-{'cpu_extra','cpu_clocked','cpu_pending'}
                    require(all(before[name]==prior[name]for name in stable),
                            'Original device kernel chain breaks inside VRAM wait')
                for bit,name in((2,'irq1'),(1,'irq2')):
                    if not before['irr']&bit and finish['irr']&bit:
                        edges.append(dict(source=name,before=span['before'],after=span['after'],span=index))
        else:
            require(span['requested']==entry['clock_divisor'],'Original fixed memory wait divisor differs')
            fixed.append(index)
        extra=span['extra_before'];clocked+=span['requested'];previous_inline=span
    require(cursor==after['ticks'],'Original actual clocks fail to close the call')
    # Primer blocks have several RunInstruction continuations and reset their
    # internal counters per call; their partition-only path is checked below.
    require(extra==row['extra_ticks'] and clocked==row['internal_clocked_ticks'],
            'Original inline fixed/dynamic accounting differs')
    require(row['extra_ticks']==3*len(dynamic),'Original dynamic span total differs')
    if 'kernel_at_return'in row:
        require(detail=='full-kernel'and len(wrapper)==1,
                'Declared ordinary opcode requires one observed wrapper drain')
        require(row['kernel_at_return']==spans[-1]['source_before']and
                row['kernel_final']==spans[-1]['source_after']and
                row['kernel_at_return']['cpu_clocked']==clocked and
                row['kernel_at_return']['cpu_extra']==extra,
                'Original CPU return/final kernel differs from actual clock callback')
    if wanted is not None:
        require(row['extra_ticks']==wanted['extra_ticks'] and
                row['internal_clocked_ticks']==wanted['internal_clocked_ticks'] and
                len(fixed)==wanted['fixed_wait_count'],'Independent dynamic/fixed clock literal differs')
        if 'clock_partition'in wanted:
            partition=wanted['clock_partition']
            require(type(partition)is dict and set(partition)=={'prefix','stall_count','suffix','drain'},
                    'Independent exact clock partition required')
            require(type(partition['prefix'])is list and type(partition['suffix'])is list,
                    'Independent fixed clock lists required')
            for value in partition['prefix']+partition['suffix']:integer(value,minimum=1)
            integer(partition['stall_count'],200000);integer(partition['drain'])
            expected=[('inline',n)for n in partition['prefix']]+[
                ('inline',3)]*partition['stall_count']+[
                ('inline',n)for n in partition['suffix']]
            if partition['drain']:expected.append(('wrapper',partition['drain']))
            require([(s['context'],s['requested'])for s in spans]==expected and
                    dynamic==list(range(len(partition['prefix']),len(partition['prefix'])+partition['stall_count'])),
                    'Independent original exact dynamic wait positions/clock partition differ')
    return dict(dynamic_indices=dynamic,fixed_indices=fixed,wrapper=wrapper,source_edges=edges)


def check_kernel_values(kernel,values,state):
    kernel_shape(kernel)
    associations={'cpu_p':5,'cpu_mask':21,'irr':26,'vdc_status':27,'cd_enabled':28,
        'cd_active':29,'scsi_signals':31,'scsi_phase':32,'scsi_data':33,
        'response_index':34,'dma_pending':35,'read_pending':36,'write_pending':37}
    require(all(kernel[name]==values[index]for name,index in associations.items()),
            'Original row kernel/device literal association differs')
    require(kernel['cpu_p']==state['p'],'Original kernel CPU status differs')


def qualify_kernel(actual,wanted,ticks):
    """Compare the declared independent blank-slot kernel, not an entry seed."""
    mapping={name:name for name in ('divider','dma_pending','read_pending','write_pending',
        'vram_delay','vram_carry','marr','read_buffer','vdc_status','cd_enabled','cd_active',
        'scsi_signals','scsi_phase','scsi_data','response_index')}
    mapping.update(hclock='hpos',irq_requests='irr')
    require(type(wanted)is dict and set(wanted)==set(mapping)|{'ticks'},
            'Complete independently modeled blank-slot kernel required')
    require(wanted['ticks']==ticks,'Independent absolute kernel timestamp differs')
    require(all(actual[target]==wanted[name]for name,target in mapping.items()),
            'Independent original DMA/queue/raster/CD kernel differs')


def qualify_block_spans(row,length):
    """Exact original continuation clocks for these WRAM-to-WRAM TII primers."""
    integer(length,65536,1)
    entry=row['entry'];divisor=entry['clock_divisor'];calls=length+2
    require(row['clock_detail']=='partition-only'and row['original_calls']==calls and
            row['internal_clocked_ticks']==row['extra_ticks']==0 and
            row['returned_ticks']==(17+6*length)*divisor,
            'Original authored block continuation/count/duration differs')
    expected=[14*divisor]+[6*divisor]*length+[3*divisor]
    require(type(row['clocks'])is list and len(row['clocks'])==calls and
            all(type(s)is dict and set(s)==PARTITION_FIELDS for s in row['clocks'])and
            [s['requested']for s in row['clocks']]==expected,
            'Original authored block continuation clock partition differs')
    cursor=entry['ticks']
    for span in row['clocks']:
        require(type(span)is dict and set(span)==PARTITION_FIELDS,'Strict compact block clock required')
        for name in PARTITION_FIELDS-{'context'}:integer(span[name])
        require(span['context']=='wrapper'and span['before']==cursor and
                span['requested']>0 and span['after']==cursor+span['requested']and
                span['extra_before']==span['clocked_before']==span['pending_before']==0 and
                span['p_before']==entry['p']&~32 and span['mask_before']==row['entry_values'][21],
                'Original block clock partition/counters differ')
        cursor=span['after']
    require(cursor==row['state']['ticks'],'Original block clock closure differs')


def qualify_gear_journal(path,trace,case):
    """New dynamic domain; never weakens the old no-stall admission checker."""
    from pcerecomp import reference_trace as v1
    rows=strict_rows(path)
    require(len(rows)==case['primer_steps']+case['steps'],'Original stall journal extent differs')
    fields=set('phase ordinal original_calls clock_detail entry state entry_vram_sha256 vram_sha256 kernel_entry entry_values values returned_ticks internal_clocked_ticks extra_ticks pending_at_return kernel_at_return kernel_final clocks original_trace'.split())
    previous_state=previous_values=previous_vram=previous_kernel=None
    source_hits=Counter();checks=0;starts=[];ends=[];commands=[];edge_witnesses=[]
    measured_events=[];status_accesses=[];oracle=case['kernel_gear']
    require(len(oracle['primer_clocks'])==case['primer_steps'],'Complete independent primer clock ledger required')
    for index,row in enumerate(rows):
        require(type(row)is dict and set(row)==fields,'Strict original stall journal row required')
        phase='primer'if index<case['primer_steps']else'measured'
        ordinal=index+1 if phase=='primer'else index-case['primer_steps']+1
        require(row['phase']==phase and type(row['ordinal'])is int and row['ordinal']==ordinal,
                'Original stall phase/ordinal differs')
        entry,after=row['entry'],row['state']
        for state in(entry,after):v1._state(state,[])
        require(previous_state is None or entry==previous_state,'Original stall state chain breaks')
        origin=0 if phase=='primer'else trace.initial['ticks']
        check_values(row['entry_values'],entry,origin);check_values(row['values'],after,origin)
        if previous_values is not None:
            require(previous_values[:7]+previous_values[8:]==row['entry_values'][:7]+row['entry_values'][8:],
                    'Original stall device chain breaks')
        for name in('entry_vram_sha256','vram_sha256'):
            require(type(row[name])is str and re.fullmatch('[0-9a-f]{64}',row[name]),'Original full VRAM hash required')
        require(previous_vram is None or row['entry_vram_sha256']==previous_vram,'Original VRAM hash chain breaks')
        for name in('kernel_entry','kernel_at_return','kernel_final'):kernel_shape(row[name])
        check_kernel_values(row['kernel_entry'],row['entry_values'],entry)
        check_kernel_values(row['kernel_final'],row['values'],after)
        require(previous_kernel is None or row['kernel_entry']==previous_kernel,'Original kernel chain breaks')
        require(row['pending_at_return']==row['kernel_at_return']['cpu_pending'],
                'Original return sampling witness differs')
        returned=integer(row['returned_ticks'],minimum=1)
        internal=integer(row['internal_clocked_ticks']);extra=integer(row['extra_ticks'])
        require(returned==after['ticks']-entry['ticks'] and internal<=returned and
                row['values'][38]-row['entry_values'][38]==extra,'Original returned/dynamic accounting differs')
        events=row['original_trace'];require(type(events)is list and 1<=len(events)<=4096,'Original event bound')
        cpu_events=[];irq_events=[];last=entry['ticks']
        for event in events:
            callback_shape(event)
            require(last<=event['cycle']<=after['ticks'],'Original stall callback time/order differs')
            last=event['cycle'];kind=event['type']
            if kind=='cpu':cpu_events.append(event)
            elif kind=='TRACE_CPU_IRQ':irq_events.append(event)
            elif kind=='vdc'and event['event']==7:starts.append(event)
            elif kind=='vdc'and event['event']==6:ends.append(event)
            elif kind=='scsi'and event['event']==0:commands.append(event)
        require(len(cpu_events)==1 and len(irq_events)<=1,'Original stall CPU/IRQ event count differs')
        opcode=cpu_events[0];data=opcode['bytes'];pc=entry['pc'];mapping=entry['mpr']
        require(opcode['cycle']==entry['ticks']and opcode['pc']==pc and opcode['bank']==mapping[pc>>13],
                'Original stall fetched PC/MPR identity differs')
        for name in('a','x','y','sp','p'):
            require(opcode[name]==(entry[name]&~32 if name=='p'else entry[name]),'Original traced CPU register differs')
        physical=tuple((mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191)for i in range(len(data)))
        source_hits[(pc,tuple(mapping),physical,tuple(data))]+=1
        is_block=data[0]in BLOCKS
        require(row['clock_detail']==('partition-only'if phase=='primer'and is_block else'full-kernel'),
                'Only actual primer block opcodes may compact clock kernels')
        calls=integer(row['original_calls'],65538,1)
        if is_block:
            require(phase=='primer'and len(data)==7,'Only authored primer blocks allowed')
            length=(data[5]|data[6]<<8)or 65536
            require(calls==length+2 and extra==0 and returned==(17+6*length)*entry['clock_divisor'],
                    'Original block continuation/count/duration differs')
            qualify_block_spans(row,length)
        else:
            require(calls==1,'Original ordinary opcode must be one call')
            wanted=None if phase=='primer'else case['expected_gear'][ordinal-1]
            require(wanted is None or 'clock_partition'in wanted,'Independent measured clock partition missing')
            spans=qualify_spans(row,wanted)
            if phase=='measured':
                for edge in spans['source_edges']:
                    span=row['clocks'][edge['span']]
                    if edge['source']=='irq1':
                        matching=[e for e in events if e['type']=='vdc'and e['event']==6 and
                                  edge['before']<e['cycle']<=edge['after']]
                        require(len(matching)==1 and span['source_after']['vdc_status']&16 and
                                span['source_after']['dma_pending']==0,
                                'Dynamic IRQ1 edge lacks original DMA completion/source witness')
                    else:
                        matching=[e for e in events if e['type']=='cdrom'and e['event']==0 and
                                  e['irq_type']&64 and e['active']&e['enabled']&64 and
                                  edge['before']<e['cycle']<=edge['after']]
                        require(len(matching)==1 and span['source_after']['cd_active']&64,
                                'Dynamic IRQ2 edge lacks original CD request/source witness')
                    # The following callback sees the real CPU sample made
                    # after hardware returned. Never call source_after a sample.
                    last_span=row['clocks'][edge['span']]
                    next_span=(row['clocks'][edge['span']+1]
                               if edge['span']+1<len(row['clocks'])else None)
                    source=last_span['source_after']
                    sampled=0 if source['cpu_p']&4 else source['irr']&~source['cpu_mask']
                    observed=next_span['pending_before']if next_span else row['pending_at_return']
                    require(observed==sampled,'Dynamic source edge lacks subsequent original CPU sampling witness')
                    edge_witnesses.append(dict(ordinal=ordinal,**edge,actual_sample=observed))
        if phase=='primer':
            require(not irq_events,'Masked guest primer delivered IRQ')
            clock=oracle['primer_clocks'][ordinal-1]
            require(clock['pc']==pc and clock['entry_ticks']==entry['ticks']and
                    clock['after_ticks']==after['ticks'],
                    'Independent complete-primer instruction clock differs')
        else:
            measured_events.extend(events)
            wanted=case['expected_gear'][ordinal-1]
            before=case['expected_initial_gear']if ordinal==1 else case['expected_gear'][ordinal-2]
            event=trace.events[ordinal-1];group=trace.instructions[ordinal-1]
            require(entry==event['entry']and after==event['state'],'Original stall raw trace/journal differs')
            require(row['entry_values']==before['values']and row['values']==wanted['values'],
                    'Independent original dynamic device literal differs')
            require(row['entry_vram_sha256']==before['vram_sha256']and row['vram_sha256']==wanted['vram_sha256'],
                    'Independent original complete VRAM literal differs')
            qualify_kernel(row['kernel_entry'],wanted['kernel_entry'],entry['ticks'])
            qualify_kernel(row['kernel_final'],wanted['kernel_final'],after['ticks'])
            if data==[0xAD,0,0]:
                status_accesses.append(dict(kind='vdc-status-ack',
                    ticks=entry['ticks']+sum(wanted['clock_partition']['prefix']),
                    value=after['a'],irq1=int(bool(row['entry_values'][26]&2))))
            vector=irq_events[0]['vector']if irq_events else None
            require(len(irq_events)==wanted['irq_count']==group['irq_count']and
                    vector==wanted['irq_vector']==event['irq_vector']==group['irq_vector'],
                    'Original actual stall IRQ delivery differs')
            if irq_events:
                require(irq_events[0]['cycle']==entry['ticks']+internal and
                        irq_events[0]['pc']==wanted['irq_return_pc'] and
                        irq_events[0]['mask']==row['values'][21],'Original stall IRQ callback timing/return differs')
        previous_state,previous_values,previous_vram,previous_kernel=after,row['values'],row['vram_sha256'],row['kernel_final']
        checks+=2*39+len(row['clocks'])*3+len(events)*3
    require(dict(source_hits)==ledger(case['source_hits_gear']),'Original complete stall source/hit ledger differs')
    require(previous_state==trace.final['state'],'Original stall final closure differs')
    require(len(starts)==1 and len(ends)==int(bool(case['sources']&2)),
            'Genuine guest DMA start/completion IRQ witnesses required')
    require(starts[0]['cycle']==oracle['dma_start_ticks'],'Independent DMA launch clock differs')
    expected_events=oracle['events']
    expected_dma=[e['ticks']for e in expected_events if e['kind']=='dma-complete'and case['sources']&2]
    require([e['cycle']for e in ends]==expected_dma,'Independent original DMA assertion clock differs')
    cd_events=[e for e in measured_events if e['type']=='cdrom']
    request=[e for e in cd_events if e['event']==0]
    require([(e['cycle'],e['irq_type'],e['active'])for e in request]==[
        (e['ticks'],64,64)for e in expected_events if e['kind']=='cd-request'],
        'Independent original CD request clock/source differs')
    require([(e['cycle'],e['irq_type'],e['active'],e['enabled'])for e in cd_events if e['event']==2]==[
        (e['ticks'],e['value'],e['active'],e['enabled'])for e in expected_events if e['kind']=='cd-enable-write'],
        'Independent original CD enable/ACK access clock differs')
    require([(e['cycle'],e['irq_type'],e['active'],e['enabled'])for e in cd_events if e['event']==1]==[
        (e['ticks'],e['active'],0,e['enabled'])for e in expected_events if e['kind']=='cd-source-clear'],
        'Independent original CD source acknowledgement clock differs')
    require(all(e['event']in(0,1,2,7)for e in cd_events),'Unexpected measured CD event outside authored stall domain')
    require(status_accesses==[e for e in expected_events if e['kind']=='vdc-status-ack'],
            'Independent original VDC status acknowledgement clock/value differs')
    require(len(commands)==1 and commands[0]['command']==0xDE and commands[0]['phase']==3 and
            commands[0]['data']==[0xDE]+[0]*9,'Complete authored directory CDB required')
    for bit,name in((2,'irq1'),(1,'irq2')):
        matching=[edge for edge in edge_witnesses if edge['source']==name]
        require(len(matching)==int(bool(case['sources']&bit)),
                'Required source must assert inside an actual dynamic VRAM wait')
    return dict(checks=checks,actual_opcode_groups=len(rows),measured=case['steps'],
                dynamic_source_edges=edge_witnesses,
                scope='Independent device/CPU/WRAM/VRAM literals and original dynamic clocks; callback exit precedes CPU resample')


def build_gear(args, out, report, bindings, compiler, fixture):
    checkout, source = infrastructure.pinned_snapshot(args.gear_source.resolve(), out, bindings)
    report['gear_source_sha256'] = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    cpp, c = reference.compile_sources(checkout, source)
    cpp.append(ROOT/'tests/geargrafx_irq_stall_probe.cpp')
    deps = checkout/'platforms/shared/dependencies'
    # IRQ events are original TraceLogger records. Disabling the original
    # disassembler also disables these records, so that define is NOT used.
    flags = ['-O2', '-ffp-contract=off', '-ffunction-sections', '-fdata-sections',
             '-DGG_DISABLE_VGMRECORDER', '-DGG_DISABLE_MMI_THREADS']
    for path in (checkout/'src', ROOT/'tests', fixture, deps/'miniz',
                 deps/'libchdr/include', deps/'minivorbis', deps/'json'):
        flags += ['-I', str(path)]
    objects = out/'gear-objects'; objects.mkdir()
    jobs = []
    for index, path in enumerate(cpp+c):
        obj = objects/(str(index)+'-'+path.stem+'.o')
        command = [str(compiler), *flags, '-x', 'c++' if path.suffix=='.cpp' else 'c',
                   *(['-std=c++20', '-include', 'cerrno'] if path.suffix=='.cpp' else ['-std=c11']),
                   '-c', str(path), '-o', str(obj)]
        report['commands'].append(command); jobs.append((command, obj))
    def compile_one(job):
        command, obj = job
        result = subprocess.run(command, capture_output=True, timeout=180)
        obj.with_suffix('.stdout').write_bytes(result.stdout)
        obj.with_suffix('.stderr').write_bytes(result.stderr)
        result.check_returncode()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(compile_one, jobs))
    libraries = [p.resolve(strict=True) for p in args.library]
    if not libraries or any(not p.is_file() for p in libraries):
        raise ValueError('Supply existing explicit Gear dependency libraries')
    bindings['external_libraries'] = {str(p):sha(p) for p in libraries}
    binary = out/('gear-irq-stall.exe' if os.name=='nt' else 'gear-irq-stall')
    common.evidence([str(compiler), *[str(obj) for _,obj in jobs], *map(str,libraries),
                     '-Wl,--gc-sections', '-o', str(binary)], 'gear-link', out, report, bindings)
    bindings['gear_objects'] = {str(obj):sha(obj) for _,obj in jobs}
    bindings['gear_binary'] = {str(binary):sha(binary)}
    return binary


def build_tool(args, out, report, bindings, compiler, fixture):
    quote = infrastructure.cmake_quote
    tool = args.tool_source.resolve()
    cmake, ninja = (Path(shutil.which(str(v)) or '').resolve() for v in (args.cmake,args.ninja))
    if not cmake.is_file() or not ninja.is_file():
        raise ValueError('Existing CMake and Ninja required')
    bindings['tools'].update({str(p):sha(p) for p in (cmake,ninja)})
    wrapper = out/'tool-wrapper'; wrapper.mkdir()
    lines = ['cmake_minimum_required(VERSION 3.20)', 'project(IRQStallProof LANGUAGES CXX)',
             *['set('+name+' OFF CACHE BOOL "" FORCE)' for name in
               ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
             f'add_subdirectory({quote(tool)} tool)',
             f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
             f'add_executable(irq-stall-probe {quote(ROOT/"tests/irq_stall_probe.cpp")})',
             f'target_include_directories(irq-stall-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
             'target_link_libraries(irq-stall-probe PRIVATE ${_module} pce-runtime)',
             'target_compile_definitions(irq-stall-probe PRIVATE \"PCE_IRQ_STALL_CUE=\\\"'+quote(fixture/'authored.cue')[1:-1]+'\\\"\")']
    file = wrapper/'CMakeLists.txt'; file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)] = sha(file)
    build = out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja',
                     '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),
                     '-DCMAKE_MAKE_PROGRAM='+str(ninja)], 'tool-configure', out, report, bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','irq-stall-probe','--parallel','2'],
                    'tool-build', out, report, bindings, 600)
    binary = build/('irq-stall-probe.exe' if os.name=='nt' else 'irq-stall-probe')
    bindings['tool_binary'] = {str(binary):sha(binary)}
    return binary


def qualify_comparison(case,comparison):
    """Pin the entire first difference to independently computed timelines."""
    from pcerecomp.irq_trace import STATE_FIELDS
    require(case['queued_accesses']is True,'Queued hardware profile required')
    integer(comparison['matched_records'],len(case['expected_runtime']))
    require(comparison['compatible']is True and comparison['profile']=='architectural-elapsed-v1'and
            comparison['view']=='retirement-boundary','Declared elapsed comparison required')
    origins={p:case['kernel_'+p]['absolute_primer_ticks']for p in('runtime','gear')}
    expected=None;matched=0
    def difference(ordinal,field,a,b):
        return dict(ordinal=ordinal,field=field,expected=a,actual=b)
    def state_difference(ordinal,label,a,b):
        for field in STATE_FIELDS:
            if field=='mpr_latch':continue
            if a[field]!=b[field]:
                if field=='ticks':
                    return dict(difference(ordinal,label+'.ticks',a[field]+origins['runtime'],
                        b[field]+origins['gear']),expected_elapsed=a[field],actual_elapsed=b[field])
                return difference(ordinal,label+'.'+field,a[field],b[field])
        return None
    left=case['expected_initial_runtime'];right=case['expected_initial_gear']
    expected=state_difference(0,'initial',left['state'],right['state'])
    if expected is None:
        for ordinal,(a,b)in enumerate(zip(case['expected_runtime'],case['expected_gear']),1):
            for field,av,bv in(('entry_pc',left['state']['pc'],right['state']['pc']),
                ('entry_mpr',left['state']['mpr'],right['state']['mpr']),
                ('irq_count',a['irq_count'],b['irq_count']),('irq_vector',a['irq_vector'],b['irq_vector'])):
                if av!=bv:expected=difference(ordinal,field,av,bv);break
            if expected is None:expected=state_difference(ordinal,'state',a['state'],b['state'])
            if expected is not None:break
            matched+=1;left,right=a,b
    require(comparison['equal']is(expected is None)and typed_equal(comparison['first_difference'],expected)and
            comparison['matched_records']==matched,'Independent exact cross-engine difference descriptor differs')


def run(args):
    tool=args.tool_source.resolve();out=args.out.resolve()
    compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    require(not out.exists()and out.is_relative_to(ROOT/'.local')and compiler.is_file(),
            'New private output and existing compiler required')
    sys.path.insert(0,str(tool))
    from pcerecomp import project,irq_trace
    from pcerecomp.capture import load_capture
    from generate_irq_stall_fixture import generate,LITERAL_COLUMNS
    require(Path(project.__file__).resolve()==tool/'pcerecomp/project.py','Selected tool import required')
    paths=[Path(__file__),*[ROOT/'tests'/name for name in
        ('generate_irq_stall_fixture.py','generate_irq_device_fixture.py','irq_stall_probe.cpp','geargrafx_irq_stall_probe.cpp',
         'irq_trace_support.hpp','reference_trace_support.hpp','reset_probe_support.hpp')],
        *[ROOT/'scripts'/name for name in
          ('irq_boundary_reference.py','beetle_reference.py','mapper_reference.py','hucard_reference.py','filtered_audio_reference.py')],
        tool/'CMakeLists.txt']
    for folder in('pcerecomp','runtime','cmake'):
        paths.extend(p for p in(tool/folder).rglob('*')if p.is_file()and
                     p.suffix in('.py','.cpp','.hpp','.h','.cmake')and '__pycache__'not in p.parts)
    paths=sorted(set(paths))
    bindings=dict(tools={str(p):sha(p)for p in(compiler,Path(sys.executable).resolve())},
                  authored_sources={str(p.resolve()):sha(p)for p in paths})
    report=dict(schema=1,result='incomplete',commands=[],bindings=bindings,
        scope='Guest-generated VRAM DMA/prefetch stalls with IRQ1/IRQ2, independent full CPU/WRAM/VRAM/device literals and original Gear clock callbacks. Separate engine scheduler timelines; no electrical bus-phase or hardware parity claim.')
    out.mkdir(parents=True);epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,path in enumerate(paths):
        saved=epoch/str(index)/path.name;saved.parent.mkdir();shutil.copyfile(path,saved)
        bindings['authored_epoch'][str(saved)]=sha(saved)
    try:
        fixture=out/'fixture';metadata=generate(fixture)
        require(metadata['schema']==1 and metadata['runtime_abi']==ABI and
                metadata['literal_columns']==LITERAL_COLUMNS and len(LITERAL_COLUMNS)==39,
                'Independent authored device fixture schema required')
        require(len(metadata['cases'])==78,'All declared dynamic-stall cases required')
        cue=(fixture/metadata['cue']).resolve(strict=True)
        require(cue.is_relative_to(fixture.resolve()),'Bound authored media path required')
        bindings['fixture']={str(p):sha(p)for p in fixture.iterdir()if p.is_file()}
        gear=build_gear(args,out,report,bindings,compiler,fixture)
        binary=build_tool(args,out,report,bindings,compiler,fixture)
        identity=project.source_identity(tool);cases=[]
        for case in metadata['cases']:
            require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',case['id']),'Safe authored case label required')
            rom=(fixture/case['rom']).resolve(strict=True)
            require(rom.is_relative_to(fixture.resolve())and rom.stat().st_size==262144 and
                    sha(rom)==case['rom_sha256'],'Exact authored BIOS required')
            directory=out/case['id'];directory.mkdir();traces={};captures={};work={}
            gear_ram=directory/'gear-wram.bin';gear_vram=directory/'gear-vram.bin';journal=directory/'gear-journal.jsonl'
            result=common.evidence([str(gear),str(rom),str(cue),case['id'],str(gear_ram),str(gear_vram),str(journal)],
                                   'gear',directory,report,bindings)
            engine=dict(name='Geargrafx',revision=reference.COMMIT,
                source_sha256=report['gear_source_sha256'],binary_sha256=sha(gear))
            path,traces['gear']=previous.trace_file(directory,'gear',result.stdout,engine,rom,case['id'],'aggregate',[])
            bindings['raw_outputs'][str(path)]=sha(path)
            for tier in('native','interpreter'):
                capture=directory/(tier+'-capture.json');ram=directory/(tier+'-wram.bin')
                vram=directory/(tier+'-vram.bin');execution=directory/(tier+'-execution.json')
                result=common.evidence([str(binary),str(rom),str(cue),case['id'],tier,str(capture),str(ram),str(vram),str(execution)],
                                       tier,directory,report,bindings)
                engine=dict(name='pcerecomp-'+tier,revision=identity['revision'],
                    source_sha256=identity['source_sha256'],binary_sha256=sha(binary))
                path,traces[tier]=previous.trace_file(directory,tier,result.stdout,engine,rom,case['id'],'aggregate',[])
                observed,digest=load_capture(capture);captures[tier]=observed
                from pcerecomp.reference_trace import _json
                require(execution.stat().st_size<=128*1024*1024,'Execution receipt exceeds protocol bound')
                work[tier]=_json(execution.read_bytes())
                bindings['raw_outputs'].update({str(path):sha(path),str(capture):digest,
                    str(ram):sha(ram),str(vram):sha(vram),str(execution):sha(execution)})
                require(ram.stat().st_size==8192 and traces[tier].final['state']['wram_sha256']==sha(ram),
                        'Actual toolkit final WRAM differs')
                require(vram.stat().st_size==65536 and sha(vram)==case['expected_runtime'][-1]['vram_sha256'],
                        'Actual little-endian toolkit VRAM differs')
            require(gear_vram.stat().st_size==65536 and sha(gear_vram)==case['expected_gear'][-1]['vram_sha256'],
                    'Actual little-endian original VRAM differs')
            require(gear_ram.stat().st_size==8192 and traces['gear'].final['state']['wram_sha256']==sha(gear_ram),
                    'Actual original final WRAM differs')
            bindings['raw_outputs'].update({str(gear_ram):sha(gear_ram),str(gear_vram):sha(gear_vram),str(journal):sha(journal)})
            internal=irq_trace.compare_traces(traces['native'],traces['interpreter'],view='raw-event-exact')
            require(internal['equal'],'Native/interpreter raw event mismatch')
            checks=qualify_case(case,traces,captures,work)
            journal_checks=qualify_gear_journal(journal,traces['gear'],case)
            comparisons={profile:irq_trace.compare_traces(traces['native'],traces['gear'],profile=profile)
                         for profile in('exact','architectural-v1','architectural-elapsed-v1')}
            qualify_comparison(case,comparisons['architectural-elapsed-v1'])
            cases.append(dict(id=case['id'],queued_accesses=case['queued_accesses'],
                literal_checks=checks,journal_checks=journal_checks,execution=work,
                native_interpreter=internal,gear_comparisons=comparisons,
                trace_hashes={name:trace.sha256 for name,trace in traces.items()},
                observed_differences=previous.all_differences(traces['native'],traces['gear'])))
        report.update(result='pass-independent-dynamic-stall-literals',tool=identity,cases=cases,
            compiled_source_plan_execution_evidence=False,literal_columns=LITERAL_COLUMNS,
            actual_work=dict(cases=len(cases),measured_per_engine=sum(c['literal_checks']['measured_retirements']for c in cases),
                native_instructions=sum(c['execution']['native']['native_steps']for c in cases),
                interpreter_instructions=sum(c['execution']['interpreter']['interpreter_steps']for c in cases),
                native_fallback=sum(c['execution']['native']['interpreter_steps']for c in cases),
                native_guards=sum(c['execution']['native']['pure_guards']for c in cases),
                block_transfers_per_tier=sum(c['execution']['native']['block_steps']for c in cases)))
    except Exception as error:
        report.update(result='fail',error=repr(error));raise
    finally:
        reference.record_preservation(report,bindings)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    require(all(report['preservation'].values()),'Bound inputs changed during qualification')
    print(json.dumps({key:value for key,value in report.items()if key not in('commands','bindings','cases')},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True)
    parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compiler',default='clang++')
    parser.add_argument('--cmake',default='cmake');parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    try:run(parser.parse_args())
    except(ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError)as error:
        print(error,file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()
