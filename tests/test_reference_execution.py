"""Independent authored policy/capture/profile provenance; no game or SDK assets."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.capture import validate_capture, validate_execution_policy
from pcerecomp.emitter import emit_capture, emit_observation_profile
from pcerecomp.observations import (
    compose_observation_profile, compose_additive_observation_profile,
    observation_profile_provenance, validate_observation_profile,
)


def policy(selected=True, tier="hybrid", span=64):
    return {"schema": 1, "reference_enabled": True, "selected": selected,
            "configured_tier": tier,
            "effective_policy": "interpreter" if selected else tier,
            "effective_native_span": 0 if selected else span}


def capture(native=0, interpreted=7, abi=29, origin=False, reference=True):
    # Literal independently mapped two-byte LDA #$2A at logical $4000.
    value = {"schema": 1, "runtime_abi": abi, "capacity": 8,
             "dropped_instructions": 0, "unreadable_instructions": 0,
             "retired_instructions": native + interpreted, "complete": True,
             "observations": [{"pc": 0x4000,
                 "mpr": [255, 248, 128, 129, 130, 131, 132, 0],
                 "physical": [0x100000, 0x100001], "data": [0xA9, 0x2A],
                 "native_hits": native, "interpreted_hits": interpreted}]}
    if origin:
        value["checkpoint_origin"] = {"sha256": "a" * 64, "ticks": 1000,
            "frame": 7, "native_steps": 800, "interpreter_steps": 200}
    if reference:
        value["execution_policy"] = policy()
    return value


class ReferenceExecutionProvenanceTests(unittest.TestCase):
    def test_six_field_policy_flags_schema_span_and_selection_are_strict(self):
        expected = policy()
        self.assertEqual(validate_execution_policy(expected), expected)
        for key, values in {
            "schema": [True, 1.0, 2], "reference_enabled": [1, 0, False],
            "selected": [1, 0, "true"], "configured_tier": ["interpreter", "unknown", 1],
            "effective_policy": ["hybrid", "native", "interpreter-only", None],
            "effective_native_span": [True, 0.0, 1, -1, 257],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_execution_policy(expected | {key: value})
        for malformed in [None, {}, expected | {"unexpected": 1}]:
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                validate_execution_policy(malformed)

    def test_enabled_unselected_policy_retains_actual_base_tier_and_span(self):
        for tier in ["native", "hybrid"]:
            for span in [1, 64, 256]:
                value = policy(False, tier, span)
                self.assertEqual(validate_execution_policy(value), value)
        for span in [0, True, 1.0, 257]:
            with self.subTest(span=span), self.assertRaises(ValueError):
                validate_execution_policy(policy(False) | {"effective_native_span": span})

    def test_selected_capture_refuses_native_and_mixed_retirements(self):
        for native, interpreted in [(1, 0), (1, 7), (2**32, 7)]:
            with self.subTest(native=native), self.assertRaises(ValueError):
                validate_capture(capture(native, interpreted))
        self.assertEqual(validate_capture(capture())[0]["interpreted_hits"], 7)

    def test_policy_metadata_requires_opted_in_ABI29_capture(self):
        for abi in [13, 18, 26, 27, 28]:
            with self.subTest(abi=abi), self.assertRaises(ValueError):
                validate_capture(capture(abi=abi))
        disabled = capture() | {"execution_policy": policy(False) | {"reference_enabled": False}}
        with self.assertRaises(ValueError):
            validate_capture(disabled)
        legacy = capture(3, 2, abi=28, origin=True, reference=False)
        self.assertEqual(len(validate_capture(legacy)), 1)

    def test_cold_reference_manifest_does_not_invent_a_checkpoint_suffix(self):
        original = capture()
        before = copy.deepcopy(original)
        with tempfile.TemporaryDirectory() as tmp:
            result = emit_capture(original, Path(tmp) / "cold")
        self.assertEqual(result["capture_execution_policy"], policy())
        self.assertNotIn("capture_checkpoint_origin", result)
        self.assertNotIn("capture_execution_window", result)
        self.assertEqual(result["captured_native_hits"], 0)
        self.assertEqual(result["captured_interpreted_hits"], 7)
        self.assertFalse(result["execution_evidence"])
        self.assertEqual(original, before)

    def test_legacy_resumed_manifest_keeps_origin_without_new_policy(self):
        original = capture(3, 2, abi=28, origin=True, reference=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = emit_capture(original, Path(tmp) / "legacy")
        self.assertEqual(result["capture_checkpoint_origin"], original["checkpoint_origin"])
        self.assertEqual(result["capture_execution_window"], "resumed-checkpoint-suffix")
        self.assertNotIn("capture_execution_policy", result)
        self.assertEqual(result["capture_runtime_abi"], 28)
        self.assertEqual(result["captured_native_hits"], 3)
        self.assertEqual(result["captured_interpreted_hits"], 2)

    def test_resumed_reference_manifest_keeps_origin_and_honest_suffix_tiers(self):
        original = capture(origin=True)
        with tempfile.TemporaryDirectory() as tmp:
            result = emit_capture(original, Path(tmp) / "reference")
        self.assertEqual(result["capture_execution_policy"], policy())
        self.assertEqual(result["capture_checkpoint_origin"], original["checkpoint_origin"])
        self.assertEqual(result["capture_execution_window"], "resumed-checkpoint-suffix")
        self.assertEqual(result["capture_retired_instructions"], 7)
        self.assertEqual(result["captured_native_hits"], 0)
        self.assertFalse(result["execution_evidence"])

    def exercise_profile(self, additive):
        legacy = capture(3, 2, abi=28, origin=True, reference=False)
        reference = capture(origin=True)
        originals = [legacy, reference]
        before = copy.deepcopy(originals)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [root / "legacy.json", root / "reference.json"]
            for path, value in zip(paths, originals):
                path.write_text(json.dumps(value), encoding="utf-8")
            raw_before = [path.read_bytes() for path in paths]
            if additive:
                profile = compose_additive_observation_profile([paths[1]], baseline_inputs=[paths[0]])
            else:
                profile = compose_observation_profile(paths)
            provenance = observation_profile_provenance(profile)
            digest = [hashlib.sha256(raw).hexdigest() for raw in raw_before]
            by_hash = {item["sha256"]: item for item in provenance}
            self.assertEqual(by_hash[digest[0]]["runtime_abi"], 28)
            self.assertNotIn("execution_policy", by_hash[digest[0]])
            self.assertEqual(by_hash[digest[0]]["native_hits"], 3)
            self.assertEqual(by_hash[digest[0]]["interpreted_hits"], 2)
            self.assertEqual(by_hash[digest[1]]["runtime_abi"], 29)
            self.assertEqual(by_hash[digest[1]]["execution_policy"], policy())
            self.assertEqual(by_hash[digest[1]]["native_hits"], 0)
            self.assertEqual(by_hash[digest[1]]["interpreted_hits"], 7)
            self.assertEqual(by_hash[digest[1]]["checkpoint_origin"], reference["checkpoint_origin"])
            result = emit_observation_profile(profile, root / "module")
            emitted = {item["sha256"]: item for item in result["observation_inputs"]}
            self.assertEqual(emitted, by_hash)
            self.assertFalse(result["execution_evidence"])
            self.assertNotIn("capture_execution_policy", result)
            self.assertEqual([path.read_bytes() for path in paths], raw_before)
            self.assertEqual(originals, before)
            self.assertEqual(len(validate_observation_profile(profile)), 1)

    def test_mixed_ABI_profile_preserves_each_original_policy_and_origin(self):
        self.exercise_profile(False)

    def test_additive_profile_preserves_unselected_reference_original_metadata(self):
        self.exercise_profile(True)


if __name__ == "__main__":
    unittest.main()
