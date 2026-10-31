# Finite host sessions

Long TCP qualification routes can explicitly select more than ten minutes
without changing the runtime or omitting their wall timer. Both `pce-headless`
and `pce-desktop` accept `--wall-seconds 1..86400`. The upper limit is one day;
there is no unlimited numeric value. Zero, negative values and values above
86,400 are refused before the guest or SDL window starts.

For a fifteen-minute session, append this to an otherwise valid host command:

```text
--wall-seconds 900
```

A schema-1 consumer descriptor requires all three independent limits:

```toml
[limits]
steps = 20000000000
ticks = 100000000000
wall_seconds = 900
```

`project verify` validates the exact integer, `project build` binds the
descriptor, and `project run` forwards the selected value unchanged. Its outer
subprocess watchdog is the selected value plus ten seconds, allowing the host
to finalize its report after its own wall deadline. Changing the descriptor
requires a matching build receipt; it cannot reuse a receipt for another
limit. Current examples retain their original short limits. A recipe choosing
600 seconds stays at 600 until its author changes it.

The raw CLI preserves its previous omission behavior: without
`--wall-seconds`, its wall timer is disabled. This is different from an explicit
zero, which is invalid, and from consumer descriptors, which cannot omit
`wall_seconds`. Prefer an explicit finite bound for diagnostic TCP sessions.

The timer starts after host initialization and uses a monotonic host clock.
It remains active while the guest is paused. Expiry produces `stop: wall_limit`
in the final report; it does not qualify a completed gameplay route or a save
publication. The deadline is checked by the host pump, so an individual long
guest instruction or host operation can delay its observation. The outer
watchdog remains a separate safeguard rather than a claim of real-time
preemption.

Dispatcher-step and guest master-tick deadlines remain active independently.
Selecting a longer wall allowance does not speed up simulation, expand TCP
request limits, change audio pacing, or bypass device waits. A TCP
`step_frames` request is still limited to 600 frames; that request bound is
unrelated to seconds.

This host setting requires a rebuilt executable and a new exact source pin for
consumer builds. This host-only setting originally retained ABI 24; the
current shared runtime requires ABI 27 for separate device/guest-write changes.
The wall allowance itself does not alter guest state semantics.
Previously qualified receipts keep their original command and timeout scope.

Authored tests check descriptor validation and forwarding, the official outer
watchdog, actual headless/SDL parser boundaries, short guest tick deadlines
under long wall allowances, and actual one-second expiry with zero guest
retirements while TCP-paused. They do not run a one-day session or establish
console timing; Geargrafx is not an oracle for this host-only policy.
