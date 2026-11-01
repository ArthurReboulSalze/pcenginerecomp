"""Independent authored distance-CD checks against untouched original cores.

Original Gear is a separate executable; port supervision is not original CPU
retirement. Toolkit port instructions execute emitted operations or interpreter
semantics. The selected drive model is not hardware or complete-game parity.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from scripts import cdda_gap_reference as infrastructure
from scripts import filtered_audio_reference as reference
from scripts import hucard_reference as common
from scripts import mapper_reference as compiler_support
from generate_cd_timing_fixture import generate as emit_fixture
from pcerecomp.abi import ABI
sha=reference.sha
MASTER=21477273
# Mathematical geometry from David Shadoff's MIT-licensed PCECD_seek,
# revision7b9a70702d2f5422b924ee3cf7d42ff3ae5436ad. Full attribution is
# retained by runtime/cd_timing.cpp; the selected 18/48 model is named Gear.
GROUPS=((10,0,12572,13347),(11,12573,30244,14682),(12,30245,49523,16017),
 (13,49524,70408,17351),(14,70409,92900,18686),(15,92901,116998,20021),
 (16,116999,142703,21356),(17,142704,170014,22690),(18,170015,198932,24025),
 (19,198933,229456,25360),(20,229457,261587,26695),(21,261588,295324,28029),
 (22,295325,330668,29364),(23,330669,333012,30699))

def require(ok,why):
    if not ok:raise ValueError(why)

def seek_ms(start,target):
    require(type(start)is type(target)is int and 0<=start<=333012 and 0<=target<=333012,'Measured seek domain required')
    src=next(i for i,g in enumerate(GROUPS)if g[1]<=start<=g[2]);dst=next(i for i,g in enumerate(GROUPS)if g[1]<=target<=g[2])
    gap=abs(target-start);a,b=GROUPS[src],GROUPS[dst]
    if src==dst:tracks=100*(gap//b[0])
    elif dst>src:tracks=100*((a[2]-start)//a[0]+(target-b[1])//b[0])+160648*(dst-src-1)
    else:tracks=100*((start-a[1])//a[0]+(b[2]-target)//b[0])+160648*(src-dst-1)
    if gap<2:return 150
    if gap<5:return (30000+b[3])//200
    if tracks<=8000:return (60000+b[3])//200
    if tracks<=16000:return (73200+b[3])//200
    if tracks<=64400:return (366*800000+b[3]*4000+(tracks-16100)*1666)//800000
    return (800*1950000+(tracks-64400)*1666)//1950000

def seek_ticks(start,target):return seek_ms(start,target)*MASTER//1000

def math_vectors():
    points={0,333012}
    for width,first,last,_ in GROUPS:
        points.update((first,last,(first+last)//2))
        for tracks in(0,1,4,5,80,81,160,161,644,645):
            for n in(-1,0,1):
                for v in(first+tracks*width+n,last-tracks*width+n):
                    if first<=v<=last:points.add(v)
    result={(a,b)for a in points for b in(0,333012)}
    for _,first,last,_ in GROUPS:
        for point in points:
            if first<=point<=last:result.update(((first,point),(point,first),(last,point),(point,last)))
    edges={v for _,first,last,_ in GROUPS for v in(first,last)}
    result.update((a,b)for a in edges for b in edges)
    for a in points:
        for delta in(0,1,2,4,5):
            for b in(a+delta,a-delta):
                if 0<=b<=333012:result.add((a,b))
    return sorted(result)

def cases():
    def read(lba,count=1):return f'S 8 0 {lba} {count}'
    def audio(op,lba=0,mode=1):return f'S {op} {mode} {lba} 1'
    result=[]
    def add(name,steps,profile='gear-distance'):result.append(dict(id=name,profile=profile,steps=steps))
    for lba in(0,2,5,810,6450):
        add(f'read-{lba}',[read(lba),'P admitted','E load -1','P before-load','A 1','P at-load','D 0','P complete'])
    add('read-fixed-control',[read(6450),'P admitted','E load -1','P before-load','A 1','P at-load','D 1','P complete'],'fixed')
    add('d8-fixed-control',[audio(0xD8,7000,1),'P admitted','E seek -1','P before-seek','A 1','P at-seek','D 0','P acked'],'fixed')
    for mode in(0,1):
        for target in(2,7000):
            steps=[audio(0xD8,target,mode),'P admitted','K','E seek -1','P before-seek','A 1','P at-seek','A 1','P after-seek','D 0','P acked']
            if mode and target==7000:steps+=['K','L before-playback','E play -1','P before-play','A 1','P at-play','A 1000','L after-playback','P after-play']
            add(f'd8-mode{mode}-target{target}',steps)
    add('resume-during-seek',[audio(0xD8,7000,0),'P paused-seeking',audio(0xD9,13999,3),'P admitted','K','E seek -1','P before-seek','A 1','P at-seek','D 0','L before-playback','E play -1','P before-play','A 1','P at-play','A 1000','L after-playback'])
    add('resume-after-seek',[audio(0xD8,7000,0),'D 0','P paused',audio(0xD9,13999,3),'P admitted','K','L before-playback','E play -1','P before-play','A 1','P at-play','D 0','A 1000','L after-playback'])
    add('read-during-seek',[audio(0xD8,7000,1),'P seeking',read(6450),'P admitted','E load -1','P before-load','A 1','P at-load','D 0','P complete'])
    add('stop-during-seek',[audio(0xD8,7000,1),'P seeking',audio(0xD9,13999,0),'P stopped','D 0','E seek -1','P before-seek','A 1','P at-seek'])
    add('pause-during-seek',[audio(0xD8,7000,1),'P seeking',audio(0xDA,0,0),'P paused','D 0','E seek -1','P before-seek','A 1','P at-seek'])
    add('reset-during-seek',[audio(0xD8,7000,1),'P seeking','W','P reset','A 20000000','P later'])
    add('q-during-seek',[audio(0xD8,7000,1),'P seeking',audio(0xDD,0,0),'D 0','P queried','E seek -1','P before-seek','A 1','P at-seek'])
    add('q-during-play-delay',[audio(0xD8,7000,1),'E seek 0','D 0',audio(0xDD,0,0),'D 0','P queried','E play -1','P before-play','A 1','P at-play'])
    add('read-retry',[read(0,2),'E load 0','P first-load','E load 0','P occupied','E load 0','P retried','D 1','P complete'])
    add('read-past-leadout',[read(14000),'P admitted','D 0','P complete'])
    return result

def fixture(out):
    out.mkdir();emit_fixture(out)
    rom=bytearray([0xEA]*262144);rom[8190:8192]=bytes((0,0xE0));(out/'authored.pce').write_bytes(rom)
    # Sparse authored payloads: bounded logical geometry, no retail bytes.
    for name,width in(('data.bin',2048),('audio.bin',2352)):
        with(out/name).open('xb')as f:f.truncate(7000*width)
    # Initial nonzero stereo samples expose an accidentally ungated source.
    with(out/'audio.bin').open('r+b')as f:f.write((bytes((0x34,0x12,0xCC,0xED)))*588)
    (out/'disc.cue').write_text('FILE "data.bin" BINARY\n TRACK 01 MODE1/2048\n INDEX 01 00:00:00\nFILE "audio.bin" BINARY\n TRACK 02 AUDIO\n INDEX 01 00:00:00\n',encoding='ascii')
    plan=out/'plan.txt';plan.write_text('\n'.join('R '+r['id']+' '+r['profile']+'\n'+'\n'.join(r['steps'])for r in cases())+'\n',encoding='ascii')
    return plan

def build_gear(args,out,report,bindings,compiler):
    # Reuse the established immutable complete-core build, changing adapter only.
    source,hashes=compiler_support.pinned_snapshot(args.gear_source.resolve(),out,bindings)
    cpp,c=reference.compile_sources(source,hashes);cpp.append(ROOT/'tests/geargrafx_cd_timing_probe.cpp')
    deps=source/'platforms/shared/dependencies';flags=['-O2','-ffp-contract=off','-ffunction-sections','-fdata-sections','-DGG_DISABLE_DISASSEMBLER','-DGG_DISABLE_VGMRECORDER','-DGG_DISABLE_MMI_THREADS']
    for p in(source/'src',ROOT/'tests',deps/'miniz',deps/'libchdr/include',deps/'minivorbis',deps/'json'):flags+=['-I',str(p)]
    objects=out/'gear-objects';objects.mkdir();jobs=[]
    for i,p in enumerate(cpp+c):
        obj=objects/(str(i)+'-'+p.stem+'.o');cmd=[str(compiler),*flags,'-x','c++'if p.suffix=='.cpp'else'c',*(['-std=c++20','-include','cerrno']if p.suffix=='.cpp'else['-std=c11']),'-c',str(p),'-o',str(obj)];jobs.append((cmd,obj));report['commands'].append(cmd)
    def one(job):
        cmd,obj=job;done=subprocess.run(cmd,capture_output=True,text=True,timeout=180);obj.with_suffix('.log').write_text(done.stdout+done.stderr);done.check_returncode()
    with ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(one,jobs))
    libraries=[p.resolve()for p in args.library];require(libraries and all(p.is_file()for p in libraries),'Explicit original-core libraries required');bindings['external_libraries']={str(p):sha(p)for p in libraries};binary=out/'gear-cd-timing.exe'
    common.evidence([str(compiler),*[str(obj)for _,obj in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(binary)],'gear-link',out,report,bindings)
    bindings['gear_artifacts']={str(p):sha(p)for p in[binary,*[obj for _,obj in jobs]]};return binary

def build_tool(args,out,report,bindings,compiler,fixture):
    q=compiler_support.cmake_quote;wrapper=out/'wrapper';wrapper.mkdir();config=wrapper/'CMakeLists.txt'
    config.write_text('\n'.join(['cmake_minimum_required(VERSION 3.20)','project(CdTimingProof LANGUAGES CXX)',*['set('+o+' OFF CACHE BOOL "" FORCE)'for o in('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],f'add_subdirectory({q(args.tool_source.resolve())} tool)',f'pce_add_native_module(_module MODULE {q(fixture/"module.cpp")} MANIFEST {q(fixture/"module.json")})',f'add_executable(cd-timing-probe {q(ROOT/"tests/cd_timing_probe.cpp")})',f'target_include_directories(cd-timing-probe PRIVATE {q(fixture)} {q(ROOT/"tests")})','target_link_libraries(cd-timing-probe PRIVATE ${_module} pce-runtime)'])+'\n')
    bindings['tool_build_inputs']={str(config):sha(config)};build=out/'tool-build'
    common.evidence([str(args.cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_MAKE_PROGRAM='+str(args.ninja)],'tool-configure',out,report,bindings)
    common.evidence([str(args.cmake),'--build',str(build),'--parallel','4'],'tool-build',out,report,bindings,600)
    binary=build/('cd-timing-probe.exe'if os.name=='nt'else'cd-timing-probe');bindings['tool_artifacts']={str(p):sha(p)for p in build.rglob('*')if p.is_file()and(p.suffix in('.obj','.o','.a')or p==binary)};return binary

def additional_math(args,out,report,bindings,compiler,vectors):
    raw=''.join(f'{a} {b}\n'for a,b in vectors)
    def invoke(binary,label,stdin):
        command=[str(binary)];report['commands'].append(command);done=subprocess.run(command,input=stdin,text=True,capture_output=True,timeout=60);(out/(label+'.txt')).write_text(done.stdout);(out/(label+'.err')).write_text(done.stderr);done.check_returncode();bindings.setdefault('raw_outputs',{})[str(out/(label+'.txt'))]=sha(out/(label+'.txt'));return done.stdout
    if args.mesen_header:
        source=args.mesen_header.resolve();require(sha(source)=='927745f6c6e03776c9058246698e12bc361016cbfb7c5cd9630bc820f7365416','Untouched pinned Mesen header required')
        shim=out/'mesen-shim';shim.mkdir();(shim/'pch.h').write_text('#include <cstdint>\n#include <cstdlib>\n');binary=out/'mesen-seek.exe'
        common.evidence([str(compiler),'-O2','-ffp-contract=off','-std=c++20','-I',str(shim),'-DPCE_MESEN_SEEK_HEADER="'+source.as_posix()+'"',str(ROOT/'tests/mesen_cd_seek_probe.cpp'),'-o',str(binary)],'mesen-seek-build',out,report,bindings)
        rows=[list(map(int,line.split()))for line in invoke(binary,'math-mesen',raw).splitlines()];require(len(rows)==len(vectors),'Mesen vector count')
        require(all(row==[a,b,seek_ms(a,b),seek_ticks(a,b)]for(a,b),row in zip(vectors,rows)),'Original Mesen floating/rational mismatch');report['mesen_math_vectors']=len(vectors);bindings['mesen_sources']={str(source):sha(source),str(ROOT/'tests/mesen_cd_seek_probe.cpp'):sha(ROOT/'tests/mesen_cd_seek_probe.cpp'),str(shim/'pch.h'):sha(shim/'pch.h')};bindings.setdefault('math_artifacts',{})[str(binary)]=sha(binary)
    if args.primary_c:
        source=args.primary_c.resolve();require(sha(source)=='9a5e9f965e9a9d46d8c7eafe3bcf9a7d949dc32608d1229e22d27e8a0a8f8d10','Untouched primary MIT seek program required');binary=out/'primary-seek.exe'
        common.evidence([str(compiler),'-O2','-x','c','-std=c11',str(source),'-o',str(binary)],'primary-seek-build',out,report,bindings)
        examples=[]
        for a,b in[(0,0),(0,1),(0,2),(0,5),(0,810),(0,6450),(0,333012),(333012,0)]:
            cmd=[str(binary),str(a),str(b)];done=common.evidence(cmd,f'primary-{a}-{b}',out,report,bindings);examples.append(dict(start=a,target=b,raw=done.stdout,selected_gear_ms=seek_ms(a,b)))
        report['primary_program_examples']=examples;report['primary_disagreement_preserved']='Overlapping initial if overwrites <2; primary intermediate/far16/36 differ from selected18/48.';bindings['primary_sources']={str(source):sha(source)};bindings.setdefault('math_artifacts',{})[str(binary)]=sha(binary)
    if not args.reference_only:
        binary=out/'tool-seek.exe';source=args.tool_source.resolve();inputs=[ROOT/'tests/cd_timing_math_probe.cpp',source/'runtime/src/cd_timing.cpp',source/'runtime/include/pce/cd_timing.hpp',source/'runtime/include/pce/runtime.hpp']
        bindings['tool_math_sources']={str(p):sha(p)for p in inputs};common.evidence([str(compiler),'-O2','-ffp-contract=off','-std=c++20','-I',str(source/'runtime/include'),str(inputs[0]),str(inputs[1]),'-o',str(binary)],'tool-seek-build',out,report,bindings)
        negatives=[(333013,0),(0,333013),(4294967295,0)];text=invoke(binary,'math-tool',raw+''.join(f'{a} {b}\n'for a,b in negatives));rows=[line.split()for line in text.splitlines()];require(len(rows)==len(vectors)+len(negatives),'Tool math extent')
        for(a,b),row in zip(vectors,rows):require(row==[str(a),str(b),'ok',str(seek_ticks(a,b))],'Production rational math differs')
        require(all(row==[str(a),str(b),'refused','0']for(a,b),row in zip(negatives,rows[len(vectors):])),'Out-of-domain profile must refuse explicitly');report['tool_math_vectors']=len(vectors);report['domain_refusals']=len(negatives);bindings.setdefault('math_artifacts',{})[str(binary)]=sha(binary)

def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--gear-source',type=Path,required=True);parser.add_argument('--tool-source',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--compiler',required=True);parser.add_argument('--cmake',required=True);parser.add_argument('--ninja',required=True);parser.add_argument('--library',type=Path,action='append',default=[]);parser.add_argument('--reference-only',action='store_true');parser.add_argument('--mesen-header',type=Path);parser.add_argument('--primary-c',type=Path);parser.add_argument('--working-source-pilot',action='store_true');args=parser.parse_args();run(args)

def run(args):
    out=args.out.resolve();require(not out.exists()and out.is_relative_to(ROOT/'.local'),'New private output required');out.mkdir(parents=True);compiler=Path(args.compiler).resolve();require(compiler.is_file(),'Compiler required')
    files=[Path(__file__),ROOT/'scripts/cd_timing_qualify.py',ROOT/'tests/geargrafx_cd_timing_probe.cpp',ROOT/'tests/cd_timing_probe.cpp',ROOT/'tests/cd_timing_math_probe.cpp',ROOT/'tests/mesen_cd_seek_probe.cpp',ROOT/'tests/geargrafx_sense_probe.cpp',ROOT/'tests/generate_scsi_fixture.py',ROOT/'tests/generate_cd_timing_fixture.py',ROOT/'tests/sense_probe_support.hpp',ROOT/'tests/reset_probe_support.hpp']
    files += [ROOT/'scripts'/name for name in('cdda_gap_reference.py','filtered_audio_reference.py','hucard_reference.py','mapper_reference.py')]
    bindings={'tools':{str(compiler):sha(compiler)},'authored_sources':{str(p):sha(p)for p in files}};report=dict(schema=1,result='incomplete',runtime_abi=ABI,oracle_commit=reference.COMMIT,scope=__doc__,commands=[],bindings=bindings,working_source_pilot=args.working_source_pilot,frozen_source_qualification=not args.working_source_pilot and not args.reference_only,
        primary_model_pin='7b9a70702d2f5422b924ee3cf7d42ff3ae5436ad',mesen_header_pin='b9fa69ddc6d0a331fb103fdb5eef6904305703c2')
    snapshot=out/'source-epoch';snapshot.mkdir();bindings['authored_snapshot']={}
    for p in files:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());bindings['authored_snapshot'][str(target)]=sha(target)
    report['profile_contract']=dict(original_gear='Original distance model for all cases, including fixed plan control labels',tool='Explicit selected profile from each plan case')
    try:
        f=out/'fixture';plan=fixture(f);bindings['fixtures']={str(p):sha(p)for p in f.rglob('*')if p.is_file()};gear=build_gear(args,out,report,bindings,compiler)
        vectors=math_vectors();raw=''.join(f'{a} {b}\n'for a,b in vectors);vectorfile=out/'math-input.txt';vectorfile.write_text(raw);cmd=[str(gear),'--math'];report['commands'].append(cmd);done=subprocess.run(cmd,input=raw,text=True,capture_output=True,timeout=60);(out/'math-gear.txt').write_text(done.stdout);(out/'math-gear.err').write_text(done.stderr);done.check_returncode();bindings.setdefault('raw_outputs',{}).update({str(p):sha(p)for p in(vectorfile,out/'math-gear.txt',out/'math-gear.err')});report['original_math_process']=dict(command=cmd,exit_code=done.returncode,input_sha256=sha(vectorfile),stdout_sha256=sha(out/'math-gear.txt'),stderr_sha256=sha(out/'math-gear.err'));rows=[list(map(int,line.split()))for line in done.stdout.splitlines()];require(len(rows)==len(vectors),'Original math vector count')
        for (a,b),row in zip(vectors,rows):require(row==[a,b,seek_ms(a,b),seek_ticks(a,b)],'Original floating/rational seek differs: '+str((a,b,row)))
        report['original_math_vectors']=len(vectors);report['original_math_exact']=True
        additional_math(args,out,report,bindings,compiler,vectors)
        if args.reference_only:report['result']='reference-only-pass'
        else:
            from pcerecomp.project import source_identity
            report['tool_revision']=subprocess.check_output(['git','-C',str(args.tool_source.resolve()),'rev-parse','HEAD'],text=True).strip()
            if not args.working_source_pilot:
                dirty=subprocess.check_output(['git','-C',str(args.tool_source.resolve()),'status','--porcelain','--untracked-files=normal','--','CMakeLists.txt','pcerecomp','runtime','cmake'],text=True);require(not dirty,'Frozen shared source requires a clean reviewed checkout')
            report['tool']=source_identity(args.tool_source.resolve());require(report['tool']==source_identity(ROOT),'Emitter and linked runtime source epochs differ')
            source=args.tool_source.resolve();tool_files=[source/'CMakeLists.txt',*sorted((source/'pcerecomp').glob('*.py')),*sorted((source/'runtime').rglob('*.cpp')),*sorted((source/'runtime').rglob('*.hpp')),*sorted((source/'cmake').glob('*.cmake'))];bindings['tool_sources']={str(p):sha(p)for p in tool_files}
            tool=build_tool(args,out,report,bindings,compiler,f)
            outputs={}
            for speed in(3,12):
                for tier,binary in(('gear',gear),('native',tool),('interpreter',tool)):
                    label=f's{speed}-{tier}';cap=out/(label+'-capture.json');work=out/(label+'-work.json');done=common.evidence([str(binary),str(plan),str(f/'authored.pce'),str(f/'disc.cue'),tier,str(speed),str(cap),str(work)],label,out,report,bindings,300);outputs[label]=dict(rows=[json.loads(line)for line in done.stdout.splitlines()],work=json.loads(work.read_text()),capture=str(cap)if tier!='gear'else None);bindings['raw_outputs'][str(work)]=sha(work)
                    if tier!='gear':
                        from pcerecomp.capture import load_capture
                        from generate_cd_timing_fixture import make_fixture
                        capture,_=load_capture(cap);snapshot,sites=make_fixture();known={pc:(opcode,address)for pc,opcode,address in sites}
                        require(capture['runtime_abi']==ABI and capture['complete']and capture['retired_instructions']==outputs[label]['work']['calls'],'Fresh actual port capture work differs')
                        for row in capture['observations']:
                            require(row['pc']in known and tuple(row['mpr'])==snapshot.mpr,'Unexpected source PC/MPR');opcode,address=known[row['pc']];length=1 if opcode==0xEA else 3;physical=[0x1f0000+(row['pc']&8191)+i for i in range(length)];require(row['physical']==physical and row['data']==[snapshot.memory[p]for p in physical],'Exact encoded source identity differs')
                            require((row['interpreted_hits']==0 if tier=='native'else row['native_hits']==0),'Unexpected guest execution tier')
                        bindings['raw_outputs'][str(cap)]=sha(cap);outputs[label]['executed_identities']=len(capture['observations'])
            report['outputs']=outputs
            from scripts.cd_timing_qualify import qualify
            report['qualification']=qualify(outputs);require(source_identity(args.tool_source.resolve())==report['tool'],'In-flight tool source changed');report['result']='pass'
    except BaseException as error:report['result']='fail';report['error']=repr(error);raise
    finally:
        reference.record_preservation(report,bindings);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in('commands','bindings','outputs','processes')},indent=2))

if __name__=='__main__':main()
