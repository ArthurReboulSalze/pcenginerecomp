# Unknown CD command response profiles

The transport distinguishes an unsupported operation from a selected device's
response to an invalid command. The default remains an explicit fault. An
unknown opcode never executes a guessed service or a no-op CPU instruction.

## Select an explicit response policy

| `--cd-unknown-status` / consumer `runtime.cd_unknown_status` | Framing for an unrecognized opcode | Outcome |
|---|---|---|
| `fault` (default) | First byte, on ACK release | Diagnostic unsupported-command fault |
| `gear-good` | First byte, on ACK release | Legacy Geargrafx/Mesen GOOD response; no operation implemented |
| `nec-invalid` | Complete packet under the NEC reference table | CHECK CONDITION with retained illegal-command sense |

The equivalent C++ API is `CdUnknownPolicy::{fault, gear_good, nec_invalid}`
and `CdControl::unknown_policy`. HuCard-only recipes reject CD response
profiles. Selecting a policy does not enable unsupported modes of a known
command or make a missing media provider valid.

For example, a CD consumer can opt in with:

```toml
[runtime]
# Alongside the descriptor's other required runtime entries:
cd_unknown_status = "nec-invalid"
```

This is an explicit emulator-reference profile, not console hardware
certification. Do not silently change a qualified consumer's selected recipe.

## Complete-packet negative responses

The NEC reference recognizes `00`, `03`, `08`, `D8`, `D9`, `DA`, `DD` and `DE`.
These retain their existing six-/ten-byte handlers. For every other opcode,
`nec-invalid` uses the pinned Beetle NEC core's high-nibble table:

| Opcode high nibble | Bytes required |
|---|---|
| `0`–`1` | 6 |
| `2`–`9` | 10 |
| `A`–`B` | 12 |
| `C`–`F` | 10 |

Each byte requires REQ/ACK capture and ACK release. Holding ACK high cannot
capture extra bytes or dispatch early. Partial packets remain pending; they
are neither accepted GOOD responses nor completed invalid-command attempts.
The final ACK release dispatches exactly once, retaining the complete CDB
and the original mapped CPU source context when supplied by guest execution.

A complete invalid packet produces sense key `$05`, ASC `$20`, ASCQ/FRU zero
and no diagnostic failure LBA. The existing fixed 18-byte NEC REQUEST SENSE
response exposes that context and clears pending sense when it snapshots the
reply. The active response remains a separate state from pending context.
Warm bus reset preserves pending sense under this reference policy; a new
machine starts with empty context. See [sense lifecycle](CD_SENSE.md).

The toolkit's existing bus reset clears a partial command packet. Original
Beetle's warm-reset path retains its partial CDB cursor, which can affect the
next packet. This difference is retained in reference reports; this profile
does not adopt that behavior or claim reset-buffer parity.

This profile retains the toolkit's existing CHECK CONDITION wire encoding:
status `$02`, message `$02`. Original Beetle emits `$01` and `$00` instead.
Reference comparisons must retain and report those raw differences; equal
error classes and sense payloads do not establish identical wire behavior.

## Why `$FF` needs framing rather than a special service

Original Gear dispatches an unrecognized first byte immediately to GOOD.
Original Beetle receives ten bytes for an `$FF` packet, then reports illegal
command. Its `$FF` command-table row is a null sentinel, not a supported
firmware operation. A host that keeps the same data latch and acknowledges
new requests can therefore send ten `$FF` bytes without writing a new value.

The retained consumer investigation identifies repeated `$FF` writes in a
System Card busy/reselection drain path. The routine's signal/ACK loop can
feed the longer packet; a one-byte GOOD response alone did not establish a
missing game operation. Title-specific callers and route controls remain in
the consumer project, outside the shared runtime.

## Diagnostics and state compatibility

`cd_unknown` retains `accepted_responses` for legacy GOOD responses and adds
`invalid_responses` plus the explicit `policy`. The opcode histogram counts
completed dispatch attempts, including a strict fault. Prefix bytes do not
increment it. `last_command` preserves the actual packet length; `origin`
retains logical PC, all MPRs, physical PC, fetch bytes and source ticks.
Inspection never clocks, reads or acknowledges the device. Response and
histogram counters reject overflow before wrapping.

The final runner's `scsi.reference_unknown_status` remains a legacy diagnostic
boolean derived from `policy == gear-good`; it is not a second configuration
switch. `scsi.unknown_commands` keeps its original GOOD-response meaning,
while `scsi.invalid_commands` counts the new negative responses.

**Runtime ABI 27 requires re-emission and rebuilding the runtime and native
module together.** Original observation ABIs 12–26 remain valid labelled
inputs; emitted modules target 27. The typed policy and rejection counter are
serialized, validated and bound to the checkpoint's machine configuration.
Developer checkpoint schema 1 remains exact-build-only: ABI26 files and
files from another module, executable or response recipe cannot be imported
by rewriting their identity. Generate a candidate-owned checkpoint instead.
See [developer checkpoints](DEVELOPER_CHECKPOINTS.md) and
[native migrations](NATIVE_MIGRATIONS.md).

## Independent reference boundaries

The source references are pinned independently:

- [Geargrafx transport, `1c62a549`](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.cpp).
- [Beetle NEC transport, `b96c11e0`](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/cdrom/scsicd.cpp).

Gear's REQUEST SENSE shortcut has no payload, so it cannot qualify NEC sense
data. Each reference keeps its own framing and raw status/message result.
Authored fixtures qualify protocol behavior separately from actual native or
interpreted guest work. They establish neither electrical bus timing nor
physical drive latency. Retained older builds or exploratory probes are not
promoted into fresh-build evidence.

The frozen qualification compiles original Gear's 39 source units plus an
authored adapter, original Beetle's SCSI translation unit, and fresh toolkit
probes. Each original core runs 252 cases: all 248 unrecognized IDs and four
abort/sense-lifetime cases. The NEC-domain run validates 1,784 records per
engine; the legacy-framing domain validates 520. Raw ACK observations remain
bound separately from the settled protocol assertions. Gear's empty SENSE
reply is retained as a difference from the toolkit's real response even when
the toolkit selects `gear-good` for unknown opcodes.

A separate authored autonomous guest executes ten `$FF` bytes, consumes the
18-byte error SENSE response, checks a subsequent clear response and completes
TEST UNIT READY. It executes 23,241 interpreted instructions, then 23,241
statically translated native instructions with zero fallback. All 893 source
identities conserve their individual retirements. The 21-field reported CPU/
work vector, 44 observed RAM bytes (two SENSE replies and status/message bytes)
and pending sense match. This is internal CPU-tier evidence alongside the original
cores' supervised device evidence, not a cross-core guest CPU timing trace.

Twelve authored Python tests check independent expected values and refusal of
changed payloads, malformed evidence, changed/missing bound files and a
prebuilt probe presented as a fresh native qualification. The driver fails if
any source/tool/artifact preservation check fails. Full native qualification
requires fresh builds; the optional externally supplied interpreted probe is
explicitly labelled and hash-bound.

### Run the authored reference matrix

Use the original pinned checkouts and compiler/static libraries from the
[reference setup](REFERENCE.md). Run the script from the toolkit checkout
being qualified; its imported compiler must match `--tool-source` (default
is that same checkout). Supply the actual required static archives, for
example:

```text
python scripts/cd_unknown_reference.py --gear-source .research/Geargrafx --beetle-source .research/beetle-pce --native --compiler clang++ --library PATH_TO_LIBCHDR --library PATH_TO_LZMA --library PATH_TO_MINIZ --library PATH_TO_ZSTD --out .local/new-unknown-reference
```

The output must be a new private directory beneath the selected toolkit's
`.local/`. The command compiles original cores separately from the toolkit,
records commands, logs, source/artifact hashes and raw observations, then
requires unchanged bindings before success. It downloads no media or source.
`--reference-only` omits toolkit execution; `--probe` identifies a prebuilt
interpreted probe and cannot be combined with `--native`.

## Bounded Ys III consumer checks

The separate ABI27 candidate retains all 57,752 compiled identities. This
unassisted cohort executes 6,816 distinct identities with zero interpreter
fallback and no guest-memory edits. Its cold 4,204-frame prefix matches the
retained pre-command observations under a narrowly checked metadata relation;
that relation is never used to erase differences after an unknown command.

Each response recipe creates its own checkpoint. The new NEC candidate
receives ten `$FF` bytes, records one invalid response and zero accepted GOOD
responses, then proceeds to a real READ `$08`. A fresh process restores the
candidate's frame-4,252 checkpoint; immediate complete files and continued
complete endpoint files match byte for byte. The 12-frame NEC suffix executes
423,360 native instructions with zero fallback. Legacy `gear-good` separately
preserves the original ABI26 per-source retirement counts for its cold
prefix, 60-frame direct continuation and 12-frame restored suffix. Reported
legacy endpoint state also matches within the declared metadata and host
presentation scope; no cross-ABI checkpoint is rewritten or imported.

A separate paced NEC fork executes 120 new frames and 3,689,416 native
instructions with zero fallback. It produces 88,457 new PCM frames; all 119
sampled active observations report zero host drops. Queue conservation is
`1 imported + 88,457 generated = 88,456 submitted + 2 pending`. The planned
pause clears 696 presentation frames; shutdown separately drains the two
pending guest frames. Conservative bounds establish at least 87,759 newly
accepted device frames, including at least 7,896 newly nonzero frames after
accounting for possible tail/pending losses. Physical playback and listening
quality remain unqualified.

These are cold-prefix and exact-build continuation tests. The already
qualified ABI26 Play selection stays protected. They do not establish the old
full route under ABI27, campaign completion or hardware conformance. Strict
baseline runs stop at the expected unsupported first byte with exit 3; their
forensic journals remain distinct from successful candidate continuations.
