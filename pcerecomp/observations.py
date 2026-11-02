"""Private, additive code catalogues with independently verifiable raw provenance.

A profile is not a capture or a newly executed run. Historical counters sum
distinct input files; overlapping windows cannot be identified automatically.
"""
import base64
import binascii
import hashlib
import io
import json
from pathlib import Path

from .capture import MAX_CAPTURE_BYTES, MAX_OBSERVATIONS, U64, integer, validate_capture
from .isa import decode

FORMAT = 'pce-observation-profile-1'
ADDITIVE_FORMAT = 'pce-observation-profile-2'
SELECTION_POLICY = ('stage 0 retains every original contribution; each later stage selects '
                    'the lowest-SHA input for identities absent all prior stages')
MAX_PROFILE_BYTES = 128 * 1024 * 1024
MAX_INPUTS = 256
MAX_TOTAL_INPUT_BYTES = 64 * 1024 * 1024
MAX_CONTRIBUTIONS = 262144
SERIALIZER = 'pce-observation-profile-json-pretty-v1'


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in observation input')
            result[key] = value
        return result

    def no_float(value):
        raise ValueError('Observation inputs require integer numeric tokens')

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_float=no_float,
                          parse_constant=no_float)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid observation JSON encoding or nesting') from exc


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          allow_nan=False).encode('utf-8')
    except (TypeError, RecursionError) as exc:
        raise ValueError('Invalid observation profile JSON values') from exc


def _digest(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in '0123456789abcdef' for c in value)):
        raise ValueError('Input identity requires lowercase SHA256')
    return value


def _add(left, right, label):
    return integer(left + right, U64, label)


def _derive(inputs, capacity):
    """Rebuild all union facts exclusively from hash-verified original bytes."""
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_INPUTS:
        raise ValueError(f'Profile requires one to {MAX_INPUTS} distinct inputs')
    seen, union, metadata = set(), {}, []
    totals = {'native_hits': 0, 'interpreted_hits': 0, 'retired_instructions': 0}
    total_bytes = contributions = 0
    for source in inputs:
        if not isinstance(source, dict) or set(source) != {'sha256', 'size_bytes', 'raw_base64'}:
            raise ValueError('Invalid observation input provenance fields')
        digest = _digest(source['sha256'])
        if digest in seen:
            raise ValueError('Duplicate observation input SHA256')
        seen.add(digest)
        size = integer(source['size_bytes'], MAX_CAPTURE_BYTES, 'input byte size', 1)
        total_bytes += size
        if total_bytes > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Total original capture bytes exceed profile limit')
        encoded = source['raw_base64']
        if not isinstance(encoded, str) or len(encoded) != 4 * ((size + 2) // 3):
            raise ValueError('Input base64 length disagrees with original byte size')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('Invalid original capture base64') from exc
        if (len(raw) != size or base64.b64encode(raw).decode('ascii') != encoded
                or hashlib.sha256(raw).hexdigest() != digest):
            raise ValueError('Original capture SHA256, size or canonical base64 disagrees')
        capture = _json(raw)
        decoded = validate_capture(capture)
        if not capture['complete']:
            raise ValueError('Observation profiles require complete lossless inputs')
        contributions += len(decoded)
        if contributions > MAX_CONTRIBUTIONS:
            raise ValueError('Observation contribution capacity exceeded')
        native = sum(item['native_hits'] for item in decoded)
        interpreted = sum(item['interpreted_hits'] for item in decoded)
        for key, value in (('native_hits', native), ('interpreted_hits', interpreted),
                           ('retired_instructions', capture['retired_instructions'])):
            totals[key] = _add(totals[key], value, 'historical '+key)
        detail = {key: value for key, value in capture.items() if key != 'observations'}
        detail.update(sha256=digest, size_bytes=size, native_hits=native,
                      interpreted_hits=interpreted, observation_count=len(decoded))
        metadata.append(detail)
        for item in decoded:
            key = (item['pc'], tuple(item['mpr']), tuple(item['data']))
            if key not in union:
                if len(union) >= capacity:
                    raise ValueError('Observation union capacity exceeded; no identities dropped')
                union[key] = {name: list(item[name]) if name in ('mpr', 'physical', 'data') else item[name]
                              for name in ('pc', 'mpr', 'physical', 'data')}
                union[key].update(native_hits=0, interpreted_hits=0, contributions=[])
            entry = union[key]
            for tier in ('native_hits', 'interpreted_hits'):
                entry[tier] = _add(entry[tier], item[tier], 'union '+tier)
            _add(entry['native_hits'], entry['interpreted_hits'], 'union total hits')
            entry['contributions'].append({'input_sha256': digest,
                                          'native_hits': item['native_hits'],
                                          'interpreted_hits': item['interpreted_hits']})
    _add(totals['native_hits'], totals['interpreted_hits'], 'historical total hits')
    if totals['native_hits'] + totals['interpreted_hits'] != totals['retired_instructions']:
        raise ValueError('Historical retirement sum disagrees')
    ordered = sorted(union.values(), key=lambda item: (item['mpr'], item['pc'], item['data']))
    for item in ordered:
        item['contributions'].sort(key=lambda contribution: contribution['input_sha256'])
    return ordered, totals, sorted(metadata, key=lambda item: item['sha256'])


def _compose_details(input_paths, *, capacity=MAX_OBSERVATIONS):
    """Compose lossless original capture files; duplicate raw files count once.

    No input is edited. SHA ordering makes results independent of argument order.
    Paths are deliberately absent from the portable, private profile.
    """
    integer(capacity, MAX_OBSERVATIONS, 'profile capacity', 1)
    sources, total, argument_digests = {}, 0, []
    for index, path in enumerate(input_paths):
        if index >= MAX_INPUTS:
            raise ValueError(f'At most {MAX_INPUTS} input paths are accepted')
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_CAPTURE_BYTES + 1)
        if len(raw) > MAX_CAPTURE_BYTES:
            raise ValueError('Code capture exceeds 64 MiB')
        digest = hashlib.sha256(raw).hexdigest()
        argument_digests.append(digest)
        if digest in sources:
            continue
        total += len(raw)
        if total > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Total original capture bytes exceed profile limit')
        sources[digest] = {'sha256': digest, 'size_bytes': len(raw),
                           'raw_base64': base64.b64encode(raw).decode('ascii')}
    inputs = [sources[key] for key in sorted(sources)]
    observations, totals, metadata = _derive(inputs, capacity)
    profile = {'format': FORMAT, 'schema': 1, 'execution_evidence': False,
               'capacity': capacity, 'inputs': inputs, 'observations': observations,
               'historical_totals': totals}
    if len(_canonical(profile)) > MAX_PROFILE_BYTES:
        raise ValueError('Observation profile exceeds 128 MiB')
    return profile, argument_digests, metadata


def compose_observation_profile(input_paths, *, capacity=MAX_OBSERVATIONS):
    """Compose original captures; duplicate bytes count once, never as execution."""
    return _compose_details(input_paths, capacity=capacity)[0]


def _derive_additive(inputs, capacity, stages):
    """Replay explicit selection history from complete, unmodified originals.

    The contribution bound limits selected metadata, not omitted overlap. Raw
    file/count/union bounds still apply to every original, including zero-novelty
    additions. Stage order is semantic; argument order within a stage is not.
    """
    if not isinstance(inputs, list) or not inputs:
        raise ValueError(f'Profile requires one to {MAX_INPUTS} distinct inputs')
    if len(inputs) > MAX_INPUTS:
        raise ValueError('Observation input capacity exceeded')
    sources = {}
    total_bytes = 0
    for source in inputs:
        if not isinstance(source, dict) or set(source) != {'sha256', 'size_bytes', 'raw_base64'}:
            raise ValueError('Invalid observation input provenance fields')
        digest = _digest(source['sha256'])
        if digest in sources:
            raise ValueError('Duplicate observation input SHA256')
        sources[digest] = source
    if list(sources) != sorted(sources):
        raise ValueError('Profile input provenance must be in canonical SHA256 order')
    if not isinstance(stages, list) or not 1 <= len(stages) <= MAX_INPUTS:
        raise ValueError('Additive selection requires nonempty bounded stages')
    used = set()
    for stage in stages:
        if (not isinstance(stage, list) or not 1 <= len(stage) <= len(sources)
                or len(used)+len(stage) > len(sources)):
            raise ValueError('Additive selection stages must be nonempty lists')
        for digest in stage:
            _digest(digest)
        if stage != sorted(set(stage)) or used.intersection(stage) or not set(stage) <= sources.keys():
            raise ValueError('Additive stages require canonical disjoint input identities')
        used.update(stage)
    if used != sources.keys():
        raise ValueError('Additive stages must account for every original input')
    union, metadata = {}, []
    totals = dict(native_hits=0, interpreted_hits=0, retired_instructions=0)
    original_count = selected_count = 0
    for index, stage in enumerate(stages):
        for digest in stage:
            source = sources[digest]
            size = integer(source['size_bytes'], MAX_CAPTURE_BYTES, 'input byte size', 1)
            total_bytes += size
            if total_bytes > MAX_TOTAL_INPUT_BYTES:
                raise ValueError('Total original capture bytes exceed profile limit')
            encoded = source['raw_base64']
            if not isinstance(encoded, str) or len(encoded) != 4 * ((size + 2) // 3):
                raise ValueError('Input base64 length disagrees with original byte size')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError('Invalid original capture base64') from exc
            if (len(raw) != size or base64.b64encode(raw).decode('ascii') != encoded
                    or hashlib.sha256(raw).hexdigest() != digest):
                raise ValueError('Original capture SHA256, size or canonical base64 disagrees')
            capture = _json(raw)
            decoded = validate_capture(capture)
            if not capture['complete']:
                raise ValueError('Observation profiles require complete lossless inputs')
            original_count += len(decoded)
            native = sum(item['native_hits'] for item in decoded)
            interpreted = sum(item['interpreted_hits'] for item in decoded)
            for key, value in (('native_hits', native), ('interpreted_hits', interpreted),
                               ('retired_instructions', capture['retired_instructions'])):
                totals[key] = _add(totals[key], value, 'historical '+key)
            detail = {key: value for key, value in capture.items() if key != 'observations'}
            detail.update(sha256=digest, size_bytes=size, native_hits=native,
                          interpreted_hits=interpreted, observation_count=len(decoded))
            metadata.append(detail)
            for item in decoded:
                key = (item['pc'], tuple(item['mpr']), tuple(item['data']))
                # Stages and their inputs are ordered, so the first later-stage
                # contributor encountered is exactly its lowest-SHA owner.
                if index and key in union:
                    continue
                selected_count += 1
                if selected_count > MAX_CONTRIBUTIONS:
                    raise ValueError('Observation contribution capacity exceeded')
                if key not in union:
                    if len(union) >= capacity:
                        raise ValueError('Observation union capacity exceeded; no identities dropped')
                    union[key] = {name: list(item[name]) if name in ('mpr', 'physical', 'data') else item[name]
                                  for name in ('pc', 'mpr', 'physical', 'data')}
                    union[key].update(native_hits=0, interpreted_hits=0, contributions=[])
                entry = union[key]
                for tier in ('native_hits', 'interpreted_hits'):
                    entry[tier] = _add(entry[tier], item[tier], 'union '+tier)
                _add(entry['native_hits'], entry['interpreted_hits'], 'union total hits')
                entry['contributions'].append(dict(input_sha256=digest,
                    native_hits=item['native_hits'], interpreted_hits=item['interpreted_hits']))
    _add(totals['native_hits'], totals['interpreted_hits'], 'historical total hits')
    if totals['native_hits'] + totals['interpreted_hits'] != totals['retired_instructions']:
        raise ValueError('Historical retirement sum disagrees')
    ordered = sorted(union.values(), key=lambda item: (item['mpr'], item['pc'], item['data']))
    for item in ordered:
        item['contributions'].sort(key=lambda contribution: contribution['input_sha256'])
    native = sum(item['native_hits'] for item in ordered)
    interpreted = sum(item['interpreted_hits'] for item in ordered)
    selected_totals = dict(native_hits=native, interpreted_hits=interpreted,
                           retired_instructions=_add(native, interpreted, 'selected total hits'))
    counts = dict(original_contributions=original_count, selected_contributions=selected_count,
                  omitted_contributions=original_count-selected_count)
    return ordered, totals, sorted(metadata, key=lambda item: item['sha256']), selected_totals, counts


def _compose_additive_details(input_paths, *, baseline_inputs=(), baseline_profile=None, capacity=None):
    from itertools import islice

    baseline = list(islice(iter(baseline_inputs), MAX_INPUTS + 1))
    additions = list(islice(iter(input_paths), MAX_INPUTS + 1))
    if baseline_profile is not None and baseline:
        raise ValueError('Choose baseline original inputs or a baseline profile, not both')
    path_count = len(baseline) + len(additions) + (baseline_profile is not None)
    if path_count > MAX_INPUTS:
        raise ValueError(f'At most {MAX_INPUTS} input paths are accepted')
    artifact = None
    if baseline_profile is not None:
        with Path(baseline_profile).open('rb') as stream:
            baseline_raw = stream.read(MAX_PROFILE_BYTES + 1)
        if len(baseline_raw) > MAX_PROFILE_BYTES:
            raise ValueError('Observation profile exceeds 128 MiB')
        prior = _json(baseline_raw)
        _validate(prior)
        artifact = dict(sha256=hashlib.sha256(baseline_raw).hexdigest(), size_bytes=len(baseline_raw))
        chosen_capacity = prior['capacity'] if capacity is None else capacity
        stages = ([list(stage) for stage in prior['selection_stages']] if prior['schema'] == 2
                  else [[item['sha256'] for item in prior['inputs']]])
        sources = {item['sha256']: dict(item) for item in prior['inputs']}
        argument_digests = []
    else:
        if not baseline:
            raise ValueError('Additive composition requires an explicit nonempty baseline')
        chosen_capacity = MAX_OBSERVATIONS if capacity is None else capacity
        prior, argument_digests, _ = _compose_details(baseline, capacity=chosen_capacity)
        stages = [[item['sha256'] for item in prior['inputs']]]
        sources = {item['sha256']: dict(item) for item in prior['inputs']}
    integer(chosen_capacity, MAX_OBSERVATIONS, 'profile capacity', 1)
    base_digests = set(sources)
    raw_bytes = sum(item['size_bytes'] for item in sources.values())
    for path in additions:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_CAPTURE_BYTES + 1)
        if len(raw) > MAX_CAPTURE_BYTES:
            raise ValueError('Code capture exceeds 64 MiB')
        digest = hashlib.sha256(raw).hexdigest()
        argument_digests.append(digest)
        if digest in sources:
            continue
        if len(sources) >= MAX_INPUTS:
            raise ValueError('Observation input capacity exceeded')
        raw_bytes += len(raw)
        if raw_bytes > MAX_TOTAL_INPUT_BYTES:
            raise ValueError('Total original capture bytes exceed profile limit')
        sources[digest] = dict(sha256=digest, size_bytes=len(raw),
                               raw_base64=base64.b64encode(raw).decode('ascii'))
    new_stage = sorted(sources.keys()-base_digests)
    if new_stage:
        stages.append(new_stage)
    inputs = [sources[key] for key in sorted(sources)]
    observations, totals, metadata, selected_totals, counts = _derive_additive(inputs, chosen_capacity, stages)
    profile = dict(format=ADDITIVE_FORMAT, schema=2, execution_evidence=False, capacity=chosen_capacity,
                   inputs=inputs, observations=observations, historical_totals=totals,
                   selection_stages=stages, selected_historical_totals=selected_totals,
                   selection_counts=counts)
    if len(_canonical(profile)) > MAX_PROFILE_BYTES:
        raise ValueError('Observation profile exceeds 128 MiB')
    return profile, argument_digests, metadata, prior, artifact, path_count


def compose_additive_observation_profile(input_paths, *, baseline_inputs=(), baseline_profile=None,
                                          capacity=None):
    """Select only novel identities, retaining immutable staged raw provenance.

    A profile baseline preserves its stages and declared capacity by default.
    An explicit capacity can change the bound, but never removes retained keys.
    The caller must retain exact original files/profile and actual-run evidence.
    """
    return _compose_additive_details(input_paths, baseline_inputs=baseline_inputs,
        baseline_profile=baseline_profile, capacity=capacity)[0]


def serialize_observation_profile(profile):
    """Exact established CLI bytes, bounded before accumulating excess output.

    Admission belongs to the composer/loader. This serializer does not grant
    validity to a caller-supplied object or rewrite an existing profile file.
    """
    encoder = json.JSONEncoder(sort_keys=True, indent=2, allow_nan=False)
    with io.BytesIO() as stream:
        for chunk in encoder.iterencode(profile):
            raw = chunk.encode('utf-8')
            if stream.tell() + len(raw) > MAX_PROFILE_BYTES:
                raise ValueError('Serialized observation profile exceeds its byte bound')
            stream.write(raw)
        if stream.tell() + 1 > MAX_PROFILE_BYTES:
            raise ValueError('Serialized observation profile exceeds its byte bound')
        stream.write(b'\n')
        return stream.getvalue()


def _plan_producer():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('observations.py', 'capture.py', 'isa.py', 'abi.py')}


def _plan_metrics(profile=None):
    if profile is None:
        return dict(unique_inputs=0, union_identities=0, contributions=0,
                    raw_bytes=0, serialized_bytes=0, serialized_sha256=None)
    return dict(unique_inputs=len(profile['inputs']), union_identities=len(profile['observations']),
                contributions=sum(len(row['contributions']) for row in profile['observations']),
                raw_bytes=sum(row['size_bytes'] for row in profile['inputs']),
                serialized_bytes=None, serialized_sha256=None)


def _baseline_profile(profile, digests):
    """Subset already admitted original contributions; never a raw capture."""
    rows = []
    for row in profile['observations']:
        contributions = [item for item in row['contributions'] if item['input_sha256'] in digests]
        if contributions:
            item = {key: row[key] for key in ('pc', 'mpr', 'physical', 'data')}
            item.update(native_hits=sum(x['native_hits'] for x in contributions),
                        interpreted_hits=sum(x['interpreted_hits'] for x in contributions),
                        contributions=contributions)
            rows.append(item)
    native = sum(row['native_hits'] for row in rows)
    interpreted = sum(row['interpreted_hits'] for row in rows)
    return dict(format=FORMAT, schema=1, execution_evidence=False, capacity=profile['capacity'],
                inputs=[item for item in profile['inputs'] if item['sha256'] in digests],
                observations=rows,
                historical_totals=dict(native_hits=native, interpreted_hits=interpreted,
                                       retired_instructions=native + interpreted))


def _plan_refusal(error, capacity):
    text = str(error)
    if text.startswith('Profile requires one to '):
        return dict(code='no_inputs', resource='unique_inputs', limit=MAX_INPUTS,
                    minimum_allowed=1, exact_required=0, required_at_least=None)
    limits = (
        ('At most ', 'input_paths', MAX_INPUTS),
        ('Observation input capacity exceeded', 'unique_inputs', MAX_INPUTS),
        ('Code capture exceeds 64 MiB', 'individual_raw_bytes', MAX_CAPTURE_BYTES),
        ('Total original capture bytes exceed profile limit', 'raw_bytes', MAX_TOTAL_INPUT_BYTES),
        ('Observation contribution capacity exceeded', 'contributions', MAX_CONTRIBUTIONS),
        ('Observation union capacity exceeded', 'union_identities', capacity),
        ('Observation profile exceeds 128 MiB', 'serialized_bytes', MAX_PROFILE_BYTES),
        ('Serialized observation profile exceeds its byte bound', 'serialized_bytes', MAX_PROFILE_BYTES),
    )
    for prefix, resource, limit in limits:
        if text.startswith(prefix):
            # No traversal beyond the admission cap merely to measure a refusal.
            return dict(code='admission_bound', resource=resource, limit=limit,
                        required_at_least=limit + 1, exact_required=None)
    return dict(code='input_admission', resource=None, limit=None, required_at_least=None,
                exact_required=None, error_type=type(error).__name__,
                message='Inputs or options did not satisfy the existing composition contract')


def plan_observation_profile(input_paths, *, baseline_inputs=(), capacity=MAX_OBSERVATIONS):
    """Read-only additive plan using the real admissions and CLI serializer.

    ``baseline_inputs`` explicitly names retained original captures. Positional
    inputs are additions, including duplicates. Every reported SHA binds the
    exact bytes read; compare the planned serialized hash with eventual output.
    Unknown refusal metrics stay null. This is neither execution authentication
    nor an equivalence proof and never emits code or a profile file.
    """
    from collections import Counter
    from itertools import islice

    unknown = {key: None for key in _plan_metrics()}
    union_limit = capacity if type(capacity) is int and 1 <= capacity <= MAX_OBSERVATIONS else MAX_OBSERVATIONS
    report = dict(schema=1, kind='observation-composition-plan', profile_format=FORMAT,
                  execution_evidence=False, equivalence_evidence=False, profile_payload_included=False,
                  serializer=dict(id=SERIALIZER, encoding='utf-8', sort_keys=True, indent=2,
                                  ensure_ascii=True, final_newline='LF'),
                  producer_source_sha256=None, baseline_policy='explicit original capture inputs',
                  limits=dict(input_paths=MAX_INPUTS, unique_inputs=MAX_INPUTS,
                              individual_raw_bytes=MAX_CAPTURE_BYTES, raw_bytes=MAX_TOTAL_INPUT_BYTES,
                              union_identities=union_limit, contributions=MAX_CONTRIBUTIONS,
                              serialized_bytes=MAX_PROFILE_BYTES),
                  input_paths=None, existing_inputs=None, new_inputs=None, duplicate_shas=None,
                  baseline=dict(unknown), combined=dict(unknown), additive=dict(unknown),
                  headroom=None, fits=False, refusal=None,
                  scope='Point-in-time catalogue admission and exact selected serialization only; overlapping sessions remain historical input contributions')
    try:
        report['producer_source_sha256'] = _plan_producer()
        # A bounded materialization also handles lazy/infinite path iterables.
        baseline = list(islice(iter(baseline_inputs), MAX_INPUTS + 1))
        additions = list(islice(iter(input_paths), MAX_INPUTS + 1))
        if len(baseline) + len(additions) > MAX_INPUTS:
            raise ValueError(f'At most {MAX_INPUTS} input paths are accepted')
        report['input_paths'] = len(baseline) + len(additions)
        profile, args, metadata = _compose_details(baseline + additions, capacity=capacity)
        base = set(args[:len(baseline)])
        all_inputs = {item['sha256'] for item in profile['inputs']}
        # Metadata deliberately omits code bytes, PC/MPR rows and hit payloads.
        sources = {item['sha256']: {key: item[key] for key in
                   ('sha256', 'size_bytes', 'runtime_abi', 'checkpoint_origin', 'execution_policy') if key in item}
                   for item in metadata}
        report['existing_inputs'] = [sources[key] for key in sorted(base)]
        report['new_inputs'] = [sources[key] for key in sorted(all_inputs - base)]
        report['duplicate_shas'] = [dict(sha256=key, argument_count=count, duplicate_arguments=count - 1)
                                   for key, count in sorted(Counter(args).items()) if count > 1]
        report['combined'] = _plan_metrics(profile)
        prior = _baseline_profile(profile, base) if base else None
        report['baseline'] = _plan_metrics(prior)
        if prior is not None:
            raw = serialize_observation_profile(prior)
            report['baseline'].update(serialized_bytes=len(raw), serialized_sha256=hashlib.sha256(raw).hexdigest())
        raw = serialize_observation_profile(profile)
        report['combined'].update(serialized_bytes=len(raw), serialized_sha256=hashlib.sha256(raw).hexdigest())
        report['fits'] = True
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['refusal'] = _plan_refusal(error, capacity)
    finally:
        for key in ('unique_inputs', 'union_identities', 'contributions', 'raw_bytes', 'serialized_bytes'):
            old, new = report['baseline'][key], report['combined'][key]
            report['additive'][key] = new - old if old is not None and new is not None else None
        report['additive'].pop('serialized_sha256')
        report['headroom'] = {key: (report['limits'][key] - value if value is not None else None)
                              for key, value in report['combined'].items() if key in report['limits']}
        report['headroom']['input_paths'] = (MAX_INPUTS - report['input_paths']
                                           if report['input_paths'] is not None else None)
        report['headroom']['individual_raw_bytes'] = (MAX_CAPTURE_BYTES - max(
            (row['size_bytes'] for row in (report['existing_inputs'] or []) + (report['new_inputs'] or [])), default=0)
            if report['new_inputs'] is not None else None)
        if report['producer_source_sha256'] is not None:
            try:
                current_source = _plan_producer()
            except OSError:
                report['fits'] = False
                report['refusal'] = dict(code='producer_unavailable', message='Planner source could not be rebound')
            else:
                if report['producer_source_sha256'] != current_source:
                    report['fits'] = False
                    report['refusal'] = dict(code='producer_changed', message='Planner source changed during admission')
    return report


def _additive_plan_metrics(profile=None):
    result = _plan_metrics(profile)
    result['original_contributions'] = (profile['selection_counts']['original_contributions']
        if profile is not None and profile['schema'] == 2 else result['contributions'])
    result['omitted_contributions'] = result['original_contributions']-result['contributions']
    return result


def plan_additive_observation_profile(input_paths, *, baseline_inputs=(), baseline_profile=None,
                                     capacity=None):
    """Code-free exact preflight for the staged additive composer, without writes.

    Full raw history and selected contribution costs are separate. The original
    baseline artifact SHA is an operation binding, not a claimed parent embedded
    in a self-contained profile. Composition re-admits the inputs independently.
    """
    from collections import Counter

    unknown = {key: None for key in _additive_plan_metrics()}
    union_limit = capacity if type(capacity) is int and 1 <= capacity <= MAX_OBSERVATIONS else MAX_OBSERVATIONS
    report = dict(schema=1, kind='additive-observation-composition-plan', profile_format=ADDITIVE_FORMAT,
        execution_evidence=False, equivalence_evidence=False, profile_payload_included=False,
        serializer=dict(id=SERIALIZER, encoding='utf-8', sort_keys=True, indent=2,
                        ensure_ascii=True, final_newline='LF'),
        producer_source_sha256=None, baseline_policy='explicit original captures or an admitted staged profile',
        baseline_artifact=None, selection_policy=SELECTION_POLICY,
        limits=dict(input_paths=MAX_INPUTS, unique_inputs=MAX_INPUTS,
            individual_raw_bytes=MAX_CAPTURE_BYTES, raw_bytes=MAX_TOTAL_INPUT_BYTES,
            union_identities=union_limit, contributions=MAX_CONTRIBUTIONS,
            serialized_bytes=MAX_PROFILE_BYTES),
        input_paths=None, existing_inputs=None, new_inputs=None, duplicate_shas=None,
        baseline=dict(unknown), combined=dict(unknown), additive=dict(unknown),
        headroom=None, fits=False, refusal=None,
        scope='Selected catalogue admission only; full original history remains historical, not deduplicated execution')
    try:
        report['producer_source_sha256'] = _plan_producer()
        profile, args, metadata, prior, artifact, path_count = _compose_additive_details(input_paths,
            baseline_inputs=baseline_inputs, baseline_profile=baseline_profile, capacity=capacity)
        report['baseline_artifact'] = artifact
        report['input_paths'] = path_count
        report['limits']['union_identities'] = profile['capacity']
        base = {item['sha256'] for item in prior['inputs']}
        sources = {item['sha256']: {key: item[key] for key in
            ('sha256', 'size_bytes', 'runtime_abi', 'checkpoint_origin', 'execution_policy') if key in item} for item in metadata}
        report['existing_inputs'] = [sources[key] for key in sorted(base)]
        report['new_inputs'] = [sources[key] for key in sorted(sources.keys()-base)]
        report['duplicate_shas'] = [dict(sha256=key, argument_count=count, duplicate_arguments=count-1)
            for key, count in sorted(Counter(args).items()) if count > 1]
        for name, selected in (('baseline', prior), ('combined', profile)):
            report[name] = _additive_plan_metrics(selected)
            raw = serialize_observation_profile(selected)
            report[name].update(serialized_bytes=len(raw), serialized_sha256=hashlib.sha256(raw).hexdigest())
        report['fits'] = True
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['refusal'] = _plan_refusal(error, report['limits']['union_identities'])
    finally:
        for key in _additive_plan_metrics():
            if key == 'serialized_sha256':
                continue
            old, new = report['baseline'][key], report['combined'][key]
            report['additive'][key] = new-old if old is not None and new is not None else None
        report['additive'].pop('serialized_sha256')
        report['headroom'] = {key: report['limits'][key]-value if value is not None else None
            for key, value in report['combined'].items() if key in report['limits']}
        report['headroom']['input_paths'] = (MAX_INPUTS-report['input_paths']
            if report['input_paths'] is not None else None)
        report['headroom']['individual_raw_bytes'] = (MAX_CAPTURE_BYTES-max(
            (row['size_bytes'] for row in (report['existing_inputs'] or [])+(report['new_inputs'] or [])), default=0)
            if report['new_inputs'] is not None else None)
        if report['producer_source_sha256'] is not None:
            try:
                current_source = _plan_producer()
            except OSError:
                report['fits'] = False
                report['refusal'] = dict(code='producer_unavailable', message='Planner source could not be rebound')
            else:
                if report['producer_source_sha256'] != current_source:
                    report['fits'] = False
                    report['refusal'] = dict(code='producer_changed', message='Planner source changed during admission')
    return report


def _validate(profile):
    fields = {'format', 'schema', 'execution_evidence', 'capacity', 'inputs',
              'observations', 'historical_totals'}
    additive = isinstance(profile, dict) and profile.get('format') == ADDITIVE_FORMAT
    if additive:
        fields |= {'selection_stages', 'selected_historical_totals', 'selection_counts'}
    if not isinstance(profile, dict) or set(profile) != fields:
        raise ValueError('Invalid observation profile fields')
    if ((profile['format'] != ADDITIVE_FORMAT if additive else profile['format'] != FORMAT)
            or type(profile['schema']) is not int or profile['schema'] != (2 if additive else 1)):
        raise ValueError('Unsupported observation profile format/schema')
    if profile['execution_evidence'] is not False:
        raise ValueError('An observation profile is not execution evidence')
    capacity = integer(profile['capacity'], MAX_OBSERVATIONS, 'profile capacity', 1)
    observations = profile['observations']
    if not isinstance(observations, list) or len(observations) > capacity:
        raise ValueError('Observation union capacity exceeded')
    if len(_canonical(profile)) > MAX_PROFILE_BYTES:
        raise ValueError('Observation profile exceeds 128 MiB')
    if additive:
        expected, totals, metadata, selected_totals, counts = _derive_additive(
            profile['inputs'], capacity, profile['selection_stages'])
        if _canonical(profile['selected_historical_totals']) != _canonical(selected_totals):
            raise ValueError('Profile selected historical totals disagree with selected originals')
        if _canonical(profile['selection_counts']) != _canonical(counts):
            raise ValueError('Profile selection counts disagree with original captures')
    else:
        expected, totals, metadata = _derive(profile['inputs'], capacity)
    if [item['sha256'] for item in profile['inputs']] != sorted(item['sha256'] for item in profile['inputs']):
        raise ValueError('Profile input provenance must be in canonical SHA256 order')
    # JSON comparison preserves strict numeric types (True and 1 are different).
    if _canonical(observations) != _canonical(expected):
        raise ValueError('Profile observations/contributions disagree with original captures')
    if _canonical(profile['historical_totals']) != _canonical(totals):
        raise ValueError('Profile historical totals disagree with original captures')
    # Decode translation reports without manufacturing a singular capture ABI.
    decoded = []
    for item in expected:
        pc, data, mpr = item['pc'], item['data'], tuple(item['mpr'])
        ins = decode(lambda address: data[(address - pc) & 65535], pc, mpr)
        decoded.append(ins.report() | {'mpr': mpr, 'native_hits': item['native_hits'],
                                       'interpreted_hits': item['interpreted_hits']})
    return decoded, metadata


def _profile_accounting(profile):
    """Manifest facts for a profile already strictly admitted by the caller."""
    result = dict(historical_totals=dict(profile['historical_totals']),
        historical_count_policy='sum of distinct raw inputs; overlapping execution windows are not deduplicated')
    if profile['schema'] == 2:
        result.update(selection_stages=[list(stage) for stage in profile['selection_stages']],
            selected_historical_totals=dict(profile['selected_historical_totals']),
            selection_counts=dict(profile['selection_counts']), selection_policy=SELECTION_POLICY)
    return result


def validate_observation_profile(profile):
    """Return decoded canonical identities, after rehashing all original inputs."""
    return _validate(profile)[0]


def observation_profile_provenance(profile):
    """Return exact original per-input metadata, without embedding source bytes."""
    return _validate(profile)[1]


def load_observation_profile_details(path):
    """Load exact bytes and return decoded identities/provenance from one admission.

    The additional results are derived from hash-verified raw capture inputs,
    never trusted profile-supplied instruction or provenance summaries.
    """
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_PROFILE_BYTES + 1)
    if len(raw) > MAX_PROFILE_BYTES:
        raise ValueError('Observation profile exceeds 128 MiB')
    profile = _json(raw)
    instructions, provenance = _validate(profile)
    return profile, hashlib.sha256(raw).hexdigest(), instructions, provenance


def load_observation_profile(path):
    profile, digest, _, _ = load_observation_profile_details(path)
    return profile, digest
