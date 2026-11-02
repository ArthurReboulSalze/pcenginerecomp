"""Pure same-ABI development-evidence relations; no file, SDK or guest access.

These checks establish typed identity/counter relationships only. They do not
admit a raw journal, validate instruction semantics or qualify a consumer.
"""
import json
import math

COUNTERS = ('ticks', 'frame', 'native_steps', 'interpreter_steps')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uint(value):
    require(type(value) is int and 0 <= value < 1 << 64,
            'Expected an unsigned 64-bit integer')
    return value


def exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    if isinstance(left, tuple):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def strict_loads(raw):
    require(type(raw) in (str, bytes), 'Expected UTF-8 JSON text or bytes')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result

    def finite(token):
        value = float(token)
        require(math.isfinite(value), 'Non-finite JSON number')
        return value

    def invalid_constant(token):
        raise ValueError('Non-finite JSON constant: ' + token)

    return json.loads(raw, object_pairs_hook=pairs, parse_float=finite,
                      parse_constant=invalid_constant)


def checkpoint_origin(metadata):
    require(type(metadata) is dict, 'Expected checkpoint metadata')
    digest = metadata['sha256']
    require(type(digest) is str and len(digest) == 64
            and set(digest) <= set('0123456789abcdef'), 'Invalid checkpoint SHA256')
    return dict(sha256=digest, **{key: uint(metadata[key]) for key in COUNTERS})


def audio_origin(metadata):
    require(type(metadata) is dict, 'Expected audio origin metadata')
    return {key: uint(metadata[key]) for key in ('pending_pcm_frames', 'source_wav_frames')}


def derive_window(lifetime, origin):
    """Subtract a typed imported origin; singular ``frame`` is a frame delta."""
    require(type(lifetime) is dict and type(origin) is dict, 'Expected counter mappings')
    return {key: uint(uint(lifetime[key]) - uint(origin[key])) for key in COUNTERS}


def validate_origin_status(status, origin, audio):
    expected = checkpoint_origin(origin)
    expected_audio = audio_origin(audio)
    require(type(status['id']) is int and 0 < status['id'] < 1 << 53 and status['ok'] is True,
            'Expected a positive typed status response')
    require(type(status['paused']) is bool and status['local_paused'] is False,
            'Invalid status pause fields')
    host = status['host']
    checkpoint = host['checkpoint']
    require(set(checkpoint) == {'resumed', 'origin', 'audio_origin', 'window'}
            and checkpoint['resumed'] is True
            and exact(checkpoint['origin'], expected)
            and exact(checkpoint['audio_origin'], expected_audio), 'Own-origin status mismatch')
    lifetime = dict(ticks=status['ticks'], frame=status['frame'],
                    native_steps=host['native_steps'], interpreter_steps=host['interpreter_steps'])
    window = derive_window(lifetime, expected)
    exposed = {key: window[key] for key in ('ticks', 'native_steps', 'interpreter_steps')}
    require(exact(checkpoint['window'], exposed), 'Imported/new work equation mismatch')
    return exposed


def compare_counter_roles(source, actual, *, source_origin, actual_origin, promote=True):
    """Compare original or promoted lifetimes without counting imported work twice."""
    require(type(promote) is bool, 'Expected an explicit boolean role')
    old_origin, new_origin = checkpoint_origin(source_origin), checkpoint_origin(actual_origin)
    source_window, actual_window = derive_window(source, old_origin), derive_window(actual, new_origin)
    for old, new in ((old_origin, new_origin), (source, actual)):
        require(uint(old['ticks']) == uint(new['ticks'])
                and uint(old['frame']) == uint(new['frame']), 'Role clocks/frames differ')
        if promote:
            require(uint(new['native_steps']) == uint(uint(old['native_steps']) + uint(old['interpreter_steps']))
                    and uint(new['interpreter_steps']) == 0, 'Per-role lifetime tier relation differs')
        else:
            require(exact({k: uint(old[k]) for k in COUNTERS},
                          {k: uint(new[k]) for k in COUNTERS}), 'Original role counters differ')
    require(source_window['ticks'] == actual_window['ticks']
            and source_window['frame'] == actual_window['frame'], 'New role window differs')
    if promote:
        require(actual_window['native_steps'] == uint(source_window['native_steps'] + source_window['interpreter_steps'])
                and actual_window['interpreter_steps'] == 0, 'New-window tier relation differs')
    else:
        require(exact(source_window, actual_window), 'Original new-window counters differ')
    return dict(source_window=source_window, actual_window=actual_window,
                new_frames=actual_window['frame'], imported_work_counted=False)


def _identity(pc, mpr, physical, data):
    require(uint(pc) < 65536 and type(mpr) in (list, tuple) and len(mpr) == 8
            and all(type(v) is int and 0 <= v < 256 for v in mpr), 'Invalid logical PC/MPR identity')
    require(type(data) in (list, tuple) and 1 <= len(data) <= 7
            and all(type(v) is int and 0 <= v < 256 for v in data), 'Invalid encoded instruction bytes')
    expected = [(mpr[((pc + i) & 65535) >> 13] << 13) | ((pc + i) & 8191)
                for i in range(len(data))]
    require(type(physical) in (list, tuple) and len(physical) == len(expected)
            and all(type(v) is int for v in physical)
            and list(physical) == expected, 'Physical fetch does not follow full mapping')
    return pc, tuple(mpr), tuple(physical), tuple(data)


def encoded_map(capture, expected_origin, expected_abi=28):
    require(type(capture['schema']) is int and capture['schema'] == 1, 'Unsupported capture schema')
    require(type(capture['capacity']) is int and 1 <= capture['capacity'] <= 65536,
            'Invalid bounded capture capacity')
    require(type(expected_abi) is int and 0 < expected_abi < 1 << 32, 'Invalid expected ABI')
    require(type(capture['runtime_abi']) is int and capture['runtime_abi'] == expected_abi,
            'Capture ABI does not identify the expected source')
    require(capture['complete'] is True and uint(capture['dropped_instructions']) == 0
            and uint(capture['unreadable_instructions']) == 0, 'Capture is not lossless')
    require(exact(capture['checkpoint_origin'], checkpoint_origin(expected_origin)), 'Capture own-origin mismatch')
    require(type(capture['observations']) is list, 'Expected capture observations')
    require(len(capture['observations']) <= capture['capacity'], 'Capture exceeds its declared capacity')
    result = {}
    for row in capture['observations']:
        key = _identity(row['pc'], row['mpr'], row['physical'], row['data'])
        require(key not in result, 'Duplicate full encoded identity')
        counts = uint(row['native_hits']), uint(row['interpreted_hits'])
        require(uint(sum(counts)) > 0, 'Observation has no retired work')
        result[key] = counts
    require(uint(sum(sum(counts) for counts in result.values())) == uint(capture['retired_instructions']),
            'Encoded rows do not conserve retired work')
    return result


def compare_encoded_maps(source, actual, *, promote=True):
    require(type(source) is dict and type(actual) is dict and type(promote) is bool,
            'Expected explicit maps and role')
    for mapping in (source, actual):
        for key, counts in mapping.items():
            require(type(key) is tuple and len(key) == 4, 'Invalid full encoded key')
            _identity(*key)
            require(type(counts) is tuple and len(counts) == 2, 'Invalid retirement pair')
            for value in counts:
                uint(value)
            require(uint(sum(counts)) > 0, 'Encoded map entry has no retired work')
    require(source.keys() == actual.keys(), 'Full encoded identity sets differ')
    for key, (native, interpreted) in source.items():
        expected = (uint(native + interpreted), 0) if promote else (native, interpreted)
        require(exact(actual[key], expected), 'Per-identity retirement relationship differs')
    return dict(passed=True, keys=len(source), native=uint(sum(n for n, i in actual.values())),
                interpreted=uint(sum(i for n, i in actual.values())))
