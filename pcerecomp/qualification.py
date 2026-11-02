"""Explicit evidence admission, not execution or game qualification.

Consumers supply exact document schemas, contract kinds, producer references
and optional claim expectations. References establish bytes, not producer
authorship. Only ``input_bindings`` is an admitted dependency table; arbitrary
payload strings, archives and nested JSON are never followed automatically.

The receipt envelope below is explicit. It does not reinterpret older consumer
formats. Native/campaign/hardware validation belongs in separately reviewed
consumer code; no validators, source loaders or callbacks are executed here.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import re

from .snapshots import FileSnapshot, JsonSnapshot, SnapshotStore


class QualificationError(ValueError):
    """An explicit evidence envelope, claim or admission plan disagrees."""


class ReceiptEmissionError(QualificationError):
    """Emission failed; a newly created artifact may remain, without admission."""

    def __init__(self, message, path, *, published):
        super().__init__(message)
        self.path = path
        self.published = published


def _require(ok, message):
    if not ok:
        raise QualificationError(message)


def _text(value, label):
    _require(type(value) is str and bool(value) and '\x00' not in value,
             label + ' must be a nonempty string')
    return value


def _schema(value):
    _require(type(value) is int and value >= 1, 'Schema must be a positive integer')
    return value


def _json_value(value):
    """Detach ordinary JSON values while retaining their exact numeric types."""
    if type(value) is dict:
        _require(all(type(k) is str for k in value), 'JSON object keys must be strings')
        return {k: _json_value(v) for k, v in value.items()}
    if type(value) is list:
        return [_json_value(v) for v in value]
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise QualificationError('Expected ordinary JSON values with finite numbers')


def _canonical(value):
    try:
        detached = _json_value(value)
        return json.dumps(detached, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (RecursionError, TypeError, ValueError, UnicodeError) as error:
        raise QualificationError('Invalid evidence JSON values') from error


def _exact(a, b):
    # Parsing/serialization retain their explicit supported-depth boundary;
    # comparison must not add another recursion limit to an admitted value.
    pending = [(a, b)]
    while pending:
        left, right = pending.pop()
        if type(left) is not type(right):
            return False
        if type(left) is dict:
            if left.keys() != right.keys():
                return False
            pending.extend((left[key], right[key]) for key in left)
        elif type(left) is list:
            if len(left) != len(right):
                return False
            pending.extend(zip(left, right))
        elif left != right:
            return False
    return True


@dataclass(frozen=True, slots=True)
class _Reference:
    path: str
    sha256: str

    @classmethod
    def from_value(cls, value):
        _require(isinstance(value, Mapping) and set(value) == {'path', 'sha256'},
                 'Reference must contain exactly path and sha256')
        path, digest = value['path'], value['sha256']
        _text(path, 'Reference path')
        _require(Path(path).is_absolute(), 'Serialized reference path must be absolute')
        _require(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest) is not None,
                 'Reference requires a lowercase SHA256')
        return cls(os.path.abspath(path), digest)

    def value(self):
        return {'path': self.path, 'sha256': self.sha256}


def _claims(value):
    if value is None:
        value = {}
    _require(type(value) is dict, 'Claim expectations must be a JSON object')
    return _canonical(value)


@dataclass(frozen=True, slots=True, init=False)
class DocumentSpec:
    """Exact document identity and consumer-declared metadata expectations.

    After schema/kind/claims pass, an optional top-level ``input_bindings``
    object admits that explicit common dependency map. Other nested reference
    strings/tables are opaque; existing consumer formats are not guessed.
    """

    _reference: _Reference
    schema: int
    kind: str
    _claims: bytes = field(repr=False)

    def __init__(self, reference, schema, kind, claims=None):
        object.__setattr__(self, '_reference', _Reference.from_value(reference))
        object.__setattr__(self, 'schema', _schema(schema))
        object.__setattr__(self, 'kind', _text(kind, 'Document kind'))
        encoded = _claims(claims)
        _require(not {'schema', 'kind'} & json.loads(encoded).keys(),
                 'Claims cannot replace document schema or kind')
        object.__setattr__(self, '_claims', encoded)

    @property
    def reference(self):
        return self._reference.value()

    @property
    def claims(self):
        return json.loads(self._claims)


@dataclass(frozen=True, slots=True, init=False)
class ReceiptSpec:
    """A positive consumer receipt, without inferring what its pass proves.

    Envelope fields are ``schema``, ``kind``, ``passed``, ``contract``,
    ``producer`` and ``input_bindings``. Ledger receipts additionally have a
    ``role``. Producer is an exact file reference whose meaning is the caller's
    responsibility, not an automatically authenticated SDK identity.
    """

    _reference: _Reference
    schema: int
    kind: str
    contract: DocumentSpec
    _producer: _Reference
    _claims: bytes = field(repr=False)

    def __init__(self, reference, schema, kind, contract, producer, claims=None):
        _require(type(contract) is DocumentSpec, 'Receipt requires an explicit DocumentSpec')
        object.__setattr__(self, '_reference', _Reference.from_value(reference))
        object.__setattr__(self, 'schema', _schema(schema))
        object.__setattr__(self, 'kind', _text(kind, 'Receipt kind'))
        object.__setattr__(self, 'contract', contract)
        object.__setattr__(self, '_producer', _Reference.from_value(producer))
        encoded = _claims(claims)
        _require(not {'schema', 'kind', 'passed', 'contract', 'producer',
                      'input_bindings'} & json.loads(encoded).keys(),
                 'Claims cannot replace mandatory receipt fields')
        object.__setattr__(self, '_claims', encoded)

    @property
    def reference(self):
        return self._reference.value()

    @property
    def producer(self):
        return self._producer.value()

    @property
    def claims(self):
        return json.loads(self._claims)


@dataclass(frozen=True, slots=True)
class CarriedAdmission:
    """An unchanged prior receipt plus an explicitly linked positive review."""

    receipt: ReceiptSpec
    review: ReceiptSpec

    def __post_init__(self):
        _require(type(self.receipt) is ReceiptSpec and type(self.review) is ReceiptSpec,
                 'Carried admission requires original and review ReceiptSpecs')


@dataclass(frozen=True, slots=True)
class ReceiptAdmission:
    _snapshot: JsonSnapshot = field(repr=False)
    spec: ReceiptSpec

    @property
    def reference(self):
        return self._snapshot.reference()

    @property
    def value(self):
        return self._snapshot.value


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    """Immutable admitted bindings; ``to_dict`` returns detached JSON data."""

    bindings: tuple[tuple[str, str], ...]
    receipts: tuple[ReceiptAdmission, ...]

    def to_dict(self):
        return {'input_bindings': dict(self.bindings),
                'receipts': [r.reference for r in self.receipts],
                'evidence_consistent': True, 'qualification': False}


class EvidenceGraph:
    """Explicit parse-once content admission using one SnapshotStore epoch."""

    def __init__(self, store: SnapshotStore):
        _require(isinstance(store, SnapshotStore), 'EvidenceGraph requires SnapshotStore')
        self._store = store
        self._receipts = {}

    @property
    def store(self):
        return self._store

    def _document(self, spec):
        _require(type(spec) is DocumentSpec, 'Expected DocumentSpec')
        snap = self.store.read_json(spec._reference.path,
                                    expected_sha256=spec._reference.sha256)
        value = snap.value
        _require(type(value) is dict and type(value.get('schema')) is int
                 and value['schema'] == spec.schema and value.get('kind') == spec.kind,
                 'Document schema or kind disagrees with its specification')
        for key, expected in spec.claims.items():
            _require(key in value and _exact(value[key], expected),
                     'Document claim disagrees: ' + key)
        if 'input_bindings' in value:
            _require(type(value['input_bindings']) is dict,
                     'Document input_bindings must be an explicit object')
            self.store.bind_all(value['input_bindings'])
        return snap

    def admit_document(self, spec):
        """Check current JSON and refs; use boundary/snapshot for graph freshness."""
        return self._document(spec)

    def _receipt(self, spec, role=None):
        _require(type(spec) is ReceiptSpec, 'Expected ReceiptSpec')
        self._document(spec.contract)
        self.store.bind(spec._producer.path, expected_sha256=spec._producer.sha256)
        snap = self.store.read_json(spec._reference.path,
                                    expected_sha256=spec._reference.sha256)
        value = snap.value
        _require(type(value) is dict and type(value.get('schema')) is int
                 and value['schema'] == spec.schema and value.get('kind') == spec.kind,
                 'Receipt schema or kind disagrees with its specification')
        _require(value.get('passed') is True, 'Receipt must explicitly have passed:true')
        _require(_Reference.from_value(value.get('contract')) == spec.contract._reference,
                 'Receipt contract reference disagrees')
        _require(_Reference.from_value(value.get('producer')) == spec._producer,
                 'Receipt producer reference disagrees')
        if role is not None:
            _text(role, 'Role')
            _require(type(value.get('role')) is str and value['role'] == role,
                     'Receipt role disagrees with the named admission')
        for key, expected in spec.claims.items():
            _require(key in value and _exact(value[key], expected),
                     'Receipt claim disagrees: ' + key)
        _require(type(value.get('input_bindings')) is dict,
                 'Receipt requires an explicit input_bindings table')
        self.store.bind_all(value['input_bindings'])
        admitted = ReceiptAdmission(snap, spec)
        self._receipts[spec] = admitted
        return admitted

    def admit_receipt(self, spec, *, role=None):
        """Check JSON/refs locally; cached binary pins are not a freshness claim."""
        return self._receipt(spec, role)

    @contextmanager
    def boundary(self):
        """Rehash every input before/after trusted caller work, even on error.

        This helper launches nothing. The caller owns its ordinary Python
        action; no action, callback or SDK path is taken from JSON. This is a
        content check at two boundaries, not a lock on concurrent writers.
        """
        self.store.revalidate()
        try:
            yield self
        finally:
            self.store.revalidate()

    def _view(self):
        return EvidenceSnapshot(tuple(self.store.bindings().items()),
                                tuple(self._receipts.values()))

    def snapshot(self):
        self.store.revalidate()
        return self._view()


class AdmissionLedger:
    """Resolve and seal one exact disjoint named current/prior admission plan.

    A carried review must have ``admissions[name]`` equal to the original
    ``{receipt, contract, producer}`` references and pin all three paths in its
    ``input_bindings``. This checks explicit approval linkage, not the review's
    gameplay semantics. Parent lookup and sealing share the same resolver.
    """

    def __init__(self, graph, *, current_contract, producer, roles, new, carried):
        _require(type(graph) is EvidenceGraph, 'Ledger requires EvidenceGraph')
        _require(type(current_contract) is DocumentSpec, 'Expected current DocumentSpec')
        _require(not isinstance(roles, (str, bytes)), 'Roles must be an explicit sequence')
        self._graph = graph
        self._current_contract = current_contract
        self._producer = _Reference.from_value(producer)
        try:
            self._roles = tuple(_text(name, 'Role name') for name in roles)
        except TypeError as error:
            raise QualificationError('Roles must be an explicit sequence') from error
        _require(bool(self._roles) and len(set(self._roles)) == len(self._roles),
                 'Expected role universe must be nonempty and unique')
        _require(isinstance(new, Mapping) and isinstance(carried, Mapping),
                 'New and carried admissions must be explicit mappings')
        new_items, carried_items = dict(new), dict(carried)
        _require(all(type(k) is str for k in (*new_items, *carried_items)),
                 'Admission role keys must be strings')
        _require(not new_items.keys() & carried_items.keys(),
                 'New and carried role sets overlap')
        _require(set(new_items) | set(carried_items) == set(self._roles),
                 'New/carried roles must exactly cover the named universe')
        _require(all(type(s) is ReceiptSpec for s in new_items.values()),
                 'New roles require ReceiptSpecs')
        _require(all(type(s) is CarriedAdmission for s in carried_items.values()),
                 'Carried roles require CarriedAdmissions')
        self._plan = tuple((name, new_items.get(name), carried_items.get(name))
                           for name in self._roles)

    @property
    def graph(self):
        return self._graph

    @property
    def current_contract(self):
        return self._current_contract

    def _resolve_role(self, name):
        _text(name, 'Parent role')
        matches = [item for item in self._plan if item[0] == name]
        _require(bool(matches), 'Unknown admission role: ' + name)
        self.graph._document(self.current_contract)
        self.graph.store.bind(self._producer.path, expected_sha256=self._producer.sha256)
        _, new, carried = matches[0]
        if new is not None:
            _require(new.contract._reference == self.current_contract._reference
                     and new.contract.schema == self.current_contract.schema
                     and new.contract.kind == self.current_contract.kind,
                     'New role must retain the current contract context')
            _require(new._producer == self._producer,
                     'New role must retain the current producer')
            return self.graph._receipt(new, name), None
        admitted = self.graph._receipt(carried.receipt, name)
        review = self.graph._receipt(carried.review)
        expected = {'receipt': admitted.reference,
                    'contract': carried.receipt.contract.reference,
                    'producer': carried.receipt.producer}
        value = review.value
        _require(type(value.get('admissions')) is dict
                 and _exact(value['admissions'].get(name), expected),
                 'Carried review must explicitly pin the original role admission')
        for ref in expected.values():
            _require(value['input_bindings'].get(ref['path']) == ref['sha256'],
                     'Carried review must pin original receipt/contract/producer bytes')
        return admitted, review

    def parent(self, name):
        """Resolve exact named metadata; binary freshness needs a boundary.

        JSON is always reread. Shared producer/input binaries reuse their
        admitted epoch pins until boundary(), snapshot() or seal() revalidates
        all content. Many parent lookups therefore avoid repeated graph scans.
        """
        admitted, _ = self._resolve_role(name)
        return admitted

    def seal(self, output, *, schema, kind, scope, details=None):
        """Emit consistency-only JSON to a new file and return its byte binding.

        No top-level passed flag or execution qualification is produced. The
        file is a point-in-time declaration, not a lock or perpetual freshness
        guarantee. If writing/postwrite validation fails, a new artifact is
        preserved and ReceiptEmissionError is raised without returning an
        admission; that file cannot satisfy a positive ReceiptSpec.
        """
        _schema(schema)
        _text(kind, 'Closure kind')
        _text(scope, 'Closure scope')
        extra = json.loads(_canonical({} if details is None else details))
        admissions = {}
        for name in self._roles:
            receipt, review = self._resolve_role(name)
            admissions[name] = {'receipt': receipt.reference,
                                'contract': receipt.spec.contract.reference,
                                'producer': receipt.spec.producer,
                                'carried': review is not None}
            if review is not None:
                admissions[name]['review'] = review.reference
        snapshot = self.graph._view()
        payload = {'schema': schema, 'kind': kind, 'evidence_consistent': True,
                   'qualification': False, 'scope': scope, 'details': extra,
                   'contract': self.current_contract.reference,
                   'producer': self._producer.value(), 'admissions': admissions,
                   'roles': list(self._roles),
                   'input_bindings': dict(snapshot.bindings)}
        encoded = _canonical(payload) + b'\n'
        try:
            spelling = os.fspath(output)
            _text(spelling, 'Receipt output path')
            path = Path(os.path.abspath(spelling))
        except TypeError as error:
            raise QualificationError('Receipt output requires a text file path') from error
        _require(str(path) not in self.graph.store.bindings(),
                 'Receipt output cannot replace an admitted input')
        published = False
        try:
            # Revalidate again at the actual publication boundary, after all
            # resolver/serialization work; never delete or replace owner data.
            _require(self.graph.store.bindings() == dict(snapshot.bindings),
                     'Evidence graph changed while preparing its closure')
            self.graph.store.revalidate()
            with path.open('xb') as stream:
                published = True
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
                created = os.fstat(stream.fileno())
            self.graph.store.revalidate()
            _require(self.graph.store.bindings() == dict(snapshot.bindings),
                     'Evidence graph changed during publication')
            actual = path.stat()
            _require((actual.st_dev, actual.st_ino) == (created.st_dev, created.st_ino),
                     'New receipt path identity changed during publication')
            return self.graph.store.bind(path,
                expected_sha256=hashlib.sha256(encoded).hexdigest())
        except (OSError, ValueError) as error:
            raise ReceiptEmissionError(
                'Receipt emission failed; any newly created artifact is preserved '
                'and is not an admitted closure: ' + str(path), path,
                published=published) from error
