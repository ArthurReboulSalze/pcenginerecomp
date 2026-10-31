"""Authored unknown-CDB framing against separately compiled original cores.

Settled protocol, retained raw ACK observations and NEC sense are separate
from autonomous toolkit guest/native work. No retail, hardware, exact access
phase, physical latency or cross-core CPU execution parity is established.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from scripts import sense_reference as sense
from scripts import hucard_reference as common
from scripts import mapper_reference as infrastructure
from scripts import filtered_audio_reference as reference
sha = reference.sha
SUPPORTED = frozenset((0, 3, 8, 0xD8, 0xD9, 0xDA, 0xDD, 0xDE))
LENGTHS = (6, 6, 10, 10, 10, 10, 10, 10, 10, 10, 12, 12, 10, 10, 10, 10)


def command(op, automatic=0):
    return ('c', automatic, 6, op, 0, 0, 0, 18 if op == 3 else 0, 0)


def plans(profile):
    if profile not in ('gear', 'beetle', 'tool-nec', 'tool-gear'):
        raise ValueError('Unknown reference domain')
    nec = profile in ('beetle', 'tool-nec')
    cases = []
    for op in range(256):
        if op in SUPPORTED:
            continue
        ops = [('r', 1), ('u', op, LENGTHS[op >> 4] if nec else 1, op % 2)]
        if nec:
            ops += [('p',), command(3, op % 2), ('p',), command(3, 1 - op % 2), ('p',)]
        ops += [command(0)]
        cases.append(dict(id='opcode-%02x' % op, operations=ops))
    for op in (1, 0x20, 0xA0, 0xFF):
        ops = [('r', 1), ('a', op, 0, 0), command(0)]
        if nec:
            ops += [('a', op, LENGTHS[op >> 4] - 1, 0), ('r', 1), command(0),
                    ('u', op, LENGTHS[op >> 4], 0), ('p',), ('z',), ('p',),
                    command(0), ('p',), command(3, 1), ('p',)]
        else:
            ops += [('u', op, 1, 0), ('z',), command(0), command(3, 1)]
        cases.append(dict(id='abort-lifetime-%02x' % op, operations=ops))
    return cases


def serialize(cases):
    return ''.join(' '.join(map(str, op)) + '\n' for c in cases for op in c['operations'])


def expected(cases, profile):
    if profile not in ('gear', 'beetle', 'tool-nec', 'tool-gear'):
        raise ValueError('Unknown reference domain')
    nec = profile in ('beetle', 'tool-nec')
    error_status, error_message = (1, 0) if profile == 'beetle' else (2, 2)
    pending = [0, 0, 0, 0]
    rows = []
    for case in cases:
        for op in case['operations']:
            if op[0] == 'r':
                pending = [0, 0, 0, 0]
            elif op[0] == 'u':
                _, code, count, automatic = op
                rows.append(dict(kind='unknown', opcode=code, count=count, automatic=automatic,
                                 status=error_status if nec else 0,
                                 message=error_message if nec else 0, data=[]))
                if nec:
                    pending = [5, 0x20, 0, 0]
            elif op[0] == 'p':
                rows.append(dict(kind='pending', values=pending[:]))
            elif op[0] == 'z':
                rows.append(dict(kind='reset'))
            elif op[0] == 'a':
                row = dict(kind='abort', opcode=op[1], count=op[2])
                if nec:
                    row.update(buffered_before_reset=op[2], buffered_after_reset=op[2] if profile == 'beetle' else 0)
                elif profile == 'tool-gear':
                    row.update(buffered_before_reset=0, buffered_after_reset=0)
                rows.append(row)
            elif op[0] == 'c':
                _, automatic, _, code, *tail = op
                data = sense.sense_bytes(pending) if code == 3 and profile != 'gear' else []
                if code == 3 and profile != 'gear':
                    pending = [0, 0, 0, 0]
                rows.append(dict(kind='reply', automatic=automatic, cdb=[code, *tail],
                                 data=data, status=0, message=0))
            else:
                raise ValueError('Unauthored operation')
    return rows


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in b)
    if type(a) is list:
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def require_preservation(report, bindings):
    reference.record_preservation(report, bindings)
    flags = report.get('preservation')
    if type(flags) is not dict or not flags or any(value is not True for value in flags.values()):
        raise ValueError('A bound source, tool, fixture or artifact changed during qualification')


def validate_rows(rows, wanted):
    if type(rows) is not list or len(rows) != len(wanted):
        raise ValueError('Unknown-CDB record count differs')
    for index, (actual, expected_row) in enumerate(zip(rows, wanted)):
        extra = {'pins', 'edges'} if expected_row['kind'] in ('unknown', 'abort') else {'pins'} if expected_row['kind'] == 'reset' else set()
        if type(actual) is not dict or actual.keys() != expected_row.keys() | extra:
            raise ValueError('Unknown-CDB record shape at ' + str(index))
        if not strict_equal({k: actual[k] for k in expected_row}, expected_row):
            raise ValueError('Unknown-CDB literal/type mismatch at ' + str(index))
        if extra:
            pins = actual['pins']
            if type(pins) is not list or len(pins) != 5 or any(type(v) is not int or v not in (0, 1) for v in pins) or pins[0]:
                raise ValueError('Bus did not return free')
        if 'edges' in extra:
            edges = actual['edges']
            if type(edges) is not list or len(edges) != actual['count']:
                raise ValueError('CDB edge count differs')
            for n, edge in enumerate(edges):
                if type(edge) is not list or len(edge) != 20 or any(type(v) is not int or v not in (0, 1) for v in edge):
                    raise ValueError('Raw ACK edge shape')
                if edge[:15] != [1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0]:
                    raise ValueError('Command direction or held ACK changed before falling edge')
                if not edge[15] or (n + 1 < len(edges) and edge[17:] != [0, 1, 0]):
                    raise ValueError('Partial CDB dispatched before full length')
    return rows


def firmware():
    code = bytearray()
    def emit(*v): code.extend(v)
    def store(address, value): emit(0xA9, value, 0x8D, address & 255, address >> 8)
    def wait(mask, wanted):
        at = len(code); emit(0xAD, 0, 0x18, 0x29, mask, 0xC9, wanted, 0xD0, 0)
        code[-1] = (at - len(code)) & 255
    def ack(): store(0x1802, 128); store(0x1802, 128); store(0x1802, 0)
    def read_to(offset): wait(64, 64); emit(0xAD, 1, 0x18, 0x8D, offset, 0x20); ack()
    emit(0x78, 0xA9, 255, 0x53, 1, 0xA9, 248, 0x53, 2)
    commands = [([255] * 10, 0, 0x50), ([3, 0, 0, 0, 18, 0], 18, 0x52),
                ([3, 0, 0, 0, 18, 0], 18, 0x54), ([0] * 6, 0, 0x56)]
    for number, (cdb, size, status) in enumerate(commands):
        store(0x1800, 0)
        for byte in cdb: wait(64, 64); store(0x1801, byte); ack()
        for i in range(size): read_to(i + (0x20 if number == 2 else 0))
        read_to(status); read_to(status + 1); wait(128, 0)
    end = 0xE100 + len(code); emit(0x80, 0xFE)
    if end >= 0xFF00:
        raise ValueError('Authored firmware bound')
    image = bytearray([0xEA] * 262144); image[256:256 + len(code)] = code
    image[8190:8192] = bytes((0, 0xE1))
    return bytes(image), end


def guest_plan():
    offsets = [*range(18), *range(0x20, 0x32), *range(0x50, 0x58)]
    return [dict(id='autonomous-invalid-sense-clear-ready', operations=[('r', 1), ('g', firmware()[1]), *[('k', n) for n in offsets], ('p',)])]


def validate_guest(rows):
    if type(rows) is not list or len(rows) != 46:
        raise ValueError('Autonomous guest record count')
    first = rows[0]
    if type(first) is not dict or set(first) != {'kind', 'values'} or first['kind'] != 'guest':
        raise ValueError('Autonomous guest CPU shape')
    cpu = first['values']
    if type(cpu) is not list or len(cpu) != 21 or any(type(v) is not int or v < 0 for v in cpu):
        raise ValueError('Autonomous guest CPU type')
    if cpu[0] != firmware()[1] or cpu[8:16] != [255, 248, 0, 0, 0, 0, 0, 0] or not 0 < cpu[16] <= 200000 or cpu[17:] != [2, 1, 1, 0]:
        raise ValueError('Autonomous guest execution/counter endpoint')
    wanted = [dict(kind='ram', values=[n, v]) for n, v in enumerate(sense.sense_bytes([5, 32, 0, 0]))]
    wanted += [dict(kind='ram', values=[0x20 + n, v]) for n, v in enumerate(sense.sense_bytes([0, 0, 0, 0]))]
    wanted += [dict(kind='ram', values=[n, v]) for n, v in zip(range(0x50, 0x58), [2, 2, 0, 0, 0, 0, 0, 0])]
    wanted += [dict(kind='pending', values=[0, 0, 0, 0])]
    if not strict_equal(rows[1:], wanted):
        raise ValueError('Autonomous guest literal RAM/sense result')
    return cpu[16]


def build_gear(args, out, report, bindings, compiler):
    checkout, source = infrastructure.pinned_snapshot(args.gear_source.resolve(), out, bindings)
    cpp, c = reference.compile_sources(checkout, source)
    cpp.append(ROOT / 'tests/geargrafx_cd_unknown_probe.cpp')
    deps = checkout / 'platforms/shared/dependencies'
    flags = ['-O2', '-ffp-contract=off', '-ffunction-sections', '-fdata-sections', '-DGG_DISABLE_DISASSEMBLER', '-DGG_DISABLE_VGMRECORDER', '-DGG_DISABLE_MMI_THREADS']
    for directory in (checkout / 'src', ROOT / 'tests', deps / 'miniz', deps / 'libchdr/include', deps / 'minivorbis', deps / 'json'):
        flags += ['-I', str(directory)]
    objects = out / 'objects'; objects.mkdir(); jobs = []
    for index, path in enumerate(cpp + c):
        obj = objects / (str(index) + '-' + path.stem + '.o')
        command = [str(compiler), *flags, '-x', 'c++' if path.suffix == '.cpp' else 'c', *(['-std=c++20', '-include', 'cerrno'] if path.suffix == '.cpp' else ['-std=c11']), '-c', str(path), '-o', str(obj)]
        jobs.append((command, obj)); report['commands'].append(command)
    def compile_one(job):
        command, obj = job; r = subprocess.run(command, capture_output=True, text=True, timeout=180)
        obj.with_suffix('.log').write_text(r.stdout + r.stderr); r.check_returncode()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(compile_one, jobs))
    libraries = [p.resolve() for p in args.library]
    if not libraries or any(not p.is_file() for p in libraries):
        raise ValueError('Explicit existing Gear external libraries required')
    bindings['external_libraries'] = {str(p): sha(p) for p in libraries}
    binary = out / 'gear-unknown.exe'
    common.evidence([str(compiler), *[str(obj) for _, obj in jobs], *map(str, libraries), '-Wl,--gc-sections', '-o', str(binary)], 'gear-link', out, report, bindings)
    bindings['gear_objects'] = {str(obj): sha(obj) for _, obj in jobs}
    bindings['gear_binary'] = {str(binary): sha(binary)}
    return binary


def build_beetle(args, out, report, bindings, compiler):
    repository = args.beetle_source.resolve(); directory = out / 'beetle'; source = directory / 'src'; cd = source / 'cdrom'; cd.mkdir(parents=True)
    originals, blobs = {}, {}
    for name in sense.BEETLE_FILES:
        raw = subprocess.check_output(['git', '-C', str(repository), 'show', sense.BEETLE + ':' + name])
        blob = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', sense.BEETLE + ':' + name], text=True).strip()
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob:
            raise ValueError('Original Beetle Git blob differs')
        path = source / Path(name).relative_to('mednafen'); path.write_bytes(raw); originals[str(path)] = sha(path); blobs[name] = blob
    bindings['beetle_compile_sources'] = originals; report['beetle_source_blobs'] = blobs
    (directory / 'compat').mkdir()
    authored = {directory / 'forced.hpp': sense.FORCED, cd / 'cdromif.h': sense.MEDIA_HEADER, source / 'state.h': sense.STATE_HEADER,
                source / 'mednafen.h': '#pragma once\n#include "../forced.hpp"\n', directory / 'compat/msvc.h': '#pragma once\n'}
    for path, text in authored.items(): path.write_text(text)
    bindings['beetle_framework'] = {str(p): sha(p) for p in authored}
    obj, binary = directory / 'probe.o', directory / 'beetle-unknown.exe'
    common.evidence([str(compiler), '-std=c++20', '-O2', '-ffunction-sections', '-fdata-sections', '-I', str(directory), '-I', str(cd), '-I', str(ROOT / 'tests'), '-include', str(directory / 'forced.hpp'), '-c', str(ROOT / 'tests/beetle_cd_unknown_probe.cpp'), '-o', str(obj)], 'beetle-compile', out, report, bindings)
    common.evidence([str(compiler), str(obj), '-Wl,--gc-sections', '-o', str(binary)], 'beetle-link', out, report, bindings)
    bindings['beetle_artifacts'] = {str(p): sha(p) for p in (obj, binary)}
    return binary


def build_tool(args, out, report, bindings, compiler, module=None):
    label = 'native' if module else 'interpreted'; q = infrastructure.cmake_quote
    cmake, ninja = (Path(shutil.which(str(v)) or '').resolve() for v in (args.cmake, args.ninja))
    if not cmake.is_file() or not ninja.is_file(): raise ValueError('Require CMake/Ninja')
    bindings['tools'].update({str(p): sha(p) for p in (cmake, ninja)})
    wrapper = out / (label + '-wrapper'); wrapper.mkdir(); source = ROOT / 'tests/cd_unknown_oracle_probe.cpp'
    lines = ['cmake_minimum_required(VERSION 3.20)', 'project(UnknownCdProof LANGUAGES CXX)', *['set(' + o + ' OFF CACHE BOOL "" FORCE)' for o in ('PCE_BUILD_TOOLS', 'PCE_BUILD_TESTS', 'PCE_BUILD_DESKTOP', 'PCE_BUILD_REFERENCE_PROBE', 'BUILD_TESTING')], f'add_subdirectory({q(args.tool_source.resolve())} tool)']
    if module:
        lines += [f'pce_add_native_module(_module MODULE {q(module / "module.cpp")} MANIFEST {q(module / "module.json")})', f'add_executable(unknown-probe {q(source)})', 'target_compile_definitions(unknown-probe PRIVATE PCE_CD_UNKNOWN_NATIVE_ONLY=1)', 'target_link_libraries(unknown-probe PRIVATE ${_module} pce-runtime)']
    else:
        lines += [f'add_executable(unknown-probe {q(source)} {q(args.tool_source.resolve() / "runtime/src/no_module.cpp")})', 'target_link_libraries(unknown-probe PRIVATE pce-runtime)']
    file = wrapper / 'CMakeLists.txt'; file.write_text('\n'.join(lines) + '\n'); bindings.setdefault('tool_build_inputs', {})[str(file)] = sha(file)
    build = out / (label + '-build')
    common.evidence([str(cmake), '-S', str(wrapper), '-B', str(build), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_COMPILER=' + str(compiler), '-DCMAKE_MAKE_PROGRAM=' + str(ninja)], label + '-configure', out, report, bindings)
    common.evidence([str(cmake), '--build', str(build), '--target', 'unknown-probe', '--parallel', '4'], label + '-build', out, report, bindings, 600)
    binary = build / ('unknown-probe.exe' if os.name == 'nt' else 'unknown-probe')
    bindings.setdefault('tool_build_artifacts', {}).update({str(p): sha(p) for p in build.rglob('*') if p.is_file() and (p.suffix in ('.obj', '.o', '.a') or p.name in ('CMakeCache.txt', 'build.ninja', 'rules.ninja', '.ninja_log'))})
    bindings.setdefault('tool_binaries', {})[str(binary)] = sha(binary)
    return binary


def execute(label, binary, plan, arguments, out, report, bindings, wanted=None):
    result = common.evidence([str(binary), str(plan), *map(str, arguments)], label, out, report, bindings)
    rows = json.loads(result.stdout)
    if wanted is not None: validate_rows(rows, wanted)
    return rows


def validate_options(args):
    if args.reference_only and (args.native or args.probe):
        raise ValueError('Reference-only cannot claim toolkit execution')
    if args.native and args.probe:
        raise ValueError('Native qualification requires freshly built interpreted and native probes; external --probe is not accepted')


def run(args):
    validate_options(args)
    compiler = Path(shutil.which(str(args.compiler)) or '').resolve(); out = args.out.resolve(); tool = args.tool_source.resolve()
    if out.exists() or not out.is_relative_to(ROOT / '.local') or not compiler.is_file(): raise ValueError('Require compiler and NEW private output')
    if not args.reference_only:
        sys.path.insert(0, str(tool))
        from pcerecomp import project
        if Path(project.__file__).resolve() != tool / 'pcerecomp/project.py':
            raise ValueError('Compiler imported from a different toolkit source')
    files = [Path(__file__), *[ROOT / 'tests' / n for n in ('cd_unknown_probe_support.hpp', 'cd_unknown_oracle_probe.cpp', 'geargrafx_cd_unknown_probe.cpp', 'beetle_cd_unknown_probe.cpp', 'sense_oracle_probe.cpp', 'geargrafx_sense_probe.cpp', 'beetle_sense_probe.cpp', 'sense_probe_support.hpp', 'reset_probe_support.hpp', 'test_cd_unknown_reference.py')], *[ROOT / 'scripts' / n for n in ('sense_reference.py', 'mapper_reference.py', 'hucard_reference.py', 'filtered_audio_reference.py', 'psg_reference.py')]]
    if not args.reference_only: files += sorted((tool / 'runtime').rglob('*.cpp')) + sorted((tool / 'runtime').rglob('*.hpp')) + sorted((tool / 'pcerecomp').glob('*.py')) + [tool / 'CMakeLists.txt', tool / 'cmake/PCEConsumer.cmake']
    bindings = dict(tools={str(compiler): sha(compiler)}, authored_sources={str(p.resolve()): sha(p) for p in files})
    report = dict(schema=1, result='incomplete', commands=[], bindings=bindings, gear_commit=reference.COMMIT, beetle_commit=sense.BEETLE,
                  scope=__doc__, differences=['Gear unknown response: first-byte GOOD; NEC reference waits full 6/10/12-byte CDB and returns invalid-command sense05/20', 'Beetle raw error status01/message00 versus toolkit02/message02, retained explicitly', 'Gear REQUEST SENSE returns no payload; toolkit/Beetle return18', 'Beetle warm reset retains a partial command prefix; toolkit clears it. Raw prefix counts are checked separately and a cold reset precedes the next command', 'ACK edge flags are retained raw; no identical callback-clock or CPU access-phase claim', 'Idle non-BSY signal wires may remain latched in a reference; only bus-free BSY is compared'])
    out.mkdir(parents=True)
    try:
        image = out / 'authored-system.pce'; image.write_bytes(firmware()[0]); media = out / 'authored.bin'; media.write_bytes(bytes(20 * 2048))
        cue = out / 'authored.cue'; cue.write_text('FILE "authored.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')
        paths = {}
        for profile in ('gear', 'beetle', 'tool-nec', 'tool-gear'):
            path = out / (profile + '.plan'); path.write_text(serialize(plans(profile))); paths[profile] = path
        path = out / 'guest.plan'; path.write_text(serialize(guest_plan())); paths['guest'] = path
        bindings['authored_fixtures'] = {str(p): sha(p) for p in (image, media, cue, *paths.values())}
        beetle = build_beetle(args, out, report, bindings, compiler)
        golden = execute('beetle-matrix', beetle, paths['beetle'], [], out, report, bindings, expected(plans('beetle'), 'beetle'))
        gear = build_gear(args, out, report, bindings, compiler)
        legacy = execute('gear-matrix', gear, paths['gear'], [image, cue], out, report, bindings, expected(plans('gear'), 'gear'))
        report.update(unknown_opcodes_per_reference=248, reference_cases_per_engine=252, beetle_records=len(golden), gear_records=len(legacy))
        if not args.reference_only:
            probe = args.probe.resolve() if args.probe else build_tool(args, out, report, bindings, compiler)
            if not probe.is_file():
                raise ValueError('Toolkit probe is unavailable')
            bindings.setdefault('tool_binaries', {})[str(probe)] = sha(probe)
            report['tool_probe_build_origin'] = 'externally supplied; source correspondence belongs to caller' if args.probe else 'fresh build from bound tool source'
            for profile in ('tool-nec', 'tool-gear'):
                actual = execute(profile, probe, paths[profile], [image, 'nec-invalid' if profile == 'tool-nec' else 'gear-good'], out, report, bindings, expected(plans(profile), profile))
                report[profile + '_records'] = len(actual)
            def guest(label, binary, native):
                capture = out / (label + '-capture.json')
                rows = execute(label, binary, paths['guest'], [image, 'nec-invalid', '--capture', capture], out, report, bindings)
                count = validate_guest(rows)
                from pcerecomp.capture import load_capture
                from pcerecomp.project import ABI
                observed, digest = load_capture(capture)
                bindings['raw_outputs'][str(capture)] = sha(capture)
                if observed['runtime_abi'] != ABI or not observed['complete'] or observed['retired_instructions'] != count or sum(r['native_hits'] for r in observed['observations']) != (count if native else 0) or sum(r['interpreted_hits'] for r in observed['observations']) != (0 if native else count): raise ValueError('Autonomous guest capture/tier conservation')
                return rows, observed, digest, count
            training = guest('interpreted-guest', probe, False)
            report['guest_interpreted_steps'] = training[3]
            if args.native:
                from pcerecomp.emitter import emit_capture
                module = out / 'native-module'; emitted = emit_capture(training[1], module, training[2])
                if emitted['unsupported_observations']: raise ValueError('Autonomous guest unsupported source')
                native = build_tool(args, out, report, bindings, compiler, module)
                result = guest('native-guest', native, True)
                if not strict_equal(training[0], result[0]): raise ValueError('Native guest CPU/RAM/sense result differs')
                def keyed(cap): return {(r['pc'], tuple(r['mpr']), tuple(r['physical']), tuple(r['data'])): r for r in cap['observations']}
                old, new = keyed(training[1]), keyed(result[1])
                if old.keys() != new.keys() or any(new[k]['native_hits'] != old[k]['interpreted_hits'] or new[k]['interpreted_hits'] for k in old): raise ValueError('Native per-source retirement conversion')
                report.update(guest_native_steps=result[3], guest_interpreted_fallback=0, guest_source_identities=len(old), native_module_observation_profile=emitted.get('observation_profile'))
                bindings['native_module'] = {str(p): sha(p) for p in module.rglob('*') if p.is_file()}
        require_preservation(report, bindings)
        report['result'] = 'pass'
    finally:
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('commands', 'bindings', 'beetle_source_blobs')}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gear-source', type=Path, required=True); p.add_argument('--beetle-source', type=Path, required=True)
    p.add_argument('--tool-source', type=Path, default=ROOT); p.add_argument('--probe', type=Path)
    p.add_argument('--native', action='store_true'); p.add_argument('--reference-only', action='store_true')
    p.add_argument('--out', type=Path, required=True); p.add_argument('--compiler', default='clang++')
    p.add_argument('--cmake', default='cmake'); p.add_argument('--ninja', default='ninja')
    p.add_argument('--library', type=Path, action='append', default=[])
    try:
        args = p.parse_args()
        run(args)
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr); raise SystemExit(1)
