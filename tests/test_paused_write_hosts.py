"""Authored same-WRAM paused CAS, real TCP, and fresh checkpoint continuation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from pcerecomp.analysis import Snapshot, analyze
from pcerecomp.emitter import emit
from scripts.dev_client import DevClient, DevError
from scripts.dev_observation import ObservationError, validate_paused_observation
from scripts.dev_write import WORK_RAM_MIRRORS, validate_paused_write
from test_dev_observation_hosts import checkpoint_core, wire_records
from test_dev_server_cli import HEADLESS, DESKTOP, ROOT


BASE = 0x1F0000
LOAD = BASE + 0x400
MPR = (255, 248, 128, 129, 130, 131, 132, 0)
# SEI, CSH, enable BG, then a native-capable self-loop in work RAM.
# No guest instruction writes the data edited through TCP below.
PROGRAM = bytes.fromhex('78 D4 03 05 13 80 23 00 80 FE')
FOOTPRINT = frozenset(range(LOAD, LOAD + len(PROGRAM)))


class WriteHost:
    """Own one subprocess and retain exact raw request/reply bytes."""
    def __init__(self, binary, root, name, *, desktop=False, tier='hybrid'):
        self.directory = root / name
        self.directory.mkdir()
        self.stdout = self.directory / 'stdout.json'
        self.stderr = self.directory / 'stderr.txt'
        self.journal = self.directory / 'wire.jsonl'
        self.client = None
        command = [str(binary), str(root / 'authored.bin'), hex(LOAD), '0x2400',
                   ','.join(map(str, MPR)), '500000000', '3000000000', tier,
                   '--dev-port', '0', '--dev-start-paused', 'on',
                   '--dev-memory-write', 'on', '--wall-seconds', '30',
                   '--checkpoint-dir', str(root / 'checkpoints'),
                   '--checkpoint-context', 'c' * 64]
        if desktop:
            command += ['--hidden', 'on', '--unthrottled', 'on', '--window-scale', '1']
        self.command = command
        environment = os.environ.copy()
        environment.update(SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software',
                           SDL_AUDIODRIVER='dummy')
        with self.stdout.open('xb') as output, self.stderr.open('xb') as errors:
            self.process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                            stdout=output, stderr=errors, env=environment,
                                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                ports = [line for line in self.stderr.read_text().splitlines()
                         if line.startswith('PCE_DEV_PORT=')]
                if ports:
                    self.port = int(ports[0].split('=', 1)[1])
                    self.client = DevClient(self.port, timeout=8, journal=self.journal)
                    break
                if self.process.poll() is not None:
                    raise AssertionError('authored write host exited before TCP: ' + self.stderr.read_text())
                time.sleep(.005)
            else:
                raise AssertionError('authored write host listener deadline exceeded')
        except BaseException:
            self.close()
            raise

    def finish(self, test):
        self.client.call('quit')
        self.client.close()
        self.client = None
        test.assertEqual(self.process.wait(timeout=5), 0, self.stderr.read_text())
        test.assertEqual(self.stderr.read_text().strip(), f'PCE_DEV_PORT={self.port}')
        result = json.loads(self.stdout.read_text())
        test.assertEqual(result['stop'], 'dev_quit')
        return result

    def close(self):
        if self.client is not None:
            try:
                self.client.call('quit')
            except (OSError, RuntimeError):
                pass
            finally:
                self.client.close()
                self.client = None
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)


def ram(client):
    return b''.join(client.read_memory(BASE + offset, 256) for offset in range(0, 8192, 256))


def cpu_source(test, state):
    cpu = state['host']['cpu']
    test.assertEqual(state['host']['pc'], 0x2408)
    test.assertEqual(cpu['mpr'], list(MPR))
    test.assertEqual(cpu['instruction_physical'], list(range(LOAD + 8, LOAD + 15)))
    test.assertEqual(cpu['instruction_bytes'], [0x80, 0xFE, 0, 0, 0, 0, 0])
    test.assertEqual(len(set(cpu['instruction_generations'])), 1)
    return cpu


def write_checked(test, app, address, data, expected):
    before = app.client.call('status')
    before_ram = ram(app.client)
    settled = app.client.call('status')
    validate_paused_observation(before, settled)
    request = dict(id=app.client._next_id, cmd='write_memory', address=address,
                   data=data.hex(), expected=expected.hex())
    acknowledgement = app.client.write_memory(address, data, expected)
    after_ram = ram(app.client)
    after = app.client.call('status')
    proof = validate_paused_write(settled, after, request=request,
                                 acknowledgement=acknowledgement,
                                 memory_before=before_ram, memory_after=after_ram,
                                 profile=WORK_RAM_MIRRORS, code_footprint=FOOTPRINT)
    changed = sum(a != b for a, b in zip(data, expected))
    test.assertEqual(after['host']['cpu']['instruction_generations'],
                     [value + changed for value in settled['host']['cpu']['instruction_generations']])
    test.assertEqual(after['host']['cpu']['instruction_bytes'], settled['host']['cpu']['instruction_bytes'])
    if changed:
        with test.assertRaises(ObservationError):
            validate_paused_observation(settled, after)
    pairs = wire_records(app.journal)
    test.assertIn((request, acknowledgement), pairs)
    return after, after_ram, proof


def exercise_write(test, binary, root, *, desktop=False, tier='hybrid', expect_native=False):
    (root / 'authored.bin').write_bytes(PROGRAM)
    (root / 'checkpoints').mkdir()
    app = WriteHost(binary, root, 'writer', desktop=desktop, tier=tier)
    proofs = []
    try:
        app.client.advance(1)
        initial = app.client.call('status')
        cpu_source(test, initial)
        test.assertGreater(initial['ticks'], 0)
        # All mirrored aliases refer to the same canonical 8 KiB byte array.
        state, data, proof = write_checked(test, app, 0x1F2300, b'\x10\0\x20\0', bytes(4))
        proofs.append(proof)
        for bank in range(0xF8, 0xFC):
            test.assertEqual(app.client.read_memory((bank << 13) + 0x300, 4), b'\x10\0\x20\0')
        state, data, proof = write_checked(test, app, 0x1F6300, b'\x10\0\x20\0', b'\x10\0\x20\0')
        proofs.append(proof)
        # One submitted range crosses the F9->FA mirror/backing wrap.
        state, data, proof = write_checked(test, app, 0x1F3FFF, b'\x31\x42\x53', bytes(3))
        proofs.append(proof)
        expected = bytearray(8192)
        expected[0x400:0x400 + len(PROGRAM)] = PROGRAM
        expected[0x300:0x304] = b'\x10\0\x20\0'
        expected[0x1FFF] = 0x31
        expected[:2] = b'\x42\x53'
        test.assertEqual(data, bytes(expected))
        before = app.client.call('status')
        with test.assertRaises(DevError):
            app.client.write_memory(0x1F4300, b'\x99', b'\0')
        test.assertEqual(ram(app.client), data)
        validate_paused_observation(before, app.client.call('status'))
        saved = app.client.call('save_checkpoint', name='frontier.pcec')['checkpoint']
        frontier = app.client.call('status')
        cpu_source(test, frontier)
        app.client.advance(2)
        endpoint = app.client.call('status')
        cpu_source(test, endpoint)
        test.assertEqual(ram(app.client), data)
        end_saved = app.client.call('save_checkpoint', name='writer-end.pcec')['checkpoint']
        writer_final = app.finish(test)
    finally:
        app.close()

    app = WriteHost(binary, root, 'restorer', desktop=desktop, tier=tier)
    try:
        test.assertEqual(app.client.call('load_checkpoint', name='frontier.pcec')['checkpoint'], saved)
        restored = app.client.call('status')
        test.assertEqual(restored['host']['cpu'], frontier['host']['cpu'])
        test.assertEqual(restored['host']['checkpoint']['window'],
                         {'ticks': 0, 'native_steps': 0, 'interpreter_steps': 0})
        test.assertEqual(ram(app.client), data)
        app.client.call('save_checkpoint', name='roundtrip.pcec')
        test.assertEqual((root / 'checkpoints/frontier.pcec').read_bytes(),
                         (root / 'checkpoints/roundtrip.pcec').read_bytes())
        app.client.advance(2)
        continued = app.client.call('status')
        test.assertEqual(continued['host']['cpu'], endpoint['host']['cpu'])
        test.assertEqual(continued['ticks'], endpoint['ticks'])
        test.assertEqual(ram(app.client), data)
        test.assertEqual(app.client.call('save_checkpoint', name='restored-end.pcec')['checkpoint'], end_saved)
        test.assertEqual((root / 'checkpoints/writer-end.pcec').read_bytes(),
                         (root / 'checkpoints/restored-end.pcec').read_bytes())
        test.assertEqual(checkpoint_core(root / 'checkpoints/writer-end.pcec'),
                         checkpoint_core(root / 'checkpoints/restored-end.pcec'))
        new_work = continued['host']['checkpoint']['window']
        test.assertGreater(new_work['ticks'], 0)
        test.assertGreater(new_work['native_steps'] if expect_native else new_work['interpreter_steps'], 0)
        if expect_native:
            test.assertEqual(new_work['interpreter_steps'], 0)
        restorer_final = app.finish(test)
    finally:
        app.close()
    pairs = [pair for name in ('writer', 'restorer')
             for pair in wire_records(root / name / 'wire.jsonl')]
    return dict(result='pass', profile=WORK_RAM_MIRRORS, writer_final=writer_final,
                restorer_final=restorer_final, imported=saved, new_work=new_work,
                proofs=proofs, wire_pairs=len(pairs), positive_cas=3,
                changed_bytes=5, stale_refusals=1, fresh_restores=1,
                roundtrip_complete_bytes_equal=True, continued_complete_bytes_equal=True)


def run_case(test, binary, label, **options):
    evidence = os.environ.get('PCE_TEST_PAUSED_WRITE_EVIDENCE')
    if evidence:
        root = Path(evidence) / label
        test.assertTrue(root.is_absolute() and root.resolve().is_relative_to(ROOT / '.local'))
        root.mkdir(parents=True)
        result = exercise_write(test, binary, root, **options)
        from scripts import dev_client, dev_write, dev_observation
        files = [Path(__file__), Path(dev_client.__file__), Path(dev_write.__file__),
                 Path(dev_observation.__file__), binary, *sorted(root.rglob('*'))]
        result['bindings'] = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in files if path.is_file()}
        (root / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    else:
        with tempfile.TemporaryDirectory() as temporary:
            exercise_write(test, binary, Path(temporary), **options)


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless runner')
class PausedWriteHeadlessTests(unittest.TestCase):
    def test_same_wram_cas_and_fresh_checkpoint_continuation(self):
        run_case(self, HEADLESS, 'headless')


@unittest.skipUnless(DESKTOP.is_file(), 'Build the optional desktop runner')
class PausedWriteDesktopTests(unittest.TestCase):
    def test_same_wram_cas_and_fresh_checkpoint_continuation(self):
        run_case(self, DESKTOP, 'desktop', desktop=True)


COMPILER = shutil.which('clang++') or shutil.which('g++')


@unittest.skipUnless(shutil.which('cmake') and shutil.which('ninja') and COMPILER,
                     'CMake/Ninja/C++ compiler required for translated WRAM execution')
class PausedWriteNativeTests(unittest.TestCase):
    def test_translated_wram_survives_data_generation_change_and_restore(self):
        evidence = os.environ.get('PCE_TEST_PAUSED_WRITE_EVIDENCE')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(evidence) / 'native-build' if evidence else Path(temporary)
            base.mkdir(parents=True, exist_ok=not bool(evidence))
            module = base / 'module'
            snapshot = Snapshot(MPR, dict(enumerate(PROGRAM, LOAD)), (0x2400,),
                                hashlib.sha256(PROGRAM).hexdigest())
            emit(analyze(snapshot), module)
            wrapper = base / 'wrapper'
            wrapper.mkdir()
            (wrapper / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.20)
project(PausedWriteNative LANGUAGES CXX)
set(PCE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory("{ROOT.as_posix()}" tool)
pce_add_consumer(write-native MODULE "{(module / 'module.cpp').as_posix()}" MANIFEST "{(module / 'module.json').as_posix()}")
''', encoding='utf-8')
            commands = (['cmake', '-S', str(wrapper), '-B', str(base / 'build'), '-G', 'Ninja',
                         '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_COMPILER=' + COMPILER],
                        ['cmake', '--build', str(base / 'build'), '--target', 'write-native', '--parallel', '2'])
            for index, command in enumerate(commands):
                run = subprocess.run(command, capture_output=True, text=True, timeout=180)
                if evidence:
                    (base / f'build-{index}.log').write_text(run.stdout + run.stderr)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            binary = base / 'build' / ('write-native.exe' if os.name == 'nt' else 'write-native')
            run_case(self, binary, 'native', tier='native', expect_native=True)


if __name__ == '__main__':
    unittest.main()
