"""Independently authored additive catalogue admission and provenance vectors.

These literals are neither retail source nor captures from a game. Expected
hit totals and boundary addresses are specified here independently of the
toolkit decoder, composer, emitter and validation helpers.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import observations as o
from pcerecomp import project
from pcerecomp.emitter import emit_observation_profile


MPR = [0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27]
ORIGIN = dict(sha256='a' * 64, ticks=3000, frame=12,
              native_steps=900, interpreter_steps=100)


def row(pc, data, native, interpreted, mapping=None):
    mapping = MPR.copy() if mapping is None else list(mapping)
    physical = [(mapping[((pc + i) & 65535) >> 13] << 13)
                | ((pc + i) & 8191) for i in range(len(data))]
    return dict(pc=pc, mpr=mapping, physical=physical, data=list(data),
                native_hits=native, interpreted_hits=interpreted)


def capture(rows, abi=27, origin=None):
    result = dict(schema=1, runtime_abi=abi, capacity=65536,
                  dropped_instructions=0, unreadable_instructions=0,
                  retired_instructions=sum(r['native_hits'] + r['interpreted_hits']
                                           for r in rows),
                  complete=True, observations=rows)
    if origin is not None:
        result['checkpoint_origin'] = copy.deepcopy(origin)
    return result


def identity(r):
    return r['pc'], tuple(r['mpr']), tuple(r['physical']), tuple(r['data'])


class AdditiveObservationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.first = self.write('first.json', capture([
            row(0x4000, [0xa9, 1], 2, 3), row(0x4002, [0xea], 0, 4)]))
        self.second = self.write('second.json', capture([
            row(0x4000, [0xa9, 1], 7, 0), row(0xffff, [0xa9, 3], 0, 2)],
            28, ORIGIN))
        changed_mpr = MPR.copy()
        changed_mpr[6] = 0x80
        self.added = self.write('added.json', capture([
            row(0x4000, [0xa9, 1], 11, 0),
            row(0x4000, [0xa9, 2], 0, 5),
            row(0x4002, [0xea], 3, 0, changed_mpr),
            row(0xffff, [0xa9, 3], 0, 13)], 28, ORIGIN))
        self.baseline = [self.first, self.second]
        self.originals = {p: p.read_bytes() for p in self.baseline + [self.added]}

    def write(self, name, value):
        path = self.root / name
        path.write_bytes(json.dumps(value, separators=(',', ':')).encode())
        return path

    def compose(self, additions=None, **options):
        return o.compose_additive_observation_profile(
            [self.added] if additions is None else additions,
            baseline_inputs=self.baseline, **options)

    def saved_profile(self, value, name='profile.json'):
        path = self.root / name
        path.write_bytes(o.serialize_observation_profile(value))
        return path

    def test_literal_selected_and_original_totals_are_distinct(self):
        profile = self.compose()
        self.assertEqual((profile['format'], profile['schema']),
                         ('pce-observation-profile-2', 2))
        self.assertIs(profile['execution_evidence'], False)
        self.assertNotIn('runtime_abi', profile)
        self.assertNotIn('checkpoint_origin', profile)
        self.assertEqual(profile['historical_totals'], dict(
            native_hits=23, interpreted_hits=27, retired_instructions=50))
        self.assertEqual(profile['selected_historical_totals'], dict(
            native_hits=12, interpreted_hits=14, retired_instructions=26))
        self.assertEqual(profile['selection_counts'], dict(
            original_contributions=8, selected_contributions=6,
            omitted_contributions=2))
        self.assertEqual(len(profile['observations']), 5)
        self.assertEqual(sum(len(r['contributions']) for r in profile['observations']), 6)
        self.assertEqual(len(o.validate_observation_profile(profile)), 5)
        known = next(r for r in profile['observations']
                     if r['pc'] == 0x4000 and r['data'] == [0xa9, 1])
        self.assertEqual((known['native_hits'], known['interpreted_hits']), (9, 3))
        self.assertEqual({r['input_sha256'] for r in known['contributions']},
                         {hashlib.sha256(p.read_bytes()).hexdigest() for p in self.baseline})

    def test_entire_raw_bytes_abis_origins_and_wrap_are_preserved(self):
        profile = self.compose()
        provenance = o.observation_profile_provenance(profile)
        self.assertEqual(sorted(r['runtime_abi'] for r in provenance), [27, 28, 28])
        self.assertEqual([r['checkpoint_origin'] for r in provenance
                          if 'checkpoint_origin' in r], [ORIGIN, ORIGIN])
        for source in profile['inputs']:
            raw = base64.b64decode(source['raw_base64'], validate=True)
            self.assertIn(raw, self.originals.values())
            self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)),
                             (source['sha256'], source['size_bytes']))
        wrapped = next(r for r in profile['observations'] if r['pc'] == 0xffff)
        self.assertEqual(wrapped['physical'], [0x4ffff, 0x40000])
        aliases = [r for r in profile['observations'] if r['pc'] == 0x4002]
        self.assertEqual(len(aliases), 2)
        self.assertEqual([r['physical'] for r in aliases], [[0x44002], [0x44002]])
        self.assertNotEqual(aliases[0]['mpr'], aliases[1]['mpr'])
        self.assertEqual({p: p.read_bytes() for p in self.originals}, self.originals)

    def test_same_stage_lowest_raw_sha_wins_regardless_argument_order(self):
        other = self.write('other.json', capture([
            row(0x4000, [0xa9, 2], 17, 0), row(0x4000, [0xa9, 1], 23, 0)], 26))
        profiles = [self.compose([self.added, other]), self.compose([other, self.added])]
        self.assertEqual(profiles[0], profiles[1])
        winner = min(hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (self.added, other))
        novel = next(r for r in profiles[0]['observations']
                     if r['pc'] == 0x4000 and r['data'] == [0xa9, 2])
        self.assertEqual(len(novel['contributions']), 1)
        self.assertEqual(novel['contributions'][0]['input_sha256'], winner)
        expected = (0, 5) if winner == hashlib.sha256(self.added.read_bytes()).hexdigest() else (17, 0)
        self.assertEqual((novel['native_hits'], novel['interpreted_hits']), expected)
        self.assertEqual(profiles[0]['selected_historical_totals'], dict(
            native_hits=12 + expected[0], interpreted_hits=9 + expected[1],
            retired_instructions=21 + sum(expected)))

    def test_extension_preserves_selected_prior_stages_and_hits(self):
        prior = self.compose()
        baseline_path = self.saved_profile(prior)
        later = self.write('later.json', capture([
            row(0x4000, [0xa9, 2], 999, 0),
            row(0x5fff, [0xad, 0, 2], 0, 19)], 28, ORIGIN))
        # A later source with a *lower* raw SHA cannot steal a prior owner.
        # Four leading LFs are an authored, valid alternative JSON encoding.
        later.write_bytes(b'\n\n\n\n' + later.read_bytes())
        self.assertLess(hashlib.sha256(later.read_bytes()).hexdigest(),
                        hashlib.sha256(self.added.read_bytes()).hexdigest())
        extended = o.compose_additive_observation_profile([later], baseline_profile=baseline_path)
        old_rows = {identity(r): r for r in prior['observations']}
        self.assertEqual({identity(r): r for r in extended['observations']
                          if identity(r) in old_rows}, old_rows)
        self.assertEqual(extended['selection_stages'][:-1], prior['selection_stages'])
        self.assertEqual(extended['selected_historical_totals'], dict(
            native_hits=12, interpreted_hits=33, retired_instructions=45))
        self.assertEqual(extended['historical_totals'], dict(
            native_hits=1022, interpreted_hits=46, retired_instructions=1068))
        self.assertEqual(extended['selection_counts'], dict(
            original_contributions=10, selected_contributions=7,
            omitted_contributions=3))
        boundary = next(r for r in extended['observations'] if r['pc'] == 0x5fff)
        self.assertEqual(boundary['physical'], [0x45fff, 0x46000, 0x46001])
        self.assertEqual(len(o.validate_observation_profile(extended)), 6)

    def test_duplicate_sha_is_idempotent_and_zero_novelty_raw_stays_provenance(self):
        prior = self.compose()
        alias = self.root / 'alias.json'
        alias.write_bytes(self.added.read_bytes())
        self.assertEqual(self.compose([alias, self.added]), prior)
        baseline_path = self.saved_profile(prior)
        self.assertEqual(o.compose_additive_observation_profile(
            [alias], baseline_profile=baseline_path), prior)
        differently_serialized = self.root / 'spaced.json'
        differently_serialized.write_text(json.dumps(json.loads(self.added.read_bytes()), indent=2),
                                           encoding='utf-8')
        extended = o.compose_additive_observation_profile(
            [differently_serialized], baseline_profile=baseline_path)
        self.assertEqual(extended['observations'], prior['observations'])
        self.assertEqual(extended['selected_historical_totals'], prior['selected_historical_totals'])
        self.assertEqual(len(extended['inputs']), 4)
        self.assertEqual(extended['selection_counts'], dict(
            original_contributions=12, selected_contributions=6,
            omitted_contributions=6))
        self.assertEqual(extended['historical_totals'], dict(
            native_hits=37, interpreted_hits=45, retired_instructions=82))

    def test_selected_contribution_cap_applies_without_relaxing_other_limits(self):
        with patch.object(o, 'MAX_CONTRIBUTIONS', 6):
            profile = self.compose()
            self.assertEqual(len(o.validate_observation_profile(profile)), 5)
            with self.assertRaises(ValueError):
                o.compose_observation_profile(self.baseline + [self.added])
        with patch.object(o, 'MAX_CONTRIBUTIONS', 5), self.assertRaises(ValueError):
            self.compose()
        total = sum(p.stat().st_size for p in self.originals)
        with patch.object(o, 'MAX_TOTAL_INPUT_BYTES', total - 1), self.assertRaises(ValueError):
            self.compose()
        with self.assertRaises(ValueError):
            self.compose(capacity=4)
        with patch.object(o, 'MAX_INPUTS', 2), self.assertRaises(ValueError):
            self.compose()

    def test_omitted_overlap_still_requires_full_raw_capture_admission(self):
        original = capture([row(0x4000, [0xa9, 1], 1, 0)], 28)
        malformed = []
        bad = copy.deepcopy(original); bad['observations'][0]['physical'][0] ^= 1; malformed.append(bad)
        bad = copy.deepcopy(original); bad['observations'][0]['native_hits'] = True; malformed.append(bad)
        bad = copy.deepcopy(original); bad.update(complete=False, dropped_instructions=1, retired_instructions=2); malformed.append(bad)
        bad = copy.deepcopy(original); bad['runtime_abi'] = 999; malformed.append(bad)
        bad = copy.deepcopy(original); bad['checkpoint_origin'] = ORIGIN | {'native_steps': False}; malformed.append(bad)
        for index, value in enumerate(malformed):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.compose([self.write(f'invalid-{index}.json', value)])

    def test_original_historical_overflow_cannot_hide_in_omitted_hits(self):
        one = self.write('huge.json', capture([row(0x4000, [0xa9, 1], 2**64 - 1, 0)]))
        two = self.write('overlap.json', capture([row(0x4000, [0xa9, 1], 1, 0)], 28))
        with self.assertRaises(ValueError):
            o.compose_additive_observation_profile([two], baseline_inputs=[one])

    def test_omitted_inputs_refuse_duplicate_json_and_noninteger_tokens(self):
        raw = json.dumps(capture([row(0x4000, [0xa9, 1], 1, 0)], 28)).encode()
        variants = [b'{"schema":1,' + raw[1:],
                    raw.replace(b'"native_hits": 1', b'"native_hits": 1e9999'),
                    raw.replace(b'"native_hits": 1', b'"native_hits": NaN'),
                    raw.replace(b'"native_hits": 1', b'"native_hits": 1.0')]
        for index, value in enumerate(variants):
            path = self.root / f'invalid-json-{index}.json'
            path.write_bytes(value)
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.compose([path])

    def test_profile_capacity_is_inherited_without_removing_retained_keys(self):
        prior = self.compose(capacity=5)
        path = self.saved_profile(prior)
        self.assertEqual(o.compose_additive_observation_profile(
            [], baseline_profile=path), prior)
        self.assertEqual(o.plan_additive_observation_profile(
            [], baseline_profile=path)['limits']['union_identities'], 5)
        with self.assertRaises(ValueError):
            o.compose_additive_observation_profile([], baseline_profile=path, capacity=4)

    def test_explicit_baseline_and_bounded_argument_iteration_are_required(self):
        with self.assertRaises(ValueError):
            o.compose_additive_observation_profile([self.added])
        path = self.saved_profile(self.compose())
        with self.assertRaises(ValueError):
            o.compose_additive_observation_profile(
                [self.added], baseline_inputs=self.baseline, baseline_profile=path)
        consumed = []
        def infinite():
            while True:
                consumed.append(1)
                yield self.added
        with self.assertRaises(ValueError):
            self.compose(infinite())
        self.assertLessEqual(len(consumed), o.MAX_INPUTS + 1)

    def test_recomputed_claims_and_policy_tampering_are_rejected(self):
        original = self.compose()
        variants = []
        for field in ('historical_totals', 'selected_historical_totals'):
            value = copy.deepcopy(original); value[field]['native_hits'] += 1; variants.append(value)
            value = copy.deepcopy(original); value[field]['native_hits'] = True; variants.append(value)
        value = copy.deepcopy(original); value['selection_counts']['omitted_contributions'] -= 1; variants.append(value)
        value = copy.deepcopy(original); value['selection_counts']['selected_contributions'] = True; variants.append(value)
        value = copy.deepcopy(original); value['observations'][0]['native_hits'] += 1; variants.append(value)
        value = copy.deepcopy(original); value['observations'].pop(); variants.append(value)
        value = copy.deepcopy(original); value['selection_stages'].append([]); variants.append(value)
        value = copy.deepcopy(original); value['selection_stages'][1] *= 2; variants.append(value)
        value = copy.deepcopy(original); value['selection_stages'][1] = ['0' * 64]; variants.append(value)
        value = copy.deepcopy(original); value['selection_stages'].reverse(); variants.append(value)
        value = copy.deepcopy(original); value['inputs'][0]['raw_base64'] = '!'; variants.append(value)
        value = copy.deepcopy(original); value['schema'] = True; variants.append(value)
        value = copy.deepcopy(original); value['format'] = 'pce-observation-profile-1'; value['schema'] = 1; variants.append(value)
        value = copy.deepcopy(original); value['execution_evidence'] = 0; variants.append(value)
        for index, value in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                o.validate_observation_profile(value)

    def test_v1_bytes_and_all_contributions_remain_unchanged(self):
        profile = o.compose_observation_profile(self.baseline + [self.added])
        self.assertEqual((profile['format'], profile['schema']), ('pce-observation-profile-1', 1))
        self.assertNotIn('selection_stages', profile)
        self.assertNotIn('selected_historical_totals', profile)
        self.assertNotIn('selection_counts', profile)
        self.assertEqual(profile['historical_totals'], dict(
            native_hits=23, interpreted_hits=27, retired_instructions=50))
        self.assertEqual(sum(len(r['contributions']) for r in profile['observations']), 8)
        expected = (json.dumps(profile, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        self.assertEqual(o.serialize_observation_profile(profile), expected)
        path = self.saved_profile(profile)
        loaded, digest = o.load_observation_profile(path)
        self.assertEqual(loaded, profile)
        self.assertEqual(digest, hashlib.sha256(expected).hexdigest())
        manifest = emit_observation_profile(profile, self.root / 'legacy')
        for field in ('selection_stages', 'selected_historical_totals', 'selection_counts', 'selection_policy'):
            self.assertNotIn(field, manifest)

    def test_v1_baseline_profile_is_admitted_without_relabeling_originals(self):
        baseline = o.compose_observation_profile(self.baseline)
        path = self.saved_profile(baseline, 'baseline-v1.json')
        expected = self.compose()
        extended = o.compose_additive_observation_profile([self.added], baseline_profile=path)
        self.assertEqual(extended, expected)
        self.assertEqual(path.read_bytes(), o.serialize_observation_profile(baseline))

    def test_roundtrip_and_independent_selected_exclusion_manifest(self):
        profile = self.compose()
        path = self.saved_profile(profile)
        loaded, digest, instructions, provenance = o.load_observation_profile_details(path)
        self.assertEqual(loaded, profile)
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(len(instructions), 5)
        manifest = emit_observation_profile(profile, self.root / 'selected', digest,
                                            exclude_ranges=[(0x44001, 1)])
        self.assertEqual(manifest['observation_inputs'], provenance)
        self.assertEqual(manifest['historical_totals'], profile['historical_totals'])
        self.assertEqual(manifest['selected_historical_totals'], profile['selected_historical_totals'])
        self.assertEqual(manifest['selection_stages'], profile['selection_stages'])
        self.assertEqual(manifest['selection_counts'], profile['selection_counts'])
        self.assertEqual(manifest['excluded_observations'], 2)
        self.assertEqual(manifest['excluded_retired_hits'], 17)
        self.assertEqual(manifest['native_instructions_emitted'], 3)
        self.assertEqual(manifest['unsupported_observations'], 0)
        self.assertIs(manifest['execution_evidence'], False)
        self.assertNotIn('capture_runtime_abi', manifest)

    def test_consumer_binding_reconstructs_selection_and_refuses_manifest_downgrade(self):
        profile = self.compose()
        path = self.saved_profile(profile)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = emit_observation_profile(profile, self.root / 'bound', digest)
        entry = dict(path=path.name, sha256=digest)
        files = {}
        project._module_observation_profile(self.root, entry, files, manifest)
        self.assertEqual(files['module_observation_profile'], path)
        changes = [('selection_stages', []), ('selected_historical_totals', profile['historical_totals']),
                   ('selection_counts', dict(original_contributions=8, selected_contributions=8,
                                              omitted_contributions=0)),
                   ('selection_policy', 'all rows'), ('observation_profile_schema', 1)]
        for field, value in changes:
            changed = copy.deepcopy(manifest); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                project._module_observation_profile(self.root, entry, {}, changed)
        for field in ('selection_stages', 'selected_historical_totals', 'selection_counts', 'selection_policy'):
            changed = copy.deepcopy(manifest); changed.pop(field)
            with self.subTest(missing=field), self.assertRaises(ValueError):
                project._module_observation_profile(self.root, entry, {}, changed)

    def test_plan_hash_matches_real_serialization_and_never_creates_artifacts(self):
        before = set(self.root.iterdir())
        plan = o.plan_additive_observation_profile([self.added], baseline_inputs=self.baseline)
        self.assertTrue(plan['fits'])
        raw = o.serialize_observation_profile(self.compose())
        self.assertEqual(plan['combined']['serialized_bytes'], len(raw))
        self.assertEqual(plan['combined']['serialized_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(plan['combined']['contributions'], 6)
        self.assertFalse(plan['execution_evidence'])
        self.assertFalse(plan['equivalence_evidence'])
        self.assertEqual(set(self.root.iterdir()), before)
        path = self.saved_profile(self.compose())
        plan = o.plan_additive_observation_profile([], baseline_profile=path)
        self.assertTrue(plan['fits'])
        self.assertEqual(plan['baseline_artifact'], dict(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size_bytes=path.stat().st_size))


if __name__ == '__main__':
    unittest.main()
