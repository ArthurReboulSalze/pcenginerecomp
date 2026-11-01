# State-aware development routes

`scripts/dev_route.py` runs finite, data-only plans over one persistent
`DevClient` connection. It observes a paused guest, asserts conditions, waits
with ordinary controller input, and sends bounded input pulses. It performs no
RAM writes, checkpoint loads, implicit pause/resume, expression evaluation or
dynamic code execution. This host-only helper does not change the runtime ABI
or the `pce-dev-1` protocol.

For raw client replies retained before validation and a stricter optional
status-pair interface, see [paused observations](PAUSED_OBSERVATIONS.md).
Its legacy fresh-muted audio policy is explicitly selected; the route runner's
existing presentation projection remains unchanged.

```sh
python scripts/dev_route.py --port 4370 --plan private-plan.json --receipt new-receipt.json --timeout 30
```

The receipt is reserved with exclusive creation before connecting. Existing
files are refused without contacting the guest. Invalid plans, connection
failures and execution failures produce structured failure receipts. The
process returns zero only for a successful plan. Keep title-specific plans,
addresses and receipts private, normally under `.local/`.

## Plan and API

```python
from scripts.dev_client import DevClient
from scripts.dev_route import validate_plan, run_plan

validated = validate_plan(plan)  # A validated deep copy; no host contact.
with DevClient(4370, timeout=30) as client:
    receipt = run_plan(client, validated)
assert receipt["ok"], receipt.get("error")
```

The caller owns the connection lifetime. `run_plan` returns a schema-1 receipt
on success or a handled validation, transport or route failure. It restores the
client's original timeout. All five combined input masks must be neutral on
entry; the helper observes first and then acquires and holds its own intent.
A wrapper that temporarily holds input for an observation must release its
own hold before calling `run_plan`. An initial conflict is refused before
acquisition, so the helper does not clear that pre-existing caller-owned hold.

The following authored example uses only a frame
predicate; frames are guest video boundaries, not controller polls:

```json
{
  "schema": 1,
  "max_frames": 120,
  "max_seconds": 30,
  "steps": [
    {"op": "assert", "predicate": {"status": {"path": ["paused"], "eq": true}}},
    {"op": "wait", "predicate": {"status": {"path": ["frame"], "min": 1, "max": 1000000}},
     "port": 0, "mask": 0, "poll_frames": 1, "max_frames": 60},
    {"op": "pulse", "port": 0, "mask": 8, "frames": 2}
  ]
}
```

All fields shown for each step are required. Unknown fields are rejected.
`assert` observes once and fails if its predicate is false. `wait` evaluates its
predicate **before** acquiring input or advancing. An initially satisfied wait
performs zero input changes and zero frame advances. Otherwise it holds the
specified mask, advances by at most `poll_frames`, and checks again. The final
advance is clamped to the remaining step and route frame limits. A still-false
predicate at either limit fails and stops the plan. `pulse` holds its mask for
the requested frames, then releases it; it does not assert that guest code has
sampled that mask.

Plans admit 1..256 steps, at most 256 predicate leaves across the complete plan,
and predicate nesting depth at most 16. Ports are 0..4 and masks 0..4095.
`poll_frames` and pulse `frames` are 1..600. Route `max_frames` is 0..10,000,000;
wait `max_frames` is 1..10,000,000. `max_seconds` is finite and in (0,3600].
These are safety bounds for an individual route. A pulse that cannot fit the
remaining frame allowance is refused before acquiring input. Each network
operation is capped by the remaining wall deadline and client timeout.

The whole plan is validated before any mutation. At the initial pause, a
preflight also resolves **every** planned status path/type and reads every
planned physical memory range. A bad later path or inaccessible later range
cannot allow an earlier pulse to execute. Predicate truth remains specific to
its step. Paths to optional fields must already exist with the required type
at preflight; the runner does not guess future field types.

## Predicates

Each predicate has exactly one operator:

| Operator | Fields and interpretation |
| --- | --- |
| `status` | `path` is 1..16 string keys or unsigned list indices. Use scalar `eq`, or inclusive numeric `min` and `max`. Equality requires the exact scalar type; booleans are not integers. Missing paths or wrong types fail. |
| `memory` | Physical `address` and contiguous hex `bytes`, with optional equal-length hex `mask`. Compare every byte, applying the mask to actual and expected values. Reads are 1..256 bytes. |
| `memory` | Alternatively, physical `address`, `size` (1, 2 or 4), `endian` (`little` or `big`), and inclusive unsigned integer `min`/`max`. |
| `source` | Logical `pc`, all eight byte-valued `mpr` entries, 1..7 exact hex `bytes`, and an equal-length `physical` array. Every physical byte address must match the supplied PC/MPR translation, including page crossings and wrap. Compare the complete identity against paused status instruction peeks. |
| `all`, `any` | A nonempty list of finite child predicates. Every branch is checked for invalid observations, even when another branch already determines the logical result. |

For example, these are authored memory predicates, not game addresses:

```json
{"all": [
  {"memory": {"address": 256, "bytes": "1234", "mask": "fff0"}},
  {"memory": {"address": 258, "size": 2, "endian": "little", "min": 4, "max": 20}}
]}
```

Reads use the server's paused physical RAM/ROM inspection API. MMIO, BRAM and
unsupported ranges remain refused. Source identity includes the logical PC,
complete MPR mapping and exact bytes at individually translated locations;
matching a logical PC or physical bank alone is insufficient. Unreadable source
bytes cannot satisfy an exact byte identity.

## Quiescence, input ownership and receipts

The host must already be paused through the network, without local pause, and
all five combined input masks must initially be zero. Each observation brackets
its physical reads with status requests. Receipts retain both complete raw
replies as `status` and `status_after`, plus every requested memory address,
length and byte result. The first observation is marked `phase: preflight`.

The type-strict quiescence comparison excludes exactly two paths, recorded in
`quiescence_ignored_paths`: response `id`, and
`host.audio_output.host`. The latter is SDL audio presentation telemetry, whose
queue/pause counters can change while guest simulation is paused. Both raw
versions remain in the receipt. Guest PCM hashes, sample counts, processing
history, device flags and every other field, including unknown future fields
outside that exact subtree, remain compared. Changes in frame/ticks, CPU,
source identity, guest devices, guest queues/DSP or unexpected buttons fail.

The runner checks the full combined button masks against its accepted intent;
it does not mask unexpected local/script input. `inputs` records accepted
network masks separately from guest latch evidence. The existing joypad latch
changes only when guest code writes its sampling controls. **A video frame is
not a controller poll.** Held duration alone cannot establish that a game
sampled a button at a particular instruction.

Normal completion and failures release only the port acquired by the current
step, using `try/finally`; no all-port clear is sent. A lost acknowledgement
after `set_input` still triggers a scoped release attempt. Final cleanup gets
at most one additional second after the route wall deadline. Release failures
are recorded and make the receipt fail. Connection closure retains the
server's existing network-input release behavior.

Receipts also retain the validated plan, per-step outcome, actual advanced
frames, last status/advance replies, accepted-input acknowledgements, cleanup
and error details. A host frame overshoot is recorded and stops further work;
the runner never silently treats it as a successful bounded advance. Failed
routes do not continue to later steps.

## Bounded ABI 26 retail investigation

The ABI 26 `d102ecb80664ea45bada4036da46b466339daf09` consumer used for this
investigation missed historical
intents 97..99 under queued VDC timing **before any assistance**. An immediate
VDC control, changing only that profile on the same executable, exited the room
and reached the intended dialogue with the original inputs. This identifies
route sensitivity; it does not establish a runtime or hardware defect. The
retained consumer executable was built from that earlier pin. The new route
client bytes match the frozen implementation below; this does not relabel the
consumer as freshly built from it. Runtime/emitter source is unchanged between
the two pins, while their complete toolkit identities remain separate.

A private sequence waits on observed position/transition predicates, rather than
assuming a fixed duration will reach the doorway. It observed Right 59, Up 112
and neutral 120 frames. The sequence repeated three times and reached frame
**22,861**, executing **8,391,320 new native
and 9 interpreted instructions**. Reapplying historical intent 100 then reached
the street and Tigre Mine dialogue at frame **23,311**. The complete suffix
executed **22,568,899 new native and 14 interpreted instructions**. These are
bounded observations of this consumer, not full migration, campaign, hardware
or checkpoint-portability qualification. No runtime change was made and the
owner's selected ABI 18 package was unchanged. Title addresses and retail
artifacts remain private.

## Independent authored input checks

The separate `scripts/state_route_input_reference.py` pipeline compares 24
authored input-latch cases against a separately compiled original Gear core,
pinned to `1c62a549328241518101f5be5bf3e6840b96ea5d`. It validates the actual
Git blobs used for compilation; the reference implementation is never copied
into the runtime. The matrix crosses three authored NOP delays, both CPU
divisors and four held-input injection phases around actual guest polls.
It retains **4,096 Gear CPU calls**, **4,096 native retirements** and a separate
**4,096 interpreted retirements**, with **453 source identities**, **348,672
literal checks** and **72 actual execution joins**. Held intent and guest-write
latch phases remain distinct. Pure NOP delays do not establish VDC stall,
timer IRQ, retail input scheduling or host-presentation parity.

`scripts/state_route_input_qualify.py` rehashes bound artifacts and checks
original reference source identities, actual commands/stdout/captures and
independently expected work. Fresh execution from the frozen implementation
passes; the separate auditor verifies **773 artifact bindings**, **130 original
Git blobs** and all execution joins, then refuses **12 written changed-copy
controls**. Qualification of retained evidence is distinct from fresh emulator
execution. A fresh Release build of the frozen implementation passes the full
required `python scripts/check.py`: **1,188 Python tests without skips,
60 C++ suites and 12 fresh-process audio cases**, including both SDL dummy-host
suites. No retry or runtime change was needed.

The reference driver requires an existing Gear checkout, C++ compiler, CMake,
Ninja and explicitly supplied external static libraries. `--help` lists their
arguments. It builds separate original-reference and toolkit executables into
a new `.local/` directory; no retail input is required. To requalify that
retained output separately:

```sh
python scripts/state_route_input_qualify.py .local/input-reference/result.json --written-controls .local/input-reference/controls
```

Requalification requires unchanged bound source/artifacts and the exact toolkit
revision. A new controls directory and changed receipt filenames are required;
existing evidence is never overwritten.

The code-only implementation is frozen at
`60affdef59e3ce4bf4d02f1d17feadcc37bc3349`. Its 78-file relevant runtime/compiler
identity remains
`e2c412f28a60fc1acb66ca20e9d6cc573b60fb164cd8c78e5b1771fe2b3e4862`,
ABI 26: these host-side contributor tools do not change guest semantics.
That unchanged code digest does not substitute for binding the route/reference
tools and the exact frozen revision in their new execution receipts.

See [TCP control](DEV_SERVER.md), [consumer migration](CONSUMER.md), and
[source identity](ARCHITECTURE.md#source-identity-and-address-translation).
