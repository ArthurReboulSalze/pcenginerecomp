"""Private discovery diagnostics; identity unions are not execution qualification.

Each closed capture keeps its own counts and original ABI/origin. Distinct
captures may overlap, so this interface deliberately supplies no combined hit
total or accumulated campaign percentage.
"""
import hashlib
from pathlib import Path
import stat

from .capture import MAX_CAPTURE_BYTES, MAX_OBSERVATIONS, U64, integer, validate_capture
from .observations import MAX_INPUTS, MAX_TOTAL_INPUT_BYTES, _json
from .emitter import NATIVE

FORMAT = 'pce-native-gap-report-1'


def _key(row):
    return row['pc'], tuple(row['mpr']), tuple(row['physical']), tuple(row['data'])


def _identity(key):
    pc, mpr, physical, data = key
    return dict(pc=pc, mpr=list(mpr), physical=list(physical), data=list(data))


def _stamp(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Discovery capture must be a regular non-symlink file')
    return info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino


def _read(path):
    before = _stamp(path)
    if before[0] > MAX_CAPTURE_BYTES:
        raise ValueError('Discovery capture exceeds 64 MiB')
    with path.open('rb') as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    if len(raw) > MAX_CAPTURE_BYTES or len(raw) != before[0] or _stamp(path) != before:
        raise ValueError('Discovery capture changed or exceeded its admitted size')
    return raw, before


def report_native_gaps(catalog, capture_paths):
    """Join complete captures to a verified declared emission catalog.

    Full keys include every fetch address. Exclusions apply to operand bytes
    and to newly discovered keys too. No source bytes are obtained from live
    RAM, a disc, an SDK import or an instruction-address interval.
    """
    from .native_catalog import NativeCatalog
    if not isinstance(catalog, NativeCatalog):
        raise ValueError('Discovery requires an admitted NativeCatalog')
    if not isinstance(capture_paths, (list, tuple)) or not 1 <= len(capture_paths) <= MAX_INPUTS:
        raise ValueError(f'Discovery requires 1..{MAX_INPUTS} capture paths')
    partitions = (catalog.emitted, catalog.excluded, catalog.unsupported)
    if (any(not isinstance(part, frozenset) for part in partitions)
            or any(partitions[i] & partitions[j] for i in range(3) for j in range(i))
            or frozenset().union(*partitions) != catalog.observed):
        raise ValueError('Invalid declared emission catalog partition')
    spans = catalog.provenance.get('excluded_physical_ranges', [])
    if not isinstance(spans, list) or len(spans) > 256:
        raise ValueError('Invalid declared physical exclusions')
    exclusions = []
    for span in spans:
        if not isinstance(span, dict) or set(span) != {'start', 'length'}:
            raise ValueError('Invalid declared physical exclusion fields')
        start = integer(span['start'], 0x1fffff, 'excluded physical start')
        length = integer(span['length'], 0x200000 - start, 'excluded physical length', 1)
        exclusions.append((start, length))
    rows, inputs, paths, total_bytes = {}, {}, {}, 0
    for supplied in capture_paths:
        path = Path(supplied).absolute()
        if path in paths:
            continue
        raw, stamp = _read(path)
        digest = hashlib.sha256(raw).hexdigest()
        paths[path] = (stamp, digest)
        if digest in inputs:
            inputs[digest]['aliases'].add(path.name)
            continue
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Discovery capture inputs exceed the existing 64 MiB aggregate bound')
        capture = _json(raw)
        observations = validate_capture(capture)
        if capture['complete'] is not True:
            raise ValueError('Discovery requires complete, lossless captures')
        native = interpreted = 0
        classifications = dict(emitted=0, excluded=0, unsupported=0, uncompiled=0)
        missing = []
        for observation in observations:
            key = _key(observation)
            if key not in rows and len(rows) >= MAX_OBSERVATIONS:
                raise ValueError('Discovery identity union exceeds 65536')
            if key in catalog.emitted:
                category = 'emitted'
            elif key in catalog.excluded or any(start <= address < start + length
                     for address in key[2] for start, length in exclusions):
                category = 'excluded'
            elif key[3][0] not in NATIVE:
                category = 'unsupported'
            else:
                category = 'uncompiled'
            item = rows.setdefault(key, _identity(key) | dict(
                mnemonic=observation['mnemonic'], category=category,
                catalog_identity=key in catalog.observed,
                native_supported=key[3][0] in NATIVE, observations=[]))
            item['observations'].append(dict(input_sha256=digest,
                native_hits=observation['native_hits'], interpreted_hits=observation['interpreted_hits']))
            native = integer(native + observation['native_hits'], U64, 'capture native total')
            interpreted = integer(interpreted + observation['interpreted_hits'], U64, 'capture interpreted total')
            classifications[category] += 1
            if category == 'uncompiled':
                missing.append(_identity(key) | dict(native_hits=observation['native_hits'],
                    interpreted_hits=observation['interpreted_hits']))
        missing.sort(key=lambda item: (-item['interpreted_hits'], _key(item)))
        inputs[digest] = dict(name=path.name, aliases={path.name}, sha256=digest,
            size_bytes=len(raw), runtime_abi=capture['runtime_abi'],
            checkpoint_origin=capture.get('checkpoint_origin'),
            retired_instructions=capture['retired_instructions'], native_steps=native,
            interpreter_steps=interpreted, observations=len(observations),
            classifications=classifications, uncompiled_by_interpreted_hits=missing)
    # Rehash every actual pathname, including distinct aliases of duplicate
    # content. A caller gets one coherent source-admission epoch, not a silent
    # mixture of bytes changed while another capture was being inspected.
    for path, (stamp, digest) in paths.items():
        raw, after = _read(path)
        if after != stamp or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Discovery capture changed during analysis')
    ordered = [rows[key] for key in sorted(rows)]
    for item in ordered:
        item['observations'].sort(key=lambda value: value['input_sha256'])
    input_rows = []
    for digest in sorted(inputs):
        item = inputs[digest]
        item['aliases'] = sorted(item['aliases'])
        item['name'] = item['aliases'][0]
        input_rows.append(item)
    unseen = [_identity(key) for key in sorted(catalog.emitted - rows.keys())]
    counts = {category: sum(item['category'] == category for item in ordered)
              for category in ('emitted', 'excluded', 'unsupported', 'uncompiled')}
    native_outside = sum(any(observation['native_hits'] for observation in item['observations'])
                         and item['category'] != 'emitted' for item in ordered)
    return dict(schema=1, format=FORMAT, runtime_abi=catalog.runtime_abi,
        policy='identity-union', qualification=False, code_bearing=True,
        scope='Declared emitted membership and per-input retired identities only; not linked-binary semantics, a nonoverlapping execution total, campaign coverage or snapshot provenance',
        catalog=dict(provenance=catalog.provenance, counts=catalog.counts), inputs=input_rows,
        summary=dict(input_occurrences=len(capture_paths), unique_inputs=len(inputs),
            duplicate_inputs=len(capture_paths) - len(inputs), union_keys=len(rows),
            emitted_observed=counts['emitted'], emitted_unexercised=len(unseen),
            excluded_observed=counts['excluded'], unsupported_observed=counts['unsupported'],
            uncompiled_observed=counts['uncompiled'], native_outside_catalog=native_outside),
        identities=ordered, emitted_unexercised=unseen)
