"""Original-core qualification of guest-created active-display VRAM waits.

Authored CPU programs and independent clock/slot expectations are separate
from raw observations. The blank/DMA-only journal contract is unchanged.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import irq_stall_reference as shared
from scripts import mapper_reference as infrastructure
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as reference
from scripts import irq_boundary_reference as previous
sha=reference.sha
require=shared.require
integer=shared.integer
typed_equal=shared.typed_equal
ledger=shared.ledger
check_values=shared.check_values
qualify_case=shared.qualify_case
qualify_comparison=shared.qualify_comparison
strict_rows=shared.strict_rows
callback_shape=shared.callback_shape

KERNEL_FIELDS=shared.KERNEL_FIELDS|{'sprite_count','sat_pending','cached_allow','vwr'}
PARTITION_FIELDS=shared.PARTITION_FIELDS
FULL_FIELDS=shared.FULL_FIELDS
BLOCKS=shared.BLOCKS


def kernel_shape(value):
    require(type(value)is dict and set(value)==KERNEL_FIELDS,'Strict original active-display kernel required')
    shared.kernel_shape({name:value[name]for name in shared.KERNEL_FIELDS})
    integer(value['sprite_count'],16)
    integer(value['sat_pending'],1024)
    integer(value['cached_allow'],1)
    for name in('marr','mawr','vwr','dcr','sour','desr','lenr','read_buffer','vram_bus'):
        integer(value[name],65535)
    integer(value['latched_cr'],65535)
    integer(value['latched_mwr'],255)


def slot_decision(kernel):
    """Independent integer predicate for the declared pinned display profile.

    This interprets an already observed state, not a source of phase goldens.
    Original eligibility methods are never called: they mutate a cache.
    """
    kernel_shape(kernel)
    h=kernel['hpos'];d=kernel['divider'];burst=kernel['burst']
    fetching=not burst and kernel['bg_start']<=h<kernel['bg_end']and 14<=kernel['vpos']<256
    sprites=bool(kernel['latched_cr']&64)
    result=dict(eligible=False,reason='dma',fetching=bool(fetching))
    if kernel['sat_pending']or kernel['dma_pending']:return result
    if kernel['vstate']!=1 or burst or(not fetching and(not sprites or not kernel['sprite_count'])):
        allowed=(h//d)%2==0;reason='idle-parity'
    elif fetching:
        relative=(h-kernel['bg_start'])//d-1
        mode=kernel['latched_mwr']&3
        allowed=relative>=0 and((relative%2==0)if mode==0 else(relative%8 in(2,3))if mode in(1,2)else False)
        reason='background';result.update(relative_dot=relative,bg_mode=mode)
    elif sprites:
        # Strict greater-than is intentional. At exact end the selected
        # original profile uses a wrapped line of elapsed sprite time.
        elapsed=h-kernel['bg_end']if h>kernel['bg_end']else 1365-kernel['bg_end']+h
        cost=(4,4,8,16)[(kernel['latched_mwr']>>2)&3]
        allowed=elapsed//d>=kernel['sprite_count']*cost and(h//d)%2==0
        reason='sprite';result.update(sprite_elapsed_dots=elapsed//d,sprite_cost=cost)
        if elapsed//d>=kernel['sprite_count']*cost and not allowed:reason='parity'
    else:allowed=True;reason='uncontended'
    if allowed and kernel['hstate']==3:
        since=((h+3)%1365+1365-kernel['hsync_start'])%1365
        if since<8*d:allowed=False;reason='hsync-exclusion'
        result['hsync_since']=since
    result.update(eligible=bool(allowed),reason=reason)
    return result


def qualify_dynamic_queue(span,increment=1):
    """One actual3tick callback contains exactly one ready-slot decision."""
    before,after=span['source_before'],span['source_after']
    require(type(increment)is int and increment in(1,32,64,128),'Declared VDC increment required')
    integer(span['before']);integer(span['after']);integer(span['requested'],3,3)
    require(span['after']==span['before']+3,'Actual queue callback timestamps differ')
    kernel_shape(before);kernel_shape(after)
    require(span['context']=='inline'and span['requested']==3 and
            before['vram_carry']==after['vram_carry']==0,'Declared CPU queue decision requires carry0 and3ticks')
    require(before['read_pending']or before['write_pending'],'Active dynamic wait has no pending VRAM request')
    delay=max(0,before['vram_delay']-3)
    decision=slot_decision(before)
    grant=delay==0 and decision['eligible']
    read=bool(grant and before['read_pending'])
    write=bool(grant and not before['read_pending']and before['write_pending'])
    require(after['vram_delay']==delay and after['read_pending']==before['read_pending']-int(read)and
            after['write_pending']==before['write_pending']-int(write),
            'Original active VRAM queue completion differs from independent ready-slot decision')
    require(after['marr']==((before['marr']+increment)&65535 if read else before['marr'])and
            after['mawr']==((before['mawr']+increment)&65535 if write else before['mawr']),
            'Original active VRAM read priority or pointer advancement differs')
    require(after['vwr']==before['vwr']and(read or after['read_buffer']==before['read_buffer']),
            'Hardware clock fabricated a CPU data latch or unrelated read-buffer change')
    return dict(before=span['before'],after=span['after'],ready=delay==0,
                grant='read'if read else'write'if write else None,
                attempt_kind='read'if before['read_pending']else'write',
                delay_before=before['vram_delay'],hclock=before['hpos'],
                read_pending=before['read_pending'],write_pending=before['write_pending'],
                marr=after['marr'],mawr=after['mawr'],read_buffer=after['read_buffer'],vwr=after['vwr'],**decision)


MODEL_FIELDS=set('ticks divider hclock dma_pending read_pending write_pending vram_delay vram_carry marr read_buffer irq_requests vdc_status cd_enabled cd_active scsi_signals scsi_phase scsi_data response_index mawr vwr vpos hstate vstate bg_start bg_end hsync_start burst latched_cr latched_mwr sprite_count sat_pending'.split())
MODEL_MAP={name:name for name in MODEL_FIELDS-{'ticks','hclock','irq_requests'}}
MODEL_MAP.update(hclock='hpos',irq_requests='irr')


def qualify_model_kernel(actual,wanted,ticks):
    kernel_shape(actual)
    require(type(wanted)is dict and set(wanted)==MODEL_FIELDS,'Complete independently modeled active kernel required')
    for name,value in wanted.items():integer(value,minimum=-2**31 if name=='vram_delay'else 0)
    require(wanted['ticks']==ticks,'Independent absolute active-kernel timestamp differs')
    require(all(actual[target]==wanted[name]for name,target in MODEL_MAP.items()),
            'Independent original active display/queue/register kernel differs')


def qualify_display_phase(kernel,case,ticks):
    """Steady guest-programmed geometry derived from clocks, never a phase seed."""
    kernel_shape(kernel);integer(ticks)
    d=case['divider'];h=ticks%1365;line=(ticks//1365)%262
    require(32<=line<80,'Measured callback left the declared steady SAT/raster interval')
    forced=32 if d==3 else 24;display=forced+24
    state=3 if h<forced*d else 0 if h<display*d else 1 if h<(display+240)*d else 2
    expected=dict(hpos=h,vpos=line,divider=d,hstate=state,vstate=1,
        bg_start=(display-16)*d,bg_end=(display+240)*d,hsync_start=0,
        burst=0,latched_cr=case['cr'],latched_mwr=case['mwr'],
        sprite_count=case['cells'],sat_pending=0,dma_pending=0)
    require(all(kernel[name]==value for name,value in expected.items()),
            'Original interior display phase/latches/cell budget differs from authored clock geometry')


def qualify_candidates(case,decisions):
    oracle=case['kernel_gear'];candidates=oracle['candidates']
    fields={'ticks','visible_ticks','context','kind','hclock','delay_before','read_pending','write_pending','allowed','reason'}
    def candidate_shape(item,grant=False):
        extra={'marr','mawr','read_buffer','vwr'}if grant else set()
        require(type(item)is dict and set(item)==fields|extra,'Strict independent ready-slot record required')
        for name in('ticks','visible_ticks','hclock','delay_before','read_pending','write_pending'):
            integer(item[name])
        for name in extra:integer(item[name],65535)
        for name in('read_pending','write_pending'):integer(item[name],1)
        require(type(item['allowed'])is bool and item['context']in('dynamic','fixed','wrapper')and
                item['kind']in('read','write')and item['reason']in('background','sprite','parity','hsync','grant')and
                item['allowed']is(item['reason']=='grant')and
                item['visible_ticks']==item['ticks']+3 and item['hclock']==item['ticks']%1365 and
                item['delay_before']<=3 and(item['read_pending']or item['write_pending']),
                'Independent ready-slot types or phase differ')
    require(type(candidates)is list and len(candidates)<=200000 and type(oracle['grants'])is list,
            'Bounded independent candidate/grant ledgers required')
    for grant in oracle['grants']:candidate_shape(grant,True)
    expected={}
    for item in candidates:
        candidate_shape(item)
        require(item['ticks']not in expected,'Duplicate independent candidate time')
        expected[item['ticks']]=item
    granted={}
    for item in oracle['grants']:
        tick=item['ticks']
        require(tick not in granted and tick in expected and expected[tick]['allowed']is True and
                typed_equal({name:item[name]for name in fields},expected[tick]),
                'Independent granted ledger is detached from a unique allowed candidate')
        granted[tick]=item
    require(set(granted)=={tick for tick,item in expected.items()if item['allowed']},
            'Independent granted ledger does not cover exact allowed candidates')
    observed={}
    for item in decisions:
        require(type(item['ready'])is bool and type(item['eligible'])is bool and
                item['grant']==(item['attempt_kind']if item['ready']and item['eligible']else None),
                'Actual granted label differs from ready read/write priority')
        if not item['ready']:continue
        reason='grant'if item['grant']else{'idle-parity':'parity','hsync-exclusion':'hsync'}.get(item['reason'],item['reason'])
        value=dict(ticks=item['before'],visible_ticks=item['after'],context=item['clock_kind'],
            kind=item['attempt_kind'],hclock=item['hclock'],delay_before=item['delay_before'],
            read_pending=item['read_pending'],write_pending=item['write_pending'],allowed=item['eligible'],reason=reason)
        require(item['before']not in observed and typed_equal(value,expected.get(item['before'])),
                'Original ready slot differs from independently timed candidate ledger')
        observed[item['before']]=value
        if item['grant']:
            grant=granted.get(item['before'])
            require(grant is not None and all(item[k]==grant[k]for k in('marr','mawr','read_buffer','vwr')),
                    'Original granted read/write data differs from independently timed completion')
    required={t for t,e in expected.items()if e['context']=='dynamic'or(e['context']=='fixed'and case['speed']==3)}
    require(set(observed)==required,'Actual observable ready-slot extent differs')
    positive=any(row['extra_ticks']for row in case['expected_gear'])
    denied=sum(not e['allowed']and e['reason']in('background','sprite')for e in candidates)
    integer(oracle['arbitration_denials'])
    coverage='arbitration-denied'if denied else'latency-only'if positive else'zero-wait'
    require(type(oracle['positive_wait'])is bool and oracle['positive_wait']==bool(positive)and
            oracle['arbitration_denials']==denied and oracle['coverage']==coverage,
            'Independent active coverage classification differs')
    boundary=[]
    if case['family']=='boundary':
        d=case['divider'];end=((32 if d==3 else 24)+24+240)*d
        end_tick=(oracle['absolute_primer_ticks']//1365)*1365+end
        for delta,kind,allowed,read,write in((-3,'read',False,1,1),(0,'read',True,1,1),(3,'write',False,0,1)):
            tick=end_tick+delta;item=observed.get(tick)
            require(item is not None and item['context']=='dynamic'and item['kind']==kind and
                    item['allowed']is allowed and item['read_pending']==read and item['write_pending']==write,
                    'Required actual ready endpoint triple/read-priority witness missing')
            boundary.append(item)
        require(typed_equal(boundary,oracle['boundary_candidates']),
                'Independent endpoint triple descriptor differs')
    else:require(oracle['boundary_candidates']==[],'Unexpected endpoint claim in another family')
    return dict(observable_ready_candidates=len(observed),independent_ready_candidates=len(expected),
                expected_coverage=coverage,cpu_wait=bool(positive),boundary_triple=boundary)


def qualify_mmio_stages(row,wanted,data):
    """Bind every declared zero-clock port effect, including the INC-high gap."""
    partition=wanted['clock_partition'];stages=wanted['mmio_stages'];spans=row['clocks']
    require(type(stages)is list,'Independent semantic port stages required')
    prefix=len(partition['prefix']);runs=partition['wait_runs']
    expected=[]
    if data in([0xAD,2,0],[0xAD,3,0]):
        require(len(runs)==1 and prefix==1 and not partition['suffix'],'Mapped read clock shape differs')
        expected=[('read-high'if data[1]==3 else'read-low',prefix+runs[0])]
    elif data in([0x8D,2,0],[0x8D,3,0]):
        require(len(runs)==1 and prefix==0 and len(partition['suffix'])==1,'Mapped write clock shape differs')
        expected=[('write-high'if data[1]==3 else'write-low',runs[0])]
    elif data==[0xEE,3,0]:
        require(len(runs)==2 and runs[1]>0 and prefix==1 and len(partition['suffix'])==1,
                'High-port INC requires a distinct queued read before its write')
        expected=[('read-high',prefix+runs[0]),('write-high',prefix+sum(runs))]
    require(len(stages)==len(expected),'Independent port-effect stage count differs')
    last_read=None
    for stage,(kind,index)in zip(stages,expected):
        require(type(stage)is dict and set(stage)=={'kind','span_index','before','after','value'},
                'Strict independent zero-clock port stage required')
        integer(stage['span_index'],len(spans)-1);integer(stage['value'],255)
        require(stage['kind']==kind and stage['span_index']==index,'Independent port effect placement differs')
        before=row['kernel_entry']if index==0 else spans[index-1]['source_after']
        after=spans[index]['source_before'];ticks=spans[index]['before']
        require(ticks==(row['entry']['ticks']if index==0 else spans[index-1]['after']),
                'Guest port effect must not invent hardware clocks')
        qualify_model_kernel(before,stage['before'],ticks)
        qualify_model_kernel(after,stage['after'],ticks)
        changes={};value=stage['value']
        if kind.startswith('read'):
            byte=(before['read_buffer']>>8)if kind=='read-high'else before['read_buffer']&255
            require(value==byte,'Independent port read differs from actual held buffer')
            last_read=value
            if kind=='read-high':
                changes.update(read_pending=1,vram_delay=15 if before['divider']==2 else 24)
        else:
            require(not before['read_pending']and not before['write_pending'],
                    'Mapped VWR write bypassed a pending queue')
            byte=((last_read+1)&255)if data==[0xEE,3,0]else row['entry']['a']
            require(value==byte,'Independent CPU store/RMW byte differs')
            changes['vwr']=((before['vwr']&255)|(value<<8))if kind=='write-high'else((before['vwr']&65280)|value)
            if kind=='write-high':
                changes.update(write_pending=1,vram_delay={4:21,3:18,2:12}[before['divider']])
        pending=changes.get('read_pending',before['read_pending'])or changes.get('write_pending',before['write_pending'])
        changes['vdc_status']=(before['vdc_status']&~64)|(64 if pending else 0)
        stable=KERNEL_FIELDS-{'cpu_extra','cpu_clocked','cpu_pending','cpu_p'}
        require(all(after[name]==changes.get(name,before[name])for name in stable),
                'Original zero-clock port effect differs from independent causal register/queue transition')
    return len(stages)


def qualify_spans(row,wanted=None,data=None):
    """Identify waits by original extra-counter increments, never length alone.

    A fast fixed memory wait is also three ticks. Only an inline callback
    with a three-tick increase in the original extra counter is dynamic.
    Hardware callback exit precedes the CPU's CheckIRQs invocation.
    """
    spans=row['clocks'];detail=row['clock_detail'];entry=row['entry'];after=row['state']
    integer(row['internal_clocked_ticks']);integer(row['extra_ticks'])
    integer(entry['ticks']);integer(after['ticks'])
    require(type(entry['clock_divisor'])is int and entry['clock_divisor']in(3,12),'Actual CPU clock divisor required')
    require(type(spans)is list and 1<=len(spans)<=200000,'Bounded original stall clock callbacks required')
    require(detail in('partition-only','full-kernel'),'Original clock detail invalid')
    cursor=entry['ticks'];clocked=extra=0;dynamic=[];fixed=[];wrapper=[];edges=[]
    previous_inline=None;queue_decisions=[];port_barriers=set()
    if wanted is not None:
        partition=wanted['clock_partition']
        require(type(partition)is dict and set(partition)=={'prefix','wait_runs','suffix','drain'},
                'Independent active clock partition required')
        for name in('prefix','wait_runs','suffix'):
            require(type(partition[name])is list,'Independent active clock lists required')
        for ticks in partition['prefix']+partition['suffix']:integer(ticks,minimum=1)
        for count in partition['wait_runs']:integer(count,200000)
        integer(partition['drain'])
        for name in('extra_ticks','internal_clocked_ticks','fixed_wait_count'):integer(wanted[name])
        require(len(partition['wait_runs'])in(0,1,2),'Declared active memory-access wait groups required')
        if not partition['wait_runs']:
            require(type(data)is list and data and(data==[0xEA]or(data[0]==0x80 and len(data)==2))and
                    not partition['prefix']and not partition['suffix']and wanted['mmio_stages']==[],
                    'Only authored non-MMIO NOP/BRA may omit memory wait groups')
        elif len(partition['wait_runs'])==1:
            require(data in([0xAD,2,0],[0xAD,3,0],[0x8D,2,0],[0x8D,3,0]),
                    'One wait group requires an authored mapped VRAM port access')
        if len(partition['wait_runs'])==2:
            require(data==[0xEE,3,0] and len(partition['prefix'])==len(partition['suffix'])==1,
                    'Only authored high-port INC may divide consecutive dynamic groups')
            port_barriers.add(len(partition['prefix'])+partition['wait_runs'][0])
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
            require(before['hpos']==span['before']%1365 and finish['hpos']==span['after']%1365,
                    'Original callback beam phase detached from actual master clock')
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
                if len(dynamic)>1 and dynamic[-2]==index-1 and index not in port_barriers:
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
        if detail=='full-kernel'and span['requested']==3 and(before['read_pending']or before['write_pending']):
            decision=qualify_dynamic_queue(span)
            queue_decisions.append(dict(span=index,clock_kind='dynamic'if difference else'fixed',**decision))
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
        expected=[('inline',n)for n in partition['prefix']]
        expected_dynamic=[]
        for count in partition['wait_runs']:
            expected_dynamic.extend(range(len(expected),len(expected)+count))
            expected.extend([('inline',3)]*count)
        expected.extend(('inline',n)for n in partition['suffix'])
        if partition['drain']:expected.append(('wrapper',partition['drain']))
        require([(s['context'],s['requested'])for s in spans]==expected and dynamic==expected_dynamic,
                'Independent original exact active wait groups/clock partition differ')
    return dict(dynamic_indices=dynamic,fixed_indices=fixed,wrapper=wrapper,source_edges=edges,queue_decisions=queue_decisions,port_barriers=sorted(port_barriers))



def check_kernel_values(kernel,values,state):
    kernel_shape(kernel)
    associations={'cpu_p':5,'cpu_mask':21,'irr':26,'vdc_status':27,'cd_enabled':28,
        'cd_active':29,'scsi_signals':31,'scsi_phase':32,'scsi_data':33,
        'response_index':34,'dma_pending':35,'read_pending':36,'write_pending':37}
    require(all(kernel[name]==values[index]for name,index in associations.items()),
            'Original row kernel/device literal association differs')
    require(kernel['cpu_p']==state['p'],'Original kernel CPU status differs')



def qualify_gear_journal(path,trace,case):
    """Active-display domain; the older blank-slot checker remains strict."""
    from pcerecomp import reference_trace as v1
    rows=strict_rows(path)
    require(len(rows)==case['primer_steps']+case['steps'],'Original stall journal extent differs')
    fields=set('phase ordinal original_calls clock_detail entry state entry_vram_sha256 vram_sha256 kernel_entry entry_values values returned_ticks internal_clocked_ticks extra_ticks pending_at_return kernel_at_return kernel_final clocks original_trace'.split())
    previous_state=previous_values=previous_vram=previous_kernel=None
    source_hits=Counter();checks=0;starts=[];ends=[];commands=[];sat_starts=[];sat_arms=[];decisions=[];port_stages=0
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
            elif kind=='vdc'and event['event']==8:sat_starts.append(event)
            elif kind=='vdc'and event['event']==0 and event['reg']==19 and event['msb']:sat_arms.append(event)
            elif kind=='vdc'and event['event']==6:ends.append(event)
            elif kind=='scsi'and event['event']==0:commands.append(event)
        require(len(cpu_events)==1 and not irq_events,'Authored active-display baseline must retain one opcode and no IRQ delivery')
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
            require(phase=='primer'and len(data)==7 and data[0]==0x73,'Only authored WRAM TII primer blocks allowed')
            length=(data[5]|data[6]<<8)or 65536
            require(calls==length+2 and extra==0 and returned==(17+6*length)*entry['clock_divisor'],
                    'Original block continuation/count/duration differs')
            shared.qualify_block_spans(row,length)
        else:
            require(calls==1,'Original ordinary opcode must be one call')
            wanted=None if phase=='primer'else case['expected_gear'][ordinal-1]
            require(wanted is None or 'clock_partition'in wanted,'Independent measured clock partition missing')
            if phase=='measured':
                for span in row['clocks']:
                    qualify_display_phase(span['source_before'],case,span['before'])
                    qualify_display_phase(span['source_after'],case,span['after'])
            spans=qualify_spans(row,wanted,data)
            if phase=='measured':
                for decision in spans['queue_decisions']:
                    decisions.append(dict(ordinal=ordinal,**decision))
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
            qualify_model_kernel(row['kernel_entry'],wanted['kernel_entry'],entry['ticks'])
            qualify_model_kernel(row['kernel_final'],wanted['kernel_final'],after['ticks'])
            port_stages+=qualify_mmio_stages(row,wanted,data)
            require(not any(e['type']in('cdrom','scsi')for e in events),
                    'Unexpected CD transport activity in idle-CD active-display baseline')
            writes=[e for e in events if e['type']=='vdc'and e['event']==0]
            stages=[s for s in wanted['mmio_stages']if s['kind'].startswith('write')]
            require(len(writes)==len(stages),'Original VDC write callback count differs')
            for write_event,stage in zip(writes,stages):
                require(write_event['cycle']==stage['before']['ticks']and write_event['reg']==2 and
                        write_event['raw']==stage['value']and write_event['msb']==int(stage['kind']=='write-high')and
                        write_event['value']==stage['after']['vwr'],
                        'Independent original VWR write callback clock/byte/word differs')
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
    require(not starts and not ends and not commands,'Unexpected measured-profile VRAM DMA/CD command source')
    require(len(sat_starts)==len(sat_arms)==1 and
            sat_arms[0]['value']==0x7000 and sat_arms[0]['cycle']<=sat_starts[0]['cycle']<trace.initial['ticks'],
            'One genuine guest-armed SATB DMA before active observation required')
    ready=[d for d in decisions if d['ready']]
    denied=[d for d in ready if not d['eligible']]
    coverage=qualify_candidates(case,decisions)
    return dict(checks=checks,actual_opcode_groups=len(rows),measured=case['steps'],
                semantic_port_stages=port_stages,queue_decisions=decisions,
                ready_candidates=len(ready),denied_candidates=len(denied),coverage=coverage,
                scope='Independent CPU/WRAM/VRAM/active kernels, exact original clocks and zero-clock port effects; callback exit precedes CPU sampling')


def build_gear(args, out, report, bindings, compiler, fixture):
    checkout, source = infrastructure.pinned_snapshot(args.gear_source.resolve(), out, bindings)
    report['gear_source_sha256'] = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    cpp, c = reference.compile_sources(checkout, source)
    cpp.append(ROOT/'tests/geargrafx_vram_active_probe.cpp')
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
    binary = out/('gear-vram-active.exe' if os.name=='nt' else 'gear-vram-active')
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
    lines = ['cmake_minimum_required(VERSION 3.20)', 'project(VramActiveProof LANGUAGES CXX)',
             *['set('+name+' OFF CACHE BOOL "" FORCE)' for name in
               ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
             f'add_subdirectory({quote(tool)} tool)',
             f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
             f'add_executable(vram-active-probe {quote(ROOT/"tests/vram_active_probe.cpp")})',
             f'target_include_directories(vram-active-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
             'target_link_libraries(vram-active-probe PRIVATE ${_module} pce-runtime)',
             'target_compile_definitions(vram-active-probe PRIVATE \"PCE_VRAM_ACTIVE_CUE=\\\"'+quote(fixture/'authored.cue')[1:-1]+'\\\"\")']
    file = wrapper/'CMakeLists.txt'; file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)] = sha(file)
    build = out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja',
                     '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),
                     '-DCMAKE_MAKE_PROGRAM='+str(ninja)], 'tool-configure', out, report, bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','vram-active-probe','--parallel','2'],
                    'tool-build', out, report, bindings, 600)
    binary = build/('vram-active-probe.exe' if os.name=='nt' else 'vram-active-probe')
    bindings['tool_binary'] = {str(binary):sha(binary)}
    return binary


def run(args):
    tool=args.tool_source.resolve();out=args.out.resolve()
    compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    require(not out.exists()and out.is_relative_to(ROOT/'.local')and compiler.is_file(),
            'New private output and existing compiler required')
    sys.path.insert(0,str(tool))
    from pcerecomp import project,irq_trace
    from pcerecomp.capture import load_capture
    from generate_vram_active_fixture import generate,LITERAL_COLUMNS
    require(Path(project.__file__).resolve()==tool/'pcerecomp/project.py','Selected tool import required')
    paths=[Path(__file__),*[ROOT/'tests'/name for name in
        ('generate_vram_active_fixture.py','generate_irq_device_fixture.py','vram_active_probe.cpp','geargrafx_vram_active_probe.cpp',
         'irq_trace_support.hpp','reference_trace_support.hpp','reset_probe_support.hpp')],
        *[ROOT/'scripts'/name for name in
          ('irq_stall_reference.py','irq_device_reference.py','irq_boundary_reference.py','beetle_reference.py','mapper_reference.py','hucard_reference.py','filtered_audio_reference.py')],
        tool/'CMakeLists.txt']
    for folder in('pcerecomp','runtime','cmake'):
        paths.extend(p for p in(tool/folder).rglob('*')if p.is_file()and
                     p.suffix in('.py','.cpp','.hpp','.h','.cmake')and '__pycache__'not in p.parts)
    paths=sorted(set(paths))
    bindings=dict(tools={str(p):sha(p)for p in(compiler,Path(sys.executable).resolve())},
                  authored_sources={str(p.resolve()):sha(p)for p in paths})
    report=dict(schema=1,result='incomplete',commands=[],bindings=bindings,
        scope='Guest-generated active-display VRAM requests with independent CPU/WRAM/VRAM/arbitration literals and original Gear clock callbacks. Separate engine scheduler timelines; no electrical bus-phase, whole-renderer or hardware parity claim.')
    out.mkdir(parents=True);epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,path in enumerate(paths):
        saved=epoch/str(index)/path.name;saved.parent.mkdir();shutil.copyfile(path,saved)
        bindings['authored_epoch'][str(saved)]=sha(saved)
    try:
        fixture=out/'fixture';metadata=generate(fixture)
        require(metadata['schema']==1 and metadata['runtime_abi']==ABI and
                metadata['literal_columns']==LITERAL_COLUMNS and len(LITERAL_COLUMNS)==39,
                'Independent authored device fixture schema required')
        require(len(metadata['cases'])==138,'All declared active-display configurations required')
        expected=set()
        for speed in(12,3):
            for divider in(4,3,2):
                expected.update(('bg',access,speed,divider,mode,128,0)
                    for mode in range(4)for access in('read','write','rmw'))
                expected.update(('sprite','read',speed,divider,mode<<2,64,cells)
                    for mode in range(4)for cells in(1,4))
                expected.update(('boundary','dual',speed,divider,15,64,cells)for cells in(1,4,16))
        actual={(c['family'],c['access'],c['speed'],c['divider'],c['mwr'],c['cr'],c['cells'])for c in metadata['cases']}
        require(actual==expected,'Exact active-display feature matrix differs')
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
        report.update(result='pass-independent-active-display-literals',tool=identity,cases=cases,
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
