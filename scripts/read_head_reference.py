"""Authored READ-to-idle-Q checks against the complete unchanged Gear core.

Gear executes its original transport/media code through register operations.
The toolkit executes real statically translated or interpreted port opcodes,
with explicitly host-supervised PC/A selection and clock waits. This qualifies
payload/head/handshake outcomes, not cross-core CPU retirement or seek timing.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import mapper_reference as infrastructure
from scripts import filtered_audio_reference as reference
from scripts import hucard_reference as common
from scripts.cue_reference import difference
sha=reference.sha


def pattern(lba):
    return [(lba*29+offset*17+(offset>>8)*7+0x53)&255 for offset in range(2048)]


def command(op,automatic,lba=0,count=1,start=False):
    cdb=[8,(lba>>16)&31,(lba>>8)&255,lba&255,count,0] if op==8 else [0xDD]+[0]*9
    return ('s' if start else 'c',automatic,len(cdb),*cdb)


def plans(mixed,automatic):
    cases=[dict(id='single-sector-idle-Q',operations=[('r',),('h',),command(8,automatic,2),('h',),command(0xDD,automatic),('h',)]),
           dict(id='multiple-sectors-idle-Q',operations=[('r',),command(8,automatic,0,3),('h',),command(0xDD,automatic)]),
           dict(id='pending-buffer-does-not-advance-head',operations=[('r',),command(8,automatic,0,2,True),('h',),('w',),('h',),('a',300000),('h',),('d',),('h',),command(0xDD,automatic)]),
           dict(id='last-data-sector-next-position',operations=[('r',),command(8,automatic,3),('h',),command(0xDD,automatic)]),
           dict(id='failed-second-sector-retains-head',operations=[('r',),command(8,automatic,3,2),('h',),command(0xDD,automatic)])]
    # Gear permits cooked READ bytes from an AUDIO CUE track; this toolkit
    # explicitly refuses them. Keep that separate media-policy discrepancy out
    # of this shared head proof. The data-only medium covers real read failure.
    return cases[:-1] if mixed else cases


def q_response(head,mixed):
    track=2 if mixed and head>=4 else 1
    relative=head-(4 if track==2 else 0)
    def bcd(value):return value//10*16+value%10
    def msf(value):return [bcd(value//4500),bcd(value//75%60),bcd(value%75)]
    return [1,1 if track==2 else 0x41,track,1,*msf(relative),*msf(head+150)]


def expected(cases,mixed):
    rows=[];head=0;active=None;leadout=7 if mixed else 4
    def complete(raw,automatic):
        nonlocal head
        payload=[];status=0
        if raw[0]==8:
            lba=((raw[1]&31)<<16)|(raw[2]<<8)|raw[3]
            for address in range(lba,lba+(raw[4] or 256)):
                if address>=4:
                    status=2;break
                payload.extend(pattern(address));head=min(address+1,leadout-1)
        elif raw[0]==0xDD:payload=q_response(head,mixed)
        else:raise ValueError('Unauthored command')
        return dict(kind='reply',automatic=automatic,cdb=list(raw),data=payload,status=status,message=status)
    for case in cases:
        for op in case['operations']:
            if op[0]=='r':head=0;active=None
            elif op[0]=='h':rows.append(dict(kind='head',values=[head]))
            elif op[0] in ('c','s'):
                _,automatic,count,*raw=op
                if len(raw)!=count:raise ValueError('Authored CDB extent')
                if op[0]=='c':rows.append(complete(raw,automatic))
                else:active=(raw,automatic)
            elif op[0]=='w':
                if active is None or active[0][0]!=8:raise ValueError('Authored pending READ required')
                raw=active[0];lba=((raw[1]&31)<<16)|(raw[2]<<8)|raw[3]
                head=min(lba+1,leadout-1)
            elif op[0]=='a':pass  # The single unread buffer holds the head.
            elif op[0]=='d':
                if active is None:raise ValueError('Authored active command required')
                rows.append(complete(*active));active=None
            else:raise ValueError('Unauthored plan operation')
    return rows


def validate_rows(actual,wanted):
    mismatch=difference(actual,wanted)
    if mismatch:raise ValueError('READ head response differs: '+json.dumps(mismatch,sort_keys=True))
    return sum(len(row['data'])+2 if row['kind']=='reply' else len(row['values']) for row in wanted)


def serialize(cases):
    return '\n'.join(' '.join(map(str,op)) for case in cases for op in case['operations'])+'\n'


def fixtures(out):
    rom=out/'authored.pce';image=bytearray([0xEA]*262144);image[8190:8192]=bytes((0,0xE0));rom.write_bytes(image)
    data=out/'data.bin';data.write_bytes(b''.join(bytes(pattern(lba)) for lba in range(4)))
    audio=out/'audio.bin';audio.write_bytes(bytes(3*2352))
    result={}
    for mixed in (False,True):
        path=out/('mixed.cue' if mixed else 'data.cue')
        path.write_text('FILE "data.bin" BINARY\n TRACK 01 MODE1/2048\n INDEX 01 00:00:00\n'+
                        ('FILE "audio.bin" BINARY\n TRACK 02 AUDIO\n INDEX 01 00:00:00\n' if mixed else ''),encoding='ascii')
        result[mixed]=path
    return rom,result


def build_gear(args,out,report,bindings,compiler):
    source,hashes=infrastructure.pinned_snapshot(args.gear_source.resolve(),out,bindings)
    cpp,c=reference.compile_sources(source,hashes);cpp.append(ROOT/'tests/geargrafx_read_head_probe.cpp')
    deps=source/'platforms/shared/dependencies'
    flags=['-O2','-ffp-contract=off','-ffunction-sections','-fdata-sections','-DGG_DISABLE_DISASSEMBLER','-DGG_DISABLE_VGMRECORDER','-DGG_DISABLE_MMI_THREADS']
    for path in (source/'src',ROOT/'tests',deps/'miniz',deps/'libchdr/include',deps/'minivorbis',deps/'json'):
        flags+=['-I',str(path)]
    objects=out/'gear-objects';objects.mkdir();jobs=[]
    for index,path in enumerate(cpp+c):
        obj=objects/(str(index)+'-'+path.stem+'.o')
        cmd=[str(compiler),*flags,'-x','c++' if path.suffix=='.cpp' else 'c',
             *(['-std=c++20','-include','cerrno'] if path.suffix=='.cpp' else ['-std=c11']),'-c',str(path),'-o',str(obj)]
        jobs.append((cmd,obj));report['commands'].append(cmd)
    def compile_one(job):
        cmd,obj=job;result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        obj.with_suffix('.log').write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(compile_one,jobs))
    libraries=[path.resolve() for path in args.library]
    if not libraries or any(not path.is_file() for path in libraries):raise ValueError('Supply explicit existing external libraries')
    bindings['external_libraries']={str(path):sha(path) for path in libraries}
    binary=out/'gear-read-head.exe'
    common.evidence([str(compiler),*[str(obj) for _,obj in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(binary)],'gear-link',out,report,bindings)
    bindings['gear_artifacts']={str(path):sha(path) for path in [binary,*[obj for _,obj in jobs]]}
    return binary


def build_tool(args,tool,out,report,bindings,compiler,fixture,label='tool'):
    cmake,ninja=(Path(shutil.which(str(value)) or '').resolve() for value in (args.cmake,args.ninja))
    if not cmake.is_file() or not ninja.is_file():raise ValueError('Require CMake and Ninja')
    bindings['tools'].update({str(path):sha(path) for path in (cmake,ninja)})
    q=infrastructure.cmake_quote;wrapper=out/(label+'-wrapper');wrapper.mkdir()
    lines=['cmake_minimum_required(VERSION 3.20)','project(ReadHeadProof LANGUAGES CXX)',
           *['set('+option+' OFF CACHE BOOL "" FORCE)' for option in ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
           f'add_subdirectory({q(tool)} tool)',
           f'pce_add_native_module(_module MODULE {q(fixture/"module.cpp")} MANIFEST {q(fixture/"module.json")})',
           f'add_executable(read-head-probe {q(ROOT/"tests/read_head_probe.cpp")})',
           f'target_include_directories(read-head-probe PRIVATE {q(fixture)})',
           'target_link_libraries(read-head-probe PRIVATE ${_module} pce-runtime)']
    config=wrapper/'CMakeLists.txt';config.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    bindings.setdefault('tool_build_inputs',{})[str(config)]=sha(config);build=out/(label+'-build')
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_MAKE_PROGRAM='+str(ninja)],label+'-configure',out,report,bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','read-head-probe','--parallel','4'],label+'-build',out,report,bindings,600)
    binary=build/('read-head-probe.exe' if os.name=='nt' else 'read-head-probe')
    bindings.setdefault('tool_build_artifacts',{}).update({str(path):sha(path) for path in build.rglob('*')
        if path.is_file() and (path.suffix in ('.obj','.o','.a') or path.name in ('CMakeCache.txt','build.ninja','rules.ninja','.ninja_log'))})
    bindings['tool_build_artifacts'][str(binary)]=sha(binary)
    return binary


def expected_hits(cases,mixed):
    """Count authored supervisor operations independently of either CPU tier."""
    from generate_scsi_fixture import make_fixture
    _,sites=make_fixture();pcs={(opcode,address):pc for pc,opcode,address in sites};hits={}
    def add(opcode,address,count):
        if count:
            pc=pcs[opcode,address];hits[pc]=hits.get(pc,0)+count
    for case in cases:
        for operation in case['operations']:
            if operation[0] in ('c','s'):
                count=operation[2]
                add(0x8D,0x1800,1);add(0x8D,0x1801,count);add(0x8D,0x1802,2*count)
    for row in expected(cases,mixed):
        if row['kind']!='reply':continue
        payload=len(row['data'])
        if row['automatic']:
            add(0xAD,0x1808,payload);add(0xEA,0,2*payload)
            add(0xAD,0x1801,2);add(0x8D,0x1802,4)
        else:
            add(0xAD,0x1801,payload+2);add(0x8D,0x1802,2*(payload+2))
    return hits


def validate_capture(capture,execution,native,hits):
    from generate_scsi_fixture import make_fixture
    snapshot,cases=make_fixture();lookup={pc:(opcode,address) for pc,opcode,address in cases}
    if type(capture) is not dict or set(capture)!={'schema','runtime_abi','capacity','dropped_instructions','unreadable_instructions','retired_instructions','complete','observations'}:
        raise ValueError('Head capture schema differs')
    integers=('schema','runtime_abi','capacity','dropped_instructions','unreadable_instructions','retired_instructions')
    if any(type(capture[key]) is not int for key in integers) or capture['schema']!=1 or capture['capacity']<=0:
        raise ValueError('Head capture integer types differ')
    if capture.get('runtime_abi')!=ABI or capture.get('complete') is not True or capture.get('dropped_instructions')!=0 or capture.get('unreadable_instructions')!=0:
        raise ValueError('Incomplete or incompatible head source capture')
    if type(capture['observations']) is not list:raise ValueError('Head source records must be a list')
    total=0;seen=set()
    for row in capture['observations']:
        if type(row) is not dict or set(row)!={'pc','mpr','physical','data','native_hits','interpreted_hits'} or type(row['pc']) is not int:
            raise ValueError('Head source record fields differ')
        if any(type(row[key]) is not list or any(type(value) is not int for value in row[key]) for key in ('mpr','physical','data')):
            raise ValueError('Head source coordinate types differ')
        pc=row['pc']
        if pc not in lookup or pc not in hits or pc in seen or row['mpr']!=list(snapshot.mpr):raise ValueError('Head full source PC/MPR differs')
        seen.add(pc);opcode,address=lookup[pc];size=1 if opcode==0xEA else 3
        physical=[0x1F0000+(pc&8191)+i for i in range(size)]
        if row['physical']!=physical or row['data']!=[snapshot.memory[p] for p in physical]:raise ValueError('Head physical source bytes differ')
        wanted='native_hits' if native else 'interpreted_hits';other='interpreted_hits' if native else 'native_hits'
        if type(row[wanted]) is not int or row[wanted]!=hits[pc] or type(row[other]) is not int or row[other]!=0:
            raise ValueError('Head source execution tier differs')
        total+=row[wanted]
    if seen!=set(hits) or not seen or total!=capture['retired_instructions'] or total!=execution['retired_instructions']:
        raise ValueError('Head actual retirement/source hit total differs')
    if execution['pure_guards']!=(4 if native else 0):raise ValueError('Head pure source guards differ')
    return total,len(seen)


def validate_execution(work,cases,records,divisor,native,hits):
    wanted=dict(schema=1,tier='native' if native else 'interpreter',divisor=divisor,
        retired_instructions=sum(hits.values()),pure_guards=4 if native else 0,cases=len(cases),records=records)
    mismatch=difference(work,wanted)
    if mismatch:raise ValueError('Head execution accounting differs: '+json.dumps(mismatch))


def run(args):
    tool,out=args.tool_source.resolve(),args.out.resolve()
    compiler=Path(shutil.which(str(args.compiler)) or '').resolve()
    if out.exists() or not out.is_relative_to(ROOT/'.local') or not compiler.is_file():raise ValueError('Require compiler and new private .local output')
    from pcerecomp.project import source_identity
    sources=[Path(__file__),ROOT/'tests/read_head_probe.cpp',ROOT/'tests/geargrafx_read_head_probe.cpp',
        ROOT/'tests/geargrafx_sense_probe.cpp',ROOT/'tests/sense_probe_support.hpp',ROOT/'tests/reset_probe_support.hpp',
        ROOT/'tests/generate_scsi_fixture.py',ROOT/'scripts/cue_reference.py',ROOT/'scripts/mapper_reference.py',
        ROOT/'scripts/filtered_audio_reference.py',ROOT/'scripts/hucard_reference.py',ROOT/'scripts/psg_reference.py',
        tool/'CMakeLists.txt',*sorted((tool/'pcerecomp').glob('*.py')),
        *sorted((tool/'runtime').rglob('*.cpp')),*sorted((tool/'runtime').rglob('*.hpp')),*sorted((tool/'cmake').glob('*.cmake'))]
    bindings=dict(tools={str(compiler):sha(compiler)},authored_sources={str(path):sha(path) for path in sources})
    report=dict(schema=1,result='incomplete',commands=[],bindings=bindings,oracle_commit=reference.COMMIT,
        scope=__doc__,not_checked=['Cross-core CPU retirement/timing','Physical drive seeks','Hardware reset parity','Captured subchannels',
            'READ user data from AUDIO tracks (known Gear/tool media-policy disagreement)','Retail software'])
    out.mkdir(parents=True)
    try:
        from generate_scsi_fixture import generate
        fixture=out/'fixture';generate(fixture);rom,cues=fixtures(out)
        bindings['fixtures']={str(path):sha(path) for path in [rom,*cues.values(),out/'data.bin',out/'audio.bin',*fixture.iterdir()] if path.is_file()}
        gear=build_gear(args,out,report,bindings,compiler)
        binary=build_tool(args,tool,out,report,bindings,compiler,fixture)
        comparisons=[];native_work=interpreted_work=0
        for mixed in (False,True):
            for automatic in (0,1):
                cases=plans(mixed,automatic);wanted=expected(cases,mixed);hits=expected_hits(cases,mixed)
                plan=out/('mixed' if mixed else 'data')
                plan=plan.with_name(plan.name+'-ack'+str(automatic)+'.plan');plan.write_text(serialize(cases),encoding='ascii')
                bindings['fixtures'][str(plan)]=sha(plan)
                gear_label=plan.stem+'-gear';gear_report=out/(gear_label+'-execution.json')
                original=common.evidence([str(gear),str(plan),str(rom),str(cues[mixed]),'gear','3','-',str(gear_report)],gear_label,out,report,bindings,180)
                gear_rows=json.loads(original.stdout);checks=validate_rows(gear_rows,wanted)
                bindings['raw_outputs'][str(gear_report)]=sha(gear_report)
                for speed in (3,12):
                    captures={}
                    for tier in ('interpreter','native'):
                        label=plan.stem+'-s'+str(speed)+'-'+tier;capture=out/(label+'-capture.json');execution=out/(label+'-execution.json')
                        actual=common.evidence([str(binary),str(plan),str(rom),str(cues[mixed]),tier,str(speed),str(capture),str(execution)],label,out,report,bindings,180)
                        rows=json.loads(actual.stdout);validate_rows(rows,wanted)
                        if rows!=gear_rows:raise ValueError('Full original Gear head response differs')
                        work=json.loads(execution.read_text());source=json.loads(capture.read_text())
                        validate_execution(work,cases,len(rows),speed,tier=='native',hits)
                        retired,sites=validate_capture(source,work,tier=='native',hits);captures[tier]=source
                        if tier=='native':native_work+=retired
                        else:interpreted_work+=retired
                        bindings['raw_outputs'].update({str(path):sha(path) for path in (capture,execution)})
                        comparisons.append(dict(media='mixed' if mixed else 'data',automatic=automatic,divisor=speed,tier=tier,
                            cases=len(cases),records=len(rows),literal_checks=checks,retired_instructions=retired,source_identities=sites))
                    def normalized_capture(value):
                        return [dict(pc=row['pc'],mpr=row['mpr'],physical=row['physical'],data=row['data'],hits=row['native_hits']+row['interpreted_hits']) for row in value['observations']]
                    if normalized_capture(captures['native'])!=normalized_capture(captures['interpreter']):raise ValueError('Native/interpreter per-source hit identities differ')
        report.update(result='pass',tool=source_identity(tool),comparisons=comparisons,native_steps=native_work,interpreter_steps=interpreted_work,
            native_fallback=0,source_scope='Full PC/8-MPR/physical/source-byte identity and paired exact per-site hits; host-supervised instruction selection')
        if args.baseline_tool:
            baseline=args.baseline_tool.resolve()
            baseline_sources=[baseline/'CMakeLists.txt',*sorted((baseline/'pcerecomp').glob('*.py')),
                *sorted((baseline/'runtime').rglob('*.cpp')),*sorted((baseline/'runtime').rglob('*.hpp')),*sorted((baseline/'cmake').glob('*.cmake'))]
            bindings['baseline_sources']={str(path):sha(path) for path in baseline_sources}
            old_binary=build_tool(args,baseline,out,report,bindings,compiler,fixture,label='baseline')
            case=plans(False,0)[:1];plan=out/'baseline-counterexample.plan';plan.write_text(serialize(case),encoding='ascii')
            capture=out/'baseline-capture.json';execution=out/'baseline-execution.json'
            bindings['fixtures'][str(plan)]=sha(plan)
            actual=common.evidence([str(old_binary),str(plan),str(rom),str(cues[False]),'interpreter','3',str(capture),str(execution)],
                'baseline-counterexample',out,report,bindings,180)
            rows=json.loads(actual.stdout);wanted=expected(case,False)
            mismatch=difference(rows,wanted)
            if len(rows)!=5 or rows[2]!=dict(kind='head',values=[2]) or rows[3].get('data')!=q_response(2,False) or not mismatch:
                raise ValueError('Baseline did not exhibit the exact loaded-LBA/idle-Q counterexample')
            baseline_hits=expected_hits(case,False)
            baseline_work=json.loads(execution.read_text())
            validate_execution(baseline_work,case,len(rows),3,False,baseline_hits)
            validate_capture(json.loads(capture.read_text()),baseline_work,False,baseline_hits)
            bindings['raw_outputs'].update({str(path):sha(path) for path in (capture,execution)})
            report['baseline_counterexample']=dict(tool=source_identity(baseline),expected_failure=True,first_difference=mismatch,
                actual_dd=rows[3]['data'],expected_dd=q_response(3,False),
                scope='Old runtime interpreter, same new authored supervisor/static fixture; actual READ sector2 then idleDD, no head-state injection')
    except Exception as error:
        report.update(result='fail',error=str(error));raise
    finally:
        reference.record_preservation(report,bindings)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if report['result']!='pass':raise ValueError('Reference input identity changed')
    print(json.dumps({key:value for key,value in report.items() if key not in ('bindings','commands')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True)
    parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-tool',type=Path)
    parser.add_argument('--compiler',default='clang++');parser.add_argument('--cmake',default='cmake');parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    try:run(parser.parse_args())
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError) as error:
        print(error,file=sys.stderr);raise SystemExit(1)
