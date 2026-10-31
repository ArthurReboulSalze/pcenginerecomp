"""Authored real-host block overshoot and fresh-process step continuation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from scripts.dev_client import DevClient
from scripts.dev_observation import validate_paused_observation
from scripts.dev_steps import StepValidationError, admit_step, seal_step
from test_dev_observation_hosts import checkpoint_core, wire_records
from test_dev_server_cli import HEADLESS, ROOT

# SEI, CSL, three STx operations enable BG, TII $4000->$6000,65536, BRA back.
# All eight MPRs alias the same RAM bank, so every transfer byte is unchanged.
# Stack writes contain zero register values and remain outside this program.
PROGRAM = bytes.fromhex('78 54 03 05 13 80 23 00 73 00 40 00 60 00 00 80 F7')
BOUNDS = dict(max_polls=1000, max_tick_delta=5_000_000,
              max_elapsed_ns=30_000_000_000, max_frame_overshoot=16)
CONTEXT = hashlib.sha256(b'authored-aliased-ram-low-speed-block-overshoot-v1' + PROGRAM).hexdigest()


class StepHost:
    """One owned headless process; successful paths quit and wait naturally."""
    def __init__(self, root, name):
        self.directory = root / name
        self.directory.mkdir()
        self.stdout = self.directory / 'stdout.json'
        self.stderr = self.directory / 'stderr.txt'
        self.journal = self.directory / 'wire.jsonl'
        self.client = None
        command = [str(HEADLESS), str(root / 'authored.bin'), '0x100000', '0x4000',
                   ','.join(['128'] * 8), '1000', '10000000', 'hybrid',
                   '--dev-port', '0', '--dev-start-paused', 'on',
                   '--video-output', 'continuous', '--wall-seconds', '30',
                   '--checkpoint-dir', str(root / 'checkpoints'), '--checkpoint-context', CONTEXT]
        with self.stdout.open('xb') as output, self.stderr.open('xb') as errors:
            self.process = subprocess.Popen(command, cwd=self.directory, stdin=subprocess.DEVNULL, stdout=output,
                stderr=errors, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                ports = [line for line in self.stderr.read_text().splitlines()
                         if line.startswith('PCE_DEV_PORT=')]
                if ports:
                    self.port = int(ports[0].split('=', 1)[1])
                    self.client = DevClient(self.port, timeout=15, journal=self.journal)
                    break
                if self.process.poll() is not None:
                    raise AssertionError('authored host exited before TCP: ' + self.stderr.read_text())
                time.sleep(.005)
            else:
                raise AssertionError('authored host listener deadline exceeded')
        except BaseException:
            self.close()
            raise

    def finish(self, test):
        self.client.call('quit')
        self.client.close()
        self.client = None
        test.assertEqual(self.process.wait(timeout=8), 0, self.stderr.read_text())
        test.assertEqual(self.stderr.read_text().strip(), f'PCE_DEV_PORT={self.port}')
        result = json.loads(self.stdout.read_text())
        test.assertEqual(result['stop'], 'dev_quit')
        return result

    def close(self):
        if self.client is not None:
            try:
                self.client.call('quit')
            except Exception:
                pass
            finally:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=8)


def observe(test, app):
    before = app.client.call('status')
    memory = b''.join(app.client.read_memory(0x100000 + offset, 256)
                      for offset in range(0, 8192, 256))
    after = app.client.call('status')
    validate_paused_observation(before, after)
    test.assertEqual(memory, PROGRAM + bytes(8192 - len(PROGRAM)))
    test.assertEqual(after['host']['cpu']['mpr'], [128] * 8)
    return after


def advance(test, app):
    before = app.client.call('status')
    request_id = app.client._next_id
    started = time.perf_counter_ns()
    after = app.client.advance(1)
    elapsed = time.perf_counter_ns() - started
    # Two fast SEI cycles, CSL's two old/one new cycles, three five-cycle STx,
    # and a (17 + 6*65536)-cycle block at divisor12 give exactly4,719,000ticks.
    test.assertEqual((after['frame'], after['ticks']), (13, 4_719_000))
    test.assertEqual((after['host']['pc'], after['host']['native_steps'],
                      after['host']['interpreter_steps']), (0x400F, 0, 6))
    test.assertEqual(after['host']['cpu']['clock_divisor'], 12)
    return dict(before=before, after=after, request_id=request_id, elapsed_ns=elapsed)


def step_pairs(test, app, timing):
    rows = wire_records(app.journal)
    test.assertTrue(all(reply['ok'] is True for _, reply in rows))
    test.assertEqual(sum(request['cmd'] == 'step_frames' for request, _ in rows), 1)
    test.assertFalse(any(request['cmd'] in ('write_memory', 'set_input', 'clear_input', 'resume')
                         for request, _ in rows))
    selected = [(request, reply) for request, reply in rows
                if timing['request_id'] <= request['id'] <= timing['after']['id']]
    test.assertEqual(selected[-1][1], timing['after'])
    return selected[0], [dict(request=request, response=reply) for request, reply in selected[1:]], len(rows)


def exercise(test, root):
    (root / 'authored.bin').write_bytes(PROGRAM)
    (root / 'checkpoints').mkdir()
    app = StepHost(root, 'writer')
    try:
        initial = observe(test, app)
        test.assertEqual((initial['frame'], initial['ticks']), (0, 0))
        saved = app.client.call('save_checkpoint', name='origin.pcec')['checkpoint']
        first = advance(test, app)
        endpoint = observe(test, app)
        validate_paused_observation(first['after'], endpoint)
        end_saved = app.client.call('save_checkpoint', name='writer-end.pcec')['checkpoint']
        writer = app.finish(test)
    finally:
        app.close()
    old_request, old_polls, writer_pairs = step_pairs(test, app, first)
    seal = seal_step(first['before'], old_request[0], old_request[1], old_polls,
                     bounds=BOUNDS, elapsed_ns=first['elapsed_ns'],
                     initial_observation='frame-zero-bootstrap')
    test.assertEqual((seal['summary']['target_frame'], seal['summary']['final_frame']), (1, 13))
    with test.assertRaises(StepValidationError):
        seal_step(first['before'], old_request[0], old_request[1], old_polls,
                  bounds={**BOUNDS, 'max_frame_overshoot': 0}, elapsed_ns=first['elapsed_ns'])
    app = StepHost(root, 'restorer')
    try:
        test.assertEqual(app.client.call('load_checkpoint', name='origin.pcec')['checkpoint'], saved)
        restored = observe(test, app)
        test.assertEqual(restored['host']['cpu'], initial['host']['cpu'])
        test.assertEqual(restored['host']['checkpoint']['window'],
                         dict(ticks=0, native_steps=0, interpreter_steps=0))
        app.client.call('save_checkpoint', name='roundtrip.pcec')
        second = advance(test, app)
        continued = observe(test, app)
        test.assertEqual(continued['host']['cpu'], endpoint['host']['cpu'])
        test.assertEqual(app.client.call('save_checkpoint', name='restored-end.pcec')['checkpoint'], end_saved)
        restorer = app.finish(test)
    finally:
        app.close()
    new_request, new_polls, restorer_pairs = step_pairs(test, app, second)
    admission = admit_step(seal, second['before'], new_request[0], new_request[1], new_polls,
                           elapsed_ns=second['elapsed_ns'])
    test.assertFalse(admission['endpoint_guest_state_compared'])
    for before, after in (('origin.pcec', 'roundtrip.pcec'), ('writer-end.pcec', 'restored-end.pcec')):
        a, b = root / 'checkpoints' / before, root / 'checkpoints' / after
        test.assertEqual(a.read_bytes(), b.read_bytes())
        test.assertEqual(checkpoint_core(a), checkpoint_core(b))
    for report in (writer, restorer):
        for key, value in dict(cycles=393253, ticks=4719000, native_steps=0, interpreter_steps=6,
                               interpreter_block_steps=1, native_block_steps=0, block_bytes=65536,
                               irq_entries=0, rti_steps=0).items():
            test.assertEqual(report[key], value, key)
    return dict(result='pass', seal=seal, admission=admission, writer=writer, restorer=restorer,
                wire_pairs=writer_pairs + restorer_pairs, complete_roundtrip_and_continuation_equal=True)


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless runner')
class SemanticStepHostTests(unittest.TestCase):
    def test_natural_block_overshoot_and_fresh_checkpoint_continuation(self):
        evidence = os.environ.get('PCE_TEST_STEPS_EVIDENCE')
        if evidence:
            root = Path(evidence)
            self.assertTrue(root.is_absolute() and root.resolve().is_relative_to(ROOT / '.local'))
            root.mkdir(parents=True)  # Never overwrite retained evidence.
            result = exercise(self, root)
            (root / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
        else:
            with tempfile.TemporaryDirectory() as directory:
                exercise(self, Path(directory))


if __name__ == '__main__':
    unittest.main()
