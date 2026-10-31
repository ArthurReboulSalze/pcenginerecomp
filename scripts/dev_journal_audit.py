"""Stream a private wire-journal snapshot; never replay or infer guest execution.

Raw responses precede client admission and schema 1 has no close marker. A
paired ledger is therefore not a successful client session/process receipt.
Visitor events are provisional until this function returns and verifies EOF,
file stability and the optional externally supplied SHA256.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from collections import Counter
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import stat
import sys
import zlib

try:
    from scripts.dev_client import MAX_REQUEST, MAX_RESPONSE, MAX_TOKEN, _finite_float
except ModuleNotFoundError:
    from dev_client import MAX_REQUEST, MAX_RESPONSE, MAX_TOKEN, _finite_float

# A protocol-sized base64 frame plus explicit schema-1 metadata. This bounds
# one record, not total journal size. Custom WireJournal.record payloads beyond
# this reader profile are unsupported and refused, never truncated silently.
MAX_METADATA = 65536
MAX_LINE = 4 * ((MAX_RESPONSE + 2) // 3) + MAX_METADATA
KNOWN_COMMANDS = frozenset(('ping', 'status', 'pause', 'resume', 'quit', 'clear_input',
                            'set_input', 'step_frames', 'screenshot', 'read_memory',
                            'write_memory', 'save_checkpoint', 'load_checkpoint',
                            'capture_summary', 'capture_sources'))


class JournalValidationError(ValueError):
    """The snapshot does not establish this declared journal relation."""


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    event: str
    request_id: int | None = None
    command: str | None = None
    wire: bytes = b''
    partial: bytes = b''
    protocol_error: str | None = None
    phase: str | None = None
    error_type: str | None = None
    error: str | None = None


def _require(value, message):
    if not value:
        raise JournalValidationError(message)


def _integer(value, low, high, name):
    _require(type(value) is int and low <= value <= high, name + ': bounded integer required')
    return value


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names), 'unexpected journal fields')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON field')
        result[key] = value
    return result


def _constant(_):
    raise JournalValidationError('nonfinite JSON value')


def _json(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=_unique,
                      parse_constant=_constant, parse_float=_finite_float)


def _base64(value, maximum):
    _require(type(value) is str and len(value) <= 4 * ((maximum + 2) // 3),
             'base64 field exceeds its protocol bound')
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise JournalValidationError('invalid base64 field') from error
    _require(len(decoded) <= maximum and base64.b64encode(decoded).decode('ascii') == value,
             'noncanonical or oversized base64 field')
    return decoded


def _frame(data, maximum):
    _require(0 < len(data) <= maximum and data.endswith(b'\n') and data.count(b'\n') == 1,
             'wire frame must contain one final newline within its protocol bound')


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


class _GzipLines:
    """Bounded single-member decoder; gzip padding/concatenation are refused."""

    def __init__(self, raw):
        self.raw = raw
        self.decoder = zlib.decompressobj(31)
        self.pending = b''
        self.buffer = b''
        self.finished = False
        self.digest = hashlib.sha256()
        self.bytes = 0

    def _read(self, size):
        data = self.raw.read(size)
        self.digest.update(data)
        self.bytes += len(data)
        return data

    def _fill(self, size):
        while not self.buffer and not self.finished:
            data = self.pending or self._read(65536)
            _require(bool(data), 'truncated gzip stream')
            try:
                self.buffer = self.decoder.decompress(data, size)
            except zlib.error as error:
                raise JournalValidationError('invalid gzip stream') from error
            self.pending = self.decoder.unconsumed_tail
            if self.decoder.eof:
                _require(not self.decoder.unused_data and not self._read(1),
                         'gzip trailing bytes or concatenated members refused')
                self.finished = True

    def readline(self, size):
        pieces = []
        count = 0
        while count < size:
            self._fill(min(65536, size - count))
            if not self.buffer:
                break
            end = self.buffer.find(b'\n', 0, size - count)
            take = end + 1 if end >= 0 else min(len(self.buffer), size - count)
            pieces.append(self.buffer[:take])
            self.buffer = self.buffer[take:]
            count += take
            if end >= 0:
                break
        return b''.join(pieces)


def audit_wire_journal(path, *, expected_sha256=None, allow_incomplete=False, visit=None,
                       encoding='plain', expected_storage_sha256=None):
    """Return a small summary only after streaming and checking the entire file.

    ``allow_incomplete`` permits a forensic unpaired intent, an unterminated
    final outer record or an invalid protocol reply lacking its failure row.
    Malformed complete outer records and impossible event order still fail.
    ``visit`` receives immutable provisional events, one at a time. An exception,
    failed hash or file change invalidates the audit; discard callback results.
    No response proves client/helper admission, fsync success, clean shutdown,
    source identity or native execution. Those require independent evidence.
    """
    _require(type(allow_incomplete) is bool, 'allow_incomplete must be boolean')
    _require(type(encoding) is str and encoding in ('plain', 'gzip'),
             'encoding must be explicitly plain or gzip')
    _require(visit is None or callable(visit), 'visit must be callable or None')
    for name, value in (('expected_sha256', expected_sha256),
                        ('expected_storage_sha256', expected_storage_sha256)):
        if value is not None:
            _require(type(value) is str and len(value) == 64
                     and all(c in '0123456789abcdef' for c in value),
                     name + ' requires lowercase SHA256')
    path = Path(path)
    _require(stat.S_ISREG(path.stat().st_mode), 'journal snapshot must be a regular file')
    digest = hashlib.sha256()
    commands = Counter()
    other_commands = 0
    requests = responses = positive = rejected = invalid = failures = records = total = trailing = 0
    session = None
    pending = None
    recent = None
    terminal = False
    next_id = 1
    ending = 'session-only'
    tail_hash = None
    partial_bytes = 0
    with path.open('rb') as raw_stream:
        start = os.fstat(raw_stream.fileno())
        _require(stat.S_ISREG(start.st_mode), 'journal snapshot must be a regular file')
        stream = _GzipLines(raw_stream) if encoding == 'gzip' else raw_stream
        while True:
            raw = stream.readline(MAX_LINE + 1)
            if not raw:
                break
            _require(not terminal, 'bytes follow a terminal failure')
            total += len(raw)
            digest.update(raw)
            _require(len(raw) <= MAX_LINE, 'journal record exceeds reader profile')
            if not raw.endswith(b'\n'):
                _require(allow_incomplete, 'unterminated outer journal record')
                trailing = len(raw)
                tail_hash = hashlib.sha256(raw).hexdigest()
                ending = 'truncated-record'
                break
            try:
                row = _json(raw)
            except (ValueError, UnicodeError, RecursionError) as error:
                raise JournalValidationError('invalid complete outer journal record') from error
            _require(type(row) is dict and type(row.get('schema')) is int and row['schema'] == 1,
                     'journal schema 1 required')
            _require(type(row.get('sequence')) is int and row['sequence'] == records,
                     'journal sequence differs')
            kind = row.get('event')
            _require(type(kind) is str and kind in ('session', 'request', 'response', 'failure'),
                     'unsupported journal event')
            _require(not terminal, 'records follow a terminal failure')
            if records == 0:
                _fields(row, ('schema', 'sequence', 'event', 'host', 'port'))
                _require(kind == 'session' and type(row['host']) is str,
                         'first record must declare a loopback session')
                try:
                    _require(ipaddress.ip_address(row['host']).is_loopback, 'session is not loopback')
                except ValueError as error:
                    raise JournalValidationError('session requires a loopback IP literal') from error
                _integer(row['port'], 1, 65535, 'session.port')
                session = dict(host=row['host'], port=row['port'])
                event = JournalEvent(records, kind)
            elif kind == 'request':
                _fields(row, ('schema', 'sequence', 'event', 'request_id', 'wire_base64'))
                _require(pending is None and not (recent and recent['invalid']),
                         'new intent precedes resolution of an earlier request')
                identity = _integer(row['request_id'], 1, MAX_TOKEN, 'request_id')
                _require(identity == next_id, 'request IDs must follow client order')
                wire = _base64(row['wire_base64'], MAX_REQUEST)
                _frame(wire, MAX_REQUEST)
                try:
                    request = _json(wire)
                except (ValueError, UnicodeError, RecursionError) as error:
                    raise JournalValidationError('recorded intent is not a client JSON request') from error
                _require(type(request) is dict and type(request.get('id')) is int
                         and request['id'] == identity, 'intent wire ID differs')
                command = request.get('cmd')
                _require(type(command) is str and command.isascii() and 1 <= len(command) <= 64,
                         'intent command differs from client contract')
                pending = dict(id=identity, command=command)
                recent = None
                next_id += 1
                requests += 1
                if command in KNOWN_COMMANDS:
                    commands[command] += 1
                else:
                    other_commands += 1
                ending = 'unpaired-intent'
                event = JournalEvent(records, kind, identity, command, wire)
            elif kind == 'response':
                _fields(row, ('schema', 'sequence', 'event', 'request_id', 'wire_base64'))
                identity = _integer(row['request_id'], 1, MAX_TOKEN, 'request_id')
                _require(pending is not None and identity == pending['id'], 'response has no matching intent')
                wire = _base64(row['wire_base64'], MAX_RESPONSE)
                _frame(wire, MAX_RESPONSE)
                protocol_error = None
                response = None
                try:
                    response = _json(wire)
                    if type(response) is not dict or type(response.get('id')) is not int or response['id'] != identity:
                        protocol_error = 'response-id'
                    elif type(response.get('ok')) is not bool:
                        protocol_error = 'response-ok'
                except (ValueError, UnicodeError, RecursionError):
                    protocol_error = 'response-json'
                responses += 1
                if protocol_error:
                    invalid += 1
                    ending = 'invalid-response-without-failure'
                else:
                    positive += int(response['ok'])
                    rejected += int(not response['ok'])
                    ending = 'paired-frames'
                response = None  # Do not retain a decoded large reply into later records.
                recent = dict(pending, invalid=protocol_error is not None)
                event = JournalEvent(records, kind, identity, pending['command'], wire,
                                     protocol_error=protocol_error)
                pending = None
            elif kind == 'failure':
                _fields(row, ('schema', 'sequence', 'event', 'request_id', 'phase',
                              'error_type', 'error', 'partial_base64'))
                identity = _integer(row['request_id'], 0, MAX_TOKEN, 'request_id')
                _require(type(row['phase']) is str and row['phase'] in ('connect', 'request')
                         and type(row['error_type']) is str and bool(row['error_type'])
                         and type(row['error']) is str, 'failure metadata differs')
                partial = _base64(row['partial_base64'], MAX_RESPONSE)
                partial_bytes = len(partial)
                if row['phase'] == 'connect':
                    _require(identity == 0 and records == 1 and requests == 0 and not partial,
                             'connect failure must precede every intent')
                    command = None
                else:
                    related = pending if pending is not None else recent
                    _require(related is not None and identity == related['id'],
                             'request failure has no matching intent/response')
                    command = related['command']
                event = JournalEvent(records, kind, identity, command, partial=partial,
                                     phase=row['phase'], error_type=row['error_type'], error=row['error'])
                failures += 1
                pending = None
                terminal = True
                ending = 'recorded-failure'
            else:
                raise JournalValidationError('session may occur only once')
            metadata = {key: '' if key in ('wire_base64', 'partial_base64') else value
                        for key, value in row.items()}
            _require(len(json.dumps(metadata, ensure_ascii=True, separators=(',', ':')).encode('ascii'))
                     <= MAX_METADATA, 'journal metadata exceeds reader profile')
            records += 1
            if visit is not None:
                visit(event)
        _require(session is not None, 'journal session is missing')
        if pending is not None or (recent and recent['invalid'] and not terminal):
            _require(allow_incomplete, 'journal ends with unresolved request evidence')
        storage_bytes = stream.bytes if encoding == 'gzip' else total
        storage_hash = stream.digest.hexdigest() if encoding == 'gzip' else digest.hexdigest()
        end = os.fstat(raw_stream.fileno())
        _require(_signature(start) == _signature(end) == _signature(path.stat()) and storage_bytes == end.st_size,
                 'journal changed during audit')
    actual_hash = digest.hexdigest()
    _require(expected_sha256 is None or actual_hash == expected_sha256, 'journal SHA256 differs')
    _require(expected_storage_sha256 is None or storage_hash == expected_storage_sha256,
             'journal storage SHA256 differs')
    forensic = bool(trailing or pending is not None or (recent and recent['invalid'] and not terminal))
    return dict(schema=1, format='pce-wire-journal-1', input_path=str(path.resolve()),
                sha256=actual_hash, bytes=total, storage_encoding=encoding,
                storage_sha256=storage_hash, storage_bytes=storage_bytes,
                session=session, records=records, request_intents=requests, response_frames=responses,
                positive_server_replies=positive, server_rejections=rejected,
                protocol_invalid_responses=invalid, failure_records=failures,
                unanswered_intents=requests-responses, last_request_id=next_id-1,
                commands=dict(sorted(commands.items())), other_command_intents=other_commands,
                ending=ending,
                unpaired_request_id=None if pending is None else pending['id'],
                trailing_record_bytes=trailing, trailing_record_sha256=tail_hash,
                failure_partial_buffer_bytes=partial_bytes, forensic_prefix=forensic,
                record_stream_complete=not trailing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--sha256', dest='expected_sha256')
    parser.add_argument('--encoding', choices=('plain', 'gzip'), default='plain')
    parser.add_argument('--storage-sha256', dest='expected_storage_sha256')
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = audit_wire_journal(args.journal, expected_sha256=args.expected_sha256,
                                    allow_incomplete=args.allow_incomplete, encoding=args.encoding,
                                    expected_storage_sha256=args.expected_storage_sha256)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, JournalValidationError) as error:
        print('wire journal: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
