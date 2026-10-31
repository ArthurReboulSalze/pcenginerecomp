"""Authored paused source-history probes across the actual shared host loop."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.capture import load_capture
from scripts.dev_client import DevClient, DevError
from test_reset_boot import authored_card

ROOT = Path(__file__).resolve().parent.parent
EXE = '.exe' if os.name == 'nt' else ''
HEADLESS = Path(os.environ.get('PCE_TEST_HEADLESS', ROOT/'build'/('pce-headless'+EXE)))
DESKTOP = Path(os.environ.get('PCE_TEST_DESKTOP', 'disabled'))
MPRS = '255,248,128,129,130,131,132,0'
# LDA #variant; STA work RAM; INC the immediate operand; BRA back to LDA.
MUTATING = bytes.fromhex('A9 01 8D 00 20 EE 01 40 80 F6')


class LiveRunner:
    def __init__(self, test, directory, *, capture=True, limit=16384, start=None, arcade=False):
        self.test = test
        self.directory = directory
        directory.mkdir()
        self.output = directory/'capture.json'
        image = directory/'authored.bin'
        options = ['--video-output', 'continuous', '--dev-port', '0',
                   '--dev-start-paused', 'on', '--wall-seconds', '20']
        if capture:
            options += ['--code-capture', str(self.output), '--capture-limit', str(limit)]
        if start is not None:
            options += ['--code-capture-start-frame', str(start)]
        if arcade:
            # Map five logical pages to side-effecting data-port windows. Slow
            # CPU speed keeps the first frame entirely inside these pages.
            # Port zero without auto-increment yields a real fetched NOP on
            # every access; setup and the JMP remain ordinary firmware code.
            program = bytes.fromhex('78 A9 FF 53 01 A9 F8 53 02 A9 40 53 7C A9 EA 8D 00 1A 4C 00 40')
            image.write_bytes(authored_card(program))
            command = [str(test.binary), '--system-card-reset', 'super', str(image),
                       '1000000', '100000000', 'hybrid', '--arcade-card', 'duo', *options]
        else:
            image.write_bytes(MUTATING)
            command = [str(test.binary), str(image), '0x100000', '0x4000', MPRS,
                       '1000000', '100000000', 'hybrid', *options]
        if test.desktop:
            command += ['--hidden', 'on', '--unthrottled', 'on', '--window-scale', '1']
        environment = os.environ.copy()
        environment.update(SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software', SDL_AUDIODRIVER='dummy')
        self.process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, env=environment)
        test.addCleanup(self.close)
        line = self.process.stderr.readline()
        test.assertTrue(line.startswith('PCE_DEV_PORT='), line)
        self.client = DevClient(int(line.strip().split('=')[1]), timeout=10)

    def finish(self):
        self.client.call('quit')
        stdout, stderr = self.process.communicate(timeout=10)
        self.test.assertEqual(self.process.returncode, 0, stderr)
        state = json.loads(stdout)
        self.test.assertEqual(state['stop'], 'dev_quit')
        return state

    def close(self):
        if hasattr(self, 'client'):
            self.client.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.communicate(timeout=5)


class LiveCaptureChecks:
    desktop = False

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def runner(self, name, **options):
        return LiveRunner(self, self.root/name, **options)

    def assert_pure(self, runner, action):
        before = runner.client.call('status')
        try:
            return action()
        finally:
            after = runner.client.call('status')
            self.assertEqual({k:v for k,v in before.items() if k != 'id'},
                             {k:v for k,v in after.items() if k != 'id'})
            if runner.output.exists():
                self.assertEqual(runner.output.stat().st_size, 0)

    def test_exact_variant_history_is_pure_and_preserves_final_capture_bytes(self):
        runner = self.runner('observed')
        initial = self.assert_pure(runner, runner.client.capture_summary)
        self.assertTrue(initial['enabled'])
        self.assertFalse(initial['window']['started'])
        self.assertEqual(initial['retired_instructions'], 0)
        runner.client.advance(1)
        history = self.assert_pure(runner, runner.client.capture_history)
        self.assertTrue(history['window']['started'])
        self.assertTrue(history['complete'])
        self.assertGreater(history['identity_count'], 256)
        self.assertEqual(history['native_instructions'], 0)
        variants = [source for source in history['sources'] if source['pc'] == 0x4000]
        self.assertEqual(len(variants), 256)
        self.assertEqual(len({row['source_id'] for row in variants}), 256)
        for row in variants:
            self.assertEqual(row['mpr'], [255,248,128,129,130,131,132,0])
            self.assertEqual(row['physical'], [0x100000,0x100001])
            self.assertEqual(set(row), {'source_id','pc','mpr','physical','native_hits','interpreted_hits'})
        self.assertEqual({source['pc'] for source in history['sources']}, {0x4000,0x4002,0x4005,0x4008})
        token = history['retired_instructions']
        page = self.assert_pure(runner, lambda: runner.client.capture_sources(256, 256, token))
        self.assertTrue(page['done'])
        self.assertEqual(page['sources'], history['sources'][256:])
        terminal = runner.client.capture_sources(history['identity_count'], 1, token)
        self.assertEqual(terminal['sources'], [])
        def outside_page():
            with self.assertRaises(DevError):
                runner.client.capture_sources(history['identity_count']+1, 1, token)
        self.assert_pure(runner, outside_page)
        runner.client.advance(1)
        def stale_page():
            with self.assertRaisesRegex(DevError, 'stale'):
                runner.client.capture_sources(0, 1, token)
        self.assert_pure(runner, stale_page)
        final_history = self.assert_pure(runner, runner.client.capture_history)
        observed = runner.finish()
        final_capture, _ = load_capture(runner.output)
        self.assertEqual(final_history['retired_instructions'], final_capture['retired_instructions'])
        expected = {(row['pc'], tuple(row['mpr']), tuple(row['physical']), row['native_hits'], row['interpreted_hits'])
                    for row in final_capture['observations']}
        actual = {(row['pc'], tuple(row['mpr']), tuple(row['physical']), row['native_hits'], row['interpreted_hits'])
                  for row in final_history['sources']}
        self.assertEqual(actual, expected)
        plain = self.runner('plain')
        plain.client.advance(1)
        plain.client.advance(1)
        baseline = plain.finish()
        self.assertEqual(runner.output.read_bytes(), plain.output.read_bytes())
        # Host polling is intentionally more frequent during inspection. Guest
        # state and captured bytes must remain identical, not SDL poll totals.
        observed.pop('desktop', None)
        baseline.pop('desktop', None)
        observed['development'].pop('port')
        baseline['development'].pop('port')
        self.assertEqual(observed, baseline)

    def test_deferred_window_and_capacity_loss_remain_explicit(self):
        runner = self.runner('deferred', limit=1, start=2)
        runner.client.advance(1)
        armed = self.assert_pure(runner, runner.client.capture_history)
        self.assertFalse(armed['window']['started'])
        self.assertEqual(armed['sources'], [])
        runner.client.advance(2)
        history = self.assert_pure(runner, runner.client.capture_history)
        window = history['window']
        self.assertEqual(window['requested_start_frame'], 2)
        self.assertEqual(window['actual_start_frame'], 2)
        self.assertEqual(window['current_frame'], 3)
        self.assertFalse(history['complete'])
        self.assertEqual(history['identity_count'], 1)
        self.assertGreater(history['dropped_instructions'], 0)
        self.assertEqual(history['unreadable_instructions'], 0)
        self.assertEqual(history['interpreted_instructions'],
                         window['current_interpreter_steps']-window['interpreter_steps_before'])
        self.assertEqual(history['retained_interpreted_instructions']+history['dropped_instructions'],
                         history['retired_instructions'])
        runner.finish()
        final, _ = load_capture(runner.output)
        for key in ('complete','capacity','retired_instructions','unreadable_instructions','dropped_instructions'):
            self.assertEqual(history[key], final[key])

    def test_unreadable_port_fetches_report_loss_without_extra_port_accesses(self):
        runner = self.runner('unreadable', arcade=True)
        runner.client.advance(1)
        history = self.assert_pure(runner, runner.client.capture_history)
        self.assertFalse(history['complete'])
        self.assertGreater(history['unreadable_instructions'], 100)
        self.assertEqual(history['dropped_instructions'], 0)
        self.assertEqual(history['retained_interpreted_instructions']+history['unreadable_instructions'],
                         history['retired_instructions'])
        self.assertTrue(all(all(not 0x80000 <= address < 0x88000 for address in row['physical'])
                            for row in history['sources']))
        final = runner.finish()
        self.assertEqual(final['arcade_card']['reads'], history['unreadable_instructions'])

    def test_disabled_capture_and_running_inspection_refuse_explicitly(self):
        runner = self.runner('disabled', capture=False)
        summary = self.assert_pure(runner, runner.client.capture_summary)
        self.assertEqual(summary, {'schema':1, 'runtime_abi':ABI, 'enabled':False})
        with self.assertRaisesRegex(DevError, 'disabled'):
            runner.client.capture_history()
        with self.assertRaisesRegex(DevError, 'disabled'):
            runner.client.capture_sources(0, 1, 0)
        runner.client.call('resume')
        with self.assertRaisesRegex(DevError, 'quiescent pause'):
            runner.client.capture_summary()
        runner.client.call('pause')
        self.assertEqual(runner.client.capture_summary(), summary)
        runner.finish()
        self.assertFalse(runner.output.exists())


@unittest.skipUnless(HEADLESS.is_file(), 'Build headless for live capture checks')
class HeadlessLiveCaptureTests(LiveCaptureChecks, unittest.TestCase):
    binary = HEADLESS


@unittest.skipUnless(DESKTOP.is_file(), 'Build desktop for live capture checks')
class DesktopLiveCaptureTests(LiveCaptureChecks, unittest.TestCase):
    binary = DESKTOP
    desktop = True


if __name__ == '__main__':
    unittest.main()
