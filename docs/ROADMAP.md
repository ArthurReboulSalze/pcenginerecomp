# Roadmap and acceptance criteria

The target is a complete, contributor-friendly recompilation ecosystem.
These are ordered dependencies, not delivery dates. A planned feature is
not an available capability. Broader platform coverage must not postpone
finishing the base PC Engine/CD correctness path.

| Stage | Deliverable | Acceptance gate | Status |
|---|---|---|---|
| 0 | Media → snapshot → decoder/CFG → direct C++ → bounded CPU sandbox | Synthetic semantics and a real local image reach compiled native execution with explicit limits | Implemented foundation |
| 1 | Complete HuC6280 interpreter and independent reference adapter | All supported encodings, addressing modes, flags and boundary cases have independent evidence; unsupported slots remain explicit | 234 opcode encodings implemented; 22 reserved slots trap; bus/reference gaps stay explicit |
| 2 | Complete native lowering and multi-context analysis | Differential runs cover all implemented semantics, indirect flow, T/decimal modes, TAM/TMA and self-modification | Direct lowering, source guards, observed contexts/byte variants and opt-in static recovery across proven TAM mappings implemented; general indirect/interprocedural recovery remains |
| 3 | Cycle/event scheduler, timer/IRQ and actual memory map | Speed-change phases, bus waits, IRQ entry/return, mirrors and device ordering match reference traces | Aggregate clocks, raster, timer/IRQ implemented; base WRAM mirrors implemented; bus phases and hardware qualification remain |
| 4 | HuCard loader, System Card and CD transport | Authentic loader path, command/sector timing, overlay loads, failures and identity checks | Base/SF2/Populous HuCard startup, Standard/Super firmware boot, Arcade Card Duo, TOC, sense/read recovery, read-only ISO/CHD/bounded BIN-CUE providers and audio timelines implemented with bounded checks; further boards, broader commands and hardware reset/bus timing remain |
| 5 | Reference video/audio/input/persistence | Correct frames and sound for diagnostic software and bounded real-title routes; isolated BRAM save/load | Continuous rendering, input, explicit isolated CD BRAM persistence and decoded/mixed digital audio implemented with bounded checks; broader title/hardware qualification remains |
| 6 | First Ys III playable vertical slice | Cold boot, title, new game, field movement, scene transitions, sound and saves, with documented native/interpreted work | Finite authentic-reset town/mine/death/retry/SAVE-LOAD native routes qualified with digital audio; separate cold-save import smoke uses mixed execution. Explicit unknown-CD response profile required; no complete port/campaign claim |
| 7 | Overlay capture/compile/cache and optimizations | Bounded capture, reproducible modules, stale-cache rejection, parity and measured performance | Retired-code capture, partitioned native emission, exact-key dispatch, shared module objects, pinned consumer builds, opt-in exact Windows package cache, managed stable-module rebuilds and verified interrupted-build recovery implemented; runtime-loaded module cache and multi-instruction blocks remain |
| 8 | Desktop/player and mod ecosystem | Reproducible packages, input picker/remapping, settings, accessibility and guarded extensions | Optional SDL/TCP development hosts and finite state-aware route client implemented; player configuration, packages and ecosystem remain |
| 9 | Enhanced presentation and game-specific features | Each feature meets its own reference, state and gameplay gate below | Planned |
| 10 | Additional hardware and broad library qualification | Separate profiles, dedicated fixtures, real software routes and compatibility reporting | Planned |

## Full feature target

| Feature | Framework responsibility | Game-specific or qualification work |
|---|---|---|
| Native Windows/Linux/macOS, x64/ARM64 | Portable generated code, CMake, reproducible packages, host backend | Actual builds and runtime checks on each target; no ARM64 claim from x64 tests |
| HuCard, CD-ROM², Super CD-ROM² | Input identity, mappers, System Card and RAM profiles | Title/revision/patch recipes and loader behavior |
| CHD and BIN/CUE, ISO | Shared TOC and bounded sector provider, CDDA, subcode policy | Disc layouts, pregap/index behavior and multitrack fixtures |
| SuperGrafx and Arcade Card | Additional VDC/priority/RAM/device profiles | Dedicated titles and hardware-specific parity routes |
| Fast startup and loading | Immutable data caching, asynchronous host I/O, native overlay cache | Preserve observable CD timing unless an explicit compatible speed mod is enabled |
| Overlay compilation | Content/mapping/ABI-keyed modules and safe invalidation | Discover real entry points; retain fallback for genuinely dynamic code |
| Enhanced renderer | Software reference, GPU backend, scaling, palette/aspect controls | Software/GPU parity, raster effects, render-thread ownership |
| Widescreen and ultrawide | Expanded presentation and hooks | Camera/world streaming, sprite culling, HUD/menu layout, scene limits |
| High refresh / interpolation | Separate guest cadence and host presentation | Object/camera matching and discontinuity handling; intentional logic-rate mods separately tested |
| Texture/tile/sprite replacements | Content hashes, packs, resource budgets and renderer hooks | Safe replacement identity, asset permission and scene coverage |
| Audio improvements | PSG/ADPCM/CDDA fidelity, mixer, latency and optional replacement audio packs | Track maps, loops, fades, seek behavior and A/V synchronization |
| Controllers / multitap | Keyboard/gamepad remapping, hotplug, two/six-button and multitap protocol | Per-title button/protocol policy and multiplayer support |
| Saves / states / rewind | Isolated atomic BRAM, versioned snapshots, bounded history | Identity/ABI/mod compatibility and device-state reconstruction |
| Local co-op / rollback netplay | Input routing, deterministic states, session compatibility | Title-specific player logic/camera, ownership and desync diagnosis |
| Mods / patch packages | IDs, revision guards, expected-byte writes, dependency/conflict checks | Reference-preserving title hooks, patch ownership and compatibility |
| Localization | Text/font/tile replacement infrastructure and pack selection | Translation rights, encoding/font coverage, layout and story review |
| Achievements / accessibility | Event hooks, remapping, readable settings and user opt-ins | Stable game events; external API policy and per-title tests |
| Debugger / profiling | Bank-aware disassembly, breakpoints, bounded tracing, native/fallback counters | Independent trace adapters, useful symbolic maps and real routes |
| Project generation | Input/profile validation, build recipes, diagnostics and contributor scaffold | Reviewed title-specific annotations and asset handling |

## Immediate contributor batches

The retained 144 later PSG values now have a complete domain explanation:
original Gear HPF output was compared to raw toolkit output. Matched-domain
[audio traces](AUDIO_TRACES.md), longer guest pipelines and authored source/
filter/checkpoint vectors close that evidence gap without altering chip gain.
Further electrical bus phases, analog measurements and reference disagreements
remain separate work; equal digital traces do not certify hardware audio.

ABI 26 closes selected guest PSG write phases and CDDA end-change behavior;
see [AUDIO_BUS_TIMING.md](AUDIO_BUS_TIMING.md). Checkpoint regressions cover
audio source and DSP boundaries. Remaining work includes other device bus
phases, hardware traces, richer CPU vectors, analog audio qualification and
additional title/hardware routes. Repeating a qualified Ys III suffix does
not broaden library coverage. Re-emit and rebuild consumers for this ABI.

Exact consumer-package reuse is now implemented for a declared Windows
LLVM-MinGW/Ninja build profile; see [BUILD_CACHE.md](BUILD_CACHE.md). It fills
one contributor-tooling gap without claiming the planned runtime overlay
cache. [Stable partitions](STABLE_EMISSION.md) and the opt-in
[managed rebuild producer](INCREMENTAL_BUILDS.md) now address same-workspace
changed-unit reuse. Experimental [native spans](NATIVE_SPANS.md) now reduce
global dispatcher calls while preserving every instruction boundary. Their
current authored benchmark remains slower than legacy execution, so the default
is unchanged. Cross-workspace object reuse and a demonstrated faster native
block path remain future work, with source guards preserved. Next compatibility
work should broaden independent CPU/device vectors and actual HuCard/media
profiles beyond the finite Ys III regression. Do not treat a repeat of the
same route as new library coverage. Opt-in unmasked second-reference IRQ
retirement now has a finite timer/flags/mapping qualification, including
explicit engine disagreements; see [IRQ_TRACES.md](IRQ_TRACES.md). Next extend
it beyond the new guest-generated timer/VDC-DMA/CD priority and acknowledgement
matrix in [IRQ_DEVICES.md](IRQ_DEVICES.md) and the blank-slot DMA/CD
[dynamic-stall matrix](IRQ_STALLS.md): further raster/sprite and ADPCM
sources, further active-display/latch combinations, overlapping device combinations and interrupted
transfers remain.

[Verified interrupted-build recovery](BUILD_RECOVERY.md) is implemented as a
separate opt-in Windows x64 LLVM-MinGW/Ninja producer. It seals preconfigure
inputs, configuration and completed object groups, proves process-tree cleanup,
checks unchanged content and emits a new recovery-bound build receipt. Ordinary
partial directories, incomplete configure and unsupported profiles still need
a new build directory. Broader toolchain support and recovery of managed module
updates need their own contracts and interruption tests.

Opt-in [additive observation composition](OBSERVATION_PROFILES.md#add-identities-without-duplicating-overlapping-contributions)
uses a version 2 stage ledger to retain original captures while selecting only
new identities from each extension. It separates selected contributions from
full historical totals and preserves earlier selections when extending a
retained profile. Deterministic preflight and original-byte/ABI/origin joins
remain mandatory. The existing input/raw-byte/identity/serialization bounds
still apply; a scalable external history representation remains future work.

The [guest-driven CD DMA/IRQ checkpoint matrix](DMA_IRQ_CHECKPOINTS.md)
adds autonomous READ polling, ADPCM DMA, actual IRQ2 entry/handler/RTI and
natural-boundary restoration. Raw original-core clock differences remain
separate from functional continuation. Coincident raster/VRAM stalls, other
interrupted transfers and hardware bus phases still need their own evidence.
The [active-display matrix](VDC_ACTIVE.md) adds authored BG/sprite and
dual-queue endpoint evidence. Its fresh frozen-source audit, corrupted-data
controls and ordinary-input Ys III TCP regression are now complete on the
documented exact source pin. A separate [checkpoint latch matrix](VDC_LATCH_CHECKPOINTS.md)
now covers selected live CR/MWR and burst transitions with pending read/write
queues. Arbitrary geometry races, interrupted CPU accesses and mixed
active-display IRQ sources remain separate qualification work.
Consumers can also select [longer finite host sessions](SESSION_LIMITS.md)
without changing guest timing; existing recipes retain their limits.
The [state-aware TCP runner](STATE_ROUTES.md) now gives consumer projects a
shared way to wait for observed transitions with bounded ordinary input.
The ABI 26 investigation repairs one earlier missed doorway and reaches the
intended street dialogue. Requalifying the consumer's later route and its
package remains separate work; frame scripts and checkpoints do not become
portable across builds or timing profiles.
ABI 25 implements selected [live BXR/BYR scroll-write windows](VDC_SCROLL.md)
and [program-range-aware CD position replies](CD_POSITION.md). These close
specific source-backed gaps; they do not establish all midline register races
or raw subchannel behavior. Native modules and custom providers must be rebuilt.
Bus-event ordering and unknown CD command semantics remain gaps.
The open [reference-trace issue #4](https://github.com/rages4calm/pcenginerecomp/issues/4)
and [media-fixture issue #3](https://github.com/rages4calm/pcenginerecomp/issues/3)
still track broader work; the current finite probes do not close those gates.

1. **Reference adapters and CPU vectors.** A bounded code-free trace format,
   reusable first-difference comparator and original full Beetle PCE-core
   adapter now exist, with finite mixed-speed and unmasked timer/flags fixtures
   alongside Gear. The IRQ-aware format preserves raw calls and actual
   retirement groups; it retains divergent original-engine behavior.
   Extend this evidence to more CPU semantics and fixtures, a full Mesen
   adapter where useful,
   source edge/bus phases and cycle/event traces. Existing CPU, block-transfer
   and IRQ/RTI state checks retain their separately documented scope.
2. **CPU and device coverage.** The implemented CPU families are listed in
   [CPU_SEMANTICS.md](CPU_SEMANTICS.md). CPU interrupt entry/RTI, block
   transfers, controller I/O, VDC/raster/DMA and continuous video now have
   bounded verification. ABI 16 adds independently checked BRK, base WRAM
   mirrors and sprite collision/overflow events. CD control, TOC, read-only sector streaming and
   CDDA/ADPCM timelines support conditional private gameplay tests. Continue
   with remaining CD command/sense/subcode behavior, additional firmware/media
   profiles and device timing. ABI 17 implements explicit Standard/Super memory
   profiles and reset-vector firmware startup; warm reset and electrical
   power-on details remain separate. The unknown-command diagnostics
   identify repeatable command sources without implementing their semantics.
   HuCard loading and mapper profiles need their own authored and real-software
   qualification. Base HuCard startup, explicit SF2 banking and Populous RAM
   are now implemented. Optional Arcade Card Duo port/RAM hardware is also
   implemented on Super System Card profiles, with authored and independent
   device checks. Pro, SuperGrafx, further boards and persistent RAM remain
   separate work. Two-bit background
   decoding and digital monochrome also have exhaustive authored and isolated
   MesenCE function/filter checks; full fetch/bus timing remains open.
   Extend decoded/mixed audio evidence separately.
   Guest SAVE/LOAD and isolated raw export/import have finite queued-timing
   qualification; explicit host CD BRAM persistence is available. Other titles,
   RAM profiles and automatic repeated publication remain separate work.
   Exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) provide paused
   machine restoration; portable/cross-build states remain unimplemented. Resolve the
   unknown-command reference profile rather than treating it as hardware
   qualification. Avoid BIOS stubs or fabricated status events.
3. **Bus phases and scheduler.** Instruction retirement advances raster and CD time
   in both execution tiers. Replace the documented instruction-entry access
   approximation with explicit bus/event ordering, then extend qualified RAM/device profiles and
   remaining I/O and timer scheduling. Preserve code-write/bank-change guards
   before optimizing native blocks.
4. **Media edge cases.** Add independently constructed CUE/multitrack
   fixtures and clarify IPL addressing variants. Keep extraction bounded and
   retain the original image byte-for-byte.
   CUE POSTGAP is now implemented, including a final CUE postgap in leadout.
   A 288-layout authored matrix and direct original-Beetle media checks cover
   it; transformed Gear layouts have an explicitly narrower scope. The CHD
   trailing-postgap profile remains distinct. Successful READ head advancement
   and idle position responses are independently checked against Gear.
   Remaining work includes richer program/gap/index/control metadata for
   position responses beyond the implemented program/gap classification,
   broader captured-subchannel device interfaces, additional layouts and actual
   title/drive qualification. These checks do not establish raw-Q support.
   D8 start admission at known program gaps is now implemented with its own
   [state/handshake contract](CD_AUDIO_GAPS.md). It preserves existing audio
   and does not create a replacement seek. Unknown-metadata approximations,
   byte-stream subchannels and hardware consensus remain open. The optional
   [distance timing profile](CD_TIMING.md) now covers bounded READ/CDDA seeks
   and playback readiness while retaining the fixed default. Further measured
   drive models and addresses outside its calibration need separate work.
   ABI 29 now provides [original 96-byte P–W and opt-in captured Q](CD_SUBCHANNEL.md):
   explicit representation/absence, CHD RW_RAW extents, CRC/ADR retention and
   exact-build checkpoint state. Synthesized replies remain the default.
   A separately selected byte-stream/IRQ profile remains planned. Gear's
   ordinary media path and Beetle's FIFO acknowledgements differ; qualify
   each proposed interface against the original core that implements it,
   including overflow, mixed IRQ sources and restoration midway through a
   byte packet. New ABI 29 consumer packages require regeneration/rebuilding
   and independent qualification; existing SDK selections do not auto-migrate.
5. **Capture inspection and trace coverage.** Paused, bounded read-only TCP
   summaries and retired source-span pages are implemented, including exact
   native/interpreted counts, completeness/loss and deferred-window metadata.
   They preserve guest state and the final capture contract. Future
   chronological or bus-access traces require separate bounded storage and
   semantics; the current accumulated identity set is not such a trace.
   [Native discovery guidance](NATIVE_DISCOVERY.md) describes joining authentic
   captures to actual emitted identities and using the existing bounded,
   mapping-aware analyzer. Reusable gap reporting and authenticated paused
   physical-snapshot export remain planned; static candidates are not executed
   coverage. RomAtlas's current PCE frontend is HuCard-only.
6. **Identity-bound developer checkpoints.** Paused exact-build machine save
   and fresh-process restore are implemented, including pending device/DSP
   state and explicit resumed-window evidence. This remains separate from CD
   BRAM persistence. See [contracts and qualification](DEVELOPER_CHECKPOINTS.md).
   Future work includes additional independent active-device traces and newly
   supported device profiles. Cross-build/module migration, in-process rewind
   and portable end-user saves remain separate unimplemented interfaces.
   Imported prefix counters never count as newly executed work.
   [Active CD READ continuation](CD_READ_CHECKPOINTS.md) now extends the authored
   checkpoint evidence to command/data/status boundaries, ACK pulses, pending
   sectors, retries and cancellation. Its direct-device, supervised guest-port,
   original-register and private retail tests retain separate scopes. Further
   active-device overlap, hardware timing and cross-build state portability
   remain open.

The [block/DMA IRQ matrix](BLOCK_DMA_IRQ.md) now witnesses READ-fed ADPCM
assertion inside incomplete original block continuations with I already clear,
and deferred whole-instruction delivery/restoration across all five families.
The [VDC/ADPCM overlap matrix](VDC_ADPCM_IRQ.md) now extends selected blank-display
queued-access cases to competing IRQ1/IRQ2 sources and real guest device
acknowledgement. Arbitrary lengths and late epilogue edges retain separate
limits. Selected active-display raster/sprite overlap is now covered by the
[active-display IRQ/checkpoint matrix](ACTIVE_IRQ_CHECKPOINTS.md): real raster
or sprite-collision IRQ1 competing with READ-fed ADPCM IRQ2, all three VCE
dividers, both CPU speeds and actual natural-boundary restores. Its original
callbacks distinguish dynamic waits, block startup and pre-target assertions.
Other geometry, sprite overflow, further source combinations, a second
independent reference and hardware bus phases remain separate gates.
The selected overlap matrix retains −6/+3-master-tick wait differences in eight
recipes. The [phase investigation](VDC_PHASES.md) now explains them through
documented CSH timing, actual CD polling counts and observed dot/slot phases.
This diagnoses the selected discrepancy without a runtime patch. A separate
[periodic HSW profile](VDC_PHASES.md#periodic-horizontal-sync-coverage) now covers
the selected sync guard, parity and scanline wrap with actual latch evidence.
Arbitrary horizontal geometry, active-display and hardware arbitration remain
separate qualification gates.
[Durable wire replies and strict paused observations](PAUSED_OBSERVATIONS.md)
add reusable diagnostics; legacy fresh
host delivery and current exact-build queue continuation keep separate scope.
The [same-ABI raw-audit integration layer](RAW_AUDIT_INTEGRATION.md) adds typed
own-origin counters and complete encoded-key relations. Consumer role adapters
still independently admit each original raw journal, parent dependency, saved
state and write authority before composing an execution qualification.
Its streaming offline reader checks retained raw journals without requiring a
new guest run or loading the whole log. A complete raw ledger remains separate
from client admission, process completion and a qualification decision.
The implemented [typed paused-write relation](PAUSED_WRITES.md) accounts for
declared data CAS effects without suppressing source generations or weakening
strict observations. Explicit RAM topology, full backing readbacks and code
footprint exclusions remain consumer obligations. Offline lossless gzip
archives now preserve exact journals with separate container hashes; active
writers and complete game qualification remain outside that archive contract.
   The [coupled CD/ADPCM matrix](CD_ADPCM_CHECKPOINTS.md) additionally covers
   selected real READ-to-DMA pending states, RAM commits, pause/reset behavior
   and sector gaps. It retains 54 original-engine timing/state differences;
   further mixed-device overlaps and bus-phase qualification remain separate.

## Additive observation profiles — implemented

Production `compose-observations` and `emit-profile` now preserve exact original
capture bytes and accept mixed supported ABI epochs. Profiles reconstruct and
check complete source identities, input contributions and historical totals;
the existing single-capture and research helpers keep their original contracts.
See [observation profiles](OBSERVATION_PROFILES.md) for the supported API/CLI.

Each profile preserves input ABI labels, raw hashes, counts and checkpoint
origins, and unions complete PC/all-MPR/physical/byte identities without
dropping variants or old keys. Capacity, integer overflow and provenance
bounds refuse excess rather than truncate. Current
capture identity capacity is 65,536; input sizes cannot simply be added or
assumed to fit before deduplication. A composed set remains source evidence,
not a combined execution receipt or new current-ABI retirement count.
Emission distinguishes original capture epochs from generated-code ABI 29,
with per-input imported work kept separate. Consumer adoption still needs a
fresh cold run, newly created exact-module checkpoints and its own route checks;
profile composition does not migrate checkpoints or qualify a campaign.

Optional consumer profile binding is also implemented. Verification checks the
retained raw profile and reconstructed metadata/selection counts, normal
build/run receipts bind its identity, and managed generations retain its exact
bytes. Existing unbound descriptors remain supported. Strengthening identity
requires new checkpoints; a bound managed workspace refuses an unbound update.
Independent execution authentication, portable checkpoints and automatic
historical-session deduplication remain outside this interface.

Read-only [composition preflight](OBSERVATION_PROFILES.md#preflight-an-extension-before-emission-or-build)
now reports exact serialized bytes/hash, additive identity/contribution costs
and remaining capacity before emission or build. It shares real composition
admission and serialization; refusal stops at existing bounds with unknown
metrics left explicit. It preserves profile-v1 provenance and does not turn
historical captures into newly executed evidence.

The first playable release needs a clearly scoped qualification record. It
does not need every enhancement, but must accurately report what executes
natively, which fallback paths remain, and which gameplay/save routes were
actually tested.

Player startup should also be separate from qualification recipes. Tests may
deliberately use fresh, unformatted volatile BRAM; a finished consumer should
use isolated persistent saves and a reviewed startup flow. Generic persistence
and identity/atomic-write safeguards are implemented in the toolkit's explicit
[BRAM sessions](PERSISTENCE.md); title adoption and startup qualification remain.
Whether to present
or bypass firmware menus belongs to each consumer, with required initialization
preserved. Skipping a menu is not evidence that execution is native, and a
visible firmware screen does not establish that it is interpreted.
