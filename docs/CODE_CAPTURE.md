# Retired-code capture and native emission

The optional host observer collects exact identities of instructions that
actually retire. It supplies an offline compiler input for overlays, MPR
changes and self-modifying code without guessing a global control-flow graph.
It is available in both headless and desktop hosts. The current runtime ABI is
29; observations from ABI 12 through 29 retain their original labels for offline regeneration. This is
an execution profile, not a save state or complete program.

**Captures contain game or firmware instruction bytes. Keep them and generated
modules private.** Store local experiments in ignored scratch. Do not publish
retail captures, generated source or title-specific debug addresses as fixtures.

## Capture a bounded run

Add these options to the existing host command:

```text
--code-capture .local/capture/run.json --capture-limit 65536
```

The output parent directory must already exist. The filename must be new;
exclusive creation refuses existing files, symlinks and hard links. The host
also refuses an alias with another input or capture output. There is no implicit
output location or overwrite option. The normal tick, instruction and optional
wall-clock limits still apply. `--capture-limit` requires `--code-capture`,
accepts 1 through 65,536 identities, and defaults to 16,384.

With capture absent, the host does not inspect instruction source for this
feature, allocate its identity tables, write a capture or add diagnostic fields.
The opt-in path increases host work and retained private data; keep its run
and observation window tied to the capability being tested.

To omit startup or assisted code from the observation itself, add
`--code-capture-start-frame N` with `--video-output continuous`. The output is
reserved exclusively during setup, but instruction peeks and hit accounting
start only before the first dispatch with completed-video sequence at least
`N`, after TCP pause handling. A paused client can restore and verify original
bytes before resuming. The flag does not restore bytes or certify them.

The final report adds `code_capture_window`: requested frame, actual start
frame/ticks and native/interpreted retirement counts before the window. An
unreached window emits an empty capture and null actual-start fields. Capture
retirements count only the window; subtract the recorded preceding counts
when comparing with whole-run retirement totals. Omitting the flag retains
whole-run capture and its existing report shape.

Before dispatch, the observer reads only the instruction's exact decoded length
through side-effect-free RAM/ROM peeks. Each byte maps independently, including
MPR page boundaries and logical `$FFFF` wrap. No neighboring bytes, CPU semantic
registers, broad RAM, BRAM or MMIO contents are captured. After dispatch it
accounts for a native or interpreted retirement; budgets, unsupported exits,
guard misses and faults before retirement do not become observations. An
instruction that retires before a later interrupt-service fault is counted.

The file is finalized after the execution loop, including an ordinary requested
TCP quit or a caught guest bus fault. An interrupted process, host setup failure
or failed output write may leave an empty or partial file. Such a file is not a
valid capture and must not be used as qualification evidence.

## Schema 1

The top-level fields are:

| Field | Meaning |
|---|---|
| `schema`, `runtime_abi` | Schema 1; individual offline observations accept ABI 12 through 29 with their original labels |
| `capacity` | Maximum unique identities retained |
| `retired_instructions` | All observed native plus interpreted retirements |
| `dropped_instructions` | Retirement occurrences for new identities when full |
| `unreadable_instructions` | Retirements whose complete bytes could not be safely peeked |
| `complete` | True exactly when both preceding loss counters are zero |
| `observations` | Deterministically ordered unique instruction identities |

Each observation contains `pc` (16-bit logical address), `mpr` (all eight
mapping bytes), `physical` (21-bit address for each fetched byte), `data` (exact
instruction bytes), `native_hits` and `interpreted_hits`. The full MPR mapping
and logical PC plus bytes identify a record; physical addresses are explicitly
recorded and checked against that mapping. Repeated byte variants at one PC,
multiple MPR contexts and overlapping retired interpretations remain separate.
No snapshot generation or complete memory image is implied.

Hit counts are nonnegative 64-bit integers with a nonzero sum per identity.
All retained hits plus both loss counters must equal `retired_instructions`.
After capacity is reached, already-retained identities continue accumulating
hits. Dropped occurrences do not report the number of distinct missing sites.
`complete` describes loss within this observed run only: it says nothing about
unvisited code, alternate inputs or campaign coverage.

## Emit a private native module

For multiple original inputs, including different supported ABI epochs, use
the separate [observation-profile composition and emission interface](OBSERVATION_PROFILES.md).
It preserves per-input raw provenance and does not fabricate one execution capture.

```text
python -m pcerecomp emit-capture .local/capture/run.json --out .local/native/run
```

The output directory must be new. The command reads at most 64 MiB, rejects
unknown or duplicate JSON fields, booleans used as integers, malformed lengths,
incorrect physical mappings, duplicate identities and inconsistent counters.
The existing ISA decoder derives operation metadata and branch targets rather
than trusting capture-supplied mnemonic or target labels.

Emission produces `module.cpp`, `module.json` and, for larger captures, separate
`module_part_NNNN.cpp` translation units plus `module_parts.hpp`. Every supported observation
has direct translated C++ operations, with no per-opcode interpreter call.
Opt-in `--partition-layout stable` instead names each part by its full MPR
mapping and fixed logical-PC range. See [stable source layout](STABLE_EMISSION.md)
and the separate [managed rebuild interface](INCREMENTAL_BUILDS.md).
Dispatch first checks the instruction deadline, then selects an exact packed
full-MPR context and logical-PC case. Exact source-byte guards choose among
variants before any guest mutation. Source selection reads the opcode once,
then each operand byte once at its canonical physical location; any unreadable
byte refuses execution. The opcode fixes length, and all operand bytes pack
into a collision-free key of at most 48 bits. Nested opcode/key switches match
every fetched byte exactly; no source hash or generation replaces that equality.
Unobserved opcodes and operand keys miss without beginning an instruction.

Multiple exact keys share one translated body only when generated statements,
retirement and timing are identical within the same logical PC/opcode. Literal
operations with different operands remain separate. Block-transfer variants
can share a body because it fetches operands live after its initial stack
writes, preserving existing semantics. `dispatch_strategy` describes this
selection and `translated_body_count` reports actual shared bodies;
`native_instructions_emitted` still counts every supported source identity.

Partitioned modules route by logical page
and, where a page spans chunks, logical-PC boundary, then execute the selected
chunk's full-PC switch and source-byte guard. The entry point remains the sole
full-MPR/deadline gate; generated part functions are internal implementation
details, not independently callable runtime entry points. A stale mapping, changed bytes, unobserved
PC or unsupported opcode returns a native miss. The host's configured dispatcher
then interprets or explicitly stops; it does not invent a replacement operation.

The manifest retains schema 1 and emits runtime ABI 26. It records the source
observation ABI separately as `capture_runtime_abi`, alongside
`native_instructions_emitted`, capture SHA-256, context count, retained hit
totals and loss metadata. Accepting ABI-12 through ABI-25 observation data does not make
old compiled modules compatible with ABI 26: regenerate and rebuild them.

Both hosts also provide paused, code-free summary and bounded source-page
queries over the current retained set. They report actual and retained tier
counts, loss, completeness and the observed window without finalizing the
private capture. Source IDs are capture-local; a complete retired source span
set is not a chronological trace or a log of individual bus reads. See
[the live query contract](DEV_SERVER.md#paused-code-capture-inspection).

`execution_evidence` remains false: emitting source proves neither successful
compilation nor executed native coverage. Report executed native/interpreted
counts from a separately bounded replay, compare semantic diagnostics and guest
images, and retain an independent reference scope where available.

## Bounded translation units

The default target is 256 supported observed identities per translation unit.
Captures at or below that size stay in one source file. Larger captures split
in deterministic MPR/logical-PC order. Same-PC byte variants stay together;
a single variant group can exceed the target. The manifest records
`partition_size`, `partitioned` and the actual `largest_partition_instructions`.
No guest block chaining or fallthrough is inferred, and compiler optimization
levels are unchanged.

```text
python -m pcerecomp emit-capture .local/capture/run.json --out .local/native/parts --partition-size 512
python -m pcerecomp emit-capture .local/capture/run.json --out .local/native/one --single-unit
```

`--partition-size` accepts 1..4096. `--single-unit` selects the same exact-key
dispatch and body sharing in one translation unit for controlled build
comparisons; it does not restore the former linear variant-chain strategy. The
Python API takes `partition_size=256` and `single_unit=False` keyword arguments.

The additive schema-1 manifest fields `translation_units` and
`generated_headers` are lists of `{file, sha256}` objects. Names are safe
basenames relative to the generated directory. `translation_units` always
starts with `module.cpp`; every other `.cpp` is compiled separately and linked
once, rather than included into another source file. The hashes identify exact
UTF-8/LF file bytes, including the declaration header. Build consumers must
validate and retain every listed source/header identity. Older schema-1
manifests without these lists continue to describe a single `module.cpp`.
Legacy snapshot/CFG emission remains single-unit.

Partitioning is a build organization feature, not execution evidence or a
persistent binary cache. Compare clean builds with the same compiler, flags,
parallelism, source identities and generated operations, and separately verify
native/interpreted execution and guest results.

A capture made under a game-specific patch includes those patched source
identities. Do not promote temporary cheat code into a distributed module.
Consumers can exclude physical source spans during emission without changing
or subtracting from the original capture:

```text
python -m pcerecomp emit-capture .local/capture/run.json --out .local/native/selected --exclude-range 0x100010:2
```

`--exclude-range ADDRESS:LENGTH` accepts decimal or `0x` integers and may be
repeated up to 256 times. Start is a 21-bit physical address; length is positive
and the entire range must fit the physical address space. Any observation with
**any** fetched byte inside an excluded span is omitted, including operands,
separate byte variants, cross-page fetches and logical-PC wrap. Exclusions apply
across MPR contexts according to the recorded physical bytes. Adjacent bytes
outside the span remain eligible. This is source selection, not a guest patch.
An omitted site falls back to the configured dispatcher policy.

The manifest records canonical sorted, deduplicated `excluded_physical_ranges`
(start/length objects), `excluded_observations` and `excluded_retired_hits`.
Original capture retirement/hit totals, completeness, loss counters and SHA-256
remain intact. `unsupported_observations` counts only selected unsupported sites;
emitted sites plus unsupported sites plus excluded sites equal all observations.
The Python API accepts `emit_capture(..., exclude_ranges=((start, length), ...))`.
Keep the raw capture and document why source ranges were excluded. Guarding a
patched identity prevents an accidental match to the original bytes; it does
not make that patch an appropriate production input.
