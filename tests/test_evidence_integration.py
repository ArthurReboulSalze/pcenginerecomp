"""Authored evidence call-path fixtures; no game, SDK or guest is executed."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import qualification as q
from pcerecomp import snapshots
from pcerecomp.snapshots import SnapshotError, SnapshotStore


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AuthoredPlan:
    """Five explicitly carried records and fourteen new general stage records."""

    def __init__(self, root):
        self.root = Path(root)
        self.refs = {}
        self.payloads = {}
        self.carried_names = (
            'reference_alpha', 'reference_beta', 'reference_gamma', 'initial', 'extension')
        self.new_names = tuple(f'stage_{number:02}' for number in range(14))
        self.roles = self.carried_names + self.new_names
        self.binary = self.root / 'authored-artifact.bin'
        self.binary.write_bytes(b'authored artifact alpha\n')
        self.binary_ref = {'path': str(self.binary), 'sha256': digest(self.binary)}
        contract_inputs = {self.binary_ref['path']: self.binary_ref['sha256']}
        self.old_producer = self.put('old-producer.json', {'authored_producer': 'original'})
        self.producer = self.put('producer.json', {'authored_producer': 'current'})
        self.old_contract_ref = self.put('old-contract.json', {
            'schema': 1, 'kind': 'authored-contract', 'policy': 'original',
            'input_bindings': contract_inputs})
        self.contract_ref = self.put('contract.json', {
            'schema': 1, 'kind': 'authored-contract', 'policy': 'current',
            'input_bindings': contract_inputs})
        self.old_contract = q.DocumentSpec(self.old_contract_ref, 1, 'authored-contract')
        self.contract = q.DocumentSpec(self.contract_ref, 1, 'authored-contract')
        self.specs = {}
        previous = None
        for name in self.roles:
            old = name in self.carried_names
            contract = self.old_contract_ref if old else self.contract_ref
            producer = self.old_producer if old else self.producer
            inputs = {contract['path']: contract['sha256'],
                      producer['path']: producer['sha256'],
                      self.binary_ref['path']: self.binary_ref['sha256']}
            if previous is not None:
                inputs[self.refs[previous]['path']] = self.refs[previous]['sha256']
            value = dict(schema=1, kind='authored-receipt', passed=True,
                         role=name, contract=contract, producer=producer,
                         input_bindings=inputs, packet_count=1,
                         payload={'steps': [1, {'label': name}],
                                  'opaque_provenance': {'path': '<BUILD>/old-input',
                                                        'sha256': '0' * 64}})
            ref = self.put(name + '.json', value)
            self.refs[name] = ref
            self.payloads[name] = value
            self.specs[name] = q.ReceiptSpec(
                ref, 1, 'authored-receipt', self.old_contract if old else self.contract,
                producer, claims={'packet_count': 1})
            previous = name
        admissions = {
            name: {'receipt': self.refs[name], 'contract': self.old_contract_ref,
                   'producer': self.old_producer} for name in self.carried_names}
        inputs = {self.contract_ref['path']: self.contract_ref['sha256'],
                  self.producer['path']: self.producer['sha256'],
                  self.old_contract_ref['path']: self.old_contract_ref['sha256'],
                  self.old_producer['path']: self.old_producer['sha256']}
        inputs.update({self.refs[name]['path']: self.refs[name]['sha256']
                       for name in self.carried_names})
        self.review_payload = dict(schema=1, kind='authored-carry-review', passed=True,
                                   contract=self.contract_ref, producer=self.producer,
                                   input_bindings=inputs, admissions=admissions)
        self.review_ref = self.put('carry-review.json', self.review_payload)
        self.review = q.ReceiptSpec(self.review_ref, 1, 'authored-carry-review',
                                    self.contract, self.producer)
        self.new = {name: self.specs[name] for name in self.new_names}
        self.carried = {name: q.CarriedAdmission(self.specs[name], self.review)
                        for name in self.carried_names}

    def put(self, name, value):
        path = (self.root / name).absolute()
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return {'path': str(path), 'sha256': digest(path)}

    def ledger(self, *, new=None, carried=None, roles=None):
        self.store = SnapshotStore()
        self.graph = q.EvidenceGraph(self.store)
        return q.AdmissionLedger(
            self.graph, current_contract=self.contract, producer=self.producer,
            roles=self.roles if roles is None else roles,
            new=self.new if new is None else new,
            carried=self.carried if carried is None else carried)

    def replace_current(self, name, **changes):
        """A self-consistent changed file/ref, so schema checks must do the work."""
        value = copy.deepcopy(self.payloads[name])
        value.update(changes)
        ref = self.put(name + '-changed.json', value)
        return q.ReceiptSpec(ref, 1, 'authored-receipt', self.contract,
                             self.producer, claims={'packet_count': 1})

    def replace_carried(self, name, variant):
        value = copy.deepcopy(self.payloads[name])
        contract, producer = self.old_contract, self.old_producer
        review = copy.deepcopy(self.review_payload)
        if variant == 'false-receipt':
            value['passed'] = False
        elif variant == 'changed-producer':
            value['producer'] = producer = self.producer
        elif variant == 'changed-contract':
            value['contract'] = self.contract_ref
            contract = self.contract
        ref = self.put(name + '-changed.json', value)
        spec = q.ReceiptSpec(ref, 1, 'authored-receipt', contract, producer,
                             claims={'packet_count': 1})
        # Make replacement byte references self-consistent. The independent
        # review's original contract/producer policy must still be enforced.
        review['admissions'][name]['receipt'] = ref
        review['input_bindings'].pop(self.refs[name]['path'])
        review['input_bindings'][ref['path']] = ref['sha256']
        if variant == 'false-review':
            review['passed'] = False
        elif variant == 'missing-approval':
            review['admissions'].pop(name)
        elif variant == 'missing-producer-pin':
            review['input_bindings'].pop(self.old_producer['path'])
        elif variant == 'altered-producer-approval':
            review['admissions'][name]['producer'] = self.producer
        review_ref = self.put('changed-carry-review.json', review)
        review_spec = q.ReceiptSpec(review_ref, 1, 'authored-carry-review',
                                    self.contract, self.producer)
        return q.CarriedAdmission(spec, review_spec)


class EvidenceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def fixture(self):
        return AuthoredPlan(self.root)

    def test_actual_parent_and_whole_seal_accept_five_carried_fourteen_new(self):
        f = self.fixture()
        ledger = f.ledger()
        for name in f.roles:
            admitted = ledger.parent(name)
            self.assertEqual(admitted.value['role'], name)
            self.assertEqual(admitted.value['contract'],
                             f.old_contract_ref if name in f.carried_names else f.contract_ref)
        output = self.root / 'sealed.json'
        result = ledger.seal(output, schema=1, kind='authored-index',
                             scope='Authored declaration consistency only')
        self.assertEqual(result.sha256, digest(output))
        value = json.loads(output.read_bytes())
        self.assertIs(value['evidence_consistent'], True)
        self.assertIs(value['qualification'], False)
        self.assertNotIn('passed', value)
        self.assertNotIn('native_qualified', value)
        self.assertNotIn('<BUILD>/old-input', f.store.bindings())
        self.assertEqual(set(value['admissions']), set(f.roles))
        for name in f.roles:
            record = value['admissions'][name]
            self.assertEqual(record['carried'], name in f.carried_names)
            self.assertEqual(record['producer'],
                             f.old_producer if name in f.carried_names else f.producer)

    def test_actual_parent_and_whole_seal_both_refuse_false_current_receipt(self):
        f = self.fixture()
        changed = dict(f.new, stage_00=f.replace_current('stage_00', passed=False))
        for action in ('parent', 'seal'):
            with self.subTest(action=action):
                ledger = f.ledger(new=changed)
                with self.assertRaises(ValueError):
                    if action == 'parent':
                        ledger.parent('stage_00')
                    else:
                        ledger.seal(self.root / 'false-index.json', schema=1,
                                    kind='authored-index', scope='Must refuse')
                self.assertFalse((self.root / 'false-index.json').exists())

    def test_self_consistent_unknown_role_or_contract_is_refused_at_real_callers(self):
        f = self.fixture()
        foreign = f.put('foreign-contract.json', {'schema': 1, 'kind': 'authored-contract'})
        for change in ({'role': 'undeclared'}, {'contract': foreign}):
            changed = dict(f.new, stage_00=f.replace_current('stage_00', **change))
            for action in ('parent', 'seal'):
                with self.subTest(change=change, action=action):
                    ledger = f.ledger(new=changed)
                    with self.assertRaises(ValueError):
                        if action == 'parent':
                            ledger.parent('stage_00')
                        else:
                            ledger.seal(self.root / 'invalid.json', schema=1,
                                        kind='authored-index', scope='Must refuse')
                    self.assertFalse((self.root / 'invalid.json').exists())

    def test_passed_schema_and_exact_claim_types_are_not_numeric_aliases(self):
        f = self.fixture()
        for changes in ({'passed': 1}, {'passed': 1.0}, {'schema': True},
                        {'schema': 1.0}, {'packet_count': True}, {'packet_count': 1.0}):
            with self.subTest(changes=changes):
                changed = dict(f.new, stage_00=f.replace_current('stage_00', **changes))
                with self.assertRaises(ValueError):
                    f.ledger(new=changed).parent('stage_00')

    def test_old_contract_producer_and_review_cannot_be_silently_relabelled(self):
        f = self.fixture()
        for variant in ('false-receipt', 'changed-producer', 'changed-contract',
                        'false-review', 'missing-approval', 'missing-producer-pin',
                        'altered-producer-approval'):
            for action in ('parent', 'seal'):
                with self.subTest(variant=variant, action=action):
                    carried = dict(f.carried,
                                   initial=f.replace_carried('initial', variant))
                    ledger = f.ledger(carried=carried)
                    with self.assertRaises(ValueError):
                        if action == 'parent':
                            ledger.parent('initial')
                        else:
                            ledger.seal(self.root / 'bad-carry.json', schema=1,
                                        kind='authored-index', scope='Must refuse')
                    self.assertFalse((self.root / 'bad-carry.json').exists())

    def test_self_consistent_new_spec_must_match_current_context_and_producer(self):
        f = self.fixture()
        for variant in ('old-producer', 'old-contract'):
            value = copy.deepcopy(f.payloads['stage_00'])
            producer, contract = f.producer, f.contract
            if variant == 'old-producer':
                value['producer'] = producer = f.old_producer
            else:
                value['contract'] = f.old_contract_ref
                contract = f.old_contract
            ref = f.put('wrong-new-context.json', value)
            changed = dict(f.new, stage_00=q.ReceiptSpec(
                ref, 1, 'authored-receipt', contract, producer))
            for action in ('parent', 'seal'):
                with self.subTest(variant=variant, action=action):
                    with self.assertRaises(ValueError):
                        ledger = f.ledger(new=changed)
                        if action == 'parent':
                            ledger.parent('stage_00')
                        else:
                            ledger.seal(self.root / 'wrong-new-context-index.json',
                                        schema=1, kind='authored-index', scope='Must refuse')

    def test_carried_contract_document_claims_are_checked_by_both_callers(self):
        f = self.fixture()
        forbidden_contract = q.DocumentSpec(
            f.old_contract_ref, 1, 'authored-contract', claims={'policy': 'unapproved'})
        altered = q.ReceiptSpec(f.refs['initial'], 1, 'authored-receipt',
                                forbidden_contract, f.old_producer)
        carried = dict(f.carried, initial=q.CarriedAdmission(altered, f.review))
        for action in ('parent', 'seal'):
            with self.subTest(action=action):
                ledger = f.ledger(carried=carried)
                with self.assertRaises(ValueError):
                    if action == 'parent':
                        ledger.parent('initial')
                    else:
                        ledger.seal(self.root / 'bad-document-claims.json', schema=1,
                                    kind='authored-index', scope='Must refuse document claim')
                self.assertFalse((self.root / 'bad-document-claims.json').exists())

    def test_returned_payload_and_constructor_mappings_do_not_change_admitted_plan(self):
        f = self.fixture()
        supplied_new = dict(f.new)
        supplied_carried = dict(f.carried)
        supplied_roles = list(f.roles)
        ledger = f.ledger(new=supplied_new, carried=supplied_carried, roles=supplied_roles)
        original = ledger.parent('initial').value
        changed = ledger.parent('initial').value
        changed['contract']['sha256'] = '0' * 64
        changed['payload']['steps'][1]['label'] = 'mutated caller copy'
        supplied_new.clear()
        supplied_carried.clear()
        supplied_roles[:] = ['undeclared']
        self.assertEqual(ledger.parent('initial').value, original)
        ledger.seal(self.root / 'detached-plan.json', schema=1,
                    kind='authored-index', scope='Original detached plan')

    def test_complete_universe_duplicate_missing_unknown_and_overlap_refuse(self):
        for variant in ('duplicate', 'missing', 'unknown', 'overlap'):
            with self.subTest(variant=variant):
                f = self.fixture()
                roles = list(f.roles)
                new = dict(f.new)
                carried = dict(f.carried)
                if variant == 'duplicate':
                    roles.append(roles[0])
                elif variant == 'missing':
                    new.pop('stage_13')
                elif variant == 'unknown':
                    new['undeclared'] = new['stage_13']
                else:
                    new['initial'] = f.specs['initial']
                with self.assertRaises(ValueError):
                    f.ledger(new=new, carried=carried, roles=roles)

    def test_unknown_parent_cannot_expand_the_declared_epoch(self):
        f = self.fixture()
        ledger = f.ledger()
        before = f.store.bindings()
        with self.assertRaises(ValueError):
            ledger.parent('undeclared')
        self.assertEqual(f.store.bindings(), before)

    def test_final_seal_revalidates_binary_dependency_after_parent_admission(self):
        f = self.fixture()
        ledger = f.ledger()
        ledger.parent('stage_00')
        info = f.binary.stat()
        old = f.binary.read_bytes()
        new = old.replace(b'alpha', b'omega')
        self.assertEqual(len(old), len(new))
        f.binary.write_bytes(new)
        os.utime(f.binary, ns=(info.st_atime_ns, info.st_mtime_ns))
        self.assertEqual(f.binary.stat().st_mtime_ns, info.st_mtime_ns)
        with self.assertRaises(ValueError):
            ledger.seal(self.root / 'drift.json', schema=1,
                        kind='authored-index', scope='Must detect current bytes')
        self.assertFalse((self.root / 'drift.json').exists())

    def test_all_nineteen_parent_lookups_read_shared_binary_once_per_epoch(self):
        f = self.fixture()
        ledger = f.ledger()
        with patch.object(snapshots, '_read', wraps=snapshots._read) as reads:
            for name in f.roles:
                ledger.parent(name)
        calls = [call for call in reads.call_args_list
                 if call.args[0] == f.binary and call.kwargs['retain'] is False]
        self.assertEqual(len(calls), 1)

    def test_receipt_json_drift_refuses_immediately_without_full_boundary(self):
        f = self.fixture()
        ledger = f.ledger()
        ledger.parent('stage_00')
        path = Path(f.refs['stage_00']['path'])
        raw = path.read_bytes()
        changed = raw.replace(b'authored-receipt', b'authored-invalid')
        self.assertEqual(len(raw), len(changed))
        path.write_bytes(changed)
        with self.assertRaises(ValueError):
            ledger.parent('stage_00')

    def test_trusted_action_boundary_checks_before_body_and_after_exceptions(self):
        f = self.fixture()
        ledger = f.ledger()
        ledger.parent('stage_00')
        entered = []
        with self.assertRaises(SnapshotError) as caught:
            with ledger.graph.boundary():
                entered.append(True)
                f.binary.write_bytes(b'authored artifact omega\n')
                raise LookupError('authored action failed')
        self.assertIsInstance(caught.exception.__context__, LookupError)
        self.assertEqual(entered, [True])
        with self.assertRaises(SnapshotError):
            with ledger.graph.boundary():
                entered.append(False)
        self.assertEqual(entered, [True])

    def test_trusted_action_exception_still_runs_postcheck_without_drift(self):
        f = self.fixture()
        ledger = f.ledger()
        ledger.parent('stage_00')
        with patch.object(f.store, 'revalidate', wraps=f.store.revalidate) as validate:
            with self.assertRaisesRegex(LookupError, 'authored action failed'):
                with ledger.graph.boundary():
                    raise LookupError('authored action failed')
        self.assertEqual(validate.call_count, 2)

    def test_failed_postwrite_publication_is_preserved_but_not_positive_admission(self):
        f = self.fixture()
        ledger = f.ledger()
        output = self.root / 'postwrite-failed.json'
        original = f.store.revalidate

        def drift_after_write():
            if output.exists():
                f.binary.write_bytes(b'authored artifact omega\n')
            return original()

        with patch.object(f.store, 'revalidate', side_effect=drift_after_write):
            with self.assertRaises(q.ReceiptEmissionError) as caught:
                ledger.seal(output, schema=1, kind='authored-index',
                            scope='Expected postwrite refusal')
        self.assertTrue(caught.exception.published)
        self.assertTrue(output.exists())
        value = json.loads(output.read_bytes())
        self.assertIs(value['qualification'], False)
        self.assertNotIn('passed', value)
        ref = {'path': str(output), 'sha256': digest(output)}
        spec = q.ReceiptSpec(ref, 1, 'authored-index', f.contract, f.producer)
        with self.assertRaises(ValueError):
            q.EvidenceGraph(SnapshotStore()).admit_receipt(spec)

    def test_existing_output_and_caller_execution_claims_never_become_generic_pass(self):
        f = self.fixture()
        ledger = f.ledger()
        existing = self.root / 'owner-authored.txt'
        existing.write_bytes(b'owner sentinel retained\n')
        with self.assertRaises(q.ReceiptEmissionError) as caught:
            ledger.seal(existing, schema=1, kind='authored-index', scope='Must not replace')
        self.assertFalse(caught.exception.published)
        self.assertEqual(existing.read_bytes(), b'owner sentinel retained\n')
        output = self.root / 'consistency.json'
        ledger.seal(output, schema=1, kind='authored-index', scope='Declared facts only',
                    details={'native_qualified': True, 'campaign_complete': True})
        value = json.loads(output.read_bytes())
        self.assertIs(value['qualification'], False)
        self.assertNotIn('passed', value)
        self.assertNotIn('native_qualified', {k: v for k, v in value.items() if k != 'details'})

    def test_json_snapshot_hashes_exact_parsed_bytes_and_detaches_nested_payload(self):
        path = self.root / 'input.json'
        raw = b'{ "value": [null, true, 1, 1.25, {"x":"authored"}] }\n'
        path.write_bytes(raw)
        store = SnapshotStore()
        snap = store.read_json(path)
        self.assertEqual(snap.sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(snap.raw, raw)
        value = snap.value
        value['value'][4]['x'] = 'changed'
        value['value'].append('extra')
        self.assertEqual(snap.value, {'value': [None, True, 1, 1.25, {'x': 'authored'}]})
        ref = snap.reference()
        ref['sha256'] = '0' * 64
        self.assertEqual(snap.reference()['sha256'], snap.sha256)
        bindings = store.bindings()
        bindings.clear()
        self.assertEqual(store.bindings(), {str(path): snap.sha256})

    def test_overlapping_binary_graphs_cache_epoch_but_explicit_freshness_detects_drift(self):
        path = self.root / 'artifact.bin'
        path.write_bytes(b'authored artifact alpha')
        store = SnapshotStore()
        admitted = store.bind(path)
        path.write_bytes(b'authored artifact omega')
        self.assertEqual(store.bind(path).sha256, admitted.sha256)
        store.bind_all({str(path): admitted.sha256})
        with self.assertRaises(SnapshotError):
            store.revalidate()
        self.assertEqual(store.bindings(), {str(path): admitted.sha256})

    def test_invalid_json_does_not_register_an_epoch(self):
        path = self.root / 'invalid.json'
        for raw in (b'{"a":1,"\\u0061":2}', b'{"x":[NaN]}',
                    b'{"x":{"n":Infinity}}', b'{"x":-Infinity}',
                    b'{"x":1e9999}', b'{"x":"\xff"}',
                    '{"x":1}'.encode('utf-16'), b'\xef\xbb\xbf{"x":1}'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                store = SnapshotStore()
                with self.assertRaises(SnapshotError):
                    store.read_json(path)
                self.assertEqual(store.bindings(), {})

    def test_parse_and_hash_share_one_snapshot_when_file_changes_during_parse(self):
        path = self.root / 'one-read.json'
        original = b'{"value":"alpha"}'
        path.write_bytes(original)
        parse = json.loads

        def mutate_after_parse(*args, **kwargs):
            value = parse(*args, **kwargs)
            path.write_bytes(b'{"value":"omega"}')
            return value

        store = SnapshotStore()
        with patch.object(json, 'loads', side_effect=mutate_after_parse):
            snap = store.read_json(path)
        self.assertEqual(snap.value, {'value': 'alpha'})
        self.assertEqual(snap.raw, original)
        self.assertEqual(snap.sha256, hashlib.sha256(original).hexdigest())
        with self.assertRaises(SnapshotError):
            store.revalidate()


if __name__ == '__main__':
    unittest.main()
