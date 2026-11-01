"""Real authored LLVM-MinGW interruption, refusal, continuation and execution.

This fixture compiles translated guest operations and 72 authored auxiliary
translation units. It kills only its known CLI parent while a later Ninja
chunk has live descendants; neither compiler wrappers nor synthetic objects
substitute for real compiler work.
"""
from contextlib import contextmanager, nullcontext
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from pcerecomp import project
from pcerecomp.emitter import emit_capture
from scripts.build_config import cmake_cache


ROOT = Path(__file__).resolve().parent.parent
MPR = [255, 248, 128, 129, 130, 131, 132, 0]


def _bundle(test):
    if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
        test.skipTest('Recoverable native producer requires Windows x64 LLVM-MinGW')
    cache = cmake_cache(ROOT/'build', os.environ.get('PCE_TEST_CMAKE_CACHE'))
    compiler = None
    if cache:
        for line in cache.read_text(encoding='utf-8').splitlines():
            if line.startswith('CMAKE_CXX_COMPILER:'):
                selected = line.split('=', 1)[1]
                compiler = Path(shutil.which(selected) or selected).resolve()
                break
    if compiler is None or compiler.name.lower() != 'clang++.exe':
        test.skipTest('Audited LLVM-MinGW compiler not selected')
    bundle = compiler.parent.parent
    if not all((bundle/name).exists() for name in (
            'bin/clang++.exe', 'bin/ninja.exe', 'bin/cmake.exe',
            'x86_64-w64-mingw32/include', 'x86_64-w64-mingw32/lib')):
        test.skipTest('Selected compiler lacks the audited self-contained bundle')
    return bundle


def _kernel():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    for name, result, arguments in (
            ('OpenJobObjectW', wintypes.HANDLE,
             [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]),
            ('QueryInformationJobObject', wintypes.BOOL,
             [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID]),
            ('OpenProcess', wintypes.HANDLE,
             [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]),
            ('WaitForSingleObject', wintypes.DWORD, [wintypes.HANDLE, wintypes.DWORD]),
            ('CloseHandle', wintypes.BOOL, [wintypes.HANDLE])):
        function = getattr(kernel, name)
        function.restype, function.argtypes = result, arguments
    return kernel


def _job_processes(kernel, build):
    # Independently reproduce the documented job namespace. Close this query
    # handle before killing the parent: retaining it would prevent kill-on-close.
    canonical = os.path.normcase(str(build.resolve()))
    name = 'Global\\pcerecomp-verified-build-v1-' + hashlib.sha256(
        canonical.encode('utf-8', errors='surrogatepass')).hexdigest()
    job = kernel.OpenJobObjectW(4, False, name)
    if not job:
        return []
    try:
        class Pids(ctypes.Structure):
            _fields_ = [('assigned', wintypes.DWORD), ('count', wintypes.DWORD),
                        ('pids', ctypes.c_size_t*256)]
        values = Pids()
        if not kernel.QueryInformationJobObject(job, 3, ctypes.byref(values),
                                                ctypes.sizeof(values), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if values.count > 256:
            raise AssertionError('Unexpected authored compiler process count')
        return list(values.pids[:values.count])
    finally:
        kernel.CloseHandle(job)


@contextmanager
def _changed(path):
    """Restore only trusted fixture bytes and original nanosecond timestamps."""
    original, info = path.read_bytes(), path.stat()
    altered = bytearray(original)
    if not altered:
        raise AssertionError('Mutation requires a nonempty authored file')
    if path.name.startswith('checkpoint-'):
        # Change a content digest while preserving valid JSON and byte length.
        position = original.index(b'"sha256":"') + len(b'"sha256":"')
        altered[position] = ord('1') if altered[position] == ord('0') else ord('0')
    else:
        altered[len(altered)//2] ^= 1
    path.write_bytes(altered)
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
    try:
        yield
    finally:
        path.write_bytes(original)
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))


class NativeBuildRecoveryTests(unittest.TestCase):
    def test_real_parent_interruption_refuses_tampering_then_reuses_sealed_objects(self):
        bundle = _bundle(self)
        artifacts = os.environ.get('PCE_TEST_RECOVERY_ARTIFACT_ROOT')
        if artifacts:
            Path(artifacts).mkdir(parents=True, exist_ok=True)
            # CMake's hash-qualified module target already has a long basename;
            # a short Windows TEMP root avoids MAX_PATH object-name rewriting.
            retained = tempfile.mkdtemp(prefix='pcer-')
            (Path(artifacts)/('location-'+Path(retained).name+'.json')).write_text(
                json.dumps(dict(authored_fixture=retained)), encoding='utf-8')
            workspace = nullcontext(retained)
        else:
            workspace = tempfile.TemporaryDirectory()
        with workspace as temporary:
            root = Path(temporary)
            tool = root/'tool'
            tool.mkdir()
            # Bind a stable source snapshot while other tests or developers may
            # edit the checkout. Do not copy .git, builds, saves or private data.
            shutil.copy2(ROOT/'CMakeLists.txt', tool/'CMakeLists.txt')
            for name in project.SOURCE_DIRS:
                shutil.copytree(ROOT/name, tool/name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            descriptor, module = self._fixture(root, tool)
            build = root/'output'
            env = dict(os.environ)
            env['PATH'] = str(bundle/'bin') + os.pathsep + env.get('PATH', '')
            # Existing checkout bytecode must never mask changed source bytes.
            prefix = [sys.executable, '-B', '-X', 'pycache_prefix='+str(root/'no-bytecode'),
                      '-m', 'pcerecomp.project']
            common = [str(descriptor), '--build-dir', str(build), '--allow-revision-override']
            command = prefix + ['build', *common, '--recoverable', '--generator', 'Ninja',
                '--recovery-toolchain-root', str(bundle),
                '--cmake-arg=-DCMAKE_CXX_COMPILER='+str(bundle/'bin/clang++.exe'),
                '--cmake-arg=-DCMAKE_MAKE_PROGRAM='+str(bundle/'bin/ninja.exe')]
            log = root/'interrupted.log'
            kernel = _kernel()
            with log.open('wb') as output:
                process = subprocess.Popen(command, cwd=tool, env=env,
                                           stdout=output, stderr=subprocess.STDOUT)
                try:
                    meta = build/'.pce-recovery'
                    deadline = time.monotonic()+360
                    handles, live, unsealed = [], [], []
                    while time.monotonic() < deadline:
                        self.assertIsNone(process.poll(), log.read_text(errors='replace'))
                        checkpoints = sorted(meta.glob('checkpoint-*.json')) if meta.exists() else []
                        if checkpoints:
                            checkpoint = json.loads(checkpoints[-1].read_text())
                            configured = json.loads((meta/'configured.json').read_text())
                            objects = configured['graph']['objects']
                            unsealed = [name for name in objects
                                        if name not in checkpoint['objects'] and (build/'build'/name).is_file()]
                            live = _job_processes(kernel, build)
                            if unsealed and len(live) >= 2:
                                handles = [kernel.OpenProcess(0x100000, False, pid) for pid in live]
                                handles = [handle for handle in handles if handle]
                                if handles:
                                    break
                        time.sleep(.01)
                    else:
                        self.fail('No durable checkpoint followed by live partial compilation: '+
                                  log.read_text(errors='replace'))
                    self.assertGreater(len(objects), 64)
                    self.assertGreater(len(checkpoint['objects']), 0)
                    self.assertTrue(unsealed)
                    process.kill()  # The only killed PID is this test's CLI parent.
                    process.wait(timeout=20)
                    try:
                        # Enter public recovery immediately, while the guardian
                        # may still be draining. A temporary input mismatch
                        # preserves the interrupted tree for later checks.
                        with _changed(module/'module.cpp'):
                            immediate = subprocess.run(prefix+['resume', *common], cwd=tool, env=env,
                                capture_output=True, text=True, timeout=30)
                        (root/'immediate-resume-refusal.log').write_text(
                            immediate.stdout+immediate.stderr, encoding='utf-8')
                        self.assertEqual(immediate.returncode, 2, immediate.stdout+immediate.stderr)
                        self.assertIn('module.source SHA256', immediate.stderr)
                        # These handles preserve process identity against PID
                        # reuse and do not retain the named job itself.
                        termination = []
                        for handle in handles:
                            status = kernel.WaitForSingleObject(handle, 10000)
                            termination.append(status)
                            self.assertEqual(status, 0,
                                             'Parent death left a known compiler descendant alive')
                        (root/'interruption.json').write_text(json.dumps(dict(
                            schema=1, parent_pid=process.pid, parent_returncode=process.returncode,
                            observed_job_members=live, observed_process_handles=len(handles),
                            process_wait_statuses=termination, sealed_objects=len(checkpoint['objects']),
                            partial_object_outputs=unsealed, execution_evidence=False)), encoding='utf-8')
                    finally:
                        for handle in handles:
                            kernel.CloseHandle(handle)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=20)

            self.assertFalse((build/'build-receipt.json').exists())
            original_contract = (meta/'contract.json').read_bytes()
            original_configured = (meta/'configured.json').read_bytes()
            descriptor_bytes = descriptor.read_bytes()
            checkpoint_files = {p.name: p.read_bytes() for p in meta.glob('checkpoint-*.json')}
            checkpoint = json.loads(next(reversed(checkpoint_files.values())))
            sealed = checkpoint['objects']
            sealed_before = {name: self._artifact(build/'build'/name) for name in sealed}
            unsealed_before = {name: self._artifact(build/'build'/name) for name in objects
                               if name not in sealed and (build/'build'/name).is_file()}
            self.assertTrue(unsealed_before)
            self.assertEqual(len(objects), 100)
            initial_sealed_before = dict(sealed_before)
            initial_unsealed = set(unsealed_before)
            initial_ninja_before = (build/'build/.ninja_log').read_bytes()
            (root/'ninja-before-first-resume.log').write_bytes(initial_ninja_before)
            (root/'first-interruption-before-resume.json').write_text(json.dumps(dict(
                objects=initial_sealed_before, unsealed_objects=sorted(initial_unsealed))), encoding='utf-8')
            initial_checkpoint_bytes = (meta/'checkpoint-000001.json').read_bytes()
            resume_command = prefix + ['resume', *common]

            # Replay a real three-record delta chain. Capture the third group's
            # completed 96 objects while the producer is between chunks, then
            # interrupt only when later C++ work is actually alive. The final
            # four units include VDC/video sources, rather than tiny fake work.
            middle_log = root/'middle-resume.log'
            with middle_log.open('wb') as output:
                middle = subprocess.Popen(resume_command, cwd=tool, env=env,
                                          stdout=output, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic()+600
                    third_before, third_ledger = None, None
                    while time.monotonic() < deadline:
                        self.assertIsNone(middle.poll(), middle_log.read_text(errors='replace'))
                        if (meta/'checkpoint-000003.json').exists():
                            if third_before is None:
                                points = [json.loads((meta/f'checkpoint-{index:06d}.json').read_text())
                                          for index in range(1, 4)]
                                third_ledger = {}
                                for point in points:
                                    self.assertEqual(point['schema'], 2)
                                    self.assertEqual(point['kind'], 'pce-object-checkpoint-delta-v1')
                                    self.assertEqual(len(point['objects']), 32)
                                    self.assertFalse(set(third_ledger) & set(point['objects']))
                                    third_ledger.update(point['objects'])
                                self.assertEqual(len(third_ledger), 96)
                                third_before = {name:self._artifact(build/'build'/name) for name in third_ledger}
                                (root/'third-group-before-second-kill.json').write_text(
                                    json.dumps(dict(objects=third_before, checkpoint_sequence=3)), encoding='utf-8')
                                (root/'ninja-at-third-group.log').write_bytes((build/'build/.ninja_log').read_bytes())
                            remaining = set(objects)-set(third_ledger)
                            later = [name for name in remaining if (build/'build'/name).is_file()]
                            live = _job_processes(kernel, build)
                            if later and len(later) < len(remaining) and len(live) >= 2:
                                handles = [kernel.OpenProcess(0x100000, False, pid) for pid in live]
                                handles = [handle for handle in handles if handle]
                                if handles:
                                    break
                        time.sleep(.01)
                    else:
                        self.fail('No third durable delta group followed by live final compilation: '+
                                  middle_log.read_text(errors='replace'))
                    middle.kill()
                    middle.wait(timeout=20)
                    try:
                        with _changed(module/'module.cpp'):
                            immediate = subprocess.run(resume_command, cwd=tool, env=env,
                                capture_output=True, text=True, timeout=30)
                        (root/'immediate-second-resume-refusal.log').write_text(
                            immediate.stdout+immediate.stderr, encoding='utf-8')
                        self.assertEqual(immediate.returncode, 2, immediate.stdout+immediate.stderr)
                        self.assertIn('module.source SHA256', immediate.stderr)
                        termination = [kernel.WaitForSingleObject(handle, 10000) for handle in handles]
                        self.assertTrue(all(status == 0 for status in termination))
                        (root/'second-interruption.json').write_text(json.dumps(dict(
                            schema=1, parent_pid=middle.pid, parent_returncode=middle.returncode,
                            observed_job_members=live, observed_process_handles=len(handles),
                            process_wait_statuses=termination, sealed_objects=96,
                            checkpoint_sequence=3, partial_object_outputs=later,
                            execution_evidence=False)), encoding='utf-8')
                    finally:
                        for handle in handles:
                            kernel.CloseHandle(handle)
                finally:
                    if middle.poll() is None:
                        middle.kill()
                        middle.wait(timeout=20)
            self.assertFalse((build/'build-receipt.json').exists())
            self.assertEqual((meta/'checkpoint-000001.json').read_bytes(), initial_checkpoint_bytes)
            self.assertEqual({name:self._artifact(build/'build'/name) for name in initial_sealed_before},
                             initial_sealed_before)
            self.assertEqual({name:self._artifact(build/'build'/name) for name in third_ledger}, third_before)
            middle_admission = json.loads((meta/'attempt-000002-admission.json').read_text())
            self.assertEqual(middle_admission['base_sequence'], 1)
            self.assertEqual(len(middle_admission['new_objects']), 68)
            self.assertFalse(middle_admission['missing_objects'])
            self.assertFalse((meta/'attempt-000002-result.json').exists())
            sealed, sealed_before = third_ledger, third_before
            unsealed_before = {name:self._artifact(build/'build'/name) for name in objects
                               if name not in sealed and (build/'build'/name).is_file()}
            self.assertTrue(unsealed_before)
            checkpoint_files = {p.name:p.read_bytes() for p in sorted(meta.glob('checkpoint-*.json'))}
            # Deterministically exercise temporary-output admission. These
            # bytes are authored here, never claimed as observed Clang output;
            # the real parent interruption and compiled objects remain above.
            temporary_target = next(iter(unsealed_before))
            target_path = build/'build'/temporary_target
            authored_temporary = target_path.with_name(target_path.stem+'-facecafe.obj.tmp')
            with authored_temporary.open('xb') as stream:
                stream.write(b'authored incomplete compiler temporary fixture\n')
            temporary_before = self._artifact(authored_temporary)
            temporary_record = dict(
                path=authored_temporary.relative_to(build/'build').as_posix(),
                target=temporary_target, bytes=authored_temporary.stat().st_size,
                sha256=temporary_before[0])
            (root/'authored-temporary-fixture.json').write_text(json.dumps(dict(
                producer='authored fixture; not observed Clang output', artifact=temporary_record)),
                encoding='utf-8')
            ninja_before = (build/'build/.ninja_log').read_bytes()

            def refused(label, expected=None):
                completed = subprocess.run(resume_command, cwd=tool, env=env,
                    capture_output=True, text=True, timeout=120)
                (root/(label+'.log')).write_text(completed.stdout+completed.stderr, encoding='utf-8')
                self.assertEqual(completed.returncode, 2, completed.stdout+completed.stderr)
                if expected:
                    self.assertIn(expected, completed.stderr)
                self.assertFalse((build/'build-receipt.json').exists())
                self.assertEqual((build/'build/.ninja_log').read_bytes(), ninja_before,
                                 'Refusal executed compiler work')
                for name, before in unsealed_before.items():
                    self.assertEqual(self._artifact(build/'build'/name), before,
                                     'Refusal cleaned an unsealed object before admission')
                self.assertEqual(self._artifact(authored_temporary), temporary_before,
                                 'Refusal cleaned an authored temporary before full admission')

            # Content changes keep both length and mtime; timestamps alone
            # cannot authorize a reused object. No checkpoint is regenerated.
            for label, path, expected in (
                    ('module', module/'module.cpp', 'module.source SHA256'),
                    ('module-header', module/'authored.hpp', 'authored.hpp SHA256'),
                    ('tool-source', tool/'runtime/src/runtime.cpp', 'Tool source digest mismatch'),
                    ('cmake-cache', build/'build/CMakeCache.txt', 'immutable configuration changed'),
                    ('ninja-graph', build/'build/build.ninja', 'immutable configuration changed'),
                    ('sealed-object', build/'build'/next(iter(sealed)), 'sealed object integrity'),
                    ('checkpoint', meta/next(reversed(checkpoint_files)), 'metadata content checksum differs')):
                with self.subTest(refusal=label), _changed(path):
                    refused(label, expected)

            contract = meta/'contract.json'
            contract.rename(meta/'trusted-contract.saved')
            try:
                refused('missing-contract', 'contract.json')
            finally:
                (meta/'trusted-contract.saved').rename(contract)

            import msvcrt
            with (build/'.pce-recovery.lock').open('r+b', buffering=0) as lock:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    refused('concurrent-resume', 'busy')
                finally:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

            trusted = root/'authored-link-target.txt'
            trusted.write_text('authored outside-build sentinel', encoding='utf-8')
            link = build/'unsafe-hardlink.txt'
            os.link(trusted, link)
            try:
                refused('unsafe-hardlink', 'hardlink')
                self.assertEqual(trusted.read_text(), 'authored outside-build sentinel')
            finally:
                link.unlink()

            self.assertEqual(contract.read_bytes(), original_contract)
            self.assertEqual((meta/'configured.json').read_bytes(), original_configured)
            self.assertEqual(descriptor.read_bytes(), descriptor_bytes)
            self.assertEqual({p.name: p.read_bytes() for p in meta.glob('checkpoint-*.json')}, checkpoint_files)
            completed = subprocess.run(resume_command, cwd=tool, env=env,
                capture_output=True, text=True, timeout=600)
            (root/'resume.log').write_text(completed.stdout+completed.stderr, encoding='utf-8')
            self.assertEqual(completed.returncode, 0, completed.stdout+completed.stderr)
            receipt = json.loads((build/'build-receipt.json').read_text())
            recovery = receipt['recovery']
            self.assertTrue(recovery['resumed'])
            self.assertGreater(recovery['attempt'], 1)
            self.assertFalse(receipt['execution_evidence'])
            self.assertEqual(set(recovery['verified_retained_objects']), set(sealed))
            self.assertEqual(len(recovery['verified_retained_objects']), 96)
            self.assertEqual(len(recovery['recompiled_unsealed_objects']), 4)
            final_admission = json.loads((meta/f"attempt-{recovery['attempt']:06d}-admission.json").read_text())
            self.assertEqual(final_admission['base_sequence'], 3)
            self.assertEqual(len(final_admission['new_objects']), 4)
            self.assertTrue(set(unsealed_before) <= set(recovery['recompiled_unsealed_objects']))
            self.assertTrue(set(unsealed_before) <= set(recovery['removed_unsealed_outputs']))
            self.assertFalse(authored_temporary.exists())
            self.assertIn(temporary_record, recovery['removed_temporary_objects'])
            self.assertEqual({name: self._artifact(build/'build'/name) for name in sealed}, sealed_before)
            # The actual Ninja log records each executed output, independently
            # of the recovery receipt's declared retained/rebuilt lists.
            after = (build/'build/.ninja_log').read_bytes()
            counts = lambda raw: self._ninja_counts(raw)
            for name in sealed:
                self.assertEqual(counts(after).get(name, 0), counts(ninja_before).get(name, 0), name)
            for name in unsealed_before:
                self.assertGreater(counts(after).get(name, 0), counts(ninja_before).get(name, 0), name)
            for name in initial_unsealed:
                self.assertGreater(counts(after).get(name, 0), counts(initial_ninja_before).get(name, 0), name)
            for name in initial_sealed_before:
                self.assertEqual(counts(after).get(name, 0), counts(initial_ninja_before).get(name, 0), name)
            points = [json.loads(p.read_text()) for p in sorted(meta.glob('checkpoint-*.json'))]
            self.assertEqual(len(points), 4)
            self.assertTrue(all(point['schema'] == 2 and 1 <= len(point['objects']) <= 32 for point in points))
            for name in configured['graph']['links']:
                self.assertGreater(counts(after).get(name, 0), counts(ninja_before).get(name, 0),
                                   'Actual archive/executable link was not executed: '+name)
            for command in receipt['commands']:
                self.assertFalse(set(sealed) & set(command), 'Retained objects were explicitly recompiled')
            self.assertTrue(Path(receipt['binary']).is_file())
            self.assertEqual(contract.read_bytes(), original_contract)
            self.assertEqual((meta/'configured.json').read_bytes(), original_configured)
            starts = sorted(meta.glob('attempt-*-start.json'))
            self.assertGreaterEqual(len(starts), 2)
            self.assertFalse((meta/'attempt-000001-result.json').exists(),
                             'Hard interruption was relabeled as a completed or failed normal return')
            failures = [json.loads(p.read_text()) for p in meta.glob('attempt-*-result.json')
                        if json.loads(p.read_text())['status'] == 'failed']
            self.assertGreaterEqual(len(failures), 3)
            run_path = root/'run-receipt.json'
            executed = subprocess.run(prefix+['run', *common, '--receipt', str(run_path)],
                cwd=tool, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(executed.returncode, 0, executed.stdout+executed.stderr)
            run = json.loads(run_path.read_text())
            self.assertTrue(run['qualified'], run)
            self.assertEqual((run['result']['native_steps'], run['result']['interpreter_steps'],
                              run['result']['guard_misses']), (200, 0, 0))
            self.assertEqual(run['result']['x'], 107)  # 1 LDX + 100 INX + 99 JMP.
            self.assertEqual(run['result']['pc'], 0x4003)
            # Independent HuC6280 totals: 2 + 100*2 + 99*4 CPU cycles.
            self.assertEqual((run['result']['cycles'], run['result']['ticks']), (598, 1794))
            self.assertEqual((run['work']['native'], run['work']['interpreted']), (200, 0))
            self.assertFalse(json.loads((build/'build-receipt.json').read_text())['execution_evidence'])
            final_receipt = (build/'build-receipt.json').read_bytes()
            completed_again = subprocess.run(resume_command, cwd=tool, env=env,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(completed_again.returncode, 2)
            self.assertIn('completed builds', completed_again.stderr)
            self.assertEqual((build/'build-receipt.json').read_bytes(), final_receipt)

    @staticmethod
    def _artifact(path):
        return project.sha256(path), path.stat().st_mtime_ns

    @staticmethod
    def _ninja_counts(raw):
        counts = {}
        for line in raw.decode('utf-8').splitlines():
            fields = line.split('\t')
            if len(fields) == 5:
                counts[fields[3]] = counts.get(fields[3], 0)+1
        return counts

    @staticmethod
    def _fixture(root, tool):
        module = root/'module'
        program = bytes([0xa2, 7, 0xe8, 0x4c, 2, 0x40])
        payload = root/'program.bin'
        payload.write_bytes(program)
        observations = []
        for pc, data in ((0x4000, [0xa2, 7]), (0x4002, [0xe8]), (0x4003, [0x4c, 2, 0x40])):
            observations.append(dict(pc=pc, mpr=MPR,
                physical=[1048576+pc-0x4000+i for i in range(len(data))], data=data,
                native_hits=0, interpreted_hits=1))
        authored = dict(schema=1, runtime_abi=project.ABI, capacity=64,
            dropped_instructions=0, unreadable_instructions=0, retired_instructions=3,
            complete=True, observations=observations)
        emitted = emit_capture(authored, module, single_unit=True)
        units = [dict(file='module.cpp', sha256=project.sha256(module/'module.cpp'))]
        header = module/'authored.hpp'
        header.write_text('#pragma once\n#include <cstdint>\n'
                          'inline constexpr std::uint64_t authored_salt = 17;\n', encoding='utf-8')
        for index in range(72):
            path = module/f'aux_{index:03d}.cpp'
            path.write_text('#include "authored.hpp"\n'
                f'extern "C" std::uint64_t authored_aux_{index}(std::uint64_t x) {{\n'
                f'  return (x ^ (authored_salt + {index}ULL)) * {index*2+3}ULL + (x >> 3);\n}}\n', encoding='utf-8')
            units.append(dict(file=path.name, sha256=project.sha256(path)))
        emitted['translation_units'] = units
        emitted['generated_headers'] = [dict(file=header.name, sha256=project.sha256(header))]
        (module/'module.json').write_text(json.dumps(emitted), encoding='utf-8')
        identity = project.source_identity(tool)
        descriptor = root/'project.toml'
        descriptor.write_text(f'''schema = 1
name = "authored-build-recovery"
[tool]
path = {json.dumps(tool.as_posix())}
revision = "{'0'*40}"
source_sha256 = "{identity['source_sha256']}"
runtime_abi = {project.ABI}
[module.source]
path = "module/module.cpp"
sha256 = "{project.sha256(module/'module.cpp')}"
[module.manifest]
path = "module/module.json"
sha256 = "{project.sha256(module/'module.json')}"
[payload]
path = "program.bin"
sha256 = "{project.sha256(payload)}"
physical_load = 1048576
pc = 16384
mpr = {MPR}
[runtime]
tier = "native"
video = "continuous"
cd_unknown_status = "fault"
joypad = 2
region = "usa"
multitap = "off"
audio = "off"
[limits]
steps = 200
ticks = 100000
wall_seconds = 5
''', encoding='utf-8')
        return descriptor, module


if __name__ == '__main__':
    unittest.main()
