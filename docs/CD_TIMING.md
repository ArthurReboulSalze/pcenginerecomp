# Explicit CD drive timing

ABI 28 adds `--cd-timing fixed|gear-distance` to both hosts. `fixed` remains
the default and preserves the existing deadlines. The optional profile
models distance-sensitive READ and CDDA seeks; it does not change command
framing, unknown-command policy, media bytes or host presentation cadence.

Consumer descriptors can opt in explicitly:

```toml
[runtime]
cd_timing = "gear-distance"
```

This is an additional runtime field in an otherwise complete descriptor.
HuCard startup refuses `gear-distance`. A CD recipe still needs the appropriate
firmware/media or an explicitly constructed transport; no medium is invented.

## Model and limits

The geometry originates in David Shadoff's MIT-licensed
[PCECD seek measurements and model](https://github.com/pce-devel/PCECD_seek/tree/7b9a70702d2f5422b924ee3cf7d42ff3ae5436ad).
The selected `gear-distance` policy uses the Gear/Mesen 18/48-frame base
constants and exclusive short-seek branch. The original standalone program
instead has 16/36 constants and overlapping short-seek branches. These are
explicitly different models, not three independent hardware measurements.
The MIT notice is retained in `runtime/src/cd_timing.cpp`; GPL reference
implementations remain in separate test executables.

The implementation uses integer rational arithmetic over fourteen rotation
zones. It preserves whole-track edge quotients and truncates to whole
milliseconds before converting to the 21,477,273 Hz guest master clock.
There is no host sleep, random rotational phase or distance inferred from
wall-clock file I/O. For example, seeks from LBA 0 take:

| Target LBA | Seek milliseconds | Master ticks |
|---|---:|---:|
| 0 or 1 | 150 | 3,221,590 |
| 2 or 4 | 216 | 4,639,090 |
| 5 | 366 | 7,860,681 |
| 810 | 432 | 9,278,181 |
| 333,012 | 2,508 | 53,865,000 |

Both seek endpoints must be in the calibrated **0..333,012** domain. The
distance profile explicitly faults outside it rather than copying the
reference's fallback to its first geometry zone. `fixed` remains available
for the wider supported TOC/address range. A valid media layout does not
by itself certify a timing model for every possible address.

## Command and head ordering

READ `$08` samples the retained drive head before cancelling audio. Its first
sector is scheduled at `now + seek + 286363`; later sectors retain the existing
1/75-second schedule. The unread-buffer retry stays 6,228,408 ticks. A
successful load moves the head past the loaded sector, clamped at the disc
tail; a retry or failed provider read does not move it.

For D8, seeks longer than 4,810,909 ticks split into a physical-seek interval
and the existing 224 ms playback delay. GOOD completion at the physical
boundary is separate from audible source readiness. Playing mode retains
the playback deadline; paused mode needs only the physical interval. Short
seeks remain unsplit. The source DAC stays gated until both deadlines clear.

D8 records its old head for the existing pending-seek position reply, then
immediately moves the retained head to the target. A READ issued during that
seek therefore measures from the target, not the old position. D9 paused
resume uses `max(now, pending_seek_deadline) + 4810909`; it does not perform
another distance seek. Existing stop/pause, reset, gap admission, sense,
DATA IN, IRQ and ACK behavior remains on the same paths. Unsupported or
overflowing new deadlines refuse before cancelling the prior timeline.

## Checkpoints and native modules

The selected timing profile is serialized as a validated enum and compared
against the independently configured destination. Pending READ, seek and
playback deadlines retain their existing fields. The host identity and TCP/
final JSON also bind/report the profile as `cd_timing.profile`.

ABI 28 requires regenerated native modules and rebuilt runtimes. Original
capture ABI labels remain intact; checkpoint schema 1 is still exact-build
only. ABI27 checkpoints are not portable into an ABI28 candidate, and changing
the timing profile is not permission to load a state from the other profile.
Each candidate must create its own checkpoint through its actual startup.

## Verification scopes

`pce-cd-timing-tests` checks literal distances, every geometry zone, deadline
splitting, source readiness, head movement, failure, cancellation and overflow.
`pce-cd-timing-checkpoint-tests` checks complete-machine continuation at
pending READ/audio boundaries, fresh provider binding, pending ADPCM and
filtered PCM state, and atomic refusal of malformed or mismatched states.
These direct-device suites execute no guest instructions.

The frozen ABI28 qualification at diagnostic revision
`ea6382a774bbe9846a12c61a2818487c3fa70e0a` reports 1,169 direct timing
checks and 64 complete-machine checkpoint cases with 204,710 expectations.
Twelve checkpoint cuts include filtered PCM continuation. The 82-file
compiler/runtime/CMake source closure is SHA256
`995ecfa893ee74ea046b758cbccfe0ab1baa57ecbec21c8a4c7313f06aca533a`.

The separate `scripts/cd_timing_reference.py` driver compiles original pinned
Geargrafx independently, compares original seek calculations with authored
rational vectors, and exercises command ports with emitted native and
interpreted guest operations. Mesen's untouched calculation and the original
MIT program retain their own scopes and differences. Working-source pilots
are labeled separately from final frozen-source qualification.

The final frozen comparison pins original Geargrafx at
`1c62a549328241518101f5be5bf3e6840b96ea5d` and Mesen at
`b9fa69ddc6d0a331fb103fdb5eef6904305703c2`. It passes 12,432 seek vectors
for the selected calculation in each core and the toolkit. Three out-of-domain
toolkit refusals remain explicit. Eight original-MIT-program outputs are
retained, including six differing whole-millisecond results and two agreements.
Twenty-one command cases run at both CPU divisors (3 and 12); the toolkit
executes **112,536 native instructions and, separately, 112,536 interpreted
instructions**, covering ten executed encoded identities. The fixture emits
74 operations; emission is not the executed-identity count. Gear's original
command ports are supervised by the test harness, rather than claiming an
original-core CPU replay. Twenty-eight internal complete-core round trips
pass. Actual writes to the sample-latch strobe precede reads: both tiers and
Gear return zero before readiness and the authored nonzero sample afterward.

The contemporary Gear source revision
`0ca083267f690205a516bb0a2a8f8c5dd5361e96` was checked for source drift:
its CD calculation, transport, audio and media inputs match the executed pin.
Other core files differ. This is a source comparison, not a fresh execution
of that later full core. Two independent audits verify the frozen result's
source/artifact bindings, raw records, per-key counts and declared differences.

The command comparison retains two older reference-policy differences. Gear's
reset keeps its pending physical seek while cancelling playback; the toolkit's
established reset cancels both. In the authored initial past-leadout READ case,
Gear reports STOPPED/GOOD while the toolkit retains IDLE and reports CHECK
CONDITION. Each engine's complete reported tuple is validated separately for
these declared cases. They are not silently projected into equality or changed
by the new timing flag. Mesen comparison here covers its calculation, not an
independent full command or guest CPU trace.

Separate Ys III startup tests use ABI28 **without native modules**, with
authentic reset and each timing profile's own newly created checkpoints.
Their first pending READ has head LBA 0 and target LBA 3,596, so it exercises
an actual distance-dependent path. Fixed and distance deadlines are
220,415,792 and 227,352,952 master ticks respectively. Both derive from the
same dispatch tick, 216,907,839, inside the raw command-counter increment
bracket; a later paused observation is not treated as command issue time.
Each profile passes two pending-READ checkpoint round trips with fresh-process
60-frame continuation and complete-file/core equality. These startup checks
execute **zero native instructions**; they do not qualify a full native game
route or import checkpoints from ABI27 or the other timing profile.

Model agreement and finite game regressions do not establish electrical bus
timing, per-drive jitter, analog audio, physical seek conformance or complete
game compatibility. The fixed reference path and its earlier qualifications
remain separate.
