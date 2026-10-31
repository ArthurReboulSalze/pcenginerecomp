"""Qualify authored CD decode holes and unused I/O against full original Gear.

This compiles the separately licensed original core without editing its source.
Explicit synthetic CPU/MPR/zero-RAM seeds are not hardware reset claims. All
accesses retire real indirect guest loads/stores. No retail inputs are needed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from pcerecomp.abi import ABI
from scripts import filtered_audio_reference as reference
from scripts import hucard_reference as common
from scripts.mapper_reference import pinned_snapshot, cmake_quote

sha = reference.sha
COMMIT = reference.COMMIT
MPR = (0, 248, 0, 0, 0, 255, 255, 0)


def plans():
    cases = []
    for profile in range(3):
        for fast in range(2):
            for alias in range(2):
                # Every decoded address, not only representative low nibbles.
                low = 0x1810 if profile < 2 else 0x1C00
                ops = [('r', profile, fast, alias), ('s',)]
                for offset in range(low, 0x2000):
                    ops.extend((('w', offset, (offset*13+71)&255), ('q', offset)))
                # Every byte at boundaries and common false port aliases.
                boundaries = (0x1810,0x1817,0x18FF,0x1901,0x1907,0x1A00,0x1BFF,0x1C00,0x1FFF) if profile < 2 else (0x1C00,0x1FFF)
                for offset in boundaries:
                    for value in range(256):
                        ops.extend((('w', offset, value), ('q', offset)))
                ops.append(('s',))
                cases.append(dict(id=f'holes-p{profile}-f{fast}-a{alias}', operations=ops))
                if profile < 2:
                    # Preserve real port behavior next to ignored aliases. No
                    # selection/streaming/sample-source timing in this proof.
                    ops = [('r',profile,fast,alias),('s',)]
                    for value in (0,0xA5,0x5A,255):
                        ops.extend((('w',0x1801,value),('q',0x1801),('w',0x1901,value^255),('q',0x1801)))
                    for value in (0,0x25,0x7F):
                        ops.extend((('w',0x1802,value),('q',0x1802),('w',0x1902,value^255),('q',0x1802)))
                    for value in (0,0xF9,0x04):
                        ops.extend((('w',0x1804,value),('q',0x1804),('w',0x1904,value^255),('q',0x1804)))
                    for value in (0,0x80,0x7F,255):
                        ops.extend((('w',0x1807,value),('q',0x1807),('w',0x1907,value^255),('q',0x1807)))
                    ops += [('q',0x18C0+i) for i in range(4)]
                    ops.append(('s',))
                    cases.append(dict(id=f'known-p{profile}-f{fast}-a{alias}',operations=ops))
    return cases


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value^byte)*1099511628211)&0xFFFFFFFFFFFFFFFF
    return value


def expected(cases):
    """Independent scalar model of the deliberately bounded port operations."""
    rows, hits = [], {0xE000:0,0xE002:0}
    for case in cases:
        for op in case['operations']:
            if op[0] == 'r':
                _,profile,fast,alias = op
                state = [0xE000,0,0,0,0,4,3 if fast else 12,0,*MPR,0,255]
                if profile < 2:
                    state += [1,0,0,0,0,0,0,0]
                ram = bytearray(8192)
                continue
            if op[0] == 's':
                rows.append(dict(kind='cpu',values=list(state)))
                memory = [fnv(ram)]
                if profile < 2: memory.append(fnv(bytes(2048)))
                rows.append(dict(kind='memory',values=memory))
                continue
            offset = op[1]
            address = (0xA000 if alias else 0xC000)|offset
            ram[16:18] = bytes((address&255,address>>8))
            if op[0] == 'w':
                value = op[2]
                state[0],state[1] = 0xE004,value
                if profile < 2:
                    if offset == 0x1801: state[24] = value
                    elif offset == 0x1802: state[20] = value&127
                    elif offset == 0x1804: state[19] = value&15
                    elif offset == 0x1807: state[18] = int(bool(value&128))
                hits[0xE002] += 1
            else:
                value = 255
                if profile < 2:
                    if offset == 0x1801: value = state[24]
                    elif offset == 0x1802: value = state[20]
                    elif offset == 0x1804: value = state[19]
                    elif offset == 0x1807: value = 128*state[18]
                    elif 0x18C0 <= offset <= 0x18C3 and profile == 1: value = (0,170,85,3)[offset&3]
                state[0],state[1] = 0xE002,value
                state[5] = (state[5]&~130)|(value&128)|(2 if value == 0 else 0)
                hits[0xE000] += 1
            state[7] += 7*state[6]
            rows.append(dict(kind='cpu',values=list(state)))
    return rows,hits


def validate_records(rows, wanted, tier):
    if len(rows) != len(wanted):
        raise ValueError(f'{tier} observation count differs: {len(rows)} vs {len(wanted)}')
    checks = 0
    for index,(actual, literal) in enumerate(zip(rows,wanted)):
        if actual != literal:
            raise ValueError(f'{tier} literal observation {index} differs: {actual}; expected {literal}')
        checks += len(literal['values'])
    return checks


def build_gear(args,out,report,bindings,compiler):
    source, source_hashes = pinned_snapshot(args.gear_source.resolve(),out,bindings)
    cpp,c = reference.compile_sources(source,source_hashes)
    cpp.append(ROOT/'tests/geargrafx_cd_decode_probe.cpp')
    deps = source/'platforms/shared/dependencies'
    flags = ['-O2','-ffp-contract=off','-ffunction-sections','-fdata-sections',
             '-DGG_DISABLE_DISASSEMBLER','-DGG_DISABLE_VGMRECORDER','-DGG_DISABLE_MMI_THREADS']
    for path in (source/'src',ROOT/'tests',deps/'miniz',deps/'libchdr/include',deps/'minivorbis',deps/'json'):
        flags += ['-I',str(path)]
    objects = out/'gear-objects';objects.mkdir()
    jobs = []
    for index,path in enumerate(cpp+c):
        obj = objects/(str(index)+'-'+path.stem+'.o')
        command = [str(compiler),*flags,'-x','c++' if path.suffix == '.cpp' else 'c',
                   *(['-std=c++20','-include','cerrno'] if path.suffix == '.cpp' else ['-std=c11']),
                   '-c',str(path),'-o',str(obj)]
        jobs.append((command,obj));report['commands'].append(command)
    def compile_one(job):
        command,obj = job
        result = subprocess.run(command,capture_output=True,text=True,timeout=180)
        obj.with_suffix('.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        result.check_returncode()
    with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(compile_one,jobs))
    libraries = [p.resolve() for p in args.library]
    if not libraries or any(not p.is_file() for p in libraries):
        raise ValueError('Supply existing external static libraries explicitly')
    bindings['external_libraries'] = {str(p):sha(p) for p in libraries}
    binary = out/'gear-cd-decode.exe'
    common.evidence([str(compiler),*[str(p) for _,p in jobs],*map(str,libraries),'-Wl,--gc-sections','-o',str(binary)],
                    'gear-link',out,report,bindings)
    bindings['gear_objects'] = {str(p):sha(p) for _,p in jobs}
    bindings['gear_binary'] = {str(binary):sha(binary)}
    return binary


def build_tool(args,out,report,bindings,compiler,fixture):
    tool = args.tool_source.resolve()
    cmake,ninja = (Path(shutil.which(str(v)) or '').resolve() for v in (args.cmake,args.ninja))
    if not cmake.is_file() or not ninja.is_file(): raise ValueError('Require CMake and Ninja')
    bindings['tools'].update({str(p):sha(p) for p in (cmake,ninja)})
    wrapper = out/'tool-wrapper';wrapper.mkdir()
    q = cmake_quote
    lines = ['cmake_minimum_required(VERSION 3.20)','project(AuthoredCDDecode LANGUAGES CXX)',
             *['set('+option+' OFF CACHE BOOL "" FORCE)' for option in
               ('PCE_BUILD_TOOLS','PCE_BUILD_TESTS','PCE_BUILD_DESKTOP','PCE_BUILD_REFERENCE_PROBE','BUILD_TESTING')],
             f'add_subdirectory({q(tool)} tool)',
             f'pce_add_native_module(_module MODULE {q(fixture/"module.cpp")} MANIFEST {q(fixture/"module.json")})',
             f'add_executable(cd-decode-probe {q(ROOT/"tests/cd_decode_oracle_probe.cpp")})',
             f'target_include_directories(cd-decode-probe PRIVATE {q(fixture)})',
             'target_link_libraries(cd-decode-probe PRIVATE ${_module} pce-runtime)']
    config = wrapper/'CMakeLists.txt';config.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    bindings['tool_build_inputs'] = {str(config):sha(config)}
    build = out/'tool-build'
    common.evidence([str(cmake),'-S',str(wrapper),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
                     '-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_MAKE_PROGRAM='+str(ninja)],'tool-configure',out,report,bindings)
    common.evidence([str(cmake),'--build',str(build),'--target','cd-decode-probe','--parallel','4'],
                    'tool-build',out,report,bindings,600)
    binary = build/('cd-decode-probe.exe' if os.name == 'nt' else 'cd-decode-probe')
    bindings['tool_build_artifacts'] = {str(p):sha(p) for p in build.rglob('*') if p.is_file() and
        (p.suffix in ('.obj','.o','.a') or p.name in ('CMakeCache.txt','build.ninja','rules.ninja','.ninja_log'))}
    bindings['tool_binary'] = {str(binary):sha(binary)}
    return binary


def validate_capture(capture,hits,native):
    total = sum(hits.values())
    if capture.get('schema') != 1 or capture.get('runtime_abi') != ABI or capture.get('complete') is not True or \
       capture.get('retired_instructions') != total or capture.get('dropped_instructions') != 0 or capture.get('unreadable_instructions') != 0:
        raise ValueError('Capture incomplete, wrong ABI or wrong actual retirement total')
    wanted = []
    for pc in sorted(hits):
        physical = pc&8191
        wanted.append(dict(pc=pc,mpr=list(MPR),physical=[physical,physical+1],
                           data=[178 if pc == 0xE000 else 146,16],
                           native_hits=hits[pc] if native else 0,interpreted_hits=0 if native else hits[pc]))
    if capture.get('observations') != wanted: raise ValueError('Full source bytes/mapping/physical identities or per-key actual hits differ')


def run(args):
    tool,out = args.tool_source.resolve(),args.out.resolve()
    compiler = Path(shutil.which(str(args.compiler)) or '').resolve()
    if out.exists() or not out.is_relative_to(ROOT/'.local') or not compiler.is_file():
        raise ValueError('Require compiler and a NEW private .local output directory')
    sys.path.insert(0,str(tool))
    from pcerecomp.project import source_identity
    import pcerecomp.project
    if Path(pcerecomp.project.__file__).resolve() != tool/'pcerecomp/project.py':
        raise ValueError('Selected toolkit package identity differs')
    sources = [Path(__file__),ROOT/'scripts/mapper_reference.py',ROOT/'scripts/filtered_audio_reference.py',
               ROOT/'scripts/hucard_reference.py',ROOT/'scripts/psg_reference.py',
               *[ROOT/'tests'/name for name in ('geargrafx_cd_decode_probe.cpp','geargrafx_reset_probe.cpp',
                 'reset_probe_support.hpp','hucard_fixture.py','generate_cd_decode_fixture.py','cd_decode_tests.cpp','cd_decode_oracle_probe.cpp')],
               *sorted((tool/'runtime').rglob('*.cpp')),*sorted((tool/'runtime').rglob('*.hpp')),
               *sorted((tool/'pcerecomp').glob('*.py')),tool/'CMakeLists.txt',*sorted((tool/'cmake').glob('*.cmake'))]
    bindings = dict(tools={str(compiler):sha(compiler)},authored_sources={str(p.resolve()):sha(p) for p in sources})
    report = dict(schema=1,result='incomplete',oracle_commit=COMMIT,commands=[],bindings=bindings,
                  scope='Authored exact Standard/Super CD decode and base HuCard unused I/O; synthetic zero RAM/register seed; actual indirect CPU operations',
                  not_checked=['Physical hardware','Electrical open bus','Retail software','Arcade/LaserActive extensions',
                               'ADPCM/CDDA sample or streaming timing','All known-port data combinations','Hardware reset parity',
                               'Mesen or Beetle CD execution'])
    out.mkdir(parents=True)
    try:
        from generate_cd_decode_fixture import generate
        fixture = out/'fixture';generate(fixture)
        cases = plans();wanted,hits = expected(cases)
        plan = out/'decode.plan';plan.write_text('\n'.join(' '.join(map(str,op)) for case in cases for op in case['operations'])+'\n',encoding='ascii')
        cases_path = out/'cases.json';cases_path.write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
        sectors = out/'authored-sectors.bin';sectors.write_bytes(bytes(2048*16))
        cue = out/'authored.cue';cue.write_text('FILE "authored-sectors.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n',encoding='ascii')
        bindings['authored_fixtures'] = {str(p):sha(p) for p in [plan,cases_path,sectors,cue,*fixture.iterdir()] if p.is_file()}
        gear = build_gear(args,out,report,bindings,compiler)
        tool_probe = build_tool(args,out,report,bindings,compiler,fixture)
        literal = {}
        result = common.evidence([str(gear),str(plan),str(fixture/'authored.pce'),str(cue)],'gear',out,report,bindings,180)
        oracle = json.loads(result.stdout)
        literal['gear'] = validate_records(oracle,wanted,'gear')
        totals = {}
        for tier in ('interpreter','native'):
            capture,execution = out/(tier+'-capture.json'),out/(tier+'-execution.json')
            raw = common.evidence([str(tool_probe),str(plan),tier,str(capture),str(execution)],tier,out,report,bindings,180)
            rows = json.loads(raw.stdout)
            literal[tier] = validate_records(rows,wanted,tier)
            if rows != oracle: raise ValueError(tier+' full original Gear comparison differs')
            work = json.loads(execution.read_text())
            if work.get('native_steps') != (sum(hits.values()) if tier == 'native' else 0) or \
               work.get('interpreted_steps') != (0 if tier == 'native' else sum(hits.values())) or \
               work.get('pure_guards') != 4 or work.get('records') != len(wanted) or work.get('cases') != len(cases):
                raise ValueError(tier+' actual work/guard/record accounting differs')
            validate_capture(json.loads(capture.read_text()),hits,tier == 'native')
            bindings['raw_outputs'].update({str(p):sha(p) for p in (capture,execution)})
            totals[tier] = work
        report.update(result='pass',tool=source_identity(tool),cases=len(cases),observations=len(wanted),
                      independent_literal_checks=literal,actual_work=totals,source_identities=2,
                      read_instructions=hits[0xE000],write_instructions=hits[0xE002],
                      source_comparison='Complete logical PC, full MPR, physical source bytes and exact per-key tier hits; no projection')
    except Exception as error:
        report.update(result='fail',error=str(error));raise
    finally:
        reference.record_preservation(report,bindings)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if report['result'] != 'pass': raise ValueError('Reference inputs changed during proof')
    print(json.dumps({k:v for k,v in report.items() if k not in ('bindings','commands')},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gear-source',type=Path,required=True)
    parser.add_argument('--tool-source',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compiler',default='clang++')
    parser.add_argument('--cmake',default='cmake')
    parser.add_argument('--ninja',default='ninja')
    parser.add_argument('--library',type=Path,action='append',default=[])
    try: run(parser.parse_args())
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError) as error:
        print(error,file=sys.stderr);raise SystemExit(1)
