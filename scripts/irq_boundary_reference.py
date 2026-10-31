"""Authored unmasked IRQ boundaries against separately built original cores.

Raw engine calls are retained. Cross-engine comparison uses an explicitly
declared post-IRQ retirement boundary; interrupt entry is never an opcode.
Source-predicted disagreements must be qualified, never hidden by field masks.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import mapper_reference as infrastructure
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as reference
from scripts import beetle_reference as beetle
sha = reference.sha


def build_gear(args, out, report, bindings, compiler, fixture):
    checkout, source = infrastructure.pinned_snapshot(args.gear_source.resolve(), out, bindings)
    report['gear_source_sha256'] = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    cpp, c = reference.compile_sources(checkout, source)
    cpp.append(ROOT/'tests/geargrafx_irq_boundary_probe.cpp')
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
    binary = out/('gear-irq.exe' if os.name=='nt' else 'gear-irq')
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
    lines = ['cmake_minimum_required(VERSION 3.20)', 'project(IRQBoundaryProof LANGUAGES CXX)',
             *['set('+name+' OFF CACHE BOOL "" FORCE)' for name in
               ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
             f'add_subdirectory({quote(tool)} tool)',
             f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
             f'add_executable(irq-boundary-probe {quote(ROOT/"tests/irq_boundary_probe.cpp")})',
             f'target_include_directories(irq-boundary-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
             'target_link_libraries(irq-boundary-probe PRIVATE ${_module} pce-runtime)']
    file = wrapper/'CMakeLists.txt'; file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)] = sha(file)
    build = out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja',
                     '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),
                     '-DCMAKE_MAKE_PROGRAM='+str(ninja)], 'tool-configure', out, report, bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','irq-boundary-probe','--parallel','2'],
                    'tool-build', out, report, bindings, 600)
    binary = build/('irq-boundary-probe.exe' if os.name=='nt' else 'irq-boundary-probe')
    bindings['tool_binary'] = {str(binary):sha(binary)}
    return binary


def trace_file(out, label, body, engine, rom, case, model, unavailable):
    from pcerecomp import irq_trace
    header = dict(type='header',schema=2,format=irq_trace.FORMAT,engine=engine,
        fixture_sha256=sha(rom),case=case,clock='master-ticks',phase=irq_trace.PHASE,
        unavailable_fields=unavailable,call_model=model)
    path = out/(label+'-trace.jsonl')
    path.open('x',encoding='utf-8',newline='\n').write(json.dumps(header,separators=(',',':'))+'\n'+body)
    return path, irq_trace.load_trace(path)


def source_counts(capture, tier):
    fields = ('pc','mpr','physical','data')
    def key(row):
        return tuple(tuple(row[field]) if isinstance(row[field],list) else row[field] for field in fields)
    return {key(row):row['native_hits' if tier=='native' else 'interpreted_hits']
            for row in capture['observations']}


def run(args):
    tool, out = args.tool_source.resolve(), args.out.resolve()
    compiler = Path(shutil.which(str(args.compiler)) or '').resolve()
    if out.exists() or not out.is_relative_to(ROOT/'.local') or not compiler.is_file():
        raise ValueError('Require new private output and existing compiler')
    sys.path.insert(0,str(tool))
    from pcerecomp import project, irq_trace
    from pcerecomp.capture import load_capture
    from generate_irq_trace_fixture import generate
    if Path(project.__file__).resolve()!=tool/'pcerecomp/project.py':
        raise ValueError('Selected compiler/runtime import required')
    names = ('generate_irq_trace_fixture.py','irq_boundary_probe.cpp',
             'geargrafx_irq_boundary_probe.cpp','beetle_irq_probe.cpp',
             'irq_trace_support.hpp','reference_trace_support.hpp','reset_probe_support.hpp',
             'geargrafx_mapper_probe.cpp','beetle_cpu_probe.cpp','generate_speed_trace_fixture.py')
    paths = [Path(__file__), *[ROOT/'tests'/name for name in names],
             *[ROOT/'scripts'/name for name in ('beetle_reference.py','mapper_reference.py',
                 'hucard_reference.py','filtered_audio_reference.py')]]
    paths += [tool/'CMakeLists.txt'] + sorted((tool/'pcerecomp').glob('*.py'))
    paths += sorted((tool/'runtime').rglob('*.cpp'))+sorted((tool/'runtime').rglob('*.hpp'))
    paths += sorted((tool/'cmake').glob('*.cmake'))
    bindings = dict(tools={str(compiler):sha(compiler)},
                    authored_sources={str(p.resolve()):sha(p) for p in paths})
    report = dict(schema=1,result='incomplete',commands=[],bindings=bindings,
        scope='Actual original-core calls and explicit post-IRQ retirement groups; '
              'fixed comparison policies preserve raw epochs, full flags/mapping/WRAM and IRQ metadata. '
              'No hardware verdict or runtime-policy change inferred from reference disagreement.')
    out.mkdir(parents=True)
    epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,path in enumerate(paths):
        saved=epoch/str(index)/path.name;saved.parent.mkdir();shutil.copyfile(path,saved)
        bindings['authored_epoch'][str(saved)]=sha(saved)
    try:
        fixture=out/'fixture';generate(fixture)
        metadata=json.loads((fixture/'fixture.json').read_text())
        bindings['fixture']={str(p):sha(p) for p in fixture.iterdir() if p.is_file()}
        gear=build_gear(args,out,report,bindings,compiler,fixture)
        binary=build_tool(args,out,report,bindings,compiler,fixture)
        if args.reuse_beetle_build:
            build_path=args.reuse_beetle_build.resolve(strict=True);built=beetle.check_build(build_path)
            if not any(Path(row['path']).name=='beetle_irq_probe.cpp' and row['sha256']==sha(ROOT/'tests/beetle_irq_probe.cpp')
                       for row in built['authored']):
                raise ValueError('Reused build must contain the exact current IRQ observer')
        else:
            original=out/'beetle';original.mkdir()
            build_path,built=beetle.build(args,original,report['commands'],probe=ROOT/'tests/beetle_irq_probe.cpp')
        report['beetle_build']=beetle.binding(build_path)
        original_inputs=[built['binary'],*built['authored'],*built['build_inputs'],*built['tools'],beetle.binding(build_path)]
        for row in built['files'].values():original_inputs.extend((row['original'],row['compiled']))
        bindings['beetle_original_build']={row['path']:row['sha256']for row in original_inputs}
        identity=project.source_identity(tool);cases=[]
        for case in metadata['cases']:
            if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',case['id']):
                raise ValueError('Safe authored case label required')
            rom=(fixture/case['rom']).resolve(strict=True)
            if not rom.is_relative_to(fixture.resolve()) or rom.stat().st_size!=262144:
                raise ValueError('Bound authored ROM required')
            directory=out/case['id'];directory.mkdir()
            traces,captures,work={},{},{}
            gear_ram=directory/'gear-wram.bin';gear_journal=directory/'gear-irqs.jsonl'
            result=common.evidence([str(gear),str(rom),case['id'],str(gear_ram),str(gear_journal)],
                                   'gear',directory,report,bindings)
            engine=dict(name='Geargrafx',revision=reference.COMMIT,
                source_sha256=report['gear_source_sha256'],binary_sha256=sha(gear))
            path,traces['gear']=trace_file(directory,'gear',result.stdout,engine,rom,case['id'],'aggregate',[])
            bindings.setdefault('raw_outputs',{})[str(path)]=sha(path)
            for tier in ('interpreter','native'):
                capture=directory/(tier+'-capture.json');ram=directory/(tier+'-wram.bin')
                execution=directory/(tier+'-execution.json')
                result=common.evidence([str(binary),str(rom),case['id'],tier,str(capture),str(ram),str(execution)],
                    tier,directory,report,bindings)
                engine=dict(name='pcerecomp-'+tier,revision=identity['revision'],
                    source_sha256=identity['source_sha256'],binary_sha256=sha(binary))
                path,traces[tier]=trace_file(directory,tier,result.stdout,engine,rom,case['id'],'aggregate',[])
                bindings['raw_outputs'][str(path)]=sha(path)
                observed,digest=load_capture(capture);bindings.setdefault('raw_outputs',{})[str(capture)]=digest
                captures[tier]=observed;work[tier]=json.loads(execution.read_text())
                bindings['raw_outputs'].update({str(ram):sha(ram),str(execution):sha(execution)})
                if ram.stat().st_size!=8192 or traces[tier].final['state']['wram_sha256']!=sha(ram):
                    raise ValueError('Actual final toolkit WRAM differs')
            internal=irq_trace.compare_traces(traces['native'],traces['interpreter'],view='raw-event-exact')
            if not internal['equal'] or source_counts(captures['native'],'native')!=source_counts(captures['interpreter'],'interpreter'):
                raise ValueError('Actual native/interpreter event or full source-hit mismatch')
            beetle_ram=directory/'beetle-wram.bin';journal=directory/'beetle-calls.jsonl'
            result=common.evidence([built['binary']['path'],str(rom),str(case['steps']),str(case['primer_steps']),
                    str(beetle_ram),str(journal)],'beetle',directory,report,bindings)
            engine=dict(name='beetle-pce',revision=beetle.PIN,
                source_sha256=built['source_sha256'],binary_sha256=built['binary']['sha256'])
            path,traces['beetle']=trace_file(directory,'beetle',result.stdout,engine,rom,case['id'],'split-irq',['mpr_latch'])
            bindings['raw_outputs'][str(path)]=sha(path)
            if beetle_ram.stat().st_size!=8192 or traces['beetle'].final['state']['wram_sha256']!=sha(beetle_ram):
                raise ValueError('Independent original final WRAM differs')
            bindings['raw_outputs'].update({str(beetle_ram):sha(beetle_ram),str(journal):sha(journal),
                                            str(gear_ram):sha(gear_ram),str(gear_journal):sha(gear_journal)})
            # Qualification remains fail-closed until the authored fixture's
            # independent scalar/path contract has been checked for all cores.
            literals=qualify_case(case,traces,captures,work,journal)
            literals['gear_journal_checks']=qualify_gear_journal(gear_journal,traces['gear'],case)
            comparisons={}
            for name in ('gear','beetle'):
                comparisons[name]={profile:irq_trace.compare_traces(traces['native'],traces[name],profile=profile)
                    for profile in ('architectural-v1','architectural-elapsed-v1')}
            qualify_comparisons(case,comparisons)
            cases.append(dict(id=case['id'],literal_checks=literals,execution=work,
                native_interpreter=internal,comparisons=comparisons,
                trace_hashes={name:trace.sha256 for name,trace in traces.items()},
                raw_events={name:len(trace.events) for name,trace in traces.items()},
                actual_instructions={name:len(trace.instructions) for name,trace in traces.items()},
                observed_differences={name:all_differences(traces['native'],traces[name])
                                      for name in('gear','beetle')}))
        accounting=accounting_edges(metadata,fixture,built,out,report,bindings)
        legacy=legacy_default_check(args,metadata,fixture,out,report,bindings)
        beetle.check_build(build_path)
        report.update(result='pass-with-explicit-reference-disagreements',tool=identity,cases=cases,
                      original_accounting_edges=accounting,legacy_v1=legacy)
    except Exception as error:
        report.update(result='fail',error=repr(error));raise
    finally:
        reference.record_preservation(report,bindings)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['result']=='failed-preservation':raise ValueError('Bound inputs changed during qualification')
    print(json.dumps({key:value for key,value in report.items() if key not in ('commands','bindings','cases')},indent=2))


def qualify_case(case,traces,captures,work,journal):
    checks=0
    def require(value,label):
        nonlocal checks
        if not value:raise ValueError(case['id']+': '+label)
        checks+=1
    for name,profile in (('native','runtime'),('interpreter','runtime'),('gear','gear')):
        trace=traces[name];expected=case['expected_'+profile]
        require(len(trace.instructions)==case['steps']==len(expected),'exact measured extent')
        for actual,literal in [(dict(state=trace.initial,irq_count=0,irq_vector=None),
                                case['expected_initial_'+profile]),*zip(trace.instructions,expected)]:
            for field,value in literal['state'].items():
                observed=actual['state'][field]
                if field=='ticks':observed-=trace.initial['ticks']
                require(type(observed)is type(value) and observed==value,
                        name+' literal state '+field+' at '+str(literal['ordinal']))
            for field in ('irq_count','irq_vector'):
                require(actual[field]==literal[field],name+' literal '+field)
    expected_sources={}
    for row in case['source_hits']:
        key=(row['pc'],tuple(row['mpr']),tuple(row['physical']),tuple(row['data']))
        require(key not in expected_sources,'independent source identity unique')
        expected_sources[key]=row['hits']
    total=case['primer_steps']+case['steps']
    require(sum(expected_sources.values())==total,'authored source ledger extent')
    for tier in ('native','interpreter'):
        capture=captures[tier]
        require(capture['runtime_abi']==ABI and capture['complete']is True and
                capture['retired_instructions']==total and not capture['dropped_instructions'] and
                not capture['unreadable_instructions'],'complete actual native work')
        require(source_counts(capture,tier)==expected_sources,'independent full PC/MPR/physical/byte hit ledger')
        other='interpreted_hits'if tier=='native'else'native_hits'
        require(all(row[other]==0 for row in capture['observations']),'actual selected tier only')
        require(len(traces[tier].events)==case['steps'],'aggregate calls are actual opcodes')
        evidence=work[tier]
        fields={'schema','case','tier','primer_steps','measured_steps','native_steps',
                'interpreter_steps','block_steps','pure_guards','raw_initial_ticks','literal_rows'}
        require(type(evidence)is dict and set(evidence)==fields,'strict actual execution receipt')
        expected=dict(schema=1,case=case['id'],tier=tier,primer_steps=case['primer_steps'],
            measured_steps=case['steps'],native_steps=total if tier=='native'else 0,
            interpreter_steps=total if tier=='interpreter'else 0,block_steps=1,
            pure_guards=4 if tier=='native'else 0,raw_initial_ticks=traces[tier].initial['ticks'])
        for field,value in expected.items():
            require(type(evidence[field])is type(value)and evidence[field]==value,'actual execution '+field)
        require(type(evidence['literal_rows'])is list and len(evidence['literal_rows'])==case['steps'],
                'actual device literal extent')
        for row,literal in zip(evidence['literal_rows'],case['expected_runtime']):
            require(type(row)is list and len(row)==26,'complete device row')
            for actual,value in zip(row,literal['values']):
                require(type(actual)is int and actual==value,'independent device literal')
    # The original has no corresponding transfer latch. No other field is
    # removed from the positive prefix before an explicit disagreement.
    known=case['known_beetle_difference']
    prefix=case['steps'] if known is None else known['ordinal']-1
    original=traces['beetle'];require(len(original.instructions)==case['steps'],'original actual opcode count')
    for index,(actual,literal)in enumerate(zip([dict(state=original.initial),*original.instructions],
                                            [case['expected_initial_runtime'],*case['expected_runtime']])):
        if index>prefix:break
        for field,value in literal['state'].items():
            if field=='mpr_latch':continue
            observed=actual['state'][field]
            if field=='ticks':observed-=original.initial['ticks']
            require(type(observed)is type(value)and observed==value,'original literal prefix '+field)
    checkpoint=None
    if known is not None:
        ordinal,field=known['ordinal'],known['field']
        expected=case['expected_runtime'][ordinal-1]['state'][field]
        actual=original.instructions[ordinal-1]['state'][field]
        require(type(actual)is int and actual==known['value'] and actual!=expected,
                'declared original state disagreement must match independent source value')
        checkpoint=dict(ordinal=ordinal,field=field,runtime=expected,beetle=actual,reason=known['reason'])
    journal_checks=qualify_journal(journal,original,case['primer_steps'])
    return dict(scalar_checks=checks,journal_checks=journal_checks,
                beetle_literal_prefix=prefix,actual_tool_retirements_per_tier=total,
                actual_declared_beetle_disagreement=checkpoint)


def qualify_comparisons(case,comparisons):
    # Both aggregate engines have already passed every authored state/IRQ
    # literal. Their only admitted differences are the declared speed-cycle
    # totals, with every actual raw clock retained in the comparison reports.
    gear=case['expected_gear'];runtime=case['expected_runtime']
    timing=[]
    for index,(left,right)in enumerate(zip(runtime,gear),1):
        for field in left['state']:
            if field!='ticks' and left['state'][field]!=right['state'][field]:
                raise ValueError('Authored Gear architectural disagreement requires separate scope')
        if left['state']['ticks']!=right['state']['ticks']:timing.append(index)
    actual=comparisons['gear']['architectural-elapsed-v1']
    if not timing:
        if not actual['equal']:raise ValueError('Unexpected Gear retirement-boundary difference')
    else:
        difference=actual['first_difference']
        if actual['equal'] or difference['ordinal']!=timing[0] or difference['field']!='state.ticks':
            raise ValueError('Gear clock difference differs from independent literal profile')
    beetle_result=comparisons['beetle']['architectural-elapsed-v1']
    known=case['known_beetle_difference']
    if known is None:
        if not beetle_result['equal']:raise ValueError('Unexpected original Beetle retirement-boundary difference')
    else:
        wanted=dict(ordinal=known['ordinal'],field=known['first_field'],
                    expected=known['first_expected'],actual=known['first_actual'])
        if beetle_result['equal']or beetle_result['first_difference']!=wanted:
            raise ValueError('Original Beetle first divergent retirement differs from declared source vector')


def qualify_journal(path,trace,primer_steps):
    """Check original call decisions from pinned pipeline fields, never PC/SP heuristics."""
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate original call journal key')
            result[key]=value
        return result
    raw=Path(path).read_bytes()
    if len(raw)>64*1024*1024:raise ValueError('Original call journal bound')
    rows=[json.loads(line,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite original journal')))
        for line in raw.splitlines()]
    if len(rows)<2 or type(rows[0])is not dict or type(rows[0].get('schema'))is not int or rows[0]!=dict(type='header',schema=1,format='pce-beetle-call-journal-1',
                     decision='original-runsub-irq-pipeline-v1'):
        raise ValueError('Actual original decision journal header required')
    fields={'irq_sample','irq_low','irq_enabled_mask','i_flag_sample','pi_mask_cache',
            'in_block_move','runrunrun','overclock','emulate_wai','raw_pc','p','ticks'}
    calls=rows[1:-1];measured=[];last=None;checks=0
    def select(p):
        if p['overclock']!=1 or p['emulate_wai']or not 0<=p['irq_enabled_mask']<=7:
            raise ValueError('Unsupported original pipeline domain')
        if p['in_block_move']:
            if not 1<=p['in_block_move']<=5:raise ValueError('Unknown original block continuation')
            return 'block-continuation',None
        if p['irq_sample']|p['irq_low']:
            # Original HuC6280::IQRESET is 0x020 (not a guest IRQ bit).
            if p['irq_sample']&0x20:return 'reset',None
            if p['irq_low']&4&p['irq_enabled_mask'] and not p['i_flag_sample']:return 'irq-entry',0xFFFA
            if p['irq_sample']&2:return 'irq-entry',0xFFF8
            if p['irq_sample']&1:return 'irq-entry',0xFFF6
        return 'opcode',None
    phase_rank={'reset':0,'primer':1,'measured':2};rank=-1
    opcodes={'primer':0,'measured':0};resets=0
    for ordinal,row in enumerate(calls,1):
        if type(row)is not dict or set(row)!={'type','ordinal','phase','opcode_ordinal','kind','irq_vector','entry','state'} or row['type']!='call' or type(row['ordinal'])is not int or row['ordinal']!=ordinal:
            raise ValueError('Strict original call record required')
        if row['phase']not in('reset','primer','measured')or type(row['opcode_ordinal'])is not int:
            raise ValueError('Original call phase/attachment required')
        if phase_rank[row['phase']]<rank:raise ValueError('Original call phases out of order')
        rank=phase_rank[row['phase']]
        for state in(row['entry'],row['state']):
            if type(state)is not dict or set(state)!=fields:raise ValueError('Complete original IRQ pipeline required')
            for key,value in state.items():
                if type(value)is not(bool if key=='emulate_wai'else int):raise ValueError('Typed original pipeline required')
                if key!='emulate_wai':
                    low,high=(-2147483648,2147483647)if key in('irq_sample','i_flag_sample','runrunrun')else(0,4294967295)
                    if not low<=value<=high:raise ValueError('Original pipeline integer outside field width')
            if state['i_flag_sample']not in(0,4):raise ValueError('Original sampled-I domain')
            if state['p']>255:raise ValueError('Original status outside byte range')
        if last is not None and row['entry']!=last:raise ValueError('Original call pipeline chain differs')
        if select(row['entry'])!=(row['kind'],row['irq_vector']):raise ValueError('Original call mislabeled versus original branch inputs')
        if row['phase']=='reset':
            resets+=1
            if ordinal!=1 or row['kind']!='reset' or row['opcode_ordinal']!=0:
                raise ValueError('Initial reset must remain separate from opcode retirement')
        else:
            if row['kind']=='reset':raise ValueError('Reset cannot become an opcode retirement')
            if row['kind']=='opcode':opcodes[row['phase']]+=1
            if row['opcode_ordinal']!=opcodes[row['phase']] or row['opcode_ordinal']<1:
                raise ValueError('Original call attachment is not the actual opcode ordinal')
        if row['kind']!='reset'and row['state']['ticks']<=row['entry']['ticks']:
            raise ValueError('Original call failed to progress')
        if row['phase']=='measured':measured.append(row)
        last=row['state'];checks+=len(fields)*2+5
    final=rows[-1]
    if not isinstance(final,dict)or set(final)!={'type','calls','measured_instructions','primer_instructions','measured_events','complete'}:
        raise ValueError('Strict original journal final required')
    if any(type(final[key])is not int for key in('calls','measured_instructions','primer_instructions','measured_events'))or type(final['complete'])is not bool:
        raise ValueError('Typed original journal final required')
    if resets!=1 or opcodes!={'primer':primer_steps,'measured':len(trace.instructions)}:
        raise ValueError('Original reset/primer/measured opcode counts differ')
    if final!=dict(type='final',calls=len(calls),measured_instructions=len(trace.instructions),
                   primer_instructions=primer_steps,measured_events=len(trace.events),complete=True):
        raise ValueError('Original call journal closure differs')
    if len(measured)!=len(trace.events):raise ValueError('Original measured calls/events differ')
    if last is None or select(last)!=('opcode',None):
        raise ValueError('Original final retirement boundary omitted pending entry or continuation')
    for row,event in zip(measured,trace.events):
        if row['kind']!=event['kind']or row['irq_vector']!=event['irq_vector']:
            raise ValueError('Actual original event differs from call journal')
        for field,state_name in(('entry','entry'),('state','state')):
            state=row[state_name];actual=event[field]
            if (actual['pc'],actual['p'],actual['ticks'])!=(state['raw_pc']&65535,state['p'],state['ticks']):
                raise ValueError('Actual original state differs from pipeline observation')
        group=next((g for g in trace.instructions if g['event_start']<=event['ordinal']<=g['event_end']),None)
        if group is None or row['opcode_ordinal']!=group['ordinal']:
            raise ValueError('Original call attached to wrong actual opcode')
        checks+=8
    return checks


def qualify_gear_journal(path,trace,case):
    """Bind original TraceLogger CPU/IRQ records to actual aggregate calls."""
    from pcerecomp import reference_trace as v1
    raw=Path(path).read_bytes()
    if len(raw)>64*1024*1024:raise ValueError('Original Gear journal bound')
    rows=[v1._json(line)for line in raw.splitlines()]
    if len(rows)!=case['primer_steps']+case['steps']:raise ValueError('Original Gear journal extent')
    ledger=Counter();measured=[];last=None;checks=0
    for index,row in enumerate(rows):
        if type(row)is not dict or set(row)!={'phase','ordinal','original_calls','entry','original_trace','state'}:
            raise ValueError('Strict original Gear call-group record required')
        phase='primer'if index<case['primer_steps']else'measured'
        ordinal=index+1 if phase=='primer'else index-case['primer_steps']+1
        if row['phase']!=phase or type(row['ordinal'])is not int or row['ordinal']!=ordinal:
            raise ValueError('Original Gear phase/ordinal differs')
        if type(row['original_calls'])is not int or not 1<=row['original_calls']<=65538:
            raise ValueError('Original Gear continuation count')
        if phase=='measured'and row['original_calls']!=1:
            raise ValueError('Measured aggregate model requires one actual call')
        for field in('entry','state'):v1._state(row[field],[])
        if last is not None and row['entry']!=last:raise ValueError('Original Gear call chain differs')
        if row['state']['ticks']<=row['entry']['ticks']:raise ValueError('Original Gear call did not progress')
        last=row['state'];events=row['original_trace']
        if type(events)is not list or not events or len(events)>2 or events[0].get('type')!='cpu':
            raise ValueError('Actual original CPU/IRQ trace records required')
        opcode=events[0]
        if set(opcode)!={'type','pc','bank','bytes'}or type(opcode['pc'])is not int or type(opcode['bank'])is not int or type(opcode['bytes'])is not list or not 1<=len(opcode['bytes'])<=7:
            raise ValueError('Strict original fetched CPU source record required')
        if any(type(value)is not int or not 0<=value<=255 for value in opcode['bytes']):
            raise ValueError('Original fetched bytes must be unsigned bytes')
        state=row['entry'];pc=state['pc'];mapping=state['mpr']
        if opcode['pc']!=pc or opcode['bank']!=mapping[pc>>13]:raise ValueError('Original CPU source mapping differs')
        physical=tuple((mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191)for i in range(len(opcode['bytes'])))
        ledger[(pc,tuple(mapping),physical,tuple(opcode['bytes']))]+=1
        vector=None
        if len(events)==2:
            irq=events[1]
            if type(irq)is not dict or set(irq)!={'type','cycle','pc','vector'}or irq['type']!='TRACE_CPU_IRQ':
                raise ValueError('Actual original hardware IRQ record required')
            if any(type(irq[field])is not int for field in('cycle','pc','vector'))or irq['vector']not in(0xFFF6,0xFFF8,0xFFFA):
                raise ValueError('Strict original IRQ metadata required')
            # This authored suite has only aggregate NOP/SEI/SET/STA-IDR,
            # BRK and speed-change instructions at delivery. None clocks
            # hardware before HandleIRQ logs; the wrapper clocks remaining
            # cycles afterwards. This is NOT a general MMIO/bus-phase rule.
            if phase!='measured' or opcode['bytes'][0]not in(0xEA,0x78,0xF4,0x8D,0x00,0x54,0xD4):
                raise ValueError('Original IRQ callback outside authored timing domain')
            if opcode['bytes'][0]==0x8D and opcode['bytes']!=[0x8D,2,0x14]:
                raise ValueError('Only authored timer-mask STA has callback timing qualification')
            from generate_irq_trace_fixture import BRK_HANDLER
            return_pc=BRK_HANDLER if opcode['bytes'][0]==0 else (pc+len(opcode['bytes']))&65535
            if irq['cycle']!=state['ticks']or irq['pc']!=return_pc:
                raise ValueError('Original IRQ callback timestamp/return PC differs from authored source contract')
            vector=irq['vector']
        if phase=='measured':
            event=trace.events[ordinal-1]
            if event['entry']!=row['entry']or event['state']!=row['state']or event['irq_vector']!=vector:
                raise ValueError('Actual original event differs from original CPU/IRQ journal')
            measured.append(row)
        checks+=len(opcode['bytes'])+15
    expected={(row['pc'],tuple(row['mpr']),tuple(row['physical']),tuple(row['data'])):row['hits']
              for row in case['source_hits']}
    if dict(ledger)!=expected:raise ValueError('Original fetched source/hits differ from independent software ledger')
    if len(measured)!=len(trace.events):raise ValueError('Original measured call count differs')
    return checks


def all_differences(native,other):
    """Enumerate actual architectural differences after the first divergence too."""
    rows=[]
    for ordinal,(left,right)in enumerate(zip([native.initial,*[g['state']for g in native.instructions]],
                                            [other.initial,*[g['state']for g in other.instructions]])):
        for field in left:
            if field=='mpr_latch':continue
            if left[field]!=right[field]:
                row=dict(ordinal=ordinal,field='state.'+field,native=left[field],reference=right[field])
                if field=='ticks':
                    row.update(native_elapsed=left[field]-native.initial['ticks'],
                               reference_elapsed=right[field]-other.initial['ticks'])
                rows.append(row)
        if ordinal:
            for field in('irq_count','irq_vector'):
                a,b=native.instructions[ordinal-1][field],other.instructions[ordinal-1][field]
                if a!=b:rows.append(dict(ordinal=ordinal,field=field,native=a,reference=b))
    return dict(unchecked=['mpr_latch'],records=rows)


def bind_original_manifest(manifest,bindings,label):
    rows=[manifest['binary'],*manifest['authored'],*manifest['build_inputs'],*manifest['tools']]
    for row in manifest['files'].values():rows.extend((row['original'],row['compiled']))
    bindings[label]={row['path']:row['sha256']for row in rows}


def accounting_edges(metadata,fixture,built,out,report,bindings):
    """Actual final-IRQ drain and real BMT continuation counts, not synthetic rows."""
    from pcerecomp import irq_trace
    case=next(c for c in metadata['cases']if c['id']=='timer-cli-low')
    rom=fixture/case['rom'];results=[]
    for label,steps,primer in(('last-opcode-IRQ',2,case['primer_steps']),('measured-TII-continuations',1,7)):
        directory=out/label;directory.mkdir();ram=directory/'wram.bin';journal=directory/'calls.jsonl'
        actual=common.evidence([built['binary']['path'],str(rom),str(steps),str(primer),str(ram),str(journal)],
                              'probe',directory,report,bindings)
        engine=dict(name='beetle-pce',revision=beetle.PIN,source_sha256=built['source_sha256'],
                    binary_sha256=built['binary']['sha256'])
        path,trace=trace_file(directory,'beetle',actual.stdout,engine,rom,label,'split-irq',['mpr_latch'])
        bindings.setdefault('raw_outputs',{})[str(path)]=sha(path)
        if len(trace.instructions)!=steps or ram.stat().st_size!=8192 or sha(ram)!=trace.final['state']['wram_sha256']:
            raise ValueError('Actual accounting edge extent/final WRAM differs')
        journal_checks=qualify_journal(journal,trace,primer)
        kinds=[event['kind']for event in trace.events]
        if label=='last-opcode-IRQ':
            if kinds!=['opcode','opcode','irq-entry']or trace.instructions[-1]['irq_vector']!=0xFFFA:
                raise ValueError('Last requested opcode did not retain exactly its IRQ-only call')
            expected=case['expected_runtime'][1]['state']
            for field,value in expected.items():
                if field=='mpr_latch':continue
                observed=trace.final['state'][field]
                if field=='ticks':observed-=trace.initial['ticks']
                if type(observed)is not type(value)or observed!=value:raise ValueError('Final IRQ edge literal '+field)
        else:
            # Actual software prefix ends just before original TII. The source
            # overlaps by one byte, so the first guest zero fills all8192 WRAM.
            if kinds!=['opcode','block-continuation','block-continuation','block-continuation']:
                raise ValueError('Actual original TII continuation accounting differs')
            if trace.final['state']['ticks']-trace.initial['ticks']!=(17+6*8191)*12:
                raise ValueError('Original full TII literal master duration differs')
            if trace.final['state']['wram_sha256']!=hashlib.sha256(bytes(8192)).hexdigest():
                raise ValueError('Original TII software WRAM clear differs')
        bindings.setdefault('raw_outputs',{}).update({str(ram):sha(ram),str(journal):sha(journal)})
        results.append(dict(id=label,instructions=steps,raw_events=len(trace.events),kinds=kinds,
            initial=trace.initial,final=trace.final,journal_checks=journal_checks,
            scope='Original observer accounting edge; not an extra game/native coverage claim'))
    return results


def legacy_default_check(args,metadata,fixture,out,report,bindings):
    """Freshly compile the unchanged default v1 observer and keep its I guard."""
    from pcerecomp.reference_trace import load_trace
    from generate_speed_trace_fixture import generate,PRIMER_STEPS,STEPS,expected_rows
    legacy=out/'legacy-v1';legacy.mkdir()
    build_path,built=beetle.build(args,legacy,report['commands'])
    bind_original_manifest(built,bindings,'legacy_original_build')
    bindings['legacy_original_build'][str(build_path)]=sha(build_path)
    fixture_dir=legacy/'fixture';generate(fixture_dir,emit_module=False)
    rom=fixture_dir/'authored.pce';ram=legacy/'final-wram.bin'
    bindings['legacy_fixture']={str(p):sha(p)for p in fixture_dir.iterdir()if p.is_file()}
    actual=common.evidence([built['binary']['path'],str(rom),str(STEPS),str(PRIMER_STEPS),str(ram)],
                          'positive',legacy,report,bindings)
    header=dict(type='header',schema=1,format='pce-cpu-trace-1',
        engine=dict(name='beetle-pce',revision=beetle.PIN,source_sha256=built['source_sha256'],
                    binary_sha256=built['binary']['sha256']),fixture_sha256=sha(rom),
        case='legacy-masked-observer-regression',clock='master-ticks',phase='instruction-boundary',
        unavailable_fields=['mpr_latch'])
    trace_path=legacy/'trace.jsonl';trace_path.write_text(json.dumps(header)+'\n'+actual.stdout,encoding='utf-8')
    trace=load_trace(trace_path)
    if trace.final['executed']!=STEPS or ram.stat().st_size!=8192 or sha(ram)!=trace.instructions[-1]['state']['wram_sha256']:
        raise ValueError('Legacy original observer failed actual v1 closure')
    for row,wanted in zip(trace.instructions,expected_rows('runtime')):
        state=row['state']
        actual_values=[state[k]for k in('pc','a','x','y','sp','p','clock_divisor')]
        actual_values.append(state['ticks']-trace.initial['ticks'])
        if actual_values!=wanted[:8]:raise ValueError('Legacy original masked CPU/clock literals differ')
    # The unchanged default observer must still stop BEFORE an unmasked next
    # opcode. The new accounting domain is opt-in, never a v1 relabeling.
    case=next(c for c in metadata['cases']if c['id']=='timer-cli-low')
    negative_rom=fixture/case['rom'];negative_ram=legacy/'must-not-exist-wram.bin'
    command=[built['binary']['path'],str(negative_rom),'2',str(case['primer_steps']),str(negative_ram)]
    report['commands'].append(command);failed=subprocess.run(command,capture_output=True,text=True,timeout=60)
    stdout=legacy/'negative.stdout';stderr=legacy/'negative.stderr'
    stdout.write_text(failed.stdout);stderr.write_text(failed.stderr)
    rows=[json.loads(line)for line in failed.stdout.splitlines()]
    if failed.returncode!=1 or 'CPU-I-unmasked instruction stepping unsupported'not in failed.stderr or negative_ram.exists():
        raise ValueError('Legacy masked observer silently accepted unmasked accounting')
    if [row['type']for row in rows]!=['initial','instruction']or rows[1]['ordinal']!=1:
        raise ValueError('Legacy refusal invented extra retirement or completion')
    bindings.setdefault('raw_outputs',{}).update({str(ram):sha(ram),str(trace_path):sha(trace_path),
                                                str(stdout):sha(stdout),str(stderr):sha(stderr)})
    beetle.check_build(build_path)
    return dict(build=beetle.binding(build_path),measured_instructions=STEPS,primer_instructions=PRIMER_STEPS,
        old_unmasked_guard_exit=failed.returncode,actual_retirements_before_guard=1,
        no_negative_wram_export=True,scope='Fresh default original observer preserves v1 and its refusal boundary')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True)
    parser.add_argument('--beetle-source',type=Path,required=True)
    parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compiler',default='clang++')
    parser.add_argument('--cmake',default='cmake');parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    parser.add_argument('--reuse-beetle-build',type=Path)
    try:run(parser.parse_args())
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError) as error:
        print(error,file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()
