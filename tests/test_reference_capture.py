"""Authored strict reference capture metadata and raw-provenance preservation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.capture import validate_capture, validate_execution_policy
from pcerecomp.emitter import emit_capture, emit_observation_profile
from pcerecomp.observations import compose_observation_profile, observation_profile_provenance, plan_observation_profile
from pcerecomp.native_catalog import load_native_catalog
from test_capture import capture, observation


def policy(selected=True):
    return dict(schema=1, reference_enabled=True, selected=selected,
        configured_tier='native', effective_policy='interpreter' if selected else 'native',
        effective_native_span=0 if selected else 64)


class ReferenceCaptureTests(unittest.TestCase):
    def test_strict_policy_types_and_coherence(self):
        valid = policy()
        self.assertEqual(validate_execution_policy(valid), valid)
        for invalid in (None, {}, valid | {'extra': 1}, valid | {'schema': True},
                valid | {'reference_enabled': 1}, valid | {'selected': 1},
                valid | {'reference_enabled': False}, valid | {'configured_tier': 'interpreter'},
                valid | {'effective_policy': 'native'}, valid | {'effective_native_span': True},
                valid | {'effective_native_span': 1}, policy(False) | {'effective_native_span': 0},
                policy(False) | {'effective_native_span': 257}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_execution_policy(invalid)

    def test_imported_native_work_is_separate_from_reference_suffix(self):
        value = capture([observation(interpreted=7)]) | {'runtime_abi': ABI,
            'execution_policy': policy(), 'checkpoint_origin': dict(sha256='a'*64,
                ticks=20000, frame=4, native_steps=9000, interpreter_steps=200)}
        original = copy.deepcopy(value)
        self.assertEqual(validate_capture(value)[0]['interpreted_hits'], 7)
        with tempfile.TemporaryDirectory() as temp:
            manifest = emit_capture(value, Path(temp)/'module')
        self.assertEqual(value, original)
        self.assertEqual(manifest['capture_execution_policy'], policy())
        self.assertEqual(manifest['capture_checkpoint_origin']['native_steps'], 9000)
        self.assertEqual(manifest['captured_native_hits'], 0)
        self.assertEqual(manifest['capture_retired_instructions'], 7)
        for changed in (value | {'runtime_abi': 28},
                value | {'execution_policy': policy() | {'reference_enabled': False}},
                value | {'observations': [observation(native=1, interpreted=6)]}):
            with self.assertRaises(ValueError):
                validate_capture(changed)

    def test_native_counterpart_and_profiles_keep_exact_policy_provenance(self):
        native = capture([observation(native=3, interpreted=0)]) | {
            'runtime_abi': ABI, 'execution_policy': policy(False)}
        reference = capture([observation(interpreted=3)]) | {
            'runtime_abi': ABI, 'execution_policy': policy()}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cold = emit_capture(reference, root/'cold')
            self.assertNotIn('capture_execution_window', cold)
            self.assertNotIn('capture_checkpoint_origin', cold)
            paths = [root/'native.json', root/'reference.json']
            for path, value in zip(paths, (native, reference)):
                path.write_text(json.dumps(value), encoding='utf-8')
            profile = compose_observation_profile(paths)
            provenance = observation_profile_provenance(profile)
            self.assertEqual({json.dumps(row['execution_policy'], sort_keys=True) for row in provenance},
                {json.dumps(value, sort_keys=True) for value in (policy(), policy(False))})
            manifest = emit_observation_profile(profile, root/'module')
            self.assertEqual(manifest['observation_inputs'], provenance)
            planned = plan_observation_profile(paths)
            self.assertTrue(planned['fits'])
            self.assertTrue(all('execution_policy' in row for row in planned['new_inputs']))
            import hashlib
            digest = hashlib.sha256(paths[1].read_bytes()).hexdigest()
            single = root/'single'
            direct = emit_capture(reference, single, digest)
            admitted = load_native_catalog(single/'module.json', paths[1])
            self.assertEqual(admitted.emitted, frozenset({(0x4000, tuple(reference['observations'][0]['mpr']),
                tuple(reference['observations'][0]['physical']), (0xa9, 42))}))
            for invalid in (None, policy(False), policy() | {'selected': 1}):
                changed = copy.deepcopy(direct)
                if invalid is None:
                    changed.pop('capture_execution_policy')
                else:
                    changed['capture_execution_policy'] = invalid
                (single/'module.json').write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_native_catalog(single/'module.json', paths[1])
        self.assertFalse(profile['execution_evidence'])
        self.assertNotIn('execution_policy', profile)
