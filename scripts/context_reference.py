"""Independent original-Gear proof of statically discovered TAM contexts.

No retail inputs, captured-code emission or interpreter opcode bridges. Original
GPL reference sources are compiled in a separate process from pinned Git blobs.
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
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as reference
from generate_context_fixture import firmware,expected_rows,generate,STEPS
sha=reference.sha


def records(raw):
    value=json.loads(raw)
    expected=[dict(kind='cpu',values=row)for divisor in(3,12)for row in expected_rows(divisor)]
    if type(value)is not list or len(value)!=2*STEPS:raise ValueError('Wrong context trace extent')
    for index,(row,literal)in enumerate(zip(value,expected)):
        if type(row)is not dict or set(row)!={'kind','values'}or row['kind']!='cpu'or type(row['values'])is not list or len(row['values'])!=20 or any(type(v)is not int or not 0<=v<2**64 for v in row['values']):raise ValueError('Invalid context trace shape')
        if row!=literal:raise ValueError(f'Independent literal context row {index} differs: {row} expected {literal}')
    return value


def build_gear(args,out,report,bindings,compiler):
    checkout,source=infrastructure.pinned_snapshot(args.gear_source.resolve(),out,bindings)
    cpp,c=reference.compile_sources(checkout,source);cpp.append(ROOT/'tests/geargrafx_context_probe.cpp')
    deps=checkout/'platforms/shared/dependencies'
    flags=['-O2','-ffp-contract=off','-ffunction-sections','-fdata-sections','-DGG_DISABLE_DISASSEMBLER','-DGG_DISABLE_VGMRECORDER','-DGG_DISABLE_MMI_THREADS']
    for p in(checkout/'src',ROOT/'tests',deps/'miniz',deps/'libchdr/include',deps/'minivorbis',deps/'json'):flags+=['-I',str(p)]
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
    binary=out/'gear-context.exe'
    common.evidence([str(compiler),*[str(obj)for _,obj in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(binary)],'gear-link',out,report,bindings)
    bindings['gear_objects']={str(obj):sha(obj)for _,obj in jobs};bindings['gear_binary']={str(binary):sha(binary)}
    return binary


def build_tool(args,out,report,bindings,compiler,fixture):
    quote=infrastructure.cmake_quote;tool=args.tool_source.resolve()
    cmake,ninja=(Path(shutil.which(str(v))or'').resolve()for v in(args.cmake,args.ninja))
    bindings['tools'].update({str(p):sha(p)for p in(cmake,ninja)})
    wrapper=out/'tool-wrapper';wrapper.mkdir()
    source=ROOT/'tests/context_tests.cpp'
    lines=['cmake_minimum_required(VERSION 3.20)','project(StaticContextProof LANGUAGES CXX)',*['set('+o+' OFF CACHE BOOL "" FORCE)'for o in('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
        f'add_subdirectory({quote(tool)} tool)',
        f'pce_add_native_module(_module MODULE {quote(fixture/"module.cpp")} MANIFEST {quote(fixture/"module.json")})',
        f'add_executable(context-probe {quote(source)})',
        f'target_include_directories(context-probe PRIVATE {quote(fixture)} {quote(ROOT/"tests")})',
        'target_link_libraries(context-probe PRIVATE ${_module} pce-runtime)']
    file=wrapper/'CMakeLists.txt';file.write_text('\n'.join(lines)+'\n')
    bindings.setdefault('tool_build_inputs',{})[str(file)]=sha(file);build=out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_MAKE_PROGRAM='+str(ninja)],'tool-configure',out,report,bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','context-probe','--parallel','4'],'tool-build',out,report,bindings,600)
    binary=build/('context-probe.exe'if os.name=='nt'else'context-probe')
    bindings['tool_binary']={str(binary):sha(binary)};return binary


def run(args):
    tool=args.tool_source.resolve();out=args.out.resolve();compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not compiler.is_file():raise ValueError('Require NEW private output and explicit existing compiler')
    if args.native:
        sys.path.insert(0,str(tool));from pcerecomp import project
        if Path(project.__file__).resolve()!=tool/'pcerecomp/project.py':raise ValueError('Wrong selected compiler import')
    sources=[Path(__file__),ROOT/'tests/generate_context_fixture.py',ROOT/'tests/context_tests.cpp',ROOT/'tests/geargrafx_context_probe.cpp',ROOT/'tests/geargrafx_mapper_probe.cpp',ROOT/'tests/reset_probe_support.hpp',*[ROOT/'scripts'/p for p in('mapper_reference.py','hucard_reference.py','filtered_audio_reference.py')]]
    sources+=sorted((tool/'pcerecomp').glob('*.py'))+sorted((tool/'runtime').rglob('*.cpp'))+sorted((tool/'runtime').rglob('*.hpp'))+[tool/'CMakeLists.txt',tool/'cmake/PCEConsumer.cmake']
    bindings=dict(tools={str(compiler):sha(compiler)},authored_sources={str(p.resolve()):sha(p)for p in sources})
    report=dict(schema=1,result='incomplete',oracle_commit=reference.COMMIT,verification_mode='static-native'if args.native else'gear-only',commands=[],bindings=bindings,
        scope='Authored firmware: real executing-page and data-page TAM, multi-bit mapping, branches/loops, same logical PC under distinct mappings; independent original Gear instruction states and literal expectations. Static schema2 CFG emission only; runtime ABI unchanged.',
        not_checked=['Retail software','Hardware bus phase or reset certification','General executable RAM mutation analysis','Indirect call/return recovery','Unproven register constants'])
    out.mkdir(parents=True);epoch=out/'authored-inputs';epoch.mkdir();bindings['authored_epoch']={}
    for index,p in enumerate(sources):
        copy=epoch/str(index)/p.name;copy.parent.mkdir();shutil.copyfile(p,copy);bindings['authored_epoch'][str(copy)]=sha(copy)
    try:
        fixture=out/'fixture';generate(fixture,emit_module=args.native)
        bindings['fixture']={str(p):sha(p)for p in fixture.iterdir()if p.is_file()}
        image=fixture/'authored.pce';gear=build_gear(args,out,report,bindings,compiler)
        golden=common.evidence([str(gear),str(image)],'gear',out,report,bindings)
        golden_rows=records(golden.stdout);literals={'gear':20*len(golden_rows)}
        if args.native:
            from pcerecomp.capture import load_capture
            from pcerecomp.project import source_identity
            binary=build_tool(args,out,report,bindings,compiler,fixture);captures={};traces={};work={}
            for tier in('interpreted','native'):
                capture=out/(tier+'-capture.json')
                result=common.evidence([str(binary),'--probe',str(image),tier,str(capture)],tier,out,report,bindings)
                traces[tier]=records(result.stdout)
                if traces[tier]!=golden_rows:raise ValueError('Exact original Gear trace mismatch')
                observed,digest=load_capture(capture);bindings['raw_outputs'][str(capture)]=digest
                if observed['runtime_abi']!=ABI or not observed['complete']or observed['retired_instructions']!=2*STEPS or any(o['interpreted_hits']if tier=='native'else o['native_hits']for o in observed['observations']):raise ValueError('Actual context tier/loss metadata differs')
                tag,n,i,g,checks=result.stderr.strip().split()
                if tag!='CONTEXT_WORK'or (int(n),int(i),int(checks))!=((80,0,1600)if tier=='native'else(0,80,1600))or(int(g)>0)!=(tier=='native'):raise ValueError('Exact native/interpreted work differs')
                work[tier]=dict(native=int(n),interpreted=int(i),pure_guards=int(g),literal_checks=int(checks));captures[tier]=observed;literals[tier]=int(checks)
            identity=lambda o:(o['pc'],tuple(o['mpr']),tuple(o['physical']),tuple(o['data']))
            if {identity(o):o['native_hits']for o in captures['native']['observations']}!={identity(o):o['interpreted_hits']for o in captures['interpreted']['observations']}:raise ValueError('Full per-source context hits differ')
            report.update(tool=source_identity(tool),execution=work,source_identities=len(captures['native']['observations']),analysis=sha(fixture/'analysis.json'))
        report.update(result='pass',cases=2,records=len(golden_rows),literal_checks=literals)
    except Exception as error:report.update(result='fail',error=str(error));raise
    finally:
        reference.record_preservation(report,bindings);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['result']!='pass':raise ValueError('Evidence preservation failed')
    print(json.dumps({k:v for k,v in report.items()if k not in('commands','bindings')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True);parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--native',action='store_true');parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compiler',default='clang++');parser.add_argument('--cmake',default='cmake');parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    try:run(parser.parse_args())
    except(ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError)as error:print(error,file=sys.stderr);raise SystemExit(1)
