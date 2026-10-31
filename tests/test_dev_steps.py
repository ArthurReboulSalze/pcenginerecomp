"""Authored semantic frame-step envelopes; no game data or remote guest runs."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts import dev_steps as steps


U64 = (1 << 64) - 1
MAX_ID = (1 << 53) - 1


def status(identity, frame, ticks, paused, *, pc=0x4000):
    return dict(id=identity, ok=True, frame=frame, ticks=ticks, paused=paused,
                local_paused=False,
                host=dict(cpu=dict(pc=pc, mpr=[255, 248, 128, 129, 130, 131, 132, 0]),
                          native_steps=30, interpreter_steps=3),
                future=dict(values=[None, False, 'retained']))


def pair(identity, frame, ticks, paused, **changes):
    response = status(identity, frame, ticks, paused, **changes)
    return dict(request=dict(id=identity, cmd='status'), response=response)


def witness():
    return dict(
        before_status=status(10, 20, 1000, True),
        step_request=dict(id=11, cmd='step_frames', frames=3),
        step_ack=dict(id=11, ok=True, target_frame=23),
        polls=[pair(12, 20, 1000, False), pair(13, 22, 1200, False),
               pair(14, 23, 1400, True)],
        bounds=dict(max_polls=5, max_tick_delta=500, max_elapsed_ns=1000,
                    max_frame_overshoot=2),
    )


def candidate():
    return dict(
        before_status=status(40, 20, 1000, True, pc=0x4100),
        step_request=dict(id=41, cmd='step_frames', frames=3),
        step_ack=dict(id=41, ok=True, target_frame=23),
        polls=[pair(42, 21, 1100, False, pc=0x4567),
               pair(43, 23, 1400, True, pc=0x4999)],
    )


def seal(row=None, **extra):
    return steps.seal_step(**(witness() if row is None else row), **extra)


class SemanticStepTests(unittest.TestCase):
    def refuse(self, row):
        with self.assertRaises(steps.StepValidationError):
            seal(row)

    def test_literal_envelope_and_unobserved_deadline_are_explicit(self):
        row = witness()
        row['polls'][0]['response']['future']['finite_fraction'] = 1.25
        original = copy.deepcopy(row)
        result = seal(row)
        self.assertEqual(result['schema'], 1)
        self.assertEqual(result['kind'], 'pce-semantic-step-1')
        summary = result['summary']
        self.assertEqual((summary['start_frame'], summary['target_frame'],
                          summary['final_frame'], summary['final_ticks']),
                         (20, 23, 23, 1400))
        self.assertEqual(summary['poll_count'], 3)
        self.assertFalse(summary['deadline_observed'])
        self.assertIsNone(summary['elapsed_ns'])
        self.assertFalse(summary['endpoint_relation_checked'])
        self.assertEqual(result['evidence']['polls'], original['polls'])
        self.assertEqual(row, original)

    def test_different_progress_counts_and_cpu_values_are_not_fake_equality(self):
        reference = seal(elapsed_ns=800)
        row = candidate()
        original = copy.deepcopy(row)
        admitted = steps.admit_step(reference, **row, elapsed_ns=700)
        self.assertEqual(admitted['candidate']['summary']['poll_count'], 2)
        self.assertTrue(admitted['candidate']['summary']['deadline_observed'])
        self.assertFalse(admitted['endpoint_guest_state_compared'])
        self.assertFalse(admitted['progress_guest_state_compared'])
        self.assertEqual(admitted['candidate']['evidence']['polls'][-1]['response']['host']['cpu']['pc'], 0x4999)
        self.assertNotEqual(reference['evidence']['polls'][-1]['response']['host']['cpu']['pc'],
                            admitted['candidate']['evidence']['polls'][-1]['response']['host']['cpu']['pc'])
        self.assertEqual(row, original)

    def test_final_only_poll_is_valid_and_baseline_is_unchanged(self):
        reference = seal()
        original = copy.deepcopy(reference)
        row = candidate()
        row['polls'] = [pair(42, 23, 1400, True)]
        result = steps.admit_step(reference, **row, elapsed_ns=0)
        self.assertEqual(result['candidate']['summary']['poll_count'], 1)
        self.assertEqual(reference, original)

    def test_poll_container_is_finite_and_does_not_mutate_tuple_input(self):
        row = witness()
        row['polls'] = tuple(row['polls'])
        original = copy.deepcopy(row)
        self.assertEqual(seal(row)['summary']['poll_count'], 3)
        self.assertEqual(row, original)
        row['polls'] = iter(row['polls'])
        self.refuse(row)

    def test_whole_instruction_overshoot_is_bound_to_actual_completion(self):
        row = witness()
        row['bounds']['max_frame_overshoot'] = 1
        row['polls'][-1]['response']['frame'] = 24
        reference = seal(row)
        self.assertEqual(reference['summary']['target_frame'], 23)
        self.assertEqual(reference['summary']['final_frame'], 24)
        replay = candidate()
        replay['polls'][-1]['response']['frame'] = 24
        steps.admit_step(reference, **replay, elapsed_ns=5)
        replay['polls'][-1]['response']['frame'] = 23
        with self.assertRaises(steps.StepValidationError):
            steps.admit_step(reference, **replay, elapsed_ns=5)
        row['bounds']['max_frame_overshoot'] = 0
        self.refuse(row)

    def test_candidate_start_target_and_final_ticks_must_match(self):
        reference = seal()
        for option in ('start-frame', 'start-ticks', 'frames', 'final-frame', 'final-ticks'):
            row = candidate()
            if option == 'start-frame':
                row['before_status']['frame'] = 19
                row['step_ack']['target_frame'] = 22
            elif option == 'start-ticks':
                row['before_status']['ticks'] = 999
            elif option == 'frames':
                row['step_request']['frames'] = 2
                row['step_ack']['target_frame'] = 22
            elif option == 'final-frame':
                row['polls'][-1]['response']['frame'] = 24
            else:
                row['polls'][-1]['response']['ticks'] = 1399
            with self.subTest(option=option), self.assertRaises(steps.StepValidationError):
                steps.admit_step(reference, **row, elapsed_ns=20)

    def test_pending_mutations_and_even_other_reads_are_refused(self):
        for command in ('set_input', 'clear_input', 'write_memory', 'step_frames',
                        'pause', 'resume', 'quit', 'save_checkpoint', 'load_checkpoint',
                        'read_memory', 'capture_summary', 'screenshot', 'ping'):
            row = witness()
            row['polls'][1]['request']['cmd'] = command
            with self.subTest(command=command):
                self.refuse(row)

    def test_incomplete_or_post_completion_polls_are_refused(self):
        for option in ('empty', 'no-final', 'final-unpaused', 'trailing-status', 'two-final'):
            row = witness()
            if option == 'empty': row['polls'] = []
            elif option == 'no-final': row['polls'].pop()
            elif option == 'final-unpaused': row['polls'][-1]['response']['paused'] = False
            elif option == 'trailing-status': row['polls'].append(pair(15, 23, 1400, True))
            else: row['polls'][1]['response'].update(frame=23, ticks=1400, paused=True)
            with self.subTest(option=option):
                self.refuse(row)

    def test_local_pause_and_premature_or_running_at_target_are_refused(self):
        for index, field, value in ((0, 'local_paused', True), (2, 'local_paused', True),
                                    (0, 'paused', True), (1, 'frame', 23),
                                    (2, 'paused', 1), (2, 'local_paused', 0)):
            row = witness()
            row['polls'][index]['response'][field] = value
            with self.subTest(index=index, field=field, value=value):
                self.refuse(row)

    def test_frames_and_ticks_must_be_monotonic_and_within_limits(self):
        for index, field, value in ((0, 'frame', 19), (1, 'frame', 19),
                                    (0, 'ticks', 999), (2, 'ticks', 1199),
                                    (2, 'ticks', 1501), (2, 'frame', 26),
                                    (2, 'ticks', 1000)):
            row = witness()
            row['polls'][index]['response'][field] = value
            with self.subTest(index=index, field=field, value=value):
                self.refuse(row)

    def test_exact_request_ack_shapes_targets_and_ids(self):
        for option in ('wrong-command', 'request-extra', 'ack-extra', 'wrong-target',
                       'bad-ack-id', 'negative-ack', 'bool-ack', 'bool-frames',
                       'zero-frames', 'too-many-frames', 'step-before-anchor'):
            row = witness()
            if option == 'wrong-command': row['step_request']['cmd'] = 'resume'
            elif option == 'request-extra': row['step_request']['extra'] = 0
            elif option == 'ack-extra': row['step_ack']['extra'] = 0
            elif option == 'wrong-target': row['step_ack']['target_frame'] = 24
            elif option == 'bad-ack-id': row['step_ack']['id'] = 12
            elif option == 'negative-ack': row['step_ack']['ok'] = False
            elif option == 'bool-ack': row['step_ack']['ok'] = 1
            elif option == 'bool-frames': row['step_request']['frames'] = True
            elif option == 'zero-frames': row['step_request']['frames'] = 0
            elif option == 'too-many-frames': row['step_request']['frames'] = 601
            else: row['step_request']['id'] = row['step_ack']['id'] = 10
            with self.subTest(option=option):
                self.refuse(row)

    def test_pending_request_ids_are_consecutive_and_responses_paired(self):
        for option in ('gap', 'duplicate', 'response-mismatch', 'bool-id', 'request-extra', 'pair-extra'):
            row = witness()
            if option == 'gap': row['polls'][1]['request']['id'] = row['polls'][1]['response']['id'] = 15
            elif option == 'duplicate': row['polls'][1]['request']['id'] = row['polls'][1]['response']['id'] = 12
            elif option == 'response-mismatch': row['polls'][1]['response']['id'] = 12
            elif option == 'bool-id': row['polls'][1]['request']['id'] = True
            elif option == 'request-extra': row['polls'][1]['request']['frames'] = 1
            else: row['polls'][1]['unseen'] = 0
            with self.subTest(option=option):
                self.refuse(row)

    def test_status_types_and_unknown_nonfinite_or_cyclic_values(self):
        for field, value in (('frame', True), ('frame', -1), ('frame', U64 + 1),
                             ('ticks', False), ('ticks', U64 + 1), ('ok', 1),
                             ('paused', None), ('local_paused', True), ('host', [])):
            row = witness()
            row['before_status'][field] = value
            with self.subTest(field=field, value=value): self.refuse(row)
        for value in (float('nan'), float('inf'), float('-inf'), object(), (1, 2)):
            row = witness()
            row['polls'][0]['response']['unknown'] = value
            with self.subTest(value=repr(value)): self.refuse(row)
        row = witness()
        row['polls'][0]['response']['unknown'] = row['polls'][0]['response']
        self.refuse(row)
        row = witness()
        nested = []
        cursor = nested
        for _ in range(1100):
            child = []
            cursor.append(child)
            cursor = child
        row['polls'][0]['response']['unknown'] = nested
        self.refuse(row)
        row = witness(); row['polls'][0]['response']['future'][1] = 'nonstring key'
        self.refuse(row)

    def test_bounds_are_explicit_exact_positive_integers(self):
        for key in ('max_polls', 'max_tick_delta', 'max_elapsed_ns', 'max_frame_overshoot'):
            for value in (True, -1, U64 + 1, '100'):
                row = witness(); row['bounds'][key] = value
                with self.subTest(key=key, value=value): self.refuse(row)
        for key in ('max_polls', 'max_tick_delta', 'max_elapsed_ns'):
            row = witness(); row['bounds'][key] = 0
            with self.subTest(key=key): self.refuse(row)
        row = witness(); row['bounds']['extra'] = 1; self.refuse(row)
        row = witness(); del row['bounds']['max_polls']; self.refuse(row)
        row = witness(); row['bounds']['max_polls'] = 2; self.refuse(row)
        row = witness(); row['bounds']['max_polls'] = 1_000_001; self.refuse(row)

    def test_elapsed_deadline_is_measured_or_explicitly_unobserved(self):
        reference = seal(elapsed_ns=1000)
        self.assertTrue(reference['summary']['deadline_observed'])
        for value in (True, -1, 1001, U64 + 1, '1'):
            with self.subTest(value=value), self.assertRaises(steps.StepValidationError):
                seal(elapsed_ns=value)
        for value in (None, True, -1, 1001):
            with self.subTest(candidate_elapsed=value), self.assertRaises(steps.StepValidationError):
                steps.admit_step(reference, **candidate(), elapsed_ns=value)
        with self.assertRaises(TypeError):
            steps.admit_step(reference, **candidate())

    def test_frame_zero_bootstrap_is_explicit_and_bounded(self):
        row = witness()
        row['before_status'].update(frame=0, ticks=0)
        row['step_request']['frames'] = 1
        row['step_ack']['target_frame'] = 1
        row['polls'] = [pair(12, 1, 100, True)]
        result = seal(row, initial_observation='frame-zero-bootstrap')
        self.assertEqual(result['evidence']['initial_observation'], 'frame-zero-bootstrap')
        settled = seal(row)
        self.assertEqual(settled['evidence']['initial_observation'], 'settled')
        row['before_status']['ticks'] = 1
        with self.assertRaises(steps.StepValidationError):
            seal(row, initial_observation='frame-zero-bootstrap')
        for mode in (None, True, 'auto', 'bootstrap'):
            with self.subTest(mode=mode), self.assertRaises(steps.StepValidationError):
                seal(initial_observation=mode)

    def test_unsigned_frame_target_and_request_id_boundaries(self):
        row = witness()
        row['before_status'].update(frame=U64 - 3, ticks=U64 - 10)
        row['step_request']['frames'] = 1
        row['step_ack']['target_frame'] = U64 - 2
        row['bounds'].update(max_tick_delta=5, max_frame_overshoot=0)
        row['polls'] = [pair(12, U64 - 2, U64 - 5, True)]
        self.assertEqual(seal(row)['summary']['final_ticks'], U64 - 5)
        row['before_status']['frame'] = U64
        self.refuse(row)
        row = witness(); row['step_request']['id'] = row['step_ack']['id'] = MAX_ID
        self.refuse(row)
        row = witness(); row['polls'][0]['request']['id'] = MAX_ID + 1
        self.refuse(row)

    def test_reference_seal_tampering_or_extra_fields_are_refused(self):
        class NonPlainKey(str):
            pass
        for option in ('schema', 'kind', 'summary', 'summary-float', 'summary-custom-key',
                       'reference-cycle', 'evidence', 'hash', 'extra'):
            reference = seal()
            if option == 'schema': reference['schema'] = True
            elif option == 'kind': reference['kind'] = 'unknown'
            elif option == 'summary': reference['summary']['poll_count'] += 1
            elif option == 'summary-float': reference['summary']['poll_count'] = 3.0
            elif option == 'summary-custom-key':
                count = reference['summary'].pop('poll_count')
                reference['summary'][NonPlainKey('poll_count')] = count
            elif option == 'reference-cycle': reference['summary'] = reference
            elif option == 'evidence': reference['evidence']['polls'][0]['response']['host']['cpu']['pc'] += 1
            elif option == 'hash': reference['evidence_sha256'] = '0' * 64
            else: reference['extra'] = 'unverified'
            with self.subTest(option=option), self.assertRaises(steps.StepValidationError):
                steps.admit_step(reference, **candidate(), elapsed_ns=10)


class AuthoredTCPTests(unittest.TestCase):
    def observed_step(self, progress):
        from tests.test_dev_client import Server
        from scripts.dev_client import DevClient
        from scripts.dev_journal_audit import audit_wire_journal

        calls = []
        def handle(request):
            calls.append(request['cmd'])
            identity = request['id']
            if request['cmd'] == 'step_frames':
                return dict(id=identity, ok=True, target_frame=3)
            polls = calls.count('status')
            if polls == 1: return status(identity, 0, 0, True)
            if 2 <= polls < 2 + len(progress):
                frame, ticks = progress[polls - 2]
                return status(identity, frame, ticks, False, pc=0x4321)
            return status(identity, 3, 300, True)

        with tempfile.TemporaryDirectory() as temporary:
            journal = Path(temporary) / 'wire.jsonl'
            with Server(handle) as server:
                with DevClient(server.port, timeout=2, journal=journal) as client:
                    before = client.call('status')
                    started = time.monotonic_ns()
                    final = client.advance(3)
                    elapsed = time.monotonic_ns() - started
            pairs = []
            pending = None
            def visit(event):
                nonlocal pending
                if event.event == 'request': pending = json.loads(event.wire)
                elif event.event == 'response':
                    pairs.append(dict(request=pending, response=json.loads(event.wire)))
                    pending = None
            audit = audit_wire_journal(journal, visit=visit)
            self.assertEqual(audit['request_intents'], 3 + len(progress))
            self.assertEqual(audit['response_frames'], 3 + len(progress))
            self.assertEqual(calls, ['status', 'step_frames'] + ['status'] * (1 + len(progress)))
            return before, final, pairs, elapsed

    def test_actual_client_progress_journal_seals_without_losing_transient_replies(self):
        before, final, pairs, _ = self.observed_step([(1, 100)])
        result = steps.seal_step(before, pairs[1]['request'], pairs[1]['response'], pairs[2:],
            bounds=dict(max_polls=3, max_tick_delta=400, max_elapsed_ns=2_000_000_000,
                        max_frame_overshoot=0), initial_observation='frame-zero-bootstrap')
        self.assertEqual(result['summary']['poll_count'], 2)
        self.assertEqual(result['evidence']['polls'][-1]['response'], final)
        self.assertEqual(result['evidence']['polls'][0]['response']['host']['cpu']['pc'], 0x4321)
        self.assertFalse(result['summary']['endpoint_relation_checked'])

    def test_actual_different_poll_counts_admit_with_caller_measured_duration(self):
        before, _, pairs, _ = self.observed_step([(1, 100), (2, 200)])
        reference = steps.seal_step(before, pairs[1]['request'], pairs[1]['response'], pairs[2:],
            bounds=dict(max_polls=4, max_tick_delta=400, max_elapsed_ns=2_000_000_000,
                        max_frame_overshoot=0), initial_observation='frame-zero-bootstrap')
        native_before, final, native_pairs, measured = self.observed_step([])
        result = steps.admit_step(reference, native_before, native_pairs[1]['request'],
                                 native_pairs[1]['response'], native_pairs[2:], elapsed_ns=measured)
        self.assertEqual(reference['summary']['poll_count'], 3)
        self.assertEqual(result['candidate']['summary']['poll_count'], 1)
        self.assertEqual(result['candidate']['summary']['elapsed_ns'], measured)
        self.assertTrue(result['candidate']['summary']['deadline_observed'])
        self.assertEqual(result['candidate']['evidence']['polls'][-1]['response'], final)


if __name__ == '__main__':
    unittest.main()
