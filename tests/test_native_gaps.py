"""Independent authored membership/window expectations; no retail input or SDK.

The expected classifications and literal wrapped fetch addresses below are
declared independently of the report and catalog reconstruction algorithms.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.native_catalog import NativeCatalog
from pcerecomp.native_gaps import report_native_gaps


MPR = [255, 248, 128, 129, 130, 131, 132, 0]
U64 = (1 << 64) - 1


def row(pc=0x4000, data=(0xA9, 42), *, physical=None, mpr=None, native=0, interpreted=1):
    # All defaults remain in one authored physical page; boundary fixtures
    # always supply their independently calculated physical addresses.
    if physical is None:
        physical = [0x100000 + pc - 0x4000 + offset for offset in range(len(data))]
    return dict(pc=pc, mpr=list(MPR if mpr is None else mpr), physical=list(physical),
                data=list(data), native_hits=native, interpreted_hits=interpreted)


def identity(value):
    return value['pc'], tuple(value['mpr']), tuple(value['physical']), tuple(value['data'])


def capture(rows=(), *, abi=29, origin=None):
    result = dict(schema=1, runtime_abi=abi, capacity=64, dropped_instructions=0,
                  unreadable_instructions=0, retired_instructions=sum(
                      value['native_hits'] + value['interpreted_hits'] for value in rows),
                  complete=True, observations=list(rows))
    if origin is not None:
        result['checkpoint_origin'] = dict(origin)
    return result


def catalog(emitted=(), *, excluded=(), unsupported=()):
    emitted, excluded, unsupported = (frozenset(identity(value) for value in group)
                                      for group in (emitted, excluded, unsupported))
    observed = emitted | excluded | unsupported
    return NativeCatalog(runtime_abi=29, observed=observed, emitted=emitted,
                         excluded=excluded, unsupported=unsupported,
                         counts=dict(observed_instructions=len(observed),
                                     native_instructions_emitted=len(emitted),
                                     native_contexts=len({key[1] for key in emitted}),
                                     excluded_observations=len(excluded),
                                     excluded_retired_hits=777777 if excluded else 0,
                                     unsupported_observations=len(unsupported)),
                         provenance=dict(scope='authored declared catalog fixture',
                                         excluded_physical_ranges=[dict(start=address, length=1)
                                             for address in sorted({address for key in excluded for address in key[2]})],
                                         original_inputs=[dict(native_hits=999999, interpreted_hits=888888,
                                                               retired_instructions=1888887)],
                                         execution_evidence=False))


class NativeGapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0

    def write(self, value=None, *, raw=None, name=None):
        self.counter += 1
        path = self.root / (name or f'capture-{self.counter}.json')
        path.write_bytes(raw if raw is not None else
                         (json.dumps(value, separators=(',', ':')) + '\n').encode())
        return path

    def summary(self, report, **expected):
        for name, count in expected.items():
            self.assertEqual(report['summary'][name], count, name)

    def test_full_identity_membership_tiers_and_unexercised_are_distinct(self):
        a = row(native=3, interpreted=2)
        changed_bytes = row(data=(0xA9, 43), interpreted=7)
        changed_mpr = MPR.copy(); changed_mpr[7] = 1  # Unused by this fetch.
        changed_context = row(mpr=changed_mpr, interpreted=11)
        cross_page = row(0x5FFF, (0xAD, 1, 2), physical=(0x101FFF, 0x102000, 0x102001),
                         native=13, interpreted=0)
        wrapped = row(0xFFFF, (0xA9, 3), physical=(0x1FFF, 0x1FE000), interpreted=17)
        unseen = row(0x4010, (0xEA,))
        excluded = row(0x4020, (0xEA,), interpreted=19)
        unsupported = row(0x4030, (0xFC,), interpreted=23)
        outside = row(0x4040, (0xEA,), native=29, interpreted=0)
        declared = catalog((a, cross_page, wrapped, unseen), excluded=(excluded,),
                           unsupported=(unsupported,))
        values = [a, changed_bytes, changed_context, cross_page, wrapped, excluded, unsupported, outside]
        report = report_native_gaps(declared, [self.write(capture(values))])
        self.assertEqual(report['format'], 'pce-native-gap-report-1')
        self.assertIs(report['qualification'], False)
        self.assertIs(report['code_bearing'], True)
        self.assertEqual(report['policy'], 'identity-union')
        self.summary(report, union_keys=8, emitted_observed=3, emitted_unexercised=1,
                     excluded_observed=1, unsupported_observed=1, uncompiled_observed=3,
                     native_outside_catalog=1)
        actual = {identity(item): item for item in report['identities']}
        for value in (a, cross_page, wrapped):
            self.assertEqual(actual[identity(value)]['category'], 'emitted')
        self.assertEqual(actual[identity(excluded)]['category'], 'excluded')
        self.assertEqual(actual[identity(unsupported)]['category'], 'unsupported')
        for value in (changed_bytes, changed_context, outside):
            self.assertEqual(actual[identity(value)]['category'], 'uncompiled')
        self.assertEqual([identity(item) for item in report['emitted_unexercised']], [identity(unseen)])
        source = report['inputs'][0]
        self.assertEqual((source['native_steps'], source['interpreter_steps'], source['retired_instructions']),
                         (45, 79, 124))
        self.assertEqual(actual[identity(a)]['observations'], [dict(
            input_sha256=source['sha256'], native_hits=3, interpreted_hits=2)])

    def test_every_mpr_register_participates_even_when_fetch_addresses_match(self):
        original = row(native=2, interpreted=0)
        alternatives = []
        for index in range(8):
            mapping = MPR.copy(); mapping[index] ^= 1
            physical = ((0x100000 ^ 0x2000, 0x100001 ^ 0x2000)
                        if index == 2 else (0x100000, 0x100001))
            alternatives.append(row(mpr=mapping, physical=physical))
        report = report_native_gaps(catalog((original,)), [self.write(capture([original, *alternatives]))])
        self.summary(report, union_keys=9, emitted_observed=1, uncompiled_observed=8)
        self.assertEqual(len({identity(item) for item in report['identities']}), 9)

    def test_identical_file_bytes_are_one_input_with_sorted_basename_aliases(self):
        value = capture([row(native=4, interpreted=3)])
        one = self.write(value, name='zeta.json')
        alias = self.write(raw=one.read_bytes(), name='alpha.json')
        declared = catalog((row(),))
        forward = report_native_gaps(declared, [one, alias, one])
        reverse = report_native_gaps(declared, [alias, one, alias])
        self.assertEqual(forward, reverse)
        self.assertEqual(len(forward['inputs']), 1)
        self.assertEqual(forward['inputs'][0]['aliases'], ['alpha.json', 'zeta.json'])
        self.assertEqual(forward['inputs'][0]['sha256'], hashlib.sha256(one.read_bytes()).hexdigest())
        self.assertEqual(forward['inputs'][0]['retired_instructions'], 7)
        self.assertEqual(len(forward['identities'][0]['observations']), 1)
        self.assertNotIn(str(self.root), json.dumps(forward))

    def test_overlapping_distinct_inputs_preserve_counts_without_aggregate_work(self):
        first = self.write(capture([row(native=3, interpreted=2)]), name='first.json')
        second = self.write(capture([row(native=5, interpreted=0)]), name='second.json')
        report = report_native_gaps(catalog((row(),)), [second, first])
        self.assertEqual(report, report_native_gaps(catalog((row(),)), [first, second]))
        self.summary(report, union_keys=1, emitted_observed=1, emitted_unexercised=0)
        actual = report['identities'][0]
        self.assertEqual(len(actual['observations']), 2)
        self.assertEqual(sorted((item['native_hits'], item['interpreted_hits'])
                                for item in actual['observations']), [(3, 2), (5, 0)])
        for field in ('native_hits', 'interpreted_hits', 'retired_instructions',
                      'native_steps', 'interpreter_steps', 'native_fraction'):
            self.assertNotIn(field, actual)
            self.assertNotIn(field, report['summary'])

    def test_original_capture_abis_and_checkpoint_prefix_remain_provenance(self):
        origin = dict(sha256='a' * 64, ticks=987654321, frame=123456,
                      native_steps=1000000, interpreter_steps=100)
        paths = [self.write(capture([row(native=5, interpreted=2)], abi=abi, origin=origin))
                 for abi in (12, 28, 29)]
        report = report_native_gaps(catalog((row(),)), paths)
        self.assertEqual(report['runtime_abi'], 29)
        self.assertEqual(sorted(item['runtime_abi'] for item in report['inputs']), [12, 28, 29])
        for item in report['inputs']:
            self.assertEqual(item['checkpoint_origin'], origin)
            self.assertEqual((item['native_steps'], item['interpreter_steps'], item['retired_instructions']), (5, 2, 7))
        self.assertEqual(len(report['identities'][0]['observations']), 3)

    def test_different_serializations_have_separate_digests_but_one_identity_union(self):
        value = capture([row(native=1, interpreted=0)])
        first = self.write(value)
        second = self.write(raw=json.dumps(value, indent=2).encode())
        report = report_native_gaps(catalog((row(),)), [first, second])
        self.assertEqual(len(report['inputs']), 2)
        self.summary(report, union_keys=1, emitted_observed=1)
        self.assertEqual(len(report['identities'][0]['observations']), 2)

    def test_empty_lossless_window_does_not_borrow_historical_profile_hits(self):
        report = report_native_gaps(catalog((row(), row(0x4010, (0xEA,)))),
                                    [self.write(capture())])
        self.summary(report, union_keys=0, emitted_observed=0, emitted_unexercised=2)
        self.assertEqual(report['identities'], [])
        self.assertEqual(report['inputs'][0]['retired_instructions'], 0)

    def test_lossy_or_inconsistent_captures_do_not_establish_unexercised_membership(self):
        declared = catalog((row(),))
        for loss in ('dropped_instructions', 'unreadable_instructions'):
            bad = capture([row()]); bad[loss] = 1; bad['retired_instructions'] = 2; bad['complete'] = False
            with self.subTest(loss=loss), self.assertRaises(ValueError):
                report_native_gaps(declared, [self.write(bad)])
        bad = capture([row()]); bad['retired_instructions'] = 2
        with self.assertRaises(ValueError):
            report_native_gaps(declared, [self.write(bad)])

    def test_strict_json_refuses_duplicate_float_nonfinite_and_extra_fields(self):
        original = json.dumps(capture([row()]), separators=(',', ':')).encode()
        cases = [original.replace(b'"schema":1', b'"schema":1,"schema":1'),
                 original.replace(b'"retired_instructions":1', b'"retired_instructions":1.0'),
                 original.replace(b'"retired_instructions":1', b'"retired_instructions":NaN'),
                 original.replace(b'"retired_instructions":1', b'"retired_instructions":1e9999'),
                 original[:-1] + b',"untrusted":Infinity}']
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                report_native_gaps(catalog((row(),)), [self.write(raw=raw)])

    def test_unsigned_types_totals_and_source_mapping_refuse_before_classification(self):
        mutations = [lambda c: c.update(runtime_abi=True), lambda c: c.update(runtime_abi=11),
                     lambda c: c.update(capacity=True), lambda c: c.update(retired_instructions=True),
                     lambda c: c['observations'][0].update(native_hits=True),
                     lambda c: c['observations'][0].update(interpreted_hits=-1),
                     lambda c: c['observations'][0].update(native_hits=U64 + 1),
                     lambda c: c['observations'][0].update(native_hits=U64, interpreted_hits=1),
                     lambda c: c['observations'][0].update(native_hits=0, interpreted_hits=0),
                     lambda c: c['observations'][0]['mpr'].__setitem__(7, False),
                     lambda c: c['observations'][0]['data'].__setitem__(1, 256),
                     lambda c: c['observations'][0]['physical'].__setitem__(1, 0x100002),
                     lambda c: c['observations'][0].update(data=[0xAD, 1], physical=[0x100000, 0x100001]),
                     lambda c: c['observations'].append(copy.deepcopy(c['observations'][0]))]
        for mutate in mutations:
            bad = capture([row()]); mutate(bad)
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(ValueError):
                report_native_gaps(catalog((row(),)), [self.write(bad)])

    def test_input_sequence_bound_includes_duplicate_arguments(self):
        path = self.write(capture([row()]))
        with self.assertRaises(ValueError):
            report_native_gaps(catalog((row(),)), [path] * 257)

    def test_new_identity_exclusion_checks_operand_bytes_before_unsupported_opcode(self):
        anchor = row(0x6000, (0xEA,), physical=(0x102000,))
        crossing = row(0x5FFF, (0xAD, 1, 2), physical=(0x101FFF, 0x102000, 0x102001))
        reserved = row(0x6000, (0xFC,), physical=(0x102000,))
        declared = catalog(excluded=(anchor,))
        report = report_native_gaps(declared, [self.write(capture([crossing, reserved]))])
        self.summary(report, union_keys=2, excluded_observed=2, unsupported_observed=0,
                     uncompiled_observed=0, emitted_unexercised=0)
        self.assertEqual({item['category'] for item in report['identities']}, {'excluded'})
        self.assertTrue(all(item['catalog_identity'] is False for item in report['identities']))

    def test_input_bytes_and_union_bounds_refuse_without_silent_truncation(self):
        first = self.write(capture([row()]))
        alias = self.write(raw=first.read_bytes())
        second = self.write(capture([row(data=(0xA9, 43))]))
        size = len(first.read_bytes())
        self.assertEqual(size, len(second.read_bytes()))
        with patch('pcerecomp.native_gaps.MAX_CAPTURE_BYTES', size - 1):
            with self.assertRaises(ValueError):
                report_native_gaps(catalog((row(),)), [first])
        with patch('pcerecomp.native_gaps.MAX_TOTAL_INPUT_BYTES', size):
            self.assertEqual(len(report_native_gaps(catalog((row(),)), [first, alias])['inputs']), 1)
            with self.assertRaises(ValueError):
                report_native_gaps(catalog((row(),)), [first, second])
        with patch('pcerecomp.native_gaps.MAX_OBSERVATIONS', 1):
            with self.assertRaises(ValueError):
                report_native_gaps(catalog((row(),)), [first, second])

    def test_partition_overlap_or_missing_observed_membership_refuses(self):
        from dataclasses import replace
        declared = catalog((row(),))
        malformed = [replace(declared, excluded=declared.emitted),
                     replace(declared, observed=frozenset())]
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(ValueError):
                report_native_gaps(value, [self.write(capture([row()]))])

    def test_same_size_same_timestamp_input_change_is_not_a_mixed_report_epoch(self):
        first = self.write(capture([row()]))
        second = self.write(capture([row(data=(0xA9, 43))]))
        changed = (json.dumps(capture([row(interpreted=2)]), separators=(',', ':')) + '\n').encode()
        self.assertEqual(len(changed), len(first.read_bytes()))
        real_open = Path.open
        mutated = False

        def external_change(path, *args, **kwargs):
            nonlocal mutated
            if path == second and not mutated:
                stamp = first.stat()
                with real_open(first, 'wb') as stream:
                    stream.write(changed)
                os.utime(first, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                mutated = True
            return real_open(path, *args, **kwargs)

        with patch.object(Path, 'open', new=external_change):
            with self.assertRaisesRegex(ValueError, 'changed'):
                report_native_gaps(catalog((row(),)), [first, second])
        self.assertTrue(mutated)

    def test_missing_cost_order_and_tier_counts_are_per_input_without_cross_window_sum(self):
        a = row(interpreted=7)
        b = row(data=(0xA9, 43), native=3, interpreted=7)
        zero = row(0x4010, (0xEA,), native=9, interpreted=0)
        first = self.write(capture([b, zero, a]), name='first.json')
        second = self.write(capture([row(interpreted=2),
                                     row(data=(0xA9, 43), interpreted=10)]), name='second.json')
        report = report_native_gaps(catalog(), [second, first])
        by_digest = {item['sha256']: item for item in report['inputs']}
        first_rows = by_digest[hashlib.sha256(first.read_bytes()).hexdigest()]['uncompiled_by_interpreted_hits']
        second_rows = by_digest[hashlib.sha256(second.read_bytes()).hexdigest()]['uncompiled_by_interpreted_hits']
        self.assertEqual([identity(item) for item in first_rows], [identity(a), identity(b), identity(zero)])
        self.assertEqual([(item['native_hits'], item['interpreted_hits']) for item in first_rows],
                         [(0, 7), (3, 7), (9, 0)])
        self.assertEqual([identity(item) for item in second_rows], [identity(b), identity(a)])
        self.assertEqual([(item['native_hits'], item['interpreted_hits']) for item in second_rows],
                         [(0, 10), (0, 2)])
        self.summary(report, union_keys=3, uncompiled_observed=3, native_outside_catalog=2)


if __name__ == '__main__':
    unittest.main()
