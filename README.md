# PC Engine Recomp

An open, experimental static recompilation toolkit for **PC Engine /
TurboGrafx-16 and CD-ROM²** games. The goal is a shared foundation for native
ports with modern rendering, audio, input, debugging, and game-specific
enhancements.

The toolkit serves independent PC Engine/TurboGrafx consumer projects. Each
project owns its game-specific routes, patches, assets and presentation choices.
Ys III is one regression case; compatibility evidence remains tied to the
tested CPU, hardware, media and runtime profiles.

**Same-build interpreter reference windows are now supported.** An explicitly
enabled build can restore its own checkpoint and run bounded interpreter-only
segments over TCP. Generated dispatch is bypassed, imported counters stay exact,
and captures/receipts record the effective execution policy. Native counterparts
use the same binary, module and machine recipe; old or disabled-build checkpoints
remain incompatible. See [setup, API and comparison rules](docs/REFERENCE_MODE.md).
Runtime ABI 29 and guest checkpoint encoding remain unchanged.

Authored tests compare 70,000 actual native instructions with 70,000 interpreted
instructions from one checkpoint: complete machine state, completed RGB and
filtered PCM agree after excluding only four tier-accounting counters. This is
internal tier parity; independent hardware/emulator and campaign evidence remain
separate.

**Consumer evidence now has shared snapshot and admission helpers.** Exact-byte
JSON snapshots, streamed artifact bindings and explicit process/seal boundaries
replace repeated private read/hash maps. A role ledger validates current and
explicitly carried results through the same resolver, preserving original
contracts and producer references. Its output records evidence consistency;
native execution and checkpoint semantics remain consumer checks. See
[the Python interfaces and private evidence contract](docs/EVIDENCE_HELPERS.md).

The helper-tooling SDL check passes **1,744 Python tests without skips,
70 C++ suites and 12 fresh-process audio checkpoint cases**. Runtime ABI 29,
CPU/device code, native translation and CMake remain unchanged. Authored
integration cases cover complete carried/current role assembly and content
drift; real-file adoption admits a 9,777-file consumer graph once, reuses an
identical overlap without binary reads, and explicitly revalidates all inputs.
A new Ys III TCP smoke test restores and immediately re-saves an identical
own-build checkpoint, then advances six frames with zero fallback. The helper
parent and retained execution SDK stay in separate processes; its consistency
closure grants no new gameplay qualification.

**Native discovery now has a reusable gap report.** `native-gaps` verifies an
observed module's declared emitted identities and exact source artifacts,
then compares full byte/MPR identities from captured windows. It keeps each
window's costs separate, identifies missing variants and avoids treating
unexercised compiled code as new execution. It supports the known ABI 28/29
selection contract without migrating an existing consumer. See
[the CLI and Python interface](docs/NATIVE_GAPS.md).

**RomAtlas now supplies actual independent decoder checks.** An isolated
offline build checks 25,221 authored records across opcode, boundary and mapping
cases, including a narrow original-core fetch probe. Known BRK metadata differences
remain explicit; no unexpected difference is accepted. See
[reference scope and reproduction](docs/ROMATLAS_REFERENCE.md).

The discovery-tooling SDL check passed **1,682 Python tests without skips, 70 C++ suites
and 12 fresh-process audio checkpoint cases**. Runtime ABI 29, CPU translation,
device code and CMake bytes are unchanged by this discovery-tooling batch.
Fresh recoverable-build errors now identify the missing recovery option before
creating output; [resume keeps its sealed-input contract](docs/BUILD_RECOVERY.md).

**ABI 29 adds opt-in captured CD subchannels.** Read-only CHD providers expose
original 96-byte P–W packets from supported `RW_RAW` extents, with explicit
absence, stored-pregap mapping and fatal decoder/source-error handling.
`--cd-subchannel captured-q` validates Q CRCs, retains position packets and
returns them through `$DD`; `synthesized` remains the default. Complete Q state
and the selected profile participate in exact-build checkpoints. Native modules
need regeneration and rebuilding; existing consumer checkpoints stay with their
original builds. The byte FIFO/subchannel IRQ interface remains separate work.
See [captured subchannel contracts and references](docs/CD_SUBCHANNEL.md).

That captured-subchannel SDL check passed **1,636 Python tests without skips, 70 C++ suites
and 12 fresh-process audio checkpoint cases**. Original Geargrafx/Beetle checks
pass 315 authored captured-Q records. The selected Ys III build remains ABI 28;
its media declares no captured subchannels. Its regression and any future ABI 29
migration retain separate evidence.

Fresh TCP/checkpoint tests on that selected package pass with zero fallback
and matching complete state, RAM, images and instruction counts; a separate
paced audio fork also passes. See [current verification scope](docs/STATUS.md#selected-abi-28-consumer-regression).

[Native discovery guidance](docs/NATIVE_DISCOVERY.md) now distinguishes
executed, compiled and statically reachable code, explains existing mapping-aware
analysis, and records the implemented gap report and planned authenticated
snapshot-export interface.

**Consumer raw audits now have reusable same-ABI relations.** The new pure
helper validates imported counters, explicit source/candidate tier relations
and complete encoded instruction identities. It rejects boolean counters,
duplicate or non-finite JSON, mapping drift and per-key count changes before
an adapter can compose its qualification. Original raw journals, process and
checkpoint provenance, write authority and final admission stay explicit.
See [consumer raw-audit integration](docs/RAW_AUDIT_INTEGRATION.md).

Ys III's two retained discovery windows now pass all four raw role audits:
**678 new frames, 21,108,383 native instructions and zero fallback**. The
linked route exercises 53,614 of 58,039 compiled identities. Fresh own-checkpoint
repeatability and a separate paced audio fork also pass; imported work and
test forks stay outside the new route totals. See [the extension's scope](docs/NATIVE_MIGRATIONS.md#raw-audited-same-build-discovery-extension).
That earlier raw-audit SDL check passed **1,616 Python tests without skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**, retaining ABI 28
and the selected consumer's compiled package.

**VDC register races now have independent guest-code coverage.** A new
24-case matrix runs actual translated and interpreted instructions against
original Geargrafx: DMA holds a VRAM request while the guest changes its
address increment, then a real port access waits for completion. All 744
native retirements run without fallback; pending state, wrap results and
timestamps match. See [queued-register race coverage](docs/VDC_ACCESS.md#guest-register-changes-during-pending-requests).

**Reference checks now reject mismatched or ambiguous replies.** The shared
Geargrafx MCP client validates response IDs and rejects duplicate JSON keys,
non-finite numbers and malformed results. Authored regressions and a real
isolated Gear smoke check the boundary. At that milestone, runtime ABI 28 and
the qualified consumer's compiled code remained unchanged. See [the reference client contract](docs/REFERENCE.md#shared-http-reference-boundary).
Ys III also passes a fresh TCP checkpoint pair on that qualified package:
each 60-frame continuation executes 1,866,913 native instructions with zero
fallback and matching complete state, RAM, pixels and encoded hit counts.
A separate 120-frame paced SDL audio fork passes with zero fallback.
That earlier VDC/reference-boundary SDL check passed **1,600 Python tests without skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**.

**All four new late-game identities now execute natively.** The staged-profile
Ys III candidate completes a fresh reset replay and seven own-checkpoint
continuations: **111,789 route frames, 3,433,175,577 native instructions and
zero interpreter fallback** across eight processes. Each added full source
identity has positive native hits. The final 522-frame window also repeats
from the same candidate-owned checkpoint with matching complete state, RAM,
pixels and per-identity counts. This finite assisted qualification keeps
checkpoint/audio forks separate from route totals and does not certify a
complete game port. See [late-identity qualification](docs/NATIVE_MIGRATIONS.md#staged-profile-v2-late-identity-qualification).

**Observation catalogues can grow without counting every overlap again.**
Opt-in `compose-observations --baseline-profile ... --new-identities-only`
preserves the original captures, ABI labels and origins while selecting only
new instruction identities from each extension. A versioned stage ledger keeps
earlier selections stable; dry-run reports exact output costs before emission.
Parser limits remain unchanged, and original historical hits stay separate
from selected contribution counts. A separately built v2 consumer passes fresh
TCP startup, retained-route replay and exact-build checkpoint continuation;
its four late additions have measured native execution. See [additive composition](docs/OBSERVATION_PROFILES.md#add-identities-without-duplicating-overlapping-contributions).

**Interrupted builds can resume verified completed work.** Opt in before the
first configure with `build --recoverable`, then use `project resume` after an
interruption. The Windows x64 LLVM-MinGW/Ninja producer verifies unchanged
inputs, configuration and durable object checkpoints, retains matching objects
and freshly links the package. A guardian holds the directory lock until owned
compiler processes exit. Ordinary old build directories cannot be retrofitted.
An actual 976-object consumer passes late-interruption recovery, fresh TCP
startup and candidate-owned checkpoint repeatability.
See [recovery setup and limits](docs/BUILD_RECOVERY.md).

**ABI28 native consumer migration now passes the retained regression route.**
The rebuilt Ys III test consumer completes a fresh **104,745-frame reset replay
with 3,209,517,525 native instructions and zero fallback**. Its own checkpoint
continuations also pass combat, the lower waterfall, complete-state repeatability
and paced digital audio checks. Independent audits verify source provenance,
per-identity retirements and device state. This qualification uses explicit
`fixed` CD timing; the optional distance profile keeps its separate scope. See
[ABI28 migration qualification](docs/NATIVE_MIGRATIONS.md#abi-28-fixed-timing-native-migration).

**ABI 28 adds optional distance-aware CD timing.** `--cd-timing gear-distance`
models READ and CDDA seek distance, physical-seek completion and later audio
readiness. The existing `fixed` profile stays the default. Native modules need
regeneration/rebuilding; checkpoints remain exact-build-only. See
[CD timing profiles](docs/CD_TIMING.md).

**Composition now has a read-only preflight.** `compose-observations --dry-run`
with explicit `--baseline-input` files reports exact output bytes/hash,
new identities, contributions and remaining capacity before a build. It
preserves profile-v1 bytes, source provenance and all existing limits. See
[composition planning](docs/OBSERVATION_PROFILES.md#preflight-an-extension-before-emission-or-build).

The earlier additive-composition SDL check passed **1,583 Python tests without skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**. Independent
earlier CD timing checks cover 12,432 seek vectors and 21 command cases at both CPU
speeds, with native and interpreted execution checked separately.

The separately rebuilt **ABI27** Ys III consumer also passes a new 2,232-frame
checkpoint combat extension: **70,860,852 native instructions, zero fallback**.
Its 29 newly compiled identities all execute; checkpoint continuation and
paced audio pass. This does not migrate that game to ABI28. See
[the extension's scope](docs/NATIVE_MIGRATIONS.md#abi-27-checkpoint-combat-extension).

**Earlier ABI 27 introduced an explicit invalid-CD-command response profile.**
`nec-invalid` receives the complete six-, ten- or twelve-byte packet before
returning CHECK CONDITION and illegal-command sense. The strict default and
legacy `gear-good` response remain available. Original Geargrafx and Beetle
are checked separately, with their wire and reset differences retained.
Fresh original-core runs cover **252 cases per core**, including all 248
unrecognized opcodes. A separate authored guest conserves **23,241 retirements
across 893 source identities**, interpreted to native with zero fallback.
Native modules require re-emission and rebuilding; old capture labels stay
intact and checkpoints remain exact-build-only. See
[unknown CD profiles](docs/CD_UNKNOWN.md).
That earlier frozen SDL build passes **1,478 Python tests without skips,
66 C++ suites and 12 fresh-process audio checkpoint cases**.

**ABI 27: a fresh Ys III route now runs entirely natively under `nec-invalid`.**
The rebuilt catalogue retains all 57,752 old identities and adds 250.
A fresh reset reaches the tested Alcaino frontier after **104,745 frames**,
with **3,209,517,525 native and zero interpreted instructions**; all 53,516
executed source identities conserve their individual counts. This finite
assisted route uses 309 explicit validated RAM writes. It is separate from
the older ABI26 stair-room route and is not campaign or hardware certification.
Fresh candidate-owned restores and paced SDL audio submission also pass.
See [ABI27 migration qualification](docs/NATIVE_MIGRATIONS.md#abi-27-native-migration).

**Earlier ABI 26 qualification: the full retained Ys III route replays natively.** A fresh
reset reaches its terminal stair room after **102,802 frames**, executing
**3,122,661,937 native and zero interpreted instructions**. The discovery
run's 3,433 fallback instructions, including 68 block transfers, become native;
all 54,610 executed source identities are retained. Candidate-owned fresh
checkpoint restores also produce identical complete continued files.
This is an assisted finite route, with 300 explicit RAM writes; complete game
and hardware compatibility remain unqualified. See
[native migration qualification](docs/NATIVE_MIGRATIONS.md).

**Semantic frame-step replay now separates progress polls from settled state.**
The pure validator retains timing-dependent observations, checks finite bounds
and exact paused frame/tick endpoints, and supports whole-instruction overshoot.
A required TCP/checkpoint fixture requests frame 1 and correctly completes at
frame 13. See [semantic frame steps](docs/SEMANTIC_STEPS.md).
That ABI 26 SDL build passed **1,461 Python tests without skips, 65 C++ suites
and 12 fresh-process audio checkpoint cases**.

**Ys III now adopts the paused-write validator and closed-journal archives
through its consumer adapters.** A guarded 60-frame checkpoint continuation
matches a fresh restore byte for byte; each suffix executes **1,951,472 native
and zero interpreted instructions**. Diagnostics were pinned separately from
the game runtime; that earlier integration left the selected build unchanged. See
[consumer write adoption](docs/PAUSED_WRITES.md#adopting-the-relation-in-a-consumer)
and [consumer journal archives](docs/PAUSED_OBSERVATIONS.md#consumer-archive-adoption).
That earlier finite integration test is separate from the full-route migration
above.

**Paused RAM writes now have a typed validation contract.** Data edits can be
checked while code executes from the same WRAM bank: exact readbacks, alias
generation increments and write counters are validated, while fetched code,
PC, mappings and other reported state stay strict. The existing paused-status
comparator is unchanged. See [typed paused writes](docs/PAUSED_WRITES.md).

**Closed development journals can be archived losslessly.** The new offline
gzip helper retains the original file and exact decompressed bytes; the
streaming reader checks both journal and container hashes. Damaged containers
are refused, and incomplete journals retain their forensic status.
See [journal archives](docs/PAUSED_OBSERVATIONS.md#archiving-a-closed-journal).
Runtime ABI 26 and checkpoint schema 1 are unchanged.
The frozen SDL build passes **1,440 Python tests without skips, 65 C++ suites
and 12 fresh-process audio checkpoint cases**.

An earlier isolated retained-build Ys III test passes the exact same-WRAM data
edit that its earlier consumer guard refused. A fresh checkpoint round trip
and one neutral frame of continuation match complete endpoint files. Each
suffix executes **31,945 native and zero interpreted instructions**. This is
an assisted tooling check; it left the selected game build and route
qualification unchanged at that time.

**Active-display IRQ and checkpoint coverage now includes raster and sprite
collision sources.** A fresh Geargrafx/native/interpreted matrix passes
**48 recipes, 720 guest processes and 288 fresh restores**, checking IRQ1/IRQ2
priority, real guest acknowledgement and queued VRAM waits. Timing differences
remain recorded. No runtime or ABI 26 change was needed.
See [active-display IRQ checkpoints](docs/ACTIVE_IRQ_CHECKPOINTS.md).
The frozen SDL build passes **1,402 Python tests without skips, 65 C++ suites
and 12 fresh-process audio checkpoint cases**.

A separate retained-build Ys III TCP test adds **144 menu-control frames**;
two fresh checkpoint suffixes match complete endpoint files. It executes
**3,900,861 native and 18 interpreted instructions**, with HP staying 11.
This is a finite regression, not new campaign or migration qualification.

**Consumer builds can now bind their observation profile explicitly.** The
optional descriptor entry verifies original profile bytes and metadata against
the emitted manifest, includes them in build/run receipts, and lets managed
rebuilds copy and archive the profile. Existing descriptors remain valid;
opting in requires fresh checkpoints because it strengthens consumer identity.
See [profile-bound consumer builds](docs/OBSERVATION_PROFILES.md#bind-the-profile-to-a-consumer-build).
An authored managed test promotes **101 native/99 interpreted instructions
to 200 native/zero interpreted**, rebuilding one source-part object. A no-op
retains all 29 object hashes and timestamps; profile bytes stay archived.
The final frozen SDL build passes **1,382 Python tests without skips, 65 C++
suites and 12 fresh-process audio checkpoint cases**. Runtime ABI 26,
checkpoint schema 1 and generated operations are unchanged.

**Mixed-ABI observation profiles are implemented.** Combine original capture
files without relabeling their ABI or losing source variants, then emit a
guarded native module through `compose-observations` and `emit-profile`.
Profiles retain exact original bytes, hashes, checkpoint origins and per-input
hit contributions. Historical sums remain separate from new execution evidence.
Runtime ABI 26 and checkpoint schema 1 are unchanged.
See [observation profiles](docs/OBSERVATION_PROFILES.md) for commands, bounds
and consumer migration requirements.
The fresh frozen SDL build passes **1,360 Python tests without skips, 65 C++
suites and 12 fresh-process audio checkpoint cases**. An authored mixed-ABI
module compiles and executes five native identities with zero fallback.
The private Ys III catalogue preserves every old identity and adds 23 through
the supported interface; its new module still needs separate game qualification.

**Phase diagnostics now cover periodic horizontal-sync blocking.** The new
profile uses actual latched video state to predict the guard and even-dot
slots separately, including scanline wrap. The earlier no-HSW API remains
available. The authored matrix adds 24 sync/tail edges to its 48 baseline
recipes. Runtime semantics and ABI 26 are unchanged.
See [horizontal-sync coverage](docs/VDC_PHASES.md#periodic-horizontal-sync-coverage).
All **216 waits across 72 recipes** match the new model. The fresh frozen SDL
build passes **1,327 Python tests without skips, 65 C++ suites and 12
fresh-process audio checkpoint cases**.

The new Ys III test exercises a **64-frame inventory-control variation** and
queued VRAM-write checkpoint continuation. Two fresh restores match complete
endpoint files; HP stays 11. It executes **1,734,111 native and 12 interpreted
instructions** on the separately pinned retained consumer.

**The selected VRAM wait differences have a causal explanation.** The earlier
no-HSW diagnostic predicts the retained −6/+3-tick differences from actual
instruction and raster phases. Its base-HuCard comparison removes CD activity:
48 recipes execute across native, interpreted and Geargrafx tiers; 46 fit that
legacy model and two are explicit horizontal-sync controls. The periodic profile
above now covers those cases. The runtime and ABI 26 are unchanged.
See [VDC phase analysis](docs/VDC_PHASES.md).
That earlier phase-analysis batch passed **1,315 Python tests without skips, 65 C++
suites and 12 fresh-process audio checkpoint cases**.

A new retained-build Ys III checkpoint check adds **160 ordinary-input
frames**, with **5,081,894 native and one interpreted instruction**. Two fresh
restores match complete endpoint files and core payloads. This is a finite
game regression; its consumer and helper source identities remain separate.

**Retained development journals now have a streaming offline reader.** It
checks raw request/reply framing, record order, types, file stability and an
optional complete-file hash without loading the entire log or replaying inputs.
The client also rejects JSON exponent overflow. Paired raw replies remain
separate from a successful game or caller validation.
See [reading journals](docs/PAUSED_OBSERVATIONS.md#reading-a-retained-journal).

**Competing video and CD interrupt checks now share checkpoint coverage.**
The new suite exercises READ-fed ADPCM IRQ2 and VDC DMA IRQ1 during queued
VRAM waits, then checks priority, device acknowledgement, RTI and pending IRQ2.
Its 48 direct checkpoint cases pass. The independent original-Geargrafx matrix
passes 72 cases and 144 fresh restores, retaining raw timing differences whose
selected entry-phase causes are now diagnosed. See
[VDC/ADPCM IRQ qualification](docs/VDC_ADPCM_IRQ.md).
ABI 26 and checkpoint schema 1 are unchanged.
That earlier diagnostic batch passed **1,295 Python tests without skips, 65 C++
suites and 12 fresh-process audio checkpoint cases**.

The previous retained-build Ys III regression adds **980 frames** through
inventory and a cave return. Two fresh restores match complete endpoint bytes.
It executes **28,258,771 native and 20 interpreted instructions**; the newer
wire client and older game runtime have separate source pins. This finite
regression does not certify a complete port or cross-build migration.
See [current verification](docs/STATUS.md).

**Developer inspections can retain replies before validation fails.**
`DevClient` has an opt-in raw wire journal, and a new typed paused-status
comparator is exact by default. An explicit legacy audio-drain policy helps
older consumers diagnose delivery counters without relaxing source or guest
synthesis checks. An authored SDL checkpoint test checks pending PCM, durable
AFTER evidence and byte-identical restored continuation.
See [paused observations](docs/PAUSED_OBSERVATIONS.md).

**DMA interrupt checks now cover all five block-transfer families.** A new
40-case Geargrafx matrix and 80 fresh restores witness IRQ2 being raised while
I is already clear during a block, then delivered after the whole instruction.
Original continuation calls stay separate from completed guest instructions.
Another 30 direct cases check stack/flags, copy patterns and checkpoint
continuation. Raw differences remain visible; ABI 26 and checkpoint schema 1
are unchanged. See [block/DMA IRQ qualification](docs/BLOCK_DMA_IRQ.md).
That earlier block/DMA batch passed **1,261 Python tests without skips, 64 C++
suites and 12 fresh-process audio checkpoint cases**.

An earlier retained-build Ys III regression adds 810 frames through a rope
bridge and cave area. Two fresh restores match complete endpoint checkpoint
bytes. One interpreted instruction and the explicit unknown-CD response policy
remain part of this finite result; it does not certify a complete port or
cross-build migration. Earlier checks remain under
[guest-driven DMA/IRQ checkpoints](docs/DMA_IRQ_CHECKPOINTS.md),
[CD/ADPCM checkpoints](docs/CD_ADPCM_CHECKPOINTS.md) and
[CD READ checkpoints](docs/CD_READ_CHECKPOINTS.md).

**State-aware TCP routes now check guest state before sending input.** Finite
data-only plans support typed status, paused physical-memory and complete source
identity predicates, bounded waits and input pulses. Receipts retain raw paused
observations and distinguish accepted host intent from guest controller
sampling. A bounded ABI 26 investigation reaches the street/Tigre Mine dialogue;
it does not establish full migration or a runtime defect. Independent authored
input checks cover 24 cases against original Gear. ABI 26 is unchanged.
See [state-aware routes](docs/STATE_ROUTES.md). The state-aware-route batch passed
**1,188 Python tests without skips, 60 C++ suites and 12 fresh-process audio
checkpoint cases**. All 24 original-Gear input cases pass; the independent
auditor also refuses 12 altered receipts.

**Audio comparisons now check the signal domain.** The 144 previously retained
PSG differences came from comparing Geargrafx's filtered output with toolkit
raw output. Matched raw and filtered checks explain them without changing chip
gain. A reusable comparer refuses mismatched filtering, timing, gain, rates and
source phases; expanded tests cover PSG edges and checkpointed filter history.
ABI 26 remains unchanged. See [audio traces](docs/AUDIO_TRACES.md).
Fresh Gear checks pass 72 longer guest pipeline cases and 3,262 digital PSG
plans. Filtered 48 kHz Ys III checkpoints reproduce death/retry twice, each
with **48,335,394 new native instructions and zero fallback**; the raw-source
projection remains identical to the earlier raw baseline.
The signal-domain audio batch passed **1,154 Python tests and 60 C++ suites**, plus 12
authored fresh-process audio checkpoint cases.

**ABI 26 corrects guest PSG write timing and CD audio end changes.** PSG
stores, memory read-modify-write operations and all five block transfers now
advance pending base clocks before updating the sound chip. Shortening CD
playback with `$D9` preserves the active sector's remaining samples before
looping or stopping. Authored checkpoint tests cover exact source/queue/filter
continuation. See [audio bus timing](docs/AUDIO_BUS_TIMING.md) and
[migration](docs/CONSUMER.md#historical-upgrade-to-abi-26).
Independent Gear checks pass 72 PSG timing cases and 72 CD end-change cases;
later PSG sample differences remain documented. Two fresh Ys III checkpoint
resumes each execute **48,335,394 new native instructions with zero fallback**
through death/retry and movement, matching the uninterrupted state and pixels.
The ABI 26 timing batch passed **1,119 Python tests and 59 C++ suites**.

**Experimental native spans preserve per-instruction boundaries.** An opt-in
stable module can retire multiple instructions within a part while keeping
exact source/mapping guards, IRQ/device timing and capture/input callbacks.
The legacy path remains the default after the current authored benchmark
showed slower span execution. Independent ADPCM HALF/END tests also extend
CPU interrupt coverage. See [native spans](docs/NATIVE_SPANS.md) and
[ADPCM IRQ qualification](docs/ADPCM_IRQ.md).

**CD audio starts now preserve playback at known disc gaps.** The runtime uses
authoritative program-range metadata before admitting a seek, preserving the
existing head, audio cursor and pending events for ignored starts. Controller
BUSY quirks and unknown-metadata limits remain explicit. This batch also adds
checkpoint tests around live VDC CR/MWR latch and VRAM queue boundaries.
See [CD audio gaps](docs/CD_AUDIO_GAPS.md) and
[VDC latch checkpoints](docs/VDC_LATCH_CHECKPOINTS.md).
That frozen compatibility batch passed **1,102 Python tests and 57 C++ suites**.
Independent Gear checks cover 160 gap starts and 36 VDC latch/checkpoint cases
with their documented controls/differences. Two fresh Ys III checkpoint resumes
each execute **87,783,727 new native instructions with zero fallback** through
mine combat, matching uninterrupted execution.

**Paused developer checkpoints now support exact-build continuation.**
The opt-in TCP host saves complete machine state to a new private `.pcec`
file, including pending video/CD work, audio queues and filter history. A
fresh paused run can restore it with the same executable, DLLs, source/module
context, media and runtime profiles. Resumed receipts and code captures keep
the imported prefix separate from newly executed work. Current ABI 29 requires
fresh exact-build checkpoints; the original introduction retained ABI 25.
Portable saves, cross-module loading and in-process rewind remain future work.
See [developer checkpoints](docs/DEVELOPER_CHECKPOINTS.md) for setup and limits.
The checkpoint-introduction batch passed **1,088 Python tests and 55 C++ suites**. A fresh native
Ys III process restores town and executes **232,019,512 new native instructions
with zero fallback** through first-mine combat, matching the uninterrupted
machine, pixels, work RAM, audio state and complete source-hit window.
Independent Geargrafx checks cover 48 authored checkpoint/IRQ continuations;
the game route is a separate finite regression.

**Observed modules now have an opt-in stable layout and managed rebuilds.**
Parts use all eight MPRs and fixed logical-PC ranges, so adding an observation
does not renumber unrelated source files. The Windows LLVM-MinGW/Ninja
workspace verifies retained objects and dependencies, preserves unchanged
source timestamps and performs a checked rebuild. Its build history stays
separate from execution qualification. The balanced default is unchanged;
stable layout can increase cold-build work. See
[stable emission](docs/STABLE_EMISSION.md) and
[managed rebuilds](docs/INCREMENTAL_BUILDS.md).
An authored capture-driven update rebuilds one object while retaining 26;
original-Gear execution and a fresh 835-unit Ys III native replay pass.

**Current status: experimental compiler/runtime with direct native code
generation, continuous video, audio, desktop/TCP development hosts and a
reusable consumer-project interface. No complete game port is certified.** The decoder
describes all 256 HuC6280 opcode slots; the native emitter and interpreter
implement 234 opcodes, including
load/store addressing, logical operations, ADC/SBC with T/decimal handling,
comparisons, shifts/rotates, INC/DEC, indirect JMP, RMB/SMB and all eight
push/pop instructions, BIT/TSB/TRB/TST, bit branches, BSR and TAM/TMA with
persistent transfer-latch semantics, plus CSL/CSH speed control and
ST0/ST1/ST2 VDC port writes, all five block transfers, RTI and BRK. The runtime
includes continuous video from guest scanline/palette history and an optional
SDL3 desktop window with keyboard/gamepad input, pause and fullscreen.
Snapshot and continuous renderers support two-bit backgrounds (including CG
bank selection) and live digital grayscale. Exhaustive authored patterns and
a separate MesenCE function/filter adapter check these modes; Geargrafx checks
the existing color path. See [video profiles and limits](docs/VIDEO_OUTPUT.md).
The opt-in loopback development server adds status, controller input, bounded
frame advancement, requested guest/SDL captures and paused physical-memory
inspection for either runner. Explicitly enabled, expected-byte-guarded RAM
edits support reproducible assisted tests; edits are counted and remain
separate from ordinary gameplay qualification. See [TCP debugging](docs/DEV_SERVER.md).
The BIOS-backed Ys III test now exercises queued VDC timing from authentic
System Card reset through town navigation, equipment purchases and first-mine
attacks, enemy rewards, received damage, natural death/retry and guest
SAVE/LOAD. These use isolated test memory and explicitly declared save inputs.
This conditional gameplay requires the explicit `--cd-unknown-status gear-good`
reference-emulator response profile; strict default mode still faults on the
encountered unknown CD command.
This does not implement or certify that unknown command.
Decoded, emitted, compiled, and executed are different milestones here.

**ABI 25 adds live scroll-write timing and program-aware CD positions.**
BXR/BYR writes near the VDC's scroll latches can affect the current scanline,
including paired BYR writes with distinct counter and line-offset behavior.
CD `$DD` replies now distinguish known program areas from authored disc gaps
instead of always assigning the preceding track. Custom providers can
explicitly report unavailable geometry and retain the documented TOC-only
fallback. Rebuild providers, generated modules and runtime together; retain
original capture labels and obtain fresh execution evidence. See
[scroll timing](docs/VDC_SCROLL.md), [CD positions](docs/CD_POSITION.md) and
[consumer migration](docs/CONSUMER.md#historical-upgrade-to-abi-25).
Separate original-Gear checks pass 19 guest scroll profiles and 18 authored
disc layouts; actual pre-fix runs demonstrate both defects. Fresh ABI25 Ys III
TCP capture, native compilation and replay also pass without interpreter
fallback on the tested route.

**Independent traces now distinguish instructions from interrupt entry.**
The opt-in IRQ trace format retains actual engine calls and groups completed
instructions without counting an IRQ entry or resumed block transfer as a new
opcode. Fifteen authored cases run through native code, the interpreter and
separately built original Geargrafx and Beetle cores. The checks expose real
differences in interrupt sampling, saved flags and speed-transition timing;
they do not silently change the runtime to match a reference. The unchanged
legacy path also checks 161 masked mixed-speed instructions. See
[IRQ traces and limits](docs/IRQ_TRACES.md) and
[actual qualification results](docs/STATUS.md).

**Device interrupt tests now exercise competing real sources.** Authored
guest firmware raises timer, VDC DMA and CD handshake interrupts, then checks
priority, masks, held lines and acknowledgements against original Geargrafx.
The 44-case suite retains actual callback/clock journals and full native versus
interpreter source accounting. Legacy immediate VDC reads keep their explicit
timing difference. See [device IRQ behavior and limits](docs/IRQ_DEVICES.md).

**IRQ1 and IRQ2 also have dedicated dynamic VRAM-stall coverage.** An authored
78-case matrix raises real DMA and CD requests while a CPU port access is
blocked. It checks both CPU speeds, all three VCE clock rates, masks,
priority, acknowledgements and full WRAM/VRAM contents against independent
timing expectations and original Geargrafx callbacks. Exact wait partitions
distinguish a dynamic stall from a fast fixed memory wait. Separate engine
scheduler differences remain explicit. See [stall verification and limits](docs/IRQ_STALLS.md).

**Active-display VRAM arbitration now has an authored test matrix.** It covers
background access modes, sprite-fetch budgets, read/write interlocks and the
fetch-end boundary using guest-created display phases. The observers preserve
actual original Gear callbacks and distinguish request latency, arbitration
denials and CPU waits. The deferred frozen-source audit, 81 corrupted-data
controls and a fresh Ys III TCP regression now pass on the documented source
pin. See [active-display tests and qualification status](docs/VDC_ACTIVE.md).

**Disc layouts now support CUE POSTGAP.** Virtual postgaps move later track
positions without consuming stored bytes. Authored layouts, direct original
Beetle media checks and explicitly equivalent Gear fixtures verify the stated
geometry/payload scope. Successful CD READs also advance the retained head
used by position queries, matching Gear; failed and blocked loads preserve it.
Captured Q now has an [explicit profile](docs/CD_SUBCHANNEL.md); subchannel
byte/IRQ and broader index history remain separate work. See
[media formats and limits](docs/MEDIA.md).

**Repeated consumer builds can reuse verified native packages.** The optional
Windows x64 LLVM-MinGW/Ninja cache freshly configures and checks the current
build inputs, then restores an identical executable/DLL package on an exact
hit. It skips consumer compilation/linking and issues a fresh receipt;
runtime tests still have to execute. Changed code or toolchains get a new
key. See [cache setup and limits](docs/BUILD_CACHE.md).

**Long diagnostic routes can keep an explicit wall timer.** Both hosts and
consumer descriptors accept 1–86,400 seconds, including sessions longer than
ten minutes. Guest step/tick limits remain active; existing recipes retain
their selected limits. Actual CLI/TCP expiry tests and a real native consumer
build/run verify the host-only change without an ABI migration. See
[finite host sessions](docs/SESSION_LIMITS.md).

The ordinary System Card bus also accepts ignored writes to decoded CD
register holes and returns pull-ups for unused expansion I/O. Known disabled
devices still fault. These are shared hardware-profile fixes, with exhaustive
authored tests and a separate Geargrafx instruction comparison; the runtime
decode fix retained ABI **24**. Reference engines disagree on some CD aliases, so this
profile and the comparison scope are explicit. See [CD I/O](docs/CD_CONTROL.md).

**Static discovery can follow proven bank switches.** Opt-in
`analyze`/`emit --follow-mappings` tracks conservative register constants
through TAM, including executing-page remaps and reused logical PCs. The
generated C++ still checks the actual full mapping and every source byte.
Unknown mapping changes and call-return mappings remain explicit; the
single-mapping path is retained. An authored original-Gear comparison checks
six mappings and 26 static sites, with 80 actual native retirements and zero
fallback. See [static discovery and bounds](docs/STATIC_ANALYSIS.md).

Clocked VDC profiles now queue CPU VRAM transfers and model display/DMA
contention. BUSY reflects pending work; CPU stalls advance devices and IRQ
sampling without inventing extra instruction retirements. The shared VRAM
read bus and fetched sprite data remain intact, and inspection stays pure.
The current shared layout requires **runtime ABI 29**: re-emit original-labeled captures and rebuild
consumers together. `--vdc-access immediate` preserves the previous reference
path; consumer projects can pin either profile. See
[queued accesses and qualification limits](docs/VDC_ACCESS.md) and
[retained VRAM bus behavior](docs/VRAM_BUS.md).

The queued-access batch's SDL check passed **1,071 Python tests without skips and
53 C++ suites**. See [status and source pins](docs/STATUS.md).
Independent Geargrafx checks cover 615 queued-access cases and a separate
**54-case timer/IRQ probe during genuine VRAM stalls**. The latter matches all
CPU/device/timestamp records exactly and executes 1,188 translated native
retirements with zero fallback.

A fresh **26,751-frame ordinary-input town and first-mine TCP test** executes
**791,721,517 native instructions with zero interpreter fallback**, including
101,674 block transfers. A separate interpreter replay matches all 629
checkpoints, 185 guest/window image and WRAM observations, full source
identities/hits, wait counters and digital PCM. Shopping/equipment, a drawn
sword, an enemy reward and received damage are verified. This qualifies a
finite route, with full campaign and physical hardware timing still open.
The route was freshly captured with ABI25, compiled and replayed natively on
the documented implementation pin, including the new stable source layout
and large-contract cache path. This is a consumer regression, not
whole-game static CFG recovery. Older qualification records retain their own
source and ABI bindings.
Separate queued death/retry and SAVE/LOAD routes now pass **28,285 and 27,845
frames**, executing **840,056,911 and 823,837,671 native instructions with
zero interpreter fallback**. Their interpreter replays match guest state,
images, source identities, digital PCM, waits and exported backup memory.
The SAVE test checks actual RAM restoration after confirmation, including a
LOAD preview that changes the HUD before loading. An authored native test
also checks queued VRAM stalls with persistence across fresh processes.
An additional fresh-process smoke test imports the successful SAVE run's
export and restores its saved town progress. That supplementary run uses
interpreter fallback; it is separate from the two fully native comparisons.
See [current evidence and comparison limits](docs/STATUS.md).

**Explicit persistent BRAM is available in both hosts and the consumer runner.**
`--bram-out` exports a new raw 2 KiB snapshot after successful execution;
opt-in consumer sessions add isolated namespaces, exact media/firmware/save-contract
binding, corruption checks, process locks and atomic save publication. Existing
volatile recipes and read-only seeds keep their behavior. A new save remains
unformatted until the guest initializes it; no firmware menu is silently skipped.
See [persistence](docs/PERSISTENCE.md) and the
[fully authored native save example](examples/persistent-consumer/README.md).
Windows consumer builds also package their linked non-system runtime DLLs,
including compiler libraries, and fail on unresolved imports. See
[package scope and verification](docs/CONSUMER.md#verify-a-windows-desktop-package).
TCP status also reports current input masks for pipelined control requests,
without changing guest joypad sampling or advancing simulation.

The shared toolkit supports multi-context native promotion and hash-pinned
consumer builds. On the retained 93,735-frame Ys III test route,
executed native instruction coverage rises from **0.173% to 99.99997%**.
This measures that route, including firmware/wait loops; unvisited code and
complete-game compatibility still require qualification.

Large observed-code modules build as separately compiled translation
units, shared by headless and desktop hosts. Native dispatch selects exact
opcode/operand keys instead of scanning source variants; every instruction
byte is still checked before guest state changes. Consumer builds pin every
generated source and header. See [performance measurement](docs/PERFORMANCE.md)
for the benchmark and its scope.
The retained ABI-12 Windows x64 comparison compiles the full module in **70.5 seconds
versus 353.2 seconds**, and five alternating authored dispatch samples show
**9.5% higher throughput** with identical results. These measurements cover
module compilation and an authored CPU workload, separately from game testing.
The bounded Ys III bootstrap's whole-process difference is about **1.4%**;
no campaign-wide speedup is claimed.

The runtime produces stereo PCM from PSG, MSM5205 ADPCM and read-only CDDA,
with bounded WAV capture and optional SDL playback. **Raw 44.1 kHz remains
the default reference path.** The opt-in filtered profile adds PSG DC removal,
ADPCM DC/low-pass filtering and gain smoothing, with deterministic **44.1 or
48 kHz** output. Separately compiled Geargrafx 1.8.4 checks match **59,505
filtered PSG stereo frames across 3,266 authored cases** and **34,112 filtered
ADPCM frames across 17 held-input cases**. These source-filter checks exclude
decoder clocks, the final mix, device conversion and analog hardware; earlier
digital-source evidence retains its documented scope.

The authored 64-tap rational FIR has at most **0.001661 dB** passband error in
the tested sweep through 18 kHz and about 0.70 ms causal delay. It cannot remove aliases
already folded into the source observations. Default **`gear-v1` timing** now
uses ceiling-rational sample edges and clock-latched PSG DAC outputs, including
register writes between PSG clocks. `--audio-timing legacy` preserves the
previous sample timing and PCM path. Timing is independent of raw/filtered
selection. **ABI 15** introduced the guest CDDA cursor and sample latch alongside
the held PSG DAC state. Retained ABI-12 through ABI-28 captures can be re-emitted for current ABI 29, but
modules and runtime must be rebuilt together.
Consumer schema remains **1**. See [audio controls, evidence and limits](docs/AUDIO_OUTPUT.md).

Guest CDDA sample-latch ports **`$1805/$1806`** now work with PCM on or off.
They hold signed post-fader samples, enforce the 700-tick admission interval
and alternate right first. Nine authored cases / **367 distinct Geargrafx
checkpoints** agree with both PCM settings. Filtering, output rate and legacy
presentation timing do not change guest latch behavior. See
[the port contract and reference limits](docs/CD_AUDIO.md#guest-sample-latch).

The retained ABI-16 consumer migration follows a checked verification path: regenerate
the retained capture, preserve translated operations and guards, then check
legacy audio, default Gear timing and audio-off execution separately. Fresh
desktop runs reproduce the **94,800-frame, 39-checkpoint assisted route** in
all three modes; fresh headless comparisons match guest state and PCM/WAV
within each audio timing profile.
Regeneration retains the existing native coverage; it adds no new gameplay
milestone. See the [current upgrade guide](docs/CONSUMER.md#upgrade-a-consumer-to-abi-29)
and [consumer integration evidence](docs/STATUS.md#abi-16-consumer-integration).

The base compatibility profile now includes **BRK in both execution tiers**,
**8 KiB work-RAM mirrors across banks `$F8..$FB`**, and **VDC sprite-zero
collision / sprite-overflow status and interrupts**, independently of host
rendering or audio. Current runtime **ABI 29** requires regenerated modules and a
matching runtime; retained ABI-12 through ABI-23 captures remain usable as
original compiler inputs. Bounded unknown-CD diagnostics retain opcode counts
and the original command source context. Strict unknown-command behavior is
unchanged. Current build results are recorded in [STATUS.md](docs/STATUS.md). Independent
Geargrafx checks cover sprite event timing, BRK/RTI and WRAM aliases; see
[compatibility contracts and limits](docs/COMPATIBILITY.md) and
[verification scope](docs/REFERENCE.md#base-compatibility-references---abi-16).

**HuCard reset-vector startup** now runs explicitly declared base cartridges
without System Card firmware. It supports selected ROM mirror maps, raw or
explicitly headered/bit-reversed input, base RAM and PSG/input/video with CD
hardware absent. Both hosts and pinned consumer builds support it. Eight
authored ROM sizes match Geargrafx across 56 cases; actual native-only HuCard
consumer tests also pass TCP guest input, mirrored fetches and digital PSG
audio. See [the HuCard contract and limits](docs/HUCARD.md).

Explicit **SF2 banking** and **Populous cartridge RAM** profiles extend this
path. SF2 supports the full 2.5 MiB image with all sixteen mapper-latch
addresses; Populous provides 32 KiB of mirrored cartridge RAM. Native guards
handle switched ROM and guest-written RAM code at the same logical and physical
addresses. Both profiles support pinned consumer builds and TCP controls,
without automatic title detection or implicit cartridge-save persistence.

An optional **Arcade Card Duo** expansion adds 2 MiB of RAM to explicit Super
System Card boots. Its four data ports, mapped windows, address arithmetic,
shifter and identification registers share the normal interpreted/native bus.
Side-effecting windows remain I/O rather than fictional executable RAM.
See [Arcade Card setup and limits](docs/ARCADE_CARD.md).

The timer preserves its disabled reset/control phase, including the readable
counter value before its first enable. Bounded, read-only TCP code-capture
inspection exposes retired source addresses and native/interpreted counts
while paused, without closing the run or exporting instruction bytes.
See [timer semantics](docs/TIMER.md) and
[live capture inspection](docs/DEV_SERVER.md#paused-code-capture-inspection).

**System Card reset-vector startup** runs the supplied firmware from its
actual ROM vector, with explicit Standard/Super memory profiles and no
preloaded IPL or invented BIOS services. Both hosts and the pinned consumer
interface support it. Startup uses a named deterministic Gear initialization
policy; it does not claim unspecified hardware power-on values or warm reset.
An audio-enabled TCP run executes **14,680 frames** from the real reset vector
through the System Card menu and new-game selection into Ys III's town opening:
**432,875,213 native / zero interpreted instructions**, with zero guard misses
and no RAM edits. A separate first-600-frame capture records **17,483,730 native
BIOS instructions**. The established `$FF` response-profile condition still
applies when leaving the introduction. This is bounded observed-code coverage;
unvisited code and complete-game compatibility remain unqualified.
See [reset boot and its reference scope](docs/SYSTEM_CARD_BOOT.md)
and the [authored example](examples/reset-consumer/README.md).

The regenerated ABI-17 module also passes the separate retained
**95,686-frame / 68-checkpoint** gameplay regression, preserving its existing
assists and filtered 48 kHz audio results. See
[native integration evidence](docs/STATUS.md#native-reset-promotion-and-abi-17-integration).

The [capture-to-native reset example](examples/reset-consumer/README.md#capture-mappings-that-a-fixed-cfg-cannot-discover)
demonstrates actual guest MPR changes and mirrored ROM fetches. Four fresh
Standard/Super × headless/desktop consumer builds each retire **200 native /
zero interpreted instructions**; separate TCP runs each execute two frames
entirely natively. The native-only Geargrafx oracle checks **1,320 translated
instructions** across 38 retained reset cases and 12 new mirror-fetch cases.
This authored coverage is separate from retail execution. Consumer receipts
also verify reset metadata against the pinned firmware vector and check fresh
capture ABI, capacity and execution-tier counts. See
[reference scope](docs/REFERENCE.md#system-card-reset-references---abi-17) and
[receipt guarantees](docs/CONSUMER.md).

**Read-only BIN/CUE support** now covers single-file and multiple-file MODE1
and AUDIO tracks, stored and virtual pregaps, and signed little-endian audio.
Consumer builds pin the CUE and every referenced BIN through one complete-image
identity. Six authored images match independently compiled Geargrafx media
reads; native-only CUE consumers also complete real guest CD reads through TCP
in both hosts. Unsupported layouts fail explicitly. See
[supported media, identity and limits](docs/MEDIA.md).
The Ys III project also passes a fresh 5,526-frame CHD boot/read/audio
regression against this update, with all 20 checkpoints matching its verified
build. Its separate native-coverage work continues independently.

The project is AI-assisted and welcomes human and AI-assisted contributions.
Every contribution needs understandable code, appropriate source
attribution, and evidence for the behavior it claims. The maintainer is
building this with contributors; expert hardware and compiler review is
especially welcome.

## What works today

- Read-only CHDv5 track inspection, hashing, stored/virtual pregap handling,
  and separation of disc LBAs from padded CHD frame offsets.
- Optional libchdr decompression with a four-hunk cache; no full-disc extraction.
- Bounded IPL discovery from CHD, supported BIN/CUE or cooked ISO and creation of a pinned
  boot-program snapshot. The supported loader subset is documented.
- HuC6280 instruction decoding, bank-aware fetches, bounded control-flow
  discovery, and explicit unresolved edges.
- Direct C++20 emission with mapping and source-byte guards. Unmatched code
  falls back to the interpreter when supported, or exits explicitly.
- Opt-in [retired-code capture](docs/CODE_CAPTURE.md) records exact executed
  instruction identities and per-tier hit counts. Offline `emit-capture`
  supports multiple full MPR contexts, overlays and source-byte variants,
  with direct translated operations and guards before guest mutation.
  Adaptive partitions and exact operand-key dispatch support larger captures;
  CMake compiles each selected module once for both hosts.
  `--code-capture-start-frame N` can exclude startup from the observation
  window, with explicit start and preceding-retirement metadata.
  Captures and game-derived modules remain private.
- A [consumer-project interface](docs/CONSUMER.md) pins tool source, ABI,
  module and input identities, builds against the shared runtime, and records
  actual native/interpreted execution. The [authored example](examples/consumer/README.md)
  builds and runs without game or firmware data.
  Windows desktop consumers include their selected SDL runtime DLL beside the
  executable and pin its hash in build/run receipts, including when embedded
  from a parent CMake project.
- Headless CPU sandbox, native/interpreter counters, deterministic synthetic
  tests, CMake/CTest integration, and a cross-platform CI template (activation
  requires GitHub workflow authorization).
- Optional independent single-step comparison through Geargrafx's MCP
  debugger: the original 47-opcode baseline passed 188 comparisons per tier;
  the 24 added bit/stack opcodes passed 128 directed comparisons per tier.
  The 97-encoding data suite passed 1,552 comparisons per tier,
  including T and decimal contexts. See [verification scope](docs/REFERENCE.md).
  The 32-opcode shift/rotate/INC/DEC/indirect-JMP batch passed 512
  comparisons per tier, including full work-RAM checks.
  The bit-test/bit-branch/BSR batch passed 480 comparisons per tier.
  The MPR batch passed 524 sequences and 1,614 instruction-state comparisons
  per route; its native-first route includes counted fallback after mapping
  changes. See the same verification scope for exact totals and limits.
  CSL/CSH checks match 120 CPU/speed states per tier. Live traces expose
  28 transition-timing differences per tier against Geargrafx 1.8.4; the
  runtime follows Mesen/Beetle's final-cycle speed-change rule.
- Optional user-supplied 256 KiB System Card ROM mapping, with read-only
  protection and synthetic firmware loader tests. See [firmware scope](docs/FIRMWARE.md).
- Limited idle CD control and **volatile 2 KiB BRAM**: `$1807` access control
  and Gear-reference gate readback,
  `$1803` read-to-lock, ACK/IRQ-enable/reset state, physical MPR aliases and
  protected/hole writes. Geargrafx checks passed 720 CPU/device states per
  tier and 48 complete work-RAM/BRAM comparisons per tier.
  Both runners accept `--bram RAW_2048_IMAGE` to read an exact 2,048-byte
  initial image into existing volatile BRAM. The file is never modified;
  there is no automatic formatting, export or host save persistence. Omitting
  the option preserves blank BRAM. Explicit export and consumer persistence are
  described in [PERSISTENCE.md](docs/PERSISTENCE.md). TCP status and final JSON report
  `cd_control.bram_seeded`. See [BRAM initialization scope](docs/REFERENCE.md#initial-bram-image-and-authentic-format-provenance).
  See [implemented registers and reference differences](docs/CD_CONTROL.md).
- Opt-in clocked CD selection and command handshake: separate host/drive data
  latches at `$1801`, REQ/ACK reception, six-byte TEST UNIT READY, and delayed
  status/message completion with an IRQ2 source. REQUEST SENSE returns the
  fixed NEC 18-byte error response, with typed media failures and retry support;
  original CHD RW_RAW capture and opt-in retained Q now have a
  [separate contract](docs/CD_SUBCHANNEL.md). See [CD error recovery](docs/CD_SENSE.md).
  Drive delays follow an explicit
  reference-emulator profile; GOOD status does not certify readable media.
  Geargrafx checks passed **743 settled CPU/device checkpoints and 21 full
  work-RAM/BRAM comparisons per tier**, including reset and ACK edge sequences.
  See [CD transport scope](docs/CD_CONTROL.md).
- Directory/TOC command `$DE` modes 0/1/2, BCD track/MSF conversion and leadout
  selection, four-byte DATA IN responses, manual and `$1808` auto-ACK, data IRQ
  sources and reset/transfer aborts. A bounded `pcerecomp toc` exporter accepts
  CHD metadata, supported BIN/CUE or a single-track ISO; `pce-headless --toc` attaches the resulting
  descriptor. This supplies metadata responses; sector attachment is separate.
  Geargrafx/Mesen and Beetle differ on response lengths; the selected four-byte
  profile and exact limits are in [CD semantics](docs/CD_CONTROL.md).
  Geargrafx checks qualified **25 of 26 plans: 1,964 settled checkpoints and
  25 full work-RAM/BRAM comparisons per tier**. One pending-response reset case
  remains unqualified after reproducible crashes of the isolated reference.
- TII, TDD, TIN, TIA and TAI block transfers: forward/backward/fixed/alternating
  addresses, 16-bit wrapping, zero length as 65,536 bytes, sequential overlap,
  genuine stack saves/restores and operands fetched after those saves. Generated
  C++ contains the copy operations directly. Guest clocks progress per byte;
  VDC waits and block-specific I/O reads are explicit. See
  [CPU semantics](docs/CPU_SEMANTICS.md) for timing, atomic deadline and IRQ limits.
  Geargrafx checks pass **810 completed-instruction CPU states, full 8 KiB RAM
  comparisons and total clock deltas per tier**, including all five zero-length
  operations. Exact per-byte bus phases and hardware behavior remain unqualified.
- CD READ `$08`: 21-bit LBA, zero-count-as-256, bounded 2 KiB DATA IN
  streaming, manual/automatic ACK, backpressure, reset and explicit failures.
  `pce-headless --disc` attaches a read-only ISO/CHD/BIN-CUE provider with actual-image
  SHA256 binding, bounded CHD caching and no extraction. CUE identities cover all
  referenced files. CHD requires an explicitly
  selected optional libchdr library. The default fixed 1x access profile omits
  seek distance; opt-in [distance timing](docs/CD_TIMING.md) covers calibrated
  READ/CDDA seeks. Neither models initial jitter. The earlier Geargrafx checks pass
  **seven plans, 201 settled CPU/device checkpoints and seven complete sectors
  (14,336 payload bytes) per tier**. Local READ/provider expectations pass
  **621,096 / 22,568 checks**; see [CD semantics](docs/CD_CONTROL.md).
- Functional single-VDC register ports, 64 KiB VRAM, buffered reads, address
  increments, register masks and direct ST0/ST1/ST2 instructions. Mapped
  accesses include a fixed CPU wait. The extended video profile adds palette
  ports and VRAM/SATB DMA, including retained-bus reads in undriven VRAM.
  Physical VRAM contention and fetch phases remain unfinished.
  Geargrafx checks passed 856 settled CPU/VDC states and 48 complete
  work-RAM/VRAM comparisons per tier.
  See [VDC semantics and limits](docs/VDC.md).
- Opt-in master-clock video timing: programmable horizontal/vertical phases,
  VBlank and raster-comparison events, latched status/IRQ acknowledgement, and
  VCE timing control. Native and interpreted instructions both advance the
  device clock. CPU bus phases remain an instruction-level approximation;
  exact access phases remain unfinished.
  Geargrafx checks passed **4,165 exact-clock device checkpoints and 15 guest
  status acknowledgements** across 15 authored timing plans.
- IRQ priority, mask/status registers, clocked timer, eight-cycle interrupt
  entry and seven-cycle RTI in both execution tiers, including delayed CLI/PLP
  recognition and already-sampled requests after SEI. Geargrafx passed **832
  plans per tier: 2,496 CPU states, 832 complete RAM images and 832 sequence
  clock deltas**. This qualifies the documented instruction-boundary profile,
  with finer MMIO/timer access phases still excluded.
- VCE's 512-entry palette, VRAM/SATB DMA and bounded RGB state inspection.
  Geargrafx passed **12 direct-device plans**, including complete VRAM, SATB
  and palette comparisons and 1,024 guest palette-read bytes. With
  `--video-output snapshot`, `--frame-out` inspects current storage and registers.
  Continuous mode instead saves the last completed historical frame.
  See [video scope](docs/VDC.md).
- Continuous software video preserves line history and converts the live VCE
  palette at every emitted guest dot. BXR/BYR, CR/burst and MWR latches,
  background/sprite priority and bounded completed-frame publication are
  implemented. Geargrafx comparisons pass **16 complete 256 Ã— 192 images /
  786,432 RGB pixels**, including midline palette, scroll and VRAM changes.
  Local expectations pass **3,950 checks**. See [continuous video](docs/VIDEO_OUTPUT.md)
  for the selected line-buffer profile, state contract and remaining limits.
- Optional SDL3 desktop host: nearest-neighbor streaming texture, integer
  letterboxing, resizing, fullscreen, pause/resume, keyboard and gamepad input,
  focus release and guest-master-clock pacing. The default build has no SDL
  dependency. See [desktop controls and scope](docs/DESKTOP.md).
- Opt-in local TCP development control: status, five controller masks,
  pause/resume, bounded frame stepping, guest or composed SDL RGB captures,
  and orderly quit. Both hosts preserve normal guest input sampling. The
  standard-library Python client can save requested images as new PNG/PPM
  files. The server is disabled by default and binds only loopback; it receives
  no file paths. See [development protocol and bounds](docs/DEV_SERVER.md).
- Six-channel PSG waveform/DDA/noise/LFO synthesis, MSM5205 digital ADPCM
  decoding and CDDA PCM from read-only CHD audio sectors. The existing port,
  IRQ, DMA, CDDA command/timeline and fader models remain separate from
  presentation. A guest-clock mixer produces raw 44.1 kHz signed-16 stereo;
  opt-in source filters and fixed-point rational resampling add filtered
  44.1/48 kHz output without changing guest cadence or the raw diagnostics.
  The optional SDL host plays bounded queues, and explicit WAV output is
  bounded and never overwrites a file. The original eight-plan settled-port
  reference remains distinct from raw CDDA samples, the separately compiled
  PSG oracle and the ADPCM decoder/save-state comparison.
  Complete retail sound, the physical analog circuit and parity with
  Geargrafx's final mixed/device output remain unqualified. See [audio output](docs/AUDIO_OUTPUT.md),
  [control scope](docs/CD_AUDIO.md) and [reference evidence](docs/REFERENCE.md).

- Opt-in joypad I/O throughout the hardware-bank `$1000..$13FF` window:
  active-low two/six-button pads, a five-port TurboTap, region/CD-presence
  bits, latched guest-write sampling.
  The selected Geargrafx reference profile and differences from Mesen/Beetle
  are documented in [controller semantics](docs/INPUT.md). The optional desktop
  host maps its live input to pad one; turbo generation and other peripherals
  remain unfinished. Independent local
  expectations pass **50,341 cases/groups**, with eight synthetic headless
  configuration tests. Geargrafx checks pass **56 plans, 2,512 CPU/port-read
  checkpoints and 56 complete work-RAM comparisons per tier**, covering USA
  region with CD hardware present and absent.

The general toolkit is exercised with an owner-supplied Ys III USA CHD. A
**60,338-frame ordinary-input route** reaches LEVEL 2, the four-exit mine
junction, combat and normal guest SAVE/LOAD. Its retained baseline-host replay
matches **14 complete checkpoint images and all original final
CPU/device/source diagnostics**, with zero RAM edits.

A separate, explicitly authorized assisted route reaches the **first
storehouse boss at frame 93,212**. Its approach uses health assistance,
queued ascent and height-held traversal, followed by an ordinary room
transition and Up door entry. During **523 boss frames**, ordinary II attacks
visibly reduce the ENEMY bar while the wizard teleports and attacks. Only
**14 current-health refills** occur during the fight; no code, position,
queue, inventory or quest edits occur after entry. Original jump code is
restored beforehand. This establishes an assisted encounter and enemy
damage, not victory or unassisted completion.

The original 785-identity module executes **5,050,558 native and
2,915,442,205 interpreted instructions** on that 93,735-frame route. Bounded
profiling observes **44,836 identities in 57 full MPR contexts** without loss.
The expanded module compiles **44,832 identities** and executes
**2,920,491,782 native instructions and 981 interpreted**, including all
460,685 block transfers natively. The entire temporary code-patch span is
excluded from promotion; original and patched identities there stay interpreted.
The unchanged raw capture and exclusion counts remain separately recorded.

The retained ABI-13 audio-enabled, partitioned-module SDL/TCP replay matches **25 complete guest PNG hashes,
all 709 existing RAM interventions and every exposed final guest
CPU/device/source diagnostic**. Its complete guest runner report also equals
the previous ABI-12 full-native run after separately validating the new
`audio_output` object and host telemetry, including all original tier and guard counts.
Total retirements, guest clocks, source generations and device results stay
exact; ephemeral TCP port and additive SDL host telemetry are checked separately.
It reads **1,181 sectors with zero errors** and retains no new image files.
The comparison excludes whole RAM and composed-window pixels. Complete accounting belongs in
[status](docs/STATUS.md) and [reference evidence](docs/REFERENCE.md).
That earlier run generates **69,095,406 stereo PCM frames**, with PSG, ADPCM and
CDDA activity and zero runtime queue discard. Unthrottled device output is
intentionally muted. A separate paced SDL check accepts/drains 930,219 frames;
neither result claims listening or analog parity.

Fresh ABI-15 headless TCP regressions complete the original **93,735-frame
assisted Ys III route** with both audio profiles. All 25 images, 25 checkpoint
states, three final states, original guest/native diagnostics, PCM fields and
bounded WAV bytes match the preceding ABI-14 runs exactly. The new port
coverage comes from authored CPU and Geargrafx tests; this replay adds no
campaign progression or listening claim. See
[current latch regression](docs/STATUS.md#ys-iii-latch-regression-through-tcp).

Retained ABI-14 headless TCP replays complete the **93,735-frame assisted Ys III
route** with legacy raw 44.1 kHz and corrected filtered 48 kHz timing. Both
match all 25 images/checkpoint states and original guest/native results.
Legacy PCM/WAV remains exact. Corrected timing produces **75,205,884 output
frames**, with source/processed counts checked against guest time and zero
runtime discard. This is source-timing regression evidence; it adds no campaign
progress or new packaged-playback claim. See
[current timing regression](docs/STATUS.md#ys-iii-timing-regression-through-tcp).

The retained ABI-13 headless and packaged [Ys III consumer](https://github.com/rages4calm/ys3recomp)
TCP replays pass the same **93,735-frame assisted route** with raw and filtered
48 kHz audio. All 25 guest image/state checkpoints and original execution
results match. Raw PCM/WAV remains unchanged; filtered output produces
**75,205,884 frames**, with identical PCM/WAV across both hosts. Separate
paced **44.1/48 kHz** checks confirm packaged SDL loading without an SDK PATH
workaround, pause/resume/input and final queue drain. Those opening checks
exercise CDDA and conversion; active source-filter agreement comes from the
authored Geargrafx cases. All **190 consumer tests** pass. The final independent
batch audit passes **1,997 checks**, rehashing **1,065 actual artifacts** with
no pending evidence. This adds no game progression, listening or hardware-audio claim. See
[retained package evidence](docs/STATUS.md#retained-abi-13-packaged-ys-iii-consumer-qualification).

The previous raw-profile headless TCP replay with the corrected PSG reproduces all
**93,735 frames, 25 complete guest images and checkpoint states**, original
guest diagnostics and native/interpreted counts. All digital audio counters,
the PCM hash and bounded 30-second WAV also remain unchanged. The authored
ultrasonic vectors exercise the fix; this game route is regression evidence
and demonstrates no audible Ys III improvement.

The retained [Ys III consumer](https://github.com/rages4calm/ys3recomp) qualification rebuilds
against the corrected PSG runtime with the SDL packaging correction. Paced playback and the
complete 93,735-frame TCP replay both start from an empty working directory
without SDK or packaged `bin` directories on `PATH`; live process inspection
confirms that Windows loads the adjacent, hash-pinned `SDL3.dll`. All 25
checkpoint images, original guest diagnostics and digital PCM results remain
exact. The separate paced run accepts/drains 710,526 PCM frames with zero
runtime discard, 2,680 explicit pause-flush drops, peak queue 1,583 and final
queue zero; pause freezes guest/PCM state and resume advances normally.
The full replay intentionally mutes fast-forward playback. All **116 consumer
tests** and **137 independent evidence checks** pass.
Official descriptor verification/build and a direct TCP supervisor are
qualified separately. This adds package execution evidence on Windows x64,
with the same assisted route and audio limits. See
[retained qualification](docs/STATUS.md#retained-packaged-ys-iii-consumer-qualification)
and the [package verification procedure](docs/CONSUMER.md#verify-a-windows-desktop-package).

Reusable development features include paused RAM/ROM inspection and explicit
`--dev-memory-write on` RAM edits with whole-range expected-byte checks,
source invalidation and counters. The debugger contains no Ys-specific
address or cheat. Optional `--bram` reads an initial 2 KiB image; by itself guest
SAVE remains volatile. Explicit export and consumer sessions now add persistence
separately, without inventing guest formatting. Explicit execution
allowances retain tick and optional wall limits.

Geargrafx independently checks CPU/device behavior, scoped assists and normal
SAVE/LOAD; an aligned STATUS text crop matches **2,560 pixels**. It does not
qualify the complete boss route. The retained ABI-12 observed-code dispatch batch
passes **78 authored Geargrafx plans**, matching CPU/MPR/latch states, instruction
clocks and complete RAM in both tiers. Current runtime ABI is **29**; ABI-12 through ABI-28
observation captures can be regenerated, but old binary modules are incompatible.
The explicit unknown-command response profile is still required. Standard/Super
reset-vector startup is implemented separately; complete campaign, electrical
reset details, hardware audio parity and full native/AOT remain unfinished. No game/firmware bytes,
generated game source, captures or saves are included.

Contributor issues were reviewed on 23 October 2026: [RMB/SMB #1](https://github.com/rages4calm/pcenginerecomp/issues/1)
and [stack semantics #2](https://github.com/rages4calm/pcenginerecomp/issues/2)
are complete. [Media fixtures #3](https://github.com/rages4calm/pcenginerecomp/issues/3)
and [cycle-aware traces / second oracle #4](https://github.com/rages4calm/pcenginerecomp/issues/4)
remain open. Focused CPU timestamp and idle CD-control checks exist; a second live
reference adapter and general bus/event traces are still needed.

## Build and test

Use Python 3.11+, CMake 3.20+, and a C++20 compiler. Ninja is used below;
MSVC, GCC, and Clang are intended hosts. Only the tested configurations in
[status](docs/STATUS.md) are confirmed locally. The CI template defines the
intended public matrix and currently requires activation.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
python scripts/check.py --python-timeout 1800
```

The retained ABI-22 persistence/packaging SDL build passes **41 suites and all 597 Python
tests with zero skips**, including 24 actual headless/SDL export checks,
20 save-session tests, four packaging checks, two pipelined-input checks and
**313,508 authored CD sense/recovery checks**,
**39,710 authored timer checks** and live
capture inspection in both hosts. It also retains **478,512 authored DSP checks**, **20,852 PCM mixer checks**
and **159 SDL dummy-device checks**. Authored timing checks cover **29,418**
sample-edge, DAC-write and decoder cases; the CDDA cursor tests exercise both
timing modes. The sample-latch suite adds **3,047 authored checks** and
**48 native/interpreter instruction sequences**. The retained ABI-15 clean
public-source default build passes **28 suites**, with eight intentional desktop-only skips among
the same 316 discovered Python
tests. The filter reference's independent
source/artifact review passes **480 checks**, rehashing 244 actual artifacts.
The retained ABI-13 embedded SDL build passes all 28 suites and all 291 Python tests
without skips, including normal nested SDK discovery.
The separately compiled Geargrafx clock-driven oracle passes **102 cases,
1,551 checkpoints and 75,137 stereo frames** after integer mixer headroom.
It clocks real ADPCM decoding at all 16 rates and checks decoder state
separately; reference callback-dependent rate transitions have an explicit
single-master-tick comparison rather than an unconditional parity claim.
[Status](docs/STATUS.md) records each configuration and its evidence separately.

The final packaged Ys III reset-prefix regression completes **5,526 frames /
152,630,394 native instructions / zero interpreted**, matching retained guest
checkpoints, images, generated PCM and source hits. The documented comparison
keeps a bounded host audio-drain phase separate from guest output. Fresh authored
consumers also demonstrate persistent save/reload in both hosts on a runtime
PATH with no SDL SDK or compiler directories. See the current
[qualification scope](docs/STATUS.md#isolated-bram-persistence-and-windows-packaging--abi-22).

Clang can be selected with `-DCMAKE_CXX_COMPILER=clang++`. CTest is also
supported: `ctest --test-dir build --output-on-failure`.

For the optional window, supply an SDL3 SDK compatible with your compiler:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DPCE_BUILD_DESKTOP=ON -DSDL3_DIR=/path/to/SDL3/lib/cmake/SDL3
cmake --build build
python scripts/check.py --python-timeout 1800
```

This adds `pce-desktop`, using the same payload/mapping/budget and optional
firmware/disc arguments as `pce-headless`. It defaults to continuous video;
headless rendering opts in with `--video-output continuous`. Arrow keys move,
Z/X are I/II, Enter is Run, Shift is Select, Space pauses, F11 toggles
fullscreen and Escape closes. See [desktop setup](docs/DEVELOPMENT.md#optional-desktop-host)
and the [complete controls](docs/DESKTOP.md). The desktop attempts audio by
default; `--audio-output off` preserves silent presentation. Headless audio
is off unless requested or a new WAV is specified. Unthrottled desktop runs
mute speakers while retaining guest-clock PCM/WAV generation. See [audio controls](docs/AUDIO_OUTPUT.md).
With audio enabled, `--audio-profile filtered --audio-rate 48000` selects
filtered 48 kHz output; omitting both options retains raw 44.1 kHz with corrected
source timing. Add `--audio-timing legacy` to reproduce the previous PCM path.

Append `--dev-port 0 --dev-start-paused on` to either continuous-video runner
for local development control; port zero chooses an available loopback port.
The runner reports it as `PCE_DEV_PORT=N` on standard error. For example:

```sh
python scripts/dev_client.py --port 4370 status
python scripts/dev_client.py --port 4370 input 0x8 --frames 2
python scripts/dev_client.py --port 4370 screenshot new-frame.png --source guest
```

Replace the example port with the reported value. Screenshots are requested
explicitly and new output paths are required. See [the TCP guide](docs/DEV_SERVER.md)
for pause semantics, limits and the composed-window capture option.

The frontend works directly from a checkout without installing packages:

```sh
python -m pcerecomp doctor
python -m pcerecomp --help
python -m pcerecomp inspect "/path/to/your/disc.chd" --hash
python -m pcerecomp toc "/path/to/your/disc.chd" --out .local/title/disc.toc
```

For optional project-local CHD decompression, install no system components;
the following command explicitly fetches the pinned libchdr source and
builds it under `.deps/` (requires Git, CMake, Ninja and a C compiler):

```sh
python scripts/bootstrap_chd.py --cc clang
python -m pcerecomp boot "/path/to/your/disc.chd" --out .local/my-game/boot
python -m pcerecomp analyze .local/my-game/boot/snapshot.toml --out .local/my-game/analysis.json --listing
python -m pcerecomp emit .local/my-game/boot/snapshot.toml --out .local/my-game/native
```

Use an empty boot/native output directory. Pass `--libchdr /path/to/library`
if it is outside the default `.deps/libchdr-build` location. See
[the developer guide](docs/DEVELOPMENT.md) for running a generated module.

## Direction and contribution

| Read | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Execution model, bank identity, runtime boundaries and state ownership |
| [Consumer projects](docs/CONSUMER.md) | Pinned project descriptors, shared-runtime builds and execution receipts |
| [Native capture](docs/CODE_CAPTURE.md) | Bounded executed identities, source variants and offline native promotion |
| [Stable emission](docs/STABLE_EMISSION.md) | Opt-in full-MPR/logical-range parts and independent Gear execution |
| [Managed rebuilds](docs/INCREMENTAL_BUILDS.md) | Checked same-workspace object reuse, immutable history and failure handling |
| [Native spans](docs/NATIVE_SPANS.md) | Experimental bounded native batches with per-instruction boundaries |
| [Developer checkpoints](docs/DEVELOPER_CHECKPOINTS.md) | Exact-build paused machine save/restore, private files and resumed evidence |
| [CPU semantics](docs/CPU_SEMANTICS.md) | Instruction contracts, status flags, stack wrapping and verification |
| [VDC semantics](docs/VDC.md) | Video ports, VRAM, raster events, clock phases and explicit limits |
| [VDC latch checkpoints](docs/VDC_LATCH_CHECKPOINTS.md) | Live CR/MWR/queue boundaries, fresh-process restoration and raw reference differences |
| [Continuous video](docs/VIDEO_OUTPUT.md) | Historical pixel/line output, frame publication and remaining fetch-phase limits |
| [Desktop host](docs/DESKTOP.md) | Optional SDL3 presentation, controls, pacing and isolation |
| [Development control](docs/DEV_SERVER.md) | Loopback TCP commands, frame stepping and requested RGB captures |
| [CD semantics](docs/CD_CONTROL.md) | Command handshake, reference timing, BRAM and explicit transport limits |
| [CD audio control](docs/CD_AUDIO.md) | Position commands, guest timeline, fader and explicit audio-output limits |
| [CD audio gap admission](docs/CD_AUDIO_GAPS.md) | Preserved playback/source state, controller quirks and independent admission checks |
| [Audio output](docs/AUDIO_OUTPUT.md) | Digital sources, optional filtering/48 kHz resampling, bounded SDL/WAV output and verification limits |
| [Controller semantics](docs/INPUT.md) | Two/six-button pads, TurboTap, sampling and reference differences |
| [Research](docs/RESEARCH.md) | Primary sources, pinned references, existing tools and design decisions |
| [Roadmap](docs/ROADMAP.md) | Full feature target, dependencies and acceptance criteria |
| [Status](docs/STATUS.md) | Verified baseline, known limitations and next useful batch |
| [Development](docs/DEVELOPMENT.md) | Reproduce builds, run the CLI and understand private outputs |
| [Contributing](CONTRIBUTING.md) | Review standards and useful contributor work |

Completing CPU/device semantics, broader independent verification, System
Card integration, audio timing and hardware verification, remaining CD services, saves
and gameplay qualification comes before a playable release. Widescreen, high-refresh presentation,
mods, localization, achievements, rewind, and netplay are part of the target
architecture, with separate implementation and qualification milestones.

## License and inputs

Original code is [MIT licensed](LICENSE); opcode metadata retains its BSD
notice. Optional dependencies retain their own terms. See
[third-party notes](THIRD_PARTY.md). Supply your own game and firmware
inputs. Please do not attach ROMs, discs, BIOS images, extracted data, or
code-bearing traces to issues or pull requests.

## Community and contact

Discord: **chrono.trigger**

[**R.A.I.D. â€” Retro AI Development**](https://discord.gg/Ad9BwSzctP) Â· a Discord
for AI-assisted retro reverse-engineering, decomp & recomp. I post my work there;
join to discuss this project and the others.
