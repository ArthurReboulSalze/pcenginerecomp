# Queued VDC VRAM accesses

Clocked VDC profiles default to queued CPU VRAM reads and writes. The untimed
functional device remains synchronous. Select `--vdc-access immediate` in
either host, or `vdc_access = "immediate"` in a consumer's `[runtime]` table,
to retain the previous aggregate reference path. `queued` selects the current
path explicitly. The host option requires an enabled clocked VDC.

## Requests and completion

Writing MARR high queues a read. Reading VRR high returns the previous buffer
and queues another read when register 2 is selected. Writing VWR high queues
a word write. Neither a queued request nor inspection publishes its result
early. The shared countdown uses these master-clock delays:

| VCE dot clock | Read | Write |
|---|---:|---:|
| 5.37 MHz | 24 | 21 |
| 7.16 MHz | 24 | 18 |
| 10.74 MHz (controls 2 and 3) | 15 | 12 |

The queue is serviced in three-master-tick groups, retaining fractional
progress while a request is pending. At most one operation completes per
group; reads have priority over writes. Completion uses live MARR/MAWR, VWR
and CR increment, preserving address wrap and the retained read-bus behavior
in [VRAM_BUS.md](VRAM_BUS.md).

Status bit 6 reports pending CPU VRAM work. Reading status clears event flags
and the local IRQ assertion while retaining BUSY for outstanding requests.
Data-port reads enter a wait only if a read is pending. Data writes to MAWR,
MARR or VWR enter a wait if either operation is pending. Once entered, the
wait drains both pending operations. Selection and other register writes do
not introduce that wait. A direct low-level port access that requires clock
progress faults; CPU accesses use the bus helper to advance it safely.

## Arbitration and CPU clocks

SATB and VRAM DMA take precedence. Otherwise admission follows the selected
display state, background fetch window and MWR access pattern, sprite count
and fetch cost, alternating idle slots and HSync exclusion window. Queue
service precedes raster advancement within a pending three-tick chunk, so
completion cannot claim a DMA slot released later in that same chunk.

Mapped reads inject their one fixed CPU cycle before observing the port;
mapped writes inject it after the port operation. Block transfers use two
fixed cycles on their respective side. ST0/ST1/ST2 advance two CPU cycles
before the port and one after it, leaving two cycles for retirement: five
base cycles in total. Generated ST bodies call the shared timed port helper,
without invoking the interpreter.

Dynamic stalls add three master ticks at either CPU speed. They advance
devices and IRQ sampling without inventing base CPU cycles or instruction
retirements. Interrupt entry remains at the existing CPU boundary. A
malformed request that cannot obtain a slot within eight longest frames
faults explicitly rather than publishing fabricated completion. This bound
exceeds a full 65,536-word DMA plus SATB and display interference.

Status and final output include a pure `vdc_access` object: `profile`,
`pending_read`, `pending_write`, `delay`, `phase` (0–2 carried master ticks),
and cumulative `wait_ticks`. Explicit consumer selections validate that
report. Debug snapshots, peeks and native guards do not advance the queue.

## ABI and qualification boundary

Runtime ABI **24** includes the queue flags, countdown, carried ticks,
arbitration windows/HSync origin and CPU wait counter. Re-emit original
ABI-12 through ABI-23 captures without relabeling them and rebuild modules
and runtime together. Consumer/capture schemas remain **1**. ABI 24 itself
introduced no save-state format. Later exact-build
[developer checkpoints](DEVELOPER_CHECKPOINTS.md) retain these fields and bind
the selected timing profile. BRAM-only saves remain a separate contract;
portable or cross-build state migration remains unimplemented.

Queued timing can change instruction counts, video or PCM at a fixed frame.
Preserve the old qualified package and qualify a fresh same-profile route;
do not demand historical immediate timing from the queued profile.

The independent adapter in `scripts/vdc_queue_reference.py` uses authored
fixtures and the separately compiled, unchanged Geargrafx core pinned at
`1c62a549328241518101f5be5bf3e6840b96ea5d`. It distinguishes synthetic slot
matrices, free-running device schedules and real CPU execution. Source
references are the [VDC queue and arbitration](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6270_inline.h),
[hardware scheduler](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/geargrafx_core_inline.h),
[CPU stall accounting](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h)
and [mapped access ordering](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory_inline.h).
The MIT implementation is original; the GPL reference is not linked into
the toolkit or copied into its runtime.

This is an emulator-reference model, not electrical or full instruction-bus
parity. Background rendering retains the separately qualified Mesen two-bit
profile, which differs from Geargrafx's four-bit-only background renderer.
Reference reports retain those raw bus differences explicitly; they cannot
be described as whole-VDC equality. Cold read-buffer initialization remains
the toolkit's deterministic zero; reference queue traces establish a common
buffer using actual prefetch and clock progress. Other dummy/fetch bus phases,
all mid-scanline races and physical hardware remain unqualified. Timer
underflow and IRQ entry during the bounded VRAM-stall sequences below now
have independent traces; other instruction phases and mixed IRQ sources
remain unqualified.

The final frozen-source reference run passes **615 cases / 2,556 records**,
with **3,678 independent literal checks per tier**. It executes **582 native
retirements**, zero interpreter fallback, 97 source identities, four MPR
contexts and 24 pure guard negatives. All 12 actual CPU cases match Gear's
states and timestamps. Exactly 99 retained MWR3 background bus differences
are reported separately; all queue/timing fields remain exact. The authored
C++ queue suite adds **49,279 expectations**. These checks establish the
bounded model above, not hardware or whole-game parity.

## Guest register changes during pending requests

`scripts/vdc_queue_reference.py --suite races --native` adds a separate
authored guest matrix. The default `--suite legacy` preserves the original
615-case ROM and plan; `--suite all` includes both. Each run requires a new
private output directory and the same pinned original Gear source and
explicit libraries described in [DEVELOPMENT.md](DEVELOPMENT.md).

The **24 cases** cover both CPU speeds, all three VCE dot dividers, and
read/write requests at `7FFF` and `FFFF`, with selected changes from increment
1 to 32, 64 or 128. Real guest instructions start a 512-word VRAM DMA and
queue the target access. Observations immediately before and after the
decisive CR high-byte write require the same pending request and a positive,
advancing DMA. A later guest data-port access incurs the wait. No pending
flag, DMA state or display phase is injected for these cases; the initial
VRAM pattern, CPU speed and common completed prefetch are authored setup.

The separately compiled original Gear core, toolkit interpreter and emitted
native module match **1,536 records**, including CPU registers/mappings,
queue/register state, timestamps, RAM and complete VRAM hashes. Each engine
passes **168 independent assertion groups** covering the pending witness,
control change, endpoint arithmetic, driven/retained read bus and complete
expected RAM/VRAM result. These are grouped assertions, not 168 individual
bytes or independent hardware measurements. The expected values are authored
arithmetic and data, not copied from either execution tier.

The native run retires **744 instructions across 124 encoded identities**
with zero fallback. Its **96 source-byte/MPR guard negatives**, including
48 at the genuine DMA-held pending window, preserve the full encoded CORE
checkpoint payload, generation counters and VDC port counters. This is a
purity check on failed dispatch, not a fresh-process checkpoint restore.
The race cases have **no reference field projections**. The existing named
MWR3 renderer differences belong only to the separate legacy cases.

A fresh `--suite all --native` run also passes **639 cases / 4,092 records**,
with **1,326 native retirements, zero fallback, 221 encoded identities and
four MPR contexts**. Its 120 pure guard negatives include the same 48 genuine
pending-window negatives. The combined run retains exactly the original
99 named MWR3 read-bus differences; no new race record differs from Gear.
The old 3,678 literal checks and new 168 assertion groups keep their distinct
units rather than becoming a count of independently measured bytes.

This closes independent guest coverage of the selected live-CR completion
semantics. It introduces no runtime fix, ABI change or checkpoint migration.
Other register races, half-written raster comparisons, further IRQ overlaps
and physical bus alignment remain separate qualification work. Ys III's TCP
checkpoint regression is separate from this authored original-core matrix.

## Timer interrupts during waits

The separate authored `scripts/vdc_irq_reference.py` probe checks timer
underflow during a CPU VRAM read blocked by a real 16-word VRAM DMA. Timer
reload/control writes and full-scheduler clocks establish the initial phase;
no pending operation is manually completed. It covers both CPU speeds,
three VCE dot speeds, remaining timer phases of **18, 30 and 60 master ticks**,
and unmasked, CPU-I-masked and IRQ-mask-deferred delivery. The guest handler
disables and acknowledges the timer, increments an observed counter, and
returns with RTI.

The frozen-source run passes **54 cases / 2,484 records**, with **972
independent literal checks per tier**. It executes **1,188 translated native
retirements with zero interpreter fallback**. All CPU/vector/stack, timer,
queue, wait and timestamp records match the separately compiled original
Geargrafx core exactly, with **no field projections**. An observational
callback in the Gear adapter records all 54 timer underflows at master tick
**3,120**, while a dynamic VRAM wait and DMA are both still active.

The **108 pure guard negatives** exercise source-byte and MPR misses with an
armed timer and pending VRAM work **before underflow**. They preserve the
observed CPU, timer, queue, clock and memory state. These misses do not claim
guard coverage with an already asserted IRQ.

These qualification additions leave **runtime ABI 24** and the canonical
compiler/runtime source unchanged. The probe requires no retail input; see
[DEVELOPMENT.md](DEVELOPMENT.md) for the immutable-source command and explicit
library inputs. Timer underflow at other instruction phases, IRQ1/IRQ2
priority or mixed-source delivery, electrical bus phases and physical
hardware remain unqualified.
