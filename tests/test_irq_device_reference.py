"""Authored journal-contract controls, without emulator/media dependencies.

The small synthetic callback records exercise evidence admission only. They
are not execution traces and do not establish CPU or device correctness.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.irq_trace import parse_trace
from scripts.irq_device_reference import (
    callback_shape, qualify_case, qualify_comparison, qualify_gear_journal,
    qualify_trace, strict_rows,
)


def encoded(rows):
    return b''.join(json.dumps(row, separators=(',', ':')).encode()+b'\n' for row in rows)


def cpu_callback(state, data):
    return dict(type='cpu', cycle=state['ticks'], pc=state['pc'],
                bank=state['mpr'][state['pc'] >> 13], bytes=data,
                **{k: state[k] for k in ('a', 'x', 'y', 'sp', 'p')})


def vdc_callback(event, cycle):
    return dict(type='vdc', cycle=cycle, event=event, chip=0, reg=0, raw=0,
                msb=0, value=0, value2=0, value3=0, param=1)


class IrqDeviceReferenceChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)/'journal.jsonl'

    def fixture(self, *, irq=False, fixed_wait=False, cd_write=None):
        state = dict(pc=0xE000, a=0, x=0, y=0, sp=255, p=4,
                     mpr=[0]*8, mpr_latch=0, physical_pc=0,
                     clock_divisor=12, ticks=0,
                     wram_sha256=hashlib.sha256(bytes(8192)).hexdigest())
        if cd_write is not None:
            state.update(a=0xC0 if cd_write == 2 else 2,
                         p=0x84 if cd_write == 2 else 4)
        initial = dict(state, pc=0xE001, physical_pc=1, ticks=24,
                       p=0 if irq else state['p'])
        data = [0xAD, 0, 0] if fixed_wait else [0xEA]
        if cd_write is not None: data = [0x8D, cd_write, 0x18]
        after = dict(initial, pc=0xE001+len(data), physical_pc=1+len(data),
                     ticks=96 if fixed_wait else 48)
        if cd_write is not None: after['ticks'] = 84
        vector = 0xFFF8 if irq else None
        if irq:
            after.update(pc=0xF800, physical_pc=0x1800, sp=252, p=4, ticks=144,
                         wram_sha256=hashlib.sha256(b'authored stack witness').hexdigest())

        def values(s, origin, sources=True, delivered=False):
            return [s[k] for k in ('pc', 'a', 'x', 'y', 'sp', 'p', 'clock_divisor')]+[
                s['ticks']-origin, *s['mpr'], s['mpr_latch'],
                int(delivered), vector if delivered else 0, 0, 0, 0, 0,
                0, 0, 0, 3 if sources else 0, 16 if sources else 0,
                64 if sources else 0, 64 if sources else 0, 0,
                200 if sources else 0, 4 if sources else 0,
                1 if sources else 0, 1 if sources else 0, 0, 0, 0, 0]

        before_values = values(initial, 24)
        after_values = values(after, 24, delivered=irq)
        if fixed_wait:
            after_values[26] = 1
            after_values[27] = 0
        if cd_write is not None:
            after_values[26] = 2
            after_values[29] = 0
            after_values[30] = int(cd_write == 2)
            after_values[31] = 0x8A if cd_write == 2 else 0x100
            if cd_write == 4: after_values[32:35] = [0, 0, 0]
        def literal(s, row, ordinal, delivered=False):
            s = dict(s, ticks=s['ticks']-24)
            return dict(ordinal=ordinal, state=s, values=copy.deepcopy(row),
                        wram_sha256=s['wram_sha256'], irq_count=int(delivered),
                        irq_vector=vector if delivered else None,
                        irq_return_pc=0xE002 if delivered else None,
                        fixed_wait_count=int(fixed_wait) if ordinal else 0,
                        internal_clocked_ticks=12 if fixed_wait and ordinal else 0)
        first = literal(initial, before_values, 0)
        last = literal(after, after_values, 1, irq)
        primer_data = [0x58] if irq else [0xEA]
        sources = [dict(pc=0xE000, mpr=[0]*8, physical=[0], data=primer_data, hits=1),
                   dict(pc=0xE001, mpr=[0]*8, physical=list(range(1, 1+len(data))), data=data, hits=1)]
        case = dict(id='authored-format-contract', primer_steps=1, steps=1,
                    block_steps=0, cd_source=64, expected_initial_gear=first,
                    expected_initial_runtime=copy.deepcopy(first), expected_gear=[last],
                    expected_runtime=[copy.deepcopy(last)], source_hits_gear=sources,
                    source_hits_runtime=copy.deepcopy(sources))
        header = dict(type='header', schema=2, format='pce-cpu-trace-2',
                      engine=dict(name='synthetic-contract', revision='1'*40,
                                  source_sha256='2'*64, binary_sha256='3'*64),
                      fixture_sha256='4'*64, case=case['id'], clock='master-ticks',
                      phase='retirement-boundary-after-irq', call_model='aggregate',
                      unavailable_fields=[])
        trace = parse_trace(encoded([
            header, dict(type='initial', state=initial),
            dict(type='event', ordinal=1, kind='opcode', entry=initial, state=after,
                 irq_vector=vector),
            dict(type='instruction', ordinal=1, event_start=1, event_end=1,
                 entry_pc=initial['pc'], entry_mpr=initial['mpr'], state=after,
                 irq_count=int(irq), irq_vector=vector),
            dict(type='final', executed=1, events=1, stop='instruction-limit',
                 complete=True, state=after)]))
        primer_events = [cpu_callback(state, primer_data), vdc_callback(7, 8),
                         vdc_callback(6, 16),
                         dict(type='scsi', cycle=20, event=0, command=0xDE,
                              phase=3, status=0, param=0, data=[0xDE]+[0]*9),
                         dict(type='cdrom', cycle=22, event=0, irq_type=64,
                              active=64, enabled=64, state=0, lba=0, param=0)]
        measured_events = [cpu_callback(initial, data)]
        if irq:
            measured_events.append(dict(type='TRACE_CPU_IRQ', cycle=24,
                                        pc=0xE002, vector=vector, mask=0))
        if cd_write is not None:
            measured_events.append(dict(type='cdrom', cycle=24, event=2 if cd_write == 2 else 4,
                                        irq_type=state['a'], active=64 if cd_write == 2 else 0,
                                        enabled=64, state=0, lba=0, param=0))
            if cd_write == 2:
                measured_events.append(dict(type='cdrom', cycle=84, event=1, irq_type=64,
                                            active=0, enabled=64, state=0, lba=0, param=0))
        measured_clocks = [dict(before=24, requested=after['ticks']-24, after=after['ticks'])]
        if fixed_wait:
            measured_clocks = [dict(before=24, requested=12, after=36),
                               dict(before=36, requested=60, after=96)]
        rows = [dict(phase='primer', ordinal=1, original_calls=1, entry=state,
                     state=initial, entry_values=values(state, 0, False),
                     values=values(initial, 0), returned_ticks=24,
                     internal_clocked_ticks=0, extra_ticks=0,
                     clocks=[dict(before=0, requested=24, after=24)], original_trace=primer_events),
                dict(phase='measured', ordinal=1, original_calls=1, entry=initial,
                     state=after, entry_values=before_values, values=after_values,
                     returned_ticks=after['ticks']-24,
                     internal_clocked_ticks=12 if fixed_wait else 0, extra_ticks=0,
                     clocks=measured_clocks, original_trace=measured_events)]
        return trace, case, rows

    def check(self, rows, trace, case):
        self.path.write_bytes(encoded(rows))
        return qualify_gear_journal(self.path, trace, case)

    def reject(self, mutate, *, irq=False, fixed_wait=False, message=None):
        trace, case, rows = self.fixture(irq=irq, fixed_wait=fixed_wait)
        mutate(rows)
        if message:
            with self.assertRaisesRegex(ValueError, message):
                self.check(rows, trace, case)
        else:
            with self.assertRaises(ValueError):
                self.check(rows, trace, case)

    def test_minimal_authored_format_and_fixed_wait_contracts(self):
        for options in ({}, dict(irq=True), dict(fixed_wait=True), dict(cd_write=2), dict(cd_write=4)):
            trace, case, rows = self.fixture(**options)
            with self.subTest(options=options):
                self.assertEqual(self.check(rows, trace, case)['measured'], 1)
                self.assertGreater(qualify_trace(trace, case, 'gear'), 0)

    def test_journal_fields_and_integer_types_are_strict(self):
        mutations = [lambda r: r[1].update(extra=True),
                     lambda r: r[1].pop('extra_ticks'),
                     lambda r: r[1].update(ordinal=True),
                     lambda r: r[1].update(original_calls=True),
                     lambda r: r[1].update(returned_ticks=False),
                     lambda r: r[1]['values'].__setitem__(26, True),
                     lambda r: r[1].update(phase='primer')]
        for mutation in mutations:
            with self.subTest(mutation=mutation): self.reject(mutation)

    def test_clock_spans_require_exact_extent_and_continuity(self):
        mutations = [lambda r: r[1].update(clocks=[]),
                     lambda r: r[1]['clocks'][0].update(before=25),
                     lambda r: r[1]['clocks'][0].update(requested=23),
                     lambda r: r[1]['clocks'][0].update(after=47),
                     lambda r: r[1]['clocks'][0].update(requested=True),
                     lambda r: r[1]['clocks'][0].update(unclaimed=0),
                     lambda r: r[1].update(internal_clocked_ticks=25),
                     lambda r: r[1].update(returned_ticks=23)]
        for mutation in mutations:
            with self.subTest(mutation=mutation): self.reject(mutation)

    def test_coherent_but_wrong_clock_partition_is_rejected(self):
        def mutation(rows):
            rows[1]['clocks'] = [dict(before=24, requested=6, after=30),
                                 dict(before=30, requested=66, after=96)]
        self.reject(mutation, fixed_wait=True, message='partition')

    def test_dynamic_wait_claim_and_extra_original_call_are_rejected(self):
        self.reject(lambda r: r[1].update(extra_ticks=1))
        self.reject(lambda r: r[1].update(original_calls=2))

    def test_primer_tii_requires_length_plus_two_original_calls(self):
        trace, case, rows = self.fixture()
        initial = dict(trace.initial, pc=0xE007, physical_pc=7, ticks=348)
        after = dict(trace.final['state'], pc=0xE008, physical_pc=8, ticks=372)
        body = [trace.header, dict(type='initial', state=initial),
                dict(type='event', ordinal=1, kind='opcode', entry=initial,
                     state=after, irq_vector=None),
                dict(type='instruction', ordinal=1, event_start=1, event_end=1,
                     entry_pc=initial['pc'], entry_mpr=initial['mpr'], state=after,
                     irq_count=0, irq_vector=None),
                dict(type='final', executed=1, events=1, stop='instruction-limit',
                     complete=True, state=after)]
        trace = parse_trace(encoded(body))
        # Authored TII $2200,$2200,2: 17+6*2 CPU cycles and four
        # original calls. The second callback group remains one NOP.
        data = [0x73, 0, 0x22, 0, 0x22, 2, 0]
        case['source_hits_gear'][0].update(data=data, physical=list(range(7)))
        case['source_hits_gear'][1].update(pc=0xE007, physical=[7])
        for wanted, pc in ((case['expected_initial_gear'], 0xE007),
                           (case['expected_gear'][0], 0xE008)):
            wanted['state'].update(pc=pc, physical_pc=pc&8191)
            wanted['values'][0] = pc
        rows[0].update(state=initial, returned_ticks=348, original_calls=4,
                       clocks=[dict(before=0, requested=348, after=348)])
        rows[0]['values'][0] = 0xE007; rows[0]['values'][7] = 348
        rows[0]['original_trace'][0]['bytes'] = data
        rows[1].update(entry=initial, state=after,
                       clocks=[dict(before=348, requested=24, after=372)])
        rows[1]['entry_values'][0] = 0xE007; rows[1]['values'][0] = 0xE008
        rows[1]['original_trace'][0].update(pc=0xE007, cycle=348)
        self.assertEqual(self.check(rows, trace, case)['measured'], 1)
        rows[0]['original_calls'] = 1
        with self.assertRaisesRegex(ValueError, 'continuation call count'):
            self.check(rows, trace, case)

    def test_callback_fields_types_bytes_and_extents_are_strict(self):
        base = cpu_callback(self.fixture()[0].initial, [0xEA])
        for field, value in (('unclaimed', 0), ('cycle', True), ('bank', 256),
                             ('pc', -1), ('a', False), ('bytes', []),
                             ('bytes', [256]), ('bytes', 'EA'), ('bytes', [0]*8)):
            event = dict(base); event[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                callback_shape(event)

    def test_callback_bounds_cover_each_device_shape(self):
        events = self.fixture()[2][0]['original_trace'][1:]
        for event in events: callback_shape(event)
        mutations = [(events[0], 'chip', 1), (events[0], 'event', 13),
                     (events[0], 'msb', 2), (events[2], 'data', [0]*17),
                     (events[2], 'data', [False]), (events[3], 'active', 256)]
        for event, field, value in mutations:
            event = dict(event); event[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                callback_shape(event)

    def test_callback_order_and_in_range_cpu_clock_are_checked(self):
        self.reject(lambda r: r[0]['original_trace'][2].update(cycle=7))
        self.reject(lambda r: r[1]['original_trace'][0].update(cycle=25))
        self.reject(lambda r: r[1]['original_trace'][0].update(cycle=49))

    def test_exact_irq_clock_return_pc_vector_and_mask(self):
        for field, value in (('cycle', 25), ('pc', 0xE003), ('mask', 1),
                             ('vector', 0xFFFA), ('mask', True)):
            with self.subTest(field=field, value=value):
                self.reject(lambda r, f=field, v=value: r[1]['original_trace'][1].update({f: v}), irq=True)

    def test_missing_extra_or_primer_irq_is_rejected(self):
        self.reject(lambda r: r[1]['original_trace'].pop(), irq=True)
        self.reject(lambda r: r[1]['original_trace'].append(copy.deepcopy(r[1]['original_trace'][1])), irq=True)
        self.reject(lambda r: r[0]['original_trace'].append(dict(type='TRACE_CPU_IRQ', cycle=24,
                                                             pc=0xE001, vector=0xFFF8, mask=0)))

    def test_fetched_register_mapping_and_bytes_are_bound(self):
        for field, value in (('a', 1), ('p', 0), ('bank', 1), ('pc', 0xE002), ('bytes', [0x78])):
            with self.subTest(field=field):
                self.reject(lambda r, f=field, v=value: r[1]['original_trace'][0].update({f: v}))

    def test_source_hit_count_and_full_mpr_identity_are_bound(self):
        for field, value in (('hits', 2), ('mpr', [1]+[0]*7), ('physical', [2]), ('data', [0x78])):
            trace, case, rows = self.fixture()
            case['source_hits_gear'][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(rows, trace, case)

    def test_cpu_ram_and_device_observation_chain_is_bound(self):
        self.reject(lambda r: r[1]['entry'].update(wram_sha256='f'*64))
        self.reject(lambda r: r[1]['entry_values'].__setitem__(29, 0))
        for column in (20, 21, 23, 26, 27, 28, 29, 30, 31, 32, 33, 38):
            with self.subTest(column=column):
                self.reject(lambda r, c=column: r[1]['values'].__setitem__(c, r[1]['values'][c]+1))

    def test_real_device_source_and_complete_command_witnesses_are_required(self):
        self.reject(lambda r: r[0]['original_trace'].pop(1))
        self.reject(lambda r: r[0]['original_trace'].pop(2))
        self.reject(lambda r: r[0]['original_trace'][1].update(param=2))
        self.reject(lambda r: r[0]['original_trace'][3].update(data=[0xDE]+[0]*8))
        self.reject(lambda r: r[0]['original_trace'][3].update(command=3))
        self.reject(lambda r: r[0]['original_trace'][4].update(irq_type=32))
        self.reject(lambda r: r[0]['original_trace'].pop(4))

    def test_cd_assertion_callback_must_report_its_source_active(self):
        self.reject(lambda r: r[0]['original_trace'][4].update(active=0))

    def test_directory_command_callback_must_come_from_command_phase(self):
        self.reject(lambda r: r[0]['original_trace'][3].update(phase=0))

    def test_pending_bootstrap_command_cannot_be_moved_after_initial_state(self):
        def mutation(rows):
            event = rows[0]['original_trace'].pop(3)
            event['cycle'] = rows[1]['entry']['ticks']
            rows[1]['original_trace'].append(event)
        self.reject(mutation)

    def test_pending_bootstrap_dma_cannot_be_moved_after_initial_state(self):
        def mutation(rows):
            for _ in range(2):
                event = rows[0]['original_trace'].pop(1)
                event['cycle'] = rows[1]['entry']['ticks']
                rows[1]['original_trace'].append(event)
        self.reject(mutation)

    def test_required_cd_enable_reset_and_clear_callbacks_cannot_be_omitted(self):
        for port, index in ((2, 1), (2, 2), (4, 1)):
            trace, case, rows = self.fixture(cd_write=port)
            rows[1]['original_trace'].pop(index)
            with self.subTest(port=port, index=index), self.assertRaisesRegex(ValueError, 'callback count'):
                self.check(rows, trace, case)

    def test_cd_access_and_ack_clear_callback_clocks_and_payload_are_bound(self):
        mutations = [(2, 1, 'cycle', 25), (2, 1, 'irq_type', 64),
                     (2, 1, 'enabled', 0), (2, 1, 'active', 0),
                     (2, 2, 'cycle', 83), (2, 2, 'active', 64),
                     (2, 2, 'irq_type', 32), (4, 1, 'cycle', 25),
                     (4, 1, 'active', 64), (4, 1, 'irq_type', 0)]
        for port, index, field, value in mutations:
            trace, case, rows = self.fixture(cd_write=port)
            rows[1]['original_trace'][index][field] = value
            with self.subTest(port=port, field=field, value=value), self.assertRaises(ValueError):
                self.check(rows, trace, case)

    def test_duplicate_json_nonfinite_and_nonobject_records_are_refused(self):
        trace, case, rows = self.fixture()
        for raw in (encoded(rows).replace(b'"ordinal":1', b'"ordinal":1,"ordinal":1', 1),
                    encoded(rows).replace(b'"returned_ticks":24', b'"returned_ticks":NaN', 1),
                    b'[]\n'):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                qualify_gear_journal(self.path, trace, case)

    def test_strict_rows_reads_authored_records_without_rewriting(self):
        rows = self.fixture()[2]
        raw = encoded(rows); self.path.write_bytes(raw)
        self.assertEqual(strict_rows(self.path), rows)
        self.assertEqual(self.path.read_bytes(), raw)

    def case_inputs(self):
        trace, case, _ = self.fixture()
        captures = {}; work = {}
        for tier in ('native', 'interpreter'):
            observations = []
            for source in case['source_hits_runtime']:
                item = {key: copy.deepcopy(source[key]) for key in ('pc', 'mpr', 'physical', 'data')}
                item.update(native_hits=int(tier == 'native'), interpreted_hits=int(tier == 'interpreter'))
                observations.append(item)
            captures[tier] = dict(runtime_abi=ABI, complete=True, retired_instructions=2,
                                  dropped_instructions=0, unreadable_instructions=0, observations=observations)
            work[tier] = dict(schema=1, case=case['id'], tier=tier, primer_steps=1,
                              measured_steps=1, native_steps=2 if tier == 'native' else 0,
                              interpreter_steps=2 if tier == 'interpreter' else 0,
                              block_steps=0, pure_guards=4 if tier == 'native' else 0,
                              raw_initial_ticks=trace.initial['ticks'],
                              literal_rows=[copy.deepcopy(case['expected_runtime'][0]['values'])])
        return case, dict(native=trace, interpreter=trace, gear=trace), captures, work

    def test_case_binds_all_tiers_and_finite_actual_work(self):
        result = qualify_case(*self.case_inputs())
        self.assertEqual(result['actual_retirements_per_tier'], 2)
        self.assertEqual(result['source_identities'], 2)

    def test_case_refuses_lost_source_or_foreign_execution(self):
        for field, value in (('runtime_abi', 23), ('complete', False),
                             ('dropped_instructions', 1), ('unreadable_instructions', 1),
                             ('retired_instructions', 1)):
            args = self.case_inputs(); args[2]['native'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): qualify_case(*args)
        args = self.case_inputs(); args[2]['native']['observations'][0]['interpreted_hits'] = 1
        with self.assertRaises(ValueError): qualify_case(*args)

    def test_case_receipt_fields_counts_and_device_literals_are_bound(self):
        for field, value in (('extra', 0), ('pure_guards', True), ('native_steps', 1),
                             ('raw_initial_ticks', 0), ('block_steps', 1), ('literal_rows', [])):
            args = self.case_inputs(); args[3]['native'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): qualify_case(*args)
        args = self.case_inputs(); args[3]['native']['literal_rows'][0][29] = 0
        with self.assertRaises(ValueError): qualify_case(*args)

    def test_runtime_capture_requires_each_full_source_key_and_hit(self):
        for field, value in (('pc', 0xE002), ('mpr', [0]*7+[1]),
                             ('physical', [8193]), ('data', [0x78]), ('native_hits', 2)):
            args = self.case_inputs(); args[2]['native']['observations'][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): qualify_case(*args)

    def test_trace_extent_and_device_column_count_are_exact(self):
        trace, case, rows = self.fixture(); case['steps'] = 2
        with self.assertRaises(ValueError): qualify_trace(trace, case, 'gear')
        self.reject(lambda r: r[1]['values'].pop())
        self.reject(lambda r: r[1]['entry_values'].append(0))

    def test_only_exact_declared_legacy_difference_is_accepted(self):
        qualify_comparison(dict(queued_accesses=True), dict(equal=True))
        with self.assertRaises(ValueError):
            qualify_comparison(dict(queued_accesses=True), dict(equal=False))
        case = dict(queued_accesses=False, kind='vdc-immediate-cancel')
        comparison = dict(equal=False, first_difference=dict(ordinal=2, field='irq_count', expected=0, actual=1))
        qualify_comparison(case, comparison)
        for field, value in (('ordinal', 3), ('field', 'state.pc'), ('expected', 1), ('actual', 0)):
            changed = copy.deepcopy(comparison); changed['first_difference'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                qualify_comparison(case, changed)
        with self.assertRaises(ValueError):
            qualify_comparison(dict(case, kind='unqualified-difference'), comparison)

    def test_trace_requires_independent_state_and_delivery_literals(self):
        for field, value in (('pc', 0xE003), ('mpr', [1]+[0]*7), ('p', 0), ('ticks', 25)):
            trace, case, _ = self.fixture(); case['expected_gear'][0]['state'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): qualify_trace(trace, case, 'gear')
        trace, case, _ = self.fixture(); case['expected_gear'][0]['irq_count'] = 1
        with self.assertRaises(ValueError): qualify_trace(trace, case, 'gear')


if __name__ == '__main__':
    unittest.main()
