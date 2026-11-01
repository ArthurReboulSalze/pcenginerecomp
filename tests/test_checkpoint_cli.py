"""Authored TCP checkpoint files through the production host, never retail data."""
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import wave

from test_dev_server_cli import HEADLESS, DESKTOP, RunningSandbox
from scripts.dev_client import DevError


def wait_paused(client, target):
    end = time.monotonic()+8
    while time.monotonic() < end:
        state = client.call('status')
        if state['paused'] and state['frame'] >= target:
            return state
        time.sleep(.005)
    raise AssertionError('authored frame step timed out')


def comparable(state):
    result = copy.deepcopy(state)
    result.pop('id')
    result['host'].pop('checkpoint', None)
    result['host']['audio_output'].pop('wav_frames', None)
    result['host']['audio_output'].pop('host', None) # Fresh SDL queues are host presentation, not guest state.
    return result


def exercise(test, binary, desktop=False):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        opts = ['--checkpoint-dir', str(root), '--checkpoint-context', 'a'*64,
                '--audio-output', 'on', '--audio-profile', 'filtered', '--audio-rate', '48000']
        app = RunningSandbox(binary, root, desktop=desktop, bios=True,
                             extra_options=opts+['--audio-out', str(root/'baseline.wav')])
        try:
            target = app.client.call('step_frames', frames=3)['target_frame']
            wait_paused(app.client, target)
            app.client.call('set_input', port=2, mask=0x821)
            initial = app.client.call('status')
            saved = app.client.call('save_checkpoint', name='frontier.pcec')['checkpoint']
            test.assertEqual(initial['ticks'], saved['ticks'])
            test.assertEqual(comparable(initial), comparable(app.client.call('status')))
            for name in ('frontier.pcec', '../bad.pcec', 'CON.pcec', 'bad:stream.pcec'):
                with test.assertRaises(DevError):
                    app.client.call('save_checkpoint', name=name)
                test.assertEqual(comparable(initial), comparable(app.client.call('status')))
            with test.assertRaises(DevError):
                app.client.call('load_checkpoint', name='frontier.pcec')
            endpoint = wait_paused(app.client, app.client.call('step_frames', frames=2)['target_frame'])
            final_saved = app.client.call('save_checkpoint', name='baseline-end.pcec')['checkpoint']
            app.client.call('quit')
            stdout, stderr = app.process.communicate(timeout=5)
            test.assertEqual(app.process.returncode, 0, stderr)
            test.assertEqual(json.loads(stdout)['checkpoint'], {'resumed': False})
        finally:
            app.close()

        # Fresh process, same binary and exact recipe; outputs are fresh windows.
        app = RunningSandbox(binary, root, desktop=desktop, bios=True,
                             extra_options=opts+['--audio-out', str(root/'resumed.wav'),
                                                 '--code-capture', str(root/'capture.json')])
        try:
            before = app.client.call('status')
            corrupt = bytearray((root/'frontier.pcec').read_bytes())
            corrupt[-1] ^= 1
            (root/'corrupt.pcec').write_bytes(corrupt)
            for name in ('corrupt.pcec', 'missing.pcec', '../frontier.pcec'):
                with test.assertRaises(DevError):
                    app.client.call('load_checkpoint', name=name)
                test.assertEqual(comparable(before), comparable(app.client.call('status')))
            loaded = app.client.call('load_checkpoint', name='frontier.pcec')['checkpoint']
            test.assertEqual(loaded, saved)
            state = app.client.call('status')
            test.assertEqual(comparable(initial), comparable(state))
            test.assertEqual(state['host']['checkpoint']['window'],
                             {'ticks': 0, 'native_steps': 0, 'interpreter_steps': 0})
            test.assertEqual(app.client.capture_summary()['checkpoint_origin'], state['host']['checkpoint']['origin'])
            restored = wait_paused(app.client, app.client.call('step_frames', frames=2)['target_frame'])
            test.assertEqual(app.client.capture_summary()['checkpoint_origin'], state['host']['checkpoint']['origin'])
            test.assertEqual(comparable(endpoint), comparable(restored))
            resumed_end = app.client.call('save_checkpoint', name='resumed-end.pcec')['checkpoint']
            test.assertEqual(final_saved['payload_sha256'], resumed_end['payload_sha256'])
            app.client.call('quit')
            stdout, stderr = app.process.communicate(timeout=5)
            test.assertEqual(app.process.returncode, 0, stderr)
            result = json.loads(stdout)
            origin = result['checkpoint']['origin']
            test.assertEqual(origin['sha256'], saved['sha256'])
            test.assertEqual(result['checkpoint']['audio_origin'], {
                'pending_pcm_frames': saved['pending_pcm_frames'], 'source_wav_frames': saved['source_wav_frames']})
            capture = json.loads((root/'capture.json').read_text())
            test.assertEqual(capture['checkpoint_origin'], origin)
            test.assertEqual(capture['retired_instructions'], result['checkpoint']['window']['interpreter_steps'])
        finally:
            app.close()
        with wave.open(str(root/'baseline.wav')) as source, wave.open(str(root/'resumed.wav')) as resumed:
            source.setpos(saved['source_wav_frames'])
            test.assertEqual(source.readframes(source.getnframes()), resumed.readframes(resumed.getnframes()))


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless runner')
class CheckpointCliTests(unittest.TestCase):
    def test_exact_fresh_process_tcp_continuation_and_rejections(self):
        exercise(self, HEADLESS)

    def test_checkpoint_commands_require_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = RunningSandbox(HEADLESS, Path(tmp))
            try:
                before = app.client.call('status')
                for command in ('load_checkpoint', 'save_checkpoint'):
                    with self.assertRaises(DevError):
                        app.client.call(command, name='test.pcec')
                self.assertEqual({k:v for k,v in before.items() if k!='id'},
                                 {k:v for k,v in app.client.call('status').items() if k!='id'})
            finally:
                app.close()

    def test_reviewed_context_mismatch_rejects_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opts = ['--checkpoint-dir', str(root), '--checkpoint-context']
            first = RunningSandbox(HEADLESS, root, extra_options=opts+['a'*64])
            try:
                first.client.call('save_checkpoint', name='start.pcec')
            finally:
                first.close()
            second = RunningSandbox(HEADLESS, root, extra_options=opts+['b'*64])
            try:
                before = second.client.call('status')
                with self.assertRaisesRegex(DevError, 'identity mismatch'):
                    second.client.call('load_checkpoint', name='start.pcec')
                self.assertEqual({k:v for k,v in before.items() if k!='id'},
                                 {k:v for k,v in second.client.call('status').items() if k!='id'})
            finally:
                second.close()

    def test_cd_timing_choice_binds_checkpoint_even_with_same_reviewed_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opts = ['--checkpoint-dir', str(root), '--checkpoint-context', 'c'*64]
            first = RunningSandbox(HEADLESS, root, bios=True,
                                   extra_options=opts+['--cd-timing', 'fixed'])
            try:
                state = first.client.call('status')
                self.assertEqual(state['host']['cd_timing'], {'profile': 'fixed'})
                first.client.call('save_checkpoint', name='fixed-drive.pcec')
                first.client.call('quit')
                first.process.communicate(timeout=5)
                self.assertEqual(first.process.returncode, 0)
            finally:
                first.close()
            second = RunningSandbox(HEADLESS, root, bios=True,
                                    extra_options=opts+['--cd-timing', 'gear-distance'])
            try:
                before = second.client.call('status')
                self.assertEqual(before['host']['cd_timing'], {'profile': 'gear-distance'})
                with self.assertRaisesRegex(DevError, 'identity mismatch'):
                    second.client.call('load_checkpoint', name='fixed-drive.pcec')
                self.assertEqual({k:v for k,v in before.items() if k!='id'},
                                 {k:v for k,v in second.client.call('status').items() if k!='id'})
                second.client.call('quit')
                second.process.communicate(timeout=5)
                self.assertEqual(second.process.returncode, 0)
            finally:
                second.close()


@unittest.skipUnless(DESKTOP.is_file(), 'Build the desktop runner')
class CheckpointDesktopCliTests(unittest.TestCase):
    def test_exact_fresh_process_desktop_continuation(self):
        exercise(self, DESKTOP, desktop=True)
