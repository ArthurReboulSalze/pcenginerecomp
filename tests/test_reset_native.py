"""Authored reset capture promotion without rebuilding consumers in each test."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.abi import ABI
ROOT = Path(__file__).resolve().parent.parent
EXE = '.exe' if os.name == 'nt' else ''
HEADLESS = Path(os.environ.get('PCE_TEST_HEADLESS', ROOT/'build'/('pce-headless'+EXE)))
SPEC = importlib.util.spec_from_file_location('authored_reset_capture',
                                              ROOT/'examples/reset-consumer/capture.py')
EXAMPLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXAMPLE)


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless reset runner')
class ResetCapturePromotionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def train(self, profile='standard', capacity=64):
        output = self.root/'new-consumer'
        EXAMPLE.capture(output, HEADLESS, ROOT, profile, capacity)
        return output

    def assert_no_promotion(self, output):
        self.assertFalse((output/'module').exists())
        self.assertFalse((output/'project.toml').exists())

    def rewrite_capture(self, output, change):
        path = output/'actual-capture.json'
        raw = json.loads(path.read_text(encoding='utf-8'))
        change(raw)
        path.write_text(json.dumps(raw), encoding='utf-8')

    def test_actual_retirements_promote_all_mapping_and_mirror_contexts(self):
        from pcerecomp.capture import load_capture
        from pcerecomp.project import verify
        for profile in ('standard', 'super'):
            with self.subTest(profile=profile):
                output = self.root/profile
                EXAMPLE.capture(output, HEADLESS, ROOT, profile)
                capture, _ = load_capture(output/'actual-capture.json')
                self.assertEqual(capture['retired_instructions'], 200)
                self.assertEqual(len(capture['observations']), 16)
                self.assertEqual(len({tuple(item['mpr']) for item in capture['observations']}), 5)
                self.assertEqual({item['mpr'][7] for item in capture['observations']}, {0, 32, 64})
                self.assertEqual(capture['observations'][0]['physical'], [0, 1])
                self.assertIn(0x4000C, [item['physical'][0] for item in capture['observations']])
                self.assertIn(0x8001D, [item['physical'][0] for item in capture['observations']])
                self.assertEqual(sum(item['interpreted_hits'] for item in capture['observations']), 200)
                descriptor = EXAMPLE.promote(output, ROOT)
                checked = verify(descriptor)
                self.assertEqual(checked['config']['boot'], dict(mode='system-card-reset', profile=profile))
                self.assertEqual(checked['config']['runtime']['tier'], 'native')
                self.assertEqual(checked['config']['runtime']['audio'], 'off')
                self.assertNotIn('payload', checked['config'])
                manifest = json.loads((output/'module/module.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['capture_runtime_abi'], ABI)
                self.assertEqual(manifest['native_instructions_emitted'], 16)
                self.assertFalse(manifest['execution_evidence'])
                source = (output/'module/module.cpp').read_text(encoding='utf-8')
                self.assertIn('s.mpr[7]=s.a;', source)
                self.assertIn('bus.write_timed(', source)
                self.assertIn('bus.retire(s,', source)
                self.assertNotIn('interpret(', source)
                self.assertNotIn('interpreter_step(', source)

    def test_actual_capacity_loss_refuses_without_partial_emission(self):
        output = self.train(capacity=1)
        raw = json.loads((output/'actual-capture.json').read_text(encoding='utf-8'))
        self.assertFalse(raw['complete'])
        self.assertEqual(raw['dropped_instructions'], 199)
        with self.assertRaisesRegex(ValueError, 'incomplete capture'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_unreadable_retirement_refuses_without_partial_emission(self):
        output = self.train()
        def lose(raw):
            raw.update(complete=False, unreadable_instructions=1, retired_instructions=201)
        self.rewrite_capture(output, lose)
        with self.assertRaisesRegex(ValueError, 'incomplete capture'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_physical_address_cannot_be_relabelled_as_its_rom_mirror(self):
        output = self.train()
        self.rewrite_capture(output, lambda raw: raw['observations'][0]['physical'].__setitem__(0, 0x40000))
        with self.assertRaisesRegex(ValueError, 'physical mapping'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_valid_but_different_context_does_not_earn_native_coverage(self):
        output = self.train()
        # MPR2 does not drive these fetches, but remains part of dispatch identity.
        self.rewrite_capture(output, lambda raw: raw['observations'][0]['mpr'].__setitem__(2, 1))
        with self.assertRaisesRegex(ValueError, 'identities differ'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_authored_source_mutation_refuses_without_partial_emission(self):
        output = self.train()
        path = output/'authored-card.pce'
        raw = bytearray(path.read_bytes())
        raw[1] = 0
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'card changed'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_provenance_pin_mutation_refuses_without_partial_emission(self):
        output = self.train()
        path = output/'capture-run.json'
        raw = json.loads(path.read_text(encoding='utf-8'))
        raw['tool']['source_sha256'] = '0'*64
        path.write_text(json.dumps(raw), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'provenance or toolkit pin changed'):
            EXAMPLE.promote(output, ROOT)
        self.assert_no_promotion(output)

    def test_repeat_capture_or_promotion_preserves_prior_outputs(self):
        output = self.train()
        with self.assertRaisesRegex(ValueError, 'new output directory'):
            EXAMPLE.capture(output, HEADLESS, ROOT)
        descriptor = EXAMPLE.promote(output, ROOT)
        before = descriptor.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            EXAMPLE.promote(output, ROOT)
        self.assertEqual(descriptor.read_bytes(), before)

    def test_report_exit_schema_completeness_and_capacity_are_strict(self):
        output = self.train()
        path = output/'capture-run.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        for field, value in (('exit_code', 3), ('exit_code', False), ('schema', True),
                             ('schema', 2), ('complete', False), ('capacity', 1),
                             ('capacity', True)):
            with self.subTest(field=field, value=value):
                changed = dict(original)
                changed[field] = value
                path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaises(ValueError):
                    EXAMPLE.promote(output, ROOT)
                self.assert_no_promotion(output)

    def test_report_argv_profile_paths_capacity_and_tier_are_bound(self):
        output = self.train()
        path = output/'capture-run.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        for index, value in ((2, 'super'), (3, 'elsewhere.pce'), (4, '201'), (6, 'native'),
                             (12, 'different-capture.json'), (14, '1'), (0, 'relative-runner')):
            with self.subTest(index=index, value=value):
                changed = dict(original)
                changed['argv'] = list(original['argv'])
                changed['argv'][index] = value
                path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'argv'):
                    EXAMPLE.promote(output, ROOT)
                self.assert_no_promotion(output)

    def test_retained_stdout_and_stderr_hashes_are_bound(self):
        for filename in ('run.stdout', 'run.stderr'):
            with self.subTest(filename=filename):
                output = self.root/filename.replace('.', '-')
                EXAMPLE.capture(output, HEADLESS, ROOT)
                path = output/filename
                path.write_text(path.read_text(encoding='utf-8')+'\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'stdout/stderr binding changed'):
                    EXAMPLE.promote(output, ROOT)
                self.assert_no_promotion(output)

    def test_dangling_module_or_descriptor_output_is_preserved(self):
        output = self.train()
        for name in ('module', 'project.toml'):
            with self.subTest(name=name):
                path = output/name
                try:
                    path.symlink_to(output/'missing-target', target_is_directory=name == 'module')
                except OSError:
                    # Windows may lack Developer Mode. Exercise the actual
                    # lexistence branch without skipping the refusal check.
                    real_is_symlink = Path.is_symlink
                    with patch.object(Path, 'is_symlink', lambda item:
                                      item == path or real_is_symlink(item)):
                        with self.assertRaisesRegex(ValueError, 'already exists'):
                            EXAMPLE.promote(output, ROOT)
                    self.assert_no_promotion(output)
                else:
                    try:
                        with self.assertRaisesRegex(ValueError, 'already exists'):
                            EXAMPLE.promote(output, ROOT)
                        self.assertTrue(path.is_symlink())
                        self.assertFalse((output/'missing-target').exists())
                    finally:
                        path.unlink()
