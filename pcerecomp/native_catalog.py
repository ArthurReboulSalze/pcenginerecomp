"""Read-only reconstruction of declared observed-module emission membership.

This checks an explicit selection contract, original observation provenance and
every manifest-listed source artifact. It neither executes an old SDK/emitter
nor proves C++ semantics, linkage, execution, coverage completeness or producer
authorship. Static-only manifests have no admitted identity catalogue here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import groupby
import json
import os
from pathlib import Path
import re
import stat

from .capture import MAX_CAPTURE_BYTES, U64, validate_capture
from .isa import NATIVE
from .observations import MAX_PROFILE_BYTES, _profile_accounting, _validate


Identity = tuple[int, tuple[int, ...], tuple[int, ...], tuple[int, ...]]
PRODUCER_CONTRACT = 'observed-abi28-29-v1'
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_TOTAL_ARTIFACT_BYTES = 512 * 1024 * 1024
_ISA_SHA = '8f1b4454029d442313b93ea162311f0cf4d46a965cdd562b1341f72c2d6ba9ea'
_EMITTER_SHA = '68368ed1230806efa907a03dc9b1d5116f3881a6917a86f6ba93f67fd7f077a6'
_NATIVE_SHA = '6951ccf25b9c079dad86a31f937af81afadae0e28add5e7635da58ca9934e6fd'
_GUARDS = ['full_mpr_snapshot', 'exact_source_bytes_per_instruction', 'instruction_deadline']
_POLICY = 'return to dispatcher, then bounded interpreter or explicit trap'


@dataclass(frozen=True)
class NativeCatalog:
    runtime_abi: int
    observed: frozenset[Identity]
    emitted: frozenset[Identity]
    excluded: frozenset[Identity]
    unsupported: frozenset[Identity]
    counts: dict
    provenance: dict


def _integer(value, maximum, label, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{label} requires an integer in {minimum}..{maximum}')
    return value


def _digest(value, label):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError(label+' requires a lowercase SHA256')
    return value


def _json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON field in native catalogue input')
            value[key] = item
        return value

    def no_float(_):
        raise ValueError('Native catalogue inputs require finite integer numeric tokens')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_float=no_float, parse_constant=no_float)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid native catalogue JSON encoding or nesting') from error


def _exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact(a, b) for a, b in zip(left, right))
    return left == right


def _expect(manifest, field, value):
    if field not in manifest or not _exact(manifest[field], value):
        raise ValueError('Module manifest disagrees with '+field)


def _stamp(value):
    # Windows Path.stat and fstat expose different legacy ctime meanings on
    # supported Python versions. File ID/size/mtime and whole-call hashes agree.
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


class _Files:
    """Whole-call content/stability epoch; never put resolved paths in reports."""
    def __init__(self):
        self.pins = {}

    def read(self, path, maximum, *, expected=None, retain=True):
        path = Path(path).absolute()
        if path.is_symlink():
            raise ValueError('Native catalogue inputs cannot be symbolic links')
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError('Native catalogue input is not a bounded nonempty regular file')
        digest = hashlib.sha256()
        chunks = []
        size = 0
        with path.open('rb') as stream:
            if _stamp(os.fstat(stream.fileno())) != _stamp(before):
                raise ValueError('Native catalogue input changed before read')
            for chunk in iter(lambda: stream.read(65536), b''):
                size += len(chunk)
                if size > maximum:
                    raise ValueError('Native catalogue input exceeds its byte bound')
                digest.update(chunk)
                if retain:
                    chunks.append(chunk)
            if _stamp(os.fstat(stream.fileno())) != _stamp(before):
                raise ValueError('Native catalogue input changed during read')
        after = path.stat()
        if path.is_symlink() or _stamp(after) != _stamp(before) or size != before.st_size:
            raise ValueError('Native catalogue input changed after read')
        actual = digest.hexdigest()
        if expected is not None and actual != _digest(expected, 'Expected file hash'):
            raise ValueError('Native catalogue input SHA256 mismatch')
        key = str(path.resolve())
        pin = _stamp(after), actual, maximum
        if key in self.pins and self.pins[key] != pin:
            raise ValueError('Native catalogue input changed within admission')
        self.pins[key] = pin
        public = dict(basename=path.name, sha256=actual, size_bytes=size)
        return b''.join(chunks) if retain else None, public

    def finish(self):
        for name, (stamp, digest, maximum) in list(self.pins.items()):
            path = Path(name)
            if _stamp(path.stat()) != stamp:
                raise ValueError('Native catalogue input epoch changed')
            self.read(path, maximum, expected=digest, retain=False)


def _selection_contract(files, producer_contract):
    if producer_contract != PRODUCER_CONTRACT or type(producer_contract) is not str:
        raise ValueError('Unsupported native catalogue producer selection contract')
    base = Path(__file__).resolve().parent
    files.read(base/'isa.py', MAX_ARTIFACT_BYTES, expected=_ISA_SHA, retain=False)
    files.read(base/'emitter.py', MAX_ARTIFACT_BYTES, expected=_EMITTER_SHA, retain=False)
    native = frozenset(NATIVE)
    if any(type(op) is not int or not 0 <= op <= 255 for op in native):
        raise ValueError('Native opcode selection contract changed')
    digest = hashlib.sha256(json.dumps(sorted(native), separators=(',', ':')).encode()).hexdigest()
    if digest != _NATIVE_SHA:
        raise ValueError('Native opcode selection contract changed')
    return native, dict(isa_sha256=_ISA_SHA, emitter_sha256=_EMITTER_SHA,
                        native_opcodes_sha256=digest, native_opcode_count=len(native))


def _artifacts(files, manifest_path, manifest):
    base = Path(manifest_path).resolve().parent
    seen, result, total = set(), {}, 0
    for field, suffix, low, high in (('translation_units', '.cpp', 1, 65537),
                                    ('generated_headers', '.hpp', 0, 256)):
        entries = manifest.get(field)
        if type(entries) is not list or not low <= len(entries) <= high:
            raise ValueError('Observed module requires bounded '+field+' artifact list')
        output = []
        for item in entries:
            if type(item) is not dict or set(item) != {'file', 'sha256'}:
                raise ValueError('Invalid module artifact fields')
            name = item['file']
            if (type(name) is not str or not 1 <= len(name) <= 128
                    or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', name) is None
                    or not name.endswith(suffix)
                    or name.split('.', 1)[0].upper() in {
                        'CON', 'PRN', 'AUX', 'NUL',
                        *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
                raise ValueError('Module artifact requires a portable '+suffix+' basename')
            if name.casefold() in seen:
                raise ValueError('Duplicate module artifact basename, case insensitive')
            seen.add(name.casefold())
            path = base/name
            if path.is_symlink() or path.resolve().parent != base:
                raise ValueError('Module artifact escapes manifest directory')
            _, binding = files.read(path, MAX_ARTIFACT_BYTES,
                                    expected=_digest(item['sha256'], 'Artifact'), retain=False)
            total += binding['size_bytes']
            if total > MAX_TOTAL_ARTIFACT_BYTES:
                raise ValueError('Total module artifact bytes exceed catalogue bound')
            output.append(binding)
        result[field] = output
    if not result['translation_units'] or result['translation_units'][0]['basename'] != 'module.cpp':
        raise ValueError('Observed module requires module.cpp as its first translation unit')
    return result


def _layout(manifest, supported, artifacts):
    size = _integer(manifest.get('partition_size'), 4096, 'Module partition size', 1)
    partitioned = manifest.get('partitioned')
    if type(partitioned) is not bool:
        raise ValueError('Module partitioned must be boolean')
    stable = 'partition_layout' in manifest
    if stable:
        _expect(manifest, 'partition_layout', 'stable')
        _expect(manifest, 'pc_bucket_size', 256)
        _expect(manifest, 'partition_identity', 'full_mpr_logical_pc_range_v1')
        if size != 256 or not partitioned:
            raise ValueError('Invalid stable module partition contract')
    elif {'pc_bucket_size', 'partition_identity'} & manifest.keys():
        raise ValueError('Stable partition metadata requires stable layout')
    elif partitioned and len(supported) <= size:
        raise ValueError('Balanced partitioning disagrees with emitted instruction count')
    parts, names = [], []
    for mpr, entries in groupby(supported, key=lambda row: row['mpr']):
        entries = list(entries)
        if stable:
            mapping = sum(value << (8*i) for i, value in enumerate(mpr))
            for page, rows in groupby(entries, key=lambda row: row['pc'] >> 8):
                parts.append(list(rows))
                names.append(f'module_m{mapping:016x}_p{page << 8:04x}.cpp')
        else:
            current = []
            for _, variants in groupby(entries, key=lambda row: row['pc']):
                variants = list(variants)
                if current and len(current)+len(variants) > size:
                    parts.append(current);current = []
                current.extend(variants)
            if current:
                parts.append(current)
    if not stable:
        names = [f'module_part_{i:04d}.cpp' for i in range(len(parts))]
    expected_units = ['module.cpp']+sorted(names) if partitioned else ['module.cpp']
    expected_headers = ['module_parts.hpp'] if partitioned else []
    if ([row['basename'] for row in artifacts['translation_units']] != expected_units
            or [row['basename'] for row in artifacts['generated_headers']] != expected_headers):
        raise ValueError('Module artifact membership disagrees with declared selection layout')
    largest = max((len(part) for part in parts), default=0) if partitioned else len(supported)
    _expect(manifest, 'largest_partition_instructions', largest)
    bodies = _integer(manifest.get('translated_body_count'), len(supported), 'Translated body count')
    if bool(bodies) != bool(supported):
        raise ValueError('Translated body count disagrees with empty/nonempty selection')
    if 'native_span' in manifest:
        if not stable:
            raise ValueError('Native spans require stable observed module layout')
        _expect(manifest, 'native_span', dict(schema=1, protocol='per_instruction_v1'))
        _expect(manifest, 'native_span_translated_body_count', bodies)
    elif 'native_span_translated_body_count' in manifest:
        raise ValueError('Native span count requires explicit native span protocol')


def _key(row):
    return row['pc'], tuple(row['mpr']), tuple(row['physical']), tuple(row['data'])


def load_native_catalog(manifest_path, observations_path, *, producer_contract=PRODUCER_CONTRACT):
    """Admit observed-module declared membership, preserving original input ABIs.

    The named contract supports the byte-identical ISA/emission selection of
    C51 ABI28 and ABI29. Caller-owned build/producer/execution proof remains
    separate. Paths never enter returned provenance beyond explicit basenames.
    Original capture/profile files and generated source are never modified.
    """
    files = _Files()
    native, selection_source = _selection_contract(files, producer_contract)
    raw, manifest_binding = files.read(manifest_path, MAX_MANIFEST_BYTES)
    manifest = _json(raw)
    if type(manifest) is not dict:
        raise ValueError('Module manifest must be an object')
    _expect(manifest, 'schema', 1)
    abi = _integer(manifest.get('runtime_abi'), 29, 'Observed module runtime ABI', 28)
    _expect(manifest, 'execution_evidence', False)
    _expect(manifest, 'dispatch_strategy', 'full_mpr_pc_opcode_operand_key')
    _expect(manifest, 'guards', _GUARDS)
    _expect(manifest, 'unsupported_policy', _POLICY)
    capture_input = 'code_capture_sha256' in manifest
    profile_input = 'observation_profile_sha256' in manifest
    if capture_input == profile_input:
        raise ValueError('Native membership unavailable: require exactly one observed capture/profile provenance')
    field = 'code_capture_sha256' if capture_input else 'observation_profile_sha256'
    maximum = MAX_CAPTURE_BYTES if capture_input else MAX_PROFILE_BYTES
    raw, input_binding = files.read(observations_path, maximum,
                                    expected=_digest(manifest[field], 'Observation input'))
    value = _json(raw)
    if capture_input:
        if any(key.startswith('observation_') for key in manifest):
            raise ValueError('Capture manifest cannot declare observation-profile provenance')
        instructions = validate_capture(value)
        provenance = [{key: item for key, item in value.items() if key != 'observations'}]
        accounting = dict(capture_runtime_abi=value['runtime_abi'],
            capture_complete=value['complete'], capture_retired_instructions=value['retired_instructions'],
            capture_dropped_instructions=value['dropped_instructions'],
            capture_unreadable_instructions=value['unreadable_instructions'],
            captured_native_hits=sum(row['native_hits'] for row in instructions),
            captured_interpreted_hits=sum(row['interpreted_hits'] for row in instructions))
        if 'checkpoint_origin' in value:
            accounting.update(capture_checkpoint_origin=value['checkpoint_origin'],
                              capture_execution_window='resumed-checkpoint-suffix')
        elif {'capture_checkpoint_origin', 'capture_execution_window'} & manifest.keys():
            raise ValueError('Module invented capture checkpoint origin')
    else:
        if any(key.startswith(('capture_', 'captured_')) for key in manifest):
            raise ValueError('Profile manifest cannot declare singular capture provenance')
        instructions, provenance = _validate(value)
        accounting = dict(observation_profile_format=value['format'],
            observation_profile_schema=value['schema'], observation_inputs=provenance,
            **_profile_accounting(value))
        if value['schema'] == 1 and {'selection_stages', 'selected_historical_totals',
                                    'selection_counts', 'selection_policy'} & manifest.keys():
            raise ValueError('Version1 profile cannot declare additive selection metadata')
    for key, expected in accounting.items():
        _expect(manifest, key, expected)
    # A later diagnostic can decode an older module's retained inputs, but
    # cannot backdate a newer capture producer into that historical emitter.
    if any(item['runtime_abi'] > abi for item in provenance):
        raise ValueError('Observation producer ABI exceeds declared module producer contract')
    base_fields = {'schema', 'runtime_abi', 'translation_units', 'generated_headers',
        'partition_size', 'partitioned', 'dispatch_strategy', 'translated_body_count',
        'largest_partition_instructions', 'native_instructions_emitted', 'native_contexts',
        'observed_instructions', 'execution_evidence', 'excluded_physical_ranges',
        'excluded_observations', 'excluded_retired_hits', 'unsupported_observations',
        'guards', 'unsupported_policy', 'scope'}
    optional = {'partition_layout', 'pc_bucket_size', 'partition_identity',
                'native_span', 'native_span_translated_body_count'}
    if set(manifest) - base_fields - optional - {field} - accounting.keys():
        raise ValueError('Unsupported observed module manifest fields')
    if type(manifest.get('scope')) is not str or len(manifest['scope']) > 4096:
        raise ValueError('Module scope requires a bounded string')
    spans = manifest.get('excluded_physical_ranges')
    if type(spans) is not list or len(spans) > 256:
        raise ValueError('Module exclusions require at most256 physical spans')
    exclusions = []
    for span in spans:
        if type(span) is not dict or set(span) != {'start', 'length'}:
            raise ValueError('Invalid physical exclusion fields')
        start = _integer(span['start'], 0x1fffff, 'Excluded physical start')
        length = _integer(span['length'], 0x200000-start, 'Excluded physical length', 1)
        exclusions.append((start, length))
    if exclusions != sorted(set(exclusions)):
        raise ValueError('Module exclusions must be canonical sorted unique spans')
    excluded, unsupported, emitted = [], [], []
    for row in instructions:
        if any(start <= address < start+length
               for address in row['physical'] for start, length in exclusions):
            excluded.append(row)
        elif row['data'][0] not in native:
            unsupported.append(row)
        else:
            emitted.append(row)
    counts = dict(observed_instructions=len(instructions), native_instructions_emitted=len(emitted),
        native_contexts=len({tuple(row['mpr']) for row in emitted}), excluded_observations=len(excluded),
        excluded_retired_hits=sum(row['native_hits']+row['interpreted_hits'] for row in excluded),
        unsupported_observations=len(unsupported))
    for key, expected in counts.items():
        _integer(manifest.get(key), U64, 'Module '+key)
        _expect(manifest, key, expected)
    artifacts = _artifacts(files, manifest_path, manifest)
    _layout(manifest, emitted, artifacts)
    files.finish()
    if capture_input:
        provenance[0].update(sha256=input_binding['sha256'], size_bytes=input_binding['size_bytes'],
            native_hits=accounting['captured_native_hits'],
            interpreted_hits=accounting['captured_interpreted_hits'], observation_count=len(instructions))
    return NativeCatalog(abi, frozenset(map(_key, instructions)), frozenset(map(_key, emitted)),
        frozenset(map(_key, excluded)), frozenset(map(_key, unsupported)), counts,
        dict(format='pce-native-catalog-1', selection_contract=producer_contract,
             membership_claim='reconstructed-declared-emission', runtime_abi=abi,
             manifest=manifest_binding, observations=dict(kind='capture' if capture_input else 'profile',
                **input_binding), artifacts=artifacts, original_inputs=provenance,
             excluded_physical_ranges=[dict(start=start, length=length) for start, length in exclusions],
             selection_source=selection_source, execution_evidence=False, linked_binary_verified=False,
             scope='Declared emitted identity membership under the named selection contract and exact input/artifact hashes; not producer authorship, generated-code semantics, linked-binary or execution qualification.'))
