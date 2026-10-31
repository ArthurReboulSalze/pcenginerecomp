# Frame-step replay and progress observations

`scripts.dev_steps` is a pure, explicit admission profile for a single paused
`step_frames` operation. It separates timing-dependent progress polls from the
actual settled endpoint. It sends nothing, authorizes no memory edit, and
never retries a request. Runtime ABI 26 and checkpoint schema 1 are unchanged.

## Why raw polling is not a replay target

`DevClient.advance` queues a frame count and polls `status` until it observes
a paused machine at or beyond the returned target. A faster native build can
produce fewer intermediate polls and different intermediate CPU/device states.
Those observations are retained evidence, not exact cross-build checkpoints.

The requested target and observed completion frame are separate. A whole
instruction, particularly a block transfer, can finish beyond a requested
frame. Bind the actual paused endpoint and an explicit overshoot allowance;
do not assume that completion equals the requested target.

## API

```python
from scripts.dev_steps import seal_step, admit_step

bounds = dict(
    max_polls=1000,
    max_tick_delta=1_000_000_000,
    max_elapsed_ns=120_000_000_000,
    max_frame_overshoot=16,
)
reference = seal_step(
    baseline_before, baseline_step_request, baseline_step_ack,
    baseline_poll_pairs, bounds=bounds,
)
proof = admit_step(
    reference, candidate_before, candidate_step_request, candidate_step_ack,
    candidate_poll_pairs, elapsed_ns=measured_candidate_elapsed_ns,
)
```

These limits are examples, not inferred hardware or route limits. Choose and
seal finite bounds for the reviewed recipe before candidate execution. Polls
are a finite list or tuple of dictionaries with exactly `request` and
`response`, containing the parsed objects from the original wire ledger.
Process one step at a time and stream the route outside the helper.

The step request contains exactly `id`, `cmd="step_frames"` and `frames`
(1..600). Its successful ACK must pair with that ID and return exactly the
target `before.frame + frames`. Pending poll IDs must be consecutive; only
successful `status` pairs may occur before completion. Other reads, controls,
writes, nested steps, gaps, local-pause interruption and trailing polls are
refused. This prevents an omitted intervening request from becoming an
apparently read-only progress interval within the declared session.
The initial status ID only has to precede the step ID; paused input/control
requests may lie between them. The caller must separately verify that interval
and bind the pre-step anchor to its sealed command sequence. Pending-phase
contiguity alone does not authenticate the earlier state or those commands.

Frames and ticks must be monotonic and inside the declared envelope. An
unpaused poll must remain below the requested frame target. The first paused
completion must reach it within the declared overshoot bound and advance
guest ticks. Candidate admission requires the same starting frame/ticks,
literal frame count, queued target and actual final paused frame/ticks as the
reference. Intermediate poll counts and CPU/device values may differ; no
projection makes them pretend to be equal.

## Timing, bootstrap and source identity

The existing wire-journal schema has no wall timestamps. Sealing with
`elapsed_ns=None` explicitly records `deadline_observed=False`; a finite
declared limit is not a measured duration. Candidate admission requires a
caller-supplied nonnegative duration within that limit. Bind its actual
monotonic-clock measurement and controller deadline separately. The pure
helper cannot authenticate a supplied number or preempt a blocked OS call.

`initial_observation="frame-zero-bootstrap"` is available only when both
initial frame and guest ticks are zero. It is never inferred from an ABI or
silently substituted for `settled`. It labels an initial pump observation;
it does not grant a host-field allowance or prove complete machine quiescence.

Pin the helper's actual source bytes and imported path independently. Like
other diagnostic scripts, it is outside `project.source_identity`'s narrower
runtime/compiler digest. It uses only the Python standard library, so a
consumer can source-only load this separately pinned helper alongside an
older diagnostic bundle. Follow the [consumer import guidance](PAUSED_WRITES.md#adopting-the-relation-in-a-consumer).

## What the proof establishes

The seal preserves complete parsed evidence plus compact progress IDs,
frame/tick values and canonical status digests. Its evidence digest refers to
canonical parsed JSON, **not exact wire bytes**. Admission reconstructs the
reference and compares its summary/digest rather than trusting supplied flags.
Retain an externally trusted hash of the seal and original closed journal;
self-consistency is not authentication of a machine, session or observation.

`endpoint_guest_state_compared=False` and
`progress_guest_state_compared=False` are intentional. A passing cadence
proof does not compare CPU registers, all MPRs, fetched bytes/generations,
native/interpreted counters, device state, RAM, images, audio or build identity.
The complete initial/final statuses remain available for the consumer's
separate strict migration comparison. Explicitly prove any tier conversion
and narrowly checked host-local differences; do not delete entire host or
checkpoint subtrees. [Paused observations](PAUSED_OBSERVATIONS.md),
[typed writes](PAUSED_WRITES.md), source capture and candidate-owned
[checkpoint tests](DEVELOPER_CHECKPOINTS.md) retain their separate contracts.

Twenty authored tests cover both accepted cadence differences and refusals.
Two use actual loopback protocol servers, `DevClient.advance`, and retained
wire journals. These synthetic protocol checks contain no retail input and
make no game, native-CPU, hardware or listening claim.

A separate authored headless TCP fixture demonstrates real whole-instruction
overshoot: a request for frame 1 completes at frame 13 after an identity-copy
65,536-byte TII. It executes six interpreted instructions, zero native, and
4,719,000 guest ticks. A fresh process restores its starting checkpoint,
reserializes it identically, repeats the step and admits the exact same
frame/tick endpoint. Complete continued checkpoint files and core payloads
match byte for byte. Both owned hosts quit naturally. This synthetic sandbox
test uses no retail input and is separate from Ys III migration evidence.
