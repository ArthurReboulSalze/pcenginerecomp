# Typed paused RAM writes

`scripts.dev_write` validates the reported effects of an explicitly declared
development-server RAM compare-and-write. It is a pure offline relation: it
does not contact a host, authorize an edit, retry an uncertain request, or
change execution policy. These host-only helpers do not change the runtime ABI
or checkpoint schema.

## Why a separate relation is needed

The host advances a bank's source generation for each byte actually changed
by a debug write. With the explicit work-RAM mirror profile, all four physical
banks `$F8..$FB` share the same 8 KiB backing and all four generation counters
advance. A data-only edit can therefore change the reported generation of
the currently fetched instruction even when its bytes are untouched.

The ordinary `validate_paused_observation` remains exact. Do not remove
generation fields or weaken its default to accommodate a write. The write
relation instead predicts the specific changes, checks them, and then applies
that same strict comparison to every other reported field.

## API

```python
from scripts.dev_write import WORK_RAM_MIRRORS, validate_paused_write

proof = validate_paused_write(
    before_status, after_status,
    request=raw_write_request,
    acknowledgement=raw_write_reply,
    memory_before=complete_wram_before,
    memory_after=complete_wram_after,
    profile=WORK_RAM_MIRRORS,
    code_footprint=original_and_live_fetched_physical_bytes,
)
```

Both readbacks are exact `bytes` objects covering the canonical 8 KiB backing
at physical `$1F0000`. Requests can address any of its `$F8..$FB` aliases,
including a physical bank boundary. The request is the exact parsed wire
object with `id`, `cmd`, `address`, `data` and `expected`; the successful reply
contains `id`, `ok`, `address` and `length`. The write ID must be between the
two status IDs. This ordering check does not authenticate a connection.

Other explicit profiles are `LINEAR_RAM`, with `memory_base` and a complete
aligned region of whole RAM banks, and `POPULOUS_RAM`, with the complete
32 KiB canonical backing at `$80000` for mapped RAM banks `$40..$5F`.
These profiles describe reviewed host mappings; no profile is inferred from
an ABI number, ROM checksum or current PC. Declaring a linear region does
not establish that it is RAM or lacks aliases.

The validator checks exact expected bytes, complete predicted readback,
successful-request and changed-byte counter increments, and nonoverflowing
generation increments for each of the seven reported fetch positions. It
excludes every submitted byte, including no-op bytes, from current fetches
and the supplied code footprint through backing aliases. Fetched bytes are
also checked against the full backing readback when they lie in that region.
All other reported fields, including unknown fields and audio telemetry,
must stay identical in value and type. Legacy audio-drain allowances do not
compose with this API.

The result records memory hashes, predicted per-bank generation deltas,
observed fetch-position deltas and the strict comparison of the projected
status. The bank list is a prediction: generations of banks outside the
reported fetch window are not visible. The nested strict proof describes
the projected statuses, after these exact declared effects are accounted for.

## Consumer responsibilities

Bind the executable, startup recipe, memory topology, source catalogue and
current live source footprint independently. A profile name is a declaration,
not evidence of those bindings. Keep title-specific edit policies and addresses
in the consumer project. Current source bytes alone cannot prove that an
address has never been executed or will never be executed later.

Retain raw requests, replies, full memory readbacks and both status objects
before calling the validator. A validation exception must not erase the AFTER
observation. An intent is not delivery proof. If sending, journaling or receiving
an acknowledgement fails, do not automatically repeat the write or infer that
the server rolled it back.

A paused host is at a whole-instruction boundary, but can still be inside a
game subroutine. Registers or other RAM may contain working copies that
overwrite edited data when execution resumes. Neither a passing relation nor
a successful checkpoint restore establishes that a particular game assist is
semantically safe. Consumer-specific invariants remain necessary.

An automatic hazard detector does not override the planner's preconditions.
A declined plan must stop the route. If a consumer revises an older restriction
to permit validated same-bank data edits, bind that change to new explicit
authority and exercise the actual planning path before resuming discovery.

Complete checkpoint bytes and continued execution supply separate evidence.
The validator compares reported source generations only; it cannot inspect
unreported bank counters or hidden machine state. Native and interpreted work,
imported prefixes and newly executed suffixes must remain separately reported.

## Adopting the relation in a consumer

Pin diagnostic helpers separately from the game executable and its runtime.
`project.source_identity` deliberately fingerprints the runtime/compiler
inputs, not the development scripts. Its source count/hash alone does not
authenticate this validator, the client, the observation helper or journal
tools. Verify the exact reviewed diagnostic Git revision and the actual
imported helper paths and file hashes. In a process that already imported
another SDK, check the complete imported closure: an older cached
`scripts.dev_observation` can otherwise satisfy the validator's import. Refuse
the wrong module before contacting a host, or isolate the reviewed helpers in
a clean process. Source-file hashing followed by ordinary Python imports is
also insufficient if an existing bytecode cache can supply older code. A
source-only loader can compile and execute the already verified bytes under
their exact filenames; keep dependency order and imported origins explicit.
Do not treat `-B` as disabling reads of existing bytecode caches.
Updating diagnostics does not require relabeling the runtime
pin or selecting an unqualified game build.

The relation runs **after** the operation. Calling it cannot prevent an unsafe
write that has already been sent. Preserve the consumer's pre-send checks:

1. Bind exact edit authority and literal expected/replacement bytes; establish
   game-specific invariants from fresh readbacks. Do not trust a success label
   or reuse an old plan against a different imported state.
2. Retain a strict paused status/readback/status interval and its current
   source-summary epoch. Verify logical PC, all eight MPRs, seven fetched bytes
   and observed generations against the current machine and backing RAM.
3. Exclude every submitted byte through backing aliases from the complete
   historical/live source footprint and current fetch. A different address
   in the same bank is permitted only when these byte exclusions pass.
   Reject stale expected bytes and known counter/generation overflow first.
4. Persist intent before sending, mark that exact operation attempted before
   the client call, and refuse reuse after any uncertain send, ACK, persistence
   or validation failure. Never assume a missing ACK means rollback.
5. Retain the actual reply and complete AFTER readbacks before invoking
   `validate_paused_write`. Keep source-summary invariance and other consumer
   policy checks alongside the returned typed effect proof.

For a group of edits, chain the actual validated observations. The first row
uses the original strict group anchor; each later row must match the preceding
row's verified AFTER state before another operation is sent. Also require
complete RAM to equal the original bytes plus exactly the prior literal rows.
Subtracting only prior write counters from a fresh status is insufficient:
a valid data edit can advance the generation of the bank containing current
code. Keep those measured effects in the chain rather than dropping generation
fields or weakening CPU/device comparison. Each row still needs its own
authority, source exclusions, write-ahead intent, ACK and typed effect proof.

A checkpoint-window capture contains newly executed source, not its complete
imported history. Bind the retained complete prefix to the exact checkpoint,
runtime, inputs and original counters, then combine its physical code footprint
with the lossless current window. Preserve each capture's ABI and origin. A
fresh-reset-only source checker should continue refusing imported histories;
add a separately reviewed checkpoint path rather than weakening it globally.
Neither the footprint union nor a passing write qualifies that historical
prefix or predicts source first executed later.

Preserve tested source hashes when publishing. If Git normalizes line endings,
record tested bytes and committed Git bytes separately. Verify the exact
declared transform and, where appropriate, identical compiled code under the
same filename. Do not silently replace an execution hash with a publication
hash or promote arbitrary source changes through a normalization allowance.

Useful adoption tests prove zero client writes for stale authority, historical/
live/current-code aliases, missing checkpoint-prefix bindings, lossy source,
changed source epochs, bad helper imports, malformed fetches and overflow.
After-send failure tests must retain evidence and forbid another attempt.
Then test a real same-bank data write and complete fresh-process checkpoint
round-trip/continued equality through the adopted consumer adapter.

## Verification

Frozen implementation `d74e0d5ea3a65264d5ab247271a50f4311d0c7f2` passes
16 authored vector groups covering all four WRAM aliases, backing and logical
PC wraps, mixed affected/unaffected fetch banks, linear bank crossings and
all Populous request banks, plus exact type, counter, overflow, code-footprint,
mapping, unrelated-field and full-memory refusals.

Three live TCP tests exercise stock headless, SDL and a newly emitted/compiled
native host executing WRAM code. Each checks changed writes, no-op, stale
refusal and complete checkpoint round-trip/continuation bytes in a fresh
process. The native restored suffix executes 59,605 native instructions and
zero interpreted instructions; stock hosts run the interpreted path. These
are authored inputs, separate from the finite retained-build Ys III assist.

The required frozen SDL checker passes 1,440 Python tests without skips,
65 C++ suites and 12 fresh-process audio checkpoint cases. See
[current status](STATUS.md#typed-paused-writes-and-closed-journal-archives--abi-26)
for the separately bound game test and its limited scope. No runtime or
emitter patch was needed for this host-side relation.
