"""Authored mixed-ABI catalogues; no retail source, firmware or captured data."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.isa import decode
from pcerecomp.abi import ABI
from pcerecomp.observations import (
    compose_observation_profile, load_observation_profile,
    observation_profile_provenance, validate_observation_profile,
)

MPR = [255, 248, 128, 129, 130, 131, 132, 0]
U64 = 2**64 - 1


def observation(pc=0x4000, data=(0xa9, 42), mpr=None, native=0, interpreted=1):
    mpr = MPR.copy() if mpr is None else list(mpr)
    ins = decode(lambda address: data[(address-pc) & 65535], pc, tuple(mpr))
    return {'pc': pc, 'mpr': mpr, 'physical': list(ins.physical), 'data': list(data),
            'native_hits': native, 'interpreted_hits': interpreted}


def capture(items=None, abi=18, origin=None):
    items = [observation()] if items is None else items
    result = {'schema': 1, 'runtime_abi': abi, 'capacity': 65536,
              'dropped_instructions': 0, 'unreadable_instructions': 0,
              'retired_instructions': sum(i['native_hits']+i['interpreted_hits'] for i in items),
              'complete': True, 'observations': items}
    if origin is not None:
        result['checkpoint_origin'] = origin
    return result


class ObservationProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = 0

    def write(self, value=None, raw=None):
        self.index += 1
        path = self.root / f'input-{self.index}.json'
        path.write_bytes(json.dumps(value).encode() if raw is None else raw)
        return path

    def profile(self):
        return compose_observation_profile([self.write(capture())])

    def test_mixed_abi_exact_raw_provenance_and_origin(self):
        origin = {'sha256': 'a'*64, 'ticks': 1000, 'frame': 12,
                  'native_steps': 800, 'interpreter_steps': 200}
        first = self.write(capture([observation(native=3, interpreted=2)]))
        second = self.write(capture([observation(native=1, interpreted=4)], 26, origin))
        originals = [p.read_bytes() for p in (first, second)]
        profile = compose_observation_profile([first, second])
        self.assertNotIn('runtime_abi', profile)
        self.assertNotIn('checkpoint_origin', profile)
        self.assertIs(profile['execution_evidence'], False)
        self.assertEqual(profile['historical_totals'],
                         {'native_hits': 4, 'interpreted_hits': 6, 'retired_instructions': 10})
        self.assertEqual(len(profile['observations']), 1)
        self.assertEqual(len(profile['observations'][0]['contributions']), 2)
        metadata = observation_profile_provenance(profile)
        self.assertEqual(sorted(item['runtime_abi'] for item in metadata), [18, 26])
        self.assertEqual(next(item for item in metadata if item['runtime_abi'] == 26)['checkpoint_origin'], origin)
        self.assertNotIn('checkpoint_origin', next(item for item in metadata if item['runtime_abi'] == 18))
        self.assertEqual([p.read_bytes() for p in (first, second)], originals)
        for item in profile['inputs']:
            raw = base64.b64decode(item['raw_base64'])
            self.assertIn(raw, originals)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
            self.assertEqual(len(raw), item['size_bytes'])
        decoded = validate_observation_profile(profile)
        self.assertEqual((decoded[0]['native_hits'], decoded[0]['interpreted_hits']), (4, 6))

    def test_order_and_duplicate_raw_are_idempotent(self):
        one = self.write(capture())
        two = self.write(capture([observation(data=(0xa9, 43))], 26))
        alias = self.write(raw=one.read_bytes())
        expected = compose_observation_profile([one, two])
        self.assertEqual(compose_observation_profile([two, alias, one, two]), expected)
        self.assertEqual(len(expected['inputs']), 2)
        self.assertEqual(expected['historical_totals']['retired_instructions'], 2)

    def test_different_serializations_are_separate_inputs(self):
        value = capture()
        one = self.write(value)
        two = self.write(raw=(json.dumps(value, indent=2)+'\n').encode())
        profile = compose_observation_profile([one, two])
        self.assertEqual(len(profile['inputs']), 2)
        self.assertEqual(profile['historical_totals']['retired_instructions'], 2)
        self.assertEqual(len(profile['observations']), 1)

    def test_all_mprs_variants_overlap_crosspage_and_wrap_preserved(self):
        items = [observation(), observation(data=(0xa9, 43)),
                 observation(0x4001, (0xea,)), observation(0x5fff, (0xad, 1, 2)),
                 observation(0xffff, (0xa9, 3))]
        for index in range(8):
            mpr = MPR.copy(); mpr[index] ^= 1
            items.append(observation(mpr=mpr))
        profile = compose_observation_profile([self.write(capture(items))])
        decoded = validate_observation_profile(profile)
        self.assertEqual(len(decoded), 13)
        self.assertIn((8191, 0x1fe000), [tuple(item['physical']) for item in decoded])
        self.assertIn((0x101fff, 0x102000, 0x102001), [tuple(item['physical']) for item in decoded])

    def test_physical_mapping_disagreement_refuses(self):
        value = capture(); value['observations'][0]['physical'][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'physical mapping'):
            compose_observation_profile([self.write(value)])

    def test_capacity_boundary_and_no_truncation(self):
        path = self.write(capture([observation(), observation(data=(0xa9, 43))]))
        self.assertEqual(len(compose_observation_profile([path], capacity=2)['observations']), 2)
        with self.assertRaisesRegex(ValueError, 'no identities dropped'):
            compose_observation_profile([path], capacity=1)
        for capacity in (0, 65537, True, 1.0):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                compose_observation_profile([path], capacity=capacity)

    def test_global_u64_boundary_and_overflow(self):
        one = self.write(capture([observation(native=U64-1, interpreted=0)]))
        two = self.write(capture([observation(0x4002, (0xea,))], 26))
        profile = compose_observation_profile([one, two])
        self.assertEqual(profile['historical_totals']['retired_instructions'], U64)
        validate_observation_profile(profile)
        three = self.write(capture([observation(0x4003, (0xea,))], 26))
        with self.assertRaisesRegex(ValueError, 'historical'):
            compose_observation_profile([one, two, three])

    def test_individual_u64_and_bad_counter_types_refused(self):
        for native, interpreted in ((U64, 1), (True, 0), (0, -1), (0, 1.0), (0, 0)):
            with self.subTest(native=native, interpreted=interpreted), self.assertRaises(ValueError):
                compose_observation_profile([self.write(capture([observation(native=native, interpreted=interpreted)]))])

    def test_empty_input_list_refused_but_empty_capture_allowed(self):
        with self.assertRaises(ValueError):
            compose_observation_profile([])
        profile = compose_observation_profile([self.write(capture([]))])
        self.assertEqual(validate_observation_profile(profile), [])
        self.assertEqual(profile['historical_totals']['retired_instructions'], 0)

    def test_incomplete_input_refused(self):
        value = capture(); value.update(complete=False, dropped_instructions=1, retired_instructions=2)
        with self.assertRaisesRegex(ValueError, 'complete lossless'):
            compose_observation_profile([self.write(value)])

    def test_invalid_original_schema_abi_unknown_fields_and_origin(self):
        variants = [capture() | {'schema': 2}, capture() | {'runtime_abi': ABI + 1},
                    capture() | {'runtime_abi': True}, capture() | {'unknown': 1},
                    capture() | {'checkpoint_origin': {'sha256': 'a'*64}}]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compose_observation_profile([self.write(value)])

    def test_duplicate_json_keys_and_noninteger_tokens_refused(self):
        raw = json.dumps(capture()).encode()
        variants = [b'{"schema":1,' + raw[1:],
                    raw.replace(b'"native_hits": 0', b'"native_hits": 0, "native_hits": 0'),
                    raw.replace(b'"runtime_abi": 18', b'"runtime_abi": 1e999'),
                    raw.replace(b'"runtime_abi": 18', b'"runtime_abi": NaN'),
                    raw.replace(b'"runtime_abi": 18', b'"runtime_abi": Infinity'),
                    raw.replace(b'"runtime_abi": 18', b'"runtime_abi": 18.0'),
                    raw.replace(b'"runtime_abi": 18', b'"runtime_abi": '+b'1'*5000)]
        for value in variants:
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                compose_observation_profile([self.write(raw=value)])

    def test_raw_unicode_encodings_preserved(self):
        for encoding in ('utf-8-sig', 'utf-16', 'utf-32'):
            raw = json.dumps(capture()).encode(encoding)
            profile = compose_observation_profile([self.write(raw=raw)])
            self.assertEqual(base64.b64decode(profile['inputs'][0]['raw_base64']), raw)
            validate_observation_profile(profile)

    def test_roundtrip_rehashes_profile_and_originals(self):
        profile = self.profile()
        raw = (json.dumps(profile, indent=2, sort_keys=True)+'\n').encode()
        path = self.write(raw=raw)
        loaded, digest = load_observation_profile(path)
        self.assertEqual(loaded, profile)
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())

    def test_original_provenance_tampering_refused(self):
        for key, value in [('sha256', 'A'*64), ('sha256', '0'*64), ('sha256', True),
                           ('size_bytes', True), ('size_bytes', 0), ('size_bytes', 1),
                           ('raw_base64', '!'), ('raw_base64', 12)]:
            profile = self.profile(); profile['inputs'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_observation_profile(profile)

    def test_raw_bytes_replaced_cannot_hide_under_original_hash(self):
        profile = self.profile()
        raw = base64.b64decode(profile['inputs'][0]['raw_base64']).replace(b'18', b'26', 1)
        profile['inputs'][0]['raw_base64'] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            validate_observation_profile(profile)

    def test_canonical_base64_pad_bits_refused(self):
        raw = json.dumps(capture()).encode()
        while len(raw) % 3 != 1:
            raw += b' '
        profile = compose_observation_profile([self.write(raw=raw)])
        encoded = profile['inputs'][0]['raw_base64']
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        variant = encoded[:-3] + alphabet[alphabet.index(encoded[-3])+1] + '=='
        self.assertEqual(base64.b64decode(variant), raw)
        profile['inputs'][0]['raw_base64'] = variant
        with self.assertRaisesRegex(ValueError, 'canonical base64'):
            validate_observation_profile(profile)

    def test_observation_contribution_and_total_tampering_refused(self):
        variants = []
        profile = self.profile(); profile['observations'][0]['data'][1] = 43; variants.append(profile)
        profile = self.profile(); profile['observations'][0]['interpreted_hits'] = True; variants.append(profile)
        profile = self.profile(); profile['observations'][0]['contributions'][0]['interpreted_hits'] = 2; variants.append(profile)
        profile = self.profile(); profile['observations'][0]['contributions'] = []; variants.append(profile)
        profile = self.profile(); profile['historical_totals']['retired_instructions'] = True; variants.append(profile)
        profile = self.profile(); profile['observations'][0]['extra'] = 0; variants.append(profile)
        for value in variants:
            with self.subTest(value=value['observations']), self.assertRaises(ValueError):
                validate_observation_profile(value)

    def test_profile_schema_and_no_capture_relabeling(self):
        original = self.profile()
        variants = [original | {'schema': True}, original | {'schema': 2},
                    original | {'format': 'capture'}, original | {'runtime_abi': 26},
                    original | {'checkpoint_origin': None}, original | {'execution_evidence': 0},
                    original | {'execution_evidence': True}]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_observation_profile(value)

    def test_duplicate_and_reordered_provenance_refused(self):
        profile = self.profile(); profile['inputs'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_observation_profile(profile)
        paths = [self.write(capture()), self.write(capture(abi=26))]
        profile = compose_observation_profile(paths); profile['inputs'].reverse()
        with self.assertRaisesRegex(ValueError, 'canonical'):
            validate_observation_profile(profile)

    def test_explicit_input_contribution_and_byte_bounds(self):
        path = self.write(capture())
        with patch('pcerecomp.observations.MAX_INPUTS', 1):
            with self.assertRaisesRegex(ValueError, 'input paths'):
                compose_observation_profile([path, path])
        with patch('pcerecomp.observations.MAX_CONTRIBUTIONS', 0):
            with self.assertRaisesRegex(ValueError, 'contribution'):
                compose_observation_profile([path])
        with patch('pcerecomp.observations.MAX_TOTAL_INPUT_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'Total original'):
                compose_observation_profile([path])
        with patch('pcerecomp.observations.MAX_CAPTURE_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'Code capture exceeds'):
                compose_observation_profile([path])
        with patch('pcerecomp.observations.MAX_PROFILE_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'profile exceeds'):
                compose_observation_profile([path])

    def test_profile_load_bounds_duplicates_and_overflow_tokens(self):
        raw = json.dumps(self.profile()).encode()
        for value in (b'{"schema":1,'+raw[1:], raw.replace(b'"schema": 1', b'"schema": 1e999', 1)):
            with self.assertRaises(ValueError):
                load_observation_profile(self.write(raw=value))
        path = self.write(raw=raw)
        with patch('pcerecomp.observations.MAX_PROFILE_BYTES', len(raw)-1):
            with self.assertRaisesRegex(ValueError, 'profile exceeds'):
                load_observation_profile(path)


if __name__ == '__main__':
    unittest.main()
