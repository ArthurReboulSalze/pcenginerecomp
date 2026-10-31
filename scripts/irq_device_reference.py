"""Guest-generated IRQ priority and device-acknowledgement reference checks.

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


def strict_rows(path):
    from pcerecomp.reference_trace import _json
    path=Path(path)
    require(path.stat().st_size<=128*1024*1024,'Original journal extent exceeds protocol bound')
    rows=[]
    with path.open('rb')as stream:
        while raw:=stream.readline(8*1024*1024+1):
            require(len(raw)<=8*1024*1024 and len(rows)<100000,'Original journal record bound')
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
            'block_steps','pure_guards','raw_initial_ticks','literal_rows'}
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


def qualify_gear_journal(path,trace,case):
    """Check actual original calls/clocks and the declared finite device scope."""
    from pcerecomp import reference_trace as v1
    rows=strict_rows(path)
    require(len(rows)==case['primer_steps']+case['steps'],'Original call journal extent differs')
    fields={'phase','ordinal','original_calls','entry','state','entry_values','values',
            'returned_ticks','internal_clocked_ticks','extra_ticks','clocks','original_trace'}
    previous_state=previous_values=None;source_hits=Counter();checks=0
    dma_start=[];dma_end=[];commands=[];cd_source_assertions=[];measured=0
    for index,row in enumerate(rows):
        require(type(row)is dict and set(row)==fields,'Strict original device journal record required')
        phase='primer'if index<case['primer_steps']else'measured'
        ordinal=index+1 if phase=='primer'else index-case['primer_steps']+1
        require(row['phase']==phase and type(row['ordinal'])is int and row['ordinal']==ordinal,'Original phase/ordinal differs')
        calls=integer(row['original_calls'],65538,1)
        require(phase!='measured'or calls==1,'Measured call must be exactly one original opcode')
        entry,after=row['entry'],row['state']
        for state in(entry,after):v1._state(state,[])
        require(previous_state is None or entry==previous_state,'Original CPU/WRAM clock chain breaks')
        origin=0 if phase=='primer'else trace.initial['ticks']
        check_values(row['entry_values'],entry,origin);check_values(row['values'],after,origin)
        if previous_values is not None:
            a,b=previous_values,row['entry_values']
            require(a[:7]+a[8:]==b[:7]+b[8:],'Original device observation chain breaks')
        returned=integer(row['returned_ticks'],minimum=1)
        internal=integer(row['internal_clocked_ticks']);extra=integer(row['extra_ticks'])
        require(after['ticks']-entry['ticks']==returned and internal<=returned,'Original returned/internal clock accounting differs')
        require(row['values'][38]-row['entry_values'][38]==extra,'Original cumulative dynamic waits differ')
        spans=row['clocks'];require(type(spans)is list and 1<=len(spans)<=200000,'Original actual clock callbacks required')
        cursor=entry['ticks']
        for span in spans:
            require(type(span)is dict and set(span)=={'before','requested','after'},'Strict original clock callback required')
            for field in span:integer(span[field])
            require(span['before']==cursor and span['requested']>0 and span['after']==cursor+span['requested'],
                    'Original clock callback chain differs')
            cursor=span['after']
        require(cursor==after['ticks'],'Original callback clocks do not close the actual call')
        events=row['original_trace'];require(type(events)is list and 1<=len(events)<=4096,'Original callback extent invalid')
        cpu_events=[];irq_events=[];cd_events=[];last_cycle=entry['ticks']
        for event in events:
            callback_shape(event)
            require(last_cycle<=event['cycle']<=after['ticks'],'Original callback timestamp/order outside call')
            last_cycle=event['cycle'];kind=event['type']
            if kind=='cpu':cpu_events.append(event)
            elif kind=='TRACE_CPU_IRQ':irq_events.append(event)
            elif kind=='vdc'and event['event']==7:
                require(phase=='primer','Unexpected measured DMA-start witness')
                dma_start.append(event)
            elif kind=='vdc'and event['event']==6:
                require(phase=='primer','Unexpected measured DMA-end witness')
                dma_end.append(event)
            elif kind=='scsi'and event['event']==0:
                require(phase=='primer','Unexpected measured command witness')
                commands.append(event)
            elif kind=='cdrom':
                cd_events.append(event)
                if event['event']==0:
                    require(phase=='primer','Unexpected measured CD-source assertion')
                    cd_source_assertions.append(event)
        require(len(cpu_events)==1 and len(irq_events)<=1,'Original opcode/IRQ callback count differs')
        opcode=cpu_events[0]
        require(opcode['cycle']==entry['ticks']and opcode['pc']==entry['pc']and
                opcode['bank']==entry['mpr'][entry['pc']>>13],'Original fetched source entry differs')
        for field in('a','x','y','sp','p'):
            require(opcode[field]==(entry[field]&~32 if field=='p'else entry[field]),'Original traced register differs')
        pc=entry['pc'];mapping=entry['mpr'];data=opcode['bytes']
        is_block=data[0]in(0x73,0xC3,0xD3,0xE3,0xF3)
        if is_block:
            # These authored block operands are ROM bytes, distinct from the
            # WRAM stack/data aliases. Original Gear returns once for start,
            # once per payload byte and once for closing. It is still one
            # opcode group, never that many retired guest instructions.
            require(len(data)==7 and all(mapping[((pc+i)&65535)>>13]<0x20 for i in range(7)),
                    'Authored original block operands must remain stable ROM')
            length=(data[5]|data[6]<<8)or 65536
            expected_calls=length+2
            require(returned==(17+6*length)*entry['clock_divisor']and extra==0,
                    'Original authored block duration differs')
        else:expected_calls=1
        require(calls==expected_calls,'Original opcode/continuation call count differs from authored operands')
        physical=tuple((mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191)for i in range(len(data)))
        source_hits[(pc,tuple(mapping),physical,tuple(data))]+=1
        if phase=='primer':require(not irq_events,'Masked software primer delivered IRQ')
        else:
            measured+=1;group=trace.instructions[ordinal-1];event=trace.events[ordinal-1]
            wanted=case['expected_gear'][ordinal-1]
            before_wanted=case['expected_initial_gear']if ordinal==1 else case['expected_gear'][ordinal-2]
            require(entry==event['entry']and after==event['state'],'Original call versus raw trace state differs')
            require(row['entry_values']==before_wanted['values']and row['values']==wanted['values'],
                    'Independent original before/after device literals differ')
            fixed=wanted['fixed_wait_count'];expected_internal=wanted['internal_clocked_ticks']
            require(extra==0 and internal==expected_internal==fixed*entry['clock_divisor'],
                    'Original measured fixed-wait/no-dynamic-stall domain differs')
            expected_spans=[entry['clock_divisor']]*fixed
            if returned>internal:expected_spans.append(returned-internal)
            require([span['requested']for span in spans]==expected_spans,'Original exact fixed-wait/drain callback partition differs')
            vector=irq_events[0]['vector']if irq_events else None
            require(len(irq_events)==wanted['irq_count']==group['irq_count']and
                    vector==wanted['irq_vector']==event['irq_vector']==group['irq_vector'],
                    'Original actual IRQ callback/delivery metadata differs')
            if irq_events:
                irq=irq_events[0]
                require(irq['cycle']==entry['ticks']+internal and irq['pc']==wanted['irq_return_pc']and
                        irq['mask']==row['values'][21],'Independent IRQ callback clock/return PC/mask differs')
            # Pin observed CD mask/reset access and ACK-driven clear clocks.
            # These are original aggregate scheduler callbacks, not physical
            # subcycle equality with the toolkit's synchronous port handler.
            counts=Counter(callback['event']for callback in cd_events)
            write_enable=data==[0x8D,2,0x18]
            write_reset=data==[0x8D,4,0x18]
            clear_expected=bool(write_enable and entry['a']&128 and
                row['entry_values'][31]&0x40 and row['entry_values'][29])
            require(counts[2]==int(write_enable)and counts[4]==int(write_reset)and
                    counts[1]==int(clear_expected),'Original required CD access/clear callback count differs')
            for callback in cd_events:
                kind=callback['event']
                if kind==2:
                    require(data==[0x8D,2,0x18]and callback['cycle']==entry['ticks']and
                            callback['irq_type']==entry['a']and callback['enabled']==entry['a']&127 and
                            callback['active']==row['entry_values'][29],'Original CD enable/ACK callback differs')
                elif kind==4:
                    require(data==[0x8D,4,0x18]and callback['cycle']==entry['ticks']and
                            callback['irq_type']==entry['a']&15 and callback['active']==row['entry_values'][29]&0x8F and
                            callback['enabled']==row['entry_values'][28],'Original CD reset callback differs')
                elif kind==1:
                    require(data==[0x8D,2,0x18]and entry['a']&128 and callback['cycle']==after['ticks']and
                            callback['irq_type']==row['entry_values'][29]and callback['active']==0 and
                            callback['enabled']==row['values'][28],'Original CD ACK-driven source-clear callback differs')
                elif kind not in(7,):
                    raise ValueError('Unexpected original CD event outside declared measured domain')
            checks+=39*2+len(spans)*3+len(events)*3+15
        previous_state,previous_values=after,row['values']
    require(dict(source_hits)==ledger(case['source_hits_gear']),'Original full fetched source/hit ledger differs')
    require(measured==case['steps']and previous_state==trace.final['state'],'Original journal closure differs')
    require(len(dma_start)==len(dma_end)==1 and dma_start[0]['param']==1 and
            dma_start[0]['cycle']<=dma_end[0]['cycle'],'One genuine authored VRAM DMA assertion required')
    require(len(commands)==1 and commands[0]['command']==0xDE and commands[0]['phase']==3 and
            commands[0]['data']==[0xDE]+[0]*9,
            'Actual complete authored directory CDB required')
    require(any(event['irq_type']&event['active']&case['cd_source']for event in cd_source_assertions),
            'Actual original CD source assertion callback required')
    return dict(checks=checks,actual_opcode_groups=len(rows),measured=measured,
                dma_start=1,dma_irq=1,complete_directory_commands=1,
                scope='Exact finite CPU/device literals, fetched identities, callback partition and selected IRQ/CD access clocks; other raw device events retained without physical bus-phase parity')


def build_gear(args, out, report, bindings, compiler, fixture):
    checkout, source = infrastructure.pinned_snapshot(args.gear_source.resolve(), out, bindings)
    report['gear_source_sha256'] = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    cpp, c = reference.compile_sources(checkout, source)
    cpp.append(ROOT/'tests/geargrafx_irq_device_probe.cpp')
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
    binary = out/('gear-irq-device.exe' if os.name=='nt' else 'gear-irq-device')
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
    lines = ['cmake_minimum_required(VERSION 3.20)', 'project(IRQDeviceProof LANGUAGES CXX)',
             *['set('+name+' OFF CACHE BOOL "" FORCE)' for name in
               ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
             f'add_subdirectory({quote(tool)} tool)',
             f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
             f'add_executable(irq-device-probe {quote(ROOT/"tests/irq_device_probe.cpp")})',
             f'target_include_directories(irq-device-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
             'target_link_libraries(irq-device-probe PRIVATE ${_module} pce-runtime)',
             'target_compile_definitions(irq-device-probe PRIVATE \"PCE_IRQ_DEVICE_CUE=\\\"'+quote(fixture/'authored.cue')[1:-1]+'\\\"\")']
    file = wrapper/'CMakeLists.txt'; file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)] = sha(file)
    build = out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja',
                     '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),
                     '-DCMAKE_MAKE_PROGRAM='+str(ninja)], 'tool-configure', out, report, bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','irq-device-probe','--parallel','2'],
                    'tool-build', out, report, bindings, 600)
    binary = build/('irq-device-probe.exe' if os.name=='nt' else 'irq-device-probe')
    bindings['tool_binary'] = {str(binary):sha(binary)}
    return binary


def qualify_comparison(case,comparison):
    """Only the declared legacy immediate-read profile may differ from Gear."""
    if case['queued_accesses']:
        require(comparison['equal'],'Unexpected Gear architectural retirement difference')
    else:
        # The independent literals qualify both full suffixes separately;
        # changing the exact first IRQ decision cannot become a generic pass.
        require(case['kind']=='vdc-immediate-cancel'and not comparison['equal']and
                comparison['first_difference']==dict(ordinal=2,field='irq_count',expected=0,actual=1),
                'Legacy immediate versus original Gear difference changed')


def run(args):
    tool=args.tool_source.resolve();out=args.out.resolve()
    compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    require(not out.exists()and out.is_relative_to(ROOT/'.local')and compiler.is_file(),
            'New private output and existing compiler required')
    sys.path.insert(0,str(tool))
    from pcerecomp import project,irq_trace
    from pcerecomp.capture import load_capture
    from generate_irq_device_fixture import generate,LITERAL_COLUMNS
    require(Path(project.__file__).resolve()==tool/'pcerecomp/project.py','Selected tool import required')
    paths=[Path(__file__),*[ROOT/'tests'/name for name in
        ('generate_irq_device_fixture.py','irq_device_probe.cpp','geargrafx_irq_device_probe.cpp',
         'irq_trace_support.hpp','reference_trace_support.hpp','reset_probe_support.hpp')],
        *[ROOT/'scripts'/name for name in
          ('irq_boundary_reference.py','beetle_reference.py','mapper_reference.py','hucard_reference.py','filtered_audio_reference.py')],
        tool/'CMakeLists.txt']
    for folder in('pcerecomp','runtime','cmake'):
        paths.extend(p for p in(tool/folder).rglob('*')if p.is_file()and
                     p.suffix in('.py','.cpp','.hpp','.h','.cmake')and '__pycache__'not in p.parts)
    paths=sorted(set(paths))
    bindings=dict(tools={str(compiler):sha(compiler)},authored_sources={str(p.resolve()):sha(p)for p in paths})
    report=dict(schema=1,result='incomplete',commands=[],bindings=bindings,
        scope='Guest-generated timer/VDC-DMA/CD sources, independent full CPU/WRAM/device literals and original Gear callbacks. '
              'Default queued profile compared to Gear; legacy immediate profile is an explicit negative comparison. '
              'No dynamic VRAM-stall, electrical bus-phase, independent Beetle-CD execution or hardware parity claim.')
    out.mkdir(parents=True);epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,path in enumerate(paths):
        saved=epoch/str(index)/path.name;saved.parent.mkdir();shutil.copyfile(path,saved)
        bindings['authored_epoch'][str(saved)]=sha(saved)
    try:
        fixture=out/'fixture';metadata=generate(fixture)
        require(metadata['schema']==1 and metadata['runtime_abi']==ABI and
                metadata['literal_columns']==LITERAL_COLUMNS and len(LITERAL_COLUMNS)==39,
                'Independent authored device fixture schema required')
        require(len(metadata['cases'])==44,'All declared device cases required')
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
            gear_ram=directory/'gear-wram.bin';journal=directory/'gear-journal.jsonl'
            result=common.evidence([str(gear),str(rom),str(cue),case['id'],str(gear_ram),str(journal)],
                                   'gear',directory,report,bindings)
            engine=dict(name='Geargrafx',revision=reference.COMMIT,
                source_sha256=report['gear_source_sha256'],binary_sha256=sha(gear))
            path,traces['gear']=previous.trace_file(directory,'gear',result.stdout,engine,rom,case['id'],'aggregate',[])
            bindings['raw_outputs'][str(path)]=sha(path)
            for tier in('native','interpreter'):
                capture=directory/(tier+'-capture.json');ram=directory/(tier+'-wram.bin')
                execution=directory/(tier+'-execution.json')
                result=common.evidence([str(binary),str(rom),str(cue),case['id'],tier,str(capture),str(ram),str(execution)],
                                       tier,directory,report,bindings)
                engine=dict(name='pcerecomp-'+tier,revision=identity['revision'],
                    source_sha256=identity['source_sha256'],binary_sha256=sha(binary))
                path,traces[tier]=previous.trace_file(directory,tier,result.stdout,engine,rom,case['id'],'aggregate',[])
                observed,digest=load_capture(capture);captures[tier]=observed
                from pcerecomp.reference_trace import _json
                require(execution.stat().st_size<=128*1024*1024,'Execution receipt exceeds protocol bound')
                work[tier]=_json(execution.read_bytes())
                bindings['raw_outputs'].update({str(path):sha(path),str(capture):digest,
                    str(ram):sha(ram),str(execution):sha(execution)})
                require(ram.stat().st_size==8192 and traces[tier].final['state']['wram_sha256']==sha(ram),
                        'Actual toolkit final WRAM differs')
            require(gear_ram.stat().st_size==8192 and traces['gear'].final['state']['wram_sha256']==sha(gear_ram),
                    'Actual original final WRAM differs')
            bindings['raw_outputs'].update({str(gear_ram):sha(gear_ram),str(journal):sha(journal)})
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
        report.update(result='pass-with-explicit-legacy-profile-differences',tool=identity,cases=cases,
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
