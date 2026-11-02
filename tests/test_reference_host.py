"""Authored paused reference windows through the production TCP host."""
import json
from pathlib import Path
import tempfile
import unittest

from test_checkpoint_cli import wait_paused
from test_dev_server_cli import HEADLESS, DESKTOP, RunningSandbox
from scripts.dev_client import DevError
from pcerecomp.capture import load_capture


def close_naturally(test, app):
    app.client.call('quit')
    stdout, stderr = app.process.communicate(timeout=5)
    test.assertEqual(app.process.returncode, 0, stderr)
    return json.loads(stdout)


def reference_checkpoint(test, binary, *, desktop=False):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        shared = ['--checkpoint-dir', str(root), '--checkpoint-context', 'd'*64,
                  '--dev-reference', 'on', '--native-span', '1']
        baseline = RunningSandbox(binary, root, desktop=desktop, extra_options=shared)
        try:
            initial = baseline.client.call('status')['host']['execution_policy']
            test.assertEqual(initial, {'schema': 1, 'reference_enabled': True, 'selected': False,
                'configured_tier': 'hybrid', 'effective_policy': 'hybrid', 'effective_native_span': 1})
            wait_paused(baseline.client, baseline.client.call('step_frames', frames=2)['target_frame'])
            with test.assertRaisesRegex(DevError, 'first dispatch'):
                baseline.client.call('reference_frames', frames=1)
            saved = baseline.client.call('save_checkpoint', name='enabled.pcec')['checkpoint']
            close_naturally(test, baseline)
        finally:
            baseline.close()
        capture_path = root/'reference.json'
        resumed = RunningSandbox(binary, root, desktop=desktop,
            extra_options=shared+['--code-capture', str(capture_path)])
        try:
            test.assertEqual(resumed.client.call('load_checkpoint', name='enabled.pcec')['checkpoint'], saved)
            copied = resumed.client.call('save_checkpoint', name='immediate.pcec')['checkpoint']
            test.assertEqual(copied['sha256'], saved['sha256'])
            test.assertEqual((root/'immediate.pcec').read_bytes(), (root/'enabled.pcec').read_bytes())
            origin = resumed.client.call('status')['host']['checkpoint']['origin']
            pending = resumed.client.capture_summary()
            test.assertFalse(pending['execution_policy']['selected'])
            test.assertEqual(pending['retired_instructions'], 0)
            # Parser-level malformed types close the strict client; those
            # independent wire refusals are covered by dev_server_tests.cpp.
            for frames in (0, 601):
                with test.assertRaises(DevError):
                    resumed.client.call('reference_frames', frames=frames)
            first = resumed.client.advance(2, reference=True)
            test.assertTrue(first['host']['execution_policy']['selected'])
            test.assertEqual(first['host']['execution_policy']['effective_policy'], 'interpreter')
            test.assertEqual(first['host']['execution_policy']['effective_native_span'], 0)
            test.assertEqual(first['host']['checkpoint']['origin'], origin)
            test.assertEqual(first['host']['checkpoint']['window']['native_steps'], 0)
            test.assertGreater(first['host']['checkpoint']['window']['interpreter_steps'], 0)
            for command, arguments in (('resume', {}), ('step_frames', {'frames': 1}),
                                       ('load_checkpoint', {'name': 'enabled.pcec'})):
                with test.assertRaises(DevError):
                    resumed.client.call(command, **arguments)
            resumed.client.call('set_input', mask=8)
            second = resumed.client.advance(1, reference=True)
            test.assertEqual(second['frame'], first['frame']+1)
            test.assertEqual(second['host']['checkpoint']['origin'], origin)
            test.assertEqual(second['host']['checkpoint']['window']['native_steps'], 0)
            test.assertGreater(second['host']['checkpoint']['window']['interpreter_steps'],
                               first['host']['checkpoint']['window']['interpreter_steps'])
            summary = resumed.client.capture_summary()
            history = resumed.client.capture_history()
            test.assertEqual(summary['execution_policy'], second['host']['execution_policy'])
            test.assertEqual(history['execution_policy'], summary['execution_policy'])
            test.assertGreater(len(history['sources']), 0)
            test.assertEqual(history['native_instructions'], 0)
            test.assertEqual(history['interpreted_instructions'],
                             second['host']['checkpoint']['window']['interpreter_steps'])
            after_inspection = resumed.client.call('status')
            test.assertEqual((after_inspection['ticks'], after_inspection['frame']),
                             (second['ticks'], second['frame']))
            test.assertEqual(after_inspection['host']['checkpoint'], second['host']['checkpoint'])
            resumed.client.call('save_checkpoint', name='reference-end.pcec')
            result = close_naturally(test, resumed)
        finally:
            resumed.close()
        capture, _ = load_capture(capture_path)
        test.assertEqual(capture['execution_policy'], result['execution_policy'])
        test.assertEqual(capture['checkpoint_origin'], origin)
        test.assertEqual(capture['retired_instructions'], result['checkpoint']['window']['interpreter_steps'])
        test.assertTrue(all(row['native_hits'] == 0 for row in capture['observations']))
        for key in ('batches', 'generated_calls', 'native_completed', 'interpreted_completed',
                    'local_continuations', 'max_completed'):
            test.assertEqual(result['native_dispatch'][key], 0)
        # Disabling the capability changes the identity even for the same build.
        disabled = RunningSandbox(binary, root, desktop=desktop,
            extra_options=['--checkpoint-dir', str(root), '--checkpoint-context', 'd'*64,
                           '--native-span', '1'])
        try:
            before = disabled.client.call('status')
            test.assertNotIn('execution_policy', before['host'])
            with test.assertRaisesRegex(DevError, 'identity mismatch'):
                disabled.client.call('load_checkpoint', name='enabled.pcec')
            with test.assertRaisesRegex(DevError, 'opt-in'):
                disabled.client.call('reference_frames', frames=1)
            after = disabled.client.call('status')
            test.assertEqual((before['ticks'], before['frame']), (after['ticks'], after['frame']))
            close_naturally(test, disabled)
        finally:
            disabled.close()


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless runner')
class ReferenceHostTests(unittest.TestCase):
    def test_headless_checkpoint_reference_window(self):
        reference_checkpoint(self, HEADLESS)

    @unittest.skipUnless(DESKTOP.is_file(), 'Build the desktop runner')
    def test_desktop_checkpoint_reference_window(self):
        reference_checkpoint(self, DESKTOP, desktop=True)
