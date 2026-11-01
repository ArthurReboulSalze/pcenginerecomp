"""Authored command-line contracts for explicitly selected profile extensions."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.cli import main
from pcerecomp.observations import (compose_observation_profile, load_observation_profile,
                                    serialize_observation_profile)
from tests.test_observation_plan import capture, row


class AdditiveCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old = self.root/'old.json'
        self.new = self.root/'new.json'
        self.old.write_text(json.dumps(capture([row(0x4000, [0xa9, 1], 2, 0)])), encoding='utf-8')
        self.new.write_text(json.dumps(capture([row(0x4000, [0xa9, 1], 4, 0),
                                               row(0x4000, [0xa9, 2], 0, 3)])), encoding='utf-8')
        self.baseline = self.root/'baseline.json'
        self.baseline.write_bytes(serialize_observation_profile(
            compose_observation_profile([self.old], capacity=3)))
        self.originals = {p: p.read_bytes() for p in (self.old, self.new, self.baseline)}

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(map(str, args)))
        return code, out.getvalue(), err.getvalue()

    def test_profile_baseline_plan_matches_exact_output_without_writes(self):
        future = self.root/'untouched'/'profile.json'
        args = ('compose-observations', self.new, '--new-identities-only',
                '--baseline-profile', self.baseline)
        code, out, err = self.invoke(*args, '--dry-run', '--out', future)
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        self.assertTrue(plan['fits'])
        self.assertFalse(future.parent.exists())
        code, out, err = self.invoke(*args, '--out', future)
        self.assertEqual(code, 0, err)
        profile, digest = load_observation_profile(future)
        self.assertEqual(profile['schema'], 2)
        self.assertEqual(profile['capacity'], 3)
        self.assertEqual(profile['selected_historical_totals']['retired_instructions'], 5)
        self.assertEqual(profile['historical_totals']['retired_instructions'], 9)
        self.assertEqual(plan['combined']['serialized_sha256'], digest)
        self.assertEqual(plan['combined']['serialized_bytes'], future.stat().st_size)
        self.assertTrue(all(p.read_bytes() == b for p, b in self.originals.items()))

    def test_explicit_raw_baseline_selects_same_keys(self):
        out = self.root/'raw-baseline.json'
        code, text, err = self.invoke('compose-observations', self.new, '--new-identities-only',
                                     '--baseline-input', self.old, '--capacity', 3, '--out', out)
        self.assertEqual(code, 0, err)
        profile, _ = load_observation_profile(out)
        self.assertEqual(profile['selection_counts'], dict(original_contributions=3,
                         selected_contributions=2, omitted_contributions=1))

    def test_profile_baseline_requires_explicit_selection_mode(self):
        out = self.root/'refused.json'
        code, _, _ = self.invoke('compose-observations', self.new,
                                 '--baseline-profile', self.baseline, '--out', out)
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())

    def test_selection_without_baseline_refuses_before_creating_parent(self):
        out = self.root/'untouched'/'refused.json'
        code, _, _ = self.invoke('compose-observations', self.new, '--new-identities-only', '--out', out)
        self.assertEqual(code, 2)
        self.assertFalse(out.parent.exists())

    def test_refused_capacity_plan_is_json_and_never_writes(self):
        out = self.root/'refused.json'
        code, text, err = self.invoke('compose-observations', self.new, '--new-identities-only',
                                     '--baseline-profile', self.baseline, '--capacity', 1,
                                     '--dry-run', '--out', out)
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(text)['fits'])
        self.assertFalse(out.exists())

    def test_output_cannot_replace_bound_baseline_even_in_plan(self):
        code, text, _ = self.invoke('compose-observations', self.new, '--new-identities-only',
                                    '--baseline-profile', self.baseline, '--dry-run', '--out', self.baseline)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(text)['refusal']['code'], 'output_admission')
        self.assertEqual(self.baseline.read_bytes(), self.originals[self.baseline])

    def test_legacy_composition_keeps_original_v1_bytes(self):
        out = self.root/'legacy.json'
        code, text, err = self.invoke('compose-observations', self.new, '--baseline-input', self.old,
                                     '--out', out)
        self.assertEqual(code, 0, err)
        expected = serialize_observation_profile(compose_observation_profile([self.old, self.new]))
        self.assertEqual(out.read_bytes(), expected)
        self.assertEqual(json.loads(text)['sha256'], hashlib.sha256(expected).hexdigest())


if __name__ == '__main__':
    unittest.main()
