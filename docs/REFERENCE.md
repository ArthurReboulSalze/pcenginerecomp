# Independent reference check

The reusable [CPU trace interface](REFERENCE_TRACES.md) now supplements the
Gear checks below with a separately compiled original Beetle/Mednafen PCE
core. It preserves raw states, engine/source identities and named comparison
scope, including unavailable state and real reference disagreements. See
[STATUS.md](STATUS.md) for the finite mixed-speed/timer results; this does
not turn either emulator into a hardware oracle or certify complete CPU,
bus, video, audio or retail compatibility.

The optional `scripts/reference_geargrafx.py` harness controls a separately
developed **Geargrafx** emulator through its actual HTTP MCP tools. It starts
and terminates its own headless portable process on a dedicated loopback
port. It does not attach to an owner's emulator session or change an AI
client's plugin configuration.

## VDC retained VRAM bus - ABI 23

`scripts/vram_latch_reference.py --native` independently builds the original
pinned Geargrafx core, the toolkit interpreter and an actual emitted/compiled
native module. Frozen implementation
[`82637854b19fde3b00c2b7fb689687c366602c20`](https://github.com/rages4calm/pcenginerecomp/commit/82637854b19fde3b00c2b7fb689687c366602c20)
has source digest `3758496d120f58b6f4c5afc30b77830fa2a8c1c2e42f82c3dd757bc20f8fb9b8`
over 65 files, ABI 23. The final authored supervisor/probe hashes are separately
bound, including a reference-only unsigned-cast/private-entry compile fix.

All three paths match **31 cases / 65,722 records / 135,397 independent literal
values per path**, including every 16-bit VRAM address. Cases cover driven and
undriven words, buffered CPU reads and all increments, ignored writes, DMA
source/destination/wrap, SATB boundaries, fetched sprite rows and stable
four-bit background scheduling with presentation enabled and disabled.
The address sweep and DMA/rendering cases directly exercise device interfaces.
The two CPU cases actually retire translated operations: **324 native / zero interpreted instructions**,
covering 162 complete source identities in four MPR contexts. Four pure guard
negatives change source bytes or full MPR context. Per-identity hit totals match
training. Raw records include exact CPU timestamps; no clock projection is
used. All eight recorded stages exit zero and 14 preservation groups pass,
covering 542 grouped file bindings.

Gear source remains pinned at `1c62a549328241518101f5be5bf3e6840b96ea5d`.
The adapter explicitly settles its original queued CPU VRAM port operations
before observations; this qualifies data/fetch semantics rather than physical
port stalls. Original operation bodies remain unchanged. Aggregate HDW and
sprite events are tested within the existing toolkit profile, not arbitrary
electrical fetch-slot interleavings or complete hardware timing.

Gear does not supply the toolkit's two-bit background profile. Separately,
`scripts/vram_latch_modes_reference.py` extracts four complete, unchanged
MesenCE functions at `4b8a196e299b3de297b204fd1208d2981562c89b`:
`LoadBackgroundTilesWidth4`, `LoadBatEntry`, `ReadVram`, `GetTilePixelColor`.
Authored state substitutes count the diagnostic callback without changing any
read/decoder body. Both CG halves and every 16-bit pattern/held seed are tested
with driven and bit-11 undriven pattern addresses: **262,144 cases / 2,097,152
pixels / 262,144 held words**, or **2,621,440 compared bytes**. Each path passes
2,359,296 independent literal-value checks. Two-bit patterns retain the fetched
selected word; an undriven pattern retains the preceding fetched BAT word.
This is function-level evidence, not a full Mesen run, CPU trace or bus timing
comparison. All external implementation bodies and generated binaries remain
private and separate from the MIT runtime.

See [VRAM_BUS.md](VRAM_BUS.md) for reset, pure inspection, fetched sprite
ownership and state compatibility. The original two-bit palette/grayscale
proof below keeps its separate historical scope.

## BRAM guest access and raw persistence boundary - ABI 22

`scripts/bram_reference.py --native` independently compiles the pinned
Geargrafx core and the toolkit interpreter, captures actual retired source
identities, emits direct native operations and compiles/runs that module.
The frozen runtime/compiler is
[`aafd99eb5d0ed31b683f6444aa09733d1acbee40`](https://github.com/rages4calm/pcenginerecomp/commit/aafd99eb5d0ed31b683f6444aa09733d1acbee40),
source `67a34d245e09e2bb9890d794c06003e338163d54ec0205712f5da2dfc5129095`
over 64 files, retaining ABI 22. The final public supervisor/probe additionally
bind their exact source hashes and call the actual raw export helper.

The packaging freeze is `d923528bfe822edd0c9c07589cd6fa05be7ffc84`, source
`f9ef132c657eb3acbdc2c072b53a12209bd6a30a3bc531b2424f4ce3894d4059`
over 65 files. An exact source bridge permits only the changed consumer CMake
helper and its new runtime-dependency script; all Python and runtime source
bytes, including the raw-export helper, are unchanged from the oracle freeze.
The final host-input reporting fix is
`05533938a934b823f0ad9590367cac85a797234b`, source
`61c02a0f766f39d8dbf6b66605680679e541255a1d3be628c59321c55a2c9abe`
over 65 files. Its only additional runtime change is a pure effective-input
getter shared by input application and TCP status. All 47 other runtime files
and 14 Python files remain identical to the device oracle's freeze. Fresh
consumer builds and TCP regression qualify final host behavior separately.

Two explicit low/high entry-speed cases match **44 records / 28,842 independent
literal values per path**: full 2,048-byte BRAM, gate, 16 work-RAM bytes and
CPU/MPR endpoints including timestamps. Actual translated code executes
**20,642 native / zero interpreted instructions**, covering 90 complete source
identities in six MPR contexts. Per-identity native hits match interpreted
training. Four complete raw exports per path preserve bytes under protection;
exports leave guest state unchanged, and reload uses fresh CPU/device instances.
Six original Gear invalid-size/short-read checks retain data and CPU/gate state.
All eight recorded stages exit zero; 14 preservation groups bind 480 files.

The Gear source pin remains
[`1c62a549328241518101f5be5bf3e6840b96ea5d`](https://github.com/drhelius/Geargrafx/tree/1c62a549328241518101f5be5bf3e6840b96ea5d).
Its original `Memory::SaveRam` / `LoadRam` operate on the 2 KiB backing memory.
Gear's default formatted seed is explicitly replaced through its original
loader with the same authored bytes used by the toolkit. The authored HuCard
reference fixture explicitly enables CD presence and public backup-RAM
configuration; no guest memory/register implementation is replaced. Raw and
LF-normalized source pairs and 40 objects are recorded separately. The first
preflight omitted backup enable and correctly saw unmapped `$F7`; that failed
fixture epoch is preserved separately from final qualification.

This is guest access/payload evidence. Gear's direct host-file truncation,
title-derived naming and formatted default are not copied into the toolkit.
Host namespace, checksum, lock, publication/failure and Unicode handling are
separate authored tests. No retail save flow, electrical access phases,
power-loss durability, save-state or complete-device restoration is certified.
See [PERSISTENCE.md](PERSISTENCE.md) for exact ownership and failure limits.

## Invalid CD command framing - ABI 27

`scripts/cd_unknown_reference.py --native` freshly compiles the original
Geargrafx/Beetle cores and both toolkit tiers. All 248 unrecognized IDs plus
four abort/lifetime cases run in each reference. The NEC domain validates
1,784 records per engine; the legacy domain validates 520. Framing, held ACK,
sense payload and explicit wire/reset differences remain separate assertions.
The authored autonomous toolkit guest executes 23,241 instructions in each
tier with zero native fallback and 893 conserved source identities; its
reported CPU/tick vector, 44 observed RAM bytes and pending sense match.

The two emulator references intentionally disagree. Gear completes one byte
with GOOD and has no SENSE payload; Beetle frames six/ten/twelve bytes and
rejects invalid CDBs. Toolkit error status/message remain `$02/$02` versus
Beetle's `$01/$00`. Toolkit reset clears a partial CDB; Beetle retains its
cursor on warm reset. No hardware or cross-core guest-cycle parity follows.
See [profiles, exact sources and rerun command](CD_UNKNOWN.md).

## NEC CD sense and read recovery - ABI 22

`scripts/sense_reference.py --native` builds separate executables around the
complete, unchanged pinned Beetle SCSI implementation, pinned Geargrafx and
the exact supplied toolkit source. The final freeze is
[`c6525a278f13709ecc39a2cb85be1b3ebf17a430`](https://github.com/rages4calm/pcenginerecomp/commit/c6525a278f13709ecc39a2cb85be1b3ebf17a430),
with canonical compiler/runtime digest
`79f5e81b0f6fea41d468e64cc1433ebaaf643ea49ac29c3a45f456b2ad44dd91`
over 62 files, ABI 22.

The Beetle adapter compares **four groups / 288 records / 6,836 data bytes**:
all 256 allocation values, no-error/repeated sense, pending error through
success/warm reset, consumption at dispatch even on abort, cold clearing,
and bounded READ error/recovery categories. Every field, row order, value
and type is checked against literal expectations. Toolkit and Beetle payloads
and lifecycle match; **eight known error replies** retain the exact raw
Beetle status/message `$01/$00` versus toolkit `$02/$02` difference. The
comparison permits only that tuple change with every other field identical.

Geargrafx checks **eight baseline responses exactly**, including TUR,
missing-medium directory status/reset, authored TOC replies and real data
READ with manual/automatic acknowledgement. Its four REQUEST SENSE replies
at allocations 0/1/18/255 deliberately have **zero data bytes**, while the
toolkit returns 18. Both raw outputs are preserved and checked as a declared
disagreement; Gear's shortcut is not used as the sense-data oracle.

The toolkit interpreter also runs an authored guest using ordinary LDA/STA
MMIO: READ on an audio track, CHECK CONDITION, REQUEST SENSE, then TUR GOOD.
Its real capture is emitted and compiled into guarded direct operations.
The native guest retires **19,618 native / zero interpreted instructions**,
covering **442 full identities / three MPR contexts**. Full CPU/RAM endpoints
and every per-identity tier hit total equal the training path; emitted code
contains no per-op interpreter bridge. The guest diagnoses one error and
requests sense once; pending sense is clear at its endpoint. This is actual
native toolkit execution evidence, separate from independent SCSI behavior.

All **15 recorded subprocess stages** exit zero and all **16 preservation
groups** pass, binding source blobs, framework inputs, compiler/libraries,
objects, fixtures, generated module, captures and raw outputs. Gear's raw CRLF
sources and private normalized copies are separately hashed; compile copies
match the pinned Git blobs. Forty Gear objects and seven generated artifacts
are included in the final graph. No GPL implementation is copied into or
linked with the MIT runtime.

The Beetle executable privately compiles seven exact upstream blobs, including
the original complete `scsicd.cpp`, command/FIFO/CD utility/filter headers and
math helpers. Authored framework substitutes provide deterministic media,
inert UI/notification services, rejection of unused save-state operations and
an invalid-Q checksum stand-in. The CDIF raw-read/validation predicates inject
success or failure outcomes; they do not independently test physical sectors,
ECC/EDC or the toolkit's MODE1 validator. No original command decoder,
sense formatter, phase or ACK operation is replaced. The adapter drives the
original DB/SEL/ACK/RST setters and `SCSICD_Run`.

These are settled device transactions, not reference CPU or clock traces.
Beetle's automatic mode is a supervisor-issued ACK pulse; Gear and toolkit
automatic mode use their actual `$1808` port. First-REQ service order, 900-tick
metadata pacing, status/message encoding and drive latency are not claimed
identical between all three. Pinned Beetle's initial READ `>` leadout check
also differs from the toolkit's deliberate `>=` rule at exactly leadout.
The independent out-of-volume vector uses LBA 25 on a 20-sector volume;
crossing leadout uses start 19/count 2. See [CD_SENSE.md](CD_SENSE.md) for the
separate mid-stream provider policy and terminal integrity-fault boundary.

```powershell
python scripts/sense_reference.py --beetle-source .local/beetle-source --gear-source .local/gear-source --tool-source .local/frozen-tool --native --compiler clang++ --library PATH_TO_LIBCHDR --library PATH_TO_STATIC_DEPENDENCY --out .local/new-sense-reference
```

Supply exact source revisions and repeat `--library` for required static
dependencies. Six authored record/fixture tests accompany the adapter.
Earlier preflight source/logs remain distinct from the final frozen result;
an initial authored supervisor name collision was corrected without changing
an emulator body. This finite scope does not certify hardware, tray insertion,
unit attention, subchannel data, full CD support, audio or campaign behavior.

Primary sources:
[Beetle NEC SCSI](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/cdrom/scsicd.cpp),
[Gear SCSI](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.cpp).

## Timer divider phase - ABI 21

`scripts/timer_reference.py --native` builds separate adapters from pinned
Geargrafx 1.8.4 and an exact supplied toolkit tree. Five authored cases compare
**1,389 observations**, with **631 independent literal checks per path**.
All 256 reload bytes, reset/same-disabled phase zero, control transitions to
3,072, 16/15/1-tick prediction boundaries, stopped waits, running reload writes
and interrupt acknowledge/mask behavior are included.

Two ordinary guest programs execute actual timer LDA/STA operations at low
and high speed. An interpreted capture is emitted and compiled into a direct
native module; the native run executes **756 instructions, zero interpreted**,
covering **579 identities / three complete MPR contexts**. CPU/MPR/timestamps,
timer state and stored response bytes match Gear exactly within these cases.
The low/high programs retire 186/570 instructions respectively. Actual native
and interpreted source keys and total hits also match; this bookkeeping is
toolkit execution evidence, separate from the independent device observations.

The reference fixture is frozen at
[`ef843af3a82f9838b3de38c771860e5bd552abae`](https://github.com/rages4calm/pcenginerecomp/commit/ef843af3a82f9838b3de38c771860e5bd552abae).
The Ys III integration uses the earlier
[`e45f57c9255983a503655df417a28c7e04103bb6`](https://github.com/rages4calm/pcenginerecomp/commit/e45f57c9255983a503655df417a28c7e04103bb6)
freeze; both have exactly the same 62-file runtime/compiler digest
`e4c078d136b76775bcc296e1d2857bbad520716afa6ea9b607e86fcb89d9ebba`.

The adapter observes the private divider through a read-only member-access
bridge and clocks Gear's unchanged hardware scheduler. Direct device-edge
cases use chunks of at most three master ticks, rather than asking Gear's
single-tick-oriented timer helper to process an arbitrary long jump.
CPU entry speed is explicitly configured in both probes; CSL/CSH then select
that same speed. Timer/counter/phase state is not injected. These are authored
initial conditions, not authentic high-speed reset or cross-speed instruction
qualification. The toolkit's existing split-cycle CSH transition intentionally
differs from Gear's selected-speed timing; see [CPU_SEMANTICS.md](CPU_SEMANTICS.md).
The earlier fixture's 27-versus-9-tick failure is retained separately and is
not relabeled as a pass. No timestamp fields are removed from the final comparison.

Eight subprocesses exit naturally with zero status, and all thirteen report
preservation groups pass. Raw Gear CRLF sources are hashed separately from
private normalized compile copies, which match the pinned Git blobs.
No GPL emulator implementation is copied into or linked with the MIT runtime.

```powershell
python scripts/timer_reference.py --gear-source .local/reference-source --tool-source .local/frozen-tool --native --compiler clang++ --library PATH_TO_LIBCHDR --library PATH_TO_STATIC_DEPENDENCY --out .local/new-timer-reference
```

Replace library placeholders and repeat `--library` for each static dependency.
Six authored model/record tests check the adapter's arithmetic and refusals.
This finite comparison does not certify physical hardware, electrical bus
phases, general IRQ redesign, retail compatibility or listening quality.
The separate paused-capture queries have authored purity/window/loss checks
and an actual native Ys III integration; Gear does not verify toolkit-specific
capture tiers, local source IDs or TCP pagination.

Primary sources: [Gear timer clock/read/control](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h),
[CPU reset state](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280.cpp).

## Arcade Card Duo - ABI 20

`scripts/arcade_reference.py --native` builds isolated adapters from a supplied
exact toolkit tree and pinned Geargrafx 1.8.4. Authored media is configured for
Arcade mapping, CD presence and Super Card RAM through three disclosed
configuration-only member-access shims, followed by the unchanged memory/CPU
reset methods. No CRC is spoofed and no device/CPU operation is patched.
Gear's block-transfer microsteps are grouped through a read-only transfer-state
observer before recording one complete instruction.

Four cases cover control modes, offset/base wrap, triggers, all register and
hole boundaries, port mirrors, shifts/rotates and actual guest data transfers.
Gear, interpreter and generated native code match **28,494 observations**;
each independently passes **28,363 literal expectations**. The actual capture
has **123 identities in five full MPR contexts** and the main native guest
executes **128 native / zero interpreted instructions**. Twenty-eight guards
and four source-byte patch/restores are separately counted. Restoring bytes
does not undo loader-generation changes or imply whole-bus rollback.

A separate interpreted port-fetch fixture checks five observations and three
literal facts: LDA consumes two live port bytes and retires once. Its actual
toolkit capture reports one unreadable instruction and zero identities. That
test is not native execution and is not merged into the 128-retirement native
claim. Native guards refuse side-effecting sources before mutation.

The report binds exact source, compiler/object/library, fixture, capture,
module, executable and raw output identities. Gear raw sources with CRLF
differences are separately hashed; private compile copies must match the
pinned Git blobs after line-ending normalization. GPL reference code stays
private and is not copied into or linked with the MIT runtime.

```powershell
python scripts/arcade_reference.py --gear-source .local/reference-source --tool-source .local/frozen-tool --native --compiler clang++ --library PATH_TO_LIBCHDR --library PATH_TO_STATIC_DEPENDENCY --out .local/new-arcade-reference
```

Replace library placeholders and repeat `--library` for each required static
dependency. Six authored model/boundary tests accompany the adapter. The
finite reference does not qualify Arcade Card Pro, electrical reset/bus
phases, real hardware, persistence, retail games, audio or campaign behavior.
Two separately built authored native consumers check the real host/TCP path;
their internal agreement is not additional external emulator evidence.

Primary sources:
[Gear Arcade Card device](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/arcade_card_mapper.cpp),
[address arithmetic](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/arcade_card_mapper_inline.h),
[CPU routing](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory_inline.h).

## Enhanced HuCard mappers - ABI 19

`scripts/mapper_reference.py --native` builds isolated adapters against an exact
supplied toolkit checkout and pinned Geargrafx 1.8.4 source. SF2's authored
2.5 MiB image selects Gear's mapper normally. For the authored Populous image,
the adapter explicitly configures the 32 KiB card-RAM size after media loading,
then calls the unchanged memory/CPU reset APIs. This configuration-only access
shim avoids the reference's CRC database; no mapper operation is patched.

Six reset cases cover all sixteen SF2 latch addresses, ignored write data,
fixed/switched ROM windows, non-latch writes, Populous aliases, surviving ROM
and real low-speed guest subroutine execution. Gear, interpreter and generated
native execution match **27,982 observations**, with **27,766 independent
literal checks per path**. Actual training contributes **33 identities / six
MPR contexts** and the fresh module executes **210 native / zero interpreted
instructions**. Four switched immediate variants share logical PC, complete
MPRs and mapped physical address. Eighteen guards and six deliberate authored
patch/restores are separate checks; byte restoration does not roll back loader
generation counters or the complete bus.

The report binds raw source/compiler/object/module/fixture/output artifacts.
The local reference source has CRLF differences from Git; fresh private compile
copies are normalized and checked against exact pinned Git blobs. This is not
a claim that the original raw checkout is clean. Reference code remains in
private compiled adapters and is not copied into the MIT runtime.

```powershell
python scripts/mapper_reference.py --gear-source .local/reference-source --tool-source .local/frozen-tool --native --compiler clang++ --library PATH_TO_LIBCHDR --library PATH_TO_STATIC_DEPENDENCY --out .local/new-mapper-reference
```

Replace the library placeholders with real files and repeat `--library` for
every static dependency required by the selected libchdr build. No library
download or discovery is implicit. Use explicit Gear/toolkit source, compiler
and fresh private output arguments. Six authored boundary tests check typed records,
literal maps, changed-source refusal and safe CMake path admission. Independent
reference evidence excludes header conversion, physical board detection,
electrical reset, persistence, analog output and exact CPU bus phases.

Separate actual-capture consumer tests qualify four fresh official packages,
headless/SDL for each profile. Ten-frame TCP routes execute 280,496 native
SF2 instructions or 298,026 native Populous instructions per host, with zero
fallback, guard misses or RAM edits. Each profile executes four actual source
variants and matches its interpreted checkpoints/hits; changed source is
refused before the first instruction. These are internal integration checks,
not additional independent emulator semantics observations.

Primary sources:
[Gear SF2 mapper](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/sf2_mapper.cpp),
[address-latch selection](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/sf2_mapper_inline.h),
[card RAM mapping](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory.cpp).

## Two-bit backgrounds and digital monochrome - ABI 18

`scripts/video_modes_reference.py` accepts exact separately supplied source
files from [MesenCE commit 4b8a196](https://github.com/nesdev-org/MesenCE/tree/4b8a196e299b3de297b204fd1208d2981562c89b).
It compiles the complete unchanged
[default filter header](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/PCE/PceDefaultVideoFilter.h)
with authored framework substitutes, plus four byte-identical extracted
[VDC method definitions](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/PCE/PceVdc.cpp).
Hashes and line spans identify every source body. Generated reference code,
external sources and compiled adapters remain private and separate from the
toolkit executable; no reference implementation is linked into the runtime.

The adapter checks **512 RGB grayscale entries and 1,048,576 two-bit palette
indices**, exhausting every selected pattern word in both CG halves. The
unselected word is its complement. Independent literal truth tables check
all pattern observations; corner literals and equal-channel checks also
check the digital grayscale output. All **1,050,112 output bytes** match.
The grayscale fixture supplies the toolkit's standard RGB palette explicitly,
so this is not a comparison with MesenCE's default palette.

```powershell
python scripts/video_modes_reference.py --mesen-source .local/reference-inputs --probe .local/build/pce-video-modes-probe.exe --compiler clang++ --out .local/new-video-reference
```

Supply `PceVdc.cpp` and `PceDefaultVideoFilter.h` from that exact pin and build
with `PCE_BUILD_REFERENCE_PROBE=ON`. The script verifies input hashes before
creating outputs, refuses an existing output directory, and records compiler,
probe, source, adapter and raw-output identities. Five authored boundary tests
check source rejection and byte-preserving extraction.

This is isolated method/filter execution, **not a full MesenCE emulator run**.
The fixture explicitly seeds CG latch state; the reference's CG self-assignment
is not evidence for latch behavior. CPU execution tiers, VRAM fetch scheduling,
MWR latch edges and analog output are outside this adapter. MAME uses a
[different studio-range grayscale policy](https://github.com/mamedev/mame/blob/master/src/devices/video/huc6260.cpp).

Pinned Geargrafx 1.8.4 ignores both background mode 3 and grayscale control.
Its fresh comparison therefore qualifies the retained four-plane color path:
**16 complete frames / 786,432 pixels**, including palette and scroll history,
match byte for byte. Do not describe the new modes as Gear-qualified.

Separate authored actual-capture-to-native consumers check integration.
Their 134 observed identities emit direct operations, with no interpreter
bridge. Two fresh official verify/build/run sequences execute **10,000 native
instructions each**. Separate headless/SDL TCP routes each execute
**440,607 native / zero interpreted instructions over 15 frames**, with zero
guard misses. Five controller-driven pictures per host match independent
pixel literals; CPU/source/device checkpoints also match the interpreted
training route. Memory edits are disabled, input release works and natural
TCP quit returns 0. These native comparisons are internal integration evidence,
separate from the MesenCE decoder/filter and Gear color-path checks.

## HuCard references - ABI 18

`scripts/hucard_reference.py --native` builds independent adapters against an
unchanged pinned Geargrafx 1.8.4 source and a clean supplied toolkit checkout.
Eight authored ROM sizes (8, 24, 128, 256, 384, 512, 768 and 1,024 KiB) cover
56 cases and 23,200 raw observations: reset seeds/vectors, all ROM windows,
absent memory/CD I/O, preserved latches, WRAM aliases and regional controller
pins. Independent literal checks pass 21,640 expectations per adapter.

Eight actual interpreted training runs compose 3,072 retirements into 111
source identities across 17 full MPR contexts. The real emitter compiles a
separate native-only probe which repeats all plans: 3,072 native instructions,
zero interpreter fallback and matching raw observations/per-identity counts.
There are 168 refusal checks and 56 deliberate authored source patches whose
bytes are explicitly restored; generation counters retain their intentional
loader changes. New guest traces avoid CSH transitions, leaving the existing
documented clock disagreement unchanged.

The authored external adapter uses Gear load/configuration/state APIs and a
compile-time access shim for its unchanged hardware scheduler, as in the reset
adapter. No Gear source or state is patched. Source/compiler/object graphs,
input ROMs, actual captures, emitted module and raw outputs remain bound in the
report. This is finite emulator-reference evidence, not retail compatibility,
electrical power-on, mapper-board detection or whole-library certification.
Dump header/bit conversion is tested independently; Gear receives decoded
authored ROM bytes. The selected 512 KiB map is a compatibility choice, not a
claim that every physical board has that decode. See [HUCARD.md](HUCARD.md).

## BIN/CUE media references - ABI 17

`scripts/cue_reference.py` builds an authored adapter against an unchanged,
separately supplied Geargrafx 1.8.4 media reader. It uses its public image API;
this is separate from the HTTP/guest-emulation adapter above. No reference
implementation is copied into the MIT runtime.

Six entirely authored single-file/multiple-file images cover cooked/raw MODE1,
AUDIO, stored/virtual pregaps, mixed raw/audio tracks, quoted paths and an
audio-first layout. **114 observations**, all **59,392 data bytes** and
**28,224 signed audio samples** match independently declared expectations,
Geargrafx, the C++ provider and Python reader. Six complete-image digests also
match independent record encoding. Unsupported layouts retain explicit faults.

A separate compiled toolkit probe performs **14 CD READ streams**, seven per
execution tier, using actual emitted LDA/STA operations. Each tier reads 14
sectors with matching payloads, status/message and ACK counts. The native
runs execute **114,877 native / zero interpreted instructions**, with zero
guard misses or read errors; interpreter runs execute the same instruction
count in their own tier. This checks the toolkit's command-stream integration;
the independent Gear comparison qualifies media geometry and byte decoding,
not whole-guest CD timing. A further 32 finite parser vectors check C++/Python
acceptance consistency, which remains internal evidence.

Run the adapter with an existing reference source and a probe built with both
`PCE_BUILD_TESTS=ON` and `PCE_BUILD_REFERENCE_PROBE=ON`:

```sh
python scripts/cue_reference.py --gear-source .local/reference/gear-source --probe build/pce-cue-oracle-probe --out .local/new-cue-reference --compiler clang++
```

The report binds the exact external source/header/object/compiler graph,
authored images, raw observations, production readers and actual probe.
The caller's toolkit build provenance remains separate. See
[media contracts and limits](MEDIA.md). This adds no physical-drive, EDC/ECC,
seek-time or hardware-conformance claim.

## System Card reset references - ABI 17

The driver also supports **native-only qualification** with `--native` and
`--tool-source` selecting a clean toolkit checkout. It records actual authored
execution, lowers the captured source identities through the real emitter,
compiles a separate translated module and probe, then repeats the same external
reference plans. A missing native translation stops explicitly. Existing
compiler/CMake/Ninja and external-library paths must be supplied as needed;
the driver does not fetch dependencies.

The native run preserves the original **38 cases / 29,824 observations** and
adds **12 separate mirrored-ROM fetch cases / 120 observations**. Actual
captures contain **303 identities in 20 full MPR contexts**; all are emitted.
The combined compiler input is explicitly composed from two complete authored
runs, not relabeled as one execution.
The compiled probe retires **1,320 native / zero interpreted instructions**,
with exact raw native/interpreted records. Original comparisons retain the
36 disclosed CSH clock differences below; mirror-case clocks agree with Gear.
Separate guard checks produce **200 refusals**; 100 deliberate authored source
mutations are explicitly recorded and restored. This is finite authored
reset/mirror coverage, not native retail firmware or whole-game qualification.

`scripts/reset_reference.py` compiles the unchanged Geargrafx 1.8.4 core at
`1c62a549328241518101f5be5bf3e6840b96ea5d` separately from the MIT runtime.
Both probes load authored System Card media and use explicit reset controls.
The **38-case / 29,824-observation** comparison includes 1,260 CPU snapshots,
36 complete 109-field device snapshots, 14,944 memory observations, 13,568
source peeks and 16 identification-port reads. Explicit seed/vector/mapping
expectations add 29,356 independent checks per implementation. Actual
compiled objects, libraries, probe/source epochs, fixtures and raw outputs
are bound before execution; no reference code is linked into the toolkit.

Architectural/device/memory values agree. The 36 existing CSH speed changes
retain an 18-master-tick difference; the driver records raw clocks and a
specific transition adjustment. It does not remove arbitrary state fields or
claim exact physical reset/bus-phase timing. Gear's default formatted BRAM is
replaced only by an explicit authored seed in both test fixtures; the runtime
does not format saves on reset. Undefined CPU/MPR/RAM values are deterministic
reference choices, not invented hardware guarantees.

Separate private Gear execution with the actual clean firmware and actual
read-only CHD reaches the System Card menu. At frames 120 and 600, all 256 ×
237 overlapping pixels match; complete images are unequal because the
documented active-VDC and fixed-VCE viewports have different origins. This
is a bounded firmware-menu comparison, not independent whole-game or mixed
retail-audio parity. See [reset contract](SYSTEM_CARD_BOOT.md) and
[actual execution scope](STATUS.md#system-card-reset-boot---abi-17).

## Base compatibility references - ABI 16

The separate `scripts/sprite_reference.py` adapter compiles unchanged Geargrafx
1.8.4 core sources at `1c62a549328241518101f5be5bf3e6840b96ea5d`. Its fully
authored 8 KiB HuCard loads through the public media API and normal reset.
The existing disclosed clock bridge then advances the actual master scheduler;
only authored initial registers, VRAM and SATB are seeded. **81 cases / 125,922
checkpoints** match both timing-only and continuous-video toolkit modes.
Checks include overflow cell budgets and partial wide admission, opaque sprite
zero collision behind an opaque background, clipping, flips, heights, two-bit
pattern selection, cached fetches, CR gating, acknowledgment, burst/vertical
windows, and all three VCE divisors. A separate original-core memory check
passes **131,072 WRAM alias readbacks and four actual LDA/STA source aliases**.

The final execution binds 130 reference blobs, 40 fresh compilation units,
four external libraries, the actual wrappers/probes and raw outputs. Authored
source epochs are archived. Two earlier wrapper-startup failures remain
separate failed receipts; no runtime change was required by those failures.

`scripts/brk_reference.py` independently compiles the same unchanged core with
normal `RunInstruction` semantics, without `GG_TESTING` or debug-BRK behavior.
**3,040 cases / 5,280 checkpoints per toolkit execution tier** agree on CPU/MPR
state, complete 256-byte stack pages and cumulative instruction clocks. Cases
cover all flags, stack wraps/aliases, PC wrap, mapped vectors, both CPU speeds,
BRK/RTI and already sampled IRQs. One earlier wrapper reset/mapping failure is
preserved separately. Exact consumed source epochs and the executed probe are
archived; this is not whole-core clock or full-RAM parity.

Pinned MAME source corroborates ignored-signature skipping. Pinned Mesen source
fetches that byte as an immediate operand; neither was executed for this
comparison. The selected Gear profile, CPU bus-phase approximation, undriven
VRAM limits, and lack of retail sprite/hardware qualification stay explicit.
GPL reference executables are external and are not linked into the MIT runtime.
See [COMPATIBILITY.md](COMPATIBILITY.md).

The separate ABI-16 consumer qualification replays the retained assisted
94,800-frame route through TCP, including fresh desktop legacy/Gear/audio-off
builds and headless comparisons in both audio timing profiles. These are same-tool regression and
packaging checks. They are distinct from the authored independent Geargrafx
CPU/device comparisons above, and do not provide independent retail mixed-audio
or hardware parity. The new command diagnostics identify the route's 53
reference-profile responses as `$FF`; a strict-policy prefix separately
confirms an explicit fault on its first occurrence. That is diagnostic fault
evidence, not implementation of the command. See
[the full execution scope](STATUS.md#abi-16-consumer-integration).

## CDDA sample-latch reference — ABI 15

`scripts/cdda_latch_reference.py` separately compiles the unchanged Geargrafx
1.8.4 core at `1c62a549328241518101f5be5bf3e6840b96ea5d` with an authored
wrapper. Its disclosed C++ member-pointer bridge calls the original core's
`ClockHardware<true,false,false>(1)` scheduler; it injects neither source
samples nor clock/fader state. Actual audio comes from an authored CUE/BIN
through public media and drive controls. SCSI command reception is bypassed.

Nine cases / **367 distinct checkpoints** match with toolkit PCM on and off.
Comparisons include both signed latest source channels, both latch bytes,
selected side, master time and BRAM before/after status reads. Cases cover
699/700-tick admission, rejected writes, all 256 write payloads, ignored high
port writes, signed extrema, pause/stop/reset-to-stop, data-track silence and
post-fader holds under real clock advancement. Fresh core construction starts
each reference case; resetting a nonzero latch in the same core is covered
only by authored runtime tests. The data-track fixture aligns the initial
head to the requested track and does not prove seek-distance parity.

The final execution binds 130 exact Gear source/header blobs, 40 fresh
compilation units, four external dependency libraries and the actual probe,
wrapper and runtime sources. All 229 bindings rehash unchanged at completion;
45 authored source files and the executed toolkit probe are also archived.
Earlier development epochs remain separate. The GPL reference executable is
not linked into the MIT runtime. CPU bus scheduling, retail mixed PCM,
variable drive seek latency and analog hardware remain outside this check.
See [the selected port contract](CD_AUDIO.md#guest-sample-latch) for explicit
Geargrafx/Mesen/Beetle disagreements.

## Digital audio reference — ABI 13

`scripts/pcm_reference.py` controls a new isolated Geargrafx 1.8.4 portable
child using authored BIOS/BIN/CUE data. The final PCM probe SHA256 is
`80148c57e9e58132b983c3c7e8abb46b221f584194482a4dd9d4272661fdee0a`.
The run matches **56 raw CDDA stereo pairs / 112 scalar samples**: 40 audio
pairs and 16 data-track silent pairs. Gear reports the next sample index;
the adapter selects the preceding generated LBA/frame, including sector wrap,
then compares both signed channel values without masking or gain projection.
The authored session leaves the CD fader disabled.
It independently waits for seek and playback delay to settle. It does not
assume matching sample-clock or seek phases.

Another **24 settled PSG waveform-index checks** match at frequencies 64,
127 and 512 after the DDA-to-wave transition. Mid-period checkpoints avoid
claiming exact CPU bus-access/oscillator edge alignment. MCP exposes waveform
index and port state, not raw PSG/ADPCM decoder PCM or hidden noise/LFO state;
those are not called sample parity. Analog filtering, reference resampling,
mixed PCM, audio devices, retail sound and hardware remain outside the run.
CUE is used for this sample oracle; CHD byte order/mapping tests use authored
decoder ABI doubles and primary-format evidence, not Gear decompression parity.

The final owned child stopped, its temporary portable configuration was
removed and all three authored input hashes remain unchanged. An initial
probe refused because command STATUS completed before the playback-delay
interval; the adapter now observes both deadlines separately. No guest
implementation or sample expectation was changed for that refusal.

Separate internal ABI-13 retail qualification reproduces all **93,735**
retained assisted Ys III frames, **25 complete guest PNG hashes** and the
original **709 RAM transactions / 723 changed bytes**. Every original final
guest JSON value remains exact against the previous full-native ABI-12 run,
including 2,920,491,782 native / 981 interpreted retirements, 981 guard misses
and all 460,685 block instructions natively. The new validated `audio_output`
object, ephemeral port and SDL host telemetry are separate; no original guest
field is projected away. The run generates 69,095,406 PCM frames with all three
sources active and zero runtime queue discard. Unthrottled device output is
intentionally muted, so it supplies digital-data and guest-state evidence,
not speaker playback or an independent retail-route audio oracle.

A separate paced SDL stream accepts/drains 930,219 input frames with pause
flushing accounted for, without a listening or analog loopback claim. The
full run uses the unchanged assistance journal, response profile and volatile
BRAM; it establishes no new progression, victory or unassisted route. All
owned test hosts stopped. Whole RAM, composed pixels, complete retail sound
and hardware parity remain excluded. See [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md)
for reproduction, source licenses and primary links, and [STATUS.md](STATUS.md)
for the complete source/mixer/queue, public-build and consumer scopes.

## Retained CPU/device reference checks

On Windows x64, Geargrafx **1.8.4** produced the following separate results.
The speed batch agrees on CPU state/speed but has documented timing differences.
The observed-code batch below checks the new compilation/dispatch path with
authored observations; it does not add hardware or full retail-route parity.
The retained CD batch checks the limited idle profile described in CD_CONTROL.md.
The retained VDC port suite checks settled register/VRAM state; it does not
compare raster events or dynamic access timing. The separate raster suite
checks the clocked video profile. The CD transport suite separately checks
settled selection, command reception and status/message completion. The TOC
suite adds actual metadata response bytes and bounded DATA IN handshakes.
The joypad suites compare CPU accesses and guest-observed controller bytes
under held input snapshots, separately with and without CD hardware.

| Run | Opcodes | Comparisons per tier | Scope |
|---|---|---|---|
| Original baseline, retained prior evidence | 47 | 188 native and 188 interpreter | Four register/flag variants each, including both conditional-branch outcomes |
| Observed-code dispatch (`scripts/capture_reference.py`) | 21 compiled identities across seven full MPR contexts | 156 CPU/MPR/latch states, 156 instruction clock deltas and 78 complete 8 KiB RAM comparisons per tier | 78 authored plans; native tier executes all 156 instructions with zero fallback; 306 additional local guard-miss checks; no retail-route or hardware parity |
| Bit/stack batch, retained prior evidence (`--suite bit-stack`) | 24 | 128 native and 128 interpreter | Four base variants each, plus four extra directed variants for each of eight stack opcodes |
| Data batch, retained prior evidence (`--suite data`, four completed shards) | 97 | 1,552 native and 1,552 interpreter | 16 vectors per encoding; all C/D/T/V combinations, indexed/indirect data addressing and full-RAM comparison |
| RMW/JMP batch, retained prior evidence (`--suite rmw-jump`, two completed shards) | 32 | 512 native and 512 interpreter | 16 vectors per opcode; edge values with both carries, T/D/V contexts, indexed memory and consecutive jump pointer bytes |
| Bit-test/branch/BSR batch, retained prior evidence (`--suite bit-test-bsr`, two completed shards) | 30 | 480 native and 480 interpreter | 16 vectors per opcode; zero/full/mixed bits, flag contexts, zero-page/indexed targets and stack wrap |
| MPR sequence batch, retained prior evidence (`--suite mpr`, four completed shards) | TAM/TMA | 1,614 instruction states and 524 final RAM/latch comparisons per route | 524 sequences; native-first: 1,078 native + 536 interpreted after MPR changes; pure interpreter: 1,614 interpreted |
| Speed batch, retained prior evidence (`--suite speed`) | CSL/CSH, NOP and TMA #0 | 120 CPU/speed states and 24 final RAM/latch comparisons per tier agreed | Not rerun this batch; 92 matching tick deltas and 28 documented transition differences per tier |
| Idle CD-control/BRAM batch, retained prior evidence (`--suite cd-control`, two completed shards) | Existing CPU loads/stores/indexed/RMW and TMA #0 | 720 CPU/device states and 48 complete work-RAM/BRAM comparisons per tier pass | 48 sequences; 720 native instructions vs 720 interpreted; real CD hardware enabled with authored bootstrap/disc; no retail inputs |
| Clocked CD command-handshake batch, retained evidence (`--suite scsi`) | CPU port accesses and settling NOPs | 743 settled CPU/device checkpoints and 21 full work-RAM/BRAM comparisons per tier pass | 21 authored plans; 1,007,851 native instructions vs 1,007,851 interpreted; original frozen probe observations bridged exactly to that batch's final build, three added edge plans checked live; no media responses or exact access-phase proof |
| TOC/DATA IN batch, qualified scope (`--suite toc`) | CPU port accesses and settling NOPs | 1,964 settled CPU/device checkpoints and 25 full work-RAM/BRAM comparisons per tier | 25 of 26 plans qualified; 653,294 native vs 653,294 interpreted instructions; eight earlier TOC plans bridge exactly to the final probe; one pending-response reset plan crashes Geargrafx and remains unqualified |
| Joypad batch (`--suite joypad` and `--suite joypad-cd`, eight completed shards each) | Port loads/stores and RMW | 2,512 CPU/port-output checkpoints and 56 complete 8 KiB work-RAM comparisons per tier pass | 56 authored plans: 28 HuCard and 28 authored-CD; 2,512 native vs 2,512 interpreted instructions; USA region line, both CD-presence states; no internal controller-state, host event scheduling, hardware or gameplay qualification |
| Settled VDC batch, retained prior evidence (`--suite vdc`, eight completed shards) | ST0/ST1/ST2, ordinary port loads/stores and settling NOPs | 856 settled CPU/VDC states and 48 complete work-RAM/VRAM comparisons per tier pass | 48 authored sequences; 14,552 native instructions vs 14,552 interpreted, including 16 settling NOPs per tested operation; standard non-CD, non-SuperGrafx HuCard profile |
| Clocked raster batch, retained evidence (`scripts/raster_reference.py`, fifteen completed shards) | Direct device-clock probe | 4,165 exact-clock checkpoints and 15 guest acknowledgements total | 15 authored timing plans; default VCE divider 4 and 262 lines; no per-tier live CPU or bus-phase claim |

Each single-step comparison checks A/X/Y/SP/P, logical PC, all eight MPRs and all 8 KiB
of work RAM after one instruction. No flags are masked out. The new vectors
explicitly cover both states of every selected bit, SP `$00/$01/$FE/$FF`,
zero/positive/negative pulled values, and every saved B/T combination for PLP.
An initial PLP mismatch exposed MAME's different internal B representation;
the runtime now follows Geargrafx/Mesen's B=0 restoration, with T preserved.
See the [instruction contract](CPU_SEMANTICS.md).

The data input matrix has 16 vectors per opcode, covering every C/D/T/V
combination with zero, sign, valid BCD and invalid-nibble inputs. It sets
zero-page operands to `$FF`, absolute bases to `$22FF`, and indirect pointers
to `$22FF`, exercising zero-page pointer wrapping and indexed page crossings.
T destination/source and pointer-high-byte aliases remain visible in the
full-RAM comparison. Immediate bytes remain the compiled `$20`; variable
operand values are exercised through memory forms. The exhaustive byte-pair
tests described in CPU_SEMANTICS are local expected-value tests, not an
exhaustive run against Geargrafx.

The RMW/JMP input matrix pairs each of `$00/$01/$02/$7F/$80/$81/$FE/$FF`
with both incoming carry states. It varies T/D/V and uses X values
`$00/$01/$E0/$FF`. All 30 RMW encodings and both indirect JMP forms are
selected. Jump pointer bytes are consecutive across `$22FF/$2300`, with
multiple targets including `$FFFF`; the test ends after JMP and does not
execute its destination. Full-address-space wrap and cross-MPR cases use
additional local native fixtures; they are not live Geargrafx evidence.

This uses self-authored synthetic HuCard/bootstrap code and synthetic RAM
patterns. Initial emulator registers/MPRs are randomized, so the harness
first establishes and verifies its mapping/speed, then sets registers
explicitly for every case. It restores mapping after TAM. It compares both
the native tier and the interpreter directly with the reference.

**Not checked by the earlier suites:** cycle/bus phases, IRQ entry/delivery, speed-change timing,
block transfer, unsupported opcode semantics, devices, CD, sound, rendering
or any game. This is independent single-step evidence, not whole-system
conformance or proof the reference emulator is infallible.

## Reproduce

Build the optional probe from the entirely synthetic fixture generator:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPCE_BUILD_REFERENCE_PROBE=ON
cmake --build build --config Release --parallel 4
```

Obtain a portable Geargrafx release from its [official releases](https://github.com/drhelius/Geargrafx/releases).
Use a dedicated copy under `.deps/geargrafx-oracle/`, including its required
runtime files. The harness refuses an executable outside this project's
`.deps/` directory. It creates `portable.ini` and writes no retail saves.
No emulator or binary is included or downloaded by the harness.

The baseline Windows artifact was:

| Identity | Value |
|---|---|
| Archive | `Geargrafx-1.8.4-desktop-windows-x64.zip` |
| Release | `1.8.4`, published 15 October 2026 |
| Archive SHA256 | `c1aceb116acf1949ab2319c217f3c0c9e9fcf836f8857176b670a749d8a2347c` |
| Executable SHA256 | `742b2d8d21060368134324e1ce6c32a9751e7a9776549ed78448eca93e6e8563` |

The archive digest matched GitHub's release-asset `digest` field before use.
The research register retains both the original main-branch pin and the
separate 1.8.4 source pin `1c62a549328241518101f5be5bf3e6840b96ea5d`,
used for the bit/stack and data semantics. This does not assert a reproducible
source-to-binary build of the supplied release executable.

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-oracle-probe.exe
```

That default selects the full current opcode set (2,848 single-step cases per tier).
The expanded default matrix has not been rerun live in this batch. It does not
include the directed MPR, speed, CD-control, CD-transport, TOC or VDC sequence suites below.
Large runs can exceed the 180-second cap; partition them with
`--shard-count 8 --shard-index N` for each N from 0 through 7, using a distinct
output folder for each. Every shard records the exact checked opcode list;
all shards must pass to claim the complete selected suite.

To reproduce the data batch, run four commands sequentially, substituting
N with each value from 0 through 3:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-oracle-probe.exe --suite data --shard-count 4 --shard-index N --out .local/data-check/four-N
```

Their disjoint opcode lists must cover all 97 data encodings and their totals
must sum to 1,552 comparisons per tier. Each run remains incomplete until
its entire shard passes. All four lists and comparison totals were checked
at closeout; they cover every selected encoding exactly once.
To select only bit/stack, use `--suite bit-stack --out .local/bit-stack-check`.
The full expanded all-opcode matrix has not been run in this batch; retained
checks remain separately identified above.

For the RMW/JMP batch append `--suite rmw-jump --shard-count 2 --shard-index N`
and `--out .local/rmw-jump-check/shard-N`, with N=0 and N=1 in separate
sequential runs. Their opcode lists must be disjoint, cover all
32 selected encodings and total 512 comparisons per tier. Each vector is
checked independently against both execution tiers. The exhaustive RMW
byte/status sweep is a local expected-value test, not an exhaustive oracle run.
Both completed reports and their combined opcode coverage/totals were verified.

For the bit-test batch use `--suite bit-test-bsr --shard-count 2 --shard-index N`
and `--out .local/bit-test-check/shard-N`, with N=0 and N=1 sequentially.
The disjoint reports cover all 30 selected opcodes, totaling 480 comparisons
per tier. Memory cases use `$FF` / `$22FF`, TST's compiled mask is `$55`,
BIT's compiled immediate is `$20`, and relative fixtures branch to themselves
when taken. BBR/BBS exercise both selected-bit states, and BSR varies SP
through `$00/$01/$FE/$FF`. Other displacement/fetch-wrap checks are local
expected-value tests; this is not exhaustive oracle testing of literals.

### MPR and transfer-latch sequences

The dedicated suite checks every TMA/TAM mask, zero-mask preservation,
ordinary memory traffic between transfers, same-value TAM writes, and
multi-register OR under a second mapping. Every sequence ends with TMA #0,
observing the reference latch through A; Geargrafx's MCP API does not expose
that latch directly. Mapping and latch resets execute actual LDA/TAM
instructions from RAM, rather than assuming debugger register writes reset
hidden CPU state. MPR1 stays mapped to work RAM so fetches remain valid.

Run four commands sequentially, substituting N with 0 through 3:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-oracle-probe.exe --suite mpr --shard-count 4 --shard-index N --out .local/mpr-check/shard-N
```

The disjoint reports must cover 524 sequence IDs and total 1,614 instruction
states per tier, plus 524 complete RAM/latch comparisons per tier. The
`native` route here is **native-first**: a changed MPR context makes its next
generated guard yield, with counted interpreter fallback. This differs from
the single-step suites' entirely native comparisons. Each sequence starts
with a native operation; same-mapping sequences remain native. Reports
include actual native/interpreter/guard counts, the probe hash and the exact
checked sequence IDs. The local expected-value suite separately executes
every mask directly in generated code under its compiled mapping.

These sequence checks do not add live cycle, speed-change or device evidence.
All four completed reports were checked for disjoint sequence IDs and complete
coverage. Native-first totals were 1,078 native instructions, 536 interpreted
instructions and 536 guard misses. The pure interpreter retired 1,614
instructions. Both routes matched every recorded instruction state and all
524 final RAM images/latch observations. Earlier single-step results were
retained and were not rerun in this batch.

### Speed transitions and the timing discrepancy

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-oracle-probe.exe --suite speed --out .local/speed-check/reference
```

This bounded suite has 24 authored sequences: both entry speeds, both speed
opcodes, four status contexts and repeated/mixed selections with following
NOPs and TMA #0. Actual LDA/TAM instructions reset mapping and latch; an
actual speed instruction establishes entry speed before registers are set.
Every measured instruction remains in work RAM under the compiled mapping.
There is no interpreter fallback in the native route.

CPU-entry timestamps come from Geargrafx's in-memory `cpu.instructions`
trace. A sentinel NOP supplies the end timestamp for the last measured
instruction. The adapter requests the current tail explicitly: the API's
`next_sequence` is a page cursor, not automatically the logger's latest
position. It rejects missing entries, stale/wrong bank/PC, non-monotonic
timestamps and overruns. Only the current bounded sequence is fetched;
full traces and retail captures are not written to the repository.

Both tiers matched **120 CPU/speed states and 24 final RAM/latch observations**.
The live trace matched 92 instruction tick deltas per tier. In the remaining
28 cases per tier, the CPU changed speed and Geargrafx charged all three
cycles at the selected speed. The runtime instead uses two entry-speed cycles
plus one selected-speed cycle, agreeing with the pinned Mesen and Beetle
source implementations. High→low CSL is 18 ticks here versus Geargrafx's 36;
low→high CSH is 27 here versus Geargrafx's 9. Same-speed selections agree.
See [CPU_SEMANTICS.md](CPU_SEMANTICS.md#cslcsh-and-speed-transitions) for sources.

The report result is **`architectural_pass_timing_discrepancy`**, with every
observed difference retained as compact metadata. Unexpected state or tick
results fail the run; the adapter does not broadly ignore timing. A known
transition difference is not presented as reference timing parity. Mesen and
Beetle were source cross-checks, not live executions in this batch. This
focused CPU timestamp schema does not complete issue #4's general bus/event
trace schema, second oracle or hardware verification.

### Idle CD control and BRAM

Build the normal test targets, then run N=0 and N=1 sequentially:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-io-tests.exe --suite cd-control --shard-count 2 --shard-index N --out .local/io-check/shard-N
```

This suite uses **`pce-io-tests`**, whose generated module has fixed hardware/
BRAM MPR aliases. It differs from the ordinary opcode probe. The harness
creates a shared authored 256 KiB reset bootstrap and a 300-sector blank
CUE/BIN under its private output parent. Geargrafx accepts that bootstrap as
an unknown-CRC System Card; the warning is expected. No known firmware CRC
is forged and no retail firmware is supplied. Media status must prove CD
hardware is enabled: HuCard-only tests could otherwise compare disabled
hardware that ignores writes. The child remains an isolated portable process,
and any synthetic BRAM files belong to that authored test media.

Each case establishes mapping/latch through actual CPU transfers, resets the
idle CD control state through CPU writes, and seeds exactly 2 KiB synthetic
BRAM plus 8 KiB work RAM. Every measured instruction compares unmasked CPU
registers/PC/MPRs and independently exposed device state: BRAM gate, ACK,
IRQ-enable/active fields, reset and IRQ2 line. The full work RAM and BRAM
contents are compared at the end. Plans cover zero/full/mixed control values,
both lock states, ignored/read-only writes, logical aliases, all BRAM boundary
classes, indexed hole crossings and TSB/TRB read-to-lock side effects.
Each sequence ends with TMA #0 so ordinary I/O cannot silently alter its latch.

The completed disjoint lists cover 48 sequences exactly once and total **720
instruction-state comparisons plus 48 full memory comparisons per tier**.
The native route retired 720 native instructions with no interpreter fallback;
the interpreter route retired 720 interpreted instructions. The local C++
suite separately checks 61,440 expected instruction cases and fatal refusal
of unsupported subcode/register accesses. Those exhaustive local byte sweeps
are not exhaustive Geargrafx runs.

This is byte/state evidence for an idle profile. Nonzero IRQ source
combinations are local/source-level checks, not live device events. It does
not verify transport, subcode, audio, IRQ delivery, device/bus timing, hardware
or gameplay. Reference disagreements and deliberately unsupported `$1807`
reads are documented in [CD_CONTROL.md](CD_CONTROL.md). Earlier emulator
checks retain their original scope and were not rerun in this batch.

### Settled VDC register and VRAM sequences

Build the normal test targets, then run N=0 through N=7 sequentially with a
separate output directory for each shard:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-vdc-tests.exe --suite vdc --shard-count 8 --shard-index N --out .local/vdc-check/shard-N
```

This suite uses **`pce-vdc-tests`** and an authored 8 KiB bootstrap. Every
run verifies that Geargrafx loaded a standard HuCard mapper with CD hardware
and SuperGrafx disabled. It establishes mapping through actual CPU transfers,
initializes the exposed VDC register state and primes the hidden read buffer
through an actual MARR high-byte write before seeding synthetic VRAM. Display,
interrupt sources and automatic DMA remain disabled in the reference profile.
No retail firmware, disc or owner save is used.

The adapter executes each target operation followed by **16 settling NOPs**.
It then compares unmasked CPU registers, PC and all eight MPRs, the VDC
selector and all twenty register values. A full 8 KiB work-RAM image and
64 KiB VRAM image are compared at each sequence's end. The directed plans
cover all 32 selectors, byte writes and masks with DMA triggers excluded,
mirrored ports and MPR aliases, all four address increments, MAWR boundaries
and ignored upper-half writes, buffered VRAM read/write streams and dedicated
ST0/ST1/ST2 routing. CR interrupt/display bits and DCR automatic-transfer
bits stay constrained; upper-half reads requiring the rendering-bus latch
are explicit local faults rather than live reference cases.

All eight completed shard lists cover **48 unique sequences** exactly once.
They pass **856 settled instruction/device observations and 48 full RAM/VRAM
comparisons per tier**, using the same emulator and probe hashes. The native
route retires **14,552 native and zero interpreted instructions**; the pure
interpreter route retires **14,552 interpreted instructions**. Each route
contains 856 tested operations and 13,696 settling NOPs. The probe's SHA256
is `80ffe5c39ac6414d4ab753afc2cc89dc8d6246d35ab9fb9ba53374669b344b30`.

These are settled functional comparisons. They do not compare busy intervals,
status event generation/acknowledgement, raster behavior, dynamic stalls,
IRQ delivery, DMA, rendering or timing. The settling NOPs also clear T, so
these observations cannot isolate when the target operation clears T; the
local independently expected instruction cases check that immediate result,
fixed access waits and both clock speeds. The local suite separately checks
77,824 CPU cases, 8,192 register-width cases and 392,991 VRAM transfer/address
cases plus status, guards, deadlines and unsupported-operation faults.
Those broader local cases are not exhaustive live Geargrafx evidence.
Earlier live suites retain their original scope and were not rerun this batch.

### Clocked CD command handshake

The `--suite scsi` adapter uses **`pce-scsi-tests`**, whose authored RAM
fixture explicitly enables the transport profile. It uses the same isolated
synthetic bootstrap and blank CUE/BIN as the idle CD suite, verifies that CD
hardware is enabled, and establishes MPRs through actual CPU transfers.
Retail firmware, disc bytes and owner saves are not used.

Run three shards sequentially, substituting `N` with 0, 1 and 2:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scsi-tests.exe --suite scsi --shard-count 3 --shard-index N --out .local/scsi-check/shard-N
```

Plans cover the host data latch, idle/held ACK, reset, six-byte TEST UNIT READY
under different IRQ masks and MPR aliases, and reset aborts during selection,
partial command reception, held ACK and status. Added edge plans check extra
ACKs after status consumption, reselection while already in COMMAND, and
signal changes under held reset. Observations compare unmasked
CPU registers/PC/MPRs, exposed SCSI phase/signals and drive data byte, ACK,
IRQ-enable/active fields, reset, IRQ2 and BRAM gate. The final 8 KiB work RAM
and 2 KiB BRAM are also compared for every plan. CPU `$1801` reads separately
observe the host latch when the drive is not sending a byte.

Finite authored delay loops advance Geargrafx by the same master ticks as
real generated/interpreted NOPs in the runtime probe. Scratch RAM and loop
registers are restored before each settled comparison. Deliberately generous
settling intervals avoid qualifying access phases as exact cycle boundaries;
the local independent suite checks literal deadline edges separately.

The completed evidence covers **21 unique plans**, passing **743 settled
checkpoints and 21 full work-RAM/BRAM comparisons per tier**. The native route
retires **1,007,851 native and zero interpreted instructions**; the interpreter
route retires **1,007,851 interpreted instructions**. Each route includes 743
observed operations and 1,007,108 settling NOPs.

The first 18 plans ran in three six-plan live shards against frozen probe
SHA256 `aed2d3604e751f229297d48566fad43e44ee2315466398ffcdb7d4ba70b26375`.
After additional edge fixes, all 18 plans produced exactly equal complete
JSON in both tiers against the final probe, including CPU/device observations,
full RAM/BRAM and instruction counters: 615 checkpoints, 18 memory comparisons
and 891,071 retirements per tier. This is an equivalence bridge, not another
live emulator run. The three added plans then ran live individually against
the final probe, adding 128 checkpoints and three memory comparisons per tier.
That batch's final ABI-6 probe SHA256 was
`bda34df2ffe2fc3be16c41683676eec732bb296155628cd3475a2e5bbea2a3eb`.
The reproduction command above partitions the current 21-plan matrix into
three seven-plan shards; it is equivalent coverage, not the exact historical
partition used for the retained proof.

This checks settled control transactions, not a sector backend, media
readiness, REQUEST SENSE, TOC/subcode, CDDA/ADPCM, CPU interrupt delivery,
hardware drive latency or gameplay. Geargrafx's response delays are an explicit
reference profile, with Mesen differences documented in [CD_CONTROL.md](CD_CONTROL.md).
Earlier suites retain their original evidence and were not rerun live in
this batch.

### Directory/TOC and DATA IN

The `--suite toc` adapter uses **`pce-scsi-tests --probe-toc`** through the
normal reference client. It creates a separate authored twelve-track CUE/BIN:
86 sectors per track, 1,032 total, with first/last tracks marked data and the
others audio. The reference's exposed metadata must match those actual tracks,
INDEX 01 LBAs and leadout before CPU comparisons begin. A synthetic System
Card bootstrap enables CD hardware; no retail BIOS/disc/save is supplied.

To reproduce the qualified selection, run the following command sequentially
with `N` equal to **0, 1, 2, 3, 5 and 6**:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scsi-tests.exe --suite toc --shard-count 7 --shard-index N --out .local/toc-check/shard-N
```

Then run these individual plans with `I` equal to **4, 11 and 18**:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scsi-tests.exe --suite toc --shard-count 26 --shard-index I --out .local/toc-check/case-I
```

The public matrix retains all 26 plans. Its remaining plan, index 25
(`toc-reset-auto-response-pending`), reproducibly crashed the isolated
Geargrafx 1.8.4 child twice with access violation `C0000005` in `ucrtbase.dll`.
It has no completed independent comparison and is **unqualified**, rather
than a passing or ignored mismatch. The local literal reset expectations
and source checks pass separately. This limitation also prevents calling a
full seven-shard matrix an all-pass result. The named plan remains available
as a reproducer through `--shard-count 26 --shard-index 25`; it is excluded
from the qualified commands above, without being removed from the matrix.

Plans cover all three supported `$DE` modes, BCD count and MSF replies,
track zero/valid audio/valid data/above-last-track and `$AA` leadout selectors,
manual and `$1808` auto-ACK, IRQ masks, MPR aliases, transfer reselection and
reset. Every observed instruction compares unmasked CPU registers/PC/MPRs,
SCSI phase/signals and actual drive byte, ACK, IRQ-enable/active fields,
reset, IRQ2 and BRAM gate. Final 8 KiB work RAM and 2 KiB BRAM are compared
per plan. Guest loads observe each response byte; expected bytes are not
injected into the reference bus.

Finite reference delay loops and actual translated/interpreted NOPs provide
the same elapsed master ticks, with reference scratch/register restoration
as in the control suite. These remain settled comparisons, not exact CPU
access phases. Local tests separately check literal 9,000/900/21/3,000-tick
boundaries, BCD limits, malformed metadata and refusal. The live selection-abort
checks retain Geargrafx's observed active IRQ `$60` until ACK clears REQ;
the source/reference difference is described in [CD_CONTROL.md](CD_CONTROL.md).

The retained 21-plan control suite was also bridged to the final ABI-7 probe:
complete JSON is exactly equal in both tiers, including 743 checkpoints,
21 full RAM/BRAM comparisons and 1,007,851 retirements per tier. This preserves
the earlier live evidence without claiming another independent emulator run.

The completed report is **`qualified_pass` for 25 of 26 registered plans**,
with **1,964 settled CPU/device checkpoints and 25 full work-RAM/BRAM
comparisons per tier**. The native route retires **653,294 native and zero
interpreted instructions**; the interpreter route retires **653,294 interpreted
instructions**. Each route includes 1,964 observed operations and 651,330
settling NOPs. The crashing plan's 50 potential checkpoints are excluded from
these totals because no independent result exists for them.

Eight plans from original shards 0/3 ran live against frozen probe SHA256
`2a870243460e18b0aa7e758068951090b387fdadcc3d424d09ffbdfc84788f5a`.
Their complete JSON then matched exactly in both tiers against the final
probe: 616 checkpoints, eight RAM/BRAM comparisons and 160,566 retirements per
tier. The remaining 17 qualified plans ran live against the final probe,
using seven-way shards 1/2/5/6 and individual indices 4/11/18. These bridges
compare full CPU/device states, memory and counters; they are not additional
live emulator runs. Final ABI-7 probe SHA256 is
`d11be952c49c3788f3ecb9968d5bbc0b9896fda58e12e0f0c2399b67514fcef9`.

This suite does not qualify physical drive response length/timing, sector
reads, media-content authentication, REQUEST SENSE, subcode, CDDA/ADPCM, CPU
interrupt delivery or gameplay. In particular, the four-byte response profile
follows Geargrafx/Mesen; Beetle's differing lengths remain documented.

## Clocked raster reference

The separate `scripts/raster_reference.py` harness compares the direct
clocked device probe **`pce-raster-tests --clock`** with Geargrafx. Its authored
HuCard executes finite CPU delay loops; debugger observations provide VCE
master-clock positions, VDC dot/line positions, horizontal/vertical phases,
latched status and local IRQ1 assertion. Explicit elapsed-clock checks reject
a delay which does not arrive at its expected VCE position. This is direct
device-clock evidence, not a native/interpreter instruction comparison.

Fifteen plans combine standard, short, narrow, delayed and oversized vertical
geometries with disabled, enabled and display-enabled CR contexts. They sample
startup and two-frame timing, including line/frame boundaries and status
accumulation. A stable guest status-port read checks acknowledgement at the
end of each plan. This suite uses the default VCE dot divider 4 and 262 lines;
the other VCE controls have local expected-value coverage, not live parity.
Register setup uses debugger writes; their CPU write phases are not qualified.

The completed run passes **4,165 exact-clock checkpoints and 15 guest status
acknowledgements across all 15 plans**, using one frozen direct probe with
SHA256 `a3baeb7a17e7c5d9d3334af0ed3a484c80bb6e7e2a65643ddb49e36c8b0ceaaa`.
The five earlier passing plans each contain 277 checkpoints; the remaining
ten contain 278 after adding one interior checkpoint. The current public
client includes that checkpoint for every plan, so a fresh complete run has
4,170 checkpoints. The retained combined result is 4,165; it is not inflated
to the newer matrix size.

The final rebuilt probe has SHA256
`1b8d401e0c3cf2c443b10859cb153e621a4b19b69f43155bb13648b51826f45c`.
All fifteen retained clock inputs produce byte-identical JSON against the
live-tested frozen probe: 4,165 checkpoints and 15 acknowledgements. This
bridge checks that added local tests and acknowledgement-window guards did
not change the retained device observations; it is not another emulator run.
The final probe also rejects an enabled event inside a status-read observation
window, avoiding an ambiguous acknowledgement comparison.

To reproduce, run fifteen commands sequentially with `N` from 0 through 14:

```sh
python scripts/raster_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-raster-tests.exe --shard-count 15 --shard-index N --out .local/raster-check/shard-N
```

Each run starts its own dedicated portable child and rejects CD/SuperGrafx
hardware profiles. Shards have a 180-second runtime limit, MCP responses are
bounded by the shared 2 MiB reader, and direct probe calls time out after ten
seconds. The compact report begins as incomplete and becomes a pass only after
all selected observations agree. The child is terminated on success or error.
No rendered video, retail image, firmware, owner settings or saves are used.

The local independent suite separately exercises literal event edges, CR
changes at event boundaries, raster-register changes, vertical latches,
partition independence, all eight low VCE timing controls and CPU retirement
cadence at both speeds. Neither this direct device reference nor those local
checks establishes CPU bus-phase accuracy, interrupt delivery, dynamic VRAM
waits, DMA, rendering or hardware qualification. Gear/Mesen event differences
are retained in [VDC.md](VDC.md).

On other hosts supply the corresponding executable filename. On a
multi-configuration build the probe may be under `build/Release/`. Those
reference sessions have not yet been run by this project.

The default output is ignored `.local/geargrafx-check/`. A compact
`result.json` records emulator identity and exact check scope. A failing
run retains one synthetic mismatch and exits nonzero; it cannot reuse a
previous pass as the current result. Work is bounded to 180 seconds, MCP
responses to 2 MiB each, and probe invocations to five seconds. No frame or
audio dump is enabled. The harness always terminates only its own child.

The reference check is optional and outside the default CI suite, so a
green synthetic CI job must not be reported as a fresh independent-reference
run. A second independently developed reference and hardware test vectors
remain useful next work.

## Joypad I/O sequence adapter

The `pce-joypad-tests --probe` fixture uses authored instructions in work RAM.
Run each command for shard indices 0 through 7, with at most two isolated
reference children at once:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-joypad-tests.exe --suite joypad --shard-count 8 --shard-index N --out .local/joypad-check/cart-N
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-joypad-tests.exe --suite joypad-cd --shard-count 8 --shard-index N --out .local/joypad-check/cd-N
```

All sixteen final shards passed: **56 plans, 2,512 CPU/port-output checkpoints
and 56 complete 8 KiB work-RAM comparisons per execution tier**. The native
route retired 2,512 generated instructions and no interpreter steps; the
interpreter route retired 2,512 interpreted instructions and no native steps.
Held button state is set through Geargrafx MCP; expected CPU registers,
flags, MPRs and guest-read port bytes come from the independent emulator.
No flags or port bits are masked out. Internal controller structs are not
compared directly; their behavior is observed through actual guest port reads.

The plans cover all twelve individual buttons, released/full/mixed masks,
two/six-button pads, five distinct pad snapshots and mixed types, TurboTap
advance/reset/overflow, repeated SEL/CLR levels, every output byte, ten
logical address aliases and RMW side effects. Separate MPR-latch preservation
is a local expected-value check, not an added live TMA observation here. Both
HuCard and authored-CD profiles use isolated synthetic inputs and compare
RAM without publishing retail bytes. The CD plans reuse the authored blank
media/bootstrap, not the owner's disc or firmware.

Geargrafx's headless `Auto` setting leaves its console enum as Auto. The
pinned core only asserts the Japanese line for explicit PCE/SGX types, so
these live checks qualify the USA line polarity, with CD present and absent.
The adapter uses that source-defined profile rather than deriving a region
from expected runtime output. An initial Japan-profile assumption failed on
bit 6 and was corrected in the adapter; the runtime was unchanged. The
Japanese bit remains independently expected/source-checked locally, with
no live qualification here. Host input changes during a guest sequence,
electrical timing, peripherals, CPU IRQ entry and gameplay remain unverified.
See [INPUT.md](INPUT.md) for source disagreements rather than assuming all
emulators implement unusual controller edges identically.

The frozen ABI-8 probe used for all final shards has SHA256
`5a4a8f16c590559645d2c31255ec9f73cbce69e879485ca3d1ced1db4e090dab`.
All final reports bind that same probe and the pinned Geargrafx executable.

## CD READ sector adapter

`scripts/read_reference.py` starts a dedicated portable Geargrafx child and
loads an authored 24-sector MODE1/2048 CUE/BIN plus an authored bootstrap.
Every sector has a deterministic, position-dependent payload. No retail
firmware, disc bytes, save files or initialized personal install are used.
Run seven shards, with `N` from 0 through 6, sequentially or at most two at once:

```sh
python scripts/read_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-read-tests.exe --shard-count 7 --shard-index N --out .local/read-check/live-N
```

All seven final shards pass: **201 CPU/settled-CD checkpoints and seven
complete 2,048-byte sectors (14,336 payload bytes) per execution tier**.
The native probe retires 15,552,742 generated instructions and no interpreter
steps; the interpreter route retires 15,552,742 interpreted instructions and
no native steps. Those totals include settling NOPs and port-access stream
instructions; they are not unique translated sites or a performance result.
All reports bind the same frozen ABI-9 READ probe, SHA256
`2887817019e0d837526cb497d3802ed59430310720658ab7d5d42c72e80c1399`.
The final probe, SHA256
`9886dbd21bf93bc7fd282770d67d76531050ba1795eb90ebf4eeb0a224f0d8b0`,
returns identical complete JSON for all seven retained plans in both tiers:
201 checkpoints per route, including payloads and execution counts. This
bridge verifies that the final added local tests and cancelled-command
cleanup preserve the live-qualified observations; it is not another
Geargrafx run.

The reference guest executes finite ordinary HuC6280 read/store loops to
capture all 2,048 payload bytes in work RAM. The toolkit probe executes its
generated or interpreted port-access instructions and returns the full
payload. Both routes compare settled CPU registers, MPRs, guest-observable
CD signals and IRQ levels with Geargrafx. Host register restoration removes
the reference capture loop's scratch registers from these observations.
The loops have different CPU instruction cadence, so this is settled
sector/handshake evidence, not exact access-phase or stream-loop CPU parity.
The complete RAM contents are not compared in this adapter.

The matrix covers manual and `$1808` automatic ACK, distinct first and next
sector payloads, backpressure, ignored upper bits in READ's LBA byte, crossing
the authored leadout, and reset with pending or buffered reads. The zero
count plan aborts before data; its effective 256-sector length is checked
by independent local expectations, not by this live fixture. Settling waits
cover the reference's seek delay, initial random drive phase and 290 ms
backpressure retry. They do not qualify those timings, physical drive
behavior, ECC/EDC decoding, IRQ delivery or gameplay.

Source facts come from the pinned Geargrafx
[READ command and sector loader](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.cpp)
and [clock/IRQ integration](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller_inline.h).
Geargrafx returns GOOD for an invalid starting LBA, while a failed sector
load or a transfer crossing leadout produces CHECK CONDITION. The runtime
deliberately reports invalid media requests as errors; invalid-start parity
is excluded from the live matrix. The runtime's fixed initial seek profile
also excludes Geargrafx's distance-dependent seek and random initial phase.
These differences must not be presented as hardware qualification.

Each shard has a 180-second work limit, 256 KiB process-log limit, shared
2 MiB MCP response limit and 30-second toolkit-probe timeout. Authored media
is reused per output parent. The compact report starts incomplete and becomes
a pass only after every selected checkpoint and payload agrees; failures
retain a bounded synthetic mismatch. Only the child started by the adapter
is terminated, including on exceptions.

## Block-transfer instruction adapter

`scripts/block_reference.py` checks TII (`$73`), TDD (`$C3`), TIN (`$D3`),
TIA (`$E3`) and TAI (`$F3`) against a separate Geargrafx 1.8.4 process.
Build the optional `pce-block-probe` with `PCE_BUILD_REFERENCE_PROBE=ON`.
Run sixteen shards, with `N` from 0 through 15 and at most two children:

```sh
python scripts/block_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-block-probe.exe --shard-count 16 --shard-index N --out .local/block-check/live-N
```

All inputs are authored. A tiny HuCard bootstrap establishes the reference
mapping, then actual guest TAM instructions map every logical page to the
same 8 KiB RAM bank. This deliberately exercises MPR aliases and complete
16-bit address wrap without introducing unsupported MMIO or writable ROM.
Each probe executes one completed instruction in its selected tier. The
adapter compares every CPU register, all flags, PC, all eight MPRs and the
entire 8 KiB RAM image, including the stack's saved and restored bytes.
Native fallback is forbidden: each native case must retire exactly one
generated instruction and zero interpreted instructions; the interpreted
case requires the converse.

The matrix contains **810 plans** across both CPU speeds and four status/SP
contexts, plus ten directed operand/stack aliases. It covers lengths 1, 2,
3, 4, 7, 9, 17, 255, 256, 257 and 1,023; all five zero-length encodings
transfer 65,536 bytes. Forward/backward overlaps, alternating-byte parity,
fixed destinations, source/destination page crossings and wrapping through
`$FFFF` are included. Stack-source and stack-destination aliases expose the
real Y/A/X pushes and X/A/Y pops. In the directed operand aliases, those
pushes modify the encoded destination and length before operand fetching.

All sixteen shards passed: **810 CPU states, 810 complete 8 KiB RAM images
and 810 complete-instruction tick deltas per execution tier**. The native
route retired 810 generated instructions and zero interpreted instructions;
the interpreter route retired 810 interpreted instructions and zero native
instructions. Forty plans exercise zero-length encodings. The frozen probe
used for every final shard has SHA256
`e5fd9765467c29048b78385b7938650d1dc4cc52aa246ce53a6575cf62bdf665`.

Geargrafx's instruction trace suppresses internal transfer microsteps.
One block-entry timestamp and a subsequent host-injected NOP sentinel give
the entire instruction's master-tick delta without storing a per-byte trace.
The CPU/RAM observation is captured before the sentinel is injected. This
qualifies complete-instruction `17 + 6*n` timing for the RAM-only profile,
including zero counts and both speed divisors. It does not qualify the bus
phase of each byte, device waits, interrupts or gameplay.

The pinned Geargrafx implementation re-fetches the opcode between transfer
bytes. This differs from the toolkit's latched, whole-instruction contract
when a transfer overwrites its own opcode. Live fixtures preserve that
opcode: zero-length TII/TDD copy each byte to itself, TIN/TIA use fixed safe
destinations, and zero-length TAI's two source bytes are authored `$F3`.
Self-overwritten opcodes therefore remain outside the independent-reference
claim rather than being treated as an emulator agreement. See the pinned
[transfer implementation](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_opcodes_inline.h)
and [instruction trace filtering](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280.cpp).

The adapter shares the established 2 MiB MCP response limit. Each shard has
a 180-second work limit, 256 KiB process-log limit and five-second toolkit
probe timeout. Only the adapter's own reference child is terminated. The
pass report binds both executable hashes and exact selected plan IDs; a
failing run keeps one bounded synthetic mismatch and remains incomplete.

## IRQ and RTI adapter

`scripts/irq_reference.py` checks interrupt entry and RTI through the optional
`pce-irq-probe`. It supplies an authored System Card bootstrap and blank CD,
then establishes three real pending sources in Geargrafx: VDC VBlank, TEST
UNIT READY status and an expired timer. The timer is disabled while its
request remains pending. Every case checks that all three source lines remain
asserted; mask combinations independently select their delivery priority.
The toolkit probe injects corresponding external request lines, separating
CPU delivery qualification from source timing qualification.

```sh
python scripts/irq_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-irq-probe.exe --shard-count 16 --shard-index N --out .local/irq-check/live-N
```

Use `N` from 0 through 15, with at most two reference children. The matrix
contains 832 plans: all 256 pulled RTI status bytes at both CPU speeds,
256 priority/mask/status/stack plans and 64 CLI, SEI and PLP delay plans.
Each case executes three natural consecutive instructions, comparing CPU
registers, flags, MPRs and PC after each instruction, then every byte of
the 8 KiB RAM image, including the wrapped stack. Distinct authored handlers
identify the selected vector. IRQ entry remains attached to the completed
instruction and must not count as an additional native/interpreted opcode.
Native fallback is forbidden.

All sixteen shards passed: **2,496 CPU states, 832 complete RAM images and
832 complete-sequence tick deltas per execution tier**. Native cases retired
2,496 generated instructions and no interpreted instructions; interpreted
cases retired 2,496 interpreted instructions and no generated instructions.
The frozen live probe has SHA256
`d58353e8b456cf1c0e8de6e7056a23f30f63b9b2fbb8ca320cc263876c147f17`.
All 1,664 complete probe outputs were subsequently bridged to the final
runtime build, including CPU states, full RAM, counters, cycles and ticks.
The final probe SHA256 is
`ac90badcda5eca669d8fa08446609ce83253dfbc64a09a8446ab0a0fa25f82cc`.

An instruction trace and a host-injected NOP sentinel measure the complete
three-instruction master-clock delta. This covers entry's eight cycles and
RTI's seven cycles, both speed divisors, return frames, CLI/PLP delayed
recognition and SEI's already-sampled request. It does not measure IRQ line
access phases, timer-edge accuracy, source cancellation within an instruction,
physical hardware or gameplay.

The source contract comes from pinned Geargrafx
[instruction/IRQ integration](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h)
and [RTI implementation](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_opcodes.cpp).
Hardware-clock callbacks can resample requests during some MMIO instructions;
the ordinary RAM instruction matrix does not qualify those access boundaries.
The adapter uses the existing 2 MiB response limit, a 180-second budget per
shard, a 256 KiB process log and a five-second probe timeout. Only its own
reference child is terminated, including on exceptions.

## Settled palette and DMA adapter

The optional `pce-video-probe` and `scripts/video_reference.py` compare direct
functional device results with an isolated Geargrafx process:

```sh
python scripts/video_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-video-probe.exe --out .local/video-check/live
```

All **12 authored plans passed**. Eight VRAM-DMA plans cover source and
destination increment/decrement combinations, forward overlap, a one-word
transfer, ignored destinations above `$7FFF` and destination wrap through
`$FFFF`. Three SATB plans cover masked completion, enabled completion IRQ
and automatic VBlank repeat. The palette plan writes and reads all 512
entries, starting at address 509 to cross the nine-bit address wrap, and
verifies low/high byte behavior and the high read port's driven upper bits.

Each plan compares the complete 64 KiB VRAM, 512-byte SATB and 1 KiB palette,
plus palette address, DMA terminal registers, status and IRQ1. The palette
case additionally compares 1,024 actual guest port-read bytes. Geargrafx
executes authored ST0/ST1/ST2 instructions to trigger transfers and finite
masked CPU loops to settle them; the toolkit probe calls device methods
directly. Consequently this is **settled device evidence**, with no native
or interpreter-tier, exact DMA timing, access-phase, renderer, hardware or
gameplay claim. The frozen live probe has SHA256
`e53ab5bb43cf0ff73dd41f0227d232b5febb9298cb25994cc36e4d4a08714a38`.
All twelve complete result hashes also match the final build's probe,
SHA256 `884ae891b6dd270fdc7917eb7f1e9b904efb4ffacc348674097c83f780f0d49f`.

The source facts are pinned Geargrafx
[VDC DMA](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6270_inline.h)
and [VCE ports](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6260_inline.h).
The adapter has a 180-second work budget, 256 KiB log limit, five-second
probe timeout and shared 2 MiB MCP response bound. Only its own child is
terminated. Reports bind executable hashes and authored plan results;
failures retain a compact mismatch instead of complete repetitive dumps.

## Continuous video pixel adapter

The optional `pce-scanline-probe` and `scripts/scanline_reference.py` compare
guest-clock frame history with the pinned portable Geargrafx 1.8.4:

```sh
python scripts/scanline_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scanline-probe.exe --out .local/desktop-check/reference/live
```

All **four plans, 16 distinct frame comparisons and 786,432 pixels passed**.
Each comparison includes all RGB bytes of a 256 by 192 VDC active viewport.
The authored fixtures exercise 32/64-column backgrounds, horizontal and
vertical scroll wrap, sprite priority, wide sprites, flips and two-bit sprite
mode. Each plan captures a settled frame, a frame with a live palette change
inside a visible line, a frame with horizontal scroll changed between line
latches, and a frame with pattern VRAM changed after the current line was
decoded. Every plan requires four different, nontrivial images. This checks
historical output that a final-state snapshot cannot reproduce.

The live reference probe has SHA256
`3425a3d430a696fdacce5b77da4fd926fa7a453c0d2ce9ebdb78b6063c02652f`.
All 16 complete RGB frame hashes and all publication sequence/tick records
also match the final build's probe, SHA256
`87bad0dffaeb9db7a9a56c76be43aed21ec410dbf38cfb1c75c95bf3afffe9ee`.
Reports bind this executable, the Geargrafx executable, each complete RGB
frame hash and local publication sequence/tick. Successful sequences are
2/3/4/5 at ticks 715,260 / 1,072,890 / 1,430,520 / 1,788,150.

Geargrafx's MCP `get_screenshot` returns the raw emulator framebuffer as PNG,
without desktop scaling or CRT shaders. Its headless debug viewport is
256 by 242, covering physical lines 14 through 255. The fixture's HSR `$0202`,
HDR `$041F`, VSR `$0F02`, VDR 191 and VCR 64 place the complete active image
at `(0, 3)` within that viewport. The adapter requires exactly this framebuffer
size and compares the full fixed crop; it does not search for a matching
subimage or move the crop to hide mismatches. Standard RGB profile 0 uses
each three-bit channel multiplied by 255 and divided by 7. Source facts come
from the pinned [VCE clock and screen bounds](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6260_inline.h),
[RGB palette conversion](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6260.cpp),
[VDC line rendering and latches](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6270.cpp)
and [raw screenshot export](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/platforms/shared/desktop/emu.cpp).

Debugger memory/register writes occur while Geargrafx is paused. Authored,
finite guest CPU delay loops advance to the specified master-clock phases;
the local probe advances the device clock directly. VRAM debugger offsets
are word offsets, and palette memory writes change the same live color table
used by the reference renderer. This is device rendering evidence for a single
VDC, divider 4 and 262-line frames. It does not qualify CPU execution tiers,
port-access phases, all timing/mode changes, collision/overflow IRQs, hardware,
retail frames, desktop presentation, audio or gameplay. Geargrafx publishes
its raw visible viewport near line 256; the toolkit publishes its VDC active
crop at frame wrap. Captures occur after both publications; identical pixels
do not establish identical publication timestamps.

The adapter permits 180 seconds, a 1 MiB child log and 2 MiB per MCP response.
It retains at most 16 reference PNGs and 16 local PPMs, all authored synthetic
content. Its PNG decoder validates CRCs, dimensions, format, filter method and
decompressed extent without another imaging dependency. Failed comparisons
retain a bounded pixel mismatch. Only its own child process is terminated.

## Settled ADPCM and PSG adapter

The optional `pce-audio-probe` and `scripts/audio_reference.py` check functional
audio-device ports with authored CD media and an authored bootstrap:

```sh
python scripts/audio_reference.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-audio-probe.exe --out .local/audio-check/live
```

All **eight plans passed**, comparing **292 guest port-read bytes** and
complete 64 KiB ADPCM RAM images. Four ADPCM plans write and read 64 bytes
at addresses `$0000`, `$0001`, `$FFDF` and `$FFFF`, including address wrap,
both rising-edge address-offset modes, the pipelined initial read latch,
settled status/control/sample-rate reads and soft reset preserving RAM.
Four PSG plans exercise disabled channel selections 0, 3 and 4, invalid
selection 7, frequency masking, waveform-upload index wrap, DDA-mode index
reset, noise-enable selection, global registers and shared I/O-latch reads.
PSG observations include all six channel register/index/mode states.

Geargrafx's MCP `amplitude` field represents channel balance, and its `dda`
field is the DDA-enable flag; it does not expose the DDA sample or waveform
RAM. The adapter maps those fields according to the pinned
[debug adapter source](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/platforms/shared/desktop/mcp/mcp_debug_adapter.cpp).
The frozen successful probe has SHA256
`a53cf55bcfec274420969d5e7295d8dc69fb8634cd9f896f8350271b85149fb2`.
All eight complete result hashes also match the final build's probe,
SHA256 `4f9fd7d701a6fc3cde13d1ae765fdb65ddc702d36b70c472b3554d5733eeb5ce`.

The reference runs real guest accesses with finite settling loops; the local
probe calls bus ports and advances device time directly. This qualifies
settled manual port effects, not CPU execution tiers, memory-slot phase
accuracy, ADPCM DMA or playback, PSG waveform bytes or oscillators, mixed
PCM, hardware or gameplay. Playback and DMA retain separate local/source
evidence. The adapter has a 180-second work budget, 256 KiB log limit,
five-second probe timeout and shared 2 MiB MCP response bound; it terminates
only its own child. Failures retain compact synthetic mismatch data.

## Unknown-command response and BRAM readback adapters

Two focused suites extend the existing SCSI CPU adapter without rerunning
its retained transport/TOC matrix:

```sh
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scsi-tests.exe --suite scsi-unknown --out .local/transport-extra-check/unknown
python scripts/reference_geargrafx.py --exe .deps/geargrafx-oracle/Geargrafx.exe --probe build/pce-scsi-tests.exe --suite scsi-bram --out .local/transport-extra-check/bram
```

The three unknown-command plans passed **87 CPU/device checkpoints and three
full RAM/BRAM comparisons per tier**, with 129,767 generated or interpreted
instructions per route, including settling NOPs. Unknown first bytes `$FF`
and `$01` produce GOOD status immediately on ACK fall, then complete status,
message and bus-free handshakes. A normal six-byte TEST UNIT READY command
following `$FF` also completes. Native fallback is forbidden. The probe
explicitly enables the reference unknown-command response quirk; the normal
strict unsupported-command profile remains separate. This establishes bus
response behavior, not implementation of unknown command operations, direct
internal command-buffer observations or audio continuation.

Four BRAM plans passed **27 CPU/device checkpoints and four full RAM/BRAM
comparisons per tier**, retiring exactly 27 instructions per route. Literal
read expectations qualify Geargrafx's `$1807` gate readback: `$80` unlocked,
`$00` locked. Repeated reads preserve the gate, reading `$1803` locks it,
writing `$1803` leaves it unchanged, and only bit 7 of `$1807` writes controls
unlocking. Exact `$B807` MPR aliases are included. An unused decoded CD port
at `$1901` returns `$FF` without changing the BRAM gate, before and after
status-port locking. This is the Gear reference
profile; it does not qualify a subcode interpretation of this port or
persistent saves.

The frozen unknown-command probe has SHA256
`be5e81782750934045a0d1bea22d8ab3796c914f62d8e0bbd55cc2962f44deab`.
All six complete unknown-command outputs match the final SCSI probe,
SHA256 `e21931a630100d5dd0c1c9b557436ac0b78854215d7654a0f56fdac5ca56a2f8`.
That final probe was checked live against all four BRAM plans, and its eight
complete result hashes were checked again at closeout.
Reports retain complete probe-result hashes for final-build bridging. Inputs
are authored bootstrap, blank CD, RAM and BRAM only. The existing adapter's
time, diagnostic, child-process and MCP bounds apply; access-phase timing,
IRQ delivery, hardware and gameplay remain outside these focused claims.

## Independent Ys III town controls

The town-control batch changed host diagnostics and its explicit execution
allowance; it did not change guest CPU/device semantics. The existing opcode,
transport, timing and synthetic rendering reference results retain their
documented scopes.

An additional isolated Geargrafx 1.8.4 run used the supplied USA disc and
System Card through authentic reset. Four separated Run taps skipped opening
segments; 110 I taps, each two held frames followed by 60 released frames,
advanced the first town dialogue. Two neutral-controlled jump checks then
observed sprite 4 at Y `176 -> 166 -> 176` and `176 -> 164 -> 176`, with X
remaining 160 and no ascent during the preceding neutral intervals. Select
opened the command menu. The successful route stepped 11,230 frames in about
198.2 wall seconds. An earlier bounded attempt remained scripted and is not
control evidence.

Restoring a private checkpoint and repeating jump/landing/Select produced a
command-menu text crop matching the local TCP capture: **72 x 40 pixels,
2,880 pixels, zero differences**, after translating Gear's viewport by
`(+24, +3)`. The blinking cursor and unrelated scene were excluded. This
qualifies that stable menu crop, not full retail-frame geometry, timing or
CPU-state equality. The reference's authentic startup and the toolkit's
IPL-entry sandbox remain distinct.

The local final-binary route separately completed 25,476 frames through town
movement/camera scrolling, jumping, the command menu, world-map travel and
town return. A hidden SDL replay matched five complete guest-image hashes
and every final CPU/device diagnostic to the headless TCP route. It still
used the explicit unknown-command response profile four times. Combat, mine
progress, campaign coverage, audible output, full native/AOT and hardware
qualification were excluded from that retained run. Screenshots, state, media and route data stay
private. All owned reference processes stopped and temporary configuration
was restored; no owner emulator saves were used.

## Independent Ys III first-mine combat

The retained first-mine batch added read-only host SATB diagnostics, not guest CPU/device
semantics. An isolated Geargrafx 1.8.4 run restored the preceding batch's
private genuine-emulator town checkpoint and used normal controller input to
talk to the wounded-miner crowd, unlock Tigre on the world map, visit the
weapon shop and buy Short Sword (400G), Leather Armor (300G) and Wooden Shield
(200G), leaving 100G. The earlier claim that red slots positively established
active starter gear is withdrawn: red highlighting alone was ambiguous, and
the restored reference checkpoint still reports STATUS attack/defense 10/10.
Equipment selection in that reference route is therefore unqualified. Buying
an item does not establish that it is active; corroborating STATUS values
are required. I leaves the equipment screen.

From a 20-HP mine-approach state, entering the mine and holding
Right+II produced an extended sword,
HP **20 → 10**, EXP **0 → 12** and gold **100 → 108**. The visible attack and
reward establish at least one enemy kill; exact kill count remains
unqualified. Received damage, death and a settled Run retry restoring 20 HP
were separately observed. An earlier Run press during the unfinished
GAME OVER transition was too early and is not retry evidence.

The first bounded reference attempt advanced 19,142 frames in 875.0 wall
seconds before its wall limit/process exit; the successful combat continuation
advanced 1,078 frames in 148.7 wall seconds. Twelve requested PNGs and a single
private resume checkpoint were retained. Reference executable SHA256 is
`742b2d8d21060368134324e1ce6c32a9751e7a9776549ed78448eca93e6e8563`,
with source pinned to `1c62a549328241518101f5be5bf3e6840b96ea5d`.
All owned reference processes and command waiters stopped, and temporary
configuration was restored. Media/firmware remained read-only and owner save
roots were not used.

The toolkit separately completed a 31,819-frame TCP route, with selected
starter gear, a visible sword, HP **20 → 2**, EXP **0 → 12** and gold
**100 → 108**, plus earlier death/Run retry. Different starting scenes and
input cadence permit **outcome-class corroboration only**. These are not
equal-damage/reward, complete-frame, CPU-state, complete SCSI trace, exact kill
count, deeper-mine/boss, campaign, audible-output or hardware checks. No guest
runtime patch was necessary or independently qualified by this reference run.
The local route still needs the explicit unknown-command response profile,
used nine times; it remains predominantly interpreted. Screenshots, media,
state, game-derived route data and diagnostics stay private.

The local EXP figure corrects an earlier transcription of 124. Exact glyph
checks on the retained image establish EXP `00012` and the separate RING field
`004`. Equipment selection, attack, received damage and the 8G reward remain
supported; this correction does not create a new combat or boss qualification.

Separately, an exact hidden SDL desktop replay of all 31,819 local frames
matches seven complete guest PNG hashes (death, retry, purchases, confirmed
equipment, sword swing and final combat) and every final CPU/device/source
identity diagnostic to the headless runner. Clearing TCP input while paused
changes only the host button mask. Both runs end by requested TCP quit. This
is internal host-consistency evidence, not an additional independent emulator
or hardware comparison.

## Initial BRAM image and authentic FORMAT provenance

Both runners now accept `--bram RAW_2048_IMAGE`: an optional, read-only file
containing exactly 2,048 raw bytes, loaded into existing volatile BRAM before
execution. Without the option the existing blank initialization is preserved.
The loader does not create a header, format memory, export guest changes or
write the input file. That retained batch used runtime ABI 12. TCP status and final JSON expose
`cd_control.bram_seeded`; an explicit dispatcher allowance of up to
20,000,000,000 steps retains tick deadlines and optional 1–600-second wall
limits. The retained BRAM/debug local and public-source builds passed 20 suites and
155 Python tests with SDL enabled; that batch's default build passed 19 suites with
155 Python tests discovered and four desktop-only skips. Those authored
checks use no retail inputs or private BRAM image.

For a separate private experiment, ordinary controller input selected FORMAT
and YES in the genuine USA System Card UI under Geargrafx 1.8.4. The resulting
blank 2,048-byte BRAM image was read from the reference, with SHA256
`7e631b4e463a04481939fde974cd341a1478af8c1f75350fd73c94a3430a0887`.
No guest-memory write tool, invented filesystem/header or owner save was used.
Supplying this image to the toolkit eliminates the earlier blank-cabinet
startup warning. The raw image, captures and reference receipts remain private.

## Formatted-start guest SAVE/LOAD, STATUS and level progression

The local TCP route uses ordinary inputs to SAVE slot 1 in the Weapon Shop
at frame 17,886. Normal LOAD at frame 18,324 restores that scene with HP 20,
EXP 0, gold 100 and active starter gear corroborated by STATUS strength 20 and
defense 25. This new positive gear evidence is distinct from the withdrawn
red-highlight-only reference claim. Guest SAVE modifies process-local BRAM;
the read-only initial seed's SHA256 remains unchanged. There is no host save
export, automatic writeback or cross-process persistence.

Geargrafx independently starts with authentically formatted BRAM, confirms
STATUS 20/25, and uses normal SAVE/LOAD slot 1 in Sarina. The stable STATUS
text after local LOAD matches Geargrafx: **80 × 32 pixels, 2,560 pixels, zero
differences**, including 587 nonblack local pixels. Gear's viewport is
translated by `(+24, +3)`. Only LEVEL 1, STR 20, DEF 25 and NEXT 100 text is
qualified. Unrelated scene, menu, sprites, cursor and counters are excluded;
this is not whole-frame, damage/reward, timing, CPU-state or hardware parity.

Normal combat with return-to-entrance healing now reaches local
**LEVEL 2, HP 30, EXP 102, gold 168**, with STATUS strength 25, defense 30 and
NEXT 300. A separate Geargrafx route reaches **LEVEL 2, HP 30, EXP 108, gold
172**, with the same strength 25, defense 30 and NEXT 300, and crosses the
hall and four-exit junction. Unequal EXP/gold reflect separate routes and do
not establish exact rewards, damage or route cadence. These observations
qualify level progression and the displayed stat classes. The ordinary local
route continues to the same junction and performs actual Mine Creek slot-3
SAVE/LOAD at HP 17 / EXP 132 before stairway combat ends at HP 6 / EXP 152.
Those normal-input checks do not qualify the boss, full campaign, hardware
or audible output; the assisted boss/replay scope is documented below.
Runtime ABI 12 and the retained 785-site initial
native module were unchanged in that retained initial-module run; its execution
was predominantly interpreted. Expanded-module qualification is recorded below.

### Assisted testing and paused RAM access

The shared TCP host now provides bounded physical RAM/ROM inspection and
explicitly enabled RAM editing. Whole-range expected-byte checks, settled
pause requirements, invalid-bank refusal and source-generation invalidation
are covered by authored socket and host integration tests. The retained BRAM/debug
local and generic public-source builds passed 155 Python tests and 20 suites with
SDL enabled; that default build passed 19 suites, with four desktop skips.
These checks validate the debugger contract, separately from guest semantics.

Before any retail edit, three retained independent Geargrafx RAM observations
were checked against health outcomes: current/max health 20/20, 30/30 and
10/30. Only the observed low-byte values and zero adjacent bytes were
qualified. The title-specific mapping stays private. A separate isolated
Geargrafx experiment edits current/max health to 99 and observes readback;
after ordinary healing updates the cached HUD it displays 099. This is
assisted reference evidence, rather than legitimate level or stat progression.
Unmodified reference checkpoints remain available. Local assisted routes must
record every edit and retain the ordinary-input prefix as a separate result.

The new host first replays the ordinary-input route through **60,338 frames**:
all **14 complete checkpoint PNGs** and every original final CPU/device/source
diagnostic match. Only the newly added debug-control enabled flag and zero
edit counters are projected into the older expected host metadata. This
bridge contains no RAM edit and retains the unchanged native-module ABI 12.
The unassisted route reaches the four-exit mine junction, actually saves and
loads slot 3 (Mine Creek, HP 17 / EXP 132), and defeats a stairway enemy. Its
final HP 6 / EXP 152 checkpoint remains separate from assisted progression.

At that exact checkpoint, independent RAM/HUD observations agree on current
health 6 and maximum 30. The first recorded local edit changes current health
to 30 and verifies readback. After normal enemy contact the guest's cached HUD
updates to 19. Local assistance refills current health to the observed game
maximum before advances of at most ten frames; it changes no maximum health,
level, equipment, position, inventory or quest flags. Every successful edit
is retained as an expected-byte transaction at its paused frame for replay.

Under that health assistance, normal chest interaction at frame 66,171
produces the Roy's Pendant message, and the miner/Chester scene at frame
70,079 produces the Storehouse Key message. These are real guest quest
triggers, not inventory/flag edits, but their route remains assisted. Natural
enemy rewards cross LEVEL 3 and change maximum health from 30 to 40 without
editing level or maximum health.

A separate temporary higher-jump code assist starts at frame 77,859. The
[first-hand USA cheat notes](https://forum.gamehacking.org/forum/video-game-hacking-and-development/hacker-threads/13996-luc-ita-s-codes/page35)
were treated as leads: the current MPR context did not match the presumed
logical address. A unique physical code window was identified, disassembled
and tested independently in Geargrafx. Paired runs from the same checkpoint
show ordinary body Y 96 → 60 at the jump apex, versus 96 → 36 with the
reversible patch; releasing the button returns to Y 96. This establishes a
higher arc, not unlimited flight or removal of stair attachment/knockback.
The local 69-byte context matches the reference before the guarded edit.
The health-preservation code proposed as invulnerability was not applied
locally. An independent paired Geargrafx probe preserves health but retains
knockback/hurt behavior; it does not establish collision immunity.

The assisted route through 79,445 frames is independently replayed by the
same host: **18 complete PNG hashes, all exposed final diagnostics and 105
edit transactions match** (104 health refills and one active higher-jump
patch). This replay adds no projection of guest state or new image files.
It is internal reproducibility evidence, separately from Geargrafx's scoped
observations and the ordinary-input prefix. That retained checkpoint does
not establish a first-boss or final SDL result.

An additional isolated Geargrafx probe verifies the active actor's canonical
16-bit screen-relative X/Y against guest arithmetic, ordinary input and
world/camera observations, then performs a guarded horizontal relocation within
the same loaded room. Readback and the rendered actor retain the changed X
position over subsequent frames; no quest, map, camera or BRAM field is
modified by that transaction. This qualifies only the tested horizontal
relocation, not arbitrary vertical movement, room transitions or full-route
parity. A vertical return leaves a negative screen-relative Y while the camera
does not follow; it is an assistance artifact and does not qualify functional
vertical relocation. The original private checkpoint is restored afterward.
No local position edit is part of the frozen 79,445-frame checkpoint.

The final reference closeout ends all nine owned Geargrafx sessions and
restores temporary configuration, including the subsequent queue probe.
Both experimental reference code patches are restored and checked by
readback. It retains 14 requested PNGs and approximately 2.6 MB under its
separate 32 MiB bound, with no new checkpoint from the queue probe. The
original assisted checkpoint is unchanged; no computer-use session or owner
save/install was used. It does
not independently establish a first-boss encounter or defeat, capture the
Storehouse Key toast, or reproduce the complete local route. These independent
probes do not qualify the complete boss route.

A subsequent paired Geargrafx probe stages the same actor/cached Y, comparing
an ordinary-gravity control against a queued eight-pixel upward step. At the
observed eight- and twelve-frame checkpoints, world Y follows the same
trajectory; consuming the queue instead moves camera Y by −8 and actor Y by
+8, preserves health, and clears the queue/flag. This independently supports
that bounded queued camera-follow behavior. It does not validate arbitrary
vertical relocation or the complete local assisted route; the earlier
raw-coordinate/camera experiment's limits still apply.

### Later assisted storehouse-interior checkpoint

A later local attempt ends by requested quit at **87,449 frames**, after an
ordinary room-transition routine reaches the green-brick storehouse interior
under position/height assistance. Its journal records **346 expected-byte
edits**: 128 health transactions (including one menu-preview edit), 215
position/camera/cache/height experiments, one inventory-state transfer and two
higher-jump transactions (application and restoration). The jump patch is
restored at frame 85,900. A fresh headless replay of all 87,449 frames matches
**22 complete PNG hashes, every exposed final CPU/device/source/debug
diagnostic and all 346 edit transactions**, without copying PNG files. It
is internal assisted-route reproducibility, not a first-boss or final SDL
qualification.

The earlier vertical/camera edits did not establish coherent room state,
including after experimental SAVE/LOAD. An ordinary LOAD of the known Mine
Creek checkpoint clears that altered state. The subsequent item-state edit
transfers the Pendant and Storehouse Key already earned earlier in the same
test, rather than claiming that the restored checkpoint earned them normally.
The [Japanese PC Engine cheat table](https://wikiwiki.jp/tg002/イースⅢ%20ワンダラーズ%20フロム%20イース)
supplied an item-flag lead. Retained independent Geargrafx RAM before/after
the normal chest/miner scenes corroborates the corresponding item-state
transition; local inventory labeling supplies separate visible confirmation
of possession, not successful use. The [USA manual, Functions/Features pages
6–7](https://www.tg-16.com/contributors/arjak/Ys_III/Ys_III.pdf) distinguishes
directional red-frame selection from Button II confirmation, with Run used
for some items. Those general controls do not establish that the INVENTORY
label view equips or activates the Key. Highlighting or identifying it does
not establish door opening; that earlier checkpoint does not isolate the
item-use mechanism or establish a boss encounter. Title-specific
addresses and game data remain private.

Host frame pause can occur inside a guest subroutine. The actor's working
copy can overwrite an otherwise successful RAM edit, and valid room/camera
state requires more than coordinate bytes. These are constraints on the
private assisted editor, not evidence of a guest CPU/device runtime defect.
The generic debugger still supplies bounded, expected-byte-guarded RAM access;
it does not create a title-specific gameplay-safe checkpoint or room setup.

### Assisted first-storehouse-boss encounter

The final local route restores the checkpoint with the actually earned
Pendant/Storehouse Key state, uses the source-checked upward camera queue and
height-held horizontal traversal, then reaches the first storehouse boss
through an ordinary room transition and Up door entry at frame **93,212**. This successful
continuation is distinct from the earlier inventory-transfer-only approach.
Both quest state and camera/approach alignment changed between those
attempts; a missing quest flag was not isolated as the cause of the earlier
failure, and no runtime defect was established.

Visual inspection confirms a green wizard that teleports and uses
sword/fireball attacks. Ordinary Button II attacks visibly reduce the ENEMY
bar by frame **93,735**, after **523 boss frames**. Those boss frames contain
**14 current-health refills only**; no code, position, camera queue, inventory
or quest edit occurs after entry. The original jump code was restored at
frame 85,900. This qualifies an explicitly health-assisted boss encounter and
visible enemy damage, not an exact HP value, defeat or ordinary-gameplay
completion. Geargrafx does not independently qualify this encounter.

The final local run records **93,735 frames / 33,650,360,835 ticks**,
**5,050,558 native + 2,915,442,205 interpreted instructions**, 1,181 sectors
with zero read errors, 372,199 IRQ/RTI sequences and 1,835,008 ADPCM DMA bytes.
Actual health and the HUD both finish at 36, with maximum health 40; final
EXP is 466, gold 484 and RP 75. The unknown-command response opt-in is used
51 times. These counters do not qualify those unknown operations or audible
output.

The complete journal has **709 successful RAM transactions / 723 changed
bytes**: 145 health edits (including one historical menu preview),
463 position/cache/raw-camera experiments, 98 canonical camera-queue edits,
one earlier inventory-state transfer and two higher-jump transactions
(application/restoration). Failed coordinate/camera approaches are retained
as edit history, not successful teleport claims. The successful approach
restores the actually earned quest checkpoint before queued ascent and
height-held traversal; no
inventory/quest/code/position/queue edit occurs after boss entry.

A fresh SDL desktop replay passes through **all 93,735 frames**, matching
**25 complete guest PNG hashes, all 709 edit transactions / 723 changed
bytes and every exposed final CPU/device/source/debug diagnostic**. It exits
cleanly with code 0 and creates no new PNG files. The source route SHA256 is
`bf16fa09c71d6ae7f9049d869dd6d15e072cd5a1a888b285b721a3b1c38294b8`;
the SDL binary is unchanged throughout the replay. This is internal
cross-host reproducibility of the assisted route. It does not compare all
guest RAM or every composed SDL pixel, and does not add independent
Geargrafx, hardware, full native/AOT, boss-defeat or campaign qualification.


## Dispatch optimization reference rerun

The optimized exact-key dispatcher was rebuilt into the authored reference
probe with 17 translation units, partition target 1, seven contexts and 21
compiled identities. The final probe SHA256 is
`866ef13b15d7da25d58b07f81319870b184ad5a0328f1ffaac8f0de893eef04c`.
Geargrafx 1.8.4 independently matches all 78 plans: per tier, 156 CPU/MPR/latch
states, 156 instruction-clock deltas and 78 complete 8 KiB RAM images. Native
execution remains 156 instructions with zero fallback; pure interpreter
execution remains 156. Another 306 local checks pass unchanged-state guard
refusals. The owned reference process stopped and its temporary configuration
was removed. This rerun covers authored CPU semantics and complete-instruction
clocks, excluding IRQ delivery, device phases, retail-route and hardware parity.

Separate compiled authored tests exercise three PCs in one logical page across
partition boundaries, two consumers sharing each module object, exact-byte
and full-MPR refusal, unreadable source and deadline refusal. The source-peek
test adds 6,668 independent groups for all 256 banks, every bank kind, bounds,
raw mutations without generation changes and absence of I/O/BRAM side effects.
These are local expectations, not additional independent emulator comparisons.

The optimized 44,832-identity module also repeats the complete retained
93,735-frame hidden SDL/TCP route. All 25 complete guest PNG hashes and the
709 original RAM transactions / 723 changed bytes match. Native/interpreted
retirements remain 2,920,491,782 / 981; all 460,685 block transfers remain native.
Its complete final JSON additionally equals the previous expanded native run,
including every tier and guard counter, after separately validating only host
transport/presentation metadata. The ephemeral port matches startup output;
SDL telemetry has the exact schema, 93,735 presentations and no local input
events. This comparison removes no guest fields. There is no whole-RAM,
composed-window pixel, independent retail-route or campaign performance claim.
The same response profile and assistance journal remain required. The owned
hidden SDL process stopped and no additional game PNG copies were created.

## Retained observed-code promotion and consumer qualification

The current compiler path records exact retired instruction identities, full
MPR contexts, physical fetch addresses and per-tier hits. It emits guarded direct
C++ for multiple contexts and byte variants, with no inferred fallthrough or
per-opcode interpreter wrapper. An authored 78-plan matrix checks seven contexts
and 21 compiled identities against Geargrafx 1.8.4. Each tier matches 156
CPU/MPR/latch states, 156 complete-instruction clock deltas and 78 full 8 KiB RAM
images. Native execution is exactly 156 instructions with zero fallback; the
pure interpreter retires the same 156. Another 306 local checks verify unchanged
state on per-byte, unknown-PC and full-context guard misses.

The matrix includes actual physical remapping at one logical PC, changed-byte
variants, cross-page and logical-wrap fetches, ADC carry/T/decimal combinations
at both speeds, TMA/TAM transitions, stack effects and RTI. It does not qualify
IRQ delivery, device bus phases, retail gameplay, hardware or every encoding.
The final exact probe was rerun after the source/build freeze. Its SHA256 is
`e136b3a217d51298d6edec5b7f4b99c7d23cbda73decb6e9d69d054ca603e270`.
Both reference sessions stopped and their temporary configuration was removed.

The unchanged retained assisted Ys III route supplies a separate internal
qualification. Profiling all 93,735 frames reproduces the baseline tier split
and observes 44,836 identities / 57 contexts, totaling 2,920,492,763 retirements
with no capacity loss or unreadable source. The raw capture SHA256 is
`f30ecfe76692c852392234ea143bb9aa7dff8c2fec75d34e3da4e8e79250d61e`.
The emitted module retains 44,832 identities in 57 contexts. Every observed
instruction touching the temporary patch span is excluded, including original
and patched forms: four identities / 981 recorded hits. Exclusion metadata is
separate; the original capture, hit counts and completeness remain intact.

The full expanded-module SDL/TCP replay executes **2,920,491,782 native and
981 interpreted instructions**, compared with the baseline **5,050,558 native
and 2,915,442,205 interpreted**. All **460,685 block instructions** now execute
natively. The native retirement ratio rises from **0.1729351% to 99.9999664%**.
It includes firmware/wait loops and is specific to this retained input route;
it is not percentage-of-game coverage or a controlled performance benchmark.

All 25 complete guest PNG hashes, 709 original RAM interventions / 723 changed
bytes and exposed final guest CPU/device/source diagnostics match. Guest clocks,
total retirements and total block instructions remain exact; only native versus
interpreted tier counts and guard misses intentionally differ. The newly
allocated TCP port is checked against startup output. The SDL-only final host
object is checked separately for its exact schema, 93,735 presented frames and
zero local input events. Neither projects a guest field. Initial additional
final-JSON checks had refused these host-only differences after the complete
TCP-state/image comparison passed; the retained results were revalidated with
those explicit transport/presentation checks, without repeating guest execution.
No new PNG files are retained. Whole RAM and composed-window pixels are excluded.

The authored consumer example also builds and executes through the new project
interface: 200 native / zero interpreted instructions, A=41, X=140, PC=16387,
1,794 ticks and a valid four-identity capture receipt. Its tool source digest
matches a clean public-source checkout. A separate Ys III consumer uses the same
source digest and official build/run guards with a smaller original-code hot
set of 2,048 identities in nine contexts. It independently reproduces the retained
93,735-frame route and 25 images with **2,784,362,065 native / 136,130,698
interpreted retirements (95.3387764%)**. That is cross-project reproducibility
under a different native selection policy, not independent PC Engine semantics.

The existing `gear-good` response profile, volatile BRAM and assistance journal
remain unchanged. No unknown CD operation, authentic reset, audio output,
complete campaign, unassisted boss defeat or unvisited native code is newly
qualified. No title addresses, code captures or generated game source are part
of the public toolkit.
