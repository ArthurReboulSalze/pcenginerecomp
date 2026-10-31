# Base PC Engine compatibility profile

The retained ABI-16 batch closes three shared execution gaps: normal PC Engine work-RAM
mirrors, BRK, and VDC sprite events. It does not introduce a complete console
reset, HuCard loader, SuperGrafx profile, or hardware-conformance claim.
ABI 17 added the separate [System Card reset-vector profile](SYSTEM_CARD_BOOT.md);
the sandbox and snapshot contracts below remain available. ABI 18 added
the explicit [base HuCard profile](HUCARD.md) without changing these CD contracts.
ABI 19 added explicitly selected SF2 banking and Populous RAM profiles.
ABI 20 added an optional [Arcade Card Duo](ARCADE_CARD.md)
expansion on Super System Card hardware.

ABI 21 preserves the timer's disabled reset/control divider phase, correcting
initial timer reads while retaining the existing interrupt boundary profile.
See [TIMER.md](TIMER.md). Paused development capture inspection separately
reports source-span and execution evidence without advancing guest time.

## Work RAM and code identity

The standard runners map physical banks `$F8..$FB` to the same 8 KiB of work
RAM. A standalone `Bus` remains an explicit sandbox until
`enable_work_ram_mirrors()` is called. Configuration rejects occupied alias
banks rather than discarding independently loaded data. This is the base
PC Engine layout; SuperGrafx has different RAM and needs its own profile.

Guest reads, writes, block transfers, loader writes, pure source peeks, and
paused TCP reads/compare-and-writes resolve the same backing storage. A changed
byte advances all four alias generations. Loader writes retain the existing
per-touched-bank generation convention. Native guards still compare current
bytes, rather than trusting generations.

The mapped physical address is retained in captures and dispatch identities.
Only storage resolves to `$F8`. Full MPRs, logical PC and exact fetched bytes
remain required: canonicalizing storage is not permission to merge source
contexts or remove byte guards. Direct access to `Bus::bytes` is internal
backing storage; guest-facing tools must use the bus/peek accessors.

## BRK and reserved encodings

BRK is a two-byte encoding, including its ignored signature byte. It pushes
`PC+2` high, low, and `(P|B)&~T` through the mapped stack, sets live I and
clears D/T, then reads the mapped `$FFF6/$FFF7` vector. Its base cost is eight
cycles at the current CPU speed. A previously sampled interrupt retains the
existing instruction-boundary delivery rule.

Generated code checks both encoding bytes before mutation and emits the stack
and vector operations directly. The interpreter does not perform a data/MMIO
read of the ignored signature under the selected Geargrafx/MAME profile. Mesen
fetches the signature as an immediate operand; exact physical fetch phases
are not certified by this choice. PC, stack and address wrapping stay observable.
The control-flow analyzer keeps the vector unresolved; it does not invent a
handler address.

There are now 234 supported opcode encodings. The remaining 22 reserved slots
still return `unsupported`; they are not silently treated as NOPs. BRK has a
dedicated vector/stack/IRQ fixture, separate from ordinary instruction tests.

## Sprite evaluation and interrupts

Sprite evaluation belongs to the VDC guest clock and runs with continuous
presentation and PCM disabled. The selected Geargrafx profile caches pattern
rows at the raster-compare fetch for the next line. Wide sprites occupy two
16-pixel cells; transparent and offscreen cells still consume the 16-cell
budget. A partially admitted wide sprite can cause overflow.

Overflow is delivered at the subsequent HDS checkpoint and gated by live CR
bit 1. Collision is checked at active HDW entry, using latched sprite display
enable and live CR bit 0. It requires overlapping opaque pixels of sprite zero
and another admitted cell inside the active width. Sprite status/IRQ handling
is independent of background priority. Status reads acknowledge the pending
events; toggling an enable afterward does not recreate an already consumed
event. The reference profile's vertical, burst, MWR and CR latches apply.

The retained ABI-16 framebuffer read current SATB and pattern storage at HDW;
its cached-row checks qualified status/IRQ behavior. The ABI-23 continuous
output consumes fetched sprite planes, position, palette and priority.
Pure snapshots still inspect current storage and held bus data. Undriven
pattern reads now return the retained word. This remains an aggregate fetch
profile, not physical VRAM fetch-slot contention. Independent emulator agreement qualifies the
selected profile, not analog video or exact CPU MMIO bus phases.

## Unknown CD command diagnostics

The strict default still faults on unimplemented commands. The explicit
`gear-good` option retains its existing reference-emulator response policy.
ABI 27 adds `nec-invalid`, receiving the full NEC-framed invalid CDB before
CHECK CONDITION and retained `$05/$20` sense. This is a named reference
response policy; [wire/reset differences](CD_UNKNOWN.md) stay explicit.
No profile implements an unknown command's operation. REQUEST SENSE is a
known implemented command with the fixed NEC data response; the toolkit does
not copy Geargrafx's GOOD-only shortcut. See [CD_SENSE.md](CD_SENSE.md).

TCP status and final JSON add `cd_unknown`: a bounded opcode-attempt histogram,
accepted GOOD-response count, invalid-response count, explicit policy,
retained last unknown CDB, and its origin when known.
The origin is the CPU state at the last latch write supplying the initial
CDB byte before ACK: logical PC,
complete MPRs, mapped physical PC, guest ticks, and seven pure source peeks.
Unreadable peeks are null. Rewriting the latch before ACK replaces that pending origin. It is not a
retirement trace or the later ACK-time state. Low-level callers that bypass the CPU bus have no origin.

Known later commands do not overwrite this last-unknown record. Transport
reset clears a pending origin but retains cumulative diagnostics. A fresh
CD profile starts fresh counters. Attempts count strict faults too;
`unknown_commands` continues to count only accepted reference responses.
No unbounded command trace or filesystem output is implicit.

## ABI and retained observations

Current runtime ABI is 27; consumer descriptor and capture schemas remain 1. Retained
ABI-12 through ABI-26 observations can be re-emitted without relabeling their original
ABI. Rebuild generated modules and runtime together. BRK's new two-byte capture
length cannot retroactively certify an older BRK observation: older runtimes
did not support its retirement.

Exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve the
work-RAM profile and canonical storage, cached sprite rows and cell budget,
overflow pending flag, burst/active state, CR/MWR latches, and CPU/device
timelines. They also retain the ABI-23 shared VDC VRAM bus word, fetched sprite
palette/priority and background tracking while presentation is disabled. See
[VRAM_BUS.md](VRAM_BUS.md). Presentation resources are recreated locally;
portable saves and cross-build state migration remain unimplemented.

ABI 24 adds queued CPU VRAM requests, BUSY, raster access slots and dynamic
CPU wait ticks. Clocked profiles default to queued access; the explicit
immediate profile retains the prior reference path. Queued timing needs a
new same-profile qualification; see [VDC_ACCESS.md](VDC_ACCESS.md).
