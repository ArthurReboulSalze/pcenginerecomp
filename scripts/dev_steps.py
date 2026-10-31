"""Pure admission of one bounded frame step and its progress observations.

Status polls made while a step is running depend on host scheduling. Their
number and intermediate CPU/device state are not deterministic replay points.
This module validates a finite progress envelope and an exact final frame/tick
endpoint, retaining parsed observations without normalizing their guest state.
The consumer separately compares final guest state, source, RAM, images and
audio under its explicitly reviewed runtime/tier contract.

Use one step at a time; stream a route outside this helper. The evidence digest
binds canonical parsed JSON, not exact wire bytes, origin, process success or
the fact that requests occurred. Bind the original closed journal separately.
Elapsed time is caller-supplied monotonic evidence. A legacy journal without
timestamps cannot establish elapsed time: sealing with None records that limit
as declared only. Candidate admission requires a supplied elapsed measurement.
No function here sends, retries, authorizes a CAS or changes a guest machine.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

MAX_COUNTER = (1 << 64) - 1
MAX_REQUEST_ID = (1 << 53) - 1
MAX_POLLS = 1_000_000
# The same per-object protocol bounds as dev_client, without importing its
# scripts namespace. Canonical JSON can be larger than the original encoding;
# this is a conservative parsed-object admission profile, not all wire frames.
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 17 * 1024 * 1024
_EVIDENCE_FIELDS = frozenset(("before_status", "step_request", "step_ack", "polls",
                              "bounds", "elapsed_ns", "initial_observation"))
_BOUND_FIELDS = frozenset(("max_polls", "max_tick_delta", "max_elapsed_ns",
                          "max_frame_overshoot"))


class StepValidationError(ValueError):
    """The retained objects do not establish the declared step relation."""


def _require(condition, message):
    if not condition:
        raise StepValidationError(message)


def _integer(value, low, high, name):
    _require(type(value) is int and low <= value <= high,
             name + ": exact bounded integer required")
    return value


def _plain(value, active):
    kind = type(value)
    if kind in (type(None), bool, int, str):
        return
    if kind is float:
        _require(math.isfinite(value), "nonfinite parsed JSON value")
        return
    _require(kind in (dict, list), "plain finite JSON values required")
    identity = id(value)
    _require(identity not in active, "cyclic parsed JSON value")
    active.add(identity)
    try:
        if kind is dict:
            _require(all(type(key) is str for key in value), "JSON object keys must be strings")
            children = value.values()
        else:
            children = value
        for child in children:
            _plain(child, active)
    finally:
        active.remove(identity)


def _encoded(value, maximum, label):
    try:
        _plain(value, set())
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                         separators=(",", ":")).encode("ascii")
    except (RecursionError, ValueError, OverflowError) as error:
        if isinstance(error, StepValidationError):
            raise
        raise StepValidationError(label + ": unsupported JSON encoding") from error
    _require(len(raw) <= maximum, label + ": parsed object exceeds protocol bound")
    return raw


def _digest(value):
    """Hash already validated plain JSON without another whole-evidence buffer."""
    digest = hashlib.sha256()
    try:
        for part in json.JSONEncoder(ensure_ascii=True, allow_nan=False, sort_keys=True,
                                     separators=(",", ":")).iterencode(value):
            digest.update(part.encode("ascii"))
    except (RecursionError, ValueError, OverflowError) as error:
        raise StepValidationError("unsupported evidence encoding") from error
    return digest.hexdigest()


def _fields(value, expected, label):
    _require(type(value) is dict and value.keys() == expected,
             label + ": exact fields required")


def _status(value, label):
    raw = _encoded(value, MAX_RESPONSE_BYTES, label)
    _require(type(value) is dict, label + ": status object required")
    identity = _integer(value.get("id"), 1, MAX_REQUEST_ID, label + ".id")
    _require(value.get("ok") is True, label + ": successful boolean ACK required")
    frame = _integer(value.get("frame"), 0, MAX_COUNTER, label + ".frame")
    ticks = _integer(value.get("ticks"), 0, MAX_COUNTER, label + ".ticks")
    _require(type(value.get("paused")) is bool, label + ": boolean pause required")
    _require(value.get("local_paused") is False,
             label + ": local pause interruption is unsupported")
    _require(type(value.get("host")) is dict, label + ": host object required")
    return identity, frame, ticks, value["paused"], hashlib.sha256(raw).hexdigest()


def _bounds(value):
    _fields(value, _BOUND_FIELDS, "bounds")
    _integer(value["max_polls"], 1, MAX_POLLS, "max_polls")
    _integer(value["max_tick_delta"], 1, MAX_COUNTER, "max_tick_delta")
    _integer(value["max_elapsed_ns"], 1, MAX_COUNTER, "max_elapsed_ns")
    _integer(value["max_frame_overshoot"], 0, MAX_COUNTER, "max_frame_overshoot")


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def seal_step(before_status, step_request, step_ack, polls, *, bounds,
              elapsed_ns=None, initial_observation="settled"):
    """Seal exactly one step and its first paused completion.

    ``polls`` is a finite list/tuple of parsed ``{request, response}`` pairs.
    Only contiguous status request IDs may follow the step ACK, so a missing
    pending request or an intervening mutation cannot be silently omitted.
    The caller must bind all objects to one actual journal/session; IDs alone
    do not authenticate that provenance. Unknown status fields remain present
    in the evidence and hashes, without being compared as transient state.

    Bounds explicitly limit polls, new guest ticks, elapsed nanoseconds and
    whole-instruction frame overshoot. ``elapsed_ns=None`` means that elapsed
    time was not supplied, not that a wall deadline was proved. No timestamps
    are invented from frame counts or a timestamp-free legacy journal.
    ``frame-zero-bootstrap`` must be selected explicitly for a frame/tick-zero
    pump observation; it grants no host-presentation comparison allowance.

    The result retains full parsed evidence plus a compact progress summary.
    It is self-consistency evidence, not a signature: retain an externally
    bound hash of the seal/raw journal before relying on it for replay.
    """
    _bounds(bounds)
    _require(type(initial_observation) is str and initial_observation in
             ("settled", "frame-zero-bootstrap"), "explicit supported initial observation required")
    before_id, start_frame, start_ticks, paused, initial_hash = _status(before_status, "before_status")
    _require(paused is True, "frame step requires a network-paused initial status")
    if initial_observation == "frame-zero-bootstrap":
        _require(start_frame == start_ticks == 0, "bootstrap observation requires frame/ticks zero")
    _encoded(step_request, MAX_REQUEST_BYTES, "step_request")
    _fields(step_request, {"id", "cmd", "frames"}, "step_request")
    step_id = _integer(step_request["id"], 1, MAX_REQUEST_ID, "step_request.id")
    _require(step_id > before_id, "step request must follow the initial status")
    _require(step_request["cmd"] == "step_frames", "literal step_frames command required")
    frames = _integer(step_request["frames"], 1, 600, "step_request.frames")
    _require(start_frame <= MAX_COUNTER - frames, "step target frame overflows")
    target = start_frame + frames
    _require(bounds["max_frame_overshoot"] <= MAX_COUNTER - target,
             "declared frame overshoot overflows")
    _encoded(step_ack, MAX_RESPONSE_BYTES, "step_ack")
    _fields(step_ack, {"id", "ok", "target_frame"}, "step_ack")
    _integer(step_ack["id"], 1, MAX_REQUEST_ID, "step_ack.id")
    _integer(step_ack["target_frame"], 0, MAX_COUNTER, "step_ack.target_frame")
    _require(step_ack["ok"] is True and step_ack["id"] == step_id
             and step_ack["target_frame"] == target, "step ACK differs from literal request/target")
    _require(type(polls) in (list, tuple) and 1 <= len(polls) <= bounds["max_polls"],
             "finite nonempty polls within declared bound required")
    if elapsed_ns is not None:
        _integer(elapsed_ns, 0, bounds["max_elapsed_ns"], "elapsed_ns")
    progress = []
    last_frame, last_ticks, previous_id = start_frame, start_ticks, step_id
    final = None
    for index, pair in enumerate(polls):
        _fields(pair, {"request", "response"}, "poll")
        request, response = pair["request"], pair["response"]
        _encoded(request, MAX_REQUEST_BYTES, "poll.request")
        _fields(request, {"id", "cmd"}, "poll.request")
        identity = _integer(request["id"], 1, MAX_REQUEST_ID, "poll.request.id")
        _require(previous_id < MAX_REQUEST_ID and identity == previous_id + 1,
                 "pending status IDs must be contiguous; a request is missing")
        _require(request["cmd"] == "status", "only status polls may occur while a step is pending")
        response_id, frame, ticks, is_paused, response_hash = _status(response, "poll.response")
        _require(response_id == identity, "poll response ID differs from request")
        _require(last_frame <= frame and last_ticks <= ticks,
                 "progress frame/ticks moved backwards")
        _require(frame <= target + bounds["max_frame_overshoot"]
                 and ticks - start_ticks <= bounds["max_tick_delta"],
                 "progress exceeds declared frame/tick envelope")
        if is_paused:
            _require(frame >= target, "step paused before requested target")
            _require(ticks > start_ticks, "completed step did not advance guest ticks")
            _require(index == len(polls) - 1, "polls follow the first paused completion")
            final = (frame, ticks, response_hash)
        else:
            _require(frame < target, "unpaused progress reached or exceeded target")
            progress.append(dict(request_id=identity, frame=frame, ticks=ticks,
                                 status_sha256=response_hash))
        last_frame, last_ticks, previous_id = frame, ticks, identity
    _require(final is not None, "step has no final paused completion")
    evidence = dict(before_status=copy.deepcopy(before_status),
        step_request=copy.deepcopy(step_request), step_ack=copy.deepcopy(step_ack),
        polls=copy.deepcopy(list(polls)), bounds=copy.deepcopy(bounds),
        elapsed_ns=elapsed_ns, initial_observation=initial_observation)
    summary = dict(start_frame=start_frame, start_ticks=start_ticks, frames=frames,
        target_frame=target, final_frame=final[0], final_ticks=final[1],
        poll_count=len(polls), progress_polls=progress,
        initial_status_sha256=initial_hash, final_status_sha256=final[2],
        elapsed_ns=elapsed_ns, deadline_observed=elapsed_ns is not None,
        endpoint_relation_checked=False)
    return dict(schema=1, kind="pce-semantic-step-1", evidence=evidence,
                evidence_sha256=_digest(evidence), summary=summary)


def _reference(value):
    try:
        _plain(value, set())
    except RecursionError as error:
        raise StepValidationError("reference nesting exceeds supported recursion") from error
    _fields(value, {"schema", "kind", "evidence", "evidence_sha256", "summary"}, "reference seal")
    _require(type(value["schema"]) is int and value["schema"] == 1
             and value["kind"] == "pce-semantic-step-1", "reference seal schema/kind differs")
    _fields(value["evidence"], _EVIDENCE_FIELDS, "reference evidence")
    evidence = value["evidence"]
    rebuilt = seal_step(evidence["before_status"], evidence["step_request"],
        evidence["step_ack"], evidence["polls"], bounds=evidence["bounds"],
        elapsed_ns=evidence["elapsed_ns"], initial_observation=evidence["initial_observation"])
    try:
        _require(_same(value, rebuilt), "reference seal differs from reconstructed evidence")
    except RecursionError as error:
        raise StepValidationError("reference nesting exceeds supported recursion") from error
    return rebuilt


def admit_step(reference_seal, before_status, step_request, step_ack, polls, *, elapsed_ns):
    """Admit a candidate cadence against a self-consistent externally bound seal.

    Candidate polls may differ in count and intermediate state. Both initial
    frame/ticks and the actual final paused frame/ticks must equal the sealed
    reference, including its observed whole-instruction overshoot. The literal
    frame count and queued target also match. A caller-provided elapsed-time
    measurement is mandatory and must obey the reference's declared bound.

    This does not compare endpoint CPU, source, guest/device state, RAM, images,
    audio, runtime identity or native/interpreted conversion. Full parsed final
    statuses remain accessible through each seal's evidence for that separately
    reviewed consumer comparison. No transient snapshot is projected into a
    fabricated baseline equality, and no CAS authority or retry is granted.
    """
    reference = _reference(reference_seal)
    _integer(elapsed_ns, 0, MAX_COUNTER, "candidate elapsed_ns")
    candidate = seal_step(before_status, step_request, step_ack, polls,
        bounds=reference["evidence"]["bounds"], elapsed_ns=elapsed_ns,
        initial_observation=reference["evidence"]["initial_observation"])
    left, right = reference["summary"], candidate["summary"]
    _require((left["start_frame"], left["start_ticks"]) ==
             (right["start_frame"], right["start_ticks"]), "candidate initial frame/ticks differ")
    _require(left["frames"] == right["frames"] and left["target_frame"] == right["target_frame"],
             "candidate literal step or target differs")
    _require((left["final_frame"], left["final_ticks"]) ==
             (right["final_frame"], right["final_ticks"]), "candidate final paused frame/ticks differ")
    return dict(schema=1, kind="pce-semantic-step-admission-1",
        reference_evidence_sha256=reference["evidence_sha256"], candidate=candidate,
        same_step_frames=True, same_target_frame=True, same_endpoint_frame_ticks=True,
        endpoint_guest_state_compared=False, progress_guest_state_compared=False)
