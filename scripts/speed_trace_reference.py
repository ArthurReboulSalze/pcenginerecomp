"""Original full-Gear mixed-speed/timer traces with explicit literal profiles."""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import mapper_reference as infrastructure
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as reference
from generate_speed_trace_fixture import generate,STEPS,PRIMER_STEPS,expected_rows
sha=reference.sha

def build_gear(args,out,report,bindings,compiler):
    checkout,source=infrastructure.pinned_snapshot(args.gear_source.resolve(),out,bindings)
    report['reference_canonical_source_sha256']=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    cpp,c=reference.compile_sources(checkout,source);cpp.append(ROOT/'tests/geargrafx_speed_trace_probe.cpp')
    deps=checkout/'platforms/shared/dependencies'
    flags=['-O2','-ffp-contract=off','-ffunction-sections','-fdata-sections','-DGG_DISABLE_DISASSEMBLER','-DGG_DISABLE_VGMRECORDER','-DGG_DISABLE_MMI_THREADS']
    for p in(checkout/'src',ROOT/'tests',out/'fixture',deps/'miniz',deps/'libchdr/include',deps/'minivorbis',deps/'json'):flags+=['-I',str(p)]
    objects=out/'gear-objects';objects.mkdir();jobs=[]
    for index,path in enumerate(cpp+c):
        obj=objects/(str(index)+'-'+path.stem+'.o')
        command=[str(compiler),*flags,'-x','c++'if path.suffix=='.cpp'else'c',*(['-std=c++20','-include','cerrno']if path.suffix=='.cpp'else['-std=c11']),'-c',str(path),'-o',str(obj)]
        jobs.append((command,obj));report['commands'].append(command)
    def compile_one(job):
        command,obj=job;r=subprocess.run(command,capture_output=True,text=True,timeout=180)
        obj.with_suffix('.log').write_text(r.stdout+r.stderr);r.check_returncode()
    with ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(compile_one,jobs))
    libraries=[p.resolve()for p in args.library]
    if not libraries or any(not p.is_file()for p in libraries):raise ValueError('Supply existing explicit external libraries')
    bindings['external_libraries']={str(p):sha(p)for p in libraries}
    binary=out/'gear-speed.exe'
    common.evidence([str(compiler),*[str(obj)for _,obj in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(binary)],'gear-link',out,report,bindings)
    bindings['gear_objects']={str(obj):sha(obj)for _,obj in jobs};bindings['gear_binary']={str(binary):sha(binary)}
    return binary


def build_tool(args,out,report,bindings,compiler,fixture):
    quote=infrastructure.cmake_quote;tool=args.tool_source.resolve()
    cmake,ninja=(Path(shutil.which(str(v))or'').resolve()for v in(args.cmake,args.ninja))
    bindings['tools'].update({str(p):sha(p)for p in(cmake,ninja)})
    wrapper=out/'tool-wrapper';wrapper.mkdir()
    source=ROOT/'tests/speed_trace_tests.cpp'
    lines=['cmake_minimum_required(VERSION 3.20)','project(SpeedTraceProof LANGUAGES CXX)',*['set('+o+' OFF CACHE BOOL "" FORCE)'for o in('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
        f'add_subdirectory({quote(tool)} tool)',
        f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
        f'add_executable(speed-probe {quote(source)})',
        f'target_include_directories(speed-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
        'target_link_libraries(speed-probe PRIVATE ${_module} pce-runtime)']
    file=wrapper/'CMakeLists.txt';file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)]=sha(file);build=out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_MAKE_PROGRAM='+str(ninja)],'tool-configure',out,report,bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','speed-probe','--parallel','4'],'tool-build',out,report,bindings,600)
    binary=build/('speed-probe.exe'if os.name=='nt'else'speed-probe')
    bindings['tool_binary']={str(binary):sha(binary)};return binary


def trace_file(out,name,body,engine,firmware):
    from pcerecomp.reference_trace import load_trace
    header=dict(type='header',schema=1,format='pce-cpu-trace-1',engine=engine,
        fixture_sha256=sha(firmware),case='software-primer-mixed-speed-masked-timer-v1',clock='master-ticks',
        phase='instruction-boundary',unavailable_fields=[])
    path=out/(name+'-trace.jsonl');path.write_text(json.dumps(header)+'\n'+body,encoding='utf-8')
    return path,load_trace(path)

def run(args):
    tool=args.tool_source.resolve();out=args.out.resolve();compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not compiler.is_file():raise ValueError('NEW private output and existing compiler required')
    sys.path.insert(0,str(tool))
    from pcerecomp import project
    from pcerecomp.reference_trace import compare_traces
    if Path(project.__file__).resolve()!=tool/'pcerecomp/project.py':raise ValueError('Selected source import required')
    paths=[Path(__file__),*[ROOT/'tests'/p for p in('generate_speed_trace_fixture.py','speed_trace_tests.cpp','geargrafx_speed_trace_probe.cpp','geargrafx_mapper_probe.cpp','reset_probe_support.hpp','reference_trace_support.hpp')],*[ROOT/'scripts'/p for p in('mapper_reference.py','hucard_reference.py','filtered_audio_reference.py')]]
    paths+=sorted((tool/'pcerecomp').glob('*.py'))+sorted((tool/'runtime').rglob('*.cpp'))+sorted((tool/'runtime').rglob('*.hpp'))+[tool/'CMakeLists.txt',tool/'cmake/PCEConsumer.cmake']
    bindings=dict(tools={str(compiler):sha(compiler)},authored_sources={str(p.resolve()):sha(p)for p in paths})
    report=dict(schema=1,result='incomplete',commands=[],bindings=bindings,scope='Authored software-primer mixed-speed/real masked timer MMIO; full original separate Gear scheduler; raw clocks retained and independently literal-checked per timing profile. No hardware-reset or IRQ-delivery parity claim.')
    out.mkdir(parents=True);epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,p in enumerate(paths):
        dest=epoch/str(index)/p.name;dest.parent.mkdir();shutil.copyfile(p,dest);bindings['authored_epoch'][str(dest)]=sha(dest)
    try:
        fixture=out/'fixture';generate(fixture);bindings['fixture']={str(p):sha(p)for p in fixture.iterdir()if p.is_file()}
        firmware=fixture/'authored.pce';gear=build_gear(args,out,report,bindings,compiler)
        reference_output=common.evidence([str(gear),str(firmware)],'gear',out,report,bindings)
        source_sha=report['reference_canonical_source_sha256']
        gear_path,golden=trace_file(out,'gear',reference_output.stdout,dict(name='Geargrafx',revision=reference.COMMIT,source_sha256=source_sha,binary_sha256=sha(gear)),firmware)
        binary=build_tool(args,out,report,bindings,compiler,fixture);identity=project.source_identity(tool);captures={};traces={};work={}
        from pcerecomp.capture import load_capture
        for tier in('interpreted','native'):
            capture=out/(tier+'-capture.json');result=common.evidence([str(binary),'--probe',str(firmware),tier,str(capture)],tier,out,report,bindings)
            path,trace=trace_file(out,tier,result.stdout,dict(name='pcerecomp-'+tier,revision=identity['revision'],source_sha256=identity['source_sha256'],binary_sha256=sha(binary)),firmware)
            traces[tier]=trace
            observed,digest=load_capture(capture);bindings['raw_outputs'][str(capture)]=digest
            n=sum(o['native_hits']for o in observed['observations']);i=sum(o['interpreted_hits']for o in observed['observations'])
            if observed['runtime_abi']!=ABI or not observed['complete']or observed['retired_instructions']!=PRIMER_STEPS+STEPS or(n,i)!=((PRIMER_STEPS+STEPS,0)if tier=='native'else(0,PRIMER_STEPS+STEPS)):raise ValueError('Actual captured work differs')
            captures[tier]=observed;work[tier]=dict(native=n,interpreted=i,literal_checks=STEPS*27,measured_instructions=STEPS,primer_instructions=PRIMER_STEPS)
        internal=compare_traces(traces['native'],traces['interpreted'])
        if not internal['equal']:raise ValueError('Exact native/interpreter raw trace mismatch')
        key=lambda o:(o['pc'],tuple(o['mpr']),tuple(o['physical']),tuple(o['data']))
        if {key(o):o['native_hits']for o in captures['native']['observations']}!={key(o):o['interpreted_hits']for o in captures['interpreted']['observations']}:raise ValueError('Full byte/MPR source hit multiset mismatch')
        initial_gear=copy.deepcopy(golden.initial);initial_native=copy.deepcopy(traces['native'].initial)
        initial_gear.pop('ticks');initial_native.pop('ticks')
        if initial_gear!=initial_native:raise ValueError('Undocumented post-software-primer initial-state difference')
        known=[]
        if len(golden.instructions)!=STEPS or len(traces['native'].instructions)!=STEPS:raise ValueError('Exact measured trace extent')
        for index,(expected,actual)in enumerate(zip(golden.instructions,traces['native'].instructions)):
            g=copy.deepcopy(expected);r=copy.deepcopy(actual)
            gt,rt=g['state'].pop('ticks'),r['state'].pop('ticks')
            if g!=r:raise ValueError('Undocumented Gear architectural/RAM difference at ordinal '+str(index+1))
            gelapsed=gt-golden.initial['ticks'];relapsed=rt-traces['native'].initial['ticks']
            if gelapsed!=expected_rows('gear')[index][7]or relapsed!=expected_rows('runtime')[index][7]:raise ValueError('Raw epoch-relative timing differs from literal profile')
            if gt!=rt:known.append(dict(ordinal=index+1,gear_raw=gt,runtime_raw=rt,gear_elapsed=gelapsed,runtime_elapsed=relapsed))
        report.update(result='pass-with-documented-reference-timing-difference',tool=identity,cases=1,measured_records=STEPS,execution=work,source_identities=len(captures['native']['observations']),native_interpreter=internal,known_gear_timing_differences=known,gear_trace=str(gear_path),timing_policy='No trace rewriting. Raw epochs retained; measured elapsed literal checks declared from actual software-primer initial boundary. Architectural/RAM fields exact; all differing ticks explicitly enumerated.')
    except Exception as error:report.update(result='fail',error=str(error));raise
    finally:
        reference.record_preservation(report,bindings);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in('commands','bindings','known_gear_timing_differences')},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True);parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--compiler',default='clang++');parser.add_argument('--cmake',default='cmake');parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    try:run(parser.parse_args())
    except(ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError)as error:print(error,file=sys.stderr);raise SystemExit(1)
