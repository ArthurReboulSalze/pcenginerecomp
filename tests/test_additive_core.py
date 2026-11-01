"""Additional authored additive operation-bound admission regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import observations as o
from tests.test_additive_observations import capture, row


class AdditiveOperationBounds(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = []
        for index in range(3):
            path = self.root / f'input-{index}.json'
            path.write_text(json.dumps(capture([row(0x4000, [0xa9, index], 0, 1)])),
                            encoding='utf-8')
            self.inputs.append(path)
        profile = o.compose_observation_profile(self.inputs[:2])
        self.baseline = self.root / 'baseline.json'
        self.baseline.write_bytes(o.serialize_observation_profile(profile))

    def test_baseline_profile_counts_as_one_operation_path(self):
        plan = o.plan_additive_observation_profile([], baseline_profile=self.baseline)
        self.assertTrue(plan['fits'], plan)
        self.assertEqual(plan['input_paths'], 1)
        self.assertEqual(plan['headroom']['input_paths'], 255)
        self.assertEqual(plan['combined']['unique_inputs'], 2)

    def test_duplicate_path_arguments_cannot_exceed_operation_limit(self):
        with patch.object(o, 'MAX_INPUTS', 2):
            with self.assertRaisesRegex(ValueError, 'At most 2 input paths'):
                o.compose_additive_observation_profile([self.inputs[0]] * 2,
                                                       baseline_profile=self.baseline)
            plan = o.plan_additive_observation_profile([self.inputs[0]] * 2,
                                                       baseline_profile=self.baseline)
        self.assertFalse(plan['fits'])
        self.assertEqual(plan['refusal']['resource'], 'input_paths')
        self.assertEqual(plan['refusal']['required_at_least'], 3)
        self.assertIsNone(plan['combined']['unique_inputs'])

    def test_distinct_input_refusal_is_not_reported_as_zero_inputs(self):
        with patch.object(o, 'MAX_INPUTS', 2):
            with self.assertRaisesRegex(ValueError, 'input capacity exceeded'):
                o.compose_additive_observation_profile([self.inputs[2]],
                                                       baseline_profile=self.baseline)
            plan = o.plan_additive_observation_profile([self.inputs[2]],
                                                       baseline_profile=self.baseline)
        self.assertFalse(plan['fits'])
        self.assertEqual(plan['refusal'], dict(code='admission_bound', resource='unique_inputs',
            limit=2, required_at_least=3, exact_required=None))

    def test_stage_argument_traversal_is_bounded_by_original_input_count(self):
        value = o.compose_additive_observation_profile([], baseline_profile=self.baseline)
        value['selection_stages'] = [[value['inputs'][0]['sha256']] * 3]
        with self.assertRaisesRegex(ValueError, 'stages must be nonempty lists'):
            o.validate_observation_profile(value)


if __name__ == '__main__':
    unittest.main()
