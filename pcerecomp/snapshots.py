"""Content snapshots for explicit, read-only evidence graphs.

JSON is hashed and parsed from the same bounded UTF-8 bytes (no BOM). Binary
artifacts are streamed. ``bind``/``bind_all`` may reuse an admitted binary
snapshot; that is an epoch cache, NOT a fresh observation of the filesystem.
Call ``revalidate`` at each use/seal boundary. It reads every admitted path
again, including aliases, and never trusts timestamps instead of content.

Checks establish content at those checks, not a filesystem lock, perpetual
immutability, producer authenticity, instruction semantics or qualification.
No content is executed and no SDK is imported.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType


DEFAULT_MAX_JSON_BYTES = 64 * 1024 * 1024
_READ_CHUNK_BYTES = 1024 * 1024


class SnapshotError(ValueError):
    """A declared snapshot, explicit graph or current-content check failed."""


def _path(value) -> Path:
    try:
        spelling = os.fspath(value)
        if type(spelling) is not str:
            raise TypeError('Expected a text path')
        return Path(os.path.abspath(spelling))
    except (TypeError, ValueError, OSError) as error:
        raise SnapshotError('Snapshot requires a valid text file path') from error


def _digest(value: str) -> str:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise SnapshotError('Expected a lowercase SHA256 digest')
    return value


def _maximum(value: int) -> int:
    if type(value) is not int or value < 1:
        raise SnapshotError('JSON byte limit must be a positive integer')
    return value


def _strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SnapshotError('Duplicate JSON field in snapshot')
            result[key] = value
        return result

    def finite(token):
        value = float(token)
        if not math.isfinite(value):
            raise SnapshotError('Non-finite JSON number in snapshot')
        return value

    def invalid_constant(_):
        raise SnapshotError('Non-finite JSON constant in snapshot')

    try:
        # json.loads(bytes) also accepts UTF-16/32. Evidence JSON here has one
        # explicit encoding and retains its original byte-level identity.
        text = raw.decode('utf-8')
        if text.startswith('\ufeff'):
            raise SnapshotError('JSON snapshots require UTF-8 without a BOM')
        return json.loads(text, object_pairs_hook=pairs, parse_float=finite,
                          parse_constant=invalid_constant)
    except SnapshotError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise SnapshotError('Invalid UTF-8 JSON snapshot') from error


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """An admitted path/content binding; metadata is not an authenticity claim."""

    path: Path = field(compare=False)
    sha256: str
    size_bytes: int
    _spelling: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, 'path', _path(self.path))
        object.__setattr__(self, '_spelling', str(self.path))
        _digest(self.sha256)
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise SnapshotError('Snapshot size must be a nonnegative integer')

    def reference(self) -> dict[str, str]:
        """Return a detached serialized reference, without path guessing."""
        return {'path': str(self.path), 'sha256': self.sha256}


@dataclass(frozen=True, slots=True)
class JsonSnapshot(FileSnapshot):
    """Exact immutable JSON bytes and a parse-once, deeply frozen value.

    ``value`` returns a detached ordinary JSON tree on every access, preserving
    dict/list/null/bool/int/finite-float types. Caller edits cannot change the
    cached parse or its original bytes.
    """

    raw: bytes = field(repr=False)
    _frozen_value: object = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        FileSnapshot.__post_init__(self)
        if type(self.raw) is not bytes:
            raise SnapshotError('JSON snapshot raw content must be immutable bytes')
        if len(self.raw) != self.size_bytes or hashlib.sha256(self.raw).hexdigest() != self.sha256:
            raise SnapshotError('JSON snapshot bytes disagree with their binding')
        try:
            frozen = _freeze(_strict_json(self.raw))
        except RecursionError as error:
            raise SnapshotError('JSON snapshot nesting exceeds supported depth') from error
        object.__setattr__(self, '_frozen_value', frozen)

    @property
    def value(self):
        return _thaw(self._frozen_value)


@dataclass(frozen=True, slots=True)
class _Pin:
    snapshot: FileSnapshot
    target: str


def _stamp(info):
    # Do not compare ctime: Windows stat/fstat have differed in its meaning.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read(path: Path, *, retain: bool, maximum: int | None = None):
    """Read through the supplied spelling; resolved targets are checks only."""
    try:
        target = str(path.resolve(strict=True))
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise SnapshotError('Snapshot input must be a regular file: ' + str(path))
        if maximum is not None and before.st_size > maximum:
            raise SnapshotError('JSON snapshot exceeds its byte limit: ' + str(path))
        digest = hashlib.sha256()
        chunks = [] if retain else None
        size = 0
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _stamp(opened) != _stamp(before):
                raise SnapshotError('Snapshot input changed before read: ' + str(path))
            while True:
                request = (_READ_CHUNK_BYTES if maximum is None
                           else min(_READ_CHUNK_BYTES, maximum - size + 1))
                chunk = stream.read(request)
                if not chunk:
                    break
                size += len(chunk)
                if maximum is not None and size > maximum:
                    raise SnapshotError('JSON snapshot exceeds its byte limit: ' + str(path))
                digest.update(chunk)
                if chunks is not None:
                    chunks.append(chunk)
            if _stamp(os.fstat(stream.fileno())) != _stamp(before):
                raise SnapshotError('Snapshot input changed during read: ' + str(path))
        if (str(path.resolve(strict=True)) != target or _stamp(path.stat()) != _stamp(before)
                or size != before.st_size):
            raise SnapshotError('Snapshot input changed after read: ' + str(path))
        snapshot = FileSnapshot(path, digest.hexdigest(), size)
        return _Pin(snapshot, target), b''.join(chunks) if chunks is not None else None
    except SnapshotError:
        raise
    except (OSError, RuntimeError, ValueError) as error:
        raise SnapshotError('Cannot read stable snapshot file: ' + str(path)) from error


class SnapshotStore:
    """One explicit content-admission epoch, without implicit graph traversal.

    Binary ``bind`` calls reuse an admitted matching reference until explicit
    ``revalidate``; repeated ``read_json`` calls do read current bytes. An epoch
    refuses conflicting digests/content or changed resolved alias targets.
    Same-byte replacements at the same target path remain valid after a real
    content check. This class is not a concurrent filesystem transaction/lock.
    """

    def __init__(self):
        # WindowsPath equality folds case even in a case-sensitive directory.
        # Preserve every supplied normalized spelling as a distinct graph key.
        self._pins: dict[str, _Pin] = {}
        self._json: dict[str, JsonSnapshot] = {}

    def _expected(self, path, expected):
        if expected is not None:
            _digest(expected)
        previous = self._pins.get(path)
        if previous is not None and expected is not None and expected != previous.snapshot.sha256:
            raise SnapshotError('Expected digest conflicts with admitted snapshot: ' + str(path))
        return previous

    @staticmethod
    def _check(pin, previous, expected):
        if expected is not None and pin.snapshot.sha256 != expected:
            raise SnapshotError('Snapshot SHA256 mismatch: ' + str(pin.snapshot.path))
        if previous is not None:
            if (pin.snapshot.sha256 != previous.snapshot.sha256
                    or pin.snapshot.size_bytes != previous.snapshot.size_bytes):
                raise SnapshotError('Snapshot content changed within admission: ' + str(pin.snapshot.path))
            if pin.target != previous.target:
                raise SnapshotError('Snapshot alias target changed within admission: ' + str(pin.snapshot.path))

    def bind(self, path, *, expected_sha256=None) -> FileSnapshot:
        """Stream a new binary artifact, or reuse its admitted epoch binding.

        This does not load binaries/CHDs into memory. Reuse is not evidence of
        current filesystem content; call revalidate before use/seal and after
        an external child has used the admitted files.
        """
        path = _path(path)
        key = str(path)
        previous = self._expected(key, expected_sha256)
        if previous is not None:
            return previous.snapshot
        pin, _ = _read(path, retain=False)
        self._check(pin, None, expected_sha256)
        self._pins[key] = pin
        return pin.snapshot

    def read_json(self, path, *, expected_sha256=None,
                  max_bytes=DEFAULT_MAX_JSON_BYTES) -> JsonSnapshot:
        """Hash/parse exactly one bounded buffer; always re-read current bytes.

        Use an explicit larger max_bytes, e.g. 128*1024*1024, for a known large
        profile. Invalid JSON or mismatched bytes never register a new pin.
        """
        path = _path(path)
        key = str(path)
        maximum = _maximum(max_bytes)
        previous = self._expected(key, expected_sha256)
        pin, raw = _read(path, retain=True, maximum=maximum)
        self._check(pin, previous, expected_sha256)
        cached = self._json.get(key)
        if cached is not None:
            if raw != cached.raw:
                raise SnapshotError('JSON snapshot raw bytes changed: ' + str(path))
            return cached
        snapshot = JsonSnapshot(path, pin.snapshot.sha256, pin.snapshot.size_bytes, raw)
        self._pins[key] = pin
        self._json[key] = snapshot
        return snapshot

    def bind_all(self, bindings: Mapping) -> None:
        """Transactionally admit an explicit absolute path->lowercase-SHA graph.

        References embedded inside JSON are not inferred or recursively opened.
        Overlapping matching pins are reused; every new file is streamed once.
        A failed graph leaves this store unchanged. Revalidate checks freshness.
        """
        if not isinstance(bindings, Mapping):
            raise SnapshotError('Snapshot graph must be an explicit path-to-digest mapping')
        declared = {}
        for supplied, expected in bindings.items():
            try:
                spelling = os.fspath(supplied)
            except TypeError as error:
                raise SnapshotError('Snapshot graph requires text file paths') from error
            if type(spelling) is not str or not Path(spelling).is_absolute():
                raise SnapshotError('Serialized snapshot graph paths must be absolute')
            path = _path(spelling)
            key = str(path)
            _digest(expected)
            if key in declared and declared[key] != expected:
                raise SnapshotError('Conflicting normalized snapshot graph aliases')
            self._expected(key, expected)
            declared[key] = expected
        staged = {}
        for key, expected in declared.items():
            if key in self._pins:
                continue
            pin, _ = _read(Path(key), retain=False)
            self._check(pin, None, expected)
            staged[key] = pin
        self._pins.update(staged)

    def bindings(self) -> dict[str, str]:
        """Return a detached admitted epoch map, not a freshness check."""
        return {key: pin.snapshot.sha256 for key, pin in sorted(self._pins.items())}

    def revalidate(self) -> None:
        """Stream every admitted supplied path again; never trust mtime alone."""
        for key, previous in tuple(self._pins.items()):
            pin, _ = _read(Path(key), retain=False)
            self._check(pin, previous, previous.snapshot.sha256)
