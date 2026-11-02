"""Isolated original Gear/Beetle captured-Q decoding and latch comparison.

The complete GPL translation units remain private, unmodified build inputs;
they are never linked to the toolkit. This checks raw96 bit lanes, CRC/ADR
admission, retained Q and DD payload construction. It is not a guest trace,
drive timing, byte FIFO/IRQ, hardware, retail or checkpoint qualification.
"""
import argparse
import binascii
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import sense_reference as shared
from scripts import mapper_reference as infrastructure
from scripts import hucard_reference as common
from scripts import filtered_audio_reference as preservation

BEETLE=shared.BEETLE
GEAR=infrastructure.COMMIT
sha=preservation.sha


def packet(payload):
    if type(payload)is not bytes or len(payload)!=10:raise ValueError('Ten authored Q bytes required')
    return payload+(binascii.crc_hqx(payload,0)^0xffff).to_bytes(2,'big')


def raw96(q,noise=0):
    if len(q)!=12:raise ValueError('Twelve Q bytes required')
    return bytes(((q[i//8]>>(7-i%8))&1)*64|((noise+i*29)&0xbf)for i in range(96))


def extract(raw):
    if type(raw)is not bytes or len(raw)!=96:raise ValueError('Exactly96bytes required')
    return bytes(sum(((raw[i*8+b]>>6)&1)<<(7-b)for b in range(8))for i in range(12))


def valid(q):return len(q)==12 and packet(q[:10])==q


def plans():
    rows=[('r',)]
    # Literal independent empty CRC: initial 0 complemented gives FF FF.
    rows.append(('q',0,raw96(bytes(10)+b'\xff\xff',0x9d)))
    rows.append(('q',0,bytes(96)))
    for adr in range(16):
        q=packet(bytes((0x40|adr,0x12,0,0x03,0x45,0x67,0,0x12,0x34,0x56)))
        rows.extend(('q',status,raw96(q,adr*13))for status in range(3))
        # Every individual checksum bit is independently corrupted.
        for bit in range(16):
            broken=q[:10]+(int.from_bytes(q[10:],'big')^(1<<bit)).to_bytes(2,'big')
            rows.append(('q',bit%3,raw96(broken,bit)))
    for track,index in ((1,1),(0xAA,1),(0x09,0),(0x99,0x99)):
        q=packet(bytes((0x01,track,index,0x99,0x59,0x74,0,0x99,0x59,0x74)))
        rows.extend((('q',2,raw96(q,0xff)),('q',1,bytes(96))))
    rows.extend((('r',),('q',0,bytes(96))))
    return rows


def expected(rows):
    last=position=bytes(12);gear=[];beetle=[]
    for op in rows:
        if op[0]=='r':last=position=bytes(12);continue
        _,status,raw=op;q=extract(raw);ok=valid(q)
        accepted=q if ok and q[0]&15==1 else raw[12:24]
        gok=valid(accepted)and accepted[0]&15==1
        gear.append([int(gok),*(accepted if gok else b'')])
        if ok:
            last=q
            if q[0]&15==1:position=q
        response=bytes(((3,2,0)[status],0))+position[1:6]+position[7:10]
        beetle.append([int(ok),*q,*last,*position,*response])
    return gear,beetle


def copy_git(repository,revision,name,target,bindings):
    raw=subprocess.check_output(['git','-C',str(repository),'show',revision+':'+name])
    blob=subprocess.check_output(['git','-C',str(repository),'rev-parse',revision+':'+name],text=True).strip()
    actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if actual!=blob:raise ValueError('Original Git blob mismatch '+name)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    bindings.setdefault('original_compile_sources',{})[str(target)]=sha(target)


def build(args,out,report,bindings,compiler):
    gear,sources=infrastructure.pinned_snapshot(args.gear_source.resolve(),out,bindings)
    flags=['-std=c++20','-O2','-ffunction-sections','-fdata-sections']
    deps=gear/'platforms/shared/dependencies'
    gobj=out/'gear.o';gbin=out/'gear-subchannel.exe'
    command=[str(compiler),*flags,'-DGG_DISABLE_MMI_THREADS']
    for inc in (gear/'src',deps/'miniz',deps/'json',deps/'qon',deps/'minivorbis',deps/'libchdr/include'):
        command+=['-I',str(inc)]
    common.evidence([*command,'-c',str(ROOT/'tests/geargrafx_subchannel_reference.cpp'),'-o',str(gobj)],'gear-compile',out,report,bindings)
    cpp,c=preservation.compile_sources(gear,sources)
    objects=out/'gear-objects';objects.mkdir();jobs=[]
    for index,path in enumerate([p for p in cpp if p.name!='cdrom_mmi_image.cpp']+c):
        obj=objects/(str(index)+'.o')
        cmd=[*command,'-x','c++'if path.suffix=='.cpp'else'c']
        if path.suffix=='.c':cmd=[x for x in cmd if x!='-std=c++20']+['-std=c11']
        else:cmd+=['-include','cerrno']
        jobs.append((cmd+['-c',str(path),'-o',str(obj)],obj))
    def compile_one(job):
        cmd,obj=job;done=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        obj.with_suffix('.log').write_text(done.stdout+done.stderr);done.check_returncode()
    report['commands'].extend(cmd for cmd,_ in jobs)
    with ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(compile_one,jobs))
    libraries=[p.resolve()for p in args.library]
    if not libraries or any(not p.is_file()for p in libraries):raise ValueError('Explicit original Gear external libraries required')
    bindings['external_libraries']={str(p):sha(p)for p in libraries}
    bindings['gear_objects']={str(p):sha(p)for _,p in jobs}
    common.evidence([str(compiler),str(gobj),*[str(p)for _,p in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(gbin)],'gear-link',out,report,bindings)
    folder=out/'beetle';source=folder/'src';cd=source/'cdrom'
    for name in [*shared.BEETLE_FILES,*['mednafen/cdrom/'+n for n in ('CDUtility.cpp','dvdisaster.h','lec.h')]]:
        copy_git(args.beetle_source.resolve(),BEETLE,name,source/Path(name).relative_to('mednafen'),bindings)
    (folder/'compat').mkdir()
    authored={folder/'forced.hpp':shared.FORCED,cd/'cdromif.h':shared.MEDIA_HEADER,
              source/'state.h':shared.STATE_HEADER,source/'mednafen.h':'#pragma once\n#include "../forced.hpp"\n',folder/'compat/msvc.h':'#pragma once\n'}
    for file,value in authored.items():file.write_text(value,encoding='utf-8')
    bindings['authored_reference_framework']={str(p):sha(p)for p in authored}
    bobj=folder/'beetle.o';bbin=folder/'beetle-subchannel.exe'
    common.evidence([str(compiler),*flags,'-I',str(folder),'-I',str(cd),'-include',str(folder/'forced.hpp'),'-c',str(ROOT/'tests/beetle_subchannel_reference.cpp'),'-o',str(bobj)],'beetle-compile',out,report,bindings)
    common.evidence([str(compiler),str(bobj),'-Wl,--gc-sections','-o',str(bbin)],'beetle-link',out,report,bindings)
    bindings['original_build_artifacts']={str(p):sha(p)for p in(gobj,gbin,bobj,bbin)}
    return gbin,bbin


def run(args):
    out=args.out.resolve();compiler=Path(shutil.which(str(args.compiler))or'').resolve()
    if out.exists()or not out.is_relative_to(ROOT/'.local')or not compiler.is_file():raise ValueError('Fresh private output and actual compiler required')
    out.mkdir(parents=True)
    authored=[Path(__file__),ROOT/'tests/geargrafx_subchannel_reference.cpp',ROOT/'tests/beetle_subchannel_reference.cpp',
              ROOT/'tests/toolkit_subchannel_reference.cpp',
              *[ROOT/'scripts'/n for n in ('sense_reference.py','mapper_reference.py','filtered_audio_reference.py','psg_reference.py','hucard_reference.py')]]
    bindings={'tools':{str(compiler):sha(compiler)},'authored_sources':{str(p):sha(p)for p in authored}}
    tool_identity=None
    if args.probe:
        from pcerecomp.project import source_identity
        tool_identity=source_identity(ROOT)
        inputs=[ROOT/'CMakeLists.txt',*sorted((ROOT/'runtime').rglob('*.cpp')),
                *sorted((ROOT/'runtime').rglob('*.hpp')),*sorted((ROOT/'runtime').rglob('*.h')),
                *sorted((ROOT/'pcerecomp').glob('*.py')),*sorted((ROOT/'cmake').glob('*.cmake'))]
        bindings['toolkit_source_epoch']={str(p):sha(p)for p in inputs}
    report=dict(schema=1,result='incomplete',scope=__doc__,gear_commit=GEAR,beetle_commit=BEETLE,commands=[],bindings=bindings,
                differences=['Gear MMI requires ADR1 and attempts alternate channel-major format; captured profile contract is explicit raw96 only',
                             'Gear MMI decoder has no retained ADR1 state; Beetle retains last valid Q separately from last valid ADR1',
                             'Gear synthesized/DD byte1 carries control/ADR; Beetle DD byte1 is zero'],
                not_checked=['Hardware','Drive/CPU/access-phase timing','1807 byte FIFO/IRQ','Original Gear full DD command handshake','Retail media','Guest execution','Checkpoint restoration'])
    try:
        rows=plans();plan=out/'authored.plan'
        plan.write_text('\n'.join(op[0]if op[0]=='r'else' '.join(map(str,(op[0],op[1],*op[2])))for op in rows)+'\n',encoding='ascii')
        bindings['authored_fixtures']={str(plan):sha(plan)};wanted=expected(rows)
        bins=build(args,out,report,bindings,compiler)
        for label,binary,expect in zip(('gear','beetle'),bins,wanted):
            actual=common.evidence([str(binary),str(plan)],label,out,report,bindings)
            shared.validate_rows(json.loads(actual.stdout),expect)
        if args.probe:
            probe=args.probe.resolve()
            if not probe.is_file():raise ValueError('Actual toolkit probe required')
            bindings['toolkit_probe']={str(probe):sha(probe)}
            actual=common.evidence([str(probe),str(plan)],'toolkit',out,report,bindings)
            shared.validate_rows(json.loads(actual.stdout),wanted[1])
            report['toolkit_records']=len(wanted[1])
            if source_identity(ROOT)!=tool_identity:raise ValueError('Toolkit source identity changed during comparison')
            report['toolkit_source_identity']=tool_identity
        report.update(result='pass',records=len(wanted[0]),valid_crc_records=sum(row[0]for row in wanted[1]),gear_adr1_admitted=sum(row[0]for row in wanted[0]))
    except Exception as error:report.update(result='fail',error=str(error));raise
    finally:
        preservation.record_preservation(report,bindings)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if report['result']!='pass':raise ValueError('Reference input preservation failed')
    print(json.dumps({k:v for k,v in report.items()if k not in('bindings','commands')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gear-source',type=Path,required=True);p.add_argument('--beetle-source',type=Path,required=True)
    p.add_argument('--compiler',default='clang++');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--library',type=Path,action='append',default=[])
    p.add_argument('--probe',type=Path)
    run(p.parse_args())
