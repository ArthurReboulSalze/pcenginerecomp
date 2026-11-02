"""Independent authored role, imported-window and encoded-identity contracts."""
import copy
import unittest

from scripts import dev_audit_relation as relation


def origin(*, native=False):
    return dict(sha256=("b" if native else "a") * 64, frame=1000, ticks=100000,
                native_steps=8000 if native else 7997, interpreter_steps=0 if native else 3)


def lifetime(*, native=False):
    return dict(frame=1002, ticks=100720, native_steps=8008 if native else 8002,
                interpreter_steps=0 if native else 6)


def authored_capture(*, native=False):
    # Literal expectations cross both an MPR segment and the logical-PC wrap.
    mpr = [0, 248, 2, 3, 4, 5, 6, 7]
    rows = [
        dict(pc=0x4000, mpr=list(mpr), physical=[0x4000], data=[0xEA]),
        dict(pc=0x5FFE, mpr=list(mpr), physical=[0x5FFE, 0x5FFF, 0x6000, 0x6001, 0x6002, 0x6003, 0x6004],
             data=[0x73, 0, 0x20, 0, 0x21, 1, 0]),
        dict(pc=0xFFFF, mpr=list(mpr), physical=[0xFFFF, 0], data=[0xA9, 5])]
    counts = [(5, 0), (1, 0), (2, 0)] if native else [(3, 2), (0, 1), (2, 0)]
    return dict(schema=1, runtime_abi=28, capacity=16, complete=True,
        dropped_instructions=0, unreadable_instructions=0, retired_instructions=8,
        observations=[row | dict(native_hits=n, interpreted_hits=i) for row, (n, i) in zip(rows, counts)],
        checkpoint_origin=origin(native=native))


def mapped(*, native=False):
    return relation.encoded_map(authored_capture(native=native), origin(native=native))


def own_status():
    return dict(id=9, ok=True, paused=True, local_paused=False, ticks=100720, frame=1002,
        host=dict(native_steps=8008, interpreter_steps=0, checkpoint=dict(resumed=True,
            origin=origin(native=True), audio_origin=dict(pending_pcm_frames=2, source_wav_frames=0),
            window=dict(ticks=720, native_steps=8, interpreter_steps=0))))


class DevAuditRelationTests(unittest.TestCase):
    def test_strict_json_accepts_finite_values_and_exact_types(self):
        self.assertEqual(relation.strict_loads('{"count":2,"optional":0.125,"nested":[true,null]}'),
                         dict(count=2, optional=.125, nested=[True, None]))
        self.assertFalse(relation.exact({"counter": True}, {"counter": 1}))
        self.assertFalse(relation.exact([1], [1.0]))
        self.assertTrue(relation.exact({"values": [0, 1]}, {"values": [0, 1]}))
        self.assertEqual(relation.strict_loads(b'{"label":"\xe2\x98\x83","time":0.5}'),
                         dict(label="\u2603", time=.5))

    def test_duplicate_and_nonfinite_json_are_never_evidence(self):
        cases = ['{"id":9,"id":1}', '{"nested":{"sha256":"a","sha256":"b"}}',
                 '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}',
                 '{"value":1e9999}', '{"value":-1e9999}']
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                relation.strict_loads(text)

    def test_unsigned_counters_have_no_boolean_or_float_aliases(self):
        self.assertEqual(relation.uint(0), 0)
        self.assertEqual(relation.uint((1 << 64)-1), (1 << 64)-1)
        for value in [True, False, 1.0, "1", None, -1, 1 << 64]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                relation.uint(value)

    def test_saved_ack_origin_preserves_identity_and_audio_prefix(self):
        meta = origin(native=True) | dict(payload_sha256="c" * 64,
            pending_pcm_frames=2, source_wav_frames=0)
        self.assertEqual(relation.checkpoint_origin(meta), origin(native=True))
        self.assertEqual(relation.audio_origin(meta), dict(pending_pcm_frames=2, source_wav_frames=0))
        for field in ["frame", "ticks", "native_steps", "interpreter_steps"]:
            broken = meta | {field: True}
            with self.subTest(field=field), self.assertRaises(ValueError):
                relation.checkpoint_origin(broken)
        with self.assertRaises(ValueError):
            relation.checkpoint_origin(meta | {"sha256": "A" * 64})
        with self.assertRaises(ValueError):
            relation.audio_origin(meta | {"pending_pcm_frames": False})

    def test_imported_work_is_subtracted_independently(self):
        self.assertEqual(relation.derive_window(lifetime(), origin()),
            dict(frame=2, ticks=720, native_steps=5, interpreter_steps=3))
        self.assertEqual(relation.derive_window(lifetime(native=True), origin(native=True)),
            dict(frame=2, ticks=720, native_steps=8, interpreter_steps=0))
        for field in ["frame", "ticks", "native_steps", "interpreter_steps"]:
            broken = lifetime() | {field: origin()[field]-1}
            with self.subTest(field=field), self.assertRaises(ValueError):
                relation.derive_window(broken, origin())

    def test_role_promotion_conserves_lifetimes_and_new_work(self):
        old, new = lifetime(), lifetime(native=True)
        saved_old, saved_new = copy.deepcopy(old), copy.deepcopy(new)
        result = relation.compare_counter_roles(old, new, source_origin=origin(),
            actual_origin=origin(native=True), promote=True)
        self.assertEqual(result["source_window"], dict(frame=2, ticks=720, native_steps=5, interpreter_steps=3))
        self.assertEqual(result["actual_window"], dict(frame=2, ticks=720, native_steps=8, interpreter_steps=0))
        self.assertEqual((old, new), (saved_old, saved_new))
        # Same-tier mode does not silently promote mixed historical work.
        relation.compare_counter_roles(old, copy.deepcopy(old), source_origin=origin(),
            actual_origin=origin() | {"sha256": "d" * 64}, promote=False)
        with self.assertRaises(ValueError):
            relation.compare_counter_roles(old, new, source_origin=origin(),
                actual_origin=origin(native=True), promote=False)

    def test_role_tampering_cannot_hide_behind_equal_total_work(self):
        failures = [
            (lifetime(native=True) | {"native_steps": 8007}, origin(native=True)),
            (lifetime(native=True), origin(native=True) | {"native_steps": 7999}),
            (lifetime(native=True) | {"native_steps": 8007, "interpreter_steps": 1}, origin(native=True)),
            (lifetime(native=True) | {"frame": 1003}, origin(native=True)),
            (lifetime(native=True) | {"ticks": 100721}, origin(native=True))]
        for final, parent in failures:
            with self.subTest(final=final, parent=parent), self.assertRaises(ValueError):
                relation.compare_counter_roles(lifetime(), final, source_origin=origin(),
                    actual_origin=parent, promote=True)

    def test_tier_counters_are_typed_before_arithmetic_normalization(self):
        for field in ["frame", "ticks", "native_steps", "interpreter_steps"]:
            for value in [True, False, 1.0]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    relation.compare_counter_roles(lifetime() | {field: value}, lifetime(native=True),
                        source_origin=origin(), actual_origin=origin(native=True), promote=True)
                with self.subTest(parent=field, value=value), self.assertRaises(ValueError):
                    relation.derive_window(lifetime(), origin() | {field: value})

    def test_every_status_has_its_own_origin_audio_and_new_work(self):
        status = own_status()
        before = copy.deepcopy(status)
        self.assertEqual(relation.validate_origin_status(status, origin(native=True),
            dict(pending_pcm_frames=2, source_wav_frames=0)),
            dict(ticks=720, native_steps=8, interpreter_steps=0))
        self.assertEqual(status, before)
        # Active progress polling is legitimate and still carries the same own origin.
        status["paused"] = False
        relation.validate_origin_status(status, origin(native=True),
            dict(pending_pcm_frames=2, source_wav_frames=0))

    def test_status_parent_audio_and_window_tampering(self):
        def change(path, value):
            result = own_status()
            at = result
            for key in path[:-1]:
                at = at[key]
            at[path[-1]] = value
            return result
        cases = [change(["id"], value) for value in [True, 1.0, 0, -1, 1 << 53]]
        cases += [change(["host", "checkpoint", "origin", "sha256"], "c" * 64),
            change(["host", "checkpoint", "resumed"], False),
            change(["host", "checkpoint", "audio_origin", "pending_pcm_frames"], 3),
            change(["host", "checkpoint", "window", "native_steps"], 8008),
            change(["host", "checkpoint", "window", "interpreter_steps"], False),
            change(["host", "native_steps"], 8007), change(["frame"], True),
            change(["local_paused"], True), change(["paused"], 1)]
        for index, status in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                relation.validate_origin_status(status, origin(native=True),
                    dict(pending_pcm_frames=2, source_wav_frames=0))

    def test_full_encoded_oracle_and_per_key_promotion(self):
        old, new = mapped(), mapped(native=True)
        self.assertEqual(len(old), 3)
        self.assertEqual(sorted(old.values()), [(0, 1), (2, 0), (3, 2)])
        self.assertEqual(sorted(new.values()), [(1, 0), (2, 0), (5, 0)])
        self.assertEqual(sum(n+i for n, i in old.values()), 8)
        self.assertEqual(sum(n for key, (n, i) in new.items() if key[3][0] == 0x73), 1)
        relation.compare_encoded_maps(old, new, promote=True)
        relation.compare_encoded_maps(old, copy.deepcopy(old), promote=False)

    def test_equal_aggregate_does_not_replace_per_key_counts(self):
        old, new = mapped(), mapped(native=True)
        keys = list(new)
        new[keys[0]] = (4, 0)
        new[keys[1]] = (2, 0)
        self.assertEqual(sum(n+i for n, i in new.values()), 8)
        with self.assertRaises(ValueError):
            relation.compare_encoded_maps(old, new, promote=True)
        new = mapped(native=True)
        new[keys[0]] = (4, 1)
        with self.assertRaises(ValueError):
            relation.compare_encoded_maps(old, new, promote=True)

    def test_direct_maps_reject_zero_and_overflow_pairs(self):
        key = next(iter(mapped()))
        for pair in [(0, 0), ((1 << 64)-1, 1), (True, 0), (1.0, 0)]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                relation.compare_encoded_maps({key: pair}, {key: pair}, promote=False)
        # Equality of empty maps is a valid relation, never a claim of execution.
        self.assertEqual(relation.compare_encoded_maps({}, {}, promote=False)["keys"], 0)

    def test_unused_mpr_and_source_bytes_are_identity(self):
        for field in ["unused_mpr", "bytes"]:
            cap = authored_capture(native=True)
            if field == "unused_mpr":
                cap["observations"][0]["mpr"][4] ^= 1
            else:
                cap["observations"][0]["data"][0] = 0x18
            changed = relation.encoded_map(cap, origin(native=True))
            with self.subTest(field=field), self.assertRaises(ValueError):
                relation.compare_encoded_maps(mapped(), changed, promote=True)

    def test_logical_wrap_requires_physical_remapping(self):
        cap = authored_capture(native=True)
        relation.encoded_map(cap, origin(native=True))
        cap["observations"][2]["physical"][1] = 0x10000
        with self.assertRaises(ValueError):
            relation.encoded_map(cap, origin(native=True))

    def test_capture_tamper_matrix(self):
        mutations = [
            lambda c: c.update(schema=2),
            lambda c: c.update(schema=True),
            lambda c: c.update(runtime_abi=27),
            lambda c: c.update(runtime_abi=True),
            lambda c: c.update(complete=1),
            lambda c: c.update(dropped_instructions=1),
            lambda c: c.update(unreadable_instructions=1),
            lambda c: c.update(retired_instructions=8008),
            lambda c: c.update(capacity=2),
            lambda c: c["checkpoint_origin"].update(sha256="c" * 64),
            lambda c: c["checkpoint_origin"].update(native_steps=True),
            lambda c: c["observations"][0].update(native_hits=True),
            lambda c: c["observations"][0].update(native_hits=1 << 64),
            lambda c: c["observations"].append(copy.deepcopy(c["observations"][0])),
            lambda c: c["observations"][0]["mpr"].pop(),
            lambda c: c["observations"][0]["data"].__setitem__(0, 256)]
        for index, mutate in enumerate(mutations):
            cap = authored_capture(native=True)
            mutate(cap)
            with self.subTest(index=index), self.assertRaises(ValueError):
                relation.encoded_map(cap, origin(native=True))


if __name__ == "__main__":
    unittest.main()
