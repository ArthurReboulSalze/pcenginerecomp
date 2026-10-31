"""Strict bounded private observations; captures contain translated-source bytes."""
import hashlib
import json
from pathlib import Path

from .abi import CAPTURE_ABIS
from .isa import decode

MAX_CAPTURE_BYTES = 64 * 1024 * 1024
MAX_OBSERVATIONS = 65536
U64 = (1 << 64) - 1


def integer(value, maximum, label, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def validate_capture(capture):
    """Return canonical observations with decoder-derived instruction metadata."""
    fields = {
        'schema', 'runtime_abi', 'capacity', 'dropped_instructions',
        'unreadable_instructions', 'retired_instructions', 'complete', 'observations'
    }
    if not isinstance(capture, dict) or set(capture) not in (fields, fields | {'checkpoint_origin'}):
        raise ValueError('Invalid code-capture fields')
    if 'checkpoint_origin' in capture:
        validate_checkpoint_origin(capture['checkpoint_origin'])
    if type(capture['schema']) is not int or capture['schema'] != 1:
        raise ValueError('Unsupported code-capture schema')
    if type(capture['runtime_abi']) is not int or capture['runtime_abi'] not in CAPTURE_ABIS:
        raise ValueError('Unsupported code-capture runtime ABI')
    capacity = integer(capture['capacity'], MAX_OBSERVATIONS, 'capacity', 1)
    dropped = integer(capture['dropped_instructions'], U64, 'dropped instructions')
    unreadable = integer(capture['unreadable_instructions'], U64, 'unreadable instructions')
    retired = integer(capture['retired_instructions'], U64, 'retired instructions')
    if type(capture['complete']) is not bool or capture['complete'] != (dropped == 0 and unreadable == 0):
        raise ValueError('Capture completeness disagrees with counters')
    observations = capture['observations']
    if not isinstance(observations, list) or len(observations) > capacity:
        raise ValueError('Observation capacity exceeded')
    seen, result, total = set(), [], dropped + unreadable
    for item in observations:
        if not isinstance(item, dict) or set(item) != {'pc', 'mpr', 'physical', 'data', 'native_hits', 'interpreted_hits'}:
            raise ValueError('Invalid observation fields')
        pc = integer(item['pc'], 65535, 'logical PC')
        mpr, raw, addresses = item['mpr'], item['data'], item['physical']
        if not isinstance(mpr, list) or len(mpr) != 8:
            raise ValueError('MPR mapping requires eight bytes')
        mpr = tuple(integer(v, 255, 'MPR') for v in mpr)
        if not isinstance(raw, list) or not 1 <= len(raw) <= 7:
            raise ValueError('Instruction data requires one to seven bytes')
        raw = tuple(integer(v, 255, 'instruction byte') for v in raw)
        if not isinstance(addresses, list) or len(addresses) != len(raw):
            raise ValueError('Physical addresses must match instruction bytes')
        addresses = tuple(integer(v, 0x1fffff, 'physical address') for v in addresses)
        def read(address):
            offset = (address - pc) & 65535
            if offset >= len(raw):
                raise ValueError('Truncated instruction data')
            return raw[offset]
        ins = decode(read, pc, mpr)
        if ins.data != raw or ins.physical != addresses:
            raise ValueError('Instruction length or physical mapping disagrees with decoder')
        native = integer(item['native_hits'], U64, 'native hits')
        interpreted = integer(item['interpreted_hits'], U64, 'interpreted hits')
        if not 0 < native + interpreted <= U64:
            raise ValueError('Observation must have a bounded nonzero hit count')
        key = (pc, mpr, raw)
        if key in seen:
            raise ValueError('Duplicate observed instruction identity')
        seen.add(key)
        total += native + interpreted
        result.append(ins.report() | {'mpr': mpr, 'native_hits': native, 'interpreted_hits': interpreted})
    if total != retired:
        raise ValueError('Capture retirement total disagrees with observations')
    return sorted(result, key=lambda ins: (ins['mpr'], ins['pc'], ins['data']))


def validate_checkpoint_origin(origin):
    """Exact imported boundary; observation totals describe only its new suffix."""
    fields = {'sha256', 'ticks', 'frame', 'native_steps', 'interpreter_steps'}
    if not isinstance(origin, dict) or set(origin) != fields:
        raise ValueError('Invalid checkpoint capture origin fields')
    digest = origin['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Checkpoint origin requires lowercase SHA256')
    for key in fields - {'sha256'}:
        integer(origin[key], U64, 'checkpoint origin '+key)
    return dict(origin)


def load_capture(path: Path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    if len(raw) > MAX_CAPTURE_BYTES:
        raise ValueError('Code capture exceeds 64 MiB')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in code capture')
            result[key] = value
        return result
    capture = json.loads(raw, object_pairs_hook=unique)
    validate_capture(capture)
    return capture, hashlib.sha256(raw).hexdigest()
