"""Independent authored framing/sense expectations and strict evidence refusals."""
import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from scripts import cd_unknown_reference as reference


def sample(profile='tool-nec'):
    case = [dict(id='authored', operations=[('r', 1), ('u', 0xA0, 12, 1), ('p',)])]
    rows = copy.deepcopy(reference.expected(case, profile))
    for row in rows:
        if row['kind'] in ('unknown', 'abort'):
            row['pins'] = [0] * 5
            row['edges'] = [[1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0] for _ in range(row['count'])]
    return rows, reference.expected(case, profile)


class UnknownCdReferenceTests(unittest.TestCase):
    def test_all_248_invalid_ids_use_independent_group_lengths(self):
        for profile in ('gear', 'tool-gear', 'beetle', 'tool-nec'):
            plans = reference.plans(profile)
            self.assertEqual(len(plans), 252)
            opcodes = [p['operations'][1] for p in plans[:248]]
            self.assertEqual({o[1] for o in opcodes}, set(range(256)) - {0, 3, 8, 216, 217, 218, 221, 222})
            self.assertTrue(all(o[2] == (1 if profile in ('gear', 'tool-gear') else (6, 6, 10, 10, 10, 10, 10, 10, 10, 10, 12, 12, 10, 10, 10, 10)[o[1] >> 4]) for o in opcodes))

    def test_error_wire_values_remain_distinct_and_gear_good_is_explicit(self):
        case = [dict(id='one', operations=[('r', 1), ('u', 255, 10, 0), ('p',)])]
        beetle = reference.expected(case, 'beetle')
        tool = reference.expected(case, 'tool-nec')
        gear = reference.expected(case, 'gear')
        self.assertEqual((beetle[0]['status'], beetle[0]['message']), (1, 0))
        self.assertEqual((tool[0]['status'], tool[0]['message']), (2, 2))
        self.assertEqual((gear[0]['status'], gear[0]['message']), (0, 0))
        self.assertEqual(tool[1]['values'], [5, 32, 0, 0])
        self.assertEqual(beetle[1]['values'], tool[1]['values'])

    def test_sense_lifetime_survives_warm_reset_and_success_then_consumes(self):
        ops = [('r', 1), ('u', 1, 6, 0), ('z',), reference.command(0), ('p',), reference.command(3), ('p',), reference.command(3), ('p',)]
        rows = reference.expected([dict(id='life', operations=ops)], 'tool-nec')
        self.assertEqual(rows[3], dict(kind='pending', values=[5, 32, 0, 0]))
        self.assertEqual(rows[4]['data'], [112, 0, 5, 0, 0, 0, 0, 10, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0])
        self.assertEqual(rows[5], dict(kind='pending', values=[0, 0, 0, 0]))
        self.assertEqual(rows[6]['data'], [112, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_partial_command_reset_difference_is_explicit(self):
        case = [dict(id='partial', operations=[('r', 1), ('a', 1, 5, 0)])]
        beetle = reference.expected(case, 'beetle')[0]
        tool = reference.expected(case, 'tool-nec')[0]
        self.assertEqual((beetle['buffered_before_reset'], beetle['buffered_after_reset']), (5, 5))
        self.assertEqual((tool['buffered_before_reset'], tool['buffered_after_reset']), (5, 0))

    def test_gear_unknown_policy_does_not_turn_toolkit_sense_into_gear_stub(self):
        case = [dict(id='sense', operations=[('r', 1), reference.command(3)])]
        self.assertEqual(reference.expected(case, 'gear')[0]['data'], [])
        self.assertEqual(reference.expected(case, 'tool-gear')[0]['data'],
                         [112, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_changed_or_missing_bound_source_cannot_be_finalized_as_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'authored-source'; path.write_bytes(b'bound')
            bindings = {'authored_sources': {str(path): hashlib.sha256(b'bound').hexdigest()}}
            report = {'result': 'incomplete'}
            reference.require_preservation(report, bindings)
            self.assertEqual(report['preservation'], {'authored_sources': True})
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError): reference.require_preservation(report, bindings)
            self.assertEqual(report['result'], 'failed-preservation')
            self.assertEqual(report['preservation'], {'authored_sources': False})
            path.unlink()
            with self.assertRaises(ValueError): reference.require_preservation(report, bindings)

    def test_typed_rows_and_retained_edges(self):
        rows, wanted = sample()
        self.assertIs(reference.validate_rows(rows, wanted), rows)
        changed = copy.deepcopy(rows); changed[0]['status'] = True
        with self.assertRaises(ValueError): reference.validate_rows(changed, wanted)
        changed = copy.deepcopy(rows); changed[0]['edges'][0][6] = True
        with self.assertRaises(ValueError): reference.validate_rows(changed, wanted)

    def test_held_ack_and_partial_direction_corruptions_refused(self):
        rows, wanted = sample()
        for at in (6, 11, 17):
            changed = copy.deepcopy(rows); changed[0]['edges'][0][at] ^= 1
            with self.assertRaises(ValueError): reference.validate_rows(changed, wanted)

    def test_missing_extra_reordered_and_changed_payload_refused(self):
        rows, wanted = sample()
        variants = [rows[:-1], rows + [rows[0]], list(reversed(rows))]
        changed = copy.deepcopy(rows); changed[0]['invented'] = 0; variants.append(changed)
        changed = copy.deepcopy(rows); changed[1]['values'][1] = 33; variants.append(changed)
        changed = copy.deepcopy(rows); changed[0]['edges'].pop(); variants.append(changed)
        changed = copy.deepcopy(rows); changed[0]['pins'][0] = 1; variants.append(changed)
        for changed in variants:
            with self.assertRaises(ValueError): reference.validate_rows(changed, wanted)

    def test_authored_guest_has_finite_boot_and_expected_invalid_sense_flow(self):
        image, end = reference.firmware()
        self.assertEqual(len(image), 262144)
        self.assertEqual(image[8190:8192], bytes((0, 225)))
        self.assertEqual(image[end - 0xE000:end - 0xE000 + 2], b'\x80\xfe')
        self.assertLess(end, 0xFF00)
        plan = reference.guest_plan()[0]['operations']
        self.assertEqual(plan[0], ('r', 1))
        self.assertEqual(plan[1], ('g', end))
        self.assertEqual(len([o for o in plan if o[0] == 'k']), 44)

    def test_unknown_profile_and_unauthored_operation_refused(self):
        with self.assertRaises(ValueError): reference.plans('automatic')
        with self.assertRaises(ValueError): reference.expected([], 'automatic')
        with self.assertRaises(ValueError): reference.expected([dict(operations=[('invented',)])], 'tool-nec')

    def test_external_binary_cannot_be_presented_as_fresh_native_qualification(self):
        for reference_only, native, probe in ((True, True, None), (True, False, Path('external')), (False, True, Path('external'))):
            with self.assertRaises(ValueError):
                reference.validate_options(SimpleNamespace(reference_only=reference_only, native=native, probe=probe))
        reference.validate_options(SimpleNamespace(reference_only=False, native=True, probe=None))
        reference.validate_options(SimpleNamespace(reference_only=True, native=False, probe=None))


if __name__ == '__main__':
    unittest.main()
