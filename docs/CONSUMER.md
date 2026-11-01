# Consumer projects

A consumer keeps its game-specific source, assets, configuration and output in
its own repository. It selects the general toolkit as a pinned dependency.
The toolkit provides CPU translation, guarded dispatch, device models and
headless/desktop hosts. A consumer owns its entry/load recipe, media identities,
native coverage targets, campaign testing and any game-specific assistance.

When toolkit and consumer qualification run concurrently, bind the explicit
descriptor, generated module, binary and package files. An owner's launcher
selection is separate from that recipe. Record its observed epochs if an
independent consumer workflow promotes a package; do not restore an older
selection or require unrelated work to freeze. Keep media and the explicitly
selected test package strict and immutable.

The public contract is `python -m pcerecomp.project` (Python 3.11+), consumer
TOML schema **1**, runtime ABI **28**, and the existing `pce-dev-1` TCP protocol.
No Python package dependency, installation, download or save write is implicit.

For finite TCP progression checks, [state-aware routes](STATE_ROUTES.md)
validate/preflight typed guest-state predicates before holding input and retain
raw observations with actual work. Keep title-specific plans private. A route
receipt qualifies only its bound consumer and observed interval; successful
input acceptance or a frame count alone does not establish guest polling or
complete migration.

Run the Python commands from the toolkit checkout, or put that checkout on
`PYTHONPATH`; descriptor paths always resolve relative to the descriptor file.

Explicit mutable BRAM sessions are available through `run --save-root`,
`--save-namespace` and `--save-contract` together. They remain separate from
immutable descriptor assets and qualify boot provenance before committing.
See [persistence contracts](PERSISTENCE.md) and the
[authored native counter example](../examples/persistent-consumer/README.md).
Those host-only additions retained ABI 22. Current runtime interfaces require ABI 28; rebuild hosts
from the newly pinned source to expose them.

## Start with an authored example

The [consumer example](../examples/consumer/README.md) generates a six-byte
authored CPU program and native translation in a new private output directory:

```sh
python examples/consumer/prepare.py .local/consumer-example
python -m pcerecomp.project verify .local/consumer-example/project.toml
python -m pcerecomp.project build .local/consumer-example/project.toml --build-dir .local/consumer-build
python -m pcerecomp.project run .local/consumer-example/project.toml --build-dir .local/consumer-build --receipt .local/consumer-run.json
```

Build needs CMake 3.20+ and a C++20 compiler. Use `--generator Ninja` or an
available native generator. Explicit package/toolchain paths may be passed as
`--cmake-arg=-DCMAKE_CXX_COMPILER=...`, `CMAKE_MAKE_PROGRAM`, `SDL3_DIR` or
`CMAKE_TOOLCHAIN_FILE`. The interface does not fetch them. These paths and
configure/build commands appear in the build receipt; a controlled build
environment remains the consumer's responsibility. Build output uses at most
two parallel compiler jobs. Choose a new build directory for each build.

An opt-in [verified package cache](BUILD_CACHE.md) can reuse an identical
Windows x64 LLVM-MinGW/Ninja executable/DLL package. Every request freshly
configures; exact hits skip consumer compilation/linking. Explicit complete
toolchain/SDK roots and the effective build model participate in the key.
Build/run receipts and runtime assets are always freshly bound. Normal builds
remain available on other supported toolchains.

For changing observed modules, opt-in [stable source layout](STABLE_EMISSION.md)
and [managed rebuilds](INCREMENTAL_BUILDS.md) provide checked same-workspace
object reuse on the audited Windows LLVM-MinGW/Ninja profile. The managed
producer owns its copied module/descriptor/build; ordinary `build` still needs
a new directory. Build receipts remain separate from execution qualification.

To retain an old catalogue while adding observations from a newer ABI, use
the supported [observation-profile interface](OBSERVATION_PROFILES.md).
`compose-observations` preserves original raw inputs and per-input evidence;
`emit-profile` generates the ordinary schema-1 module consumed here. Retain
the hash-bound profile alongside build evidence. Optional
`[module.observation_profile]` with `path` and `sha256` makes the consumer
verifier admit it and bind it in build/run receipts; managed builds also copy
and archive its exact bytes. Existing descriptors remain valid. Opting into
this binding changes checkpoint context and requires fresh checkpoints even
when generated C++ is unchanged. A composed
catalogue does not qualify migration or make an older checkpoint compatible
with the new module: use a fresh cold run and new exact-module checkpoints.

An observed module emitted with `--partition-layout stable --native-span`
supports optional `[runtime] native_span = 1..256`. The consumer checks its
versioned manifest capability and validates final native-dispatch accounting
against actual retired work. Omission preserves legacy single-step execution;
this experimental option has not established a general speedup. See
[boundary and benchmark contracts](NATIVE_SPANS.md). Complete machine
[developer checkpoint/resume](DEVELOPER_CHECKPOINTS.md) is available for exact
builds and fresh paused execution windows, without an ABI change.

For a desktop build, add `--desktop` and provide the SDL3 package path if it
is not already discoverable. On Windows the linked PE import closure is resolved
and non-system runtime DLLs are copied beside the executable and included in
`output_files` hashes. This includes selected shared SDL and compiler runtimes;
unresolved imports and conflicting basenames stop the build. The tested LLVM/MinGW
consumer starts with SDK/compiler directories absent from `PATH`; a changed
packaged DLL is refused by the execution receipt guard. Imported target scope,
single/multi-configuration mappings and static SDL selection are handled
without exporting third-party targets globally. CMake 3.20 remains the minimum.
That packaging correction retained ABI 13 and descriptor schema 1. The current
compatibility upgrade requires ABI 27, regenerated modules, updated revision/source
pins and a new build receipt. Keep previous immutable qualification receipts.

The dependency scanner runs through CMake's script-mode
[`file(GET_RUNTIME_DEPENDENCIES)`](https://cmake.org/cmake/help/v3.20/command/file.html#get-runtime-dependencies)
using the configured PE inspection tool, selected compiler/link directories and
selected SDL. It excludes API contracts and resolved Windows-root files, copies
only linked imports and checks destinations before copying. This does not
package optional dynamically loaded modules such as an explicitly supplied
libchdr, certify every MSVC redistributable setup, or collect licenses for the
producer. In particular, MSVC CRTs installed in System32 are excluded under the
system-directory policy; qualify the actual distribution environment separately.

### Verify a Windows desktop package

Build-time SDK discovery and runtime DLL discovery are separate checks. A
successful link does not prove the resulting consumer can start independently
of the SDK. Qualify a fresh desktop build as follows:

1. Pin an immutable toolkit revision and exact source digest, verify the
   descriptor, and build into a new directory. Check that `output_files`
   includes both the executable and its selected shared `SDL3.dll`.
   Freeze the consumer's toolchain pin before starting the test, including
   when selecting an explicit revision override. Keep revision, source digest
   and ABI values stable through both verification calls: changing the
   manifest mid-run can change the verifier's identity record even when the
   selected toolkit source has not changed.
2. Start the consumer from an empty working directory with a child-only
   `PATH` containing neither SDK runtime directories nor the packaged `bin`
   directory. Keep system paths needed by Windows; do not change the owner's
   environment. Record the exact child `PATH` and any removed SDL driver
   overrides.
3. Inspect the running process's loaded `SDL3.dll` path and hash. They must
   identify the adjacent DLL bound by the build receipt. An executable hash,
   clean `PATH`, or successful TCP connection alone does not prove that DLL
   was selected. Recheck the packaged files after execution.
4. Through TCP, check status, controller input, guest and presentation
   captures, pause/resume and clean quit. Use a paced audio-enabled run to
   check device-open state, accepted/drained PCM, bounded queue depth and
   pause-flush drops. Keep unthrottled, speaker-muted route replay separate
   from playback evidence. TCP status can precede the main-thread audio
   drain: generated-minus-submitted frames may still be pending in the
   8,192-frame source queue. Check that bound and zero runtime discard
   separately from the SDL queue; require zero pending source frames at
   settled and final drain boundaries.
5. Retain exact commands, process exit status, loaded-module evidence,
   unchanged input hashes and owned-child cleanup with the consumer's
   private qualification receipts.

The official `project run` command performs its own receipt checks and requires
an explicit `limits.wall_seconds` from 1 through 86,400 seconds. Longer routes
can select a larger finite value in the descriptor; the command forwards it to
the host and retains an outer watchdog ten seconds longer. Direct TCP-supervised
execution remains a separate scope: retain official `project verify` and
`project build` bindings and report its actual command and watchdog. Neither
method establishes listening, analog output parity or complete-game compatibility.
See [finite host sessions](SESSION_LIMITS.md).

## Descriptor

All keys shown below are required, except the explicitly marked audio options. Unknown top-level or contract-table keys,
invalid types, unsupported versions, missing files and hash mismatches stop
before execution. SHA256 values are lowercase, complete 64-character digests.
`tool.revision` is a complete lowercase Git commit, not a branch or tag.
`MODULE_SOURCE_SHA256`, `MANIFEST_SHA256` and other uppercase strings below
are placeholders to replace, not accepted values.

```toml
schema = 1
name = "my-consumer"

[tool]
path = "../pcenginerecomp"
revision = "COMPLETE_40_CHARACTER_COMMIT"
source_sha256 = "TOOL_SOURCE_SHA256"
runtime_abi = 28

[module.source]
path = "private/generated/module.cpp"
sha256 = "MODULE_SOURCE_SHA256"

[module.manifest]
path = "private/generated/module.json"
sha256 = "MANIFEST_SHA256"

[payload]
path = "private/program.bin"
sha256 = "PAYLOAD_SHA256"
physical_load = 1048576
pc = 16384
mpr = [255,248,128,129,130,131,132,0]

[runtime]
tier = "hybrid"
video = "continuous"
cd_unknown_status = "fault"
# Optional CD profile; omit to keep fixed deadlines. HuCard refuses gear-distance.
cd_timing = "fixed"
joypad = 2
region = "usa"
multitap = "off"
# Optional; omit to retain the selected runner's audio default.
audio = "off"

[limits]
steps = 2000000
ticks = 100000000
wall_seconds = 60
```

An optional asset table is exactly `path` plus `sha256`. Supported table names
are `bios`, `bram`, `toc`, `disc`, `libchdr` and `input_script`. BIOS must be
262,144 raw bytes; initial BRAM must be 2,048 raw bytes. `libchdr` requires a
disc. Media geometry, TOC semantics and input-script contents retain the
runtime's validation; descriptor verification establishes their input identity.
For a supported BIN/CUE `[disc]`, `sha256` is the complete-image digest of the
exact CUE and all declared binary files. Verification discovers those files
and binds each `disc_component:<relative-name>` independently in build/run
receipts. It preserves the declared CUE directory when resolving relative
`FILE` names, including permitted links. ISO/CHD hashes remain whole-file
digests. No unverified component override is accepted. See
[the supported subset and digest encoding](MEDIA.md).

```toml
[bram]
path = "private/initial-bram.bin"
sha256 = "BRAM_SHA256"
```

There is one initial contiguous payload, which must fit the existing standard
CD/work RAM loader. PC is logical 16-bit; all eight MPR bytes are required.
The module source and manifest are pinned independently. Manifest schema 1,
runtime ABI 28 and a positive emitted native-site count are required; optional
emitter provenance fields are retained in the hash-pinned manifest. Initial
payload identity does not identify every later overlay. Generated dispatch
continues to guard logical PC, complete MPR mapping and exact fetched bytes.
The descriptor does not bypass those checks or claim a later overlay is known.

New observed-module manifests contain `translation_units` and
`generated_headers`, each an array of `{ "file": "basename", "sha256": "..." }`.
Retain the complete generated directory. Verification pins every listed file
in the build and execution receipts, including a single-unit module. Both
arrays must be present if either is supplied. Names must be portable direct
children of the manifest directory; duplicates, symlinks, missing entries and
stale hashes are refused. Manifests are bounded to 64 MiB. Older manifests
without either array retain the single-source contract. Descriptor schema
remains 1. ABI 27 requires newly generated modules and a matching runtime;
pin the new tool revision and exact source digest when upgrading. ABI-12 through ABI-26
observation captures remain accepted for regeneration; compiled ABI-12 through ABI-26
modules/objects are not compatible with ABI 27.

Supported runtime values are `native|hybrid`, `snapshot|continuous`,
`fault|gear-good|nec-invalid`, `2|6` buttons, `usa|japan` and `off|on` multitap.
`gear-good` is an explicit unknown-command *response* profile; it does not
implement the unknown command's operation. Native tier refuses uncovered
execution rather than silently using the interpreter. Hybrid coverage is
reported from actual native/interpreted retirements.
`nec-invalid` receives the complete NEC-framed invalid command before CHECK
CONDITION and sense `$05/$20`. Default `fault` remains explicit; known command
semantics that are unsupported still fault under every profile. See
[unknown-command profiles](CD_UNKNOWN.md) for raw wire/reset differences.
The optional `[runtime] audio` key accepts `on|off` and passes the explicit
runner setting. If omitted, desktop attempts SDL playback while headless keeps
PCM disabled unless WAV capture is explicitly requested. Audio production,
device-open success and physical/audible correctness are separate results.
The descriptor's `qualified` result does not establish audio parity. See
[AUDIO_OUTPUT.md](AUDIO_OUTPUT.md) for the digital profile and capture bounds.
Optional `audio_profile = "raw"|"filtered"` and integer `audio_rate = 44100|48000`
require explicit `audio = "on"`. They default to raw 44.1 kHz; raw at 48 kHz is
refused. Optional `audio_timing = "gear"|"legacy"` also requires explicit audio
on. The default is `gear`, with corrected sample-edge and PSG held-DAC timing.
Select `legacy` explicitly to compare against prior PCM baselines. For example:

```toml
audio = "on"
audio_profile = "filtered"
audio_rate = 48000
audio_timing = "gear"
```

The filtered profile adds a versioned `audio_output.processing` object and
reports PCM/WAV hashes in the processed output domain. Raw source counters and
the separately recorded raw mixed hash remain in the original 44.1 kHz domain.
Keep those contracts separate when validating an upgrade. Gear timing adds
`audio_output.timing = "gear-v1"`; legacy timing retains the prior PCM report
shape. Timing can legitimately change PCM and raw-source activity/hash fields;
compare against a fresh reference with the same timing rather than demanding
an old PCM hash. Descriptor schema remains 1. Current ABI 28 requires re-emitting
compatible captures and rebuilding modules and runtime together. Exact DSP
history is retained by the opt-in [developer checkpoint format](DEVELOPER_CHECKPOINTS.md);
it does not provide migration between these audio/runtime epochs.

Limits are 1..20,000,000,000 dispatcher steps, 1..(2^64 - 1) master ticks and
1..86,400 wall seconds. A block-transfer instruction can consume many guest
cycles; steps are not a replacement for the tick/wall bounds.

## Upgrade a consumer to ABI 28

Pin the reviewed toolkit revision and source digest, set `runtime_abi = 28`,
re-emit original-labelled captures and rebuild all generated modules and hosts.
ABI28 serializes the selected CD timing profile; existing `fixed` deadlines
remain the default. Optional `runtime.cd_timing = "gear-distance"` changes
READ/CDDA timing and needs its own qualification. See [CD timing](CD_TIMING.md).
Preserve the previously qualified package until the new candidate passes its
own source, native execution, device and audio checks. Create checkpoints
through that candidate's own startup; cross-build, cross-ABI and cross-profile
imports remain refused. A no-module interpreted startup test does not qualify
a native consumer migration. Original capture ABI labels and profile-v1
provenance remain intact.

## Upgrade a consumer to ABI 27

This earlier migration applies to consumers pinned to the ABI27 toolkit.

Pin the reviewed toolkit revision and source digest, set `runtime_abi = 27`,
re-emit the original labelled captures and rebuild every generated module and
host. ABI27 adds a typed CD unknown-response policy and checked invalid-command
counter to the machine state. The default remains strict; `nec-invalid` is an
explicit recipe change. Retain the old selected build and qualification until
the new recipe passes its own source, native-tier, device and audio checks.
Use candidate-owned fresh checkpoints; schema 1 does not permit cross-build,
module, ABI or response-profile imports. A short diagnostic suffix does not
qualify the old full route under a new profile. See
[migration qualification](NATIVE_MIGRATIONS.md) and [CD profiles](CD_UNKNOWN.md).

## Historical upgrade to ABI 26

Pin the reviewed toolkit revision and source digest, set `runtime_abi = 26`,
re-emit retained observations with their original ABI labels, then rebuild
the complete module and runtime. ABI 12–25 captures remain offline compiler
inputs; old binaries, native objects and checkpoints are incompatible.
Editing an assertion or manifest number alone does not update generated
guest operations. Capture, descriptor and checkpoint payload schemas remain 1.

ABI 26 changes PSG guest-write timing, including memory RMW and all five
block transfers. Device clocks and IRQ sampling precede the PSG write, while
delivery retains the normal retirement boundary. CDDA also finishes the
active sector after D9 shortens its end. Qualify fresh source-hit, guest-state
and audio evidence, and retain the old qualified package and receipts.
See [audio bus timing](AUDIO_BUS_TIMING.md). Exact-build developer checkpoints
must be created by the new package; no cross-build migration is provided.

## Historical upgrade to ABI 25

Pin the exact reviewed toolkit revision and source digest, set
`runtime_abi = 25`, re-emit retained observations with their original ABI labels,
and rebuild module plus runtime. Capture/consumer schemas remain 1. Retained VDC bus and fetched rendering
state make older binary objects incompatible even when instruction bodies
are unchanged. Retain the old qualified package and receipts until the new
build passes its finite guest-state, native-tier, source and audio checks.

ABI 25 adds guest scroll-write latch history and a pure sector-provider
program-range interface. Rebuild custom providers and generated modules with
the runtime; older binary layouts are incompatible. Re-emit a retained capture
with its original ABI label, then obtain fresh execution evidence. In
particular, a historical capture does not establish the new video/CD behavior.
The descriptor, capture and TCP schemas remain unchanged. See
[live scroll writes](VDC_SCROLL.md) and [CD position](CD_POSITION.md).

ABI 24 previously changed emitted ST0/ST1/ST2 bodies to the timed CPU-aware VDC API.
Re-emit the observations; changing old ABI assertions alone is insufficient.

Clocked VDC access defaults to queued transfers with dynamic wait ticks.
Set optional `[runtime].vdc_access = "queued"` or `"immediate"` to pin the
profile explicitly. Both hosts report `vdc_access` in status and final output;
explicit consumer selections validate that report. Unknown fields remain
errors in strict wrappers, so admit the six documented diagnostic fields
without dropping unrelated state. Queued timing can change work counts,
images and PCM at a fixed frame: qualify a new same-profile reference instead
of assuming old immediate hashes. The explicit immediate profile preserves
the prior timing path. See [VDC_ACCESS.md](VDC_ACCESS.md).

The VRAM bus capability requires no new descriptor field. CPU/DMA/rendering
reads share held VRAM data; inspection stays pure. See [VRAM_BUS.md](VRAM_BUS.md).
The existing CD sense/recovery capability also requires no new descriptor field. Known
REQUEST SENSE is implemented independently of `fault|gear-good|nec-invalid` unknown-command
policy. Runs that request sense or diagnose an error add the bounded `cd_sense`
diagnostic object; healthy routes without such activity retain their metadata
shape. Validate that object explicitly when qualifying an error-recovery route;
do not discard unexpected device fields or loosen ordinary source/state checks.
See [CD_SENSE.md](CD_SENSE.md).

Existing System Card and snapshot recipes remain supported. For a base
HuCard, use strict `[boot]` fields `mode = "hucard-reset"`, `profile = "base"`,
`header = "none"|"copier512"`, `encoding = "linear"|"bit-reversed"` and a pinned
`[cartridge]` raw-file table. It conflicts with payload/BIOS/CD/BRAM inputs.
The consumer independently validates initial metadata against the decoded
vector, ROM size and explicit no-CD profile. See [HUCARD.md](HUCARD.md).
The same strict recipe accepts `profile = "sf2"` and `"populous"` with their
exact ROM sizes. Initial SF2 metadata includes `mapper_latch = 0`; Populous
includes `cartridge_ram_bytes = 32768`. Base/System Card metadata is unchanged.

An optional `[boot].arcade_card = "duo"` is admitted only with
`mode = "system-card-reset"`, `profile = "super"`. It forwards the explicit
host flag and requires initial `arcade_card: "duo"` metadata. Omission retains
the existing profile; HuCard, standard and payload recipes reject attachment.
See [the expansion contract](ARCADE_CARD.md).

An ABI update alone adds no native coverage. Neither startup nor code capture
is a persisted save-state format; this upgrade adds no owner-save migration.

## Upgrade a consumer to ABI 17

This retained procedure describes the earlier System Card integration. Use
the ABI-27 procedure above for current builds.

Pin the new exact revision/source digest, set `runtime_abi = 17`, re-emit
retained ABI-12/13/14/15/16 captures with their original labels, and rebuild
modules plus runtime. Consumer/capture schemas remain 1. Retain prior receipts;
the new Bus layout is not compatible with older binary objects. An ABI upgrade
alone adds no native coverage or campaign evidence.

Existing `[payload]` recipes keep their snapshot/IPL behavior. To execute a
System Card from reset, replace `[payload]` with strict `[boot]` fields
`mode = "system-card-reset"` and `profile = "standard"` or `"super"`, and
require the normal hashed `[bios]` input. Both startup tables together, neither
table, inferred hardware, and arbitrary PC/MPR overrides are rejected.

The command generator emits a distinct no-payload grammar; optional media,
BRAM, input, audio and TCP controls remain bound normally. Reset metadata
reports the initial state without relabeling later execution as native.
Standard headless and Super desktop authored official runs each retire
200 native / zero interpreted instructions and capture the three expected
source identities. See [the reset example](../examples/reset-consumer/README.md)
and [startup contract](SYSTEM_CARD_BOOT.md).

The separate Ys III project can keep a qualified ABI-16 dependency while
testing a new route; reset startup is an explicit migration and new entry
recipe, not a reason to modify an already qualified consumer mid-run.

## Upgrade a consumer to ABI 16

This retained procedure describes the earlier ABI-16 integration. Use the
ABI-27 procedure above for current builds.

Pin the new exact tool revision and source digest, set `runtime_abi = 16`,
re-emit retained ABI-12/13/14/15 observations with their original ABI labels,
and rebuild all generated translation units and the runtime. Descriptor and
capture schemas remain 1. The current capture table records BRK's ignored
signature as a second encoding byte; older runtimes could not retire BRK.
No capture-window fields change.

Preserve the previous qualified project and receipts. Recheck every MPR,
source identity, guard, exclusion and generated source hash; ABI migration
alone adds no native coverage. The normal runners now map F8 through FB as
aliases of the same 8 KiB. Guest/device code using formerly missing sprite
IRQs may legitimately change execution. Full generation reports can also show
new F9/FA/FB updates after WRAM writes. Diagnose such differences against the
[explicit compatibility contract](COMPATIBILITY.md), rather than deleting
fields or forcing old hashes to pass.

TCP and final JSON add the bounded `cd_unknown` diagnostic object described in
that contract. It is additive evidence, not a new CD response policy. Keep
strict faults, known unsupported commands, inherited assists and actual
native/interpreted work visible. Check presentation-on/off guest behavior and
retain the selected audio profile/rate/timing. This batch introduces no state
restore or host-save migration.

The authored consumer checks exercise three fresh official verify/build/run
sequences, including actual two-byte BRK capture, regeneration and another
native execution. The separate retail consumer retains all 209 generated
files' operations and guards while rebuilding for ABI 16. Its legacy, default
Gear and audio-off routes are regression evidence, not new native coverage.
See [the actual migration results and limits](STATUS.md#abi-16-consumer-integration).

## Upgrade a consumer to ABI 15

This retained procedure documents the earlier ABI-15 audio/latch integration.
Use the ABI-27 procedure above for the current runtime.


Preserve the previous source pin, generated module, build/run receipts and
qualified route before changing a consumer. Keep those artifacts immutable;
new qualification belongs in a new private directory. Reuse original media
read-only and keep guest BRAM volatile. This upgrade introduces no save-state
migration format.

Pin a clean toolkit checkout by complete revision and source digest, then set
the descriptor's `tool.runtime_abi` to **15**. Retained observation captures
from ABI 12, 13 or 14 remain offline compiler inputs: preserve their original
bytes and recorded ABI. Do not change a capture's ABI label to make it look
new. Regenerate from that capture with the new emitter:

```sh
python -m pcerecomp emit-capture PRIVATE_CAPTURE --out NEW_PRIVATE_MODULE
```

Repeat the original `--exclude-range ADDRESS:LENGTH` options and partition
settings where applicable. Retain every generated translation unit and header,
update descriptor module/manifest hashes, and build in a fresh directory.
Old compiled objects cannot be reused. Compare the new manifest's input
identity, mappings, exclusions and site counts with the retained generation.
An ABI-only regeneration should conserve translated operations and guards;
it does not establish new native coverage or require an artificial native gain.

Audio timing needs an explicit migration decision. ABI 13's former output
path corresponds to `audio_timing = "legacy"`; the ABI-15 default is `gear`.
To verify preservation of a prior filtered 48 kHz baseline, use:

```toml
[runtime]
audio = "on"
audio_profile = "filtered"
audio_rate = 48000
audio_timing = "legacy"
```

Then qualify `audio_timing = "gear"` separately. Keep the same route, inputs,
module, controls and assistance journal. Guest state, source identities and
native/interpreted work should remain conserved across the timing change;
PCM hashes and source-activity fields can legitimately differ. Gear output
must report `audio_output.timing = "gear-v1"`; legacy output omits that field.
For a fresh zero-phase Gear run at guest tick `t`, source frames equal
`floor(t*44100/21477273)`; filtered 48 kHz output frames equal
`floor(source_frames*160/147)`. Check these relationships at checkpoints,
alongside the full raw-source and processed-output diagnostics.

A useful migration matrix compares explicit legacy PCM against the retained
baseline, new Gear PCM across fresh headless and desktop hosts, and audio-off
guest/native behavior against the enabled runs. Keep each timing/profile/rate
combination distinct. Compare complete image hashes, checkpoint/end states,
source identities and execution counters; compare PCM/WAV only within the
appropriate audio contract. Host-only telemetry needs separate checks. A WAV
bounded to the opening cannot establish later gameplay audio equality;
whole-stream and checkpoint PCM hashes provide that additional evidence.
Cross-host agreement is runtime regression evidence, not an independent
emulator or hardware oracle.

If the retained baseline recorded a bounded code-capture window and the new
run does not, first validate the original capture, its actual start boundary
and retirement totals. Then compare through an explicit projection of that
known observation-only metadata. Keep guest/source diagnostics and execution
totals intact; a broad removal of capture-related fields can hide a mismatch.
ABI regeneration itself does not require another retail capture.

Consumer wrappers must forward and validate timing rather than relying on
defaults. Reject conflicting descriptor/CLI selections and duplicate timing
flags. Timing/profile/rate options require explicitly enabled audio. Preserve
historical qualifiers with their original assumptions; an ABI upgrade needs
conservation checks rather than weakening a previous native-gain requirement.

Use official `project verify` and `project build` bindings for each descriptor.
A short official `project run` smoke and a longer TCP-supervised route prove
different scopes; explicitly select a finite wall limit and disclose any
supervisor's separate watchdog. On Windows, qualify the packaged SDL DLL from
an empty working directory and sanitized PATH, then check TCP pause/resume and
input at paced execution. Device acceptance does not establish listening.

## Exact source identity and development overrides

```sh
python -m pcerecomp.project identity ../pcenginerecomp
```

This reports the current Git revision and a digest of exact source bytes.
The digest includes root `CMakeLists.txt` and `.py`, `.cpp`, `.hpp`, `.h` and
`.cmake` files below `pcerecomp/`, `runtime/` and `cmake/`, including untracked
files of those types. `__pycache__`, tests, documentation and external build
outputs are excluded. Paths are sorted by their relative POSIX names; each
digest input is UTF-8 path, NUL, decimal byte count, NUL, exact file bytes.
Line endings therefore matter.

Matching HEAD alone does not establish source identity. A relevant dirty edit
invalidates a previously pinned source digest. For reviewed development code,
the consumer may deliberately pin the exact current digest. If the expected
commit differs, `--allow-revision-override` is additionally required on every
verify/build/run command. The override is recorded and **never relaxes the
source digest or ABI check**. Without Git metadata an exact digest can still
be checked, but revision verification requires that explicit override.
An enclosing parent repository's revision is not used as an export's identity.

A source change between build and execution invalidates the build receipt.
Changes while configuring/building are checked again before creating that
receipt. Source changes during execution mark the execution unqualified.
These are integrity checks on a cooperative local workspace, not an atomic
snapshot of concurrently edited files or a signed supply-chain attestation.
For publication use an isolated, immutable pinned checkout/export.

## CMake embedding

For a consumer that already manages its own CMake build:

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyConsumer LANGUAGES CXX)
set(PCE_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_REFERENCE_PROBE OFF CACHE BOOL "" FORCE)
add_subdirectory("../pcenginerecomp" "tool")
pce_add_consumer(my-port MODULE "private/generated/module.cpp"
  MANIFEST "private/generated/module.json")
```

`pce_add_consumer(target MODULE source [MANIFEST manifest] [DESKTOP])` compiles
the selected generated module and links the shared host/runtime.
Without an explicit manifest it discovers a sibling `module.json` when present.
New manifests select and verify every translation unit/header; the entry
source alone is insufficient for a partitioned module. Repeated consumers of
the same canonical module/manifest share one object library in that CMake
build tree. Standalone headless and desktop hosts also share this compilation.
For a custom host, `pce_add_native_module(objects MODULE source [MANIFEST manifest])`
returns the object-library target to link. There is no persistent compiler cache.
It does not copy either. `DESKTOP` requires `PCE_BUILD_DESKTOP=ON` and an
installed/discovered SDL3 package; Windows shared SDL is copied beside the
consumer executable. A direct CMake invocation is an embedding API, **not** a
replacement for descriptor verification or execution receipts. The Python
build command generates a minimal wrapper that performs both in order.
Embedded toolkit tests default off through `PCE_BUILD_TESTS`, independently of
the parent's `BUILD_TESTING`. A consumer can keep its own tests enabled without
building the toolkit's standalone runners or test suite.

The build receipt binds descriptor/tool/module/input identities to the exact
executable SHA256 and every regular file beside it (including a copied SDL
DLL). Before run, these hashes and the original descriptor are rechecked.
This does not hash the complete system dynamic linker/compiler installation.

## TCP automation and execution receipts

```sh
python -m pcerecomp.project run path/to/project.toml --build-dir path/to/build --receipt path/to/new-run.json --dev-port 0 --start-paused
```

TCP needs continuous video. Port 0 requests an ephemeral loopback port;
`PCE_DEV_PORT=...` is printed immediately on inherited stderr. Connect using
[`scripts/dev_client.py`](../scripts/dev_client.py): status, five input slots,
pause, frame-step, RGB capture and clean quit use the existing
[development-server contract](DEV_SERVER.md). Screenshot files, input actions
and TCP assertion results belong in the consumer's additional evidence.
`--memory-write` explicitly enables guarded paused RAM edits; it is off by
default and never bypasses compare-before-write/range/source invalidation.
Receipts retain the host's debug-write counters, so assisted tests stay visible.

Add `--checkpoint-dir path/to/EXISTING-private-directory` to opt into developer
checkpoints. This requires `--dev-port` and `--start-paused`. The runner derives
the reviewed context from the verified tool revision/source, complete module
and asset identities, boot/load recipe and runtime profiles; the host separately
checks actual binaries and input files. Use paused TCP `save_checkpoint` with a
new `.pcec` basename. A fresh run of the exact build may add
`--checkpoint-load frontier.pcec`, or load through TCP before first execution.
Output paths and finite limits may change; step/tick allowances then describe
the new window. Persistent BRAM sessions cannot publish checkpoint-loaded state.

On resume, receipts require `checkpoint_validation.valid`; `work` counts only
the new suffix and identifies its imported origin. Lifetime counters remain in
the full result. File/live captures include `checkpoint_origin`, and generated
module provenance preserves it without claiming imported work or full-reset
execution. Boot metadata identifies the checked startup recipe, while the
resumed scope explicitly denotes continuation. These are private diagnostic
artifacts with no cross-build, cross-module or portable-save compatibility.

Run arguments are passed as an argument vector with `shell=False`. Every run
has descriptor step/tick/wall bounds plus a host-process timeout. The receipt
uses a new path and records exact command, binary/input/tool identities,
exit code, elapsed time, timeout, unchanged-input checks, actual native and
interpreted retirements/fraction, and the complete final host diagnostic JSON.
A failed or timed-out run is not marked qualified. Input BRAM changes remain
volatile; the original BRAM image is checked unchanged after execution.
Native-site counts alone never count as executed native work.

Reset recipes additionally require `boot_validation.valid = true`. The receipt
checks the reported initial boot state against the selected hardware profile,
the reset vector in the hash-pinned BIOS, the named deterministic initialization
and the explicit/blank BRAM policy. Initial state is distinct from the final CPU
state. Missing, mistyped or inconsistent metadata prevents qualification; the
complete host result and validation error remain recorded. Snapshot recipes
retain their previous receipt fields without an implied reset validation.

Add `--code-capture path/to/NEW-private-capture.json --capture-limit 16384` to
record bounded observed instruction identities for the next offline emission.
The parent directory must already exist; capacity is 1..65,536. The execution
receipt validates capture schema, identity mappings, the current runtime ABI,
the requested capacity and actual retirement totals. For a complete capture,
native and interpreted hits must each match the host's execution counts.
Then it records the hash, byte size, observation count and completeness/drop
counters. A malformed/missing capture cannot qualify; a valid incomplete
capture explicitly retains its drop and unreadable counts. Retained hits may
not exceed either actual execution tier; missing retirements must equal the
recorded loss and remain `unclassified_retirements`, without an invented tier.
Fresh host output must use ABI 27; accepting older offline observations does
not qualify a stale fresh capture. This is an observation set, not
proof all reachable code was discovered. Keep capture bytes private and use
the toolkit's `emit-capture` command to produce another guarded native module.
The [authored reset capture example](../examples/reset-consumer/README.md#capture-mappings-that-a-fixed-cfg-cannot-discover)
demonstrates promotion across actual MPR changes and ROM mirrors with a
native-only replay. A real firmware project needs its own private capture and
execution evidence; the authored result does not supply retail coverage.

The receipt's `qualified` flag means the checked host exited successfully,
reported valid work counters and retained its pinned identities. It does not
mean hardware accuracy, independent Geargrafx agreement, full campaign,
authentic reset, audible correctness or persistent save compatibility. Keep independent
reference evidence separate and describe its actual scope. Private retail
payloads, generated game source, captures and receipts must stay outside public
commits; only authored fixtures belong in public tests/examples.
