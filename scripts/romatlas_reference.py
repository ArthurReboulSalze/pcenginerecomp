"""Opt-in original RomAtlas decoder / original-core authored fetch comparison.

No image frontend, commercial bytes, CD emulation or toolkit execution occurs.
Original GPL source is built only in a private isolated executable. Cargo
metadata/build stay offline; every registry version/checksum must belong to
the pinned upstream lock, and unpacked dependency bytes are checked as well.
Known exact disagreements stay visible. Any new difference fails.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tomllib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcerecomp import isa
PIN='3d0d1393149491777626f5a8e4461f7c49b2d6df'
PREFIX='vendor/jgenesis-pce/'
CRATES=('cpu/huc6280-emu','common/jgenesis-common','common/jgenesis-proc-macros')
PCS=(0,0x1ffd,0x1ffe,0x1fff,0x7fff,0xfff9,0xfffe,0xffff)
MPRS=((0,1,2,3,4,5,6,7),(255,248,128,130,131,132,2,0),(255,)*8)
PATTERNS=((0,0,0,0,0,0),(0x80,0xff,0,0x7f,1,0x80),(0xff,)*6,(0x7f,0x80,0xff,0x12,0x34,0x56))

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def strict(raw):
    def pairs(rows):
        result={}
        for k,v in rows:
            require(k not in result,'Duplicate JSON key');result[k]=v
        return result
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda s:(_ for _ in()).throw(ValueError(s)))
    def finite(v):
        if type(v)is float:require(math.isfinite(v),'Nonfinite JSON number')
        if type(v)is dict:
            for child in v.values():finite(child)
        elif type(v)is list:
            for child in v:finite(child)
    finite(value);return value

def exact(a,b):
    if type(a)is not type(b):return False
    if type(a)is dict:return a.keys()==b.keys()and all(exact(a[k],b[k])for k in a)
    if type(a)is list:return len(a)==len(b)and all(exact(x,y)for x,y in zip(a,b))
    return a==b

def plans():
    records=[]
    def add(pc,data,mpr,phase='decode',tag='full'):
        records.append(dict(id=len(records)+1,pc=pc,bytes=list(data),mpr=list(mpr),phase=phase,tag=tag))
    for op in range(256):
        for pc in PCS:
            for mpr in MPRS:
                for pattern in PATTERNS:add(pc,(op,*pattern),mpr)
    for op in range(256):
        length=isa._LENGTH[isa._ROWS[op].split('.')[1]]
        for size in range(length):add(0xffff,(op,*PATTERNS[1])[:size],MPRS[1],tag='truncated')
    add(65536,(0xea,),MPRS[0],tag='invalid_pc')
    for pc in PCS:
        for mpr in MPRS:
            for data in ((0xea,),(0xa9,0x93),(0x4c,0x34,0x12),(0,0xA5)):
                add(pc,data,mpr,phase='cpu',tag='mapped_fetch')
    return records

def instruction(record):
    data=record['bytes'];pc=record['pc'];mpr=tuple(record['mpr'])
    return isa.decode(lambda address:data[(address-pc)&65535],pc,mpr)

def expected_instruction(record):
    ins=instruction(record);d=ins.data;name=ins.mnemonic.lower();mode=ins.mode;word=lambda i:d[i]|d[i+1]<<8
    refs=[];arg='';target=ins.target
    if name=='ill':name='illegal'
    elif name=='ina':name='inc';arg='a'
    elif name=='dea':name='dec';arg='a'
    elif mode=='acc':arg='a'
    elif mode=='imm':arg=f'#${d[1]:02x}'
    elif mode=='blk':
        arg=','.join(f'${word(i):04x}'for i in(1,3,5))
        refs=[dict(cpu_address=word(i),kind=kind,indirect=False,indexed=False,length=word(5))for i,kind in((1,'block_source'),(3,'block_destination'))]
    elif mode in('imz','izx','ima','imx'):
        absolute=mode in('ima','imx');address=word(2)if absolute else 0x2000+d[2]
        arg=f'#${d[1]:02x},'+(f'a:${address:04x}'if absolute else f'z:${d[2]:02x}')+(',x'if mode in('izx','imx')else'')
        refs=[dict(cpu_address=address,kind='memory',indirect=False,indexed=mode in('izx','imx'))]
    elif mode in('rel','zrl'):
        arg=(f'${d[1]:02x},'if mode=='zrl'else'')+f'${target:04x}'
        if mode=='zrl':refs.append(dict(cpu_address=0x2000+d[1],kind='memory',indirect=False,indexed=False))
        refs.append(dict(cpu_address=target,kind='control',indirect=False,indexed=False))
    elif mode in('zpg','zpx','zpy','idx','idy','zpi','abs','abx','aby','ind','iax'):
        address=word(1)if len(d)==3 else 0x2000+d[1]
        args={'zpg':f'${d[1]:02x}','zpx':f'${d[1]:02x},x','zpy':f'${d[1]:02x},y','idx':f'(${d[1]:02x},x)',
              'idy':f'(${d[1]:02x}),y','zpi':f'(${d[1]:02x})','abs':f'a:${address:04x}','abx':f'a:${address:04x},x',
              'aby':f'a:${address:04x},y','ind':f'(${address:04x})','iax':f'(${address:04x},x)'}
        arg=args[mode];refs=[dict(cpu_address=address,kind='control'if name in('jmp','jsr')else'memory',
                               indirect=mode in('idx','idy','zpi','ind','iax'),indexed=mode in('zpx','zpy','idx','idy','abx','aby','iax'))]
    terminal=name in('brk','rti','rts','jmp','bra','illegal')
    successors=[]if terminal else[ins.next_pc]
    if target is not None:successors.append(target)
    after=list(record['mpr'])
    if name=='tam':after=[None if d[1]&(1<<i)else value for i,value in enumerate(after)]
    text=name+(' '+arg if arg else'')
    assembly=None if name=='illegal'or(mode in('rel','zrl')and not -128<=target-(ins.pc+len(d))<=127)else text
    return dict(opcode=d[0],length=len(d),text=text,assembly=assembly,after=dict(mpr=after,sf2_bank=None),successors=successors,references=refs,terminal=terminal)

def expected_cpu(record):
    d=record['bytes'];pc=record['pc'];mpr=record['mpr'];address=lambda a:(mpr[(a&65535)>>13]<<13)|(a&8191)
    require(d and d[0]in(0xea,0xa9,0x4c,0),'Explicit authored original-core CPU opcode required')
    reads=[[address(pc+i),value]for i,value in enumerate(d)]
    writes=[];next_pc=(pc+len(d))&65535;s=255;a=0
    if d[0]==0x4c:next_pc=d[1]|d[2]<<8
    elif d[0]==0xa9:a=d[1]
    elif d[0]==0:
        reads.extend(([address(0xfff6),0x67],[address(0xfff7),0x45]));s=252
        writes=[[address(0x21ff),next_pc>>8],[address(0x21fe),next_pc&255],[address(0x21fd),0x14]];next_pc=0x4567
    return dict(pc=next_pc,a=a,s=s,reads=reads,writes=writes)

def compare(records,actual):
    require(len(records)==len(actual),'Exact original record extent')
    differences=[];matched=cpu_cases=0;opcode_set=set()
    for request,response in zip(records,actual):
        require(type(response)is dict and type(response.get('id'))is int and response['id']==request['id']and type(response.get('ok'))is bool,'Original response identity/types')
        if request['phase']=='cpu':
            require(response['ok']is True and set(response)=={'id','ok','cpu'},'Original authored CPU response')
            observed=dict(response['cpu']);operations=observed.pop('operations');require(type(operations)is int and 0<operations<=64,'Bounded actual CPU operations')
            require(exact(observed,expected_cpu(request)),'Unexpected original mapped fetch/BRK result at '+str(request['id']))
            decoded=instruction(request)
            require(exact(observed['reads'][:len(decoded.data)],[list(v)for v in zip(decoded.physical,decoded.data)]),'Toolkit physical fetch resolution differs from original core')
            cpu_cases+=1;continue
        if request['tag'] in('truncated','invalid_pc'):
            # BRK's original frontend length-one defect also accepts a lone opcode.
            known=request['pc']<=65535 and request['bytes']==[0]
            if known:
                expected=expected_instruction(dict(request,bytes=[0,0]));expected['length']=1
                require(exact(response,dict(id=request['id'],ok=True,instruction=expected)),'Known BRK truncation discrepancy changed')
                differences.append(dict(id=request['id'],opcode=0,kind='brk_missing_signature_accepted',reference_length=1,toolkit_length=2))
            else:
                message='missing opcode or PC exceeds 16 bits'if request['tag']=='invalid_pc'or not request['bytes']else'truncated HuC6280 instruction'
                require(exact(response,dict(id=request['id'],ok=False,error=message)),'Truncated/invalid original instruction error differs')
            continue
        require(response['ok']is True and set(response)=={'id','ok','instruction'},'Original decoder refused full authored bytes')
        expected=expected_instruction(request);observed=response['instruction'];opcode_set.add(request['bytes'][0])
        if request['bytes'][0]==0:
            require(expected['length']==2,'Expected toolkit BRK signature length changed')
            adjusted=dict(expected);adjusted['length']=1
            require(exact(observed,adjusted),'Unrecognized BRK difference')
            differences.append(dict(id=request['id'],opcode=0,kind='brk_signature_length',reference_length=1,toolkit_length=2))
        else:require(exact(observed,expected),'Unexpected original decoder difference at '+str(request['id'])+': '+str(observed)+' expected '+str(expected));matched+=1
    require(opcode_set==set(range(256)),'All256 encodings must be observed')
    counts={name:sum(d['kind']==name for d in differences)for name in sorted({d['kind']for d in differences})}
    return dict(decoder_full_matches=matched,known_exact_differences=differences,known_disagreement_counts=counts,original_core_fetch_cases=cpu_cases,all256_encodings_observed=True,
                physical_scope='Physical fetch/read/BRK-stack addresses are actual original huc6280-emu BusInterface callbacks. RomAtlas decode itself has no physical-address output; no ROM frontend or CD claim.')

def git_blob(checkout,name):
    raw=subprocess.check_output(['git','-C',str(checkout),'show',PIN+':'+name])
    blob=subprocess.check_output(['git','-C',str(checkout),'rev-parse',PIN+':'+name],text=True).strip()
    require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'Pinned Git blob differs '+name)
    return raw

def snapshot(checkout,out):
    files=['Cargo.lock','Cargo.toml','crates/romatlas-pce/src/decode.rs',PREFIX+'Cargo.toml',PREFIX+'LICENSE',PREFIX+'ROMATLAS.md']
    files+=subprocess.check_output(['git','-C',str(checkout),'ls-tree','-r','--name-only',PIN,*[PREFIX+c for c in CRATES]],text=True).splitlines()
    bindings={};saved={}
    for name in sorted(set(files)):
        raw=git_blob(checkout,name);path=out/'original'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        bindings[str(path)]=sha(path);saved[name]=path
    return saved,bindings

def run_command(command,label,out,report,stdin=None,env=None):
    report['commands'].append(list(map(str,command)))
    result=subprocess.run(list(map(str,command)),input=stdin,capture_output=True,timeout=600,env=env)
    (out/(label+'.stdout')).write_bytes(result.stdout);(out/(label+'.stderr')).write_bytes(result.stderr)
    report.setdefault('processes',[]).append(dict(label=label,returncode=result.returncode))
    require(result.returncode==0,label+' failed; original output retained')
    return result.stdout

def registry_binding(folder,expected):
    """Admit exact archived and unpacked bytes; no extractor or download."""
    archive=folder.parents[2]/'cache'/folder.parent.name/(folder.name+'.crate')
    require(sha(archive)==expected,'Original locked crate archive checksum differs')
    result={str(archive):expected};members=set();total=0
    with tarfile.open(archive,'r:gz')as tar:
        for entry in tar:
            if entry.isdir():continue
            require(entry.isfile()and not entry.issym()and not entry.islnk(),'Registry archive special file refused')
            name=Path(entry.name)
            require(name.parts[0]==folder.name and '..'not in name.parts and not name.is_absolute(),'Registry archive path refused')
            relative=Path(*name.parts[1:]);require(relative not in members,'Duplicate archived registry file');members.add(relative)
            total+=entry.size;require(total<=64*1024*1024,'Registry source package bound')
            data=tar.extractfile(entry).read();digest=hashlib.sha256(data).hexdigest()
            require(sha(folder/relative)==digest,'Unpacked registry source changed: '+str(relative));result[str(folder/relative)]=digest
    actual={p.relative_to(folder)for p in folder.rglob('*')if p.is_file()}
    require(actual-members<={Path('.cargo-ok'),Path('.cargo-checksum.json')},'Unadmitted extra registry source files')
    return result

def run(args):
    out=args.out.resolve();checkout=args.source.resolve()
    require(not out.exists()and out.is_relative_to(ROOT/'.local'),'Fresh private output directory required')
    out.mkdir(parents=True);report=dict(schema=1,result='incomplete',pin=PIN,commands=[],scope=__doc__,bindings={})
    try:
        # Keep rustup proxy basenames: resolving cargo.exe to rustup.exe changes
        # dispatch semantics. The actual toolchain/version is recorded below.
        cargo=Path(shutil.which(str(args.cargo))or'').absolute();rustc=Path(shutil.which('rustc')or'').absolute()
        require(cargo.is_file()and rustc.is_file(),'ExistingCargo/Rust required; no installation implicit')
        proxy=Path(shutil.which('rustup')or'').absolute()
        if proxy.is_file()and cargo.resolve()==proxy.resolve():
            cargo=Path(run_command([proxy,'which','cargo'],'actual-cargo',out,report).decode().strip())
            rustc=Path(run_command([proxy,'which','rustc'],'actual-rustc',out,report).decode().strip())
            require(cargo.is_file()and rustc.is_file(),'Existing actual Rust toolchain required')
        env=dict(os.environ,RUSTC=str(rustc),RUSTC_WRAPPER='',RUSTC_WORKSPACE_WRAPPER='')
        report['compiler_selection']=dict(rustc=str(rustc),wrappers_disabled=True)
        files,original=snapshot(checkout,out);report['bindings']['original_sources']=original
        authored=[Path(__file__),ROOT/'tests/romatlas_reference.rs',ROOT/'tests/test_romatlas_reference.py',ROOT/'pcerecomp/isa.py']
        report['bindings']['authored_and_toolkit_sources']={str(p):sha(p)for p in authored}
        report['bindings']['tools']={str(p):sha(p)for p in(cargo,rustc)}
        for tool in(cargo,rustc):run_command([tool,'--version'],tool.stem+'-version',out,report)
        version=run_command([rustc,'-vV'],'rustc-details',out,report).decode('utf-8')
        hosts=[line.removeprefix('host: ')for line in version.splitlines()if line.startswith('host: ')]
        require(len(hosts)==1,'Explicit actual Rust host target required');host=hosts[0]
        wrapper=out/'wrapper';wrapper.mkdir();src=wrapper/'src';src.mkdir()
        workspace=tomllib.loads(files[PREFIX+'Cargo.toml'].read_text());deps=workspace['workspace']['dependencies']
        lock=tomllib.loads(files['Cargo.lock'].read_text());versions={p['name']:p['version']for p in lock['package']}
        # Original whole crate manifests stay untouched. The authored root only
        # supplies their same inherited version/dependency/lint definitions.
        vendor=out/'compile-vendor';vendor.mkdir()
        compiled={}
        for crate in CRATES:
            for name,original_file in files.items():
                if name.startswith(PREFIX+crate+'/'):
                    target=vendor/Path(name).relative_to(PREFIX);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original_file.read_bytes());compiled[str(target)]=sha(target)
        report['bindings']['unchanged_original_crate_compile_sources']=compiled
        manifest='[workspace]\nresolver="3"\nmembers='+json.dumps(list(CRATES))+'\n[workspace.package]\nversion="0.13.0"\n[workspace.dependencies]\n'
        for name,value in deps.items():
            if isinstance(value,dict)and 'path'in value:value=dict(value,path=(vendor/value['path']).as_posix())
            if isinstance(value,str):manifest+=name+'='+json.dumps(value)+'\n'
            elif isinstance(value,dict):manifest+=name+'={'+','.join(k+'='+json.dumps(v)for k,v in value.items())+'}\n'
        manifest+='[workspace.lints.rust]\nrust_2018_idioms="warn"\n[workspace.lints.clippy]\nall={level="warn",priority=-1}\n'
        (vendor/'Cargo.toml').write_text(manifest,encoding='utf-8')
        manifest='[workspace]\nresolver="3"\n[package]\nname="pce-romatlas-reference"\nversion="0.0.0"\nedition="2024"\nlicense="GPL-3.0-only"\n[dependencies]\n'
        manifest+='anyhow="='+versions['anyhow']+'"\nserde={version="='+versions['serde']+'",features=["derive"]}\nserde_json="='+versions['serde_json']+'"\n'
        manifest+='huc6280-emu={path='+json.dumps((vendor/'cpu/huc6280-emu').as_posix())+',features=["test-apis"]}\n'
        (wrapper/'Cargo.toml').write_text(manifest,encoding='utf-8');(wrapper/'Cargo.lock').write_bytes(files['Cargo.lock'].read_bytes())
        main='#[path='+json.dumps(files['crates/romatlas-pce/src/decode.rs'].as_posix())+'] mod original_decode;\ninclude!('+json.dumps((ROOT/'tests/romatlas_reference.rs').as_posix())+');\n'
        (src/'main.rs').write_text(main,encoding='utf-8')
        metadata=run_command([cargo,'metadata','--offline','--filter-platform',host,'--manifest-path',wrapper/'Cargo.toml','--format-version','1'],'metadata',out,report,env=env)
        resolved=tomllib.loads((wrapper/'Cargo.lock').read_text());upstream={(p['name'],p['version'],p.get('source'),p.get('checksum'))for p in lock['package']}
        packages=json.loads(metadata)['packages'];registry={};host_packages=[]
        for p in resolved['package']:
            if 'source'in p:require((p['name'],p['version'],p['source'],p.get('checksum'))in upstream,'Dependency resolution outside exact original lock')
        for package in packages:
            if package['source']is None:continue
            folder=Path(package['manifest_path']).parent
            expected=next(p['checksum']for p in resolved['package']if p['name']==package['name']and p['version']==package['version']and 'checksum'in p)
            registry.update(registry_binding(folder,expected))
            host_packages.append(dict(name=package['name'],version=package['version'],checksum=expected,license=package['license']))
        report['bindings']['registry_sources']=registry
        report['locked_registry_packages']=[dict(name=p['name'],version=p['version'],source=p['source'],checksum=p['checksum'])for p in resolved['package']if 'source'in p]
        report['admitted_host_registry_packages']=host_packages;report['host_target']=host
        report['dependency_scope']='All51 locked versions/checksums remain within the original upstream lock; only host-resolved packages are archive/source-admitted and eligible for this host build. Non-host lock entries are not claimed downloaded, built or source-verified.'
        report['bindings']['wrapper']={str(p):sha(p)for p in(wrapper/'Cargo.toml',wrapper/'Cargo.lock',src/'main.rs',vendor/'Cargo.toml')}
        target=out/'target';run_command([cargo,'build','--offline','--locked','--release','--verbose','--manifest-path',wrapper/'Cargo.toml','--target-dir',target],'build',out,report,env=env)
        binary=target/'release'/('pce-romatlas-reference.exe'if os.name=='nt'else'pce-romatlas-reference');report['bindings']['binary']={str(binary):sha(binary)}
        records=plans();raw=b''.join((json.dumps({k:v for k,v in r.items()if k!='tag'},separators=(',',':'))+'\n').encode()for r in records)
        (out/'authored-input.jsonl').write_bytes(raw)
        report['bindings']['authored_inputs']={str(out/'authored-input.jsonl'):sha(out/'authored-input.jsonl')}
        observed=run_command([binary],'actual',out,report,stdin=raw);actual=[strict(line)for line in observed.splitlines()]
        report['bindings']['raw_command_outputs']={str(p):sha(p)for suffix in('*.stdout','*.stderr')for p in out.glob(suffix)}
        report.update(compare(records,actual),records=len(records),result='pass',unknown_differences=0,toolkit_instruction_retirements=dict(native=0,interpreted=0),
                      original_core_instruction_calls=sum(r['phase']=='cpu'for r in records))
    except Exception as error:report.update(result='fail',error=str(error));raise
    finally:
        flags={group:all(Path(p).is_file()and sha(p)==digest for p,digest in bindings.items())for group,bindings in report['bindings'].items()}
        report['preservation']=flags
        if not all(flags.values()):report['result']='failed-preservation'
        (out/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    require(report['result']=='pass','Source/artifact preservation failed')
    print(json.dumps({k:v for k,v in report.items()if k not in('commands','bindings','known_exact_differences','locked_registry_packages','admitted_host_registry_packages')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cargo',default='cargo')
    run(p.parse_args())
