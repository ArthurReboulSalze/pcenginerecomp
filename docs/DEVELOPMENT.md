# Developer guide

## Layout

```text
pcerecomp/       Python media, decoder, CFG and C++ emitter
cmake/          Shared-runtime consumer embedding helper
examples/       Authored consumer example without retail inputs
runtime/        C++20 state, bus, partial interpreter, headless and optional SDL3 host
tests/          Authored synthetic fixtures and native comparison harness
scripts/        Dependency bootstrap, test runner and publication audit
docs/           Architecture, sources, roadmap and current status
.local/         Ignored private images-derived snapshots/reports/modules
.deps/          Ignored optional dependency source/build
.research/      Ignored downloaded reference material
build/          Ignored CMake outputs, including synthetic generated module
```

## Reproducible baseline

Python 3.11+, CMake 3.20+, C++20, and Ninja for the commands below. There are
no third-party Python runtime requirements. A source checkout can be used
without `pip install`. An optional install provides the `pcerecomp` command.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
python scripts/check.py
```

For a Clang build append `-DCMAKE_CXX_COMPILER=clang++` on configure. For an
MSVC build use an initialized developer shell or the appropriate Visual
Studio generator. With a multi-configuration generator build with
`--config Release` and use `ctest --test-dir build -C Release`.
The convenience test runner expects binaries directly under `--build`;
use CTest for multi-configuration generators.

CTest registers 43 default suites, including mixed-speed traces, static mapping contexts, System Card reset, enhanced
HuCard mappers, Arcade Card Duo, timer phase, live capture, BRK, work-RAM
mirrors and sprite events. The baseline includes frontend, CPU runtime,
native source guards, CD control, VDC ports,
raster, CD transport, joypad, READ, provider, block transfers, IRQ/RTI,
palette/snapshot, DMA, PSG, ADPCM, CDDA, input scripts, continuous video,
digital audio output, PSG PCM, ADPCM PCM, CDDA PCM/stream ordering and
the development TCP server. Enabling the desktop adds separate SDL
renderer/input and audio-host suites, making 45 (44 C++ suites plus Python discovery).
`scripts/check.py` runs the same suites directly for toolchains without `ctest`.
Its complete Python suite has a finite 600-second default wall deadline;
`--python-timeout 1..86400` selects a different positive integer deadline for
slower machines or instrumented runs. Each individual C++ suite retains its
60-second deadline. A timeout fails the check; it does not skip unfinished
tests or qualify partial output. This runner limit is separate from guest-host
`--wall-seconds` and does not change the test selection.
The retained ABI-12 dispatch-batch expanded-module run passes all 21 enabled suites and 231 Python
tests, including 18 development-client checks. The desktop suite passes 122
assertions; the actual-socket TCP suite passes 119. Public-source-only build
qualification is recorded separately in [STATUS.md](STATUS.md).
That batch's clean public-source checkout also passes all 20 default suites (231 Python
tests discovered, four desktop-only skips) and 21 SDL suites (all 231 tests).
Both use empty module selection and authored fixtures without retail input.
Embedded consumers use the separate `PCE_BUILD_TOOLS` and `PCE_BUILD_TESTS`
options, both off by default when added as a subdirectory. Parent
`BUILD_TESTING` settings remain independent. See [CONSUMER.md](CONSUMER.md)
for hash-pinned projects and the authored build/run example, and
[CODE_CAPTURE.md](CODE_CAPTURE.md) for private observed-code promotion.
For opt-in static recovery across proven mapping changes, see
[STATIC_ANALYSIS.md](STATIC_ANALYSIS.md). It emits directly from source
analysis, separately from observed-code promotion. The authored
`pce-context-tests` fixture checks both CPU speeds, executing/data-page TAM,
full-context source reuse, exact literal state and pure guards. The separate
reference adapter compiles original Geargrafx in its own process:

```text
python scripts/context_reference.py --native --gear-source PATH_TO_PINNED_GEAR --tool-source PATH_TO_FROZEN_TOOL --out .local/context-reference --library PATH_TO_LIBCHDR_STATIC --library PATH_TO_LZMA --library PATH_TO_MINIZ --library PATH_TO_ZSTD
```

This finite reference check covers 80 instruction records and 1,600 literal
CPU/mapping/RAM/time checks in each of Gear, interpreter and native execution.
The native module executes all 80 instructions without fallback, with 26 source
identities across six mappings. Its 326 deadline/full-MPR/every-byte guard
negatives preserve observed state. It does not qualify already-pending IRQs,
physical bus phases or general executable-RAM mutation analysis.

The [instruction trace interface](REFERENCE_TRACES.md) adds strict JSONL
validation and a reusable first-difference comparator. Optional
`scripts/beetle_reference.py` builds an original independent PCE core and
uses its instruction-step API. `scripts/speed_trace_reference.py` builds the
separate original-Gear and genuinely translated native/interpreter fixture.
Reference disagreements stay explicit; a named comparison profile describes
the checked state instead of silently dropping fields. Baseline
`pce-speed-trace-tests` needs only authored source and the normal toolchain.

Large observed modules use independent translation units and a shared object
library for both hosts. `PCE_MODULE_MANIFEST` optionally selects the manifest;
otherwise CMake discovers `module.json` beside `PCE_MODULE_SOURCE`. Keep all
manifest-listed sources and headers together. The emitted source/header hashes
are checked at configuration; changed artifacts trigger reconfiguration.
See [PERFORMANCE.md](PERFORMANCE.md) for the authored dispatcher benchmark,
separate compile measurements and comparison controls. Inline source peeks
preserve exact byte identity. Current runtime requires ABI 27; regenerate
modules and rebuild runtime together rather than reusing earlier ABI objects.
ABI-12 through ABI-25 observation captures remain accepted for offline regeneration.
The retained ABI-13 builds passed all 27 expanded/SDL suites and all 254 Python tests.
That retained clean public-source default build passed all 25 suites, with 254 Python
tests discovered and seven desktop-only skips. Authored consumer and full-route
audio/guest-state qualifications are recorded in [STATUS.md](STATUS.md).
The C++ suite checks generated instructions against the interpreter and also
checks 92,160 independently expected bit/stack cases, 7,340,032 arithmetic/
logic cases, 340 addressing cases, 3,932,160 RMW cases, 16,384 indirect
JMP cases, 4,849,664 bit-test cases, 2,228,224 bit-branch/BSR cases and
1,114,112 MPR/latch cases and 524,288 speed cases,
plus source guards, mapping aliases and explicit faults. Synthetic host tests
exercise optional firmware mapping, call/return and rejection/protection rules.
See [CPU_SEMANTICS.md](CPU_SEMANTICS.md)
for the status and cycle contracts and [REFERENCE.md](REFERENCE.md) for the
optional independently developed emulator comparison.
The separate `pce-io-tests` module adds 67,584 expected CD-control/BRAM
instruction cases, 2,048 readback sequences and 16,144 register-decoding groups,
and doubles as the CD reference probe. Its entirely
authored fixture uses MPR aliases for hardware and BRAM and tests locked/
upper-hole writes, RMW side effects, deadlines, guards and unsupported reads.

The separate `pce-vdc-tests` module checks 77,824 expected CPU cases, 8,192
register-width cases and 392,991 VRAM transfer/address cases. It covers the
opt-in single-VDC profile and serves as its independent-reference probe. See [VDC.md](VDC.md) for port,
register, VRAM and timing contracts and deliberately unsupported behavior.

The `pce-vdc-queue-tests` suite adds **49,279 authored expectations** for
request countdowns, partial clock carry, BUSY, live registers, arbitration,
DMA/SATB precedence, CPU wait accounting and pure inspection. Eight real
headless/SDL TCP cases cover ordinary and block data reads, MPR aliases,
explicit immediate and default queued profiles.

`scripts/vdc_queue_reference.py` compiles the original pinned Geargrafx core
as a separate process. Supply a Geargrafx checkout at the pinned commit and
explicit static dependencies using repeated `--library` arguments (libchdr,
its LZMA dependency, miniz and zstd for the recorded Windows build). `--native`
builds the selected toolkit source, captures authored execution, emits and
compiles a native module, and checks actual native hits and pure guards.
Use a new private output directory with `--out .local/queue-reference` and
`--tool-source` for an immutable reviewed checkout. No retail data is needed.
The final ABI24 qualification covers 615 cases / 2,556 records and 3,678
independent literal checks per tier. Twelve CPU cases match registers and
master timestamps across both CPU speeds and three VCE dot speeds, including
ST ports, mapped aliases, TIA/TAI, DMA overlap and both-pending waits. The
582 native retirements have zero fallback; 24 guard negatives remain pure.
The report records 99 specific MWR3 background bus differences instead of
claiming whole-renderer equality; all other compared fields remain exact.
See [VDC_ACCESS.md](VDC_ACCESS.md) for those boundaries.

The additional `scripts/vdc_irq_reference.py` probe checks real timer
underflow during a queued VRAM read blocked by a finite DMA. Its **54 cases /
2,484 records** cover both CPU speeds, three VCE dot speeds, remaining timer
phases **18/30/60 master ticks**, immediate delivery and CPU-I/IRQ-mask-deferred
delivery. The guest handler disables and acknowledges the timer and executes
RTI. All records, including CPU/vector/stack, timer/queue state and master
timestamps, compare exactly against original Geargrafx, with **no field
projections**. Each tier passes **972 independent literal checks**; the
translated run executes **1,188 native retirements with zero fallback**.
The **108 pure source/MPR guard negatives** run with an armed timer and
pending VRAM work before underflow, preserving all observed state. They do
not qualify guard behavior with an already asserted IRQ.

Run the authored probe from this checkout with the pinned Geargrafx source,
an immutable reviewed toolkit checkout and explicit existing static libraries:

```text
python scripts/vdc_irq_reference.py --native --gear-source PATH_TO_PINNED_GEAR --tool-source PATH_TO_FROZEN_TOOL --out .local/vdc-irq-reference --library PATH_TO_LIBCHDR_STATIC --library PATH_TO_LZMA --library PATH_TO_MINIZ --library PATH_TO_ZSTD
```

Replace the path arguments with the supplied checkout and library files. The
recorded Windows build uses libchdr, its LZMA dependency, miniz and zstd;
repeat `--library` for each required library. The output directory must be
new and private. Compiler, CMake and Ninja can be selected explicitly with
`--compiler`, `--cmake` and `--ninja`. `--native` captures authored interpreter
execution, emits and compiles a module, and requires actual native execution
with matching per-source hits. Omission produces an explicitly labeled
Gear-only observation run, not a toolkit comparison. No retail input is
required.

The original Gear callback independently records all 54 underflows at master
tick 3,120 while dynamic wait ticks and pending DMA are both nonzero. These
checks add qualification without changing runtime ABI **24** or canonical
compiler/runtime source. Other instruction phases, IRQ1/IRQ2 priority and
mixed-source delivery, electrical bus phases and physical hardware remain
unqualified. See [VDC_ACCESS.md](VDC_ACCESS.md).

The separate `pce-raster-tests` module checks 977 groups of literal event
boundaries, VBlank/RCR enable gating, acknowledgement, phase latches and
unsupported operations. These include 161 direct device groups and 816 bus
checks covering all eight VCE timing controls, MPR pages and port mirrors,
fixed waits, generation stability and unsupported/disabled ports. Its 240,015
cadence/alias/speed/refusal checks exercise native and interpreted NOP
retirement at both CPU speeds, multiple frame boundaries and
unchanged clocks on a deadline or source-guard miss. Its `--clock` mode is a
direct device probe for the independent reference, not native instruction
evidence. See [REFERENCE.md](REFERENCE.md) for reproducible Geargrafx checks.

The separate `pce-scsi-tests` module exercises the opt-in clocked CD transport
with authored work-RAM code: 8,369 control groups, including 4,096 latch/control byte
groups and 4,096 RMW groups, plus directed checks. It covers
selection and command-byte deadlines, TEST UNIT READY completion, status/message
acknowledgement, reset cancellation, held ACK, unsupported commands, IRQ2
refusal, native source guards and execution budgets. Its `--probe` mode supplies
settled transaction observations for the Geargrafx `--suite scsi` adapter;
it uses real generated/interpreted NOPs for bounded settling delays. No retail
firmware, sector backend or save file is required. See [CD_CONTROL.md](CD_CONTROL.md).
Its TOC extension separately checks 418 groups of literal directory responses, DATA IN,
manual/auto-ACK deadlines, reset/selection aborts and refusal boundaries.
`--probe-toc` supplies observations for the independent `--suite toc` adapter.
Frontend tests cover disc geometry, descriptor formatting and protected
inputs; headless tests exercise untrusted parser boundaries and exporter/parser
interoperability with entirely authored ISO data.

The separate `pce-joypad-tests` module uses authored port-access code and
independently expected controller nibbles, control edges, tap scans, output
latching, region/CD bits, mapping aliases and guard/deadline refusal. Headless
host tests separately cover CLI configuration and input immutability. See
[INPUT.md](INPUT.md) for the selected reference profile and option format;
[REFERENCE.md](REFERENCE.md) records the live Geargrafx scope.

The generated synthetic test module is always separate from the module
selected for `pce-headless`; a local title experiment cannot silently
substitute game bytes into public tests.
The host tests use the headless executable from the selected build directory
(`PCE_TEST_HEADLESS` under CTest or `scripts/check.py`). See
[FIRMWARE.md](FIRMWARE.md) for private ROM loading and current execution scope.
Runtime ABI **16** adds cached sprite evaluation, base work-RAM mirrors and
bounded CD diagnostics. ABI 15 added the guest CDDA cursor/latch; ABI 14 added
held PSG DAC state. ABI **13** added digital synthesis/ADPCM decoder and bounded stereo
output state. ABI 12 added continuous output ownership to the VDC, including
historical latches, the decoded line and bounded front/back RGB buffers.
ABI 11 added IRQ/timer, functional palette/DMA, PSG/ADPCM/CDDA state
and bounded scripted-input support. ABI 10 added completed block counters and block-aware access/clock
contracts; modules emit their own block loops. ABI 9 added the sector buffer, provider ownership and load scheduler.
ABI 8 added controller configuration, sampled buttons and joypad protocol
state; ABI 7 added TOC metadata, bounded DATA IN and auto-ACK state; ABI 6
introduced clocked CD transport, ABI 5 introduced the
video-clock execution contract, ABI 4 introduced VDC
state, ABI 3 introduced CD-control bus state and
ABI 2 introduced the MPR latch.
Regenerate older modules and rebuild consumers; the generated assertion rejects
mixing versions. The reference probe's optional MPR sequence mode counts native
execution and interpreter fallback separately after mapping changes.
The speed suite checks both entry divisors and CSL/CSH transitions through
bounded CPU traces. Its explicit result is `architectural_pass_timing_discrepancy`:
state/speed agrees with Geargrafx, while transition ticks follow Mesen/Beetle
and differ from Geargrafx 1.8.4. Do not summarize this as timing parity.
The CD-control suite separately verifies byte-level CPU/device state against
Geargrafx using authored CD media. It does not resolve those timing differences.

The separate `pce-scanline-tests` checks **3,950 independent expectations** for
historical palette/VRAM/SATB effects, scroll latching, burst and geometry
changes, stable publication, all eight timing controls, partitioning,
raster reset, bounds and unchanged guest state. Its optional live adapter
compares complete authored frames with Geargrafx; see
[VIDEO_OUTPUT.md](VIDEO_OUTPUT.md) and [REFERENCE.md](REFERENCE.md).

## Optional desktop host

The default configure keeps `PCE_BUILD_DESKTOP=OFF`, so public source tests
and `pce-headless` do not require SDL. To build the window, provide a matching
SDL3 development SDK and its CMake package directory:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DPCE_BUILD_DESKTOP=ON -DSDL3_DIR=/path/to/SDL3/lib/cmake/SDL3
cmake --build build --parallel 4
python scripts/check.py
```

CMake requires SDL 3.2 or later. The tested Windows x64 SDK is the official
SDL 3.4.18 MinGW development archive; use an SDK matching your compiler and
architecture rather than mixing MinGW and MSVC libraries. SDK files remain
outside public source, conventionally under ignored `.deps/`. CMake copies a
shared SDL DLL beside the desktop executable and test on Windows. Other
platforms use their configured shared-library search paths. SDK provenance,
controls and API references are in [DESKTOP.md](DESKTOP.md).

`pce-desktop` uses the same `PCE_MODULE_SOURCE` and payload/mapping/budget
arguments as the headless executable. With an empty module selection it is
interpreter-only; compiling a module does not prove the executed route used
it. Keep the JSON's native/interpreter counters with each result.

```sh
build/pce-desktop .local/title/boot/boot-0.bin 0x100000 0x4000 255,248,128,129,130,131,132,0 1000000 10000000 hybrid --window-scale 3 --wall-seconds 60
```

Use load/entry/MPR values from your own snapshot. This is an argument-format
example, not a complete firmware/disc recipe. Add separately supplied
`--bios`, `--disc`, `--toc` and `--libchdr` options when appropriate. Retail
game images, extracted payloads, firmware, output images and input recipes
stay private. This host never opens owner saves or an initialized install.

The desktop defaults to continuous video and refuses snapshot mode.
`--window-scale 1..6` selects its initial size; `--unthrottled on|off` controls
host waiting, and `--wall-seconds 1..86400` bounds a diagnostic run even while
paused. `--hidden on` is for automated host tests. Optional
`--window-capture NEW_PPM` captures the actual SDL renderer target, including
letterbox bars, through exclusive creation and a four-million-pixel cap.
`--frame-out NEW_PPM` instead captures the completed guest RGB picture.
Normal desktop use writes neither image. SDL dummy/software test evidence is
separate from visible-window inspection and physical-controller qualification.

## Digital audio and capture

The desktop attempts audio output by default. Headless keeps the audio-disabled
reference path unless `--audio-output on` or `--audio-out NEW_WAV` is supplied.
Append `--audio-output off` to an existing route when reproducing a prior silent
baseline. Device-open failure under the desktop's implicit default is reported
on stderr and in `audio_output.device_open`; explicit `on` makes it fatal.
Desktop `--unthrottled on` mutes device presentation while preserving normal
guest-clock PCM and WAV generation. `audio_output.fast_forward_muted` records
that state; intentionally muted submissions count as dropped device frames.

```text
--audio-out .local/new-audio.wav --audio-frames 44100
```

This captures at most one second of 44,100 Hz signed-16 stereo PCM to a new
WAV. The default capture limit is 30 seconds; the supported bound is
1..5,292,000 stereo frames (120 seconds). The limit caps the output file,
not the guest run. The runtime counts generated/nonzero/discarded frames and
reports PCM hash, peak, WAV frames/truncation and SDL queue state separately.
Do not equate a nonzero waveform or dummy SDL device with physical playback.

The five audio-focused default suites cover mixer scheduling, PSG synthesis,
ADPCM decode, CDDA provider/cache and continuous CDDA source order. The SDL
audio-host suite separately covers queue bounds, pauses and failures. To build
the optional independent PCM probe, configure with
`-DPCE_BUILD_REFERENCE_PROBE=ON`; run `scripts/pcm_reference.py` as documented
in [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md). Its 56 exact raw CDDA pairs and 24 settled
PSG phase checks do not qualify the final mix, ADPCM PCM or analog filtering.

## Local development control

Both runners include the opt-in `pce-dev-1` loopback TCP interface. No server
starts unless `--dev-port` is supplied. To choose an available port and wait
for development commands, append these flags to a valid invocation:

```text
--video-output continuous --dev-port 0 --dev-start-paused on --wall-seconds 120
```

The runner prints `PCE_DEV_PORT=N` to standard error. The normal guest step/tick
limits and optional wall limit remain active. The standard-library Python
client uses that reported port:

```sh
python scripts/dev_client.py --port 4370 status
python scripts/dev_client.py --port 4370 frames 2
python scripts/dev_client.py --port 4370 input 0x8 --slot 0 --frames 2
python scripts/dev_client.py --port 4370 screenshot new-frame.png --source guest
python scripts/dev_client.py --port 4370 screenshot new-window.png --source present
```

`present` requires the desktop executable and reads its SDL composition,
including letterboxing. It does not capture the operating-system desktop.
The server returns one inline RGB24/base64 response; it accepts no file paths.
The client writes PNG or PPM only when a new output filename is requested,
using exclusive creation. Screenshot requests before the first complete guest
frame return an error.

Held masks support all five controller slots and combine with script/live
input through the existing guest-write-sampled joypad. Keep a connection open
for a held input; disconnect clears its masks. The CLI's bounded `input`
operation holds and clears them automatically. Network pause does not override
a local desktop pause. Frame advancement stops at normal safe boundaries,
not inside a guest instruction. A paused run remains inspectable after a
client disconnect.

The read-only `status` response includes `host.vdc.satb`, the 256 raw SATB
words. These are observational values, not guest MMIO reads or memory-write
controls. An authored host integration test verifies DMA-populated values and
repeated paused observations without advancing guest state. See
[DEV_SERVER.md](DEV_SERVER.md) for the diagnostic schema and bounds.

The main-thread server accepts one client on `127.0.0.1`, bounds requests to
8 KiB and response storage to 17 MiB, and enforces five-second idle/partial/
transmit deadlines. Polling is nonblocking and transfers at most 64 KiB per
call. Paused physical RAM/ROM reads are bounded to 256 bytes. RAM edits require
`--dev-memory-write on`, a settled pause and matching expected bytes for the
entire range. MMIO/BRAM/ROM writes are rejected; changed RAM bytes invalidate
their source generations. Edit counters distinguish assisted tests. There is
no host-language evaluation or file upload. Full wire
syntax, source lineage, limits and reproducible connection examples are in
[DEV_SERVER.md](DEV_SERVER.md).

## Block-transfer checks

`pce-block-tests` uses wholly authored code and an independent byte-array model.
It checks 1,600 transfers, 5,120 status/stack-pointer matrix cases, source/mapping
and deadline guards, block I/O/VDC waits and deferred IRQ boundaries. Four local
TAI cases deliberately overwrite the active opcode; those are excluded from
live Geargrafx parity because its implementation refetches the opcode. The zero-length
cases execute the full 65,536 bytes. Entire work RAM and changed-byte generations
are compared, including stack aliases; completion counters count instructions
separately from payload bytes. MMIO instruction checks are interpreted; both-tier
RAM and deferred-IRQ cases qualify the generated operations separately.

With `PCE_BUILD_REFERENCE_PROBE=ON`, `pce-block-probe` supports the independent
Geargrafx adapter in `scripts/block_reference.py`. See REFERENCE.md for the actual
live matrix, clock totals and exclusions. No media is required by local tests.
The headless JSON reports `native_block_steps`, `interpreter_block_steps` and
`block_bytes` for completed operations. Partial fatal transfers do not retire or
increment these completion counters.

## IRQ and functional device checks

`pce-irq-tests` checks 65,536 independent entry cases, 262,144 RTI status/stack
cases, 32 sampling sequences, 15 guard/mapping/deadline groups and 779 IRQ/timer
register groups. The optional `pce-irq-probe` plus `scripts/irq_reference.py`
compare real pending sources in Geargrafx with corresponding injected request
lines in the local probe. The live matrix passes 832 plans per tier, 2,496 CPU
states, 832 full RAM images and 832 sequence tick deltas. Those comparisons
qualify aggregate instruction boundaries, not physical device access phases.

`pce-video-tests` checks 628,214 palette/snapshot expectations, and
`pce-dma-tests` checks 14,786 DMA expectations. The optional `pce-video-probe`
and `scripts/video_reference.py` compare settled VCE/VRAM/SATB results with
Geargrafx. Current-state RGB inspection has separate local pixel expectations;
it is not covered by that direct-device live adapter. See [VDC.md](VDC.md).

`pce-audio-tests` checks PSG register/waveform/DDA/noise/LFO storage;
`pce-adpcm-tests` checks RAM, delayed ports, length/playback consumption and
CD DMA. The optional `pce-audio-probe` and `scripts/audio_reference.py` compare
settled manual ADPCM/PSG ports against Geargrafx; playback/DMA/oscillator/PCM
qualification is explicitly excluded. `pce-cdda-tests` checks 7,134 audio
control/position/fader and explicit unknown-response-profile expectations;
its seek/sector profile is documented in
[CD_AUDIO.md](CD_AUDIO.md), without a live CDDA or audible-output claim.

All these public fixtures are authored and use no retail input. Build optional
probes with `-DPCE_BUILD_REFERENCE_PROBE=ON`; the precise run commands and
successful reference scope are in [REFERENCE.md](REFERENCE.md). Keep at most
two isolated reference children active and retain bounded summaries rather
than repeated full memory/trace dumps.

## Metadata-only TOC attachment

```sh
python -m pcerecomp toc "/path/to/disc.chd" --out .local/title/disc.toc
```

This command reads CHD metadata and hashes the source without decompression.
A single-track cooked ISO and the [bounded BIN/CUE subset](MEDIA.md) are also
supported. CUE needs no libchdr and uses a complete-image digest covering every
referenced BIN, rather than hashing the descriptor alone. The bounded `PCE_TOC 1`
descriptor records the source SHA256 and disc INDEX 01/leadout LBAs; it
contains no sectors. Keep it under `.local/`; `*.toc` is ignored and the
publication audit rejects descriptors. The exporter refuses an output alias
of the original input.

Pass `--toc .local/title/disc.toc` to the headless runner, alongside `--bios`
in either order if firmware is needed. The runner validates descriptor syntax
and geometry but does not reopen or rehash the original image. Attachment
alone provides directory responses without readable sectors or the extended
audio profile. `--toc`
alone enables transport/volatile BRAM, without enabling the video profile.
See [CD_CONTROL.md](CD_CONTROL.md) for the exact format, pregap/postgap policy,
BCD bounds and reference discrepancies. Metadata-only attachment does not
supply bytes. To attach an actual read-only image, add `--disc /path/to/disc.iso`
or `--disc /path/to/disc.chd --libchdr /absolute/path/to/libchdr.dll` (use the
shared-library suffix for your host). An existing `--toc` must match the actual
image SHA256 and geometry exactly; without it the provider derives both.
The host hashes the full image once, then reads sectors on demand with one
bounded CHD hunk cached. No extraction is required. Its JSON reports provider,
load/byte/error counters and pure source peeks at the stopped PC, including
overlays. The image is never opened for writing.

`pce-read-tests` checks 621,096 independent READ expectations.
`pce-sector-tests` checks 22,568 provider expectations and requires the built
`pce-sector-decoder-fixture` module path; CTest/check.py supply it. That authored
ABI double tests CHD geometry/cache handling without optional libchdr, and is
not a real CHD decompression test. The generic source build has no libchdr
link dependency; `${CMAKE_DL_LIBS}` supplies portable optional dynamic loading.

## Optional CHD backend

```sh
python scripts/bootstrap_chd.py --cc clang
```

This explicitly fetches a pinned source revision, refuses an existing dirty
or differently pinned checkout, and builds a shared libchdr locally. It does
not install anything system-wide. The default backend has no network fetch
during its CMake build. Source acquisition uses GitHub and can be performed
ahead of time. An existing compatible library can instead be supplied with
`--libchdr`. Metadata-only `inspect` does not need the library.

## A private image experiment

```sh
python -m pcerecomp inspect "/path/to/disc.chd" --hash --out .local/title/disc.json
python -m pcerecomp boot "/path/to/disc.chd" --out .local/title/boot
python -m pcerecomp analyze .local/title/boot/snapshot.toml --out .local/title/analysis.json --listing
python -m pcerecomp emit .local/title/boot/snapshot.toml --out .local/title/native
```

Boot/native output directories must be empty to avoid replacing a different
experiment. Analysis JSON can be regenerated in place. Default CFG budget
is 10,000 instructions, with a hard accepted maximum of 100,000. The CHD
reader keeps four hunks in memory. Only IPL-declared boot sectors are read;
this command does not extract a BIN/WAV copy of the disc.

For a single physically contiguous boot segment, link the generated module
by passing its **absolute** path to CMake:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DPCE_MODULE_SOURCE=/absolute/private/title/native/module.cpp
cmake --build build
```

The headless runner's positional arguments are:

```text
pce-headless IMAGE PHYSICAL_LOAD PC MPR_CSV MAX_STEPS MAX_TICKS native|hybrid
```

Take the load address, entry and mapping from your snapshot. For the
standard CD RAM analysis mapping, an example is:

```sh
build/pce-headless .local/title/boot/boot-0.bin 0x100000 0x4000 255,248,128,129,130,131,132,0 100 100000 hybrid
```

On Windows use `build/pce-headless.exe`. A JSON result reports stop reason,
registers, cycles/ticks and native/interpreter counters. Exit **0** means a
step or tick boundary was reached, **2** is invalid input, **3** is an
unsupported instruction, guard miss in native-only mode, or bus fault.
An explicit unsupported stop is useful development evidence; it is not a
successful boot. The runner handles one contiguous payload only; it does
not reconstruct an authentic firmware-initialized machine.

For a BIOS-backed extended run, `--bios /path/to/syscard.pce` enables IRQ/timer,
functional VCE/DMA and audio state alongside CD transport. Add `--disc` for
real read-only sector access; TOC metadata alone cannot supply bytes. Explicit
execution budgets permit 1 through 20,000,000,000 dispatcher steps, selected explicitly;
tick deadlines and optional wall limits still apply. A budget exit, visible
state inspection or functional audio command completion does not certify
playability or full native/AOT execution.

`--bram /path/to/initial.bram` optionally seeds the existing volatile BRAM from
an explicitly selected, read-only raw 2,048-byte input before execution. It
does not format the image, auto-load an owner save or persist guest writes.
Without this option, initial state is unchanged. A standalone BRAM attachment
enables only idle CD control and joypad CD presence; existing BIOS/transport
profiles remain enabled when combined. See [FIRMWARE.md](FIRMWARE.md) for exact
loading, locking and restart semantics. The optional `--wall-seconds` bound
accepts 1 through 86,400 and is independent of the explicit step allowance.
Omitting it retains the raw host's existing disabled wall timer; explicit zero
is refused. Consumer descriptors require a finite value. See
[finite host sessions](SESSION_LIMITS.md).

`--frame-out .local/title/state.ppm` exports one bounded P6 RGB image from the
stopped state in the default snapshot mode. Existing output paths are refused. This inspection reads current
VRAM, SATB, palette and registers without advancing clocks; it cannot reproduce
historical scanline effects. Two-bit background CG selection and the explicit
digital monochrome profile are supported. Undriven-VRAM inspection observes the
stored bus word without driving it. See [the video contract](VDC.md#two-bit-background-and-digital-monochrome-profiles)
and [VRAM bus ownership](VRAM_BUS.md).
Keep retail images private.

Use `--video-output continuous` to select guest-clock historical output in
`pce-headless`. Its `--frame-out` then exports the last completed frame, not
an end-state reconstruction. A run that has not completed a frame cannot
export a valid picture. JSON records completed sequence, guest timestamp,
rendered-line and pixel counters. Host presentation never advances the guest
or changes device deadlines. See [VIDEO_OUTPUT.md](VIDEO_OUTPUT.md).

Use `--input-script .local/title/input.txt` for reproducible input transitions:

```text
PCE_INPUT 1
# Master tick, then five active-high button masks.
0 0 0 0 0 0
21477273 8 0 0 0 0
21835227 0 0 0 0 0
```

This authored example presses Run on pad one after approximately one guest
second and releases it later. Each event has exactly six unsigned decimal or
`0x` hexadecimal fields. Ticks must increase strictly; button masks are at most
`0xFFF`. Files are ASCII, at most 16 KiB and 256 events, with a `PCE_INPUT 1`
header. Events apply at the first instruction boundary at or after the stated
tick. They update host snapshots; the joypad still relatches only on guest
control writes. A long block transfer can cross an input deadline before the
next boundary. These files are input recipes, not save states or desktop input
configuration. `pce-input-script-tests` verifies parser bounds and malformed
inputs. Do not publish game-derived timing/trace data with the public fixtures.

Unknown CD command IDs fault by default. For explicit compatibility research,
`--cd-unknown-status gear-good` selects the source-documented Geargrafx/Mesen
one-byte unknown-command GOOD-response quirk; the JSON records the selected
policy and `unknown_commands` counter. Known commands with unsupported
operations still fault. REQUEST SENSE is implemented separately with its fixed
NEC response and error lifecycle; see [CD_SENSE.md](CD_SENSE.md). Selecting the quirk does
not implement an unknown command's operation or qualify its hardware behavior.
The current retail menu-to-story route is conditional on this opt-in; strict mode
retains the unknown-command stop. Keep that distinction in every result claim.

Clear a private module selection before returning to the generic sandbox:

```sh
cmake -S . -B build -DPCE_MODULE_SOURCE=
cmake --build build
```

## Snapshot schema 1

A hand-authored snapshot pins physical byte segments. Each file is resolved
relative to the TOML file; source SHA256 is verified before analysis.

```toml
schema = 1
mpr = [255, 248, 128, 129, 130, 131, 132, 0]
entry_points = [16384]

[[segments]]
physical = 1048576
file = "your-private-code.bin"
sha256 = "replace-with-the-actual-segment-sha256"
```

TOML/JSON snapshots and generated modules contain original program bytes or
translated logic. Keep them private even if the filename itself is not an
image extension. `module.json` reports emission counts; it is not execution
evidence. `.gitignore` is a convenience, not authorization to publish data.

## Publishing source

The optional [consumer package cache](BUILD_CACHE.md) is a separate explicit
build feature. Test fresh cold and warm packages, verify their receipts and
launch the restored package independently of SDK search paths. A warm hit
still configures and may perform compiler probes; it skips consumer compilation
and linking. Transport unit tests alone do not prove a usable native package.
Keep all cached game binaries and private evidence out of publication.

The initial GitHub credential permits source publication but lacks the
`workflow` scope needed to publish Actions workflows. The reviewed pipeline
is retained as `.github/ci-template.yml`; it does not execute in that location.
After the repository owner authorizes `gh auth refresh -h github.com -s workflow`,
copy that file to `.github/workflows/ci.yml`, commit and push. The template
runs synthetic tests on Windows/Linux/macOS and builds the optional pinned
CHD backend. It uses no game input. A template is not a passing CI run.

Stage only authored source, synthetic tests and documentation, inspect
`git diff --cached`, then run `python scripts/audit_public.py`. The audit
checks tracked paths, simple credential/personal-path patterns, text/binary
content and size caps. It is a focused publication check, not a complete
secret, copyright or license scanner. CI uses no retail inputs and uploads
no title-derived artifacts.
