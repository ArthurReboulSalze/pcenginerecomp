"""Actual Windows process-tree ownership tests using authored temporary writers."""

import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from pcerecomp import build_process


_WINDOWS_X64 = (sys.platform == 'win32' and ctypes.sizeof(ctypes.c_void_p) == 8
                and platform.machine().lower() in ('amd64', 'x86_64'))
_ROOT = Path(__file__).resolve().parents[1]

_RUNNER = r'''
import json, os, sys
from pathlib import Path
from pcerecomp.build_process import run
spec = json.loads(sys.argv[1])
result = run(spec['command'], env=spec['env'], cwd=Path(spec['cwd']))
assert result.returncode == 0 and result.stdout is None and result.stderr is None
'''

_LEASE_RUNNER = r'''
import json, os, sys
from pathlib import Path
from pcerecomp.build_process import run
from pcerecomp.build_recovery import _locked
spec = json.loads(sys.argv[1])
with _locked(Path(spec['cwd'])):
    run(spec['command'], env=spec['env'], cwd=Path(spec['cwd']))
'''

_BUILDER = r'''
import json, os, subprocess, sys, time
from pathlib import Path
root = Path(sys.argv[1])
writer = subprocess.Popen([sys.executable, '-c', r"""
import os, sys, time
from pathlib import Path
root = Path(sys.argv[1])
with (root / 'heartbeat').open('ab', buffering=0) as stream:
    while True:
        stream.write(b'x')
        time.sleep(.01)
""", str(root)])
(root / 'pids.json').write_text(json.dumps([os.getpid(), writer.pid]))
deadline = time.monotonic() + 10
while not (root / 'heartbeat').exists():
    if time.monotonic() >= deadline:
        raise RuntimeError('writer did not start')
    time.sleep(.005)
if sys.argv[2] == 'exit':
    sys.exit(0)
while True:
    time.sleep(1)
'''


@unittest.skipUnless(_WINDOWS_X64, 'verified process-tree profile requires Windows x64')
class BuildProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pcerecomp-owned-process-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ)
        self.env['PYTHONPATH'] = str(_ROOT)

    def runner(self, command, *, cwd=None, env=None):
        spec = {'command': command, 'cwd': str(cwd or self.root),
                'env': self.env if env is None else env}
        return [sys.executable, '-c', _RUNNER, json.dumps(spec)]

    def wait_file(self, path):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                value = path.read_bytes()
            except FileNotFoundError:
                value = b''
            if value:
                return value
            time.sleep(.005)
        self.fail(f'owned fixture did not write {path.name}')

    def open_processes(self, pids):
        # Independent OS handles prevent PID reuse from weakening death checks.
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.CloseHandle.restype = w.BOOL
        handles = []
        for pid in pids:
            handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE only.
            self.assertTrue(handle, ctypes.get_last_error())
            self.addCleanup(kernel.CloseHandle, handle)
            handles.append(handle)
        return kernel, handles

    def test_stdio_arguments_unicode_environment_and_cwd_are_preserved(self):
        directory = self.root / 'working space 雪'
        directory.mkdir()
        arguments = ['', 'space value', 'a"b', 'trailing\\', '雪', 'x\\"y', '& exit 3']
        environment = dict(self.env, RECOVERY_VALUE='snow 雪 and spaces')
        environment.pop('RECOVERY_MUST_BE_ABSENT', None)
        code = ("import json,os,sys;sys.stdout.reconfigure(encoding='utf-8');"
                "print(json.dumps([sys.argv[1:],os.getcwd(),os.environ['RECOVERY_VALUE'],"
                "os.environ.get('RECOVERY_MUST_BE_ABSENT')],ensure_ascii=False));"
                "print('owned stderr',file=sys.stderr)")
        outer_env = dict(self.env, RECOVERY_MUST_BE_ABSENT='not inherited')
        result = subprocess.run(self.runner([sys.executable, '-c', code, *arguments],
                                            cwd=directory, env=environment),
                                env=outer_env, capture_output=True, encoding='utf-8',
                                check=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(json.loads(result.stdout),
                         [arguments, str(directory), environment['RECOVERY_VALUE'], None])
        self.assertEqual(result.stderr.strip(), 'owned stderr')

    def test_return_value_and_nonzero_exit_status(self):
        result = build_process.run([sys.executable, '-c', 'pass'],
                                   env=self.env, cwd=self.root)
        self.assertIsInstance(result, subprocess.CompletedProcess)
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(result.stdout)
        self.assertIsNone(result.stderr)
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            build_process.run([sys.executable, '-c', 'raise SystemExit(37)'],
                              env=self.env, cwd=self.root)
        self.assertEqual(caught.exception.returncode, 37)

    def test_missing_executable_fails_without_fallback(self):
        with self.assertRaises(OSError):
            build_process.run([str(self.root / 'missing.exe')], env=self.env, cwd=self.root)

    def test_atomic_assignment_refusal_never_executes_command(self):
        kernel = build_process._kernel()
        marker = self.root / 'must-not-exist'

        def refuse(*args):
            ctypes.set_last_error(50)  # ERROR_NOT_SUPPORTED
            return 0

        with patch.object(kernel, 'UpdateProcThreadAttribute', side_effect=refuse):
            with patch.object(build_process, '_kernel', return_value=kernel):
                with self.assertRaisesRegex(OSError, 'atomic assignment required'):
                    build_process._run_owned([sys.executable, '-c',
                                              f'from pathlib import Path;Path({str(marker)!r}).touch()'],
                                             env=self.env, cwd=self.root)
        self.assertFalse(marker.exists())
        build_process.quiesce(self.root)

    def test_unrelated_inheritable_handle_is_not_forwarded(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)

        class Security(ctypes.Structure):
            _fields_ = [('length', w.DWORD), ('descriptor', w.LPVOID),
                        ('inherit', w.BOOL)]

        kernel.CreateEventW.argtypes = [ctypes.POINTER(Security), w.BOOL, w.BOOL, w.LPCWSTR]
        kernel.CreateEventW.restype = w.HANDLE
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        security = Security(ctypes.sizeof(Security), None, True)
        event = kernel.CreateEventW(ctypes.byref(security), True, False, None)
        self.assertTrue(event)
        try:
            # Runner deliberately receives this extra inheritable event. Its
            # managed child must not receive it, even with bInheritHandles=True.
            signal = ("import ctypes,sys;from ctypes import wintypes as w;"
                      "k=ctypes.WinDLL('kernel32');k.SetEvent.argtypes=[w.HANDLE];"
                      "k.SetEvent(int(sys.argv[1]))")
            subprocess.run(self.runner([sys.executable, '-c', signal, str(event)]),
                           env=self.env, close_fds=False, check=True, timeout=15,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(kernel.WaitForSingleObject(event, 0), 258)
        finally:
            kernel.CloseHandle(event)

    def test_existing_active_job_refuses_commands_and_recovery(self):
        process = subprocess.Popen(self.runner([sys.executable, '-c', _BUILDER,
                                                str(self.root), 'wait']),
                                   env=self.env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            self.wait_file(self.root / 'pids.json')
            self.wait_file(self.root / 'heartbeat')
            marker = self.root / 'must-not-run'
            with self.assertRaisesRegex(OSError, 'remains active'):
                build_process.run([sys.executable, '-c',
                                   f'from pathlib import Path;Path({str(marker)!r}).touch()'],
                                  env=self.env, cwd=self.root)
            with self.assertRaisesRegex(OSError, 'recovery refused'):
                build_process.quiesce(self.root, timeout=.03)
            self.assertFalse(marker.exists())
            self.assertIsNone(process.poll())
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
            build_process.quiesce(self.root)

    def test_keyboard_interrupt_drains_the_running_tree(self):
        wait = subprocess.Popen.wait
        observations = []

        def interrupt_when_writer_ready(process, timeout=None):
            pids_file = self.root / 'pids.json'
            if not observations and pids_file.exists() and (self.root / 'heartbeat').exists():
                observations.append(self.open_processes(json.loads(pids_file.read_text())))
                raise KeyboardInterrupt
            return wait(process, timeout=timeout)

        with patch.object(subprocess.Popen, 'wait', new=interrupt_when_writer_ready):
            with self.assertRaises(KeyboardInterrupt):
                build_process.run([sys.executable, '-c', _BUILDER, str(self.root), 'wait'],
                                  env=self.env, cwd=self.root)
        self.assertEqual(len(observations), 1)
        observer, handles = observations[0]
        self.assertTrue(all(observer.WaitForSingleObject(h, 0) == 0 for h in handles))
        build_process.quiesce(self.root)

    def test_cleanup_closes_new_process_admission_before_handle_snapshot(self):
        code = r'''
import subprocess, sys, time
from pathlib import Path
root = Path(sys.argv[1])
(root / 'ready').touch()
while not (root / 'spawn-now').exists():
    time.sleep(.005)
try:
    subprocess.Popen([sys.executable, '-c',
        'import sys;from pathlib import Path;Path(sys.argv[1]).touch()', str(root / 'escaped')])
except OSError:
    (root / 'blocked').write_text('child admission refused')
else:
    (root / 'launched').write_text('unexpected child')
while True:
    time.sleep(1)
'''
        kernel = build_process._kernel()
        wait = kernel.WaitForSingleObject
        interrupted = []
        snapshot = build_process._member_handles

        def interrupt_when_ready(handle, timeout):
            if not interrupted and (self.root / 'ready').exists():
                interrupted.append(True)
                raise KeyboardInterrupt
            return wait(handle, timeout)

        def attempt_spawn_before_snapshot(actual_kernel, job):
            (self.root / 'spawn-now').touch()
            self.wait_file(self.root / 'blocked')
            self.assertFalse((self.root / 'escaped').exists())
            self.assertFalse((self.root / 'launched').exists())
            return snapshot(actual_kernel, job)

        with patch.object(kernel, 'WaitForSingleObject', side_effect=interrupt_when_ready):
            with patch.object(build_process, '_kernel', return_value=kernel):
                with patch.object(build_process, '_member_handles', side_effect=attempt_spawn_before_snapshot):
                    with self.assertRaises(KeyboardInterrupt):
                        build_process._run_owned([sys.executable, '-c', code, str(self.root)],
                                                 env=self.env, cwd=self.root)
        build_process.quiesce(self.root)

    def test_drain_failure_cannot_be_mistaken_for_a_launch_error(self):
        with patch.object(build_process, '_drain', side_effect=OSError('injected drain failure')):
            with self.assertRaisesRegex(build_process._CleanupFailure, 'cleanup was not proven'):
                build_process._run_owned([sys.executable, '-c', 'pass'],
                                         env=self.env, cwd=self.root)

    def test_guardian_cleanup_failure_quarantines_lease_and_never_signals_completion(self):
        import msvcrt
        from pcerecomp.build_recovery import _locked

        kernel = build_process._kernel()
        completed = kernel.CreateEventW(None, True, False, None)
        cancelled = kernel.CreateEventW(None, True, False, None)
        owner = kernel.OpenProcess(0x100000, False, os.getpid())
        for handle in (completed, cancelled, owner):
            self.assertTrue(handle)
            self.addCleanup(kernel.CloseHandle, handle)
        lease_fd = os.open(self.root / '.pce-recovery.lock', os.O_CREAT | os.O_RDWR | os.O_BINARY)
        request_read, request_write = os.pipe()
        response_read, response_write = os.pipe()
        descriptors = [lease_fd, request_read, request_write, response_read, response_write]
        try:
            payload = dict(command=['not-executed'], env={}, cwd=str(self.root))
            os.write(request_write, json.dumps(payload).encode())
            os.close(request_write)
            descriptors.remove(request_write)
            inherited = [build_process._duplicate(kernel, handle) for handle in (
                msvcrt.get_osfhandle(request_read), msvcrt.get_osfhandle(response_write),
                owner, completed, cancelled, msvcrt.get_osfhandle(lease_fd))]
            os.close(request_read)
            descriptors.remove(request_read)
            os.close(response_write)
            descriptors.remove(response_write)
            argv = [str(Path(build_process.__file__).resolve()), '--guardian', *map(str, inherited)]
            with patch.object(sys, 'argv', argv):
                with patch.object(build_process, '_run_owned',
                                  side_effect=build_process._CleanupFailure('injected unproven drain')):
                    self.assertEqual(build_process._guardian_main(), 1)
            response = json.loads(os.read(response_read, 4096))
            self.assertEqual(response['kind'], 'error')
            self.assertIn('_CleanupFailure', response['message'])
            self.assertEqual(kernel.WaitForSingleObject(completed, 0), 258)
            os.close(lease_fd)
            descriptors.remove(lease_fd)
            self.assertEqual((self.root / '.pce-recovery.lock').read_bytes(),
                             b'PCERECOMP_UNPROVEN_PROCESS_CLEANUP_V1\n')
            with self.assertRaises(ValueError):
                with _locked(self.root):
                    self.fail('quarantined cleanup must never admit recovery')
        finally:
            for descriptor in descriptors:
                os.close(descriptor)

    def test_parent_hard_kill_drains_builder_and_writer_before_immediate_resume(self):
        process = subprocess.Popen(self.runner([sys.executable, '-c', _BUILDER,
                                                str(self.root), 'wait']),
                                   env=self.env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        try:
            pids = json.loads(self.wait_file(self.root / 'pids.json'))
            self.wait_file(self.root / 'heartbeat')
            kernel, handles = self.open_processes(pids)
            self.assertTrue(all(kernel.WaitForSingleObject(h, 0) == 258 for h in handles))
            process.kill()  # Terminate ONLY the owning recovery parent, never its children.
            process.wait(timeout=10)
            # No settling sleep: recovery enters the barrier immediately.
            build_process.quiesce(self.root)
            self.assertTrue(all(kernel.WaitForSingleObject(h, 0) == 0 for h in handles))
            closed = (self.root / 'heartbeat').read_bytes()
            marker = self.root / 'resumed'
            build_process.run([sys.executable, '-c',
                               f'from pathlib import Path;Path({str(marker)!r}).write_text("ok")'],
                              env=self.env, cwd=self.root)
            self.assertEqual(marker.read_text(), 'ok')
            self.assertEqual((self.root / 'heartbeat').read_bytes(), closed)
        finally:
            if process.poll() is None:
                process.kill()
            _, stderr = process.communicate(timeout=10)
            build_process.quiesce(self.root)
            if process.returncode not in (0, 1):
                self.assertEqual(stderr, b'')

    def test_inherited_directory_lease_outlives_hard_killed_cli(self):
        from pcerecomp.build_recovery import _locked

        command = self.runner([sys.executable, '-c', _BUILDER, str(self.root), 'wait'])
        command[2] = _LEASE_RUNNER
        process = subprocess.Popen(command, env=self.env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            pids = json.loads(self.wait_file(self.root / 'pids.json'))
            self.wait_file(self.root / 'heartbeat')
            kernel, handles = self.open_processes(pids)
            process.kill()
            process.wait(timeout=10)
            deadline = time.monotonic() + 10
            while True:
                try:
                    with _locked(self.root):
                        # Actual lease acquisition, not elapsed time, is the proof.
                        self.assertTrue(all(kernel.WaitForSingleObject(h, 0) == 0
                                            for h in handles))
                        build_process.quiesce(self.root)
                    break
                except ValueError as error:
                    self.assertIn('directory is busy', str(error))
                    if time.monotonic() >= deadline:
                        self.fail('guardian did not release the lease after cleanup')
                    time.sleep(.005)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
            build_process.quiesce(self.root)

    def test_normal_builder_exit_also_terminates_lingering_writer(self):
        build_process.run([sys.executable, '-c', _BUILDER, str(self.root), 'exit'],
                          env=self.env, cwd=self.root)
        # OpenProcess may legitimately fail after exit, so use a fresh observer
        # to verify the process IDs are absent rather than assuming PID existence.
        pids = json.loads((self.root / 'pids.json').read_text())
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        kernel.CloseHandle.argtypes = [w.HANDLE]
        for pid in pids:
            handle = kernel.OpenProcess(0x100000, False, pid)
            if handle:
                try:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 0), 0)
                finally:
                    kernel.CloseHandle(handle)
            else:
                self.assertEqual(ctypes.get_last_error(), 87)  # ERROR_INVALID_PARAMETER
        build_process.quiesce(self.root)


if __name__ == '__main__':
    unittest.main()
