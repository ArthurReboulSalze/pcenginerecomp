"""Authored evidence envelopes; no SDK, game content or guest execution."""
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.qualification import (AdmissionLedger, CarriedAdmission,
    DocumentSpec, EvidenceGraph, QualificationError, ReceiptEmissionError,
    ReceiptSpec)
from pcerecomp.snapshots import SnapshotStore


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pce-qualification-')
        self.root = Path(self.temp.name).resolve()
        self.temporary_parent = Path(tempfile.gettempdir()).resolve()
        self.assertTrue(self.root.is_relative_to(self.temporary_parent))
        self.addCleanup(self.cleanup)
        self.producer = self.binary('producer.txt', b'authored producer declaration')
        self.dependency = self.binary('payload.bin', b'authored binary input')
        self.current = self.document('current.json', 'authored-current')
        self.old = self.document('old.json', 'authored-prior')

    def cleanup(self):
        self.assertEqual(Path(self.temp.name).resolve(), self.root)
        self.assertTrue(self.root.is_relative_to(self.temporary_parent))
        self.temp.cleanup()

    def reference(self, path):
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def binary(self, name, data):
        path = self.root/name
        path.write_bytes(data)
        return self.reference(path)

    def write(self, name, value):
        path = self.root/name
        path.write_text(json.dumps(value), encoding='utf-8')
        return self.reference(path)

    def document(self, name, kind):
        return DocumentSpec(self.write(name, {'schema': 1, 'kind': kind}), 1, kind)

    def receipt(self, name='new', contract=None, **changes):
        contract = contract or self.current
        value = {'schema': 1, 'kind': 'authored-role', 'passed': True,
                 'role': name, 'contract': contract.reference,
                 'producer': self.producer,
                 'input_bindings': {self.dependency['path']: self.dependency['sha256']},
                 'checkpoint': {'frame': 17, 'mapping': [3, 5]},
                 'opaque': {'path': '<BUILD>/not-an-input', 'sha256': 'metadata only'}}
        value.update(changes)
        reference = self.write(name + '.json', value)
        return ReceiptSpec(reference, 1, 'authored-role', contract, self.producer)

    def graph(self):
        return EvidenceGraph(SnapshotStore())

    def ledger(self, graph=None, spec=None):
        return AdmissionLedger(graph or self.graph(), current_contract=self.current,
            producer=self.producer, roles=['new'],
            new={'new': spec or self.receipt()}, carried={})

    def test_specs_detach_references_claims_and_admission_payload(self):
        spec = self.receipt()
        reference, producer = spec.reference, spec.producer
        claims = {'checkpoint': {'frame': 17, 'mapping': [3, 5]}}
        pinned = ReceiptSpec(reference, 1, 'authored-role', self.current, producer, claims)
        reference['sha256'] = '0'*64
        producer['path'] = '<changed>'
        claims['checkpoint']['mapping'][0] = 99
        pinned.claims['checkpoint']['frame'] = False
        admission = self.graph().admit_receipt(pinned, role='new')
        admission.value['checkpoint']['mapping'].clear()
        self.assertEqual(admission.value['checkpoint'], {'frame': 17, 'mapping': [3, 5]})
        with self.assertRaises(FrozenInstanceError):
            pinned.schema = 2

    def test_claims_are_type_sensitive_and_reserved_fields_refuse(self):
        spec = self.receipt()
        for expected in (True, 17.0):
            pinned = ReceiptSpec(spec.reference, 1, spec.kind, self.current,
                                 self.producer, {'checkpoint': {'frame': expected,
                                                               'mapping': [3, 5]}})
            with self.assertRaisesRegex(QualificationError, 'claim'):
                self.graph().admit_receipt(pinned)
        for key in ('schema', 'kind', 'passed', 'contract', 'producer', 'input_bindings'):
            with self.assertRaises(QualificationError):
                ReceiptSpec(spec.reference, 1, spec.kind, self.current,
                            self.producer, {key: None})

    def test_document_claims_are_detached_and_strict(self):
        reference = self.write('claim-contract.json',
            {'schema': 1, 'kind': 'declared', 'identity': {'epoch': 9}})
        claims = {'identity': {'epoch': 9}}
        document = DocumentSpec(reference, 1, 'declared', claims)
        claims['identity']['epoch'] = 11
        self.graph().admit_document(document)
        bad = DocumentSpec(reference, 1, 'declared', {'identity': {'epoch': 9.0}})
        with self.assertRaises(QualificationError):
            self.graph().admit_document(bad)

    def test_deep_claims_do_not_leak_a_bare_recursion_error(self):
        nested = 7
        for _ in range(500):
            nested = {'child': nested}
        reference = self.write('deep-contract.json',
            {'schema': 1, 'kind': 'deep', 'identity': nested})
        try:
            document = DocumentSpec(reference, 1, 'deep', {'identity': nested})
            admitted = self.graph().admit_document(document)
            self.assertEqual(admitted.reference(), reference)
        except ValueError:
            # Parser/serializer depth limits vary by supported Python runtime;
            # an explicit boundary refusal is permitted, an uncaught recursion
            # failure after successful parsing is not.
            pass

    def test_schema_and_pass_are_not_numeric_aliases(self):
        for schema in (True, 1.0, 0):
            with self.assertRaises(QualificationError):
                DocumentSpec(self.current.reference, schema, self.current.kind)
        for value in (False, 1, 1.0, None):
            spec = self.receipt('failed-' + str(value), passed=value)
            with self.assertRaisesRegex(QualificationError, 'passed'):
                self.graph().admit_receipt(spec)
        spec = self.receipt('float-schema', schema=1.0)
        with self.assertRaisesRegex(QualificationError, 'schema'):
            self.graph().admit_receipt(spec)

    def test_only_explicit_dependency_map_is_followed(self):
        spec = self.receipt()
        graph = self.graph()
        graph.admit_receipt(spec)
        bindings = graph.snapshot().to_dict()['input_bindings']
        self.assertIn(self.dependency['path'], bindings)
        self.assertFalse(any('<BUILD>' in path for path in bindings))
        self.assertEqual(len(bindings), 4)  # contract, producer, receipt, explicit binary

    def test_nineteen_roles_share_one_explicit_contract_binary_read(self):
        contract_ref = self.write('common.json', {'schema': 1, 'kind': 'common',
            'input_bindings': {self.dependency['path']: self.dependency['sha256']},
            'opaque': {'path': '<BUILD>/unopened', 'sha256': 'provenance only'}})
        contract = DocumentSpec(contract_ref, 1, 'common')
        names = [f'role-{i:02d}' for i in range(19)]
        specs = {name: self.receipt(name, contract, input_bindings={}) for name in names}
        ledger = AdmissionLedger(self.graph(), current_contract=contract,
            producer=self.producer, roles=names, new=specs, carried={})
        real_open = Path.open
        binary_reads = []

        def count_open(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get('mode', 'r')
            if str(path) == self.dependency['path'] and mode == 'rb':
                binary_reads.append(True)
            return real_open(path, *args, **kwargs)

        with patch.object(Path, 'open', count_open):
            for name in names:
                self.assertEqual(ledger.parent(name).value['input_bindings'], {})
            self.assertEqual(len(binary_reads), 1)
            source = Path(self.dependency['path'])
            before = source.stat()
            source.write_bytes(b'changed! binary input')
            os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
            ledger.parent(names[-1])  # metadata is local; binary freshness is explicit
            self.assertEqual(len(binary_reads), 1)
            with self.assertRaises(ValueError):
                with ledger.graph.boundary():
                    self.fail('A changed common dependency cannot enter trusted work')
            with self.assertRaises(ValueError):
                ledger.seal(self.root/'refused.json', schema=1,
                            kind='closed', scope='Shared input fixture')
        self.assertFalse((self.root/'refused.json').exists())

    def test_contract_dependency_table_is_explicit_and_strict(self):
        for value in (False, None, [], 'not a table'):
            reference = self.write('bad-contract.json',
                {'schema': 1, 'kind': 'common', 'input_bindings': value})
            with self.assertRaisesRegex(QualificationError, 'input_bindings'):
                self.graph().admit_document(DocumentSpec(reference, 1, 'common'))
        no_receipt_map = self.receipt('missing-map')
        path = Path(no_receipt_map.reference['path'])
        value = json.loads(path.read_bytes())
        del value['input_bindings']
        reference = self.write(path.name, value)
        spec = ReceiptSpec(reference, 1, no_receipt_map.kind,
                           self.current, self.producer)
        with self.assertRaisesRegex(QualificationError, 'input_bindings'):
            self.graph().admit_receipt(spec)

    def test_plan_freezes_callers_and_rejects_unknown_missing_or_overlap(self):
        spec = self.receipt()
        roles, new, carried = ['new'], {'new': spec}, {}
        ledger = AdmissionLedger(self.graph(), current_contract=self.current,
            producer=self.producer, roles=roles, new=new, carried=carried)
        roles.append('extra')
        new.clear()
        carried['new'] = None
        self.assertEqual(ledger.parent('new').value['role'], 'new')
        with self.assertRaisesRegex(QualificationError, 'Unknown'):
            ledger.parent('extra')
        for names, fresh, prior in [(['new', 'new'], {'new': spec}, {}),
                                    (['new', 'missing'], {'new': spec}, {}),
                                    (['new'], {'new': spec, 'extra': spec}, {}),
                                    (['new'], {'new': spec}, {'new': None})]:
            with self.assertRaises(QualificationError):
                AdmissionLedger(self.graph(), current_contract=self.current,
                    producer=self.producer, roles=names, new=fresh, carried=prior)

    def test_carried_parent_and_seal_retain_exact_old_contract(self):
        prior = self.receipt('retained', self.old)
        target = {'receipt': prior.reference, 'contract': self.old.reference,
                  'producer': self.producer}
        review_value = {'schema': 1, 'kind': 'authored-review', 'passed': True,
            'contract': self.current.reference, 'producer': self.producer,
            'admissions': {'retained': target},
            'input_bindings': {ref['path']: ref['sha256'] for ref in target.values()}}
        review_ref = self.write('review.json', review_value)
        review = ReceiptSpec(review_ref, 1, 'authored-review', self.current, self.producer)
        ledger = AdmissionLedger(self.graph(), current_contract=self.current,
            producer=self.producer, roles=['retained'], new={},
            carried={'retained': CarriedAdmission(prior, review)})
        self.assertEqual(ledger.parent('retained').value['contract'], self.old.reference)
        emitted = ledger.seal(self.root/'closed.json', schema=1,
                              kind='authored-closure', scope='Declared evidence only')
        result = json.loads(emitted.path.read_bytes())
        self.assertEqual(result['admissions']['retained']['contract'], self.old.reference)
        self.assertEqual(result['admissions']['retained']['review'], review_ref)
        self.assertTrue(result['evidence_consistent'])
        self.assertIs(result['qualification'], False)
        self.assertNotIn('passed', result)

    def test_actual_json_drift_between_parent_and_seal_refuses_before_write(self):
        ledger = self.ledger()
        admission = ledger.parent('new')
        path = Path(admission.reference['path'])
        value = json.loads(path.read_bytes())
        value['passed'] = False
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(ValueError):
            ledger.seal(self.root/'refused.json', schema=1, kind='closed', scope='fixture')
        self.assertFalse((self.root/'refused.json').exists())

    def test_binary_pins_are_local_until_explicit_content_boundary(self):
        ledger = self.ledger()
        ledger.parent('new')
        path = Path(self.dependency['path'])
        before = path.stat()
        path.write_bytes(b'changed! binary input')
        self.assertEqual(path.stat().st_size, before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        # Parent JSON is current, but its binary dependency remains an epoch pin.
        ledger.parent('new')
        entered = []
        with self.assertRaises(ValueError):
            with ledger.graph.boundary():
                entered.append(True)
        self.assertEqual(entered, [])
        with self.assertRaises(ValueError):
            ledger.graph.snapshot()
        with self.assertRaises(ValueError):
            ledger.seal(self.root/'refused.json', schema=1, kind='closed', scope='fixture')
        self.assertFalse((self.root/'refused.json').exists())

    def test_snapshot_is_immutable_and_detached(self):
        graph = self.graph()
        graph.admit_receipt(self.receipt())
        snapshot = graph.snapshot()
        snapshot.to_dict()['input_bindings'].clear()
        self.assertEqual(len(snapshot.bindings), 4)
        with self.assertRaises(FrozenInstanceError):
            snapshot.bindings = ()

    def test_seal_has_two_content_boundaries_and_snapshot_has_one(self):
        ledger = self.ledger()
        ledger.parent('new')
        real_open = Path.open
        binary_reads = []

        def count_open(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get('mode', 'r')
            if str(path) == self.dependency['path'] and mode == 'rb':
                binary_reads.append(True)
            return real_open(path, *args, **kwargs)

        with patch.object(Path, 'open', count_open):
            ledger.seal(self.root/'closed.json', schema=1,
                        kind='closed', scope='Declared evidence only')
            self.assertEqual(len(binary_reads), 2)
            ledger.graph.snapshot()
            self.assertEqual(len(binary_reads), 3)

    def test_exclusive_publication_preserves_existing_owner_bytes(self):
        ledger = self.ledger()
        target = self.root/'existing.json'
        target.write_bytes(b'authored owner data')
        with self.assertRaises(ReceiptEmissionError) as caught:
            ledger.seal(target, schema=1, kind='closed', scope='fixture')
        self.assertIs(caught.exception.published, False)
        self.assertEqual(target.read_bytes(), b'authored owner data')

    def test_postwrite_drift_preserves_failed_artifact_without_positive_admission(self):
        ledger = self.ledger()
        output = self.root/'preserved-failure.json'
        real_fsync = os.fsync

        def mutate_after_flush(fd):
            real_fsync(fd)
            Path(self.dependency['path']).write_bytes(b'changed! binary input')

        with patch('pcerecomp.qualification.os.fsync', side_effect=mutate_after_flush):
            with self.assertRaises(ReceiptEmissionError) as caught:
                ledger.seal(output, schema=1, kind='closed', scope='fixture')
        self.assertIs(caught.exception.published, True)
        self.assertTrue(output.exists())
        value = json.loads(output.read_bytes())
        self.assertNotIn('passed', value)
        self.assertIs(value['qualification'], False)
        failed = ReceiptSpec(self.reference(output), 1, 'closed',
                             self.current, self.producer)
        with self.assertRaisesRegex(QualificationError, 'passed'):
            self.graph().admit_receipt(failed)


if __name__ == '__main__':
    unittest.main()
