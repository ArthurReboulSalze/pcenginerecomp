# Current status — 1 November 2026

## Independent pending-VRAM guest coverage and reference admission

The new opt-in queue race matrix passes 24 cases / 1,536 records against
the original Geargrafx core pinned at `1c62a549328241518101f5be5bf3e6840b96ea5d`.
Real guest instructions change CR increment while a guest-started 512-word
DMA holds the VRAM request pending. Both CPU speeds, three VCE dividers and
selected driven/undriven wrap cases match without field projections.
All 744 translated retirements execute natively with zero fallback across
124 encoded identities; 96 pure source/MPR misses include 48 in genuinely
pending windows. Full CORE preservation for those guard misses remains
separate from fresh-process checkpoint restoration. See
[the authored guest scope](VDC_ACCESS.md#guest-register-changes-during-pending-requests).
The fresh combined old/new run passes 639 cases / 4,092 records and 1,326
native retirements with zero fallback. It preserves exactly the old 99
named MWR3 read-bus differences; all new race fields remain exact.

The shared HTTP Gear client now validates response identity and shape and
refuses duplicate keys, non-finite JSON and malformed tool content. Six
authored replies accepted by the exact previous client are refused by the
new client. Fourteen focused tests and an actual isolated Gear initialization,
empty notification acknowledgement and no-media tool call pass. These checks
qualify transport admission, not CPU semantics. See
[the shared reference boundary](REFERENCE.md#shared-http-reference-boundary).

Compiler/runtime source remains the same 84-file digest
`16679df8f6758cbac67e97dc2a3cb20d327ee80631e3cce25601dc0672b0734a`;
runtime ABI 28 and exact-build checkpoint compatibility are unchanged. No
consumer rebuild is required. This batch strengthens verification without inventing a VDC
or CD runtime defect. Captured subchannels and other device profiles remain
[planned work](ROADMAP.md).

The Ys III project separately tests its now-selected, previously qualified
native package through TCP. Two distinct processes each continue 60 frames
from the same package-owned final checkpoint, executing **1,866,913 native
instructions and zero interpreted instructions** across 2,962 full encoded
identities. Both entire immediate checkpoint files equal the source file;
continued files, CORE/HOST, RAM, pixels and per-key counts match. The tests
make no new RAM writes. Imported frame 111,789 and its instruction/PCM prefix
are not newly executed work. This is a fresh exact-build continuation
regression, separate from cold-reset qualification and ongoing discovery.

A separate paced 120-frame fork from the same checkpoint executes 3,736,634
native instructions with zero fallback and closes naturally through SDL.
Digital queue accounting is exact: 33 imported frames + 88,457 newly
generated = 88,487 submitted + 3 pending. The 604-frame planned pause-tail
clear, zero observed active drops and three shutdown frames remain separate.
Raw newly generated/nonzero counters support a conservative lower bound of
87,850 fresh nonzero frames accepted by the device. The capped 88,200-frame
WAV contains 33 imported and 88,167 fresh frames; it does not prove the
remaining newly generated tail. This is digital submission evidence, not a
listening, physical-device fidelity or complete-campaign claim.

The fresh required SDL build/check passes **1,600 Python tests with zero skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**. Both the shared
84-file compiler/runtime identity and the complete public verification-source
epoch remain unchanged during that check. Independent fixture/core proofs,
HTTP transport tests and retail checkpoint/audio forks retain separate scopes.

## Four staged late identities qualified

The existing profile-v2 consumer now completes a fresh 104,745-frame reset
replay and seven candidate-owned continuations: **111,789 route frames,
3,433,175,577 native instructions and zero interpreted instructions** across
eight processes. All four added byte/mapping identities have positive native
execution and conserve their original per-key native-plus-interpreted counts.
Complete source/state comparisons retain their exact declared relations.

The canonical route exercises **53,613 of 58,039 compiled identities**, leaving
4,426 unexercised. All 53,606 previously exercised identities recur; three
retained identities are first exercised later alongside the four additions.
Each addition retires exactly once natively in the canonical route. Repeated
checkpoint/audio forks do not inflate this coverage union.

The final 522-frame window repeats from the same candidate-owned checkpoint;
all 6,851 encoded identities/counts, whole checkpoint files, CORE/HOST, RAM and
pixels match. Independent prefix checkpoint and paced digital-audio forks also
pass. All repeat/audio forks are excluded from route and coverage totals.
The route contains 314 declared validated data writes, not an unassisted
campaign. No older-build checkpoint, owner save or installation is used.

This qualifies execution of the four additions on the unchanged
`cd5bff67b323098979345f76d5b87075fc628e72` implementation and its already built
58,039-identity candidate. It adds no runtime/ABI semantics or fresh hardware
claim, and changes no consumer default. See [the complete source, checkpoint
and digital-audio scope](NATIVE_MIGRATIONS.md#staged-profile-v2-late-identity-qualification).

## Staged additive observation composition

Opt-in [profile-v2 composition](OBSERVATION_PROFILES.md#add-identities-without-duplicating-overlapping-contributions)
retains complete original captures while selecting only new full instruction
identities from each extension. Its stage ledger preserves earlier selected
contributions; original historical totals, selected totals and omitted overlap
are independently reconstructed. Profile-v1 bytes/manifests and existing
input/raw-byte/identity/serialization bounds remain unchanged.

The real consumer's four authentic micro-captures add four identities but
3,615 original rows. Ordinary full composition would require 264,174
contributions, beyond the unchanged 262,144 limit. The official two-stage
extension retains all 58,035 original rows exactly, produces 58,039 identities
and 260,563 selected contributions, and preserves all 16 original raw inputs
(46,869,819 bytes). Exact dry-run bytes/hash match both actual outputs; the
final profile is 129,648,072 bytes, below 128 MiB. Repeating the same extension
preserves the exact profile hash. Original input ABI/origin labels remain.

Re-emitting the retained profile reproduces all 948 C++/header files exactly.
The four new direct translations change only two existing stable partitions.
An independent authored comparison also preserves 26 version-1 artifacts
across six emission configurations. These composition/emission checks do not
establish execution of the four new identities.

Frozen implementation `cd5bff67b323098979345f76d5b87075fc628e72` has 84 shared
source files, SHA256
`16679df8f6758cbac67e97dc2a3cb20d327ee80631e3cce25601dc0672b0734a`.
All 60 runtime/CMake source files retain the earlier exact bytes. Emitter
metadata changes preserve the translation core and ABI 28. Existing Gear
reference checks keep their original source pins; this interface milestone
does not broaden hardware/device compatibility.

That frozen source passes the complete required SDL checker: **1,583 Python
tests with zero skips, 68 C++ suites and 12 fresh-process audio checkpoint
cases**, with identical shared source before/after. An authored profile-v2
consumer actually compiles and runs six direct native instructions with zero
interpretation, independently expected A=41, X=43 and PC=$4003. Its profile
binding and later tamper refusal are checked separately from game execution.

An ordinary fresh v2-bound retail consumer compiles all 976 objects and three
archive/executable links. It completes **900 fresh startup frames, 27,025,270
native instructions and zero interpreted instructions**, then two candidate-owned
60-frame continuations of **1,602,420 native and zero interpreted instructions**
each. Immediate and continued whole checkpoint files, CORE/HOST, full RAM,
pixels and all 187 encoded identities/counts in the 900-to-960 suffix match.
The first 900 frames retain separate aggregate counters. Its runtime PATH
contains Git and Windows directories; the actual adjacent SDL library is
verified. No old-build checkpoint is imported and no guest RAM write is used.
That initial startup/checkpoint qualification did not establish execution of
the four later identities. The subsequent dedicated qualification above does;
consumer selection remains a separate responsibility.

Separately, the existing selected consumer's new 84-frame checkpoint route
executes **2,666,212 native and one interpreted instruction**, exposing the first
pending identity. Its own 60-frame cut followed by direct/restored 24-frame
suffixes matches complete files, RAM, pixels and 3,860 encoded identities;
each suffix records 762,336 native and one interpreted instruction. These are
current-build hybrid evidence, with original source and prefix provenance kept
separate from the new v2 candidate. No selection or checkpoint migration is
implied.

## Verified interrupted consumer builds

Opt-in [build recovery](BUILD_RECOVERY.md) is implemented for Windows 10/11
x64 LLVM-MinGW/Ninja. A durable preconfigure contract and configured seal bind
the original inputs and effective graph. Immutable object/dependency groups
let `project resume` retain verified work, rebuild unsealed outputs and freshly
link the package. An independent guardian holds the directory lease until
owned compiler descendants exit; uncertain cleanup quarantines the directory.
Ordinary old directories, incomplete configuration, changed inputs or sealed
objects, unsafe paths and completed builds refuse recovery.

Frozen revision `9d219b7a27fa67ff3f31a124e5d449b7eaf1789b`, 84 shared source
files, SHA256
`74b4a39c59ac5ee0fd40ea54af9b7099aa2aa0f5dbce5b3107df2bf2e6ef35ac`,
passes the complete required SDL checker: **1,554 Python tests with zero skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**. Source identity
is unchanged before/after the check. Thirteen process tests and 60 repeated
cleanup stress cases separately cover hard parent termination, immediate
lease reacquisition, descendant termination and fail-closed cleanup errors.

A genuine authored 100-object build is interrupted during compilation after
sealing 32 objects, then interrupted again after sealing 96. Its final public
resume retains those 96 objects, rebuilds four, executes all archive/executable
links and passes official execution with
**200 native instructions, zero interpreted instructions and zero guard misses**.
Independent arithmetic checks X=107, PC=$4003, 598 CPU cycles and 1,794 master
ticks. A separate retained-artifact audit passes 530 checks. The deterministic
temporary-file fixture is explicitly authored; an actual larger consumer
interruption independently exposed Clang's temporary-output naming. The fix
admits only exact audited object siblings, discards them after full admission
and records path/target/size/hash. Rejected admission preserves those files.
The original failed consumer attempt and canceled checker remain separate.

A later full-size consumer exposed a second defect: its cumulative checkpoint
grew to 171,930,946 bytes, beyond its own reader's 64 MiB bound. The final
format keeps that per-record bound and writes at most 32 object updates per
delta. Replaying the hash chain assembles the ledger. Durable admissions keep
missing-object rebuilds unsealed across further interruptions, even when an
attempt commits no delta or leaves bytes identical to an old object. Authored
tests exercise aggregate history above 64 MiB. Earlier cumulative-format
builds and their limited execution receipts retain their original source;
they are not upgraded or relabeled as delta-format qualification.

A separate 976-object native consumer is then interrupted after 416 sealed
objects. Its 13 compact records total **73,318,494 bytes**, above the unchanged
67,108,864-byte reader bound, while its largest record is only 5,703,823 bytes.
Public resume validates the history, retains 416 objects, rebuilds 560 and
freshly links the executable and project archives. Runtime DLLs are copied and
byte-verified against their declared inputs. Original before-cut
object hashes, timestamps and Ninja execution records are retained separately.

That recovered package completes **900 fresh TCP-controlled startup frames,
27,025,270 native instructions and zero interpreted instructions**. Two
candidate-owned 60-frame continuations each execute **1,602,420 native and zero
interpreted instructions**. Immediate and continued complete checkpoint files,
CORE/HOST, RAM and pixels match. All 187 encoded identities and their counts
match within the recorded 900-to-960 suffix; the first 900 frames have separate
aggregate counters, not that per-key capture. No old checkpoint import or guest
RAM write is used. The runtime PATH excludes LLVM and SDL SDK directories.
This qualifies the recovered package and finite startup/checkpoint window;
the consumer's new catalogue additions and expanded route remain separate
qualification work.

The complete runtime/CMake/top-level CMake/emitter closure, 61 files, remains
byte-identical to the earlier ABI28 source. ABI 28 and guest semantics are
unchanged. Earlier full-route, Gear and audio qualifications below retain
their original source pins and scope; this build feature does not migrate or
broaden those claims. Guest checkpoints remain exact-build-bound.

## Verified baseline

This is an executable compiler/runtime foundation with continuous software
video and an optional desktop window. Queued VDC tests cover ordinary town
navigation, first-mine combat, natural death/retry and guest SAVE/LOAD. Earlier
qualified profiles also demonstrate level progression. Separate, explicitly assisted
tests reach the Pendant, Storehouse Key and first-storehouse-boss encounter,
with observed damage to the enemy bar. The complete final route reproduces
across headless and SDL hosts within the documented comparison scope.
**No complete game port is certified.**
The public source needs no retail input to build or test. SDL is optional.

## ABI28 native consumer migration

The fixed-timing ABI28 consumer completes a fresh reset replay of **104,745
frames, 3,209,517,525 native instructions and zero interpreted instructions or
guard misses**. Independent audits join every one of its 53,516 executed
encoded identities, all 108,460 semantic records, 147,100 raw request/reply pairs,
309 typed assists and 26 complete-state comparisons. Historical reference
prefix and tail processes retain their separate provenance; the candidate
actually starts from reset.

Its own checkpoint lineage then passes the retained 432-frame suffix,
2,232-frame combat extension and new 960-frame lower-waterfall window. The four
separate processes execute **3,325,153,884 native and zero interpreted
instructions across 108,369 contiguous route frames**. All 7,238 source
fallback retirements become native. The catalogue preserves 58,031 identities
and adds one, for 58,032; 53,576 actually execute, leaving 4,456 unexercised.
All nine source files retain exact bytes, original ABI labels and declared
provenance, including the earlier derived catalogue. The 127,924,412-byte
profile remains within unchanged parser limits.

Each assisted extension compares all three raw source/native checkpoint cuts,
with only the fixed timing insertion and exact lifetime tier equations allowed
in CORE; all 60 HOST bytes are strict. The two main link/final comparisons
retain their separate, exact ACK-backed WAV scalar relation. Every file binds
its own producer package, context, fingerprint and actual save reply. No ABI27
checkpoint is loaded into the candidate.

Two further fresh continuations each execute **60 frames and 1,836,171 native
instructions with zero fallback**; immediate own-cut and complete continued
files, RAM, pixels and source-hit counts match. The direct/restored audio
origins are separately ACK-bound to `{40, 441000}` and `{40, 0}`. A paced
120-frame fork executes **3,672,293 native and zero interpreted instructions**,
generates 88,457 new PCM frames and proves at least 87,719 newly accepted SDL
frames. Its 728-frame planned pause clear and ten-frame shutdown drain stay
separate from active observations, which show zero drops or unplanned clears.
These digital checks do not establish listening or physical hardware parity.

Fresh verification uses unchanged shared source at
`a96e7891c33690d41f6fe12ce1904fe160a0c9a2`, 82 files, SHA256
`995ecfa893ee74ea046b758cbccfe0ab1baa57ecbec21c8a4c7313f06aca533a`.
The complete required SDL checker passes **1,508 Python tests with zero skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**. A separate fresh
Gear command comparison covers seven authored cases at both CPU speeds,
with 25,162 native and separately 25,162 interpreted toolkit retirements.
It reuses explicitly sealed compilations; retained original-core supervision
and known reset/leadout differences keep their documented scope.

The first native attempt remains failed after an inherited capture-summary
comparison rejected the actual ABI28 tag. New versioned diagnostic adapters
keep original labels, strict reply types, source-only imports and all other
state comparisons intact. The interrupted build and refused same-directory
recovery also remain distinct receipts. General runtime/emitter semantics are
unchanged in this migration; title-specific routes and assistance remain in
the consumer. See [complete migration scope](NATIVE_MIGRATIONS.md#abi-28-fixed-timing-native-migration)
and [build recovery](CONSUMER.md#recover-an-interrupted-build).

## ABI 28 CD drive timing and composition planning

The optional `gear-distance` timing profile adds distance-sensitive READ and
CDDA deadlines using a bounded integer model with published measurement
provenance. Physical seek completion and playback readiness are distinct.
`fixed` remains the default with its original deadlines; unknown-command
response policies are independent. The profile is serialized, configuration
checked, recipe-bound and reported by both hosts. Native modules require
regeneration/rebuilding for ABI28; exact-build checkpoints are not migrated.
See [CD timing and reference scope](CD_TIMING.md).

Read-only `compose-observations --dry-run` shares real composition admissions
and exact profile-v1 serialization. Explicit retained baseline inputs let it
report new keys, raw bytes, contributions, exact output bytes/hash and headroom
without writing or building. Existing limits and original bytes/ABI/origin
provenance are unchanged. The real seven-input baseline reproduces exactly;
the separate consumer's eight-input extension also matches its planned bytes
and hash. See [composition planning](OBSERVATION_PROFILES.md#preflight-an-extension-before-emission-or-build).

The qualifications below remain tied to their original ABI/source epochs;
an existing ABI27 game package is not automatically an ABI28 qualification.

Frozen diagnostic revision `ea6382a774bbe9846a12c61a2818487c3fa70e0a`
passes the complete required checker: **1,508 Python tests, zero skips,
68 C++ suites and 12 fresh-process audio checkpoint cases**. Its shared
compiler/runtime/CMake closure is 82 files, SHA256
`995ecfa893ee74ea046b758cbccfe0ab1baa57ecbec21c8a4c7313f06aca533a`.
Independent frozen-source comparison passes 12,432 seek vectors per model
and 21 command cases at both CPU speeds. Toolkit guest runs execute
112,536 native and, separately, 112,536 interpreted instructions across ten
executed encoded identities. Original Gear command-port supervision and
Mesen calculation comparisons retain their separate scopes and declared
reset/leadout differences. See [qualification details](CD_TIMING.md#verification-scopes).

The separate ABI27 consumer extension retains all 58,002 compiled identities
and adds 29. Its real eight-input profile exactly matches the preflight's
126,156,528 bytes and hash. A fresh native reset repeats the 104,745-frame
main route, followed by its own checkpoint-linked extensions. The new
2,232-frame combat window executes **70,860,852 native and zero interpreted
instructions**, promoting all 331 discovery retirements. All 29 additions
execute; the main/extension union is 53,568 executed identities, with 4,463
compiled identities still unexercised. Candidate-owned checkpoint and paced
audio tests pass separately. See [native combat extension](NATIVE_MIGRATIONS.md#abi-27-checkpoint-combat-extension).

## ABI 27 invalid-CD-command profile

The opt-in `nec-invalid` profile receives a complete unknown CDB under the
NEC reference's six-/ten-/twelve-byte table, then reports CHECK CONDITION and
sense key `$05`, ASC `$20`. The default `fault` and legacy first-byte
`gear-good` profiles remain explicit. No `$FF` firmware operation is invented.
Known commands with unsupported semantics still fault.

The typed policy and checked invalid-response counter are serialized,
validated and configuration-bound. Native modules must be re-emitted and
rebuilt for ABI 27; original capture labels 12–26 remain intact. Checkpoint
schema 1 remains exact-build-only, with fresh candidate-owned states required.
Current Python emission/build/reference contracts share the ABI constant,
and CMake generation dependencies include it.

Authored direct-device tests cover all 248 unrecognized opcodes under all
three profiles, held ACK, prefix/completion boundaries, error/sense lifecycle,
overflow and 200 complete-machine checkpoint cuts. These checks are separate
from actual interpreted/native guest execution and independent core results.
Original Gear completes an unknown first byte with GOOD; original Beetle
frames the full packet and returns illegal-command sense. Toolkit error wire
bytes remain `$02/$02`, versus Beetle's `$01/$00`. Toolkit reset clears a
partial CDB; Beetle's warm-reset cursor retention is recorded as a difference.
See [unknown CD commands](CD_UNKNOWN.md).

Fresh original-core comparison covers 252 cases per core, including every
unrecognized opcode. The autonomous authored toolkit guest separately
executes 23,241 interpreted and then 23,241 native instructions with zero
fallback; all 893 source identities conserve retirements. Its reported CPU/
work vector, 44 observed RAM bytes and pending sense agree. These are
separate proof scopes from the complete-state checkpoint cuts.

The earlier bounded ABI27 Ys III candidate passes an unassisted cold prefix, ten-byte `$FF`
rejection followed by READ `$08`, and candidate-owned fresh checkpoint
restores with complete-file continuation equality. A paced 120-frame fork
executes 3,689,416 native instructions with zero fallback and proves newly
generated audio submission under separately counted pause/shutdown clearing.
This cohort executes 6,816 of the retained 57,752 compiled identities. The
ABI26 Play package stayed protected at that milestone; those bounded checks
alone did not qualify a full route, campaign, listening or hardware. See
[the bounded consumer scope](CD_UNKNOWN.md#bounded-ys-iii-consumer-checks).

Frozen code `1bac964633c624f2d6834337e621940c41c8aeb4` passes fresh SDL Release
configure/build and the complete required checker: **1,478 Python tests with
zero skips, 66 C++ suites and 12 fresh-process audio checkpoint cases**.
The shared compiler/runtime/CMake closure is 80 files, SHA256
`7c2771ff590fcd2cdfdfd51e71c8a34aab2a6a86b48d275d6071b8832647e8c4`.
The original independent matrix uses diagnostic code `68125cf`; the latest
repeated comparison pins `b1ffdcc`, and the consumer pins `d71add5`. All four
revisions have identical 80-file shared source bytes. Later fixes affect diagnostic guards, authored
examples and test expectations, without relabeling those original receipts.

## ABI 27 native migration

The ABI27 catalogue preserves all 57,752 retained identities and adds 250,
for 58,002 compiled identities. Seven original capture inputs retain their
ABI labels, raw bytes, checkpoint origins and per-input contributions.
The 121,417,027-byte profile stays within existing public parser limits;
checkpoint reconstruction and native verification captures are excluded.

A fresh native reset passes the admitted `nec-invalid` route through the
actual Alcaino frontier: **104,745 frames, 3,209,517,525 native instructions
and zero interpreted instructions or guard misses**. All 53,516 executed
source identities conserve their counts; 6,899 interpreted retirements become
native. The route contains 5,523 bounded steps and 309 typed assisted writes.
It compares against a separately admitted reset prefix plus an exact-build
checkpoint tail, not a falsely relabeled uninterrupted reference run.
See [the migration scope](NATIVE_MIGRATIONS.md#abi-27-native-migration).

All 26 source/native checkpoint comparisons pass with exact non-tier machine
state and explicitly bounded host WAV bookkeeping. Two candidate-owned
fresh-process suffixes each execute 60 frames and 1,836,171 native instructions
with zero fallback; immediate and continued whole checkpoint files match.
A separate paced 120-frame suffix executes 3,672,293 native instructions with
zero fallback. It synthesizes 88,457 new PCM frames and proves at least 87,760
newly accepted SDL frames. Imported PCM, planned pause clearing and shutdown
draining are separate, with zero observed active drops or unplanned clears.
These are digital synthesis and submission checks, not listening or hardware
qualification. The shared runtime/compiler and checkpoint schema are unchanged.

A read-only 432-frame extension from the successful build's own final
checkpoint executes 13,795,134 native instructions with zero fallback,
converting seven more interpreted retirements. The main/extension union is
53,528 executed identities; all 250 newly compiled identities execute. Five
of the extension's twelve identities absent from the main run are new to
the catalogue, while seven were already retained. Its inherited 309 debug
writes remain visible, with no new writes.

## Earlier full retained-route native migration (ABI 26)

Ys III's fresh ABI 26 native replay passes the retained route through the
terminal stair room: **102,802 frames, 3,122,661,937 native instructions and
zero interpreted instructions**. Each executed source identity conserves its
discovery retirements; 3,433 fallback instructions, including 68 block
transfers, become native. The composed catalogue retains all 57,545 old
identities and adds 207; 54,610 distinct identities actually execute.
Historical profile sums are separate from these new execution totals.
The route retains the explicit `cd-unknown-status=gear-good` compatibility
policy; this native migration does not resolve unknown CD command semantics.

The consumer seals 5,257 semantic frame requests and compares 94,286 settled
semantic records. Progress polls remain retained under finite bounds rather
than being falsely compared as deterministic CPU snapshots. All 300 explicit
assists use the typed RAM-write relation. Six nonempty automated semantic
rules cover part of the 33 case boundaries; retained images and controls add
miner dialogue, an assisted deeper-boss defeat/rewards and terminal-stair
movement. The result is finite assisted coverage, not a completed campaign.

An independent comparison of all 16 baseline/native checkpoint pairs finds
every serialized machine-core byte equal outside five explicitly validated
execution-tier counters. Original archives and their separate module
fingerprints remain intact; no modified checkpoint is loaded.

Candidate-owned checkpoint tests restore in fresh processes. Immediate files
and complete continued files match; each neutral suffix executes 60 new
frames and 1,851,616 native instructions with zero fallback. Digital synthesis
and SDL presentation accounting remain separate. A new 120-frame paced
suffix executes 3,703,226 native instructions with zero fallback, generates
88,456 new PCM frames and quits naturally. All 119 active observations show
zero host drops; planned pause clearing and shutdown draining are separately
accounted. Device submission does not establish listening or physical
playback parity. The earlier failed zero-drop-across-pause criterion remains
preserved.

This batch changes shared diagnostic tooling and its required host coverage;
runtime/compiler/CMake sources, ABI 26 and checkpoint schema 1 are unchanged.
No new Geargrafx run is claimed for the consumer migration. See
[native migrations](NATIVE_MIGRATIONS.md) for reusable identity, replay,
counter-conversion, checkpoint and audio qualification requirements.

## Semantic frame steps for native replay

The new standalone `scripts.dev_steps` seals a single literal `step_frames`
operation and admits a candidate's bounded progress against its actual paused
endpoint. Intermediate polls can differ in count and CPU/device state; their
parsed observations remain retained, with no fabricated guest-state equality.
Literal frame count, queued target and starting/final frame/ticks stay exact.
Intervening requests, gaps, pause interruption, incomplete steps, invalid
types, overflow, altered seals and bound violations are refused. Final guest,
source, RAM, image, audio and tier comparisons remain the consumer's duty.
See [SEMANTIC_STEPS.md](SEMANTIC_STEPS.md).

Timestamp-free journals do not establish wall duration. An unmeasured baseline
is explicitly marked; candidate admission requires a separately supplied
elapsed measurement within a declared bound. The digest binds canonical
parsed evidence, not raw wire bytes or process success. The caller binds the
closed source journal and any pre-step commands separately. An explicit
frame-zero label grants no automatic host-field allowance or reset claim.

Frozen code `2c08093266162b403a545208361e045be54dc1f7` passes fresh SDL Release
configure/build and the required checker: **1,461 Python tests without skips,
65 C++ suites and 12 fresh-process audio checkpoint cases**. Twenty authored
step tests include two loopback protocol/journal checks; a new required real
headless-host test adds complete checkpoint restore/continuation coverage.
The earlier helper-only freeze `929dcc3` separately passed 1,460 Python tests;
the final freeze adds that host regression without changing helper semantics.

The authored real host's one-frame request naturally completes at frame 13
after a 65,536-byte identity-copy TII: six interpreted instructions, zero
native, 4,719,000 ticks. A fresh process restores the starting checkpoint and
produces identical complete endpoint files and core payloads. Both hosts quit
naturally. A separate private raw audit joins 151 request/reply pairs and 128
RAM chunks across 35 bindings. This is synthetic host evidence, not new game,
native-emitter, Geargrafx or hardware qualification.

Runtime/compiler/CMake sources remain unchanged: 79 files, SHA256
`d17bdc9159b53b00144a388ebe45a6f7e5e7c5767b7de1989df0e50db24e213c`.
Runtime ABI 26/checkpoint schema 1 are unchanged. The helper sits outside that
narrower source digest and must be independently pinned as a diagnostic input.

## Consumer adoption of paused writes and archives

Ys III's consumer now integrates the shared relation through its own single-use
assist adapter and adopts an explicit closed-journal archive workflow. Its
diagnostic dependency is pinned to `1be93679c3318c667f97f55cb37af625a86ad875`,
separately from the retained ABI 26 executable and selected ABI 18 launcher.
Neither a runtime patch nor a native-module rebuild is needed for this step.

Independent review fixed consumer integration gaps before the canonical test:
stale Python bytecode/cached helper imports, missing live source-epoch joins,
missing journal enforcement, ambiguous/nonfinite closure JSON and incomplete
retained-prefix provenance checks. Diagnostic helpers execute verified source
bytes. The prefix capture hash must match its original closed receipt and
full-reset window; a new hash with matching totals is insufficient. These
requirements are reusable contributor guidance under
[consumer write adoption](PAUSED_WRITES.md#adopting-the-relation-in-a-consumer)
and [archive adoption](PAUSED_OBSERVATIONS.md#consumer-archive-adoption).

The final-source consumer test restores its closed frame-69,891 checkpoint,
re-establishes authority for one exact living-HP data CAS and uses the adopted
adapter while code executes from the same WRAM bank. A fresh process restores
the postwrite checkpoint with complete immediate reserialization equality.
Writer and restorer each run five neutral 12-frame steps, checking HP, the
read-only maximum, actor, neutral state, source and audio-loss predicates at
their boundaries. Each 60-frame suffix retires **1,951,472 native and zero
interpreted instructions**, with **21,536,028 new ticks**. Complete continued
files and separately parsed core payloads match byte for byte. Both owned
hosts quit naturally; their closed journals are archived without removing
or relabeling originals.

The independent offline audit rehashes 1,032 artifact bindings and joins all
544 full-RAM reply chunks to 652 raw request/reply pairs across 1,306 records.
It reconstructs the adopted adapter's one actual CAS, checks each of the ten
title-guard observations follows its own step before the next advance, and
verifies retained-prefix identity plus imported/new/cumulative counter equations.
The original 645,761-byte and 474,559-byte journals remain intact alongside
114,740-byte and 85,014-byte gzip archives. Independent streaming decompression
and raw-event digests preserve every request, reply and ID. Publication source
bytes are checked separately against the consumer commit.

The imported 2,117,569,044 native/614 interpreted discovery prefix remains
separate and unqualified as a full route. This does not select a new game
build, establish listening/hardware parity, certify future code footprints
or prove a campaign milestone. The earlier pilot remains a separate source
epoch. No additional guest run is inferred from offline journal audits.

Independent checks pass **24 authored consumer adoption tests** and **76
focused unchanged-toolkit checks**. The previous fresh toolkit build/check
baseline below remains its own epoch; production/compiler/runtime sources
are unchanged in this adoption-documentation batch.
The consumer's full suite separately passes **547 tests without skips** and
its public adoption is
[`50d669e`](https://github.com/rages4calm/ys3recomp/commit/50d669e1380f69ae57607d393d0415124067176a).
Its archive wrapper and authored test were executed with CRLF source bytes
that Git normalizes to LF. Their raw hashes remain distinct; publication
admission checks the exact line-ending transform and identical compiled code
under the same filename. The diagnostic helper bytes retain their exact Git
pins. This normalization relation does not rewrite the execution receipts.

## Typed paused writes and closed journal archives — ABI 26

The separate `scripts.dev_write.validate_paused_write` relation checks one
declared successful RAM CAS against raw request/ACK objects, complete backing
readbacks, exact counters and alias-generation arithmetic. Code bytes, logical
PC, all eight MPRs and other reported fields remain strict. Explicit WRAM,
linear-RAM and Populous mappings are supported; host/source/topology bindings
and complete historical/live code-footprint authority remain caller duties.
Predicted noncurrent bank deltas are not observed generation evidence.
See [PAUSED_WRITES.md](PAUSED_WRITES.md).

The offline gzip archive helper preserves exact original journal bytes and
retains the source file, with separate stored-container hashes. Streaming
admission requires one intact gzip member; CRC/truncation/trailing bytes and
concatenated members are refused. An explicit forensic-prefix option never
excuses container damage. Schema 1 has no connection-close marker: declaring
the writer closed is an external obligation, not inferred from paired replies.
See [journal archives](PAUSED_OBSERVATIONS.md#archiving-a-closed-journal).

These are host diagnostic tools. They do not change guest CPU/device behavior,
runtime ABI 26, checkpoint schema 1, native dispatch or consumer selection.

Frozen code `d74e0d5ea3a65264d5ab247271a50f4311d0c7f2` passes the fresh SDL
Release build and required checker: **1,440 Python tests without skips,
65 C++ suites and 12 fresh-process audio checkpoint cases**. Thirty-eight
new Python tests include 16 authored write-vector groups, 19 archive tests
and three live TCP host tests. Runtime/compiler identity remains 79 files,
SHA256 `d17bdc9159b53b00144a388ebe45a6f7e5e7c5767b7de1989df0e50db24e213c`.

The authored headless and SDL fixtures execute WRAM-resident code; a separate
freshly emitted/compiled native fixture executes the same operations. Each
checks three successful writes including a no-op, one stale refusal, literal
generation deltas, complete backing RAM and backing-boundary wrap. Immediate
and continued complete checkpoint files match after a fresh process restore.
Each restored two-frame suffix executes 59,605 instructions and 715,260 ticks:
interpreted in the stock hosts, native with zero interpreted instructions in
the generated fixture. Imported prefix work stays separately reported. Each
fixture retains 360 raw request/reply pairs. This is authored host evidence,
not new Geargrafx or hardware qualification of debug operations.

The separate retained-build Ys III check restores the closed frame-69,891
discovery checkpoint into an isolated muted host. It independently rechecks
the exact literal HP 29-to-40 assist and excludes its backing aliases from
41,985 supplied original/live source-footprint bytes. One actual paused CAS
changes one canonical WRAM byte; the seven reported fetch generations advance
76,303,470 to 76,303,471 while PC, all MPRs, fetched bytes and other reported
state remain exact. Noncurrent alias generation changes are predicted effects,
not directly observed counters.

The postwrite checkpoint round-trips byte for byte in a fresh process. Writer
and restorer then each execute one neutral frame: **31,945 native, zero
interpreted instructions and 355,317 new ticks**. Complete endpoint files and
their separately parsed core payloads match byte for byte. The imported
2,117,569,044 native/614 interpreted prefix remains assisted discovery evidence;
this is not a new runtime build, consumer adoption, route qualification or
campaign milestone. Both owned hosts quit naturally with code 0. The original
failed consumer preflight and selected ABI 18 launcher remain unchanged.

A separate offline archive of a closed prior TCP journal preserves all
**755 events and 377 request/reply pairs**, with exact raw replies and IDs.
The 2,121,817-byte original becomes a new 119,868-byte gzip file; an independent
standard-library streaming decompression reproduces the original full hash.
This is historical-log verification, not another gameplay run.

## Active-display raster/sprite IRQ checkpoints — ABI 26

New authored coverage combines actual raster-compare or sprite-collision IRQ1,
READ-fed ADPCM IRQ2 and a queued high-byte VRAM read or TAI during visible
HDW/VDW. It varies both CPU speeds, all three VCE dividers and guest retain/
mask acknowledgement policies. Source identities, CPU/stack, literal full
memory expectations, actual execution tiers and imported/new work remain
separate checks. No injected IRQ or device phase is used. No runtime or emitter
patch was justified. See [ACTIVE_IRQ_CHECKPOINTS.md](ACTIVE_IRQ_CHECKPOINTS.md).

Frozen code `a07fba09359103f237a8dbf600842b9bba351617` passes **48 recipes,
144 recipe/cut cases, 720 fresh guest processes and 288 fresh restores**.
The native tier executes **37,412,496 instructions with zero fallback**;
the separate interpreted tier executes **37,412,496 instructions**. Original
Gear retires 36,955,404 instructions through 46,717,884 CPU calls; 9,762,480
extra continuation calls are not opcodes. Actual hardware callbacks number
46,818,564. Of 2,800 compiled identities, 2,792 execute; eight terminal BRA
self-loops remain compiled but unretired.

The run freshly compiles 40 reference objects: 39 original/dependency objects
and one authored observer. It rehashes 130 original Git blobs and 3,399 artifact
bindings. Frozen standalone admission passes, including **11 written altered
receipt refusals**. The ledger preserves 2,437 raw differences across every
one of the 144 cases. Passing functional and continuation checks is not full
cross-core timing agreement or hardware qualification.

A separate raw callback audit checks both HALF/END assertions, first grants
and source/IRQ chronology in all 144 original target groups. **36 fast scalar
groups assert during three-tick dynamic waits; 36 fast TAI groups assert during
ordinary 42-tick startup callbacks; 72 slow groups already have IRQ2 pending
before the target.** Every IRQ1 source is already pending before target entry.
The first read grant sees both requests/sample bits; TAI delivery occurs only
in completed call 4. Startup is not a wait. An earlier overbroad working audit
was rejected and retained; its corrected three-class receipt is separate.
Native aggregate entry/retirement records do not supply device-edge timestamps.

The three exact-build cuts precede ADPCM DMA arming, follow IRQ1 entry, and
follow real guest acknowledgement/masking before PLA/RTI. Restores import
raw core-codec bytes and preserve suffix source/state records and complete
canonical endpoint hashes. These probe files are not the desktop host's
fingerprint wrapper. The actual host-backed retail check below remains a
different checkpoint contract.

Fresh SDL Release configure/build and the required checker all exit 0:
**1,402 Python tests without skips, 65 C++ suites and 12 fresh-process audio
checkpoint cases**. Twenty new Python tests include a required six-recipe
native/interpreted checkpoint smoke with 24 actual child processes. The live
authored SDL fixture again preserves 152 pending PCM frames, four strict paused
pairs, 37 request/reply pairs and complete checkpoint round-trip/continued
endpoint bytes. Runtime/compiler inputs remain 79 files, SHA256
`d17bdc9159b53b00144a388ebe45a6f7e5e7c5767b7de1989df0e50db24e213c`;
diagnostic sources are separately bound. ABI 26/checkpoint schema 1 are unchanged.

The new Ys III test uses frozen `40f44c8` client/reader helpers and the retained
`d102ecb80664ea45bada4036da46b466339daf09` consumer, not a rebuilt retail
module. It adds **144 ordinary-input frames**, 27,095→27,239, with a new
checkpoint at 27,143 and two fresh 96-frame suffixes. The inventory stays
visible and HP remains 11. No activation button, assist, memory write, capture
or WAV is used, and no owner/peer files are modified.

Actual new work is **3,900,861 native/18 interpreted instructions**; each suffix
executes **2,599,983 native/12 interpreted**, separate from the imported
793,539,726 native/72 interpreted prefix. All three complete 2,692,138-byte
endpoint files and 2,691,918-byte core payloads match byte for byte. A queued
write remains present at origin/cut/end, read pending is false, delay/carry
zero; the whole interval executes 27,942 new VRAM wait ticks.

There are 239 exact paused pairs, 425 additional **overlapping** automatic guards,
264 continued comparisons and 711 raw origin equations. Journals retain 2,645
records/1,321 request-reply pairs. New CD READ, ADPCM DMA and decoded ADPCM counts
are zero; 180 CDDA sectors produce 106,148 PCM frames. Unknown `$FF` acceptance
stays four under explicit `gear-good`. No per-direction latch, combat, listening,
campaign or migration result is inferred. All three owned hosts exit naturally
with code 0. PID-aware cleanup admission distinguishes unrelated Windows PID
reuse; the earlier PID-only audit and corrected 568-binding epoch stay separate.

## Profile-bound consumer builds — ABI 26

Consumer schema 1 now accepts optional `[module.observation_profile]` with
`path` and `sha256`. The verifier admits the exact bounded profile file once,
then checks original input provenance, historical totals and native/unsupported/
excluded source-selection counts against the hash-pinned module manifest.
Build/run receipts retain `module_observation_profile`; it is not a runtime
asset or guest argument. Strict manifest parsing also refuses duplicate keys
and nonfinite numeric tokens. Existing unbound descriptors stay supported.

Managed builds copy the raw profile under a fixed owned filename, normalize
the copied descriptor, archive exact bytes per generation and bind the profile
as a mutable module/cache input. Unchanged bytes retain their timestamp.
Tampering with the live profile or active generation's archived copy blocks
reuse. A bound workspace cannot accept an unbound update; weakening that
contract requires a new workspace. Candidate admission precedes output mutation.
No additional compiler search root is authorized by a profile's location.

Adding the optional binding changes the exact consumer checkpoint context,
even when C++ bytes are unchanged. It requires a fresh cold run and new
checkpoints. Runtime/CMake bytes, runtime ABI 26 and checkpoint schema 1 stay
unchanged. These checks bind provenance and selection facts to separately
hash-pinned source; they do not authenticate historical execution or re-prove
C++ derivation. See [the consumer contract](OBSERVATION_PROFILES.md#bind-the-profile-to-a-consumer-build).

Frozen implementation `40f44c843e29c72a39dc982ed59a2af2e7de5e6b` has 79 relevant
source files, SHA256
`d17bdc9159b53b00144a388ebe45a6f7e5e7c5767b7de1989df0e50db24e213c`.
Twenty-two new authored tests cover consumer admission, single-pass loading,
managed ownership and actual build/run behavior. Independent frozen review
also rejects 22 altered admission cases and checks 11 managed ownership/history
conditions. The earlier source-race refusal and superseded initial freeze
remain separate records; they are not successful final verification.

The final frozen SDL Release configure/build and required checker all exit 0:
**1,382 Python tests without skips, 65 C++ suites and 12 fresh-process audio
checkpoint cases**. The live authored SDL fixture again preserves 152 pending
PCM frames, four strict paused pairs, 37 raw request/reply pairs and complete
checkpoint round-trip/continued endpoint file bytes. Root closeout rehashes
1,012 retained bindings. A separate controlled post-admission profile change
is refused during final input binding, before returning a verified consumer
or starting a host.

A retained frozen native test creates, promotes and no-ops a managed workspace.
Two actual cold runs execute **101 native/99 interpreted**, then **200 native/
zero interpreted** instructions after promotion. Both independently check
X=106, PC=$4100, 600 cycles and 1,800 ticks. There is no imported work. Promotion
rebuilds one source-part object; the no-op preserves all 29 object hashes and
timestamps. Exact profiles, immutable generation history, actual build/run
receipts and captures are retained: 52 artifacts and 87 object bindings. An
actual corrupt candidate is refused with the workspace unchanged. A separate
ordinary consumer fixture compiles and runs six native instructions with zero
fallback, retains its external profile in build/run receipts, and refuses
post-build profile tampering before execution.

Fresh final-source emission of the retained 57,568-identity catalogue matches
all 945 prior C++/header/manifest files byte for byte. Composition and validation
functions remain unchanged apart from the additive details-loader interface;
the emitter itself is unchanged. This is emission conservation, not a new
retail module build or execution. The optional binding adds no new Geargrafx,
Ys III TCP, campaign, listening or cross-build checkpoint claim. The consumer
project continues its separately pinned migration gate without being forced
to adopt this feature.

## Mixed-ABI observation profiles — ABI 26

Production `compose-observations` and `emit-profile` now compose supported
original ABI epochs without relabeling them. Profiles embed exact raw capture
bytes with SHA256/size and reconstruct every full PC/MPR/source identity,
per-input contribution and historical total on admission. Original checkpoint
origins remain per-input; there is no aggregate capture ABI or checkpoint.
Only complete lossless inputs admit. Capacity, contribution, byte and U64
limits refuse excess rather than discard observations. Exact duplicate raw
inputs count once; overlapping events across distinct inputs are not inferred.
See [the versioned contract](OBSERVATION_PROFILES.md).

Frozen implementation `42910a2a9fdffb978d5eaafa713edc7dbd7ccc9f` adds 33 authored
tests across strict composition, CLI preservation and shared emission. A fresh
authored mixed-18/26 C++ module executes all five supported identities,
**five native instructions and zero interpreted**, with independent expected
register/guard checks, 12 cycles and 36 ticks. The unsupported identity remains
a native miss. The opt-in span path is compiled in this test, not executed.
Separate frozen-source review passes 25 altered-profile refusals and six
legacy-emission configurations with 25 byte-identical C++/header pairs and
unchanged manifest semantics. Actual production consumer descriptor admission
also accepts the new manifest and pins its generated code artifacts.

The source identity is 79 relevant files, SHA256
`510ad0dc3b2ee48bf216438ea42aeae0aaf80601f0af3885c7f878a00cc52765`.
Runtime/CMake bytes, runtime ABI 26 and checkpoint schema 1 remain unchanged.
An earlier CRLF working-source proof stays separate from the canonical LF
Git freeze; fresh frozen imports repeat the admissions and output comparison.

Its fresh SDL Release configure/build and required `scripts/check.py` all
exit 0: **1,360 Python tests without skips, 65 C++ suites and 12 fresh-process
audio checkpoint cases**. The live authored SDL fixture retains 152 pending
PCM frames, four strict paused pairs and 37 raw request/reply pairs, plus
complete round-trip and continued endpoint checkpoint bytes after a fresh
restore. The root closeout rehashes 3,828 retained bindings. These authored
host checks remain separate from the retail consumer composition below.

Private consumer-input qualification combines original ABI18 and ABI26 files:
57,545 and 39,222 identities intersect at 39,199, yielding **57,568**, preserving
every older key plus 23 additions. Those additions retain their 25 original
interpreted input hits; composition does not promote them into native execution.
The 70,364,221-byte profile is deterministic under reversed input order and
rehashes original bytes unchanged. All 57,568 identities emit under ABI26.
Stable emission changes four existing source buckets; 940 source/header files
remain byte-identical, with no new bucket. Regenerating the old catalogue
also preserves all 943 prior C++ files. Frozen output comparison joins 1,891
profile/generated-source/header/manifest files exactly across source epochs.

These consumer checks compose and emit; they do not compile or run a new game
module. Historical input sums include a preexisting catalogue and are not one
verified execution window. No new Geargrafx, retail TCP, campaign, listening,
checkpoint conversion or ABI migration result is inferred. The Ys III project
is coordinating its separate cold-build and exact-module route qualification.
Original captures, profile, generated game code and receipts remain private;
no peer checkout or owner files were modified by this batch.

## Periodic horizontal-sync phase coverage — ABI 26

The separate `blank-periodic-hsw-read-v1` diagnostic now predicts the selected
horizontal-sync guard, even-slot parity and scanline wrap. Its inputs include
actual pre-grant Hstate/countdown, HSYNC anchor and latched horizontal lengths;
live registers are retained separately. The old no-HSW function and its API
remain unchanged. No runtime, emitter, ABI 26 or checkpoint-field change occurs.

Frozen code `d62fbe33190ff22d7c7334c8756d84a1709a1436` passes **72 recipes across
216 fresh guest processes and 216 exact HSW-profile predictions**. It preserves
48 baseline recipes and adds 24 sync-start/tail edges selected from guest TII
cycle arithmetic before execution. Edge ROM/source-plan hashes remain identical
to that pre-execution design. Native CSH's real 18-tick origin difference stays
in the records; phases and inputs are not adjusted to obtain agreement.

Its fresh SDL Release build and required `scripts/check.py` both exit 0:
**1,327 Python tests without skips, 65 C++ suites and 12 fresh-process audio
checkpoint cases**. The live authored SDL fixture again preserves 152 pending
PCM frames, four strict paused pairs, 37 raw request/reply pairs and complete
round-trip/continued endpoint file bytes after a fresh restore. Runtime/compiler
inputs remain 78 files, SHA256
`6fd2b045fc235d4c26c8ad2a11683ea871adf03d43f631debcbd4df4ced30f48`;
diagnostic sources are separately hash-bound.

Native and separate interpreter tiers each execute **7,932 instructions**,
636 blocks and 1,763,112 block bytes, with zero native fallback. Original Gear
retires 7,932 instructions through 1,771,680 actual calls; 1,763,748 continuation
calls are not guest opcodes. All logical CPU, source, full WRAM/VRAM and actual
latch checks pass. Of 372 compiled identities, 362 execute; ten terminal BRA
variants are compiled but unretired. The legacy model separately admits 166
observations and truthfully refuses 50 with HSW interference.

Gear's 72 original ledgers join 226 actual candidate callbacks, including 88
HSW-blocked candidates, 66 parity-only holds and eight pre-HDS grants whose
future clock wraps into a new line. Native/interpreted candidate positions are
analytical predictions joined to entry/exit state and total waits, not observed
native device callbacks. All guest queue carries are zero; carry one/two tests
are pure arithmetic vectors. Arbitrary geometry, active-display arbitration and
hardware/sub-three-tick accuracy remain outside this profile.

Fresh reference builds compile 40 objects (39 original/dependency objects and
one authored observer) and bind 1,134 artifacts and
130 original Git blobs. Standalone and root audits pass, including ten written
altered receipts and a separate missing-raw-VDC-source refusal. Raw/compiled
source preservation and all 24 preselected input designs rehash unchanged.
See [VDC_PHASES.md](VDC_PHASES.md#periodic-horizontal-sync-coverage).

A separate conservation audit joins all 144 fresh baseline reports to the prior
48-recipe epoch after dropping only appended read-only phase/callback fields.
All 48 ROM pairs and 96 capture pairs match byte for byte. The legacy function,
helpers and constants remain source-identical; 1,518 bindings rehash. This is
offline preservation analysis of existing runs, not additional guest execution.

The new Ys III regression is a **64-frame inventory-control variation** from
27,095 to 27,159, with a new checkpoint at 27,119 and two fresh 40-frame
suffixes. This frame range was previously traversed with different controls;
it is new execution/input variation, not new campaign progress. HP stays 11
and inventory remains visible. No activation buttons, assists, memory writes,
WAV or code capture are used, and no owner files are modified.

The retained `d102ecb80664ea45bada4036da46b466339daf09` consumer uses frozen
`266ffccef675fcba98328fbd91b82447381df1ea` client/reader helpers. Actual new
work is **1,734,111 native and 12 interpreted instructions**; each fresh suffix
executes **1,082,802 native and six interpreted**, separate from the imported
793,539,726 native/72 interpreted prefix. All three complete 2,692,138-byte
endpoint files and 2,691,918-byte core payloads match byte for byte.

A queued VDC write is present at origin, new cut and endpoint, with delay/carry
zero; the interval executes 12,423 new wait ticks. This is natural-boundary
queued-work continuation, not a mid-instruction checkpoint. The older API does
not expose per-direction guest input-latch consumption, so accepted controls
are not promoted into a claim that each direction was sampled. There are 139
exact paused pairs, 250 overlapping automatic guards, 136 continued comparisons
and 401 origin equations; 1,825 raw journal records contain 911 request/reply
pairs. Offline admission rehashes 549 bindings. All three hosts quit naturally
with exit 0 and no owned host remains active.

No new CD READ, ADPCM DMA or ADPCM decoded samples occur; 80 CDDA sectors
produce 47,177 PCM frames. Unknown `$FF` acceptance remains four under explicit
`gear-good`. No current-toolkit retail build, cross-context checkpoint import,
combat, listening, hardware or complete-game qualification is inferred.

## VDC phase diagnosis and independent HuCard controls — ABI 26

The selected −6/+3-tick wait differences now have a source-ledger and arithmetic
explanation. Fast entry differs by 18 ticks because of the already documented
CSH rule. Slow entry differs by 780 ticks, exactly five actual command-REQ
polling quartets at 13 cycles and CPU divisor 12. Independent dot-ordinal and
three-tick-slot arithmetic predicts all 144 retained native/original waits.
These are re-read retained observations, not new guest executions or shifted
clock records. Old horizontal entry positions are source-backed projections,
with additional observer runs checking those projections separately.

The new pure `blank-even-no-hsw-v1` diagnostic refuses unsupported state and
requires factual source/countdown/phase/queue inputs plus an independently
established HSW-exclusion predicate. It changes no runtime/emitter semantics,
ABI 26 or checkpoint schema. Fresh authored base-HuCard recipes exclude CD
hardware entirely: 48 recipes execute in each of three tiers; 46 recipes admit
138 exact predictions and two recipes remain six explicit HSW refusal controls.
For the latter, actual reads wait through horizontal clock 21 and grant at 24;
HSW blocks through 18, while odd-dot parity accounts for the hold at 21.
See [VDC_PHASES.md](VDC_PHASES.md) for equations, source identities and limits.

Frozen diagnostic code is `266ffccef675fcba98328fbd91b82447381df1ea`.
Its fresh SDL Release build and required `scripts/check.py` both exit 0:
**1,315 Python tests without skips, 65 C++ suites and 12 fresh-process audio
checkpoint cases**. The live authored SDL test again checks 152 pending PCM
frames, four strict paused pairs and 37 raw wire request/reply pairs; complete
round-trip and continued endpoint file bytes match after a fresh restore.
The runtime/compiler input set remains 78 files, SHA256
`6fd2b045fc235d4c26c8ad2a11683ea871adf03d43f631debcbd4df4ced30f48`;
the new diagnostic sources are separately hash-bound. The fresh reference
executes **5,280 native and 5,280 separately interpreted instructions** with
zero native fallback. Each tier retires 408 blocks/1,171,248 bytes. Gear retires
5,280 instructions through 1,176,936 calls, including 1,171,656 continuations.
Of 282 compiled identities, 276 execute. Standalone and root re-audits pass:
918 bound artifacts, 130 original blobs, 40 reference-build compilations, ten written
altered-receipt refusals and one additional missing-raw-source refusal.

The frozen retained-data audit separately re-admits 144 old waits, 72 original
grant starts and 24 source-origin proofs. Additional read-only observer runs
provide 48 reports/1,128 selected phase rows and exact projection to the older
records; their 690 preserved bindings rehash. These epochs are not counted as
the fresh HuCard matrix or a new retail run. No general HSW solver or hardware
phase accuracy is claimed.

The new private Ys III regression runs **160 ordinary-input frames**,
27,603→27,763, with a new checkpoint at 27,647 and two fresh 116-frame suffixes.
It uses the frozen `5376b9852c71a8f17bf7667a9e7c0027ba2b1459` client/reader with
the same retained `d102ecb80664ea45bada4036da46b466339daf09` consumer. No new
runtime build or cross-build checkpoint import is claimed. Actual new work is
**5,081,894 native and one interpreted instruction**; each restoring suffix
executes **3,685,274 native and one interpreted**, separate from the imported
808,158,756 native/92 interpreted prefix. All three complete endpoint file and
core byte arrays match. The observed HP path is 20→11→2, ending alive; it is no
combat-success or damage-cause oracle, and no further controls are sent.

All three owned hidden/muted processes quit naturally with exit 0. The raw
journals contain 1,925 records/961 request-reply pairs. There are 131 exact
measured paused pairs, 236 **overlapping** automatic guards, 136 continued-status
comparisons and 459 raw origin equations. New CD READ/ADPCM DMA/decode counts
are zero; 201 new CDDA sectors produce 117,942 PCM frames. Unknown `$FF`
acceptance stays four under the explicit `gear-good` policy. No owner file is
modified; no assist, memory write, WAV or code capture is used. Offline admission
rehashes 549 bindings; journal pairing alone does not qualify the run.

## Streaming diagnostics and competing VDC/ADPCM interrupts — ABI 26

The offline [wire-journal reader](PAUSED_OBSERVATIONS.md#reading-a-retained-journal)
streams records with bounded retained state, checks framing, request IDs,
canonical base64, JSON types, EOF identity and optional whole-file SHA256.
It retains negative failure evidence and explicitly distinguishes forensic
prefixes. A paired ledger establishes neither caller admission nor process
success. Twenty-one authored reader tests pass. Investigation also corrected
`DevClient` accepting exponent overflow as infinity; both the client and reader
now refuse it. No runtime, emitter, ABI or checkpoint-format change was needed.

The new required [VDC/ADPCM IRQ suite](VDC_ADPCM_IRQ.md) passes 48 direct cases
and 29,760 checks: 1,224 actual interpreted opcodes, 36 actual TAI retirements,
zero native execution, plus 24 imported prefix opcodes/12 transfers. It checks
real READ-fed ADPCM IRQ2 competing with VDC DMA completion IRQ1 inside a queued
VRAM wait, IRQ1 priority, real status acknowledgement, RTI, and either later
IRQ2 delivery or guest CD masking. Full WRAM/VRAM, stack/register expectations,
provider rebinding, pure saves, transactional refusals and complete serialized
continuations accompany the interrupt checks. Source reasoning bounds assertion
inside the wait; the direct suite records no independent edge callbacks.

Frozen code pin `5376b9852c71a8f17bf7667a9e7c0027ba2b1459` has 78 relevant
source files, SHA256 `6fd2b045fc235d4c26c8ad2a11683ea871adf03d43f631debcbd4df4ced30f48`.
Its fresh SDL Release build and required `scripts/check.py` both exit 0:
**1,295 Python tests without skips, 65 C++ suites and 12 fresh-process audio
checkpoint cases**. Actual native/interpreted work remains scoped by each
suite. The live authored SDL fixture retains 152 pending PCM frames, four exact
paused pairs and 37 raw request/reply pairs. A fresh restore matches complete
checkpoint round-trip and continued endpoint file bytes. The failed PowerShell
stderr-wrapper epoch is preserved separately; the successful direct-process
driver records its actual command, combined output and exit independently.
The autonomous matrix passes **24 recipes, 72 cases, 144 fresh restores and
360 actual guest processes**, plus 40 fresh reference-build compilations. There are
1,807 bound artifacts and 130 original Git blobs; standalone qualification,
ten altered-receipt refusals and a fresh original-source re-audit pass.
It executes **1,264,464 native instructions with zero fallback** and the same
number separately interpreted. Per tier, 456,360 are creating-prefix work and
404,052 belong to each creating/restoring suffix. Original Gear retires
1,105,272 instructions through 11,566,224 CPU calls; 10,460,952 extra continuation
calls are not opcodes. Of 642 compiled identities, 638 execute.

Actual original callbacks witness both sources before the queued read grant;
TAI defers IRQ until its completed fourth call. The native source-before-grant
proof instead uses a real provider witness and a conservative remaining-time
bound; exact native device-edge timestamps are not claimed. Complete encoded
endpoint state **hashes** match fresh same-tier restores; final endpoint files
are not written. Raw differences remain visible in all 72 cases. In particular,
eight recipes/24 cuts retain −6 or +3 master ticks of dynamic-wait difference.
The subsequent phase diagnosis above explains their selected entry origins;
the original raw clocks are preserved and no stall-algorithm defect is inferred.
The [matrix document](VDC_ADPCM_IRQ.md) records the profiles, source review and
remaining active-display/hardware gates.

The new frozen offline reader also re-audits seven selected retained raw-wire
snapshots without contacting a host, including the three new retail journals
below. An earlier failed recorder has a fully paired raw ledger too, providing
a concrete reason not to promote format completeness into test success.

The separate Ys III TCP interval runs **980 new frames**, 26,623→27,603,
with a new checkpoint at 27,095. Actual images show inventory and a return to
the cave; sampled HP changes 11→20 without assigning an item or damage cause.
The new whole interval executes **28,258,771 native and 20 interpreted**
instructions. Each of two fresh 508-frame suffixes executes **14,619,030 native
and 20 interpreted** instructions. The imported 779,899,985 native/72 interpreted
prefix is separate. All three complete 2,692,138-byte endpoint files match
byte for byte (SHA256 `e13006318ad9e8e0aae874ebdcdae9393396a649c516f6bb1ab6080d7d55933e`);
their complete 2,691,918-byte core payloads also match separately.

Actual transport/observation helpers are frozen `e08425ca6c607289a18ee6055999e22d4a7461d5`,
while the consumer remains retained SDK `d102ecb80664ea45bada4036da46b466339daf09`.
This is no freshly rebuilt current-toolkit game or ABI 18 migration claim.
There are 3,877 raw journal records/1,937 request-reply pairs, 275 exact measured
paused pairs, and 465 additional **overlapping** automatic guards; the latter
are not 740 independent cases. The three owned hidden/muted hosts quit naturally
with code 0. No owner install/save, assist, physical write, WAV or code capture
was used. There is no new CD READ sector, ADPCM DMA byte or ADPCM decoded sample
in this retail interval; 1,228 new CDDA sectors produce 722,393 PCM frames.
The explicit `gear-good` unknown-CD policy remains selected, with accepted
unknown `$FF` count unchanged at four. No listening, retail active-DMA IRQ,
hardware, cross-build or complete-game qualification follows from this route.

## Durable observations and block/DMA IRQ edges — ABI 26

`DevClient` now offers exclusive, opt-in raw wire journals. Requests are
flushed/fsynced before sending and replies before decoding or caller
validation. Failures cannot silently lose the received AFTER evidence.
The new paused-status comparator checks every reported field/type except the
transport ID by default. An explicit legacy fresh-muted profile describes
source-backed whole-queue delivery while preserving reported source/device/
synthesis fields; it is never inferred from an ABI number. Runtime semantics,
ABI **26**, checkpoint schema 1 and the existing route projection are unchanged.

Fifteen authored wire tests and twenty observation vectors pass. The separate
live SDL fixture retains **152 pending PCM frames**, checks four exact paused
pairs and **37 raw request/reply pairs**, preserves AFTER evidence despite a
deliberate comparison failure, and reproduces complete checkpoint round-trip
and continuation bytes after a fresh restore. The frozen legacy helper also
accepts **69 durable consumer pairs**, including one observed **12-frame**
delivery and 68 zero deliveries. The earlier failed consumer AFTER is still
missing; its exact delta is not reconstructed. Unreported queue contents and
capture/campaign eligibility remain separate from reported-status relations.

The next authored hardware fixture raises READ-fed ADPCM HALF/END with I
already clear during all five block families. The separate Gear run witnesses
an incomplete continuation cause, with IRQ2 delivered only after the complete
block. **20 recipes, 40 boundary cases and 80 fresh restores** pass, executing
**279,380 native and 279,380 separately interpreted instructions**, zero native
fallback. Per tier, 243,300 belong to creating prefixes and 18,040 to each
uninterrupted/new restoring suffix. Original Gear completes **261,740 guest
instructions through 5,709,420 CPU calls**; its 5,447,680 extra continuation
calls are not opcodes. No mid-block checkpoint interface is claimed.

The auditor checks **13,107,200 ADPCM RAM and 1,638,400 WRAM expected values**,
**1,227 bindings**, **130 original Git blobs**, **200 execution joins and 40
compilation joins**. All **10 altered receipts** are refused. 350 source
identities actually retire; two additional terminal branches are compiled
only. Complete same-tier encoded-state hashes match. **330 tracked raw
scalar/work differences across all 40 cases remain**, including differently
defined callback/continuation and capture/commit counters. The required direct
suite separately passes **30 cases and 6,070 checks**, with **350 interpreted
opcodes, 50 block retirements and zero native opcodes**; ten prefix opcodes/
blocks are imported. Its READ setup is host-supervised.

The retained d102 ABI 26 Ys III TCP regression adds **810 frames** through a
rope bridge/cave image, observing HP 20 to 11 without a damage-cause or quest
claim. **26,177,351 new native instructions and one interpreted instruction**
execute. Each of two fresh 450-frame suffixes adds **14,256,668 native and one
interpreted instruction**; complete endpoint checkpoint/core bytes match.
It adds no CD READ/DMA/ADPCM decoding in this interval. Conditional unknown
`$FF` handling remains, increasing three to four. This is the retained
consumer, not a new runtime build or ABI 18 migration. Owner files stay isolated.

Frozen implementation `e08425ca6c607289a18ee6055999e22d4a7461d5` has **78**
relevant source files and SHA
`d9f23444a23ea1d713697ebbef2856dfa2ba80941c6e9aff6b22066d02be3f00`.
The fresh Release SDL build passes the full required check: **1,261 Python
tests without skips, 64 C++ suites and 12 fresh-process audio checkpoint
cases**. A separate read-only retained-game host executes the new frozen
client: **44 request/reply pairs**, one strict paused pair and zero guest
advancement, with source/WRAM/screenshot readbacks matching its checkpoint.
See [paused observations](PAUSED_OBSERVATIONS.md) and
[block/DMA IRQ qualification](BLOCK_DMA_IRQ.md) for exact interfaces, raw
differences, source/consumer scope and reproduction.

## Autonomous CD DMA and CPU IRQ continuation — ABI 26

Authored guest programs now qualify READ handshakes, ADPCM DMA and actual
IRQ2 entry/handler/RTI together. The frozen reference passes **20 recipes,
40 boundary cases and 80 fresh restores**. It executes **9,771,064 native
and 9,771,064 separately interpreted instructions**, with zero native fallback;
original Gear executes **9,735,052 actual CPU instructions/calls and hardware
callbacks**. Each toolkit tier counts 9,322,784 creating-prefix instructions,
224,140 uninterrupted-suffix instructions and 224,140 new restoring-suffix
instructions. Imported prefix work is not replayed.

The audit checks **13,107,200 independently expected RAM byte values**,
**1,226 artifact bindings**, **130 original Git blobs**, **200 execution joins**
and **40 compilation joins**. All **10 altered receipts** are refused.
348 native source identities actually retire; two more terminal branches are
compiled only. Completed handler-entry checkpoints retain the real stack;
they do not expose halfway-completed interrupt pushes. Full same-tier encoded
state hashes match after fresh restoration.

**484 tracked raw scalar/work differences across all 40 cases remain visible.**
They include clocks, polling work and transient device state, plus differently
defined original callback and DMA-commit counters. The toolkit counts DMA
captures. These are distinct measurements, not 484 demonstrated runtime bugs.
Original selected CPU/CD/ADPCM/SCSI blobs match current upstream; electrical
bus phases and hardware accuracy remain unqualified. The separate direct
suite passes **20 cases and 7,148 checks**, executing **410 interpreted
opcodes, zero native opcodes**, with 150 imported prefix opcodes. Its device
setup is host-supervised; it is not the autonomous original-core proof.

The retained d102 ABI 26 Ys III TCP regression adds **1,054 frames**, reaching
the visible Sarina map and an outdoor path. It executes **32,548,213 new native
instructions and one interpreted instruction**, transferring 96 CD sectors
and 131,072 ADPCM DMA bytes, with no newly decoded ADPCM samples. Uninterrupted
and two fresh 394-frame restoring suffixes produce byte-identical complete
endpoint files/core payloads. Each restoring suffix adds **12,478,595 native
instructions with zero fallback**. Both retail checkpoint boundaries have
inactive DMA; a pending CDDA sector deadline continues identically. This uses
the retained consumer, not a new toolkit consumer build, and accepts one
additional unknown `$FF` under explicit `gear-good` policy. Owner packages and
saves remain untouched; no migration, campaign or listening parity is claimed.

Frozen implementation `485af70b3c0f10d95dfeb82e75fdefbf625883ab`, ABI **26**,
has **78** relevant source files and SHA
`d25aea1cbc26903481a500ce3533782e80643e761cf9b9c63aaad3f50618e002`.
The fresh Release SDL build passes the complete required check: **1,212 Python
tests without skips, 63 C++ suites and 12 fresh-process audio cases**.
Runtime/emitter semantics and checkpoint schema 1 are unchanged. See
[guest-driven DMA/IRQ checkpoints](DMA_IRQ_CHECKPOINTS.md) for source pins,
complete work counts, retained failures, reproduction and scope.

## Coupled CD/ADPCM DMA continuation — ABI 26

Authored READ commands now qualify checkpoints across the coupled transport,
DMA capture, ADPCM write-latch/RAM commit and ACK path. The reference matrix
passes **32 cases and 64 fresh restores**, with **2,092 actual native and 2,092
separately interpreted retirements**, zero native fallback, and nine actual
port-source identities. Device DMA work is counted separately from guest
instructions. Original Gear uses actual Standard CD hardware setup and
register/device execution with **zero guest CPU calls**.

The audit verifies **10,488,480 independently expected RAM/reply/end-IRQ
values**, **1,182 artifact bindings**, **130 original Git blobs** and **160
execution joins**; all **10 altered receipts** are refused. The original
adapter records **4,277,838 one-master-tick hardware-clock calls**. Its coarse
waits have separate safety/purity checks. **54 raw clock/state differences**
across 28 cases remain explicit; functional agreement does not establish
clock, electrical bus-phase or hardware parity. The separate direct suite
passes **7,343,716 expectations across 60 cases**, with zero guest retirements
and device IRQ-line scope only.

The private retained ABI 26 consumer extends its street regression by 1,024
frames. Each fresh restoring suffix retires **9,732,834 new native and 5
interpreted instructions**, transferring **65,536 DMA bytes from 32 CD
sectors** and continuing **65,350 ADPCM samples**. Uninterrupted and two
restored endpoint checkpoint files are byte-identical, including complete
machine/ADPCM RAM/PCM payloads. Neither retail checkpoint is mid-DMA; the
authored matrix supplies that boundary evidence. Owner saves/packages remain
untouched and full ABI 26 migration remains unqualified.

Fresh frozen implementation `43ebd1cdf875e004f17c090c12d26f2a9517cc59`, ABI
**26**, has **78** relevant files and SHA
`bf024e586702e159c7ba353c2faf7df266414ebeb6c659ecce3d51922092898b`.
Its fresh Release build passes the complete required check: **1,200 Python
tests without skips, 62 C++ suites and 12 fresh-process audio cases**.
Runtime/emitter semantics and checkpoint schema 1 are unchanged. See
[coupled CD/ADPCM checkpoints](CD_ADPCM_CHECKPOINTS.md) for raw differences,
failed adapter epochs, exact work and scope.

## Active CD READ checkpoint continuation — ABI 26

The new authored CD READ pipeline checkpoints real host-supervised guest port
operations at partial-command, pending-load, ACK, buffer, retry, reset and
reselection boundaries. A separate original Gear core supplies live cut and
payload/status/message observations. Across **32 cases**, the toolkit retires
**443,710 native instructions and 443,710 separately interpreted instructions**,
including **64 fresh restoring processes**. Gear executes register/device code
with **zero guest CPU calls**. This does not establish cross-core CPU or bus
timing parity. Six port sites actually retire; six compiled terminating branch
loops remain compilation-only evidence.

The auditor verifies **1,182 artifact bindings**, **130 original Git blobs** and
**160 execution joins**. Independent expected data and cut-state/deadline fields
complement fresh-process full-state continuation. A separate direct-device
suite passes **616,524 expectations across 40 cases**, including partial CDB
ACK/REQ and STATUS/MESSAGE/bus-release edges, with **zero guest retirements**.
Save/load invokes no sector-provider reads; restoration rebinds the provider
created by normal media setup. Invalid checkpoint copies leave the live
machine unchanged.

The retained earlier ABI 26 consumer has a new exact-build street checkpoint.
One uninterrupted path and two fresh restores match through frame **23,735**;
each restored 424-frame suffix executes **13,546,923 new native instructions
and 36 interpreted instructions**, separate from its imported prefix. Guest
state/source, device/PCM status, work RAM and pixels match. These ordinary-input
tests leave owner saves and the selected consumer package untouched. The earlier
diagnostic executable is not relabeled as a new toolkit build, and full ABI 26
migration remains unqualified. See [CD READ checkpoints](CD_READ_CHECKPOINTS.md).

Fresh reference/native builds use frozen implementation
`235b7ee74c2eb8585396c971e165327ec0d4aa0e`. Test-only follow-up
`b2f45bef5545e2926080a44cc24874c36fa8e5ee` corrects the runner's expected suite
count. It passes the complete required `python scripts/check.py`: **1,194 Python
tests without skips, 61 C++ suites and 12 fresh-process audio cases**, using
the implementation's native binaries with byte-identical native sources and
CMake inputs. Both pins share the **78-file** relevant-code SHA
`8b83f573f36dc00e3e84cf81302854d9ba7eafdcdc3389f6fecd2e6bbbc1ce0f`.
The earlier full run's stale-count failure remains a failed epoch. No runtime
implementation, generated instruction semantics, ABI 26 or checkpoint schema 1
was changed.

## State-aware TCP routes and bounded migration investigation — ABI 26

The standard-library `scripts/dev_route.py` runner validates a complete finite
plan and preflights all planned status paths/types and physical reads before
mutating input. Typed status, masked/exact memory, unsigned memory ranges and
complete PC/eight-MPR/fetched-byte identities support assertions and bounded
waits. An initially satisfied wait performs zero input changes and zero frame
advances. Scoped input cleanup runs on success/failure; receipts preserve raw
before/after observations and accepted intent separately from guest latch
sampling. Quiescence ignores only response IDs and the exact SDL audio
presentation subtree, retaining all guest PCM/device/source state comparisons.
See [state-aware routes](STATE_ROUTES.md).

The same ABI 26 `d102` consumer misses historical intents 97..99 with queued
VDC timing before assistance; an immediate-only control exits. A private
state-aware Right 59 / Up 112 / neutral 120 sequence repeated three times
reaches frame 22,861 with **8,391,320 new native / 9 interpreted instructions**.
Historical intent 100 then reaches the street and Tigre Mine dialogue at frame
23,311; the complete suffix executes **22,568,899 new native / 14 interpreted
instructions**. This is a bounded route investigation, not a runtime/hardware
defect finding or full migration qualification. The owner's selected ABI 18
package remains unchanged. No title addresses are public and ABI 26 is unchanged.

Separate original-Gear input checks cover **24 authored cases**, **4,096 Gear
CPU calls**, **4,096 native** and **4,096 separately interpreted retirements**,
**453 source identities**, **348,672 literal checks** and **72 execution joins**.
They qualify held-intent/guest-latch phases, not retail polling, VDC stalls or
hardware input timing. Fresh original-Gear and toolkit execution from frozen
implementation `60affdef59e3ce4bf4d02f1d17feadcc37bc3349` passes. Its separate
auditor verifies **773 artifact bindings and 130 original Git blobs**, and
refuses **12 written altered receipts**. The fresh frozen Release build passes
the required `python scripts/check.py`: **1,188 Python tests without skips,
60 C++ suites and 12 fresh-process audio cases**, including both SDL suites.
The 78-file relevant-code SHA remains
`e2c412f28a60fc1acb66ca20e9d6cc573b60fb164cd8c78e5b1771fe2b3e4862`.
The retail route uses the earlier bound diagnostic executable, with identical
new route-client bytes; it is not a new consumer build from the frozen pin.

## Matched PSG domains and filtered checkpoints — ABI 26

All 144 later values retained by the previous guest PSG probe are exactly
explained by comparing Gear's post-HPF output with raw toolkit PCM. An
independent requalification derives all 32 integer gain levels with Decimal
arithmetic, rehashes the actual 216 retained stdout files and predicts all
864 scalar observations. The source gain and existing filtered path require
no runtime change. Prior raw evidence remains intact; it is not rewritten to
pretend the signal domains were identical.

The reusable `pcerecomp.audio_trace` module and CLI validate explicit source/
filter/mix/resampling domains and refuse incompatible comparisons. New
original-Gear guest probes retain pre-half channel sums, actual HPF frames
and separate actual native/interpreted raw and filtered outputs. Full source
identity, clocks, work counts and source/trace associations stay explicit.
See [AUDIO_TRACES.md](AUDIO_TRACES.md).

Authored equations extend gain/DAC/balance coverage, source mode edges,
binary32 histories, rational FIR expectations and fresh-process audio-payload
continuation. The first toolkit source sum remains independently expected
because there is no observer inside the instruction; all actual output frames
and later held sums are observed. Reference disagreements on noise, LFO and
reset behavior remain separate from this declared digital profile.

Runtime ABI **26**, generated operations, defaults and checkpoint payload
schema **1** are unchanged. A changed reviewed build/profile still requires
new exact-build checkpoints. Filtered 48 kHz retail qualification uses its
own fresh baseline, never the old raw PCM or Gear's different output pipeline.

Frozen implementation `2058923b54e3d83b59b3fcb50a542ceda5d2951c` has canonical
SHA-256 `e2c412f28a60fc1acb66ca20e9d6cc573b60fb164cd8c78e5b1771fe2b3e4862`
over **78 relevant source files**, ABI **26**. The audit-only follow-up
`8cedfacb11e0982770de75f4026c081e0bd7d31c` additionally requires the exact
toolkit revision, not merely its source digest and file count. Both revisions
share the relevant-code identity; the original frozen execution is preserved.

The clean audit-follow-up checkout passes the full required
`python scripts/check.py`: **1,154 Python tests without skips, 60 C++ suites**,
including both SDL dummy-host suites, and the **12 fresh-process audio
checkpoint cases**. Its native binaries were built from the relevant-code-
identical frozen implementation. No test or runtime retry is introduced.
The separately reported consumer SDK cache-publication `WinError 5` remains
unresolved: focused unchanged diagnostics and this full run pass, while the
failed SDK epochs remain failed. See [cache boundaries](BUILD_CACHE.md#boundaries).

The direct authored suite passes **3,151,387 checks**, including **3,145,728**
DAC/volume/stereo-balance cases across all six channels and both centered and
unipolar profiles. Decimal-derived gains, wave/DDA/noise/LFO edges, odd halves,
unclipped HPF history and long decay have independent expected values. Six
complete 256-source-frame signals cover raw, filtered 44.1 kHz and filtered
48 kHz, the latter using independent direct-convolution expectations. Twenty-
eight fresh-machine continuations cover all six PSG divider residues. A writer
and a fresh restorer additionally exercise **12 audio-payload cases**, with
actual truncated-copy and duplicate-write refusals. These device fixtures
retire **zero guest instructions**.

The new independent guest pipeline executes **72 original Gear cases** with
**2,048 source frames each**, four 512-frame drains, **144 actual native and
144 interpreted toolkit retirements**, **152 original CPU microstep calls**
and **112 original PSG writes**. There are **2,948,544 independent scalar
checks**, including **1,179,648 actual toolkit PCM values**. All matched raw
and filtered 44.1 kHz values agree. The audit verifies **1,706 bindings**,
**130 original Git blobs**, **360 actual stdout/execution joins** and **432
domain traces**. The strengthened auditor requalifies the preserved execution
and refuses **23 written changed-copy controls**, including a relabeled tool
revision. That follow-up is an audit, not new emulator execution.

A fresh direct-source Gear comparison also passes **3,262 authored plans**,
**187,126 plan operations**, **49,258 stereo/phase records** and **492,580
scalar comparisons**. Raw stereo values, all six waveform indices and both
noise seeds match exactly. Its device-clock adapter executes **zero guest
instructions**; it does not establish CPU bus timing or filtered/FIR parity.

The fresh official ordinary, non-cache SDL consumer reuses the immutable
**846 ABI 26 translation units**, originally emitted from the actual ABI 24
capture. No capture is regenerated or relabeled as new discovery. Explicit
`filtered` / `48000` / `gear` settings bind the new recipe. Authentic reset
with blank volatile BRAM reaches frame **26,751**, **9,603,475,248 ticks** and
**791,721,517 native / zero interpreted** instructions. Two fresh restores
each execute **48,335,394 new native / zero interpreted instructions, zero
guard misses**, through death/retry and movement to frame **28,285**.

All **11 paused states**, **10,230 complete source identities and hit counts**,
RGB/window RGB, WRAM, source PCM, filter/FIR history and complete canonical
CPU/device/audio state match the uninterrupted filtered run. Current images
show GAME OVER, HP recovery and subsequent hero movement. The old ABI 26
checkpoint is refused for binary/module/source/media/profile identity,
without canonical-payload mutation. Duplicate save refusal is also pure.
All three owned hosts exit naturally with code zero, loaded adjacent SDL with
SDK directories absent, and leave no owned processes. No owner install,
save, launcher selection, memory assist or local input is used.
PCM evidence consists of matching rolling hashes and complete pending queue/
DSP state; this run records no retail WAV and makes no listening claim.

A separate read-only comparison checks the old raw baseline against the new
filtered run's **raw-source projection** at all 11 aligned states. Source
frame counts, raw hashes/peaks/nonzero counts, all source activity counters,
guest clocks/state, WRAM, pixels and complete source-hit windows agree; 59
runtime/compiler source files are byte-identical. At the endpoint the raw
projection has **20,849,902 frames**, while the processed 48 kHz stream has
**22,693,770 frames**. All processed hashes differ from raw, as expected.
This is internal cross-profile continuity, not Gear retail or listening parity.
The explicit unknown-CD `gear-good` response remains required. Hardware,
analog, 48 kHz Gear, campaign and portable checkpoint coverage remain outside
this qualification.

## Guest audio write phases and CD end changes — ABI 26

Guest PSG writes now advance their remaining instruction base clocks before
the register update. Stores, memory RMW/TRB/TSB and all five block transfers
use the timed helper in generated code and the interpreter. VDC source waits
remain separately charged; IRQ sampling advances with clocks while delivery
retains the normal retirement boundary. Immediate supervisor APIs remain
available. Old generated modules require re-emission, not edited assertions.

Admitted D9 end changes preserve the current CDDA sector's remaining source
frames, including a rounded final-frame token, before LOOP/IRQ/STOP. Authored
ramps and checkpoint tests exercise source order, paused continuation and
output-off/raw/filtered paths. Both defects have actual retained failing runs
against the preceding runtime. Independent original Gear execution and finite
retail regressions have separate scopes. See [AUDIO_BUS_TIMING.md](AUDIO_BUS_TIMING.md).

ABI 26, original-labeled historical capture regeneration, old-module refusal
and fresh exact-build checkpoints are the current consumer contract. Payload,
capture and descriptor schemas remain 1; no cross-build state migration is
implemented. Earlier measured batches below retain their original identities.

Frozen implementation `19b6c44d9237501d29750a274362d5872bf3c738` has canonical
SHA-256 `23cf3102627c92f2e957017b5a2a2a993c4543b7fb695a03db53cb793acc1e6c`
over **77 relevant source files**, ABI **26**. Later documentation closeout
preserves that relevant-code identity.

The full required `python scripts/check.py` run passes **1,119 Python tests
without skips and 59 C++ suites**, including both SDL dummy-host suites.
The clean test-only follow-up `616c95fbf1351818e8ce3f3e76a853d49982e5d1`
corrects an older reset-promotion assertion to recognize the new timed-write
API; its 77-file relevant-code identity matches the frozen implementation
and native binaries. Earlier failed test output remains private and intact.

The authored PSG suite passes **721 checks** across **36 complete source
identities**, with **82 native and 82 interpreted retirements** including
checkpoint branches and block IRQ controls. It checks mapped aliases,
ordinary RAM/non-PSG I/O, all five transfers with RAM and VDC read sources,
fixed wait preservation and deferred IRQ delivery. The direct CD suite passes
**14,638 checks** across end-before/current/future controls, paused remainders,
the rounded final-frame token, explicit stop/reseek cancellation and complete
checkpoint continuation with output off, raw and filtered 44.1/48 kHz.

Separately compiled original Gear executes **72 PSG CPU cases**: 36 source
identities at both divisors, with **72 native / zero interpreted** toolkit
retirements and a separate equal interpreter run. Original Gear records
**152 CPU microstep calls and 112 actual PSG writes**. Complete PC/MPR/physical
source bytes, completed clocks, final PC/DDA and the first stereo PCM boundary
match after the toolkit's documented mixer gain. **144 later PCM values
differ** and remain raw; full synthesis parity is not claimed. The functional
VDC source fixture explicitly seeds READ_BUFFER zero in both engines, rather
than claiming reset-value parity. The audit rehashes **984 bindings**, all
**130 original Git blobs** and 216 stdout/case associations. Nine written
changed-copy controls are refused. Actual old-runtime native/interpreted
executions reproduce the early-write defect across all 72 cases.

The independent CD end matrix executes **72 original device cases** with
**731,340 native / zero interpreted** toolkit retirements, plus equal separate
interpreter work. Original Gear's **731,340 port calls are device operations,
not CPU retirements**. There are **2,814,480 literal source/latch/control
checks**. All seven PC/full-MPR/physical/fetched-byte identities have
independently predicted hit counts. At divisor 3, playing IRQ/STOP admissions
retain 278/270 samples of the current sector; at divisor 12 they retain
275/266. Paused admission retains all 588. Seek and source-admission clocks
remain engine-specific raw evidence. No actual guest case produced a rounded
terminal-tail callback; the direct device fixture covers that boundary
separately. The audit checks **481 bindings**, **130 original Git blobs** and
actual stdout/execution/capture joins, and refuses **49 written changed-copy
admissions**. An old-runtime guest-port execution independently reproduces
the first shortened-end sample failure.

A fresh official ABI 26 SDL consumer regenerates the retained, originally
ABI 24 death-route capture (**44,412 observations**, **846 translation units**).
This is regeneration of actual historical observations, not fresh discovery
or relabeled capture evidence. The new build boots from authentic System Card
reset with blank volatile BRAM and reaches a new checkpoint at frame
**26,751**, **9,603,475,248 ticks**, **791,721,517 native / zero interpreted**.
Two fresh processes each restore that exact checkpoint and execute
**48,335,394 new native / zero interpreted instructions, with zero guard
misses**, through natural death/retry and movement at frame **28,285**.
Imported prefix work remains separate; final lifetime native work is
**840,056,911**.

All **11 paused observations**, **10,230 complete fetched-byte source
identities**, guest/window RGB, full WRAM, digital PCM state and complete
canonical CPU/device/audio/DSP payload match the uninterrupted run. All three
written endpoint checkpoint files are byte-identical. Current PNGs visibly
show GAME OVER, restored HP and subsequent hero movement; read-only retained
field observations show HP 4 → 0 → 20. Inputs use ordinary Run/retry and Right,
with no memory assists or owner save access. The explicit `gear-good`
unknown-CD response profile remains necessary. Hybrid mode is configured;
actual fallback on this finite route is zero.

The old ABI 25 checkpoint copy and duplicate save are refused without guest
or canonical-payload mutation. SDK-free child startup loads the bound adjacent
SDL DLL. All three owned hosts exit naturally with code zero and closed
supervisor threads. The audit rechecks 869 preparation bindings and nine
imported supervisor/TCP bindings. Mutable peer launcher selections are
observed separately, never restored or frozen. No retail WAV-byte, listening,
independent retail Gear equality, campaign or checkpoint portability claim
is made. The Ys III project's independently selected package remains its
own qualification epoch.

## CD audio gap admission and VDC checkpoint boundaries — ABI 25

Known in-range non-program positions now leave the CD audio/head/source
timeline intact when D8 requests a new start. The controller retains the
selected reference profile's GOOD/BUSY decision, including a BUSY request with
no new seek event. Unknown metadata retains its declared approximation;
program data remains admissible, and strict leadout handling remains distinct
from original Gear. ABI 25 and checkpoint schema are unchanged. See
[CD_AUDIO_GAPS.md](CD_AUDIO_GAPS.md).

The existing VDC CR/MWR policies already matched the pinned source. New
checkpoint fixtures exercise live writes and pending read/write/dual queues
around HDS, VSW, VSync and frame burst decisions. Direct device clocks and
fresh-process state continuity are separate from guest opcode timing; raw
unused-buffer differences in supplemental burst cases remain explicit. See
[VDC_LATCH_CHECKPOINTS.md](VDC_LATCH_CHECKPOINTS.md).

The original-Gear checkpoint adapter now rehashes every required raw/source/
binary/artifact binding and matches admissions to their actual journal,
stdout and captures. Earlier evidence is preserved; focused requalification
and changed-copy refusal controls are distinct from new emulator execution.

Frozen implementation `687797ec054476d85c9bbc08ae2e1c4576cd9a22` has canonical
SHA-256 `0eefbbde35b8fd8a2eac852eb899db46f61bef0d0efc97f9fb3e1fc2d3c93bf8`
over **77 relevant source files**, with unchanged ABI **25**. A fresh frozen
SDL/reference build and `python scripts/check.py` pass **1,102 Python tests
without skips and 57 C++ suites**. The subsequent documentation closeout
retains this relevant-code identity.

The direct CD suite passes **215,525 authored checks**, including all D8 mode
bytes, known/unknown/invalid metadata, pending seeks, source rearm ordering,
and full checkpoint/PCM/FIR continuation. The apparent unsynchronized helper
ordering counterexample is retained separately: it does not reproduce through
the public bus's same-tick synchronization, so it is not a guest race claim.

The new separately compiled original Gear matrix runs **192 cases per engine**:
160 gap cases, 16 program controls and 16 controls preserving the known leadout
disagreement. Toolkit work is **1,196,896 native / zero fallback**, plus equal
separate interpreted work, at both CPU divisors and four authored CUE layouts.
All four full source identities execute with independently predicted per-site
counts. Original Gear's 1,196,896 operations are **port calls**, not retired
CPU instructions. There are 10,464 independent literal checks. Seek-origin and
deadline differences remain raw; only the declared admission/logical/controller
scope is qualified. The audit rehashes **546 bindings and 130 original Git
blobs**, requalifies eight actual dataset associations and rejects **34
written/reloaded corrupted admissions**. The prior clean runtime reproduces
the ignored-gap defect with the same native port probe; its failed raw result
is preserved without changing that source or repairing the output.

The direct VDC suite passes **4,933 checks**. Its fresh original-Gear proof
executes **36 device-clock cases**, 684 rows per engine and 77,976 independent
scalar checks across original/create/fresh-resume records. Twenty-seven CR/MWR
cases match all 38 fields. Nine burst cases retain **159** narrowly bounded
unused-index-buffer difference rows; all 22 control/latch/queue fields remain
exact and refreshed indices match. There are **zero native/interpreted
retirements** in this device fixture. All 36 written final payload pairs are
byte-identical. An independent audit rehashes 887 artifacts, checks 130 original
Git blobs, decodes 108 actual payload headers, verifies 72 create/resume process
associations and rejects 37 written/reloaded malformed admissions. A discovered
case-metadata admission weakness was fixed before freeze; accepted historical
pilot copies and their corrected rejection receipts are both retained.

The strengthened checkpoint oracle gate requalifies all 48 retained original
ADPCM/IRQ references and refuses changed copies from all 14 binding groups.
A fresh current-runtime checkpoint regression then executes **4,608 native
and 4,608 interpreted suffix retirements** across create/resume processes
(2,304 per tier specifically restored), matching those retained Gear records;
576 written/reloaded payload/profile refusals pass. This is new continuation
execution against a preserved reference, not a new original-emulator run.

The official native SDL consumer boots once and saves a new-build checkpoint
at frame **23,986**, tick **8,610,857,745**, importing **703,937,790 native**
retirements. Two fresh processes each run **87,783,727 new native / zero
interpreted** instructions with zero misses to mine combat at frame **26,751**.
Each matches 25 paused observations, complete work RAM, raw guest/window RGB,
PCM diagnostics, **15,006** full source identities/hits and the entire endpoint
file/payload. Core SHA-256 remains
`ae9ab02e5560875aef1319f10631d1941dad4270413617ff35b764d2ad52a5d4`.
A copied prior-build checkpoint is actually refused before execution, without
mutating initial state; its original remains unchanged. All three owned hosts
exit naturally, inspect the adjacent SDL DLL on an SDK-free PATH, and preserve
853 protected/module/media bindings. Root separately decodes the 150 actual
PNGs, checks 100 RGB pairs and independently decodes imported/new CPU counts.
Root qualification binds **4,781** final artifacts; receipt SHA-256:
`6b78e1eba487ec92ba947b62ad526ed9409c258b09b8ed849859cd30c8e89a7b`.

This remains a finite ordinary-input regression with volatile BRAM, explicit
`gear-good` and native-span 16. It does not establish that Ys III exercises the
new gap branch, retail WAV parity, physical drive timing, audible parity or
campaign completion. No owner install/save/selector or peer process is changed.
The Ys III project's unaligned ABI18 room-entry/HP observation is preserved as
an independent unresolved report; it is not attributed to this CD fix or VDC.

## Developer checkpoint implementation — ABI 25

[Developer checkpoints](DEVELOPER_CHECKPOINTS.md) now implement explicit paused
save and fresh-process restore for the exact binary, reviewed source/module,
media and machine recipe. The complete machine includes partial video, pending
VRAM/DMA/IRQ/CD events, controller latches, CDDA/ADPCM/PSG and exact PCM/filter/FIR
history. Files use bounded fieldwise encoding, integrity checks, exclusive
creation and transactional decode. SDL resources and read-only media handles
are rebuilt locally. Runtime ABI remains **25**.

The host preserves its input cursor and audio-drain polling phase; a pause does
not drain guest PCM. Reports and captures distinguish the imported prefix from
newly executed window work, with explicit inherited audio queue/WAV markers.
Host restore requires a fresh paused window; portable states, in-process rewind,
cross-build migration and owner-save publication are outside this interface.

Frozen implementation `1f64378aaf1d4d83bd6b9549cd5aa5bface3e341` has canonical
SHA-256 `c03984578f064946f328643456eb38a1ef337873307a6bb8f8d6e129566f7ea5`
over **77 relevant source files**. The later documentation closeout retains
that code identity. A clean frozen SDL/reference build and
`python scripts/check.py` pass **1,088 Python tests without skips and 55 C++ suites**.

Authored gates pass **272** machine/envelope checks and **106** audio/CD
checks. Fresh headless and SDL TCP continuations match full canonical machine
payloads and WAV suffix bytes, with corruption, overwrite and opt-in refusals.
The official consumer API also builds and restores an authored native program:
its qualified receipt counts **79,474 new native / zero interpreted** instructions
and 715,266 new ticks separately from 119,210 imported retirements. Live/file
captures and subsequent emission preserve the origin; endpoint payloads match.
Persistent BRAM publication from the imported state is refused.

Fresh original Geargrafx commit `1c62a549328241518101f5be5bf3e6840b96ea5d`
runs **48 guest-created ADPCM/IRQ cases**. Their checkpoint continuations
execute **4,608 native and 4,608 interpreted suffix retirements** across
uninterrupted/restored processes; **2,304 per tier** are specifically fresh
restored work. All measured initial/suffix CPU/device/WRAM records match Gear,
with 357,504 independent literal checks and **576 actual written/reloaded
corruption/profile refusals**. Full PC/eight-MPR/physical/fetched-byte identities
and hits match. The known raw fast-CSH prefix difference remains explicit;
measured suffix clocks match. A separate audit checks 1,054 original bindings,
130 source Git blobs, actual journals/stdout/captures and 31 corrupted admission
copies. These are finite digital checks, not hardware or analog certification.

The freshly rebuilt official native SDL consumer saves Ys III in town at
frame **19,126**, importing **559,702,005 native** retirements. A fresh process
restores that exact checkpoint and runs ordinary equipment/navigation/mine
combat to frame **26,751**, retiring **232,019,512 new native / zero interpreted**
instructions with zero guard misses. All **115** paused suffix observations,
full work RAM, raw guest/window pixels, PCM diagnostics and **23,736** complete
source identities/hits match uninterrupted execution. The entire endpoint
checkpoint files and 2,691,918-byte core payload are identical; core SHA-256 is
`ae9ab02e5560875aef1319f10631d1941dad4270413617ff35b764d2ad52a5d4`.
The root separately decodes all **460 PNGs**, validates checkpoint envelope/CPU
counters and binds **5,058** final artifacts. Root receipt SHA-256:
`f5661ef3cab4198f568d37dc0bd52e5c98f6446564288f5e1c646d85d5c59db2`.

Both retail processes exit naturally and load the checked adjacent SDL DLL without
an SDK PATH workaround. Seven protected originals and all 837 module files
remain unchanged; no owner installation, save, selector or peer process is
modified. This retained route uses explicit `gear-good`, volatile BRAM and
native-span 16. SDL host counters are recreated presentation state. Retail WAV
byte parity, cross-build restore and campaign completion are not claimed;
authored host tests separately prove pending-PCM/WAV suffix continuity.

## Optional native spans and ADPCM IRQ qualification — ABI 25

Frozen implementation `c4bc42842a28adbbe3c990b56a4a03fca7dc7757` has canonical
SHA-256 `29b879e976cbb65c4b1c3d753341956a99b0f1d3d6b76813dcf994a15f4cd2eb`
over **71 files**, ABI **25**. The optional span entry is additive; existing
single-step modules and the default host path remain supported. There is no
`Cpu`/`Bus` layout or production device-policy change.

[Native spans](NATIVE_SPANS.md) execute several direct translated operations
inside a stable part, while retaining full logical-PC/eight-MPR/source guards
and every instruction's device/IRQ and host observer boundary. CMake selects
the extra symbol only for a versioned opted-in manifest; runtime/consumer limits
are explicit. Capture, input, pause/frame, tick/step deadlines and fault closure
remain per instruction. No ambient global execution mode is used.

The fresh original-Gear proof uses an actual interpreted capture, then the same
native binary at limits **1, 2, 16 and 256**. It executes **320 native instructions
with zero fallback**, plus 80 interpreted instructions and 80 original Gear
records, checking **9,600 independent literals**. All 26 full source identities
and ten parts execute across six MPR contexts and three PC ranges. There are
**1,304 actual pure guards**. Outer calls are 80/40/6/2, generated-entry calls
80/50/24/20 and actual local continuations 0/30/56/60. The independent audit
requalifies 84 positives and rejects **83 written/reloaded corrupted copies**,
with 524 bound originals unchanged.

A separate frozen C++ matrix passes **368 checks**, 112 serial cases and three
observer cases, with 115 complete actual captures accounting for 376 native and
12 interpreted retirements. It covers self-modified opcodes/operands, TAM,
IRQ/RTI, block writes to upcoming source, speed/deadline boundaries, observer
yield/throws and faults before/after retirement. Authored headless and SDL host
tests compare legacy omission and limits 1/16/256 from the same binary, with
matching actual captures and independently expected 200 native instructions,
A=41, X=140, PC=$4003 and 1,794 master ticks.

**No speedup over legacy execution is established.** The frozen same-binary
benchmark runs four modes, each with one warmup and five alternating samples
of three million native retirements: **72 million actual native instructions**
overall, with zero interpreter work or guard misses. Independent CPU/flags/MPR,
27,011,700-tick, full RAM/code hashes and generation literals agree. Shared-host median
times are **45.782 ms legacy**, **72.798 ms span1**, **52.518 ms span16** and
**47.819 ms span64**. Span16 is about 14.7% slower and span64 about 4.45% slower
in this authored workload despite fewer dispatcher calls. The legacy default
is retained. These raw no-capture/video/audio/observer measurements do not
establish retail performance, and comparison only against span1 would mislead.

The independent [ADPCM IRQ suite](ADPCM_IRQ.md) adds **48 guest-created cases**
at both CPU speeds: HALF/END thresholds, status reads that do not acknowledge,
CPU and CD masks, held requests/RTI, reload/reset, sampled-source retention and
competing VDC IRQ1 priority. It executes **4,276 native instructions with zero
fallback**, plus 4,276 separate interpreted instructions and 104 block transfers
per tier. All **228 compiled identities** actually execute. There are 2,304
measured instruction records per engine, **268,128 independent literals** and
192 pure guards. Original Gear's **399,611 continuation calls** remain calls,
not an inflated opcode count. Its known fast-CSH primer clock difference stays
raw and explicitly checked; measured suffix state and elapsed clocks match.
All 147 directly supervised stages return zero. The audit checks original Git
blobs/objects/raw associations, rejects **64 actual corrupted copies** and
retains 1,041 bound originals unchanged. This device proof uses the single-step
native path; span/device combinations beyond the separate tests remain open.

Fresh SDL-enabled `python scripts/check.py` passes **1,071 Python tests, zero
skips, and 53 C++ suites** on the frozen implementation. Python takes 308.166
seconds; all checks take 353.929 seconds. The configure/build/check stages and
their exact source remain bound separately from benchmark/reference runs.

The same frozen source passes three fresh **26,751-frame** Ys III TCP runs:
an actual no-module interpreter capture, then opted-in native limits 16 and 1.
The complete 43,574-identity capture supplies **835 translation units and one
header**, with separate direct-operation body counts for the two entry paths.
The official native cold build and fresh-configure warm restore pass; a second
reviewed descriptor changes only the runtime limit to one and restores the
**same executable/DLL bytes and compile key**. Single observed cold/warm times
are **438.310 s / 19.054 s**. No old capture or ABI is relabeled.

Each native run retires **791,721,517 native instructions, zero fallback and
zero guard misses**, versus the same fresh interpreter work. Strict I/N16 and
N1/N16 comparisons pass **629 states, 185 guest/window image pairs**, full WRAM,
digital PCM/bounded WAV bytes and every full source identity/per-key hit count.
Both native runs complete 101,674 block transfers and 57,757,710 queued VDC wait
ticks. Root reviewed six new native images and independently reexecuted both
post-run validators, binding town movement, purchases/equipment, mine combat,
received damage and reward observations. This repeats the finite regression;
it adds no campaign or new-title compatibility claim.

Native16 records **49,482,595 batches, 73,405,136 generated entries and
718,316,381 actual local continuations**. Native1 records 791,721,517 entries
and zero local continuations. Its 791,721,518 batches include the final
zero-retirement quit attempt. These counters are independently checked against
actual work. Controller timings include capture/TCP/shared-host scheduling,
and the native runs partly overlap; they are not a statistical speed benchmark.

The route's 25 controls pass (24 rejected copies and an accepted poll projection),
along with **14 cache, five bootstrap and 15 new dispatch-metadata** corrupted-file
rejections. Original inputs and proofs remain unchanged. The complete audited
cache contract is 604,728 UTF-8 bytes; its full digest participates in the
compact package identity. Both native packages run SDK-free with hidden/muted
SDL. No owner installation, save or launcher selection is written. The explicit
`gear-good` unknown-CD profile remains required for this finite route.

At this earlier span milestone, consumer feedback produced the acceptance plan
for the [developer checkpoint interface](DEVELOPER_CHECKPOINTS.md). The newer
implementation and its verification scope are described above.

## Stable modules and managed contributor rebuilds — ABI 25

Observed-code emission now offers a stable layout keyed by the complete eight
MPR bytes and fixed 256-byte logical-PC ranges. Adding observations preserves
unrelated part names and contents; the balanced default retains its prior
behavior. The managed Windows LLVM-MinGW/Ninja producer copies a validated
module into its own workspace, verifies retained build/module bytes and
timestamps, reconfigures and audits CMake/Ninja, rebuilds, then rechecks actual
compiler dependencies and external inputs. Interrupted generations refuse
further producer reuse and official execution. See [stable emission](STABLE_EMISSION.md)
and [managed builds](INCREMENTAL_BUILDS.md).

Frozen implementation `830cc08d54740162c7a0aa956e01c4219ab3bea8` has canonical
SHA-256 `4474aae95a1eff710e4f72cb66e10a2dc8a1d8e7ee76972cddbc1612b3e67855`
over **70 files**, ABI **25**. No guest CPU/device semantics or ABI change is
introduced. Original Geargrafx remains pinned to
`1c62a549328241518101f5be5bf3e6840b96ea5d` in a separate executable.

The fresh authored context proof executes **80 native instructions with zero
fallback**, a separate 80 interpreted instructions and 80 original Gear
records. All **26 full source identities and ten stable parts** execute across
six MPR contexts and three logical-PC ranges, at both CPU speeds. Checks cover
**4,800 independent state literals and 326 actual pure guard refusals**.
The audit requalifies 61 positives and rejects **60 corrupted copies**, with
511 bound original files unchanged. An earlier working-source pilot retained
its failed preservation result; both subsequent clean frozen proofs remain
separate actual runs.

The authored managed-build test promotes an actually captured missing `INX`:
**101 native / 99 interpreted** becomes **200 native / zero interpreted**.
Only its affected object rebuilds, while **26 objects retain exact bytes and
timestamps**. A separate clean build matches the full guest state and capture.
The current public integration test also checks a capture-metadata-only update,
an exact-descriptor no-op, changed-input refusal and interrupted-run refusal.
Its independent endpoint is X=106, PC=$4100 and 1,800 master ticks.

A real stable-layout retail build exposed a **604,682-byte** audited contract
that exceeded the generic cache's 256 KiB limit. The corrected producer hashes
the **complete** canonical UTF-8 contract into a compact manifest identity;
the full contract and audit remain in the build receipt. It neither drops
audit fields nor raises the generic cache/manifest bounds. Authored 835-unit
publish/restore tests pass; changing a deep header causes a real miss. See
[cache identity](BUILD_CACHE.md). The earlier failed retail build/capture
retains its original source pin and is not relabeled as the corrected run.

Fresh `python scripts/check.py` passes **1,049 Python tests, zero skips, and
52 C++ suites**. Python takes 272.071 seconds; the complete rerun takes
316.804 seconds. The C++ binaries are explicitly reused from implementation
`242ad25904d2c7cba8e22ab52bdb0f34728dc71c`: all native/CMake/emitter/generator
inputs are byte-identical. Of 442 tracked files, only five differ: the two
Python cache implementation files, two Python cache tests and cache documentation.
The original complete 1,044-test/52-suite run also passes. This is a fresh
Python/check-runner execution on the corrected source, not a claimed second
C++ compilation of identical inputs.

The corrected source also passes a fresh authentic-reset **26,751-frame**
Ys III TCP pair. Actual interpretation supplies a new complete ABI25 capture;
only that capture emits **43,574 identities across 835 translation units and
one header**. The official cold build and fresh-configure warm restoration
produce identical packages. Their single observed times are **373.220 s /
17.585 s**, during other work; these are not a controlled benchmark. The full
**609,812-byte** input contract remains in the receipt, with its complete
digest bound by the compact cache manifest.

Actual execution is **791,721,517 native instructions, zero fallback and zero
native guard misses**, versus the same interpreted work. All 629 paused states,
185 guest/window image pairs, full WRAM, digital PCM/bounded WAV bytes and full
PC/all-eight-MPR/physical/byte identities and hits match. Both tiers execute
101,674 block transfers and 57,757,710 queued VDC wait ticks. Root reviewed six
fresh native PNGs and independently reran the strict checker, binding nine
town/purchase/equipment/mine milestones. Gold changes 900→500→200→204, HP reaches
4 after damage and EXP reaches 6. This is the finite ordinary-input regression,
not additional library or campaign coverage.

All 25 route controls pass (24 rejected copies plus one accepted poll
projection), along with **14 cache** and **five bootstrap-provenance** rejection
controls. A separate read-only audit reconstructs both complete compact-key
contracts, 954 actual configure-input rows and the cold compiler-header closure.
The seven protected originals and four runtime inputs stay unchanged; no owner
save, installation or launcher selection is written. Both hidden/muted hosts
quit naturally. The explicit `gear-good` unknown-CD profile remains required
for this route; its command semantics are not implemented by this compiler batch.

The source audit found no justified new CR/MWR fix. A late 263-to-262-line
VCE switch remains explicitly unsupported; Gear's equality-only wrap is not
sufficient evidence to replace that refusal. Broader bus/hardware behavior,
additional media/library profiles and multi-instruction native dispatch remain
separate work. Build success does not establish execution or campaign coverage.

## Live scroll writes and CD program ranges — ABI 25

Two reproduced compatibility defects are fixed: late BXR/BYR writes now
update the appropriate current-line latch/offset, and CD `$DD` position replies
use actual program ranges rather than assigning every gap to the preceding
track. These are general video/CD changes, independent of Ys III. Providers
distinguish authoritative gaps from unavailable metadata; the latter retains
an explicit TOC-only approximation. Unknown CD commands keep the strict default.

Runtime/compiler implementation `e2455171c375241d7b4ebad5f3547d3d101faa25`
has canonical SHA-256
`56196c55c70d3e31d7cb3c629d88b076d5607bde723bc2199ea32ba6d4d142ca`
over **69 files**, ABI **25**. Observer/test correction
`97f16a3fd1c66e7dbd7477692cbfbfe970d3fa55` has identical runtime, compiler,
CMake, generator and native-test inputs. Its two changed files correct unsigned
register JSON serialization in the original Gear observer and a cache-negative
fixture whose old alternate ABI became equal after the bump. The original
failed JSON and full-check attempt remain preserved; outputs and expectations
were not repaired or backfilled. The corrected original observer was freshly
compiled. Native binaries are explicitly reused from the identical inputs.

The [scroll suite](VDC_SCROLL.md) passes **19 guest-created profiles** against
separately compiled original Geargrafx, native execution and the interpreter.
Six actual ABI24 counterexamples demonstrate the previous X/Y errors. The new
run executes **1,935 native instructions with zero fallback**, plus 1,935
separate interpreted instructions and **304 block transfers per tier**. All
**153 compiled source identities** are actually observed. Checks cover full
CPU/MPR/WRAM literals, per-line history, sixteen contrasting pixel indices and
31 timed guest port actions (30 original data-register callbacks plus selection).
Original Gear completes 1,935 opcodes across **1,425,892 actual continuation
calls**; those calls are not inflated into instruction counts. Output-disabled
native execution preserves the same guest state. All 19 positive datasets
requalify; **11 corrupted copies are rejected**, with 514 bound files unchanged.

The [CD position suite](CD_POSITION.md) passes **18 authored CUE layouts**:
plain, virtual-pregap and stored-INDEX00, data/audio tails and BCD boundaries.
There are **144 original Gear cases**, plus **288 cases per toolkit tier** at
both CPU speeds and both ACK profiles. Successful READs naturally establish
the head before full DD DATA IN/status/message transactions. Independent
payload/position expectations check **1,486,080 literals**. Actual work is
**1,795,968 native instructions with zero fallback** plus an equal interpreter
run and **288 pure guards**. All 180 positive datasets requalify (720 case
instances); **27 corrupted copies are rejected**, with 1,206 bound inputs
unchanged. The C++ provider suite separately passes **260 checks**, including
authored ISO/CUE and synthetic CHD geometry, postgaps, source changes, purity
and invalid custom-provider results. This does not claim direct Gear POSTGAP,
compressed-CHD, raw-subchannel or cross-core CPU-timing parity.

The fresh **ABI25** Ys III route starts with an actual `no_module` interpreter
capture, then emits and builds its native module from that new capture alone.
No historical ABI24 capture is relabeled. Both isolated **26,751-frame** TCP
runs pass: **791,721,517 native instructions, zero fallback and zero native
guard misses** versus an equal fresh interpreter run. All **43,574 full source
identities/hits**, 629 paused states, 185 guest/window image pairs, full WRAM,
digital PCM and bounded WAV bytes match within the documented projections.
Both execute **101,674 block transfers** and **57,757,710 VDC wait ticks**.
Root reviewed six new PNGs and bound nine town/equipment/mine milestones.

The new official native package passes actual cold compilation and warm cache
restoration after fresh configure, with identical package bytes and SDK-free
execution. Single observed cold/warm times are **159.2629 s / 15.7565 s**;
these are not a general benchmark. The bootstrap interpreter receipt explicitly
contains no future native-package binding. The 25 route controls (24 rejected
copies and one accepted poll projection) and eight cache rejection controls
pass. Five additional real-copy controls reject forged bootstrap package/binary
provenance, a missing capture binding and old or altered capture claims.
Seven protected originals and all four runtime inputs remain unchanged;
owner saves, installation and launcher selection were not written. Both game
hosts quit naturally.

The full SDL-enabled `python scripts/check.py` rerun passes **1,011 Python
tests, zero skips, and 52 C++ suites**. Python takes 183.304 seconds; complete
suite execution takes 230.830 seconds. The 53 CTest registrations are inspected
metadata, not another execution.

ABI 25 requires rebuilding custom providers and regenerating native modules.
Historical captures remain readable with their original labels, while new
qualification needs fresh execution. The earlier completed proofs below keep
their own source pins. Arbitrary midline races, raw subchannels, electrical
hardware behavior and full-game compatibility remain unqualified. The finite
retail route still requires the explicit `gear-good` unknown-command profile.

## Previous active-display VRAM arbitration — frozen proof and retail regression

The [new active-display suite](VDC_ACTIVE.md) passes **138 authored cases**
against original Geargrafx and independent clock, CPU, WRAM, VRAM and device
expectations. It executes **36,070 native instructions with zero fallback**
plus an equal separate interpreter run, including 3,048 block transfers per
tier, 552 pure guards and 1,803 actually observed translated source identities.
There are 6,624 measured retirements per engine and all 18 genuine dual-queue
endpoint triples pass. Separate engine timing differences remain explicit.
No production CPU/device semantic change or ABI migration was needed.
Fresh SDL-enabled `scripts/check.py` passes **980 Python tests, zero skips,
and 50 C++ suites**. The new C++ suite has 141,416 checks; generated CTest
metadata has 51 entries including Python, without a second execution.

The deferred work is now complete on a fresh clean frozen checkout of
`860067355f154147c8ae4e94d058356fca6d7b18`, canonical source SHA-256
`222b3f6d788f4b5ed7f81d1e501db722db0fa2da4096af54568309fd4f583f81`
over **69 files**, ABI **24**. The original working-source proof retains its
own earlier epoch; it was not relabeled. Original Geargrafx remains pinned to
`1c62a549328241518101f5be5bf3e6840b96ea5d` in a separate executable.

The independent frozen reference audit rehashes **3,391 files**, checks
130 original Git blobs and unchanged compile copies plus 40 objects, and
requalifies **800,676 literal checks and 38,644,452 journal expectations**.
All 138 actual positive datasets requalify; **81 corrupted copies are
rejected**, with 3,390 original bound inputs unchanged. The control harness
records one missing-field rejection as `KeyError`, which the public CLI
already catches; the other 80 are `ValueError`. Earlier failed audit helpers
remain separate, including corrections for newline normalization, shared
emitted bodies and an identifier in a no-call comment. No oracle values or
engine outputs were rewritten to pass the audit.

The fresh isolated **26,751-frame** Ys III TCP pair passes strict comparison:
**791,721,517 native instructions, zero fallback and zero native guard misses**
versus the same retired work in a fresh `no_module` interpreter. Both execute
**101,674 block transfers** and accumulate **57,757,710 queued VDC wait ticks**.
All **43,574 full source identities and per-key hits**, 629 paused states,
185 guest/window image pairs, full WRAM, digital PCM reports and bounded WAV
bytes match within the declared projections. Root opened six fresh PNGs and
bound nine WRAM milestones covering town movement, purchases/equipment,
first-mine attacks, an enemy reward and received damage.

The native package is freshly emitted from the original ABI24 capture without
excluded observations. An actual cold build and a fresh warm configure restore
identical packaged bytes; the restored executable runs without an SDL SDK PATH
workaround. Single observed cold/warm times are **159.8164 s / 16.2031 s**,
not a general benchmark. All 25 route admission controls pass (24 rejections
and one accepted poll projection), as do eight cache rejection controls.
The independent retail audit reexecutes the strict checker and rehashes
**1,942 bound files**, five compile trees and 662 normalized configure rows.
The seven protected original inputs are unchanged; owner saves, installation
and launcher selection were not written. Both game hosts quit naturally.

This closes the previously deferred authored/retail work for that exact pin.
It does not qualify midline latch races, electrical bus phases or a complete
campaign. The explicit `gear-good` unknown-CD response profile remains required
for this retail route; strict default mode still faults on that command.

## Longer finite consumer sessions — host-only follow-up

Both hosts and schema-1 consumers now accept explicit wall limits from
**1 through 86,400 seconds**. Existing recipes retain their selected value;
raw CLI omission still disables only its wall timer, while consumer descriptors
require an explicit positive integer. Guest step/tick deadlines and the
official outer watchdog at the selected wall limit plus ten seconds remain
active. No guest model, native lowering, state layout or ABI changes.
See [finite host sessions](SESSION_LIMITS.md).

Real headless and SDL tests check the new parser boundaries and one-second
expiry while TCP-paused, with zero guest retirements. An actual official
authored consumer build/run with `wall_seconds = 900` executes **200 native
instructions and zero fallback**, yielding independently expected A=41,
X=140, PC=16387 and 1,794 master ticks. This tests forwarding and execution,
not 900 seconds elapsed. Its exact working-source canonical SHA-256 is
`c336cabb5eea660171e825d60fb3b1c927e3d67fb68f77057ba5d8cdd53519e7`
over 69 files. It is separate from the frozen retail/reference source above.

A separate current-host TCP startup smoke uses the actual BIOS/disc inputs,
an explicit 900-second allowance and a packaged SDL host under sanitized PATH.
It reaches the System Card menu after **1,000 frames / 29,156,556 interpreted
instructions / zero native instructions**, then quits naturally. No owner
save, installation or selection is written. This verifies current-host startup
and the longer option, not another native gameplay route or 900 seconds elapsed.

The complete Python suite now has a finite default **600-second** deadline,
with `scripts/check.py --python-timeout 1..86400` for an explicitly selected
bound. The growing suite exceeded the previous aggregate 180-second deadline
in a concurrent run while compiling an authored consumer fixture; that failed
attempt is retained. Test selection and individual 60-second C++ deadlines are
unchanged. This test-runner setting is separate from guest host-session limits.

Fresh SDL-enabled `python scripts/check.py` passes **991 Python tests, zero
skips, and 50 C++ suites** on the host-option source. Python completes in
166.278 seconds; all suites finish successfully in 210.848 seconds. The
51 CTest registrations are inspected metadata, not a second execution.

## Previous IRQ1/IRQ2 dynamic-stall suite — ABI 24

Fresh SDL-enabled `scripts/check.py` passes **892 Python tests, zero skips,
and 49 C++ suites**. Generated CTest metadata has 50 registrations including
Python; no second CTest execution is implied. The new
[dynamic-stall suite](IRQ_STALLS.md) passes without a production CPU/device
semantic change or ABI migration.

Frozen implementation `06d97f42c78f55a752187a063aaf7f6161f051ea` has canonical
source SHA-256 `4ad299601b2c91ec3fe791daab2bb1effe5f45583119c2f102917acfca1f1587`
over **69 files**, ABI **24**. Original Geargrafx
`1c62a549328241518101f5be5bf3e6840b96ea5d` runs separately with public authored
firmware/media loading, **Standard CD hardware and zero expanded Card RAM**.
No host writes establish a pending IRQ, DMA counter, raster phase or queue.

All **78 configurations** pass independent CPU/clock/full 8 KiB WRAM,
64 KiB little-endian VRAM and 39-column device literals. Each engine has
**3,744 measured retirements**. Actual toolkit work is **19,227 native
instructions with zero fallback**, plus an equal separate interpreter run,
including **1,548 block transfers per tier** and **312 pure native guards**.
All **635** compiled translated logical-PC/full-MPR/physical/byte identities
are actually observed with independently expected per-key hits. The C++
selftest passes **77,610 checks**.

The matrix covers both CPU speeds and all three VCE rates: competing sources,
CPU masks, the I flag, individual sources, low/high data reads, writes,
`INC $0002`, wrapped stacks and remapped vectors. Seventy-two subsequent-CD-
byte cases use 256-word DMA; six first-DATA-IN cases use 2,048 words. Guest
instructions initialize distinct source/tail VRAM words and a known old read
buffer, warm up a complete blank frame, launch DMA and queue a MARR prefetch.
Every required source rises strictly inside the resulting real dynamic wait.
The finite transport ends with ACK held and IRQ2 masked; it does not claim a
complete directory-response transaction or idle-bus completion.

Every original clock callback remains in the journal. An original extra-cycle
counter increase identifies each three-tick dynamic wait; a fast fixed memory
wait also lasts three ticks and cannot be substituted. Hardware-exit kernels
explicitly precede CPU resampling. Subsequent callbacks or actual CPU return
supply the sampled-pending witness. Only primer block transfers compact their
per-span kernels; their exact `14 + 6*N + 3` cycle continuation partition,
`N+2` calls, counters and flags remain checked. Ordinary return/final kernels
are bound to the actual wrapper callback. The 37-field raw kernels retain
more state than the explicitly modeled 18-field blank-slot kernel.

There are **52 elapsed retirement matches and 26 independently predicted
timing differences**. Every first difference is a retirement clock: Gear is
three ticks later in 14 cases, six ticks earlier in 11 and six ticks later
in one. Registers, mappings, WRAM and IRQ metadata match throughout both
complete measured suffixes. Raw fast-primer origins differ by 18 ticks.
Gear's deferred ACK processing and the toolkit's synchronous handshake also
retain their separate source-edge clocks. These differences are not erased
to force equality.

The independent final reference audit rehashes **2,127 bound files**, verifies
130 original Git blobs and unchanged compile copies plus 40 objects, and
requalifies **452,556 literal checks and 11,500,470 journal expectations**.
The 102 original IRQ deliveries and every compiled/observed source count are
bound to actual raw outputs. A newline-only assumption in the private audit
helper failed before its correction; that failed receipt remains separate.
No proof or expected result was rewritten.
All 78 positive baselines requalify in the actual mutation run; **81 corrupted
copies are rejected** and 2,126 original paths remain unchanged. Controls cover
dynamic/fixed wait classification, source and CPU-sample clocks, queue/kernel
continuity, return snapshots, block callback collapse, acknowledgements,
WRAM/VRAM, source hits and execution accounting.

The fresh isolated **26,751-frame** Ys III TCP pair passes strict comparison:
**791,721,517 native instructions, zero fallback and zero native guard misses**
versus 791,721,517 instructions in a fresh same-source `no_module` interpreter.
Both execute **101,674 block transfers** and accumulate **57,757,710 queued
VDC wait ticks**. All **43,574 full source identities and per-key hits**,
629 paused states, 185 guest/window image pairs, full WRAM, source PCM reports
and bounded WAV bytes match within the declared projections. The interpreter
has one expected `no_module` lookup miss per interpreted instruction; that is
kept separate from the native run's zero misses. Root reviewed six actual new
PNGs and bound nine WRAM milestones: town movement, Short Sword/Leather Armor
equipment and first-mine sword combat, rewards and received damage.

The official four-file native package is freshly compiled from the unchanged
actual ABI24 capture, with no ABI relabeling or excluded observations. A
fresh configure restores an identical warm package on cache key
`06f5207e9788ea0e40b906592eb5c0d4be635eb322ad2b2e3fb72f252eccf486`.
Actual concurrent cold/warm observations are **172.8621 s / 15.3707 s**;
these single observations are not a general performance benchmark. The tests
execute the warm package without the SDL SDK PATH workaround. There are
25 route-admission controls (24 rejections and one accepted documented poll
projection) and eight rejected cache controls. The independent retail audit
reexecutes the strict checker and rehashes 1,936 file bindings, five compile
trees and 662 normalized cold/warm configure rows.

All seven protected original inputs remain unchanged. Owner saves,
installation and launcher selection were not written; selection is observed
read-only. Both owned hosts quit naturally and the closed process census is
empty. The explicit `gear-good` unknown-CD-response profile remains required
for this retail route; strict default behavior still faults on that unknown
command. This batch does not implement it.

This qualifies the authored blank-slot DMA/CD combinations. Active-display
stalls, other raster/sprite/ADPCM sources, overlapping device combinations,
interrupted transfers, electrical bus phases and independent Beetle CD
execution remain separate work. Repeating the finite retail regression
checks integration; it does not add campaign or hardware coverage.

## Previous device IRQ priority and acknowledgement suite — ABI 24

The fresh SDL-enabled `scripts/check.py` passes **852 Python tests, zero skips,
and 48 C++ suites**. Generated CTest metadata has 49 registrations including
Python; no second CTest execution is implied. This batch adds the authored
[device IRQ suite and original call journals](IRQ_DEVICES.md). The existing
CPU/runtime ordering passed the new checks; no production CPU/device semantic
change or ABI migration was justified.

Frozen implementation `9099c5d27afccd5fce7514a3bb2494feeb214d2f` has canonical
source SHA-256 `899b515405b8272def686b515530ef4f0e965ad80acd6438cdbcb5370ec6b21b`
over **69 source files**, ABI **24**. Later documentation retains those code
bytes. Freshly compiled original Geargrafx
`1c62a549328241518101f5be5bf3e6840b96ea5d` uses actual public authored firmware
and CUE loading with **Standard CD hardware and zero expanded Card RAM**,
matching the declared toolkit profile. Earlier Super-CD preflights remain
separate preliminary evidence.

All **44 guest-only configurations** pass their independent CPU/clock/full
8 KiB WRAM and 39-column device literals. They execute **8,074 translated
native instructions with zero fallback**, plus an equal separate interpreter
run, including **668 block transfers per tier**. There are **2,112 measured
retirements per engine** and **176 pure native guards**. The authored source
plan compiles 535 translated identities; the actual native captures also
observe all **535 unique logical-PC/full-MPR/physical/byte identities** with
independent per-key counts. Native/interpreter raw CPU events and device
literals agree. The standalone C++ selftest passes **33,924 checks**.

Guest firmware raises real timer, one-word VDC DMA and CD `$DE` DATA IN/STATUS
sources, then executes real handlers and acknowledgements. The matrix covers
all eight CPU disable masks at both CPU speeds, timer → IRQ1 → IRQ2 priority,
held-line reentry, stack wrapping, remapped vectors, timer-acknowledgement
fallback and the following device-access distinctions:

| Access | Qualified aggregate outcome |
|---|---|
| Queued VDC status read | Clears live IRQ1 but can retain the pre-acknowledgement CPU sample |
| Legacy immediate status read | Clears before resampling and cancels the same IRQ1 |
| VDC status INC | Its later write/wait replaces the sample and cancels delivery |
| CD ACK, source disable or reset | Can lower the live line while a sampled IRQ2 still delivers |
| CD active-status read | Does not acknowledge its source |

**42 cases match original Gear retirement states with elapsed clocks**. The
two explicit legacy immediate-read cases instead pin the exact differing IRQ
decision and independently check both complete suffixes. Raw clocks retain
the known **18-master-tick** fast-primer CSH epoch difference. No flags,
mapping, memory or later timing discrepancy is silently normalized away.
Original Gear records **68 hardware IRQ entries**, versus **66** across the
toolkit's matrix including those two intentional legacy cancellations.

The actual original callback journal retains CPU/VDC/CD/SCSI events, complete
clock spans, returned versus internally clocked ticks and original continuation
counts. It checks **255,288 literal scalars and 209,664 journal expectations**.
Missing CD callbacks, an in-range IRQ timestamp change, incorrect return PC or
mask, a shortened block-call count, a misplaced bootstrap witness and source/
device mutations are rejected. All **58 actual-evidence corruption controls**
pass without modifying the positive inputs. Independent review rehashes
**1,281 files**, verifies **130 original Git blobs and unchanged compile copies**
and checks all 44 completed Standard-CD process diagnostics.

Original Gear defers the ACK-driven SCSI source update until its hardware
clock; the toolkit's port handler processes it synchronously. The preserved
callback times and completed-instruction outcomes have explicitly different
scopes. These tests do not qualify physical bus phases, every raster/sprite
or ADPCM IRQ source, or IRQ1/IRQ2 delivery during dynamic VRAM stalls. Existing
timer-during-stall tests remain separate. No original Beetle CD execution,
electrical hardware verdict or broad console compatibility is inferred.

The newly emitted **43,574-site** consumer module and fresh same-source
`no_module` desktop each complete the isolated **26,751-frame** ordinary-input
Ys III route from authentic System Card reset through town, equipment and
first-mine combat. The native run retires **791,721,517 instructions with zero
fallback or guard misses**, plus **101,674 block transfers**. Its separate
interpreter replay matches **629 state observations**, **185 guest/window image
observations**, full WRAM, complete source identities/hits and digital PCM/WAV
evidence under the unchanged declared host-only projections. Queued VDC wait
ticks remain **57,757,710**. Root opened six actual new native PNGs and bound
the review; the checker rehashes **1,176 files**. Twenty-five route controls
(24 rejected mutations and one admitted host-poll variation) and eight cache
controls pass. The retail checker changes only its frozen directory and exact
source SHA; ABI 24, the 69-file count, assertions and projections are unchanged.

The actual restored SDL package executes without an SDK PATH dependency.
The cold configure/build took **173.73 seconds** and its verified same-key
warm restore after fresh configuration took **15.94 seconds**, skipping
consumer compilation/linking. These single paired observations include
hashing and concurrent work and are not a speed benchmark.

Both hosts close naturally and leave no owned process. All seven protected
inputs, old captures/proofs and owner saves/install remain untouched. A
legitimate external Ys III launcher-selection update before the runs is
recorded through the fresh read-only observation; this toolkit batch neither
writes nor restores that selection. No memory assistance, migration or new
listening qualification is involved. The finite route still requires the
explicit `gear-good` unknown-CD response profile. This repeats internal
regression coverage rather than expanding title/campaign or hardware claims.

## IRQ-aware independent retirement traces — ABI 24 unchanged

The IRQ-retirement batch's SDL-enabled `scripts/check.py` passed
**814 Python tests, zero
skips, and 47 C++ suites**. Generated CTest metadata contains 48 registrations,
including Python; no second CTest execution is implied.

The opt-in [IRQ trace interface](IRQ_TRACES.md) retains actual raw calls and
explicit completed-instruction groups. IRQ entry, reset and resumed block
transfers cannot become invented opcode retirements. The default v1 trace
interface and masked Beetle observer remain unchanged. No production CPU,
device or interrupt-policy change was made in this batch.

Frozen implementation `6adc64a5f67d789679d0e4a7f4db606550b2e9f1` has canonical
source SHA-256 `84088130826c65ae023bd2d187c18378bb3efd14755878ac3a10f486eba9b6fc`
over **69 source files**, ABI **24**. Documentation commits retain these
compiler/runtime bytes. Separately compiled, unchanged original Geargrafx
`1c62a549328241518101f5be5bf3e6840b96ea5d` and full Beetle PCE core
`b96c11e095b6a40a412d2da02766ae1c3f4fd539` run **15 authored cases**.
Guest software initializes the timer, registers, mapping and RAM; the harness
does not seed them through host inspection APIs.

The toolkit executes **12,068 native instructions with zero fallback**, plus
an equal separate interpreter run, including software primers. There are
**128 measured retirements per engine**. Independent literal CPU/clock/WRAM
states, full PC/MPR/physical/byte source-hit ledgers, actual tier counts,
device literals and four pure guards per native process pass. Native and
interpreter raw-event traces are exactly equal. The C++ selftest also passes
**25,460 checks** across both tiers.

Gear matches all declared state and IRQ literals. Thirteen elapsed-clock
cases agree with the toolkit; two speed-transition cases retain the known
Gear aggregate timing difference. Fast software primers also expose an
18-master-tick raw epoch difference, retained explicitly rather than rewritten.
Ten Beetle cases agree in raw CPU/mapping/clock/WRAM retirement states after
excluding only its unavailable transfer latch. Five cases expose the
source-predicted differences below; the exact first-difference descriptor and
independent PC/P witness must match. Divergent suffixes are retained as
observations, not claimed as complete independent literal parity.

| Case | Original Beetle difference from the selected toolkit/Gear profile |
|---|---|
| RTI with a held timer line | Reenters at restored-I RTI boundary; toolkit/Gear delay one instruction |
| Timer mask during STA | Live mask suppresses entry; toolkit/Gear retain the entry sample |
| Timer unmask during STA | Live mask permits immediate entry; toolkit/Gear wait |
| Pending BRK | Sets I and suppresses a second hardware entry; toolkit/Gear enter twice |
| PLP raw B representation | Retains raw B in live P; toolkit/Gear clear it |

Original call journals are rechecked against the pinned IRQ pipeline branch,
including final drain. Actual original Gear trace callbacks provide IRQ
vector, return PC and timestamp. Their exact timestamp/return-PC contract is
qualified only for this suite's no-clocked-I/O delivery sites; it is not a
universal MMIO phase rule. Raw trace files, journals, original sources,
authored inputs, binaries and final RAM are bound separately.

Two additional original-Beetle accounting checks prove that a final requested
opcode retains its IRQ-only call without fetching handler code, and a measured
TII completes through three continuation calls as one retirement. They add no
native or game coverage claim. A fresh build of the unchanged default observer
passes its **161 measured / 20 primer** masked v1 instructions and still refuses
the next unmasked opcode explicitly. IRQ1/IRQ2 priority, actual VDC
acknowledgement phases, interrupted transfers, finer bus phases and physical
hardware remain separate work. Reference disagreement is not a hardware verdict.
Independent final review rehashes **2,018 binding entries** and checks both
fresh original-core build epochs. All **37 post-run evidence mutations** are
rejected, including an in-range callback timestamp/return-PC change, a
coherent mapping/source-ledger change, incorrect first-divergence descriptors
and an omitted final interrupt/continuation.

A fresh **26,751-frame** isolated Ys III TCP pair executes the newly emitted
**43,574-site** ABI 24 module from authentic System Card reset through town,
ordinary purchases/equipment and first-mine combat. The native run retires
**791,721,517 instructions with zero interpreter fallback or guard misses**
and **101,674 block transfers**. The fresh same-source `no_module` interpreter
matches combined work, **629 state observations**, **185 guest/window image
observations**, full WRAM, source identities/hits and digital PCM/WAV evidence
under the existing declared host-only projections. Queued VDC wait ticks are
**57,757,710**. Six actual new PNGs were opened and bound to the visual review.
The independent checker rehashes **1,177 files**; 25 route controls (24 rejected
mutations and one permitted host-poll variation) and eight cache controls pass.
The checker retains all prior assertions and projections, changing only its
frozen path and exact source identity/count.

The actual restored desktop package runs without an SDK PATH dependency.
Its cold build took **172.98 seconds**, and the verified same-key warm restore
after fresh configuration took **13.45 seconds**, with no consumer compile.
These are single observations under concurrent work, not a benchmark.
Two intervening private attempts safely missed because of CMake object-path
shortening and prerequisite ordering; both builds and failed assertions remain
retained. A matching-layout attempt proves the real hit. No cache-key checks
were weakened; [BUILD_CACHE.md](BUILD_CACHE.md) describes the limitation.

Both hosts close naturally and leave no owned process running. The seven
protected inputs, old captures/proofs and owner save/install/selection remain
untouched. No memory assistance, selection migration or new listening claim
is involved. This repeats a finite internal regression, not expanded title
coverage, a full campaign, or independent full-game hardware parity. The
explicit `gear-good` unknown-CD response profile remains required. The Ys III
consumer project reports no new shared defect and retains its independent
ABI 18 pin.

## CUE postgaps and CD READ head position — ABI 24 unchanged

The CUE batch's SDL check passed **760 Python tests, zero skips, and 46 C++ suites**.
It added CUE POSTGAP support in both the Python frontend and C++ provider,
plus a correction to the retained CD data head used by idle position queries
and later audio seeks. All fixtures are authored; baseline tests use no retail
input. [MEDIA.md](MEDIA.md) documents the format policies.

`POSTGAP` inserts virtual disc frames after a track's program. It does not
consume file bytes, shift FILE-relative indices, extend the stored payload,
or turn missing audio/data into stored sectors. Ordering, duplicates, MSF/
leadout limits, source changes and component identities remain checked.
The CUE profile includes a final postgap in leadout, following original Beetle;
the existing Gear-compatible CHD profile still excludes a final CHD postgap.
An exhaustive authored C++ matrix passes **2,451,979 checks across 288 layouts**.
Python tests and actual headless/desktop TCP tests verify shifted disc reads
still return the original file-frame payload without debugger writes.

Fresh, separately compiled original media readers qualify **seven authored
layouts**. Toolkit provider/cache observations pass **220,738 scalar checks
over 614 records**; Python adds **42,750**. Original Beetle reads the actual
POSTGAP CUEs and passes **195,684 checks over 183 records**. Original Gear reads
**six separately retained equivalent-PREGAP layouts**, passing **35,064 checks
over 274 records**. Gear's CUE parser does not implement POSTGAP; trailing CUE
postgaps are omitted from those transformed inputs. This is an explicit
cross-format/reference distinction, not direct Gear POSTGAP parsing parity.
Thirteen material observation mutations are rejected; all **1,145 binding
entries** rehash unchanged. The media proof checks geometry, payload, stored
samples and the existing playback cache/gate. It does not execute guest CPU
instructions or qualify a full audio scheduler, raw Q/subchannels or hardware.

Successful READ loads now retain **loaded LBA + 1, clamped to disc end** under
the selected Gear profile. A blocked buffer or failed provider read preserves
the previous head; the queued next-load address remains independent. A fresh
old-runtime build reproduces a READ at LBA 2 retaining head/relative position 2.
The corrected build and original Gear instead report head/relative position 3,
with absolute position 153 frames. Reading the last data sector before an audio
track also reports the next track through idle DD. Typed audio-track data-read
refusals remain the toolkit's separate policy; they are not claimed to match
Gear's more permissive audio-sector READ behavior.

The independently compiled full original Gear core matches the bounded
head/command records across both ACK modes and CPU speeds. The toolkit runs
**371,952 native instructions with zero fallback**, plus an equal separate
interpreter run, through actual guest LDA/STA/NOP port operations. There are
**123,460 independent literal checks and 148 records across 36 case executions
per toolkit tier**. Full PC/MPR/physical/byte identities and independently
derived per-site retirements match. Four pure guards per native process and
38 rejection controls pass; all **626 final bindings** rehash unchanged.
Original Gear uses its actual command/register/device implementations through
an authored supervisor. This proves declared head/payload/status behavior,
not Gear CPU-retirement or exact drive-clock parity. The runtime's existing
distance-independent loading cadence and unknown-command policy are unchanged.

The fresh BIOS-backed Ys III TCP regression also passes **26,751 frames** from
authentic System Card reset through town, shopping/equipment and first-mine
attacks, rewards and damage. The newly emitted module executes
**791,721,517 native instructions, zero fallback/guard misses and 101,674 native
block transfers**. A fresh same-source no-module interpreter matches all
**629 checkpoints, 185 guest/window image and full-WRAM observations, 43,574
complete source identities/hits**, device state, **57,757,710 VDC wait ticks**
and digital PCM/bounded WAV. Root reviewed six new screenshots and actual RAM
milestones: 900→500→200 gold purchases, then HP 20→4, EXP 0→6 and gold 200→204.
The unchanged strict checker rehashes **1,176 files**; its only adaptations are
the new frozen path/source pin. All 25 prior route controls and eight cache
controls pass. The actual tested executable is a fresh verified warm restore
from this source, with an identical four-file cold/cache/warm package; cold
and warm observations are 160.53 and 16.23 seconds, respectively. SDK paths
are removed from its child environment, and its adjacent SDL DLL is checked
live. These are single build observations, not a new compiler benchmark.

This remains a finite internal native/interpreter retail regression. The
independent Gear command proof and Beetle media proof above have their own
scopes. The explicit `gear-good` unknown-CD policy remains required; no unknown
command, complete campaign, physical listening or hardware timing is certified.
Seven protected originals, old proofs, owner saves/install/launcher selection
remain untouched; all owned test hosts exit naturally. The Ys III project
retains its independent consumer pin.

Frozen implementation
[`fdfff5decbf362d88c6ee73c6a4f399ac2209c54`](https://github.com/rages4calm/pcenginerecomp/commit/fdfff5decbf362d88c6ee73c6a4f399ac2209c54)
has canonical compiler/runtime source
`5827c729dcba00705a52c445e8302c512e57cb85e335123fc90843ec9ff5e122`
over **68 files**, ABI **24**, and consumer/capture schemas **1**. Only private
CUE bookkeeping and existing drive-head behavior change; generated state
layout is unchanged. Existing valid CUE coordinates and compound identities
retain their behavior. Raw subchannel capture, exact program/gap/index/control
geometry for all DD responses, unmasked second-reference IRQ retirement,
bus-event ordering and broader title/hardware coverage remain open.

## Consumer package cache and ordinary CD I/O — preceding baseline

The preceding SDL/reference check passed **735 Python tests, zero skips, and
45 C++ suites**. No retail input is required by these tests. The optional
package-cache producer adds 23 storage tests, 17 declared-input/configuration
tests, eight consumer-wiring tests and one actual native cold/warm package
test. Existing save-export, reset and Arcade Card fixtures now assert the
new ignored-hole behavior while retaining real disabled-device refusal and
failed-run save-publication guarantees.

**Contributor tooling:** an explicit Windows x64 LLVM-MinGW/Ninja consumer
cache now freshly configures, audits actual CMake inputs/targets/flags and
normalized Ninja graphs, and hashes the declared module/toolchain/runtime/SDK
trees before lookup. Exact hits restore an immutable executable/DLL package
without consumer compilation/linking. Compiler-discovery probes may still run.
Cold builds audit actual compiler header dependencies; both paths recheck
inputs and issue a fresh build-only receipt. Corrupt, partial, linked or
mismatched entries stop explicitly. Normal uncached builds remain available.
This is a trusted toolkit/SDL configuration profile, not arbitrary CMake
hermeticity, changed-unit caching or runtime-loaded native modules. See
[BUILD_CACHE.md](BUILD_CACHE.md).

One real 43,574-site consumer qualification measures **154.17 seconds cold
versus 15.25 seconds warm**, including fresh configuration and input auditing.
All four executable/DLL files are byte-identical. These are one paired sample
under concurrent qualification work, not a general performance guarantee.
The actual restored executable runs the retail regression below with SDK
directories removed from child `PATH`; live process inspection confirms its
adjacent packaged SDL DLL. Eight additional read-only qualification mutations
reject dangling binary/descriptor labels, false commands/hit/execution claims,
changed keys/contracts and missing package files.

**Shared bus compatibility:** unassigned writes within the decoded CD window
`$1800..$1BFF` are ignored, preserving device/latch/gate/storage state while
counting accepted CD accesses. Ordinary System Card unused `$1C00..$1FFF`
reads return `$FF` and writes are ignored. HuCard routing, explicit Arcade Card
interception, identification pins and disabled known-device faults remain
separate. A bare sandbox does not acquire an ordinary hardware map. No new
device fields or state format are introduced. The authored exhaustive test
passes **31,464,248 checks**, with **5,230,464 instructions in each execution
tier**, including alias/value boundaries and pure guards.

An independently compiled original Geargrafx core passes **20 authored cases,
82,144 instructions per tier, 82,224 records and 2,038,488 independent literal
scalar checks per tier**. Native work has zero fallback. Raw CPU/device/WRAM/
BRAM records agree without projections; complete PC, all eight MPRs, physical
source bytes and per-key hits agree across native and interpreted work. Four
pure guard tests and 36 evidence rejection controls pass; all 453 reference
input/artifact bindings rehash unchanged. This uses explicit synthetic setup,
not firmware-formatting or physical reset qualification. Mesen source agrees
with the chosen strict CD decode; Beetle source instead aliases low register
bits and handles an absent Arcade window differently. Those additional
findings are source inspection only. See [CD_CONTROL.md](CD_CONTROL.md).

**Fresh retail regression:** a newly emitted observed-code module and the
actual warm restored package complete **26,751 frames**, with
**791,721,517 native instructions, zero fallback/guard misses and 101,674
native block transfers**. A fresh same-source no-module interpreter replay
matches all **629 checkpoints, 185 guest/window image and full-WRAM
observations, 43,574 complete source identities and per-key hits**, device/
queue/wait state and digital PCM/bounded WAV. Both retain **57,757,710 VDC wait
ticks**. Root reviewed six new screenshots for town movement, equipped Short
Sword/Leather Armor, mine entry and a drawn sword. Actual RAM records ordinary
900→500→200 gold purchases, then HP 20→4, EXP 0→6 and gold 200→204 in combat.
The independent checker rehashes 1,176 actual files; its 25 existing controls
retain the earlier comparison scope. Native/interpreter equality is internal
regression evidence; Gear device qualification is separate. The explicit
`gear-good` unknown-CD response profile is still required. No unknown command,
complete game, hardware timing or physical listening claim is added.

Frozen implementation
[`8add7506f75018d9b3b7517ada0b99db30bed16e`](https://github.com/rages4calm/pcenginerecomp/commit/8add7506f75018d9b3b7517ada0b99db30bed16e)
has canonical compiler/runtime source
`466e7e20c1691ee54bd6b32f52a76e402c32eeda7b8ae4a84ca49ba8f142b6e8`
over **68 files**, runtime ABI **24** and consumer schema **1**. Subsequent
test-fixture corrections preserve that canonical identity. Every retail
asset, translated module, cache package, save, capture and screenshot remains
private. No owner install/save/launcher selection was changed; owned test
hosts exited. The Ys III project keeps its independent consumer pin.

Next gates are broader independent CPU/device vectors and bus-event ordering,
unmasked second-reference IRQ retirement, additional HuCard/media profiles,
changed-unit build reuse and runtime-overlay contracts. Repeating this route
does not establish wider library coverage. See [ROADMAP.md](ROADMAP.md).

## Full-core second reference and code-free traces — preceding baseline

The preceding full SDL/reference check passed **686 Python tests, zero skips, and 44 C++
suites**. The new `pcerecomp.reference_trace` module validates bounded,
code-free JSONL and reports the first divergent instruction boundary. Engine
and fixture identities, complete MPRs, raw status/registers, physical PC,
master time and work-RAM hashes remain in the evidence. Invalid/truncated
streams stop explicitly. Twenty-seven authored parser/comparator tests cover
field integrity, closure, incompatible inputs, first differences, named scopes
and CLI refusal/output behavior. See [REFERENCE_TRACES.md](REFERENCE_TRACES.md).

A separately built original **Beetle/Mednafen PCE core** at
`b96c11e095b6a40a412d2da02766ae1c3f4fd539` supplies the second independent
execution path. The adapter builds the original CPU, memory, VCE/VDC, PSG,
input, mapper and support implementations with an authored observer, rather
than extracting instruction functions or sharing toolkit devices. Its
built-in instruction-step API runs actual guest instructions; original video
events and long-block continuation remain active. Bounded software frame
buffers satisfy the original renderer's requirements. Observation is repeated
to detect mutation, and the final raw 8 KiB RAM digest is independently checked
with Python. Optional CHD and physical-drive interfaces are disabled for this
HuCard-only fixture; no reference core is needed by baseline tests or shipped
as part of the runtime.

An entirely authored firmware runs **20 guest primer instructions** to set
mapping/register/status/stack state and clear WRAM, followed by **161 measured
instructions**. The measured sequence includes **130 NOP delay instructions**,
same-speed and cross-speed CSL/CSH, real timer enable/read/disable, IRQ-mask/
request reads and acknowledgement through mapped MMIO. CPU I and the IRQ mask
remain set: this is not interrupt-delivery qualification. The adapter now
explicitly refuses CPU-I-unmasked steps before executing them, including
primers and block continuations, rather than counting an IRQ-entry-only return
as an instruction. The static module
executes **181 native / zero interpreted instructions**; a separate interpreter
run executes 181, with **181 byte-aware source identities and per-key hits**
matching exactly. Native, interpreter and original Gear each pass **4,347
independently authored scalar checks** under their declared timing profiles.

The final full Beetle run matches **all 161 measured native and interpreter
CPU/WRAM trace states**, including the complete mapping, raw P and raw master
timestamps. All three measured origins are **590,628 ticks**, ending at
**594,912**. This uses `architectural-v1`: **only `mpr_latch` is excluded**,
because Beetle has no corresponding persistent latch. It is reported as null,
never fabricated. No initial clock-offset adjustment is needed. Default
`exact` comparison correctly rejects the latch mismatch at ordinal 0.

Original Gear's established cross-speed timing difference is preserved:
first divergence at **ordinal 7**, CSH, is **590,901 versus 590,919 ticks**.
All six differing timestamps are enumerated; other compared CPU/WRAM fields
match. The actual source uses three cycles at selected speed, whereas the
chosen toolkit/Beetle profile changes speed for the final cycle. Raw traces
are not rewritten. A separate six-instruction Beetle diagnostic also observes
multi-bit TMA returning **$22** for selected mappings **$11/$22**, versus the
toolkit's documented OR contract **$33**. That diagnostic is an actual Beetle
observation plus source-contract comparison, not a fresh all-engine parity
matrix or a hardware verdict. Reference engines can disagree in different ways.

Frozen implementation
[`cbcd997e6bae0cbaa368d59ba28882cead92096e`](https://github.com/rages4calm/pcenginerecomp/commit/cbcd997e6bae0cbaa368d59ba28882cead92096e)
has canonical compiler/runtime source
`0516f5759c80c572bcfc4b72273c08058984c0ca1a4531f788c225502d797ea6`
over **66 files**. Runtime ABI **24** and consumer/capture schemas **1** stay
unchanged. Trace format 1 is a separate diagnostic contract. Static emission
still has no execution-evidence claim until independently run. Final reference
builds use the actual frozen helper/source bytes; failed preflight attempts
remain separate. No CPU/device semantics were changed in this batch.

Reference-step hardening
[`b09f09e3da6f401dc1b9866fdef442709c54398a`](https://github.com/rages4calm/pcenginerecomp/commit/b09f09e3da6f401dc1b9866fdef442709c54398a)
preserves that same canonical compiler/runtime identity. A fresh original-core
build with the guard still matches all 161 measured states. Actual authored
CLI → NOP negatives exercise both measured and primer paths: each stops with
exit 1 before the unmasked NOP, without a complete final record or RAM export.
The measured case retains the one genuinely retired CLI rather than inventing
an additional instruction. Earlier reference builds remain labeled separately.

Remaining boundaries include IRQ delivery and internal timer-phase equivalence
across all references, bus-access timestamps, dynamic overlay source identity
in chronological traces, full CPU-family coverage, rendering/audio/CD parity
and hardware. These finite comparisons do not establish complete emulation.

A fresh official consumer build on the frozen **0516… / 66-file / ABI-24**
source re-emits the original unchanged ABI-24 observations. The isolated
**26,751-frame** Ys III TCP route reaches town movement, purchases/equipment
and first-mine combat with **791,721,517 native instructions, 101,674 native
block transfers, zero interpreter fallback and zero guard misses**. The new
same-source interpreter pair matches **629 checkpoints, 185 guest/window RGB
and complete WRAM observations, 43,574 full source identities and combined
per-key hits**, CPU/devices, PCM, bounded WAV and **57,757,710 VDC wait ticks**.
Fresh root image review and canonical RAM verify gold **900 → 500 → 200**,
then combat **HP 20 / EXP 0 / gold 200 → 4 / 6 / 204**. Twenty-four corrupted
inputs are rejected and one documented host-poll projection is accepted; all
1,161 qualified bindings are rehashed unchanged. This is native/interpreter
retail regression, not a Beetle CD-game comparison. The explicit `gear-good`
unknown-command response remains required. No owner save, installation or
launcher selection is changed; all owned hosts are stopped.

## Proven static MPR discovery — retained ABI 24 evidence

That batch's full SDL/reference check passed **659 Python tests, zero skips, and 43 C++
suites**. The compiler adds opt-in schema-2 analysis and direct emission across
proven TAM mapping changes. Legacy schema-1 analysis/emission stays available.
Conservative A/X/Y facts merge at logical-PC/full-MPR nodes; executing-page
remaps, multi-bit masks and repeated logical PCs retain distinct contexts.
Unknown mappings, indirect targets and callee return mappings stay unresolved.
All native dispatch still guards actual mappings and every fetched byte before
effects. Static facts do not replace runtime checks or establish execution.
See [STATIC_ANALYSIS.md](STATIC_ANALYSIS.md).

The **22 analyzer and five emitter/CLI tests** cover safe merges, pruning,
limits, page crossings, logical wrap, unknown facts, calls and rejection of
changed source/metadata. Bounds account for admitted exploration work even
when later precision loss prunes some reachable output. The CLI makes the
context mode explicit and prints full mappings in its listing.

An original authored HuCard program is discovered as **26 static sites across
six mappings**, then emitted directly from that analysis. It uses multi-bit
TAM to change the data and executing pages together, changes data banks,
loops and revisits a logical PC with different source bytes. A separate
original-Gear process and both toolkit execution tiers match **80 instruction
records / 1,600 independently authored literal checks per tier** across CPU
divisors 3 and 12. Records include PC, registers/status, complete MPRs, transfer
latch, WRAM results, physical PC and master ticks, with no field projections.
The actual generated run retires **80 native / zero interpreted instructions**;
all 26 full source identities and per-key hits match the interpreter. Its
**326 pure deadline, full-mapping and every-source-byte guard negatives**
preserve observed state. Already-pending IRQ guards, physical bus phases and
general executable-RAM mutation analysis are not qualified by this fixture.

Compiler candidate
[`c51f4b24ac5e0cf398a309f0c0233161d890738e`](https://github.com/rages4calm/pcenginerecomp/commit/c51f4b24ac5e0cf398a309f0c0233161d890738e)
has canonical compiler/runtime identity
`0556671b322a090232024d14f392d380d5b6647846f5a3b3d6ef5195c06d5d95`
over **65 files**. Runtime ABI **24** and capture/consumer schemas **1** stay
unchanged; the compiler source pin changes. Static analysis/manifests retain
`execution_evidence: false`; the separately captured authored retirements are
the execution evidence. No game-specific address or device behavior is added.

A fresh consumer build on that exact frozen source re-emits the original
ABI-24 observed-code capture without exclusions or relabeling. An isolated
**26,751-frame** ordinary-input Ys III TCP route starts at authentic System
Card reset and reaches town navigation, purchases/equipment and first-mine
combat. Actual native execution is **791,721,517 instructions and 101,674 block
transfers, zero interpreter fallback and zero guard misses**. The same-source
no-module interpreter replay matches all **629 state checkpoints, 185 guest/
window RGB and complete WRAM observations**, **43,574 full source identities
and combined per-key hits**, CPU/devices, digital PCM, bounded WAV and
**57,757,710 queued VDC wait ticks**. Twenty-five checker controls pass:
24 evidence corruptions are rejected and one explicitly permitted host-poll
projection is accepted. The final 1,161 bound inputs are rehashed unchanged.

Root reviewed fresh images showing town movement, the selected sword/armor,
the mine and a drawn sword. Canonical RAM confirms ordinary gold deductions
**900 → 500 → 200**, then combat progress **HP 20 / EXP 0 / gold 200 →
4 / 6 / 204**. This route uses observed-code modules: it checks consumer
compatibility after the compiler change rather than measuring retail static
CFG coverage. The new discovery feature is independently executed by the
authored fixture above. No RAM edits, owner-save/installation/selector writes,
gameplay expansion or consumer migration are involved. The explicit
`gear-good` unknown-CD response profile remains required; this batch does not
implement the unknown command or certify a complete port, listening or hardware.

## Queued VDC death/retry and guest SAVE/LOAD — retained ABI 24 evidence

That batch's full check passed **632 Python tests, zero skips, and 42 C++ suites**.
`tests/test_queued_persistence.py` adds an entirely authored native consumer
that couples real queued VRAM/DMA waits to two isolated persistent launches
and a volatile reference. All three execute 200 native instructions with zero
fallback/guard misses and 128 completed DMA words; counter values are 1 → 2
across sessions and 1 again for volatile memory. Exact payloads and persistence
hashes are checked. The final focused test also passes after strengthening the
volatile assertions. This is an authored counter contract, not a game filesystem.
See [PERSISTENCE.md](PERSISTENCE.md).

Two fresh retail cases extend queued timing through the original guest code:

| Case | Frames | Native instructions | Native blocks | Source identities |
|---|---:|---:|---:|---:|
| Natural death and Retry | 28,285 | 840,056,911 | 109,452 | 44,412 |
| Guest SAVE/change/LOAD | 27,845 | 823,837,671 | 105,236 | 41,304 |

Both native cases have **zero interpreted instructions and zero guard misses**.
Their no-module interpreter replays conserve all combined instruction/block
counts. Strict comparison covers **657 checkpoints / 195 guest-window/WRAM
observations** for death and **697 / 209** for SAVE, full CPU/device/source/PCM
reports, finalized byte-aware source identities with per-key combined hits,
waits, bounded WAV and identical same-contract 2 KiB exports. Dynamic VDC wait
ticks are **62,010,537** and **59,603,445** respectively. Twenty-two negative
controls reject changed evidence. Capture metadata preserves code-free live
multiplicity without inventing append-ID-to-byte associations.

Natural combat takes HP **4 → 0** with visible GAME OVER and progress
EXP 6 / gold 204. Ordinary Run confirms Retry; after the actual loading
transition, canonical state is **HP 20 / EXP 0 / gold 200**, with a visible cave
entrance and ordinary movement. This is an area-entry rollback, not preservation
of the last combat gains. The unseeded case exports unchanged zero-filled
backup memory: it does not implicitly format memory or create a guest SAVE.

The separate SAVE recipe explicitly copies a blank 2 KiB image previously
formatted through the real System Card UI. Startup metadata is validated as
actually seeded, rather than projected onto an unseeded contract. A previously
empty private slot 2 is selected and saved at Sarina with **HP 20 / EXP 0 /
gold 200**. Ordinary mine combat changes canonical RAM to **4 / 6 / 204**.
The LOAD preview already displays saved HUD values while canonical RAM remains
changed. Only actual I-confirm plus settling restores canonical **20 / 0 / 200**
and the Sarina scene; ordinary movement/interaction then works.

The saved export differs from the authenticated blank seed at **28 byte
positions**, and native/interpreter exports match exactly. This is a snapshot
difference count, not a write count or serialized record length. No whole-WRAM
saved-versus-loaded or exact-XY requirement is imposed; the guest initializes
working state and resumes at its defined area entry. The canonical compiler
and runtime remain source
`5d44f16e42c4de2a90984581f17f4c4690017babd2eca42cc3715c042ec9301c`
over **65 files**, ABI **24**, consumer/capture schemas **1**. Newly observed
supported source/MPR variants were captured and genuinely emitted; no shared
runtime defect, HLE save service, hidden format or new save-state ABI was added.

An isolated original Geargrafx reference independently observes natural
HP **20 → 2 → 0**, GAME OVER and ordinary Retry to **20 / 0 / 100**. A separate
validated postboot episode saves private slot 2 at **30 / 188 / 228**, changes
progress through combat to **27 / 194 / 232**, observes the same misleading
preview distinction and restores canonical **30 / 188 / 228** after actual
LOAD. Its backup image differs at 33 positions after SAVE and stays stable
through the later actions. The retained Gear seed declares a different backup
header from the native BIOS-formatted seed. These are independent semantic
outcomes, not native/Gear seed, header, byte, reset, frame or exact spawn parity.
Only episode initialization uses debugger checkpoint loading; the tested LOAD
is the actual game command. No health, position, quest or code edits are used.

All cases use private inputs/exports. No owner save, installation or launcher
selection is replaced. A separate **6,062-frame fresh-process smoke test** imports
the SAVE case's successful-stop raw export as an explicit read-only seed.
Authentic reset and Continue recognize the created file; actual LOAD restores
the saved **20 / 0 / 200** town state and ordinary movement/interaction works.
It executes **155,898,079 native and 13,402,080 interpreted instructions**.
This is mixed execution, with no cold native/interpreter pair or zero-fallback
claim. It verifies import after orderly export, not immediate disk publication
at the guest SAVE command or crash/power-loss durability.

Full campaign, physical listening/hardware, exact native/Gear retail clock
parity and emulator machine-state persistence remain unqualified.
The explicit `gear-good` unknown-CD response profile is still required.

The following earlier queued town/mine receipt retains its original counts
and scope.

## Queued VDC gameplay and interrupt qualification — ABI 24 unchanged

Verification commit
[`8aa3208805e5d635b04dab15e7893eb9bc671da3`](https://github.com/rages4calm/pcenginerecomp/commit/8aa3208805e5d635b04dab15e7893eb9bc671da3)
adds authored reference fixtures without changing canonical compiler/runtime
source `5d44f16e42c4de2a90984581f17f4c4690017babd2eca42cc3715c042ec9301c`
(**65 files**, ABI **24**, consumer/capture schemas **1**).

That earlier full check passed **631 Python tests, zero skips, and 42 C++
suites**. A new separately compiled original-Gear proof passes **54 cases /
2,484 records / 972 independent literal checks per tier**, with **1,188 actual
native retirements**, zero interpreter fallback and 14 source identities.
Both CPU speeds, three VCE speeds and remaining timer phases of 18, 30 and
60 master ticks cover underflow during a real VRAM-DMA-blocked CPU read. Timer, CPU/vector/stack,
queue, wait counters and timestamps match exactly with **no projections**.
The handler disables and acknowledges the timer and returns with RTI;
unmasked, CPU-I-masked and IRQ-mask-deferred delivery are covered.

An original-Gear callback observes every underflow at master tick 3,120 while
both dynamic waits and DMA remain active. The **108 pure source/MPR guard
negatives** cover an armed timer and pending VRAM before underflow, without
claiming already-asserted-IRQ guard coverage. Other instruction phases,
mixed IRQ sources, physical bus timing and hardware remain unqualified.
See [VDC_ACCESS.md](VDC_ACCESS.md) and the reproduction command in
[DEVELOPMENT.md](DEVELOPMENT.md).

### Fresh ordinary town and first-mine route

A new **26,751-frame** TCP route starts at authentic System Card reset and
uses ordinary controller inputs with debugger writes disabled. It covers
town movement, Short Sword and Leather Armor purchases/equipment, actual
mine entry, a visibly drawn sword, an enemy reward and received damage.
Gold changes **900 → 500 → 200** for the purchases; the final 240-frame cave
combat changes **HP 20 → 4, EXP 0 → 6 and gold 200 → 204**. The player remains
alive. No quest, position, health, code or owner-save assistance is used.

The first completed exploration exposed **229 fallback hits on 158 source
identities**: 138 keys for previously observed instruction bytes at the same
PC/physical addresses under new full-MPR contexts, four new byte variants
and 16 new PC/physical identities. None
hit the retained historical jump exclusion. These were supported coverage
gaps, not a confirmed runtime defect. A complete actual ABI-24 capture was
re-emitted through the normal compiler interface, without relabeling old
observations, producing **43,574 observed native sites** and no exclusions
or unsupported observations. This is the catalogue size, not 43,574 newly
added sites. The canonical compiler/runtime and ABI are unchanged.

An official consumer build and separate no-module interpreter then replay
the exact finite controls. The native run executes **791,721,517 native /
zero interpreted instructions**, **101,674 native block transfers**, zero
guard misses, **89,129 IRQ entries/RTIs**, **57,757,710 dynamic VDC wait ticks**
and 775 sectors. The interpreter conserves all combined instruction and
block counts. Both queues settle idle at natural quit. The combat interval
alone executes **7,597,903 native instructions with zero fallback**.

An independent post-run checker requires more than successful supervisor
closure. It verifies **629 checkpoints**, **185 guest/window RGB and full
8 KiB WRAM observations**, complete CPU/device/source/PCM reports, wait
counters and all **43,574 finalized byte-aware PC/MPR/physical source keys
with combined per-key hits**. The bounded WAV prefix is byte-identical;
its ten seconds cover silent boot, while full-route digital PCM is checked
through the source report. Thirteen negative controls reject changed evidence.

Only the documented TCP token/port, execution-tier counters, validated paused
WAV drain/muted SDL submitted/dropped counts and `desktop.polls` are projected;
other host diagnostics remain checked. The endpoint validator checks every
shared CPU/device field and explicitly validates TCP quit's neutral controller
masks without guest clock advancement. Paused source/pixel/WRAM inspection
preserves the complete observed guest/PCM state. Code-free live source rows
are checked as metadata/hit multisets with cardinality and local-ID continuity;
they cannot associate append IDs with finalized byte variants. See
[DEV_SERVER.md](DEV_SERVER.md) for that distinction.

Separately isolated original Geargrafx reproduces ordinary town/menu input
and cave sword/reward/damage outcomes from a previously validated unassisted,
equipped postboot checkpoint: **HP 20 → 10, EXP 0 → 12, gold 100 → 108**.
Its equipment and starting history differ from the fresh native route. This
is independent outcome evidence, not matched retail boot/frame/clock/pixel
parity; the exact authored timer/queue traces have their separate scope above.

Power-interrupted and diagnostic-wall-limit exploration records are retained
and excluded from successful whole-route qualification. All seven protected
originals and explicit test packages remain unchanged. The independent Ys III
project legitimately promoted its own launcher selection while this work ran;
both selector epochs were preserved, without restoring or overriding it.
All owned test hosts stopped. No live installation or owner save was modified.

This batch does not certify queued-profile campaign/boss completion,
SAVE/LOAD beyond the stated route, physical listening, analog video/audio or
hardware timing. The existing explicit `gear-good` unknown-CD response remains
required. The following closed ABI-24 boot/intro receipt retains its original
counts and narrower scope.

## Queued VDC VRAM accesses and wait states — ABI 24

The current implementation is
[`88789045f43abc15b643fb74d2d73345ef386a58`](https://github.com/rages4calm/pcenginerecomp/commit/88789045f43abc15b643fb74d2d73345ef386a58),
canonical source
`5d44f16e42c4de2a90984581f17f4c4690017babd2eca42cc3715c042ec9301c`
over **65 files**, runtime ABI **24**, consumer/capture schemas **1**. Original
ABI-12 through ABI-23 captures retain their labels and can be re-emitted;
rebuild generated modules and runtime together.

Clocked profiles now queue CPU VRAM requests with real BUSY, delayed buffer
publication, live-register completion, DMA precedence and modeled display
access slots. CPU waits add three master ticks at either CPU speed while
devices and IRQ sampling advance. ST ports, mapped accesses and block
transfers use their documented fixed-cycle ordering. The explicit immediate
profile retains the previous aggregate timing path. Status/inspection stays
pure. See [VDC_ACCESS.md](VDC_ACCESS.md).

The SDL/reference build passes **627 Python tests, zero skips, and 42 C++
suites**. This includes **49,279** new queue expectations and eight actual
headless/SDL TCP cases. The separate original-Gear comparison passes **615
cases / 2,556 records**, with **3,678 independent literal checks per tier**,
**582 actual native retirements**, zero fallback and 24 pure guard negatives.
All 12 actual CPU cases match registers and master timestamps, including
both CPU speeds, three VCE speeds, ST ports, mapped I/O, TIA/TAI, DMA/BUSY
and draining both pending requests.

Exactly 99 MWR3 background read-bus differences are retained and reported:
Gear's four-bit background renderer differs from the toolkit's previously
Mesen-qualified two-bit profile. Queue/timing fields remain exact; this is
not whole-renderer equality. Timer progress during stalls has authored local
checks; independent timer-underflow/IRQ-entry traces during those stalls
remain deferred. Electrical bus phases, other instruction access phases and
complete-game compatibility remain unqualified.

### Fresh Ys III TCP qualification

The original ABI-17 observations were re-emitted for ABI 24 and built through
the official consumer interface. The generated-source audit covers 258
artifacts: 257 ABI assertions and exactly 586 dedicated ST bodies changed;
all other translated bytes, source guards and manifest metadata are retained.

Three fresh 5,526-frame reset/menu/intro runs use the same 21 ordinary controls
and 20 paused checkpoints. The explicit immediate run matches retained
ABI-18 guest state, source hits, both whole images and bounded PCM/WAV,
with **152,630,394 native retirements / zero interpreted**. Queued native
execution records **152,395,920 native retirements / zero interpreted**,
**6,440 native block transfers**, zero guard misses and **3,116,439 dynamic
VRAM wait ticks**. A separate same-source interpreter desktop reproduces all
20 guest/source/PCM states, both images, bounded WAV, final CPU/device state,
wait counts and combined hits for all **11,711 source identities**. Execution
tier and host presentation drain are the only documented comparison
projections. Both queues settle idle before natural quit.

These fresh runs cover authentic System Card reset, firmware/menu input and
the opening sequence, not queued-profile town navigation or combat. The
existing explicit `gear-good` unknown-CD response profile is retained; this
does not implement the unknown command. No RAM edits, boot skips, new owner
saves or live installation are used. The actual consumer selector and seven
protected originals remain unchanged. Packaged runs use adjacent runtime
DLLs on a restricted PATH, without an SDK workaround. The independent Ys III
chat retains its own selected package and migration schedule.

### Previous closed ABI-23 receipt

The following section retains the earlier batch's original source identity,
counts and scope. Its immediate timing limitations describe that historical
implementation; current queued access behavior is described above.

## VDC VRAM bus and fetched rendering — ABI 23

Implementation
[`82637854b19fde3b00c2b7fb689687c366602c20`](https://github.com/rages4calm/pcenginerecomp/commit/82637854b19fde3b00c2b7fb689687c366602c20)
has canonical compiler/runtime source digest
`3758496d120f58b6f4c5afc30b77830fa2a8c1c2e42f82c3dd757bc20f8fb9b8`
over **65 files**, runtime ABI **23**, consumer/capture schemas **1**. Original
ABI-12 through ABI-22 captures keep their labels and can be re-emitted; rebuild
modules and runtime together.

CPU VRAM prefetch, VRAM/SATB DMA and modeled sprite/background fetches now share
a retained 16-bit read bus. Driven reads update it; upper-half reads retain it.
Writes keep their ignored-upper-half and pointer behavior. CPU read buffering
remains separate. Continuous sprites consume fetched planes, position, palette
and priority. Background scroll/mode and read-bus tracking advance even when
presentation is disabled. Pure current-state snapshots, paused inspection and
native guards do not drive the bus. The timing model remains aggregate; CPU
VRAM access queues, dynamic slot waits and electrical bus phases are not added.
See [VRAM_BUS.md](VRAM_BUS.md).

The dedicated C++ suite passes **100,072 authored expectations**, including all
65,536 read addresses, address increments/wrap, high-source/destination DMA,
SATB crossing, fetched sprite races, two-bit upper patterns and output-on/off
bus equivalence. Four actual headless/SDL TCP tests check guest port results,
aliases, DMA/SATB, pure capture/status inspection and unchanged input files.
These host fixtures execute interpreted guest code; actual translated native
device execution is qualified separately by the independent reference run.

The previous scanline fixture expected a new MWR mode before its real latch
event. It now advances through VSW before comparing settled pixels, retaining
the same 6,403 positive scroll/sprite/history expectations. No retail images
are substituted as expected values.

The stable SDL/reference build passes **42 suites: 610 Python tests with zero
skips plus 41 C++ suites**. Geargrafx, direct toolkit device operations and the
interpreted/native guest probes match **31 cases / 65,722 records / 135,397
independent literal values per path**. The two CPU cases retire **324 native /
zero interpreted instructions**, covering 162 complete source identities and
four MPR contexts, with four pure source/mapping guard negatives. CPU timestamps
match without projection. All eight subprocess stages and 14 preservation
groups (542 bindings) pass. Queued Gear port completion is explicitly settled;
physical CPU access latency is not certified.

Separately, four unchanged extracted MesenCE functions match **262,144 two-bit
fetch cases / 2,097,152 pixels / 262,144 held words**, totaling 2,621,440 bytes.
Each path passes 2,359,296 independent literal checks, including both CG halves
and bit-11 undriven patterns. The debugger-notification stub only counts events.
This is function-level evidence rather than a full Mesen or timing run. The
final probe is an immutable copy made after the stable build; earlier proof
epochs that bound a subsequently rebuilt central executable remain separate.
See [REFERENCE.md](REFERENCE.md) for exact source and adapter scope.

A freshly regenerated ABI-23 Ys III package passes the existing **5,526-frame
TCP reset prefix** on an OS/PowerShell/Git-only PATH: **152,630,394 native / zero
interpreted instructions**, 6,440 native block operations, zero guard misses
and zero RAM edits. All 20 guest checkpoints, 21 controls, complete PNGs, bounded
WAV, cumulative PCM and per-source hit counts match the retained ABI-18 run.
The comparison validates the original bounded pending host-audio drain contract
at every checkpoint and projects only submitted/dropped presentation counters;
guest PCM frames/hash and the settled full runner remain exact. Original ABI-17
input labels remain unchanged; fresh captures retain ABI 23. Pure initial/final
capture inspection preserves all 11,679 identities and 46 repeated pages.
Natural quit returns zero, the child stops, seven original inputs and the actual
peer selection remain unchanged. The route retains its explicit `gear-good`
unknown-command policy, disabled Arcade Card and muted presentation; it does
not qualify additional campaign, physical audio or retail undriven-read usage.

## Isolated BRAM persistence and Windows packaging — ABI 22

This and subsequent sections retain historical pins and counts. Use the
ABI-23 section above for current builds.

Implementation
[`05533938a934b823f0ad9590367cac85a797234b`](https://github.com/rages4calm/pcenginerecomp/commit/05533938a934b823f0ad9590367cac85a797234b)
has canonical compiler/runtime source digest
`61c02a0f766f39d8dbf6b66605680679e541255a1d3be628c59321c55a2c9abe`
over **65 files**. Host-only persistence/packaging retains runtime ABI **22** and
consumer/capture schemas **1**. Rebuild hosts from the pinned source to expose
the new options; existing translated ABI-22 operations keep their semantics.

Both hosts support explicit atomic create-new raw `--bram-out` export after
successful finalization, preserving the old read-only `--bram` seed. Checked
consumer sessions add safe namespaces, media/firmware/save-contract bindings,
strict bounded checksummed envelopes, crash-released process locks and explicit
atomic publication. CUE component hashes participate in compatibility. Corrupt,
mismatched or concurrently edited stores stop; faults, unsupported code and
wall-time interruption cannot implicitly publish a session. Windows command
arguments and relevant file opens also preserve Unicode paths. Default volatile
recipes and guest clocks/gates/source guards remain unchanged.

Windows consumer builds scan linked PE imports recursively and package resolved
non-system DLLs, including the selected SDL and compiler runtimes. Unresolved or
conflicting dependencies stop the build. Fresh analysis inputs avoid stale
output-DLL shadowing. The tested LLVM/MinGW packages need libc++ and libunwind;
neither their SDK nor compiler directories need to remain on the runtime PATH.
Windows-root dependencies and API contracts are excluded; universal MSVC CRT
redistribution and optional runtime-loaded backends are not qualified.

The final host also reports current combined input masks when `set_input` or
`clear_input` and `status` arrive in one TCP poll. A pure shared getter removes
the previous deferred-report phase without changing guest input relatching or
simulation cadence. Deterministic same-send tests exercise both actual hosts,
all five slots and script/network OR behavior while full paused guest state
remains unchanged. The earlier clean-PATH Ys failure was isolated to this
host field and retained separately; its comparator was not relaxed.

The fresh final SDL/reference build passes **41 suites: 597 Python tests, zero skips,
plus 40 C++ suites**. New coverage includes 24 real headless/SDL export tests,
20 session tests (including real process contention/crash release), five
reference-supervisor tests and four consumer contract tests. Four packaging
checks and two same-send input-status tests exercise the final host fixes;
existing tests remain in the full run. See [PERSISTENCE.md](PERSISTENCE.md) for post-publication
failure, directory durability and cooperative-lock limits.

The independent Geargrafx/interpreter/emitted-native comparison matches **two
speed cases / 44 records / 28,842 literal values per path**, with full 2 KiB BRAM,
gate, 16 work-RAM bytes and CPU/MPR timestamps. Actual native execution retires **20,642
instructions / zero interpreted**, covering 90 full source identities in six
MPR contexts. Four raw exports per path and fresh-instance reload checks preserve
locked backing bytes; the new toolkit export primitive is exercised directly. All eight
recorded stages and 14 preservation groups pass. Gear's formatted default,
authored fixture configuration and host-policy proof boundary are disclosed in
[REFERENCE.md](REFERENCE.md).

The device oracle uses the original persistence freeze `aafd99e` / source
`67a34d245e09e2bb9890d794c06003e338163d54ec0205712f5da2dfc5129095`
over 64 files. The final source bridge permits only the consumer CMake helper,
its new dependency script and the pure host-input reporting change in
`headless.cpp`. All other runtime and Python source bytes, including device
semantics and the raw-export helper, are identical. The source bridge is checked
separately from fresh final-package execution.

Three freshly built, exactly pinned authored consumer packages pass on a
Windows/System32/Git-only runtime PATH. Headless and SDL first/reload/default
launches each execute **200 native / zero interpreted instructions**, with zero
guard misses and locked BRAM. Saved counter bytes advance from one to two across
processes; default volatile launches leave the stored envelope unchanged.
Two one-frame TCP save/reload sessions each retire **7,451 native instructions**,
with zero interpreter fallback, guard misses or RAM edits, and quit naturally.
Live module inventories verify the adjacent packaged libc++/libunwind files;
all owned processes stop. This is an authored counter, not a retail save route.

The fresh final native Ys III package completes the existing **5,526-frame TCP
reset prefix** on an OS/PowerShell/Git-only PATH: **152,630,394 native / zero
interpreted instructions**, 6,440 native block operations, zero guard misses,
zero RAM edits and 177 sectors. All 20 guest checkpoints, 21 controls, both
whole PNGs, bounded WAV, cumulative PCM and finalized per-identity capture hits
match the retained ABI-18 run. Original profile labels remain ABI 17; the new
capture retains ABI 22. Initial/final capture inspection is pure, including
11,679 identities and 46 repeated pages. Originals and actual selected peer
package remain unchanged; natural quit returns zero and the child stops.

At the final paused route checkpoint, two **host presentation** counters are
25 frames behind the baseline: submitted/dropped 4,073,390 versus 4,073,415.
Produced guest PCM and its hash are exact. The original replay already permits
up to 8,192 pending presentation frames; later inspection and the finalized
runner drain all 4,073,415 frames with no runtime loss. The stronger raw outer
comparison's failure is retained. A separate offline validator admits exactly
those two fields at that single index and literal 25-frame difference, checking
every other raw field and the complete settled result unchanged. It launches
no additional guest and never rewrites the execution receipt. Muted output
does not qualify listening, analog hardware or further campaign coverage.

A new namespace is deliberately unformatted. The consumer must qualify its
actual guest format/save/reload and preferred startup flow before claiming the
blank-memory warning is gone. No owner save discovery, menu bypass, snapshot
format or automatic consumer-package migration is introduced.

## CD sense and typed read recovery — ABI 22

This and subsequent sections retain their historical source pins and counts.
Use the explicit-persistence section above for current builds.

Implementation
[`c6525a278f13709ecc39a2cb85be1b3ebf17a430`](https://github.com/rages4calm/pcenginerecomp/commit/c6525a278f13709ecc39a2cb85be1b3ebf17a430)
has canonical compiler/runtime source digest
`79f5e81b0f6fea41d468e64cc1433ebaaf643ea49ac29c3a45f456b2ad44dd91`
over **62 files**. Runtime ABI **22** adds pending sense context and counters;
consumer/capture schemas remain **1**. Original-labeled ABI-12 through ABI-21
observations remain compiler inputs; regenerate modules and rebuild runtime.

REQUEST SENSE `$03` returns the fixed NEC 18-byte payload, independently of
allocation byte, with clear-on-dispatch behavior, successful-command retention
and warm-reset preservation. Typed media read errors retain key/ASC/ASCQ and
host-only failure-LBA diagnostics, so a guest can request sense and retry.
Source changes, missing configuration, host I/O and opaque decoder failures
remain terminal. A failed CHD decode also invalidates its old cache tag before
reuse. Healthy runs with no sense/error activity retain their metadata shape.
See [CD_SENSE.md](CD_SENSE.md) for exact mappings and reference differences.

The fresh SDL/reference build passes **41 suites: 540 Python tests, zero skips,
plus 40 C++ suites**. The new sense suite passes **313,508 authored checks**
covering all allocation bytes, response tuples, lifetime/reset/abort, retry,
both execution tiers/speeds, fatal boundaries and pure native guards. READ
passes 621,096 checks; provider suites pass 24,947 ISO/CHD and 13,081 CUE checks,
including identity precedence and failed-decoder cache recovery. Two actual
host tests retrieve no-error and missing-medium responses across warm reset,
verify repeated sense clears the context and leave files/debug-write counters
unchanged. These host tests execute interpreted guest code.

The final isolated, unchanged Beetle SCSI core matches **four groups / 288
records / 6,836 response-data bytes**, including all 256 allocation values.
Geargrafx matches **eight baseline transport responses exactly**. Its four
REQUEST SENSE responses deliberately differ: no payload versus the toolkit's
18 bytes. Eight known error replies retain the exact Beetle status/message
`$01/$00` versus toolkit `$02/$02` distinction; every other compared field is
equal. Only that explicit wire tuple distinction is allowed; this is a settled
protocol comparison, not clock parity.

Actual interpreter capture, emission and compilation produce a native guest
that performs READ-on-audio → CHECK CONDITION → REQUEST SENSE → TEST UNIT READY.
It executes **19,618 native / zero interpreted instructions**, covering **442
full source identities / three MPR contexts**. Full CPU/RAM endpoints and
per-identity hit totals match training. Its diagnostic error count is one;
pending sense is cleared after the request. All 15 recorded subprocess stages
exit zero and all 16 preservation groups pass. Framework/media substitutions,
ACK and validation boundaries are disclosed in [REFERENCE.md](REFERENCE.md).
This does not certify hardware timing, ECC, full CD protocols or a campaign.

A freshly regenerated ABI-22 Ys III consumer also passes the existing
**5,526-frame TCP reset prefix**: **152,630,394 native / zero interpreted
instructions**, 6,440 native block operations, zero guard misses and zero RAM
edits. All 20 full paused checkpoints (apart from RPC IDs), 21 control actions,
two complete PNGs, bounded WAV, cumulative PCM and per-identity source hits
match the retained ABI-18 qualification. Original profile labels remain ABI 17;
the fresh actual capture remains ABI 22. The unchanged route performs no sense
requests or diagnosed read errors, so `cd_sense` is correctly absent. Recovery
semantics are qualified separately by the authored/reference tests above.

Initial and final live capture inspections leave full guest status unchanged
and the capture file empty until natural quit. All 11,679 retained identities
and 46 repeated source pages match the finalized capture as a multiset,
preserving duplicate visible variants. The run exits naturally with status 0;
seven protected originals, the immutable 31-file historical harness snapshot
and the peer's actual selected package remain unchanged. It uses ordinary
Super reset with Arcade Card disabled and muted presentation. No peer ABI
migration, new campaign route, owner installation, listening or hardware claim
is implied.

## Timer phase and paused capture inspection — ABI 21

This and subsequent sections retain their historical source pins and counts.
Use the ABI-22 section above for current builds.

Implementation
[`d813bd911571375e701241bd623f343119845726`](https://github.com/rages4calm/pcenginerecomp/commit/d813bd911571375e701241bd623f343119845726),
with a reference-only fixture configuration correction at
[`e45f57c9255983a503655df417a28c7e04103bb6`](https://github.com/rages4calm/pcenginerecomp/commit/e45f57c9255983a503655df417a28c7e04103bb6),
has canonical runtime/compiler source digest
`e4c078d136b76775bcc296e1d2857bbad520716afa6ea9b607e86fcb89d9ebba`
over **62 files**. Runtime ABI **21** adds the stopped timer divider phase;
consumer/capture schemas remain **1**. Re-emit original-labeled ABI-12 through
ABI-20 captures and rebuild modules/runtime together.

The disabled timer now distinguishes its untouched reset phase from a timer
that has been enabled and stopped. Initial reads, reload-only writes and
repeated control writes preserve their source-backed values; running edges,
IRQ acknowledgement and the existing delivery profile retain their contracts.
See [TIMER.md](TIMER.md).

Both hosts expose paused `capture_summary` and bounded `capture_sources`
queries. They report full-context retired source spans, capture-local identity
IDs, actual/retained execution-tier counts, window and completeness/loss without
bus reads, guest clock progress or finalizing the private capture. The strict
Python client can collect all pages at one retirement token. This is a bounded
set of encoded pre-retirement spans, not a chronological trace or bus-read log;
source absence requires a complete relevant window and backing-alias reasoning.
See [DEV_SERVER.md](DEV_SERVER.md#paused-code-capture-inspection).

The SDL/reference build passes **40 suites: 532 Python tests, zero skips,
plus 39 C++ suites**. The dedicated timer suite passes **39,710 authored
expectations**, covering reset/control phases, all reload bytes and I/O
mirrors, both execution tiers/speeds, IRQ/RTI, block transfers and pure guards.
The direct capture suite passes 22 checks; the expanded TCP protocol suite
passes 141. Eight actual headless/SDL host tests exercise more than 256
self-modified identities, paging, stale-token refusal, deferred windows,
capacity loss and unreadable port-source observations. Repeated queries leave
guest state unchanged, and final capture bytes match query-free runs.

An independent frozen Geargrafx adapter, interpreter and emitted/compiled
native module match **five cases / 1,389 observations**, each passing **631
literal checks**. The actual native guest retires **756 instructions, zero
interpreted**, with 579 source identities in three full MPR contexts. CPU
timestamps remain part of the comparison. Explicit synthetic initial speeds
avoid the already documented cross-speed CSH discrepancy; the initial failed
fixture remains retained. The final reference-only fixture revision is
[`ef843af3a82f9838b3de38c771860e5bd552abae`](https://github.com/rages4calm/pcenginerecomp/commit/ef843af3a82f9838b3de38c771860e5bd552abae),
with the same canonical runtime/compiler digest as the consumer freeze.
See [REFERENCE.md](REFERENCE.md) for exact configuration and proof boundaries.

A freshly regenerated ABI-21 Ys III consumer passes the existing **5,526-frame**
TCP reset prefix: **152,630,394 native / zero interpreted instructions**,
6,440 native block operations, zero guard misses and zero RAM edits. All 20
raw paused checkpoints (apart from RPC IDs), 21 control actions, two complete
PNGs, bounded WAV, cumulative PCM and final source-hit evidence match the
retained ABI-18 qualification. The original source profile remains ABI 17;
fresh actual capture files retain ABI 21.

At that final pause, the actual public client inspects all **11,679 retained
identities**, then repeats all **46 source pages** at the same epoch. Initial
and final queries preserve the full guest status, and the capture file remains
empty until natural exit. The live source-span/hit multiset, including duplicate
visible variants, matches the final private capture exactly. The package quits
naturally with exit 0; protected inputs, the peer's selected launcher and owner
saves remain unchanged. This is the existing finite route with Arcade Card
disabled and muted presentation, not additional campaign, physical hardware,
listening or peer-package migration qualification.

## Arcade Card Duo expansion — ABI 20

This and subsequent sections retain their historical source pins and counts.
Use the ABI-22 section above for current builds.

Implementation
[`bd770a16b80f3cb00d6f89ea725c64623338a386`](https://github.com/rages4calm/pcenginerecomp/commit/bd770a16b80f3cb00d6f89ea725c64623338a386)
has canonical source digest
`f4a648f8d707be4fe4dfb0968f26fa048430c708274d70dd078be87a62ca1156`
over **62 files**. Runtime ABI **20** owns an optional Arcade Card device;
consumer/capture schemas remain **1**. Retained ABI-12 through ABI-19 inputs
keep their original labels and must be re-emitted/rebuilt for 20.

Explicit Super System Card reset recipes accept `--arcade-card duo` or
`[boot].arcade_card = "duo"`. The expansion supplies 2 MiB RAM, four independent
data ports and mapped I/O windows, address/offset/increment controls, triggers,
shift/rotate and identification registers. Disabled profiles retain their
metadata shape and behavior. Pure peeks, native source guards, loader writes
and debugger RAM operations cannot mistake these side-effecting windows for
ordinary RAM. The interpreter still consumes live port-sourced instruction
bytes; captures mark those unreadable rather than inventing native identities.
See [ARCADE_CARD.md](ARCADE_CARD.md) for the exact profile and limits.

The fresh SDL/reference build passes **38 suites / 511 Python tests, zero
skips**. The Arcade C++ suite passes **3,515,903 authored expectations**,
covering control arithmetic, all window offsets, register/hole boundaries,
shifts, native/interpreted ordinary instructions and block transfers, setup,
loader refusal and side-effecting instruction fetches. Six actual host tests
cover wrapped guest transfers, all ports, rotation, input/release, debugger
refusal and invalid attachment recipes.

Geargrafx, the toolkit interpreter and actual emitted/compiled native code
match **four cases / 28,494 observations**, with **28,363 independent literal
checks per path**. Actual training yields **123 identities / five full MPR
contexts**; the main native stream executes **128 native / zero interpreted
instructions**. Twenty-eight guard checks use four authored source patches
with bytes restored; loader generations retain their intentional changes.
A separate port-sourced LDA test matches five observations and three literal
checks in Gear and the interpreter: one retirement is correctly reported as
unreadable, with zero captured identities and no native promotion. Reference
configuration shims and whole-transfer observation grouping are disclosed in
[REFERENCE.md](REFERENCE.md); electrical bus phases are not certified.

Two fresh official authored consumer packages, headless and SDL, each execute
**10,000 native instructions**. Separate ten-frame TCP routes each execute
**248,833 native / zero interpreted instructions**, including **5,468 native
block transfers**, with zero guard misses or RAM edits. Five input states and
release exercise all four ports, wrapping transfers and the shifter. Full
guest checkpoints and per-identity capture hits match the interpreted training
route; input files remain unchanged and natural quit returns 0. Two changed
reset-opcode negatives stop at zero guest ticks before retirement. These are
integration checks, separate from independent device evidence. No retail
Arcade title, Pro board, persistence or hardware qualification is claimed.

The existing Ys III reset prefix also passes on a freshly emitted and built
ABI-20 consumer: **5,526 frames, 20 paused checkpoints, 21 control actions,
152,630,394 native / zero interpreted instructions**, 6,440 native block
operations and zero guard misses or RAM edits. Full checkpoint state (apart
from RPC request IDs), both complete PNGs, the bounded WAV, cumulative PCM
and per-identity capture hits match the retained ABI-18 qualification.
The original ABI-17 profile remains unchanged; actual new captures retain
ABI 20. This uses ordinary Super System Card reset **with Arcade Card
disabled**, qualifying compatibility of the existing route rather than
retail Arcade Card software. The run quits naturally with exit 0; protected
inputs, the peer launcher selection and owner saves remain unchanged.
Muted presentation does not establish listening or physical-device parity.

## Enhanced HuCard mapper profiles — ABI 19

The following sections retain their earlier source pins and qualification
counts. Use the ABI-22 section above for the current runtime.

Implementation
[`41c18edc9671ebaf0bf1a37df7c79c8a6f3fbb9d`](https://github.com/rages4calm/pcenginerecomp/commit/41c18edc9671ebaf0bf1a37df7c79c8a6f3fbb9d)
has canonical source digest
`a0098d37fc1e97085fcdb49d7be57ca1957187afdb37398d5a8e1698f3693fa9`
over **60 files**. Runtime ABI **19** owns explicit mapper profile, selector
and retained SF2 ROM state. Consumer/capture schemas remain **1**. Retained
ABI-12 through ABI-18 observations remain original inputs; re-emit and rebuild
for 19 rather than relabeling old captures or reusing binary objects.

The explicit `sf2` profile supports a 2.5 MiB cartridge, fixed 512 KiB ROM and
four switched 512 KiB blocks. All sixteen physical bank-00 latch addresses
`$1FF0..$1FFF` select by address; data is ignored. The explicit `populous`
profile overlays 32 KiB RAM at `$40..$5F`, including all eight aliases per page.
ROM backing is preserved. Both retain absent CD hardware, original source
identities and guarded direct translations. Unseen switched bytes miss before
mutation. Profile selection is never inferred from a title or checksum.
See [HUCARD.md](HUCARD.md) for sizes, mappings, loader writes and limitations.

The fresh SDL/reference build passes **37 suites / 495 Python tests, zero
skips**. The new C++ suite checks **2,209,540 authored expectations**, including
both execution tiers/speeds, mapper writes from the executing window, block
transfers, same-address variants, RAM aliases, loader patches, generation
invalidation, pristine setup and explicit refusals. Eight real host tests also
check encoded inputs, guest input/release and a separately counted RAM CAS.

An independently compiled Geargrafx adapter, interpreter and actual translated
native module match **six cases / 27,982 observations**. Each path also passes
**27,766 independent literal checks**. Actual training captures **33 identities
in six full MPR contexts**; the emitted probe executes **210 native / zero
interpreted instructions**. Eighteen guard checks use six deliberate source
patches whose bytes are restored; loader generations retain those changes.
The Populous reference uses a disclosed RAM-size configuration shim, not a
CRC-spoofed game or modified mapper implementation. Private compile copies
match pinned Git blobs after line-ending normalization; raw source hashes are
also bound. This is finite emulator agreement, not physical-board or bus-phase
qualification. See [REFERENCE.md](REFERENCE.md).

Four fresh official authored consumer builds/runs execute **10,000 native
instructions each**. Separate headless/SDL TCP routes each run ten frames and
five controller states: SF2 executes **280,496 native instructions per host**;
Populous executes **298,026**, with zero interpreter fallback or guard misses.
Four actual code variants at the same PC/MPR/physical address are qualified
per profile. Guest/source/device checkpoints and per-identity hits match the
interpreted training routes; inputs stay unchanged, RAM edits stay zero and
natural quit returns 0. Four changed-source negatives stop at zero guest ticks
before retirement. These integration comparisons remain separate from Gear's
independent semantics check. No cartridge persistence or complete-title claim
is introduced.

The BIOS-backed Ys III regression also passes on this exact ABI-19 source.
The original retained ABI-17 observation profile is re-emitted with the real
compiler, preserving its original label. All 258 generated artifacts match
the qualified ABI-18 module apart from 257 ABI assertions. A fresh official
SDL package executes **5,526 TCP frames / 152,630,394 native instructions**,
zero interpreter fallback, zero guard misses and zero RAM edits. All 20 raw
paused checkpoints match the previous ABI-18 run after removing only RPC IDs;
the 21 actions, two whole PNGs, bounded WAV and normalized final guest state
match too. Digital PCM remains **4,073,415 stereo frames**, hash
`16759294491241433069`, with zero runtime loss and 177 sectors read. The new
actual capture is labeled **19**; source identities and per-tier hits match
the prior capture without rewriting either artifact.

This isolated gate uses a byte-preserving private consumer-harness copy with
four explicitly reviewed compatibility callbacks and 28 negative vectors.
They admit only the selected source/ABI and extend capture-version admission
without relaxing state, source, boot, package, image or PCM checks. Seven
protected originals and the consumer's selected launcher are unchanged.
Natural TCP quit returns 0 and the owned child stops. The two explicit
`gear-good` responses remain required. Muted unthrottled presentation is not
a listening test. The consumer's longer independent campaign/native-coverage
work retains its own source pin; this gate adds no title progression.

## Two-bit backgrounds and digital monochrome — ABI 18

The following sections retain earlier source pins and qualification counts.
Use the ABI-19 mapper section above for the current runtime.

Implementation
[`943fe06e59c5d657f1d88005583edac816e14e4c`](https://github.com/rages4calm/pcenginerecomp/commit/943fe06e59c5d657f1d88005583edac816e14e4c)
has canonical source digest
`8ee2c73e60779e6caf604c9bc2c5d5fe58a27c77283ae91fe18c72fab5047267`
over **60 files**. Runtime ABI **18** and both schema-1 formats are unchanged;
consumer source pins and binaries still require fresh qualification.

Background access mode 3 now decodes the two planes selected by MWR bit 7.
Both renderers preserve palette stride, transparent zero and sprite priority.
VCE bit 7 selects the explicit `mesen-standard-rgb-v1` digital monochrome
profile. Continuous output retains the existing MWR vertical latch and samples
palette/monochrome at each emitted dot. Standard color bytes, guest scheduling,
CPU/CD/audio behavior and state layout are unchanged. See [VDC.md](VDC.md).

The fresh SDL/reference build passes **36 suites / 475 Python tests, zero
skips**. Snapshot/palette tests pass **1,735,358 expectations**; continuous
output passes **6,403**, including mode/latch transitions and per-dot history.

A separate MesenCE adapter executes four exact extracted VDC definitions and
the complete unchanged filter header under authored dependency substitutes:
**1,048,576 palette indices and 512 grayscale RGB entries** match exactly.
It checks selected-word decoding/filtering, not a complete emulator, fetch
timing or latch edges. Geargrafx ignores both settings; its separate retained
color-path comparison still matches **16 frames / 786,432 pixels** exactly.
Neither adapter certifies analog colorburst behavior. See [REFERENCE.md](REFERENCE.md).

An authored HuCard is configured entirely by guest instructions. Actual TCP
input switches CG0/CG1 and monochrome on/off, including release. Its capture
contains **134 identities**. Two fresh official consumer builds/runs execute
**10,000 native instructions each**. Separate headless/SDL TCP tests each
execute **440,607 native / zero interpreted instructions over 15 frames**,
with zero guard misses, five exact expected pictures and matching CPU/source/
device checkpoints. RAM edits are disabled and natural quit returns 0.

A fresh official SDL package also reruns Ys III's **5,526-frame reset prefix**
against this exact source, reusing the existing ABI-18 module unchanged.
All **20 raw paused checkpoints** match the prior qualified ABI-18 build
after removing only RPC request IDs; the 21 control actions, two complete
PNG files, bounded WAV and code capture match too. Actual execution is
**152,630,394 native / zero interpreted instructions**, zero guard misses,
177 sectors and **4,073,415 PCM frames**, hash `16759294491241433069`, with
zero runtime audio loss or RAM edits. Natural TCP quit returns 0 and the
owned child stops. Seven protected originals and the consumer's selected
launcher remain unchanged. Unthrottled SDL presentation is muted; no listening
claim is made.

This regression uses a private byte-preserving copy of the consumer's replay
harness with two explicitly reviewed identity callbacks accepting only the
new source pin; 14 changed-identity/type negatives are refused. The remaining
boot, package, asset and replay validators are unchanged. It does not modify
the consumer's public ABI ledger or promote its selected package. Its separate
longer gameplay/native-coverage work retains its own source pin and evidence.
The two explicit `gear-good` responses are still required; the unknown CD
command, analog video, physical VRAM fetch timing and complete-game coverage
remain unqualified.

## Authentic base HuCard startup — ABI 18

The following HuCard section retains its original implementation pin and
qualification counts. Use the video section above for the latest source.

Implementation
[`6935e46ff8aefacf8ea058a385198299c4e2cd5c`](https://github.com/rages4calm/pcenginerecomp/commit/6935e46ff8aefacf8ea058a385198299c4e2cd5c)
has canonical source digest
`9414ed390229b8d411f2f79f6c22080d68fef7b09aef2bf99db0046751e34cf0`
over **60 files**. Runtime ABI **18** adds explicit cartridge mapper state;
consumer/capture schemas remain **1**. Retained ABI-12 through ABI-17 captures
remain original compiler inputs and must be re-emitted/rebuilt for ABI 18.

The new base HuCard recipe executes the cartridge's actual reset vector,
selected ROM mirror map and base WRAM/video/PSG/timer/IRQ/controller hardware
without a BIOS, CD RAM, BRAM, CD transport or ADPCM. Header stripping and bit
reversal are explicit declarations. The Python source-snapshot command and
pinned consumer recipe validate raw/decoded identity and typed initial state.
See [HUCARD.md](HUCARD.md) for supported boards, conversions and limits.

The fresh SDL/reference build passes **36 suites / 468 Python tests, zero
skips**. The cartridge suite passes **447,758 authored expectations**; 26 real
host tests cover both headless/SDL startup, mappings, no-CD I/O, explicit dump
formats, actual guest input/release, captures and PSG-only digital audio.
They caught a stale capture ABI literal; the writer now emits the runtime
constant. The original failed cohort is preserved, and the corrected cohort
passes without relabeling any old capture.

An unchanged separately compiled Geargrafx 1.8.4 adapter and actual interpreter
and native probes match **eight ROM sizes / 56 cases / 23,200 observations**,
with 21,640 independent literal checks per adapter. The actual eight-run
capture union has **111 identities / 17 complete MPR contexts**. Its freshly
translated module executes **3,072 native / zero interpreted instructions**.
An additional 168 guard checks use 56 deliberate source patches with bytes
explicitly restored; loader generation changes remain disclosed. These new
traces use low speed and need no CSH clock projection.

Two fresh official authored HuCard consumers, headless and SDL, each execute
**6,000 native / zero interpreted instructions** using an explicitly headered,
bit-reversed input. Separate native-only TCP runs each execute **21,289 native
instructions over three frames**, with zero fallback/guard misses, mirrored
ROM fetches, WRAM alias checks, actual guest button press/release, captures and
natural quit. Digital PSG output matches: **2,203 stereo frames**, PCM hash
`14021925444880039481`, zero runtime discard, and no CD/ADPCM samples. SDL dummy
unthrottled presentation is deliberately muted; its host-only statistics are
recorded separately. This is no listening or physical-device claim. Changed
authored source is refused before the first instruction, at zero guest ticks.

The first private cross-host proof attempt failed only because it compared
the entire audio object, including three additional SDL presentation fields.
Its raw outputs and driver remain preserved. A fresh complete run declares
those exact host-only fields before testing; all common digital audio and
guest state remain strict.

The Ys III project also regenerates its retained ABI-17 observations for ABI
18 and passes a fresh **5,526-frame CHD reset prefix**. All 20 checkpoints,
two guest images, capture identities and digital PCM match the prior qualified
prefix: **152,630,394 native / zero interpreted instructions**, 177 sectors,
4,073,415 stereo PCM frames (3,307,345 nonzero mixed frames), hash
`16759294491241433069`, zero runtime loss and zero RAM edits. Natural TCP quit
returns 0. The two explicit `gear-good` responses remain required. The 258
regenerated files retain the same translated operations with updated ABI
assertions; old capture labels and qualification epochs remain preserved.
This finite regression adds no campaign or listening claim. The implementation does
not add SF2/Populous RAM/SuperGrafx profiles, warm reset, owner persistence or
an implementation of the existing unknown `$FF` CD command.

## BIN/CUE media and pinned consumers

The following sections retain historical qualification with their original
source pins and test counts. Use the ABI-18 section above for the current
runtime and migration status.

The new shared media implementation is
[`95fe3e07e63b0869de8c9d7b70681b5c557abf01`](https://github.com/rages4calm/pcenginerecomp/commit/95fe3e07e63b0869de8c9d7b70681b5c557abf01),
canonical source digest
`60c37d9fb5b1a1318cd2509c7ac1cc45c03a9939116d04e836aa67e0e03c4ffb`
over **57 files**. Runtime ABI **17** and consumer/capture schema **1** remain
unchanged: this adds host media readers and input bindings, without changing
CPU/Bus layout or translated instruction semantics. Consumer packages still
need fresh source pins, builds and execution receipts.

The bounded read-only BIN/CUE subset supports single/multiple binary files,
cooked/raw MODE1, AUDIO, stored and virtual pregaps, and little-endian signed
audio samples. Complete-image identity covers exact CUE bytes and every
referenced binary. Python inspect, TOC export and bounded IPL discovery use
the same layout contract. Consumers bind all components, preserve the declared
CUE root through permitted links, and reject changed inputs. CLI outputs
cannot replace the CUE, a referenced file or an existing hardlink alias.
Unsupported formats/layouts stop explicitly; see [MEDIA.md](MEDIA.md).

The fresh SDL/reference build passes **35 suites / 420 Python tests, zero
skips**. The CUE provider adds **13,059 authored expectations**; 32 additional
finite vectors check parser acceptance consistency across C++ and Python.
The separately compiled unchanged Geargrafx 1.8.4 media reader matches six
authored images: **114 observations / 59,392 data bytes / 28,224 signed audio
samples**. All six compound identities match independent record encoding.

A separate actual translated-MMIO probe executes seven READ streams per tier,
14 sectors per tier: **114,877 native / zero interpreted instructions**, and
the same count in the interpreter-only runs. Payloads, ACKs, status/message,
zero guard misses and zero read errors agree. Gear independently checks the
media geometry/bytes; this command-stream check is toolkit functional evidence,
not external whole-guest bus timing.

Two fresh official authored CUE consumer verify/build/run sequences, headless
and SDL, each execute **600,000 native / zero interpreted instructions**.
Separate native-only TCP runs each advance **26 frames / 803,697 native
instructions**, with zero fallback/guard misses, one READ and all 2,048 guest
RAM bytes matching independently authored data. Normal input/release,
captures and natural TCP quit pass; memory editing remains disabled and its
counters stay zero. Four interpreter-host runs separately cover cooked/raw
sectors in both hosts. Every authored input remains unchanged. PCM is off in
these short data-path proofs; their captures add no audio-output claim.

The separate Ys III project also freshly rebuilds the same qualified native
module against this toolkit source and passes a **5,526-frame CHD reset
prefix** through ordinary TCP controls. All **20 checkpoints and two guest
images** match its retained ABI-17 reference, including CPU/MPR/source/device
state and digital PCM. Actual work is **152,630,394 native / zero interpreted
instructions**, 177 sectors read and 4,073,415 stereo PCM frames, including
3,307,345 nonzero mixed frames, with zero RAM edits or runtime audio discard
and natural TCP quit 0. The bounded
10-second WAV prefix is boot-silent and byte-identical; later cumulative PCM
is nonzero. The fresh official SDL package retains the same 258 generated
artifacts and verifies its packaged SDL outside the SDK PATH. The explicit
`gear-good` profile is still used twice. This is a compatibility regression,
separate from that project's ongoing town-coverage work; it adds no campaign
milestone and does not replace its previously qualified launcher selection.

Existing CHD/ISO input identities and semantics remain unchanged. The earlier
native System Card and assisted gameplay sections below retain their original
source pins and execution scope. The new media reader does not implement the
unknown `$FF` CD command, add persistence, or certify a complete game.

## Native reset promotion and ABI-17 integration

The shared toolkit now checks native reset execution independently and provides
a reusable actual-capture-to-native consumer example. Production implementation
[`bb3b695b782352bdfacd8db877f2a843bd1242f1`](https://github.com/rages4calm/pcenginerecomp/commit/bb3b695b782352bdfacd8db877f2a843bd1242f1)
has canonical source digest
`5d3551481d1245d8cec9011d0f390ad0b464720c2d1f37a0fce601d0888e7a0d`
over 54 files. ABI **17** and both schema-1 formats remain unchanged.
The only canonical source change from the original reset batch is consumer
receipt validation in `project.py`; all runtime and emitter bytes are identical.
The authored helper and native reference adapter are finalized in
[`24244348370187c343c4ae223c7282a08252106e`](https://github.com/rages4calm/pcenginerecomp/commit/24244348370187c343c4ae223c7282a08252106e),
with that same canonical source digest. Native modules and input pins still
require fresh generation/build/run qualification for the selected consumer.

The fresh SDL/reference build passes **34 suites / 386 Python tests with zero
skips**. Reset receipts verify the initial typed metadata against the selected
hardware, pinned BIOS vector, deterministic policy and BRAM source. Fresh
captures must have the current ABI, requested capacity and consistent native /
interpreted retirement counts. Explicit loss remains visible and unclassified;
older offline capture inputs retain their original ABI labels.

The actual authored training run records 16 identities across five complete
MPR contexts, including ROM fetches in banks `$00`, `$20` and `$40`. Four fresh
official Standard/Super × headless/SDL-desktop verify/build/run sequences each
retire **200 native / zero interpreted instructions**, with matching guest
CPU/device state and actual native captures. Each separate paused TCP test
executes **79,448 native / zero interpreted instructions** over two frames,
verifies mirrored reads and the authored RAM result, and quits cleanly with
zero RAM edits. Each changed-CSH negative stops at a native guard miss after
six retired instructions, before the changed instruction executes. PCM is
explicitly off for these short CPU/mapping proofs; they add no audio claim.

The unchanged external Geargrafx oracle repeats all **38 original cases /
29,824 observations**, plus **12 separately authored mirror-fetch cases / 120
observations**. Actual captured source identities are emitted, compiled and
executed: **303 identities / 20 MPR contexts, 1,320 native / zero interpreted
instructions**. Native/interpreted raw records match exactly. Original Gear
comparisons retain the known **36 CSH differences of 18 master ticks**; the
additional mirror-case clocks agree. Separate guard tests check 200 refusals
with 100 intentional authored source mutations explicitly recorded/restored.
These are finite authored proofs, distinct from native retail qualification.

The Ys III consumer's separate ABI-17 reset recipe now executes the actual
**14,680-frame** firmware-to-town-opening route with **432,875,213 native /
zero interpreted instructions**, **41,179 native / zero interpreted block
transfers**, and zero guard misses. Its fresh official package uses the actual
capture union: **52,556 eligible identities / 79 MPR contexts**, including
7,674 newly observed identities. The original six-byte source exclusion remains
in force. The raw reset capture retains 36,145 identities, all 432,875,213
retirements and zero dropped/unreadable instructions; source ABI labels remain
unchanged. Emitted source is compiled as 257 translation units plus its header.

The native run follows the same normal controls as the interpreted baseline:
reset → System Card menu → Run → disc introduction → Beginning → blank-BRAM
Proceed → town opening. All ten guest images, guest CPU/MPR/source/device/CD
state and digital PCM/bounded WAV agree within the stated comparison scope.
Both full runs retain 105 states and 115 actions, natural TCP quit 0, unchanged
protected input assertions and **zero RAM edits**. This is a new native boot
proof, not a new campaign milestone or complete port certification.

The same regenerated module also passes the retained **95,686-frame /
68-checkpoint** IPL-start gameplay regression on ABI 17: **2,980,431,691 native /
981 interpreted instructions** and 470,652 native block transfers. Guest state
and the retained filtered 48 kHz PCM comparison agree within that route's
existing scope. It keeps the original 709 assisted transactions / 723 edited
bytes, with no new assists, and quits naturally with exit 0. This separate
assisted regression does not change the zero-RAM-edit reset proof above.

The only old-reference input-status projection is the explicitly witnessed
same-tick release observation at frame 11,660. The old status still held I;
the new host had applied release. All other guest fields remain strict, and the
actual next two-frame advance confirms release with an exact guest-state match.
The original failed attempt and both raw observations remain preserved. There
is no broad removal of button fields. See [input acknowledgement semantics](DEV_SERVER.md).

A separate first-600-frame native menu run records **17,483,734 native / zero
interpreted instructions**: 17,483,730 BIOS-range hits and four RAM hits. Its
frame-120 and frame-600 guest images match the retained toolkit images exactly,
tying this bounded native menu result to the earlier explicit Gear viewport
comparison. Full Gear/tool images still differ by the documented black-border
crop; this is not a new whole-retail CPU/timing comparison.

Guest audio remains on: 10,821,162 stereo frames, PCM hash
`16077886581937742416`, zero runtime discard and the same bounded 441,000-frame
WAV prefix. The run reads 516 sectors without read errors and still requires
the explicit `gear-good` response profile twice. This does not implement `$FF`,
add listening/hardware parity or introduce persistent host saves.

See [the capture example](../examples/reset-consumer/README.md#capture-mappings-that-a-fixed-cfg-cannot-discover),
[reset contract](SYSTEM_CARD_BOOT.md) and [reference limits](REFERENCE.md).

## System Card reset boot - ABI 17

This section preserves the original reset batch's execution and reference
scope. Later native integration is recorded above.

The toolkit now has an explicit Standard/Super System Card reset-vector
startup path in both hosts and the consumer interface. It maps the selected
ROM/RAM hardware, initializes the named deterministic reference state, then
executes the actual supplied firmware. No extracted IPL, game entry address,
firmware patch or invented BIOS service is used. Existing snapshot/IPL recipes
remain available. BRAM is blank/unformatted or an explicit read-only seed;
there is no automatic formatting, owner-save discovery or persistence.

The immutable implementation is
[`df110529bd79cded48d9607653c8b6218bce4b3b`](https://github.com/rages4calm/pcenginerecomp/commit/df110529bd79cded48d9607653c8b6218bce4b3b),
source digest `c3dd7c6de6bba4abdb92eb3f90c1c5dbecf387790a15db654b597eda0225f1d7`
over 54 canonical files. Runtime ABI is **17**; consumer and capture schemas
remain 1. Retained ABI-12/13/14/15/16 captures can be re-emitted and rebuilt
without relabeling their original observations.

That fresh SDL/reference build passes **34 suites / 360 Python tests without
skips**. The new reset fixture checks **6,105,054 authored expectations**;
22 actual host tests cover headless/desktop reset, mapping, preserved inputs,
invalid grammar, captures and paused-before-first-instruction TCP control.

Independent unchanged Geargrafx 1.8.4 execution passes **38 authored cases /
29,824 observations**, including complete 109-field initial device snapshots,
CPU traces, explicit seeds/vectors/regions, memory mirrors, expansion RAM,
absent memory, source peeks and identification pins. Selected architectural
state agrees. The **36 CSH transitions retain the established 18-master-tick
clock difference**; raw clocks and the disclosed transition adjustment are
recorded, rather than claiming unconditional cycle parity.

Separate real clean USA firmware/actual-disc execution reaches the System
Card menu through 600 frames in Gear and this runtime. All **60,672 overlapping
pixels** match at both frame 120 and 600. Full frames remain unequal because
the toolkit uses active-VDC rows and Gear's selected fixed VCE viewport keeps
three additional black rows. No raster timing or image bytes are altered to
force agreement.

Standard headless and Super SDL desktop authored official consumer
verify/build/run sequences each retire **200 native / zero interpreted
instructions**, with literal CPU/clock results and actual three-identity
captures. This proves native reset-entry integration without any retail data;
it does not turn an interpreter-only retail boot into native execution.

A separate BIOS-backed TCP run starts at reset and completes **14,680 frames**:
System Card menu → Run → disc-loaded introduction → Beginning → unformatted
BRAM warning → Proceed → opening story and town opening. It retires **432,875,213
interpreted / zero native instructions**, reads 516 sectors with zero read
errors, and ends by clean TCP quit. Normal controller input is scripted; there
are **zero RAM edits**, no preloaded IPL and no owner save. This qualifies
firmware/disc startup and the observed opening, not a new campaign milestone
or fully native retail port.

Audio stays enabled throughout: **10,821,162 stereo frames** synthesized with
nonzero PSG, ADPCM and CDDA contributions, zero runtime discard, and a bounded
10-second WAV. The WAV alone covers only its recorded prefix; cumulative
diagnostics cover later synthesis. This headless check is not new listening,
device-playback or independent retail mixed-audio parity evidence.

The run still needs the explicit `gear-good` policy when leaving the
introduction, used twice. A separate strict prefix reaches the same first
`$FF` and stops explicitly with one attempt, zero accepted responses and
natural process exit 3. Reset-vector startup does not implement that command.
Earlier private controller-harness failures are preserved separately; the
completed route and strict prefix use the corrected helper and clean exits.

At that stage, the Ys III consumer's independent coverage work stayed on its
qualified ABI-16 pin while reset startup was tested separately. Earlier ABI-16
and older sections below retain their historical qualification scope.
See [the startup contract and limits](SYSTEM_CARD_BOOT.md),
[consumer migration](CONSUMER.md#upgrade-a-consumer-to-abi-17), and
[authored example](../examples/reset-consumer/README.md).

## Base compatibility - ABI 16

The retained ABI-16 shared runtime adds normal PC Engine F8-FB work-RAM aliases,
direct native/interpreted BRK, and device-clock VDC sprite collision/overflow
events. There are 234 supported opcode encodings; 22 reserved slots still
trap explicitly. Runtime ABI is **16**, with unchanged schema-1 consumer and
capture formats. Re-emit retained ABI-12/13/14/15 captures and rebuild modules
with the runtime. No new capture or native gain is implied by an ABI upgrade.

The immutable implementation is
[`3bd06b5055c92e9f368aab7023098ff8aa796854`](https://github.com/rages4calm/pcenginerecomp/commit/3bd06b5055c92e9f368aab7023098ff8aa796854),
canonical source digest
`720e3c1e980e3ad9d03b28cb4b31db696fe3bb27e687c0cf19bc3d0f3f1c9440`
over 54 source files. A fresh build from that exact checkout passes the checks
below. An earlier working-tree CRLF header epoch is preserved separately;
canonical public LF bytes were rebuilt and checked without changing semantics.

The fresh SDL/reference-probe build passes **33 suites and all 328 Python
tests without skips**. New authored expectations include **426,004 WRAM
checks, 2,374,129 BRK checks and 211 sprite checks**. Actual TCP checks cover
alias reads and atomic compare/write behavior; authored unknown-CD traffic
tests strict fault and explicit reference-response modes with retained source
context. Existing audio, rendering, device, compiler and packaging suites pass.

Three fresh authored official consumer verify/build/run sequences each retire
**200 native / zero interpreted instructions**. The BRK fixture captures
its actual two-byte encoding, then capture-to-native regeneration and another
fresh official run reproduce the capture and final diagnostics exactly.
Authored ABI-12/13/14/15 format fixtures re-emit successfully for ABI 16;
they are format checks, not executions by those historical runtimes.

Separately compiled unchanged Geargrafx 1.8.4 matches **81 sprite cases /
125,922 checkpoints** in each toolkit video-on/off mode, plus **3,040 BRK
cases / 5,280 checkpoints** in each execution tier. The external memory check
passes 131,072 WRAM alias readbacks and four actual instruction-fetch aliases.
These are finite authored device/CPU proofs, not retail/hardware conformance.
Earlier external-wrapper startup failures and obsolete-fixture failures are
preserved separately; no runtime correction was needed for those harness errors.

Unknown CD commands still fault by default; REQUEST SENSE remains unsupported.
New bounded `cd_unknown` diagnostics retain opcode attempts and last-unknown
CDB/origin without replacing it with later known commands. The origin is
the last latch-write PC/MPR/fetch supplying the initial CDB byte before ACK,
not an ACK-time retirement trace. Physical
VRAM contention, undriven rendering-bus reads, authentic reset, HuCard mappers,
SuperGrafx/Arcade Card and persistent host saves remain separate gaps.
See [the compatibility contract](COMPATIBILITY.md),
[reference scope](REFERENCE.md#base-compatibility-references---abi-16), and
[consumer upgrade procedure](CONSUMER.md#upgrade-a-consumer-to-abi-16).

## ABI-16 consumer integration

The separate Ys III consumer re-emits its original ABI-13 observations for
the exact ABI-16 implementation above. All **208 translation units and one
header** retain their translated operations, source guards and exclusions,
with only ABI assertions changed. The capture still contains **44,879 eligible
identities across 57 MPR contexts**; no new observation or native gain is
claimed.

Fresh official desktop builds complete the same assisted **94,800-frame
route** with legacy filtered 48 kHz, default Gear filtered 48 kHz, and audio
off. All **39 images/checkpoint states and three endpoints** preserve the
retained guest/source/IRQ/generation fields. Each run retires **2,953,438,406
native / 981 interpreted instructions**, including **466,118 native / zero
interpreted block transfers** and 981 guard misses. The 709 inherited RAM
compare-and-swap transactions submit 49,303 bytes and change 723 bytes; there
are no new assists or campaign milestones. Original media, captures and old
qualified receipts remain unchanged and private.

Fresh legacy and Gear headless runs match their corresponding desktop routes,
including all new `cd_unknown` diagnostics, PCM and bounded WAV bytes.
The headless run's explicit Gear flag
and the desktop's omitted/default flag both select the same three-key audio
profile. Legacy and Gear PCM hashes remain `13785118638779356764` and
`1852331864136332503`, respectively; the audio-off route produces no PCM/WAV.
The first 30-second WAV alone cannot qualify the full audio stream; checkpoint
and cumulative hashes retain that separate scope.

The new diagnostics identify all **53 reference-profile responses as opcode
`$FF`**, rather than assuming they are REQUEST SENSE. A separate strict-policy
probe stops at the first `$FF` with one attempt, zero accepted responses and
the explicit unsupported-command fault. It qualifies fault diagnostics, not
a successful route or normal process shutdown. The assisted route still
requires `gear-good`; no unknown CD operation is implemented by this result.

A separate official `project run` smoke passes **60 frames / 2,014,178 native /
zero interpreted instructions**. Full routes use the separately bounded
1,800-second TCP supervisor, not the official command's 600-second bound.
The paced packaged SDL check loads its adjacent runtime from an empty working
directory with sanitized PATH, exercises input/capture/pause/resume, accepts
and drains **773,361 output frames**, and ends with zero runtime discard and
an empty device queue. Pause-flush device drops are recorded separately;
this is device acceptance, not listening or analog-audio parity.

The fresh consumer-embedded runtime passes **33 suites / 328 Python tests
without skips**. The consumer's own final suite passes **324 tests without
skips**, including strict ABI-16 capture and additive diagnostic validation.
These runs qualify the reusable consumer interface and the retained route;
they add no independent retail-game oracle, full-campaign, authentic-reset or
hardware-conformance claim. Earlier ABI-15 evidence below remains historical.

## ABI-15 consumer integration

The reusable consumer contract is exercised against the same qualified
ABI-15 implementation described below. A fresh authored example passes official
prepare, verify, build and run: **200 native / zero interpreted instructions**,
expected CPU state, and an actual four-identity / 200-retirement capture.
Authored ABI-12/13/14 format fixtures re-emit successfully for ABI 15;
these fixtures do not claim execution by older runtimes. All 57 focused
capture/project tests pass.

The Ys III consumer's retained ABI-13 observation union re-emits **44,879
eligible identities / 57 complete MPR contexts**. All **208 translation units
and one header** preserve their translated operations and guards after
normalizing only ABI assertions. The existing source exclusion and its
981 interpreted retirements remain intact. This is an ABI migration, with
no additional native gain or new campaign coverage.

Fresh official headless and desktop builds execute the same assisted
**94,800-frame route**, including its retained combat, Game Over and Continue
section. Both audio timings match all **39 image/checkpoint states and three
endpoints** across hosts. Native work remains **2,953,438,406 native + 981
interpreted**, with **466,118 native / zero interpreted block transfers**.
The audio-off desktop replay also completes the same route. No new assistance
is introduced: 709 compare-and-swap transactions submit 49,303 bytes and change
723 bytes. Original media and captures remain private and unchanged; prior
qualified source epochs are preserved in exact private archives.

| Audio mode | Result |
|---|---|
| Explicit legacy, filtered 48 kHz | All checkpoint/final PCM and bounded WAV bytes match the retained ABI-13 consumer and fresh ABI-15 headless reference; cumulative PCM hash `13785118638779356764` |
| Default Gear, filtered 48 kHz | Desktop PCM/WAV matches the fresh headless reference; cumulative PCM hash `1852331864136332503` |
| Both enabled modes | 76,060,360 output frames / 69,880,456 source frames, peak 13,355 and zero runtime discard |

Gear source counts match `floor(ticks*44100/21477273)` and filtered output
counts match `floor(source_frames*160/147)` at all 39 checkpoints and three
endpoints. The first 30-second WAV remains byte-identical across timings;
whole-stream/checkpoint hashes provide the later audio evidence.

A separate official consumer `project run` TCP smoke passes **60 frames /
2,014,178 native / zero interpreted instructions**. The full routes use a
separate 1,800-second consumer supervisor with official verify/build bindings,
not the command's 600-second limit. A paced packaged Gear/48 kHz check passes
adjacent-SDL loading from an empty working directory with sanitized PATH,
TCP input/captures, pause freeze and resumed advancement. It produces 773,361
output frames with zero runtime discard. Device acceptance is separate from
listening or hardware accuracy.

The fresh embedded shared-runtime check passes **30 suites / 316 Python tests
without skips**. Consumer migration checks pass **283 tests without skips**.
Independent root evidence review rehashes 655 actual artifacts and passes
27,328 checks. These are runtime/consumer regression results; retained finite
Geargrafx source oracles keep their original scope. No independent retail
mixed-audio oracle, complete-game port or hardware certification is added.
See [the migration procedure](CONSUMER.md#upgrade-a-consumer-to-abi-15).

## CDDA sample-latch ports

The guest now reads signed post-fader CDDA samples through `$1805/$1806`,
independently of PCM output, filtering, output rate and legacy presentation
sample timing. Accepted `$1805` writes are at least 700 master ticks apart,
alternate right first and retain one coherent 16-bit sample. Reads do not
advance or toggle it; `$1806` writes are ignored. `$1803` reports the selected
side and relocks BRAM. See [the exact contract](CD_AUDIO.md#guest-sample-latch).

The implementation is frozen at
[`e0f67bf64fe670723acd4443b0da76f3bfe8276f`](https://github.com/rages4calm/pcenginerecomp/commit/e0f67bf64fe670723acd4443b0da76f3bfe8276f),
source digest `38573f59cd17b1b9c640337ac6c1d9db80b3dc926d42312f8cedfd28d7959dd7`
over 53 canonical files. Runtime **ABI 15** owns the guest CDDA cursor, phase,
raw/post-fader holds and latch state. Descriptor schema remains **1**.
ABI-12/13/14 captures remain accepted; re-emit and rebuild modules and runtime
when upgrading. There is no snapshot compatibility contract.

The SDL/native-module configuration passes **30 suites and 316 Python tests
without skips**. New authored checks cover **3,047 latch/source expectations**
and **48 native/interpreter latch instruction sequences**, including signed
loads and flags, both CPU speeds and MPR aliases. The full SCSI, CDDA, DSP,
timing, video, compiler and host suites pass. A clean immutable public-source
build without SDL or a generated game module passes **28 suites**, discovering
the same 316 Python tests with eight intentional desktop-only skips.
A maximum-timestamp regression
found during this batch is fixed: an exhausted CD source timeline has no
future representable deadline, while actual command/output scheduling overflow
still faults explicitly.

A separately compiled unchanged Geargrafx 1.8.4 core passes nine authored
cases / **367 distinct reference checkpoints**, each compared with toolkit PCM
on and off. The real master scheduler advances source and fader clocks using
an authored CUE/BIN. The disclosed private-clock member-pointer bridge changes
no reference source or sample state. The final oracle and its exact executed
probe/source bindings are preserved separately from earlier development runs.
This qualifies the selected reference profile; CPU bus phases, variable seek
distance, retail mixed-audio parity and hardware output remain unqualified.
Full reset is covered by authored runtime checks; the reference cases start
fresh cores rather than resetting a previously nonzero latch in place.

## Ys III latch regression through TCP

Two fresh ABI-15 headless TCP executions finish the original assisted
**93,735-frame route**. Legacy raw 44.1 kHz and Gear filtered 48 kHz each
match their preceding ABI-14 execution exactly: all **25 complete guest image
hashes, 25 checkpoint states, three final states, every guest/native/device
field, every PCM field and the bounded WAV bytes**. Final execution remains
2,920,491,782 native / 981 interpreted retirements, 981 guard misses and
460,685 native / zero interpreted block transfers. The original 44,832
identities / 57 MPR mappings were re-emitted for ABI 15; all 208 generated
files retain the translated operations and guards, changing only ABI assertions.

The original 709 compare-and-swap transactions submit 49,303 bytes and change
723 bytes. No new assists or campaign progression are added. This route
regresses existing behavior; the authored CPU and independent Gear tests
supply the new latch-port coverage. No retail latch usage, independent retail
mixed-PCM parity, packaged device playback, listening or hardware qualification
is claimed. Both owned headless children exit normally; all seven protected
inputs and the original capture remain unchanged.

These direct runs use a disclosed private frozen snapshot of the consumer's
helpers, adapted for ABI 15. A new preflight initially omitted the existing
route-directory capture fallback and stopped before launching a game. The
exact old helper, failed preflight logs and harness are preserved; a separate
amendment records the corrected path resolution. Original captures are present
and match their previous receipt hashes. Actual successful supervisors and
qualifications are retained independently. At this latch-port milestone,
the consumer's separate native-coverage work remained on its published
capture-only ABI-13 pin; the ABI-15 adoption is qualified separately above.

## Retained ABI-14 audio timing and source accuracy

Default source timing now uses **ceiling-rational sample edges**, beginning at
master tick 488 rather than 487, and holds each PSG channel's stereo DAC output
between positive PSG clocks. Timed DDA/gain/control writes no longer become
audible before the next PSG clock; waveform-memory writes and DDA-falling
transitions retain their immediate update rules. Explicit
`--audio-timing legacy` preserves the preceding floor-edge/analytical PCM path.
Raw/filtered selection and 44.1/48 kHz output remain independent of timing.

The implementation is frozen at
[`8b620e0e2f07f12997637645fb938f231a31c097`](https://github.com/rages4calm/pcenginerecomp/commit/8b620e0e2f07f12997637645fb938f231a31c097),
source digest `00b49884c490729b33c05b01dc315811629ebb77cef686ff45ae747dd70976ef`
over 53 canonical files. Runtime **ABI 14** adds per-channel held DAC state;
descriptor schema remains **1**. ABI-12/13 captures can be re-emitted, with
modules and runtime rebuilt together. Old compiled modules are incompatible.

The expanded SDL/native-module build passes **29 suites and all 308 Python
tests without skips**. Authored timing checks pass 29,418 expectations;
776 PSG checks include held writes, and 16,748 CDDA cursor checks run under
both timing profiles. Existing DSP, mixer, decoder and host suites pass.
A clean immutable public-source build without SDL or a generated game module
passes **27 suites**, discovering the same 308 Python tests with eight
intentional desktop-only skips.

The separately compiled unchanged Geargrafx clock-driven oracle passes
**102 authored cases / 1,551 checkpoints / 75,137 stereo frames**, measured
after integer one-third mixer headroom. It uses actual source clocks, timed
register writes and real ADPCM decoding from authored RAM at all 16 rates;
decoder state is compared separately. It injects no predictor/filter state.
Ordinary callback partitions agree; three overdue-rate cases explicitly use
single-master-tick Gear callbacks and retain its coarse-callback disagreement.
Fader master time, delayed bus slots/DMA, CDDA, pre-mix source S16 equality,
retail mixed-audio parity, listening and hardware remain outside that oracle.

The additive capture-window ancestor
[`c5aa9a26125edabdbe98a68bf716bff6eacd310e`](https://github.com/rages4calm/pcenginerecomp/commit/c5aa9a26125edabdbe98a68bf716bff6eacd310e)
retains ABI 13 for consumers qualifying native coverage separately. Its clean
no-module build passes 26 suites / 294 Python tests with eight desktop-only
skips; all 11 focused capture tests run without skips. The current ABI-16
toolkit includes the same `--code-capture-start-frame` feature. Capture starts
after a completed-frame threshold at a safe instruction boundary; its report
separates preceding retirements from the capture window. It does not restore
or certify game bytes. See [CODE_CAPTURE.md](CODE_CAPTURE.md).

## Ys III timing regression through TCP

Two fresh ABI-14 **headless** TCP executions finish the same assisted
**93,735-frame route**. Both match all 25 complete guest image hashes, all
25 checkpoint states, three final statuses and every original guest/device
diagnostic. Execution remains **2,920,491,782 native / 981 interpreted
retirements**, 981 guard misses, and **460,685 native / zero interpreted
block transfers**. The original module's 44,832 identities / 57 mappings were
re-emitted for ABI 14; its 208 generated files differ only in ABI assertions,
with translated operations, guards, capture and exclusions unchanged.

| Timing/output | Actual result |
|---|---|
| Legacy raw 44.1 kHz | All 13 PCM fields and bounded WAV match the retained raw baseline exactly: 69,095,406 frames, hash 7,177,686,580,420,813,080, peak 13,000 and zero discard |
| Gear filtered 48 kHz | 75,205,884 output frames; hash **12,432,665,724,897,062,919**, 71,837,759 nonzero frames, peak 13,355 and zero discard |
| Gear raw-source projection | 69,095,406 source frames; hash **16,552,896,032,681,844,245**, 65,958,169 nonzero frames, peak 13,000; nonzero PSG 27,644,754 / ADPCM 4,030,676 / CDDA 49,762,727 |

At all checkpoint/final statuses, gear source counts equal
`floor(guest_ticks*44100/21477273)` and 48 kHz output counts equal
`floor(source_frames*160/147)`. Final guest time is 33,650,360,835 ticks.
The bounded 30-second filtered WAV still has 1,440,000 frames and SHA256
`daac69ca4a6707ac94fe4fc5f6006c362a3918835ef52b909e6183c7e8d7770d`;
its retained opening does not expose the later full-stream timing changes.
Whole-stream hashes/activity counters provide the additional regression data.

The original 709 compare-and-swap RAM transactions submit 49,303 bytes and
change 723 bytes. No new assists or campaign progression are added. A private
wrapper initially confused submitted and changed bytes in its last assertion;
both actual supervisors had already passed and exited normally. A separate
read-only closeout independently rechecks the retained executions, journal,
full comparisons and provenance. Original failure receipts remain unchanged;
no game replay or raw output is rewritten to close that harness error.

These are direct supervised headless runs using a disclosed private snapshot
of the consumer's helpers, adapted for ABI 14 and explicit timing validation.
They do not claim official consumer `project run`, new packaged/device
playback, independent Gear retail mixed PCM or listening/analog qualification.
All seven protected inputs and the original capture remain unchanged; both
owned headless children exit cleanly. The consumer's separate native-coverage
work can use the published ABI-13 capture-only ancestor without adopting the
timing migration.

## Retained ABI-13 audio filtering and resampling

At this retained pin, the default was **raw 44.1 kHz stereo**, preserving the
preceding samples, diagnostics and guest timeline. `--audio-profile filtered` added PSG DC
blocking and ADPCM DC/low-pass filtering with gain smoothing. Filtered
output supports 44.1 kHz passthrough or `--audio-rate 48000` using an authored,
fixed-memory **64-tap, 160-phase Q30 FIR**. Consumer schema **1** optionally
selected the same profile/rate. That correction retained **ABI 13**, allowing
the then-existing 208-file module to be reused after a runtime rebuild. The
ABI-15 sample-latch upgrade required module regeneration; current ABI 16
also requires regenerated modules.

The implementation is frozen at
[`72bd5a2d4616d50d8b19f0d78c5af6ddfbd1c777`](https://github.com/rages4calm/pcenginerecomp/commit/72bd5a2d4616d50d8b19f0d78c5af6ddfbd1c777),
with 53 canonical source files and source digest
`0bfa0312dfaa28e4ae0371007385086c885d8fd6f4e5a231870f4d61b557aef3`.

The filtered profile retains unclipped PSG half-sample precision and ADPCM
history while decoder values are held or stopped; ADPCM reset clears its
filter history and restores initial gain. Guest clocks,
source observations and the raw reference path remain separate from these
presentation histories. At 48 kHz the output count is exactly
`floor(source_frames*160/147)`, with **31 source frames** of causal FIR delay,
zero initial history and no synthesized tail. PCM drains and presentation
pauses do not reset the DSP. Filtered diagnostics explicitly distinguish raw
44.1 kHz observations from processed output frames/hash/WAV.

| Evidence | Result | Limit |
|---|---|---|
| Expanded-module SDL build | **28 suites / all 291 Python tests pass**, without skips; 478,512 authored DSP checks, 20,852 mixer expectations and 159 SDL dummy-device checks | Windows x64; component/host tests, separate from retail-route and physical-device evidence |
| Clean frozen public-source default build | **26 suites pass; 291 Python tests discovered with eight intentional desktop-only skips** | Windows x64, no generated game module or desktop host; distinct from the expanded SDL configuration |
| Separately compiled unmodified Geargrafx 1.8.4 PSG filters | **3,266 authored cases / 59,505 stereo frames match exactly**; actual one-frame and 509-frame reference drains agree | Positive source-clock observations and synthetic unclipped half-sample sums; no hardware, final-mix or resampler parity |
| Separately compiled unmodified Geargrafx ADPCM filters | **17 held-input cases / 34,112 stereo frames match exactly**, including reset, decay and fader targets zero/one | Per-sample reference drain only; fixture-controlled held predictor/fader inputs, without ADPCM decoder/clock integration or continuous fader-timeline qualification |
| Authored FIR response | All 160 phases, DC–18 kHz in 50 Hz increments: maximum magnitude error **0.00166081 dB**; worst phase at source Nyquist **−72.2656 dB**. Streamed 20.5/21.5/22 kHz tones produce 23.6/22.6/22.1 kHz images **−81.35/−77.62/−78.17 dB** relative to input | Analytic/authored coefficient and actual rational-stream tests, without Geargrafx/SDL device-conversion or analog measurements |
| Independent filter-reference review | **480 checks pass**, rehashing **244 actual artifacts** with no pending evidence; source/compiler/probe/plan/output bindings and the claimed comparisons are independently checked | Audits the recorded external execution; not another emulator, a new retail run or physical audio measurement |

The filter oracle binds 130 external source/header files, four libraries,
compiler options, probes, plans and raw output hashes, and rejects unpinned
compilation inputs. Seven authored adapter tests exercise its preservation
and failure checks. The original GPL implementation remains an external
reference; the runtime contains independently authored equations and FIR
coefficients. See [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md) for exact equations,
controls, diagnostics, reference commands and source provenance.

Filtering the existing 44.1 kHz observations cannot reconstruct transitions
already lost at that stage or remove aliases already folded into them.
Geargrafx source-filter agreement does not qualify its final unity-gain mix,
host resampling, the console's analog circuit or complete retail sound.
The earlier raw-source and consumer results below retain their original scope.

## Retained ABI-13 packaged Ys III consumer qualification

The [Ys III consumer revision 6f0f9bf](https://github.com/rages4calm/ys3recomp/commit/6f0f9bf645495c2510ae128fb525fe078979a00f) rebuilds against
the frozen filtering/resampling pin above. Fresh headless reference
runs and packaged desktop TCP replays each complete the same **93,735-frame
route**, once with raw 44.1 kHz and once with filtered 48 kHz output. All
**25 complete guest image hashes, 25 checkpoint states and three final TCP
statuses** preserve the original guest fields. Final CPU/device/source state
and execution counts remain exact: **2,920,491,782 native / 981 interpreted
retirements**, 981 guard misses, **460,685 native / zero interpreted block
transfers**. Both hosts exit normally under each profile.

| Complete-route audio | Result | Scope |
|---|---|---|
| Raw 44.1 kHz reference and desktop | All 13 existing PCM fields and bounded 30-second WAV remain identical to the retained raw baseline: **69,095,406 frames**, PCM hash **7,177,686,580,420,813,080**, peak 13,000, 65,958,163 nonzero mixed frames and zero runtime discard | Raw default and diagnostics remain unchanged; unthrottled device output is intentionally muted |
| Filtered 48 kHz reference and desktop | **75,205,884 output frames**, exactly `floor(69095406*160/147)`; PCM hash **8,515,195,911,678,413,936**, peak 13,355, 71,837,781 nonzero mixed frames and zero runtime discard; processed PCM/WAV match across hosts | 31-source-frame FIR latency, no tail flush; internal cross-host reproducibility, not Geargrafx retail mixed-output or hardware parity |
| Unchanged raw source domain | 69,095,406 source frames; raw hash 7,177,686,580,420,813,080, peak 13,000, 65,958,163 nonzero mixed frames; nonzero PSG **27,644,755**, ADPCM **4,030,681**, CDDA **49,762,727** | Source counters/observations retain the 44.1 kHz domain, separately from processed output |

The filtered 30-second WAV contains **1,440,000 stereo frames / 5,760,044 bytes**,
SHA256 `daac69ca4a6707ac94fe4fc5f6006c362a3918835ef52b909e6183c7e8d7770d`.
This is the same assisted IPL-entry/`gear-good`/volatile-BRAM route, including
the original **709 RAM transactions / 723 changed bytes**. There are no extra
assists or new campaign progression. The seven protected inputs and original
code capture remain unchanged. This demonstrates presentation isolation and
repeatability, without independent retail mixed-audio, analog or listening
qualification.

The frozen consumer DSP qualification passes strict comparisons against the
old raw baseline and the new raw/processed headless references, including all
25 checkpoint states and three final statuses. Raw source fields and original
guest diagnostics remain exact while declared processed-output fields use
their separate profile-specific expectations.

The final independent batch audit passes **1,997 checks** and rehashes
**1,065 actual artifacts**, including every frozen consumer evidence binding,
with no failures or pending evidence. It checks the recorded Geargrafx filter
comparisons, authored FIR tests, builds/packages and internal retail replay
results within their separate scopes. This audit does not add independent
retail mixed-audio, decoder-clock, physical-device or listening qualification.

Two separate paced packaged executions select filtered 44.1 and 48 kHz output.
Both start in an empty
isolated working directory with no SDK or packaged `bin` directories on the
child `PATH`; actual same-process module inspection before and after execution
confirms the adjacent SDL DLL path/hash against the executable/build receipt.
Official descriptor verification and builds remain distinct from these direct
TCP-supervised executions; they are not official `project run` receipts.

Both runs generate **710,526 raw source frames** with raw PCM hash
**9,100,448,555,341,449,602**, peak 10,366, 524,060 nonzero raw mixed frames
and zero runtime queue discard. This paced opening contains CDDA energy but no
nonzero PSG/ADPCM source frames, so these checks qualify output conversion,
packaging and pacing rather than active source-filter quality.

| Paced output | Result | Host queue accounting |
|---|---|---|
| Filtered 44.1 kHz | 710,526 output/WAV frames; PCM hash 9,100,448,555,341,449,602 and peak 10,366 | 2,393 explicit pause-flush drops; peak pending 1,364 frames; final queue zero |
| Filtered 48 kHz | **773,361 output/WAV frames**, exactly `floor(710526*160/147)`; PCM hash 17,430,929,810,710,949,061 and peak 10,434 | 2,782 explicit pause-flush drops; peak pending 1,675 frames; final queue zero |

The queried SDL devices report the selected 44.1/48 kHz rates respectively,
stereo and numeric format 33056 (F32). Device acceptance/drain and queried
format do not qualify listening, analog levels or device-sample/WAV parity.
Both tests retain timestamped snapshots at least 0.15 seconds apart proving
paused guest clocks, source/processed counters and hashes remain unchanged;
resume, input press/release, guest/presentation captures and clean quit pass.
There are no RAM edits, and both owned children stop. All **190 consumer
tests** pass, including 15 new DSP qualification cases.

A fresh authored embedded SDL build uses an empty game module and completes
119 build steps. Its unchanged normal `scripts/check.py` runs **28 upstream
suites and all 291 Python tests with zero skips**, including the original
packaging test's nested SDK discovery. No test adapter or `PCE_TEST` override
is used. This qualifies the shared nested CMake-cache discovery correction;
it uses no retail execution, owner installation or saves. The consumer's 190
tests also pass in that configuration. The earlier raw-route results below
retain their original scope.

## Retained audio accuracy — digital reference

The PSG digital reference now uses a complete 32-sample waveform mean for
ordinary effective periods **1–5**, with per-channel nearest rounding and
ties away from zero before channel summation and half-scale truncation.
Period zero still means 4,096 PSG clocks. Periods 6 and above, DDA, noise,
configured LFO source/destination channels and trigger-held channel 1 retain
their separate sample rules. Waveform writes immediately affect the mean;
oscillator phase, guest clocks and register state remain unchanged.
No state field, runtime ABI **13** or consumer schema **1** changed.

The implementation is qualified at revision
`df7e16d465b1618e936d2750bdbe3259b56996a9`, source digest
`f2615f6278c030542fdef56e1709e6891f6e349662b2869a3a11f606a0431caf`.
That expanded-module SDL build passes **27 suites and all 273 Python tests**;
focused authored checks include **732 PSG** and **20,828 mixer** expectations.
A clean public-source default build passes **25 suites**, with seven
desktop-only skips among the same 273 discovered Python tests.

| Evidence | Result | Limit |
|---|---|---|
| Separately compiled Geargrafx 1.8.4 PSG source | 3,262 authored cases / 49,258 raw stereo pairs match, including six waveform indices and two noise seeds per observation, fractional means, side gains, both DAC profiles, DDA, noise and LFO | Pinned external source; positive oscillator-clock boundaries, raw half-gain digital profile before filters, resampling or source mixing; no zero-clock cached-DAC, CPU bus-phase, game or hardware parity |
| Unmodified Geargrafx 1.8.4 ADPCM binary | 18 authored cases / 108 main checkpoints across all 16 rates; predictor/index, nibble/address/length, IRQ flags and running phase match; stop/restart/reset adds five continuous probe checkpoints from one initial state; 131 raw serialized states checked overall | Pinned Windows v44 save-state layout, uniquely identified authored 64 KiB RAM and cross-checked public fields; no filtered/scaled emulator output or analog DAC parity |
| Finite ADPCM end | Decoder/end state agrees; reference stopped-phase residue 186,918 and runtime residue 55,846 are independently derived from the same vector | Their difference is two master ticks: Gear retains its whole six-tick CPU callback remainder; runtime stops at the exact integer tick. Stopped phases are explicitly not claimed identical |
| Independent evidence review | Reproduces both oracle comparisons and verifies bound source, binary, input and output identities | Source/state evidence only; not a second emulator or independent retail-route comparison |
| Fresh corrected-profile Ys III headless TCP replay | All 93,735 frames, 25 complete guest image hashes, 25 checkpoint states and every original final guest diagnostic match; 2,920,491,782 native / 981 interpreted retirements, 981 guard misses and all 460,685 block transfers native remain exact | Same assisted route, 709 original RAM transactions / 723 changed bytes, explicit `gear-good` profile, IPL entry and volatile BRAM; no extra assistance, campaign progress or independent retail-route comparison |
| Corrected-profile full-route digital output | All source counters and output remain unchanged: 69,095,406 frames; nonzero PSG 27,644,755, ADPCM 4,030,681, CDDA 49,762,727, mixed 65,958,163; peak 13,000, PCM hash 7,177,686,580,420,813,080, zero runtime discard; bounded 30-second WAV remains byte-identical | The authored ultrasonic cases exercise the correction. This route supplies regression evidence and demonstrates no retail PCM change or audible improvement |

The old PSG implementation fails the new unchanged oracle plan; the corrected
implementation passes. ADPCM runtime behavior did not need a decoder change.
The adapters preserve external source/binary/input identities, stop their
owned Gear process and remove its temporary configuration. Authored adapters
and wrappers are public; the GPL reference implementation stays an external
input and is not included or linked into the runtime. Commands and source
pins are documented in [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md#independent-digital-source-checks).
The fresh replay independently reproduces the earlier PCM/WAV values below
with the corrected source. Its retained 1,323,000-frame WAV has SHA256
`ee86382ebc96da7833c3b6fe36dd6b8c7703cc9a8f85d00e3f1d6d25b123d40f`.
Normal before/after source, input, capture and consumer-pin identity checks
pass. An earlier completed attempt failed its final context-identity check
after the concurrent consumer pin changed; that failed receipt remains
retained. The fresh run freezes the pin and passes the ordinary checks.
All seven protected inputs and the original code capture remain unchanged;
the owned headless child stopped. The earlier measurements below retain
their original qualification scope.

## Retained packaged Ys III consumer qualification

The separate [Ys III consumer revision 4046079](https://github.com/rages4calm/ys3recomp/commit/40460793193227f2ab6adadde5040f1b0a797f84)
rebuilds against the corrected toolkit revision `df7e16d` and source digest
above. The same 208 generated module files retain all 44,832 identities /
57 complete MPR contexts and are reused unchanged under ABI 13.
Its packaged desktop TCP replay independently reproduces the same complete
93,735-frame route, 25 guest image hashes/checkpoint states, original guest
and native/interpreted diagnostics, every source/mixed audio counter, PCM hash and WAV.
No extra assistance or audible-improvement claim is added.

Both the full and separate paced executions use an empty isolated working
directory and child `PATH` without SDK or packaged `bin` directories.
Live same-process inspection before and after execution confirms the
adjacent SDL DLL's path/hash against the bound executable and build receipt.
The full route intentionally mutes fast-forward device output.
The paced probe opens the default audio device, keeps fast-forward mute
false, and submits **710,526 frames**, with zero runtime discard, **2,680
pause-flush drops**, peak pending queue **1,583**, and final queue zero.
Timestamped snapshots at least 0.15 seconds apart prove paused guest/PCM
invariance; resume advances frame 901 to 962. TCP input, guest/presentation
captures and clean quit pass. Both owned children stopped.

All **116 consumer tests** pass. The fresh embedded authored build discovers
273 upstream Python tests with one nested SDK-discovery skip; that original
packaging test body passes separately with explicit SDK discovery and no
skip. This is distinct from the standalone expanded SDL build's all-273,
zero-skip result above. The final independent audit passes **137 checks**
and rehashes **487 actual artifacts**, with no pending evidence. Official
descriptor/build verification and direct TCP supervision retain separate
scopes; these are not official `project run` execution receipts.
See the [consumer package procedure](CONSUMER.md#verify-a-windows-desktop-package).

## Retained packaged Ys III qualification

This retained qualification precedes the PSG correction above.
The separate [Ys III consumer](https://github.com/rages4calm/ys3recomp)
builds its desktop executable through the official interface against toolkit
revision `cca01ca746cbee224f9050bb4064779f1800d093`, source digest
`cedf5f31116a20d7dd5eacdec8eeb156d67a962ef22f9c40316e9dd87f5dcfec`.
Consumer revision [97a013b](https://github.com/rages4calm/ys3recomp/commit/97a013b515a0b11d3a831ff1305d86f0607ddcf2)
records this qualification and its reusable package/queue validation tests.
The packaging correction changes neither runtime ABI **13** nor descriptor
schema **1**. The same 207 translation units and one generated header retain
44,832 identities / 57 complete MPR contexts and the original six-byte
promotion exclusion. No runtime/compiler source change was needed in this
qualification batch.

Both paced and full-route executions use an empty isolated working directory
and a child `PATH` without SDK runtime or packaged `bin` directories. Live
process inspection at startup and completion identifies the adjacent
`SDL3.dll`, matching the DLL hash bound in the new build receipt. The
executable and packaged DLL retain those hashes after execution. No SDK
`PATH` workaround, implicit DLL copy or owner environment change is used.

| Evidence | Result | Limit |
|---|---|---|
| Packaged desktop TCP replay | All 93,735 frames, 25 complete guest image hashes, 25 checkpoint states, 709 original transactions / 723 changed bytes and final original guest diagnostics match | Same assisted IPL-entry route and explicit `gear-good` profile; no extra assistance, progression or independent retail-route qualification |
| Native execution | 2,920,491,782 native / 981 interpreted retirements, 981 guard misses and all 460,685 block transfers native remain exact | Coverage measures this observed route, including firmware/wait loops; no complete-game coverage claim |
| Full-route digital output | 69,095,406 stereo frames, PCM hash 7,177,686,580,420,813,080 and all source counters match; zero runtime discard. The bounded 30-second WAV is byte-identical to the earlier audio qualification | Unthrottled presentation is explicitly muted; route PCM/WAV agreement is internal reproducibility, not audible or analog parity |
| Paced packaged SDL stream | 710,526 frames accepted/drained; device open, fast-forward mute false, zero runtime discard, peak pending queue 1,600 frames, final queue zero; 2,916 device frames discarded by explicit pause flushes | Separate paced TCP input, guest/presentation capture, pause/resume and clean-quit test; no RAM edits, listening or analog-output qualification |
| Test suites | Toolkit: 27 suites and all 254 Python tests pass; consumer: all 104 tests pass | Windows x64; retained default-source and other reference scopes remain below |

Official descriptor verification and build receipts bind the package. A
separately bounded direct TCP supervisor owns the execution tests; these are
not official `project run` execution receipts. One paused checkpoint's TCP
snapshot precedes the main-thread audio drain, retaining 29 generated frames
in the bounded 8,192-frame source queue. The other 24 checkpoints and final
drain have zero pending source frames. This source queue is checked separately
from the SDL queue and explicit device drops; runtime discard stays zero.
Both test children stopped.
The final evidence audit passes 92 checks and rehashes 238 artifacts. The
earlier qualifier failure remains retained: it incorrectly required every
checkpoint to have drained immediately. The corrected validator checks the
bounded pending frames, applies WAV quotas to actually drained frames, and
requires final queues to settle; authored acceptance/rejection regressions
cover those contracts. No runtime result or raw route receipt was changed.
Volatile BRAM, conditional firmware entry, unknown-command response and
assisted-encounter limits remain unchanged. The earlier consumer audio batch
used the SDK `PATH` workaround; its receipts remain retained under that scope.
This batch establishes the subsequent packaged execution rather than
retroactively changing those receipts. See the
[consumer package procedure](CONSUMER.md#verify-a-windows-desktop-package).

## Windows embedded desktop packaging correction

A parent-created desktop consumer now receives its selected SDL runtime DLL
beside the executable, with that DLL included in build/execution receipt hashes.
Previously the directory-local imported SDK target was hidden from the parent
packaging rule: an authored build succeeded but exited with loader status
`0xC0000135` before guest entry. Runtime metadata is now captured where the
target is visible; configuration mappings are preserved without global target
promotion or a CMake minimum increase.

Two added regression tests cover imported scope, single/multi-configuration
selection, static/built targets, actual SDK packaging, execution without SDK
DLL directories on `PATH`, and refusal after packaged-DLL tampering. The authored
consumer executes 200 native / zero interpreted instructions through the official
interface. Runtime sources, ABI 13 and consumer schema 1 are unchanged; the
audio/gameplay evidence below remains its original qualification scope.
The packaging-correction expanded/SDL builds pass 27 suites and all 254 Python tests. Clean
default public source passes 25 suites with seven desktop-only skips among
254 Python tests. These are Windows x64 results; other hosts remain unqualified.
The correction was qualified at code revision
`a4c1de1602b6d383436a5c20d4493ad22a7b3428`, source digest
`cedf5f31116a20d7dd5eacdec8eeb156d67a962ef22f9c40316e9dd87f5dcfec`.
The standalone runtime executable hashes are unchanged from the audio batch.

## Digital audio milestone — ABI 13

This retained milestone records the initial digital profile and its original
PCM/WAV results. The current PSG correction and larger oracle scope are above.

The runtime now produces 44,100 Hz signed-16 stereo PCM from centered
HuC6280A PSG synthesis, the unsigned 12-bit wrapping MSM5205 ADPCM decoder
and read-only CHD CDDA samples. Fixed one-third source gains, CD fader gating,
a bounded guest-clock queue, optional SDL playback and explicit bounded new
WAV capture are implemented. Guest cadence and device control/IRQ state remain
separate from host presentation. See [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md).

At this retained milestone, native ABI was **13**; consumer TOML schema was **1**. ABI-12 code
observations can be regenerated into ABI-13 modules; compiled ABI-12 objects
must not be linked to the new runtime. The optional consumer `[runtime] audio`
setting selects `on|off`; omission preserves the host's default. Desktop
attempts audio by default; headless stays off unless explicitly requested or
capturing a WAV. Disabled audio preserves the previous reference path.
Unthrottled desktop execution mutes device presentation and reports
`fast_forward_muted`; source-clock PCM and bounded WAV capture continue.

| Evidence | Result | Limit |
|---|---|---|
| Focused authored digital tests | 20,692 mixer, 154 PSG, 4,220 ADPCM, 11,830 CDDA provider/cache and 8,374 CDDA stream-order checks pass | Source expectations are not an external oracle |
| Retained audio-batch builds | Expanded module: 27 suites / all 252 Python tests pass. Clean public-source default: 25 suites / 252 Python tests discovered, six desktop-only skips; clean SDL: 27 suites / all 252 Python tests pass | Windows x64; empty module selection in public-source builds; superseded test counts are recorded in the packaging correction above |
| Independent Geargrafx 1.8.4 raw CDDA | 56 stereo pairs / 112 scalar samples match, including 40 audio pairs and 16 data-track silent pairs | Authored CUE/BIOS; samples selected by observed LBA/frame identity; no CHD decompression, exact sample-clock/seek, mixed-output or hardware parity |
| Independent Geargrafx PSG phase | 24 settled waveform-index checks match at frequencies 64, 127 and 512 | Safe mid-period checkpoints after DDA fall; no raw PSG/ADPCM PCM, hidden noise/LFO state or analog output comparison |
| SDL audio host | 150 focused authored queue/pause/bounds checks passed; 18 CLI/WAV integration tests pass, including dummy-device unthrottled mute | Synthetic host/CLI checks, separate from real-device evidence |
| Paced real SDL device stream | 930,219 PCM frames submitted; device opens, `fast_forward_muted=false`, zero runtime discard, 1,032 pause-flush device drops, peak pending input 1,591 frames and final input queue zero; PCM hash 13,875,472,373,063,429,143 | Approximately 21 paced seconds; data accepted/drained through SDL, not listening, loopback, analog-level or complete-game audio qualification |
| Current Ys III bootstrap | 30 million instructions: ABI-13 audio-off report matches the retained baseline exactly; audio-on matches after removing only the new `audio_output` object; 783,067 PCM frames, 598,753 nonzero CDDA frames, 596,601 nonzero mixed frames, peak 10,366, zero queue discard | Bootstrap scope only; no PSG/ADPCM energy on this segment |
| Full ABI-13 audio-enabled Ys III SDL/TCP route | All 93,735 frames, 25 complete guest PNG hashes, 709 original RAM transactions / 723 changed bytes and every original final guest JSON value match the previous full-native ABI-12 run; 2,920,491,782 native / 981 interpreted instructions, 981 guard misses and 460,685 native / zero interpreted block transfers remain exact | Only new validated `audio_output`, ephemeral TCP port and SDL host telemetry are separate; no original guest-field projection, extra assistance or progression; no whole-RAM, independent retail-route or hardware parity |
| Full-route digital PCM and WAV | 69,095,406 stereo frames; nonzero PSG 27,644,755, ADPCM 4,030,681, CDDA 49,762,727, mixed 65,958,163; peak 13,000, PCM hash 7,177,686,580,420,813,080; zero runtime discard. WAV retains 1,323,000 frames / 5,292,044 bytes with truncation reported | Source counters overlap; WAV is the first bounded 30 guest seconds. Unthrottled device presentation intentionally drops all submitted frames under `fast_forward_muted=true`; this run is not playback proof |
| Official ABI-13 consumer contract | Twelve translation units / eleven identities / one MPR context execute 200 native / zero interpreted instructions; A=31, PC=16409, ticks=2385; four PCM frames at stereo (1,761, 0), peak 1,761 and hash 2,178,522,702,462,881,053; complete eleven-observation ABI-13 capture | Source/module/input/output/capture pins validated; authored program, not game sound or hardware parity |

The successful owned Gear process stopped and its temporary portable
configuration was removed. All three authored reference inputs remain
unchanged. The first probe correctly refused while the independent playback
delay was still pending; the final adapter observes seek and playback-delay
completion separately before comparing exact raw samples. No runtime
expectation was relaxed to make that reference check pass.
The full route and paced SDL test also stopped their owned children. Paced PCM contains 745,905
nonzero CDDA frames and 743,753 nonzero mixed frames, peak 10,366. These are
source/queue measurements; they do not establish what reached the speakers.
The full route's 306.1768-second wall time is an operational run bound, not a
controlled speed benchmark. Retained performance measurements below belong
to the prior ABI-12 dispatch batch. That audio qualification used revision
`d72d6583e492224656ec0638f52e02798738ffb8` and source digest
`f873f8d0e06418dffbf1ed478cd46bf1eae6fdf4511fc2797db8193bf04c99f6`;
documentation-only closeout does not change that source digest.

All seven protected input hashes remained unchanged. No original media,
owner save, installation or settings were modified.

## Retained dispatch and module-build milestone — ABI 12

Observed-code dispatch now uses full-MPR/page/PC routing, exact opcode/operand
keys and shared identical bodies. Source peeks remain pure, checking every
byte on each instruction; direct raw RAM changes cannot hide behind unchanged
generation counters. The dedicated native-source test passes 6,668 independent
expectation groups. That retained run used runtime ABI **12** and descriptor schema **1**.

The retained 44,832-identity module emits 207 independently compiled units
with a 256-identity partition target. Its largest same-PC group has 3,695
variants and deliberately stays together. The two hosts share one module
object library. Generated sources total 22,988,937 bytes including the header,
compared with the older 17,067,985-byte source: this change targets compiler
work and dispatch cost, not smaller source text. All listed sources and headers
are hash-pinned through consumer build/run receipts. Authored compiled tests
verify same-page partition boundaries, object reuse and tamper rejection.

The final 17-unit authored probe independently passes Geargrafx's same 78-plan
matrix in both tiers: 156 CPU/MPR/latch states, 156 clock deltas and 78 complete
8 KiB RAM matches per tier, plus 306 local unchanged-state guard checks.
Native execution is 156 instructions with zero fallback. See
[measurement details](PERFORMANCE.md) and [reference scope](REFERENCE.md).

That batch's expanded-module build passes all **21** enabled suites and **231 Python
tests**. An isolated clean source checkout with the same source digest passes
all **20 default suites** (231 tests, four desktop-only skips) and **21 SDL
suites** (all 231 tests), using empty module selection and authored inputs.
The official consumer interface separately builds a five-unit authored module
and verifies its header and every source in the receipt. Execution qualifies
200 native / zero interpreted instructions, A=41, X=140, PC=16387 and 1,794 ticks,
with a complete four-identity capture and unchanged source/input/output hashes.

The final optimized-module hidden SDL/TCP run reproduces all **93,735 frames**,
**25 complete guest PNG hashes** and the original **709 RAM interventions / 723
changed bytes**. It retires **2,920,491,782 native + 981 interpreted instructions**
and all **460,685 block transfers natively**. After checking ephemeral TCP port
and SDL host telemetry separately, its complete final runner JSON equals the
previous full-native run, including tier counts and 981 guard misses. No guest
field or tier counter is projected away in this additional comparison.
The earlier lower-coverage route remains a separate bridge. This adds no new
assistance, progression, boss victory or unassisted qualification. The owned
test host stopped; no new game screenshots were retained.

Local performance measurements separately record full-module compile time
**353.221 → 70.502 seconds** at the same two-job cap (one sample each), and
**1.09472×** authored dispatch throughput across five alternating measured
pairs with identical counters/checksums. A 30-million-instruction Ys III bootstrap
with 1,062 completed frames and zero fallback has identical complete final JSON;
whole-process medians are **3.059198 → 3.015789 seconds**. These scopes differ:
the bootstrap difference is roughly 1.4%, with startup/rendering/media overhead
included. Shared host load/caches are disclosed; no whole-campaign speed claim
is made. See [PERFORMANCE.md](PERFORMANCE.md) for controls and limits.

## Retained observed-code and consumer milestone

The shared compiler now accepts bounded retired-code observations and emits
multiple complete MPR contexts, source-byte variants and overlapping observed
interpretations. Logical PC, full mapping and exact instruction bytes remain
mandatory dispatch guards. The raw capture and generated game/firmware source
stay private. These retained results used runtime ABI **12** and consumer descriptor schema **1**.

| Evidence | Result | Limit |
|---|---|---|
| Complete profiling route | 93,735 frames; 44,836 observed identities, 57 full MPR contexts, 2,920,492,763 retirements; zero dropped/unreadable instructions | Complete for this observed run only, not all reachable game code |
| Expanded direct C++ module | 44,832 compiled identities in 57 contexts; four identities / 981 observed hits excluded because they touch the temporary patch span | Original and patched interpretations in that span both remain interpreted; raw capture, original hit totals and completeness are unchanged |
| Executed coverage, full SDL/TCP replay | 2,920,491,782 native + 981 interpreted; **99.9999664% native**, up from 0.1729351%; all 460,685 block transfers native | Retired instruction ratio includes firmware/wait loops; no whole-program coverage, controlled speed benchmark or campaign-completion claim |
| Replay correctness | All 93,735 frames, 25 complete guest PNG hashes, 709 original RAM interventions / 723 changed bytes and every exposed final guest CPU/device/source value match; total retirements and clocks exact | Tier splits/guard counts intentionally change; ephemeral TCP port and additive SDL telemetry checked separately. No whole-RAM, composed-pixel or independent retail-route parity |
| Final Geargrafx observed-code probe | 78 authored plans; per tier 156 CPU/MPR/latch states, 156 instruction-clock deltas and 78 complete 8 KiB RAM comparisons; native tier 156 instructions, zero fallback; 306 local unchanged-state guard checks | Seven contexts / 21 compiled identities; remap, variants, cross-page/wrap, T/decimal, TMA/TAM, PHA/RTI. No IRQ delivery, device timing, retail-route or hardware qualification |
| Consumer interface, authored build/run | Pinned tool/source/ABI/module/input identities verified; embedded shared runtime builds without retail data; 200 native / zero interpreted instructions, A=41, X=140, PC=16387, ticks=1794; valid complete four-identity capture receipt | Source digest equals clean public-source checkout; build/run/capture identities checked separately; parent test configuration preserved |
| Separate Ys III consumer integration | Official project build/run guards reproduce all 93,735 frames, 25 images and 709 interventions with 2,784,362,065 native / 136,130,698 interpreted instructions (95.3387764%) | Consumer deliberately chooses a smaller 2,048-identity / nine-context original-code hot set; same tool source digest. Internal cross-project reproduction, not a second emulator or hardware oracle |
| Current default public-source build | All 19 suites pass; 202 Python tests discovered, four desktop-only skips | Empty module selection; authored fixtures, no private title/firmware/generated module |
| Current SDL public-source and expanded-module builds | All 20 suites and all 202 Python tests pass in each; 119 actual TCP assertions, 18 client checks, 122 SDL renderer/input assertions | Windows x64 / Clang 22.1.8 / SDL 3.4.18; other hosts and physical-controller interaction still require runs |

The successful expanded route uses the same input and assistance journal as
its baseline. It adds no new game progression or RAM intervention. The first
storehouse boss encounter and observed damage remain explicitly assisted;
there is no victory claim. The `gear-good` unknown-response profile and volatile
BRAM conditions remain visible and unresolved as before. See
[CODE_CAPTURE.md](CODE_CAPTURE.md), [CONSUMER.md](CONSUMER.md) and
[REFERENCE.md](REFERENCE.md).

## Retained hardware and gameplay evidence

The following rows preserve earlier qualification scopes and counters. Their
BRAM/debug-batch totals and older native modules describe those retained runs;
the current compiler/consumer result is recorded above.

| Evidence | Result | Limit |
|---|---|---|
| Windows x64, Python 3.14.5, Clang 22.1.8, CMake 3.31.12, Ninja | Runtime, generated synthetic modules, headless runner and optional reference probe compiled | Other hosts require their own build/run evidence |
| Retained BRAM/debug default source checkout | Generic sandbox and optional reference probes compiled; all 19 suites pass; 155 Python tests discovered, with four desktop-only tests skipped | Windows x64; SDL disabled, empty module selection, no private dependencies or title inputs |
| Retained BRAM/debug desktop source checkout | All 20 suites and all 155 Python tests pass, including desktop and TCP host integration | Windows x64, SDL 3.4.18 SDK; empty module selection; authored fixtures only, no private game/firmware/generated module |
| Complete local verification, retained BRAM/debug batch | All 20 enabled suites pass, including 155 Python tests | Windows x64, optional SDL enabled; authored synthetic tests; public-source-only qualification is reported separately |
| Frontend/host unit suite, retained BRAM/debug batch | 155 tests pass, including initial-BRAM loader and execution-limit checks, 18 development-client checks and DMA-populated SATB/paused-observation checks | Media/analysis/decoding, loader/source protection, descriptors, controller/scripts, explicit response profiles, reference adapters and live runner/server integration; not retail game fixtures |
| Generic initial BRAM image, retained BRAM/debug batch | Optional read-only exact 2,048-byte seed loads into existing volatile BRAM; absent option preserves blank state; TCP/final JSON identify whether seeded | No formatting, file modification, export, persistent host saves or runtime ABI change; guest changes remain process-local |
| Local formatted-start SAVE/LOAD, retained BRAM/debug batch | Normal SAVE slot 1 at frame 17,886 and LOAD at 18,324 restore Weapon Shop with HP 20, EXP 0, gold 100 and STATUS strength/defense 20/25 | Authentic System Card FORMAT seed is read-only and unchanged; game uses existing volatile BRAM; no cross-process persistence/export or authentic-reset qualification |
| Independent Geargrafx formatted-start SAVE/LOAD and STATUS, retained BRAM/debug batch | Normal SAVE/LOAD slot 1 in Sarina retains STATUS 20/25; stable LEVEL 1 / STR 20 / DEF 25 / NEXT 100 text matches the local loaded scene: 80 × 32 crop, 2,560 pixels, zero differences | Crop aligned by (+24, +3); unrelated scene/menu/cursor/counters excluded; no full-frame, damage/reward, timing, CPU-state or hardware parity |
| Normal level progression, current local and reference routes | Local LEVEL 2, HP 30, EXP 102, gold 168, STATUS 25/30, NEXT 300; Geargrafx LEVEL 2, HP 30, EXP 108, gold 172, same STATUS 25/30/NEXT 300; both reach the four-exit junction | Separate normal-input routes with unequal EXP/gold: outcome classes and displayed stats only; no independent boss, full-route, campaign or audio qualification |
| Ordinary-input local route and current-host bridge | 60,338 frames; four-exit mine junction, normal slot-3 Mine Creek SAVE/LOAD at HP 17 / EXP 132, then stairway combat ending HP 6 / EXP 152; current host matches 14 complete PNG hashes and every original final CPU/device/source diagnostic | Zero RAM edits; only new host-control metadata is projected into older expectations; current-host reproducibility, not whole-route independent emulator or final SDL qualification |
| Assisted local route and retained replay checkpoint | Owner-authorized current-health refills; Roy's Pendant at frame 66,171 and Storehouse Key at 70,079 acquired through normal chest/dialogue triggers; temporary higher jump from 77,859; replay through 79,445 matches 18 complete PNG hashes, final diagnostics and 105 edits (104 health refills, one jump patch) | Separate from ordinary gameplay; no level/max-health/equipment/inventory/quest/position edits at this checkpoint; jump patch active there; no boss or final SDL result in that retained run |
| Later assisted storehouse-interior route, replayed through 87,449 | Clean requested quit after reaching green-brick storehouse interior through an ordinary room transition under position/height assistance; fresh headless replay matches 22 complete PNG hashes, final diagnostics and 346 edits: 128 health (one menu preview), 215 position/camera/cache/height experiments, one earned-item-state transfer after LOAD, two jump-patch transactions | Failed vertical/camera experiments were cleared by normal LOAD; higher-jump patch restored at 85,900; no extra PNG copies; no boss, final SDL or ordinary-gameplay qualification |
| Assisted first-storehouse-boss encounter, final route | Boss entered at frame 93,212; observed green wizard teleport/sword/fireball behavior; ordinary II attacks visibly reduce the ENEMY bar by frame 93,735; 523 boss frames with 14 current-health refills only | No code/position/camera-queue/inventory/quest writes after boss entry; jump patch restored at 85,900; successful approach restores actually earned item checkpoint, then uses queued ascent and height-held traverse, followed by ordinary room transition/Up door entry; no boss defeat, unassisted route or independent whole-route qualification |
| Final assisted local run, retained BRAM/debug batch | 93,735 frames / 33,650,360,835 ticks; 2,920,492,763 instructions: 5,050,558 native + 2,915,442,205 interpreted; 1,181 sectors, zero read errors; 372,199 IRQ/RTI sequences; 1,835,008 ADPCM DMA bytes; final actual/HUD HP 36 / maximum 40, EXP 466, gold 484, RP 75 | 709 RAM transactions / 723 changed bytes: 145 health (one historical menu preview), 463 position/cache/raw-camera experiments, 98 canonical queue, one earlier inventory test, two jump apply/restore; explicit unknown-response profile used 51 times; no victory or full native/AOT qualification |
| Final SDL cross-host replay | All 93,735 frames reproduce; 25 complete guest PNG hashes, all 709 edit transactions / 723 changed bytes and every exposed final CPU/device/source/debug diagnostic match; clean exit 0; zero new PNG files | Same frozen source and unchanged SDL binary; comparison covers exposed diagnostics and guest images, not whole RAM or every composed SDL pixel; internal reproducibility, not independent hardware/full-game parity |
| Independent Geargrafx assisted probes | Health readback/HUD checks, paired ordinary versus higher-jump arcs, and guarded horizontal relocation within the same loaded room | Scoped assist behavior only; no complete assisted route, boss, full-frame, timing, CPU-state or hardware parity; horizontal reference relocation is not local route evidence |
| Continuous video expectations, retained first-mine checks | 3,950 independent checks pass; existing 628,214 snapshot/palette expectations also pass | Historical palette/VRAM/SATB/scroll changes, CR/MWR latches, bounded publication/reset, all VCE timing controls, partitioning and unchanged guest state; physical fetch/contention and sprite IRQs excluded |
| Independent Geargrafx continuous video, retained video batch | Four authored plans × four distinct frames: 16 complete 256 × 192 RGB images / 786,432 pixels match byte for byte; final probe bridges all images and publication timestamps exactly | Active crop of Geargrafx's debug viewport; midline palette, line-latched scroll, VRAM changes, map wrap and sprite modes; no hardware/full-game frame qualification |
| Optional SDL3 desktop host, retained first-mine tests and earlier UI evidence | 122 renderer/input assertions pass; preceding video batch observed visible menu, Run-to-warning, pause/resume and fullscreen transitions | SDL 3.4.18 Windows x64; two-frame quick-tap retention and keypad direction aliases locally tested; physical controller and other operating systems unqualified |
| Loopback development server, retained BRAM/debug batch | 119 actual TCP assertions plus 18 Python client checks pass; both hosts' integration tests pass | Strict bounded protocol, five input slots, pause/step/status/capture/quit, paused RAM/ROM inspection and opt-in compare-before-write RAM edits; source invalidation, disabled/stale/cross-bank refusals, disconnect and stalled-peer behavior; no independent PC Engine oracle claim |
| Independent Geargrafx town controls, retained town batch | Authentic-reset route: 11,230 frames; two neutral-controlled I jump/land cycles; Select menu confirmed; aligned 72 x 40 menu text crop matches all 2,880 pixels | Different startup from local IPL sandbox; blinking cursor/unrelated scene excluded; no full retail-frame, CPU-state, combat, hardware or campaign parity claim |
| Independent Geargrafx first-mine combat, retained first-mine batch | Normal quest/shop progression and visible sword; HP 20 → 10, EXP 0 → 12, gold 100 → 108; death and settled Run retry restore HP 20 | Earlier selected-gear claim withdrawn: red slots alone were ambiguous; restored checkpoint STATUS remains 10/10. Different starting scene/cadence permits outcome-class corroboration only; no exact damage/reward/frame/CPU parity, kill count, boss, campaign, audio or hardware qualification |
| Internal native/interpreter checks | 14,912 comparisons across 233 opcodes pass | Shared framework assumptions can still be wrong |
| Independent IRQ/RTI expectations | 65,536 entry cases, 262,144 RTI cases, 32 sampling sequences, 15 guard/mapping/deadline groups and 779 register/timer groups pass | Both tiers/speeds; aggregate sampling contract, no physical bus-phase qualification |
| Independent Geargrafx IRQ/RTI check | 832 plans per tier: 2,496 CPU states, 832 complete work-RAM images and 832 complete-sequence clock deltas pass | Real pending sources in reference, corresponding injected lines in local probe; no native fallback; source edge/MMIO phases and hardware excluded |
| Independent palette/snapshot expectations | 628,214 checks pass | Palette byte/index/mirror sweep, tile planes, sprite sizes/flips/priority/line budget and no simulation mutation; current-state image only |
| Independent VRAM/SATB DMA expectations | 14,786 checks pass | Direction/overlap/address wrap, dot cadence, terminal registers, completion gates and SATB priority/repeat; CPU contention excluded |
| Independent Geargrafx palette/DMA check | 12 direct-device plans pass, including full VRAM/SATB/palette and 1,024 guest palette-read bytes | Settled device effects, no per-tier CPU execution, exact DMA phases, frame rendering or hardware claim |
| Independent PSG expectations | 2,144 register groups, 174,592 waveform/DDA/LFO cases and 769 bus/latch groups pass | Write-side state only, no oscillator clocks or PCM synthesis |
| Independent ADPCM expectations | 20,736 port/slot/control groups, 67 playback/length groups, 10 DMA groups and 257 bus groups pass | RAM/ports, consumed nibbles, length IRQs and CD DMA; no decoded PCM or audio output |
| Independent Geargrafx ADPCM/PSG check | Eight direct-device plans pass: 292 guest read bytes, complete ADPCM RAM and six PSG channel states | Settled manual ports only; ADPCM playback/DMA, waveform bytes, oscillators and mixed audio excluded |
| Independent CDDA control/fader/response-profile expectations | 7,134 checks pass | D8/D9/DA/DD state/position/response boundaries, fader and explicit unknown-command profile; deterministic seek and sector timeline, no live CDDA or PCM qualification |
| Independent input-script expectations | 4,136 checks pass | ASCII/size/event bounds, full 12-bit masks, integers and host snapshot format; no desktop polling or gameplay certification |
| Independently expected bit/stack checks | 92,160 cases pass across both tiers, plus mutation/mapping/fault checks | Instruction-level cycles checked; no bus-phase/IRQ model |
| Independently expected data checks | 7,340,032 arithmetic/logic cases and 340 addressing cases pass | All ADC/SBC byte pairs under C/D/T/V combinations in both tiers; instruction-level timing only |
| Independently expected RMW/JMP checks | 3,932,160 RMW and 16,384 indirect JMP cases pass, plus native wrap/MMU/fault checks | Every RMW byte/status combination in both tiers; instruction-level timing only |
| Independently expected bit-test/branch/BSR checks | 4,849,664 bit-test and 2,228,224 branch/BSR cases pass | Synthetic operands/status/stack cases; fixed native immediate/mask values, not every encoding of literals |
| Independently expected MPR/latch checks | 1,114,112 cases pass, plus remap/mutation/deadline sequences | All masks/byte values in both tiers; arbitrary-map OR sweep interpreted; instruction-level timing only |
| Independently expected speed checks | 524,288 cases pass, plus sequence/deadline/mutation/fault checks | All status/latch bytes, both entry speeds and tiers; independently specified split-cycle tick table |
| Independently expected CD-control/BRAM checks | 67,584 native/interpreter instruction cases, 2,048 BRAM readback sequences and 16,144 decoded register groups pass, plus extent/lock/alias/RMW/guard/deadline/fault checks | Both tiers/speeds and reference BRAM readback/undefined-read decoding; idle control scope, no transport/audio scheduler claim |
| Independent Geargrafx unknown-command response check | Three plans, 87 CPU/device checkpoints and three complete RAM/BRAM comparisons per tier pass | Explicit unknown-response profile; proves protocol response, not unknown-command operations or hardware |
| Independent Geargrafx BRAM/read decoding check | Four plans, 27 CPU/device checkpoints and four complete RAM/BRAM comparisons per tier pass | BRAM gate readback, lock/alias behavior and unused decoded CD read `$FF`; no subcode interpretation or persistence |
| Independently expected CD-transport checks | 8,369 groups pass: 4,096 latch/control byte groups, 4,096 RMW groups and directed handshake/timing/reset/IRQ/guard/refusal checks | Both execution tiers and CPU speeds; literal local deadlines, TEST UNIT READY only; no sector responses or live access-phase proof |
| Independently expected TOC/DATA IN checks | 418 groups pass: literal BCD/response bytes, manual/auto-ACK timing, status/message completion, data IRQs, reset/selection aborts, metadata validation and explicit refusal | Both execution tiers/speeds; four-byte Gear/Mesen metadata-response profile, no readable sector provider or hardware qualification |
| Independently expected joypad checks | 50,341 cases/groups pass: 32,768 button, 8,192 control, 136 tap, 9,228 bus and 17 host/configuration checks; eight synthetic headless tests also pass | Both execution tiers/speeds; selected Geargrafx reference profile, no desktop polling or physical controller qualification |
| Independent block-transfer expectations | 1,600 instructions plus 5,120 status/stack cases, four local destructive-opcode cases, 23 guards/deadlines, 8,204 device checks and four deferred IRQ groups pass | Both tiers/speeds for RAM and deferred IRQ; interpreted actual MMIO plus block-aware wrapper checks; aggregate cycle profile, no exact bus-phase claim |
| Independent Geargrafx block transfers | 810 completed-instruction CPU/MPR states, 810 full 8 KiB RAM comparisons and 810 matching complete-instruction clock deltas per tier; all 16 shards pass | Both speeds, all five zero-count transfers, overlap/wrap/stack/operand aliases; no native fallback; excludes opcode-overwrite/MMIO/access phases/IRQ delivery/hardware |
| Independent READ expectations | 621,096 checks pass: full 256-sector request, both CPU tiers/speeds and ACK modes, byte/backpressure/reset/failure/guard boundaries | Deterministic 1x timing constants; no physical seek or IRQ delivery proof |
| Independent provider expectations | 22,568 checks pass: SHA256 known answers, ISO, CHD geometry/cache through an authored decoder ABI double | ABI double does not test actual decompression |
| Independent Geargrafx READ check, retained evidence | Seven plans; 201 settled CPU/device checkpoints and seven complete sectors / 14,336 payload bytes per tier pass | 15,552,742 retired native vs interpreted instructions including delay NOPs; exact seek/access/stream-loop cadence not qualified; final probe bridged exactly |
| Private on-demand CHD provider check | Six real sectors / 12,288 bytes agree with Python slicing/mapping; six protected input hashes unchanged | Shared libchdr decoder, not independent decompression qualification |
| Independent Geargrafx 1.8.4 joypad check, retained evidence | 56 plans, 2,512 CPU/port-read checkpoints and 56 complete 8 KiB work-RAM comparisons per tier pass; 2,512 native vs 2,512 interpreted instructions | USA region with CD present/absent; Japanese line local/source-only; guest output observations, no direct internal controller-state, host event timing, hardware or gameplay proof |
| Independent Geargrafx 1.8.4 TOC/DATA IN check, retained qualified scope | 25 of 26 plans qualified; 1,964 settled CPU/device checkpoints and 25 full work-RAM/BRAM comparisons per tier; 653,294 native vs 653,294 interpreted instructions | `toc-reset-auto-response-pending` remains unqualified after two reference access violations; eight earlier TOC plans bridge exactly to final ABI-7 probe; no sector, exact access-phase, hardware or gameplay proof |
| Independent Geargrafx 1.8.4 CD-transport check, retained evidence | 21 plans; 743 settled CPU/device checkpoints and 21 full work-RAM/BRAM comparisons per tier pass | 1,007,851 native vs 1,007,851 interpreted instructions including settling NOPs; frozen original 18 plans bridged exactly to that batch's final build, three added edge plans checked live; no sector backend, access-phase, hardware or gameplay proof |
| Independently expected VDC checks | 77,824 instruction expectations, 8,192 register-width cases and 392,991 VRAM transfer/address cases pass, plus status/guard/deadline/fault checks | Both execution tiers for CPU cases; synchronous functional profile; fixed access waits, no raster/rendering/DMA |
| Independent raster expectations | 977 directed groups plus 240,015 native/interpreter cadence, alias, speed and refusal checks pass | Literal edges, CR gating, status acknowledgement, timing latches, partition independence, all eight VCE timing controls; no sub-instruction bus-phase or rendered proof |
| Independent Geargrafx 1.8.4 raster check, retained evidence | 15 plans; 4,165 exact-clock device checkpoints and 15 guest status acknowledgements pass | VCE/VDC positions, horizontal/vertical phases, sticky VBlank/RCR flags and local IRQ1; divider 4 / 262 lines; direct device probe, no per-tier live CPU or bus-phase claim |
| Independent Geargrafx 1.8.4 MCP check, retained VDC port batch | 48 sequences; 856 settled CPU/VDC states and 48 full work-RAM/VRAM comparisons per tier pass | Eight disjoint shards; 14,552 native vs 14,552 interpreted instructions including 13,696 settling NOPs per route; no live busy/status-event, dynamic timing, DMA, rendering or gameplay proof |
| Independent Geargrafx 1.8.4 MCP check, retained CD-control batch | 48 sequences; 720 CPU/device states and 48 full RAM/BRAM comparisons per tier pass | Two disjoint shards; authored synthetic bootstrap/CD; 720 native vs 720 interpreted instructions; no live nonzero IRQ-source, cycle/device-phase or gameplay proof |
| Independent Geargrafx speed batch, retained prior evidence | 24 sequences; 120 CPU/speed states and 24 final RAM/latch comparisons per tier agreed; 92 tick deltas per tier agreed | Not rerun this batch; 28 documented transition-timing differences per tier remain |
| Independent Geargrafx MPR batch, retained prior evidence | 524 sequences, 1,614 instruction states and 524 final RAM/latch comparisons per route passed | Not rerun in the retained BRAM/debug batch; native-first: 1,078 native + 536 interpreted after context changes |
| Independent Geargrafx bit-test/branch/BSR batch, retained prior evidence | 480 native + 480 interpreter comparisons across all 30 opcodes passed | Not rerun in the retained BRAM/debug batch |
| Independent Geargrafx RMW/JMP batch, retained prior evidence | 512 native + 512 interpreter comparisons across all 32 opcodes passed | Not rerun in the retained BRAM/debug batch |
| Independent Geargrafx data batch, retained prior evidence | 1,552 native + 1,552 interpreter comparisons across all 97 data encodings passed | Not rerun in the retained BRAM/debug batch |
| Independent Geargrafx bit/stack, retained prior evidence | 128 native + 128 interpreter comparisons across all 24 bit/stack opcodes passed | Not rerun in the retained BRAM/debug batch |
| Independent Geargrafx baseline, retained prior evidence | 188 native + 188 interpreter comparisons across the original 47 opcodes passed | Not rerun in the retained BRAM/debug batch |
| Local owner-supplied Ys III USA CHD | Track metadata, hashing, two-hunk decompression and 4 KiB initial program extraction verified | Filename/internal title identify the local input; no external dump-database certification |
| Supplied USA v3.0 firmware | Raw 256 KiB size and MD5 match the documented USA BIOS; SHA1/SHA256 pinned locally | Supplied patched USA/Japan images have distinct hashes and are excluded from the baseline; see FIRMWARE.md |
| Boot-program-only analysis | 203 discovered instruction sites, all 203 native-emittable, 25 unresolved records | Static discovery is not an execution-coverage measurement |
| Combined local boot/BIOS snapshot | 785 discovered sites, all 785 native-emittable, 47 unresolved records under a 1,024-instruction analysis limit | One initial MPR context; no speculative firmware services |
| Compiled local boot/BIOS module, retained ABI-11 conditional story route | 229,808,207 instructions: 7,234,070 native + 222,574,137 interpreted; 288 sectors, 589,828 DATA IN ACKs including four TOC bytes, 262,144 ADPCM DMA bytes and 18,191 IRQ/RTI sequences; 22 scripted host events; Beginning/Continue → Beginning → blank volatile-BRAM warning → Proceed → opening story portraits and river/mountains/bird scene | Tick-budget stop at 3,000,000,009 ticks, about 139.7 guest seconds, no runtime fault; requires explicit `--cd-unknown-status gear-good`, used twice; no continuous rendering in this retained run, controllable gameplay, campaign, authentic reset or audio-output proof |
| Compiled local boot/BIOS module, ABI-12 continuous menu route | 30 million instructions, 1,062 completed historical frames; all compared CPU/CD/VDC fields exactly match the retained menu route | Recompiled same initial snapshot; reference-response opt-in still required; actual desktop menu observed separately; no full native/AOT or gameplay qualification |
| Compiled local boot/BIOS module, ABI-12 continuous story route | 8,356 completed frames; 229,808,207 instructions: 7,234,070 native + 222,574,137 interpreted; 288 sectors, 262,144 ADPCM DMA bytes, 18,191 IRQ/RTI sequences and all 22 scripted events; historical image shows river/mountains/bird scene | Tick-budget stop at 3,000,000,009 ticks, about 139.7 guest seconds, no runtime fault; same response-profile condition and execution totals as the retained story route; no controllable gameplay, campaign, authentic reset, audible output or full native/AOT qualification |
| Actual SDL window with TCP-controlled Ys III route, retained video batch | Menu → Beginning → warning → Down selects Proceed → I confirms → boat/mast and opening portrait scenes; 8,000 frames, 2,871,925,884 ticks / 133.7 guest seconds; 7,301,883 native + 213,086,766 interpreted instructions; 16,037 IRQ/RTI, 288 sectors, zero read errors, 262,144 ADPCM DMA bytes; clean requested quit | Eight requested guest/SDL captures, no per-frame dump; final hidden GPU-window replay matches three retained guest-image hashes and final state totals; response-profile opt-in used twice; no gameplay/campaign, authentic reset or audible output claim |
| Compiled local boot/BIOS module, retained ABI-12 TCP town-control route | 25,476 frames / 9,145,722,501 ticks; 761,925,353 instructions: 8,504,219 native + 753,421,134 interpreted; 867 sectors, zero read errors, 1,251,328 ADPCM DMA bytes, 79,118 IRQ/RTI sequences; directional movement/camera, I jump, Select menu, world map and town return observed | Clean TCP quit; exact hidden SDL replay matches five complete guest PNG hashes and all final CPU/device diagnostics; explicit unknown-response profile used four times; retained 785-site module, mostly interpreted; no combat/mine/campaign/audio/authentic-reset qualification in that run |
| Compiled local boot/BIOS module, retained ABI-12 TCP first-mine combat route | 31,819 frames / 11,422,827,780 ticks, about 531.9 guest seconds; 948,642,279 instructions: 8,504,219 native + 940,138,060 interpreted; 915 sectors, zero read errors, 1,316,864 ADPCM DMA bytes, 104,414 IRQ/RTI sequences; Tigre unlocked normally, unarmoured death/Run retry, starter gear bought and positively selected, visible sword; final HP 20 → 2, EXP 0 → 12, gold 100 → 108 | Clean TCP quit; exact hidden SDL replay matches seven complete guest PNG hashes and every final CPU/device diagnostic; explicit unknown-response profile used nine times; retained 785-site module, mostly interpreted; no guest CPU/device patch needed; exact kill count, deeper mine/boss/campaign, audio, authentic reset and full native/AOT unqualified |

The first-mine EXP observation above corrects the prior transcription of 124.
Exact glyph checks on the retained frame establish EXP `00012` and the separate
RING field `004`. This corrects the HUD reading; the equipment, attack,
received-damage and gold-reward observations are unchanged. The retained BRAM/debug build's
155-test qualification is separate from retained first-mine gameplay evidence.
New formatted-start SAVE/LOAD, STATUS, ordinary-input mine progression and
the assisted checkpoints are qualified only as listed above. The local
first-boss encounter and visible enemy damage are established under health
assistance. Final route accounting and successful SDL replay are recorded above. No boss
defeat, complete campaign or ordinary-gameplay qualification is claimed.

The public baseline has no ROM, BIOS, extracted game bytes, generated game
source, save files or initialized personal install. Private derived data is
under ignored `.local/`. Original CHD SHA256 was established before work and
is checked again at closeout; nothing writes the original image.

The local toolchain does not provide a `ctest` binary; verification uses
`python scripts/check.py`. The retained pre-desktop batch passed all 17 suites
and 112 Python tests, including a separate generic public-source build.
The retained BRAM/debug build passed all 20 enabled suites, including 155 Python
tests, adding generic initial-BRAM loading and larger explicit execution limits.
The retained observed-code/consumer build passed all 202 Python tests as recorded above.
The retained first-mine build passed 138 Python tests. GitHub CI
template uses CTest on Windows/Linux/macOS runners and separately builds the
pinned optional CHD backend. The initial CLI credential lacks GitHub's
`workflow` scope, so `.github/ci-template.yml` is initially inactive. No remote
CI pass is claimed. Enable it using the instructions in the developer guide.

## Deliberate limits

- Decoder metadata covers 256 encoding slots; runtime support is 234 opcodes.
- Load/store, logical, ADC/SBC and comparison encodings are supported, including
  indexed/indirect data addressing, T destinations and decimal arithmetic.
- Shifts/rotates, INC/DEC memory/accumulator and both indirect JMP forms are supported;
  indirect destinations remain unresolved in static discovery.
- RMB/SMB, push/pop, BIT/TSB/TRB/TST, BBR/BBS and BSR are supported.
- TAM/TMA cover all masks and the persistent transfer latch. I/O open bus is
  separate and retained by the IRQ/PSG profile. Current native ABI is 28; regenerate incompatible older modules.
- CSL/CSH use two cycles at entry speed and one at selected speed.
  Geargrafx's live transition timestamps differ; see CPU_SEMANTICS.md.
- Idle CD-control/BRAM routing and opt-in clocked selection/REQ/ACK transport
  are implemented; TEST UNIT READY and directory/TOC modes 0/1/2 complete
  through DATA IN where needed, then status and message phases. Manual and
  `$1808` auto-ACK are supported for bounded metadata responses.
  See CD_CONTROL.md for exact registers, reference delays and discrepancies.
  REQUEST SENSE and typed READ recovery are implemented; raw captured
  subchannels remain outside the supported profile. CDDA D8/D9/DA/DD has
  functional control/position responses and separately enabled digital PCM output. READ `$08` requires a separately
  attached read-only provider. Metadata-only attachment does not verify an image;
  `--disc` hashes/derives geometry and enforces exact descriptor agreement.
  The default fixed 1x profile omits seek distance; opt-in `gear-distance`
  covers calibrated READ/CDDA seeks. Reset jitter and accelerated speeds
  remain unmodeled. See [CD timing](CD_TIMING.md).
- Opt-in joypad I/O routes all `$1000..$13FF` mirrors, with two/six-button
  pads, a five-port TurboTap, region/CD bits and guest-write-sampled output.
  Headless flags provide held button snapshots and bounded tick-scripted input;
  the optional SDL3 host maps keyboard/gamepad input to slot zero. Other
  peripherals remain planned. See [INPUT.md](INPUT.md) and [DESKTOP.md](DESKTOP.md).
- Functional single-VDC ports/registers, buffered VRAM and ST0/ST1/ST2 are
  implemented; the extended profile adds VCE palette and VRAM/SATB DMA, while
  undriven reads retain the VRAM bus word. See [VDC.md](VDC.md) and [VRAM_BUS.md](VRAM_BUS.md).
- Opt-in raster timing generates VBlank and raster-comparison events from
  master-clock horizontal/vertical phases. VCE timing control selects dot
  divisors and 262/263-line frames. Optional images inspect current VRAM,
  SATB, palette and registers. Separately enabled continuous output records
  historical lines and live-dot palette values; it preserves the legacy
  non-rendering path. Queued CPU VRAM accesses model contention with display
  and DMA; physical fetch phases and narrow latch rewrites remain unqualified.
  Sprite collision/overflow IRQs use a separately qualified
  device-clock pipeline. See [VIDEO_OUTPUT.md](VIDEO_OUTPUT.md).
- TII/TDD/TIN/TIA/TAI have genuine stack effects, wrapped per-byte addressing,
  17+6*n base cycles and block-aware I/O. A started bounded block completes
  past the entry deadline; IRQ entry is deferred until the transfer completes.
  Fatal faults are nontransactional; there is no partial-transfer resume state.
- IRQ delivery, RTI and timer/interrupt registers are implemented using an
  explicit aggregate sampling profile. Finer device access phases, a complete
  interpreter, full System Card profile and general bus phases remain. Base WRAM
  mirrors are implemented.
- Unknown CD commands fault by default. Explicit `--cd-unknown-status gear-good`
  selects the source-documented reference-emulator GOOD-response quirk and
  counts each use. It does not implement unknown command operations or convert
  known unsupported commands to success. Retail menu evidence is conditional
  on that profile; strict mode remains an unresolved correctness boundary.
- Both runners accept `--bram RAW_2048_IMAGE`, a read-only exact 2,048-byte
  initial snapshot. The default remains blank and unformatted; seeds remain
  read-only. Explicit raw export and isolated consumer save sessions are
  implemented. Guest formatting and SAVE/LOAD require actual guest actions;
  no filesystem or firmware service is fabricated. See [PERSISTENCE.md](PERSISTENCE.md)
  and the finite queued SAVE/LOAD and cold-import scope above.
- The explicit dispatcher step allowance is at most 20,000,000,000. Tick
  deadlines and optional 1–600-second wall limits still apply.
- PSG retains functional register state and adds an opt-in centered digital
  oscillator/noise/LFO profile. ADPCM decodes consumed nibbles, and CDDA can
  supply raw stereo PCM. Bounded digital mixing, SDL playback and WAV capture
  are implemented. Optional source filters match the scoped Geargrafx
  equations, and an authored FIR supports 48 kHz output. Complete-game audible
  correctness, source-transition aliasing, final emulator mix/device-conversion parity
  and the physical analog circuit remain unqualified. See [AUDIO_OUTPUT.md](AUDIO_OUTPUT.md).
- Deadline accounting is at instruction boundaries, not cycle-accurate.
- Legacy CFG discovery retains one MPR context and stops at mapping changes.
  Opt-in static context discovery follows proven constant TAM mappings;
  unknown mappings and indirect/call-return flow remain explicit. Observed-code
  modules separately support actual retired contexts and source-byte variants.
  All paths preserve per-instruction guards and explicit fallback. See [STATIC_ANALYSIS.md](STATIC_ANALYSIS.md).
- Bounded retired-code capture and offline direct emission are implemented.
  No automatic in-process recompiler, persistent overlay cache or optimizing
  block IR is implemented.
- CHD, ISO and bounded BIN/CUE providers support their documented MODE1/AUDIO
  layouts. Boot extraction retains its documented loader subset; unsupported
  layouts stop explicitly. See [MEDIA.md](MEDIA.md).
- Explicit payload/IPL sandboxes and real-vector HuCard/System Card startup
  are separate recipes. Reset uses the documented deterministic seed and
  hardware profile, not a hardware power-on/reset-phase certification.
- The optional desktop displays completed frames with nearest pixels and
  guest-clock pacing, and supports resize/fullscreen/pause/focus/input. It has
  optional bounded SDL audio output; it has no settings persistence or owner-save access. Physical audio/gamepad
  and non-Windows host qualification remain.
- The optional `pce-dev-1` TCP interface controls only the running guest and its
  SDL composition. It binds loopback, is disabled by default, and bounds
  request/response storage, polling and idle peers. Captures are requested,
  not automatic. It does not capture the owner's desktop. Paused RAM edits
  require separate opt-in and whole-range expected bytes; edit counters
  distinguish assisted tests. See [DEV_SERVER.md](DEV_SERVER.md).
- Explicit CD BRAM persistence and raw export are implemented. Rewind,
  emulator machine states, netplay and an enhancement release remain outside
  this baseline. The full target remains in the roadmap.

## Next useful batch

Evaluate guarded multi-instruction blocks and persistent cache identity using
the measured partitioned-module baseline. Preserve exact
source/mapping invalidation, aggregate clock/IRQ behavior and explicit fallback.
Measure compile time, instruction/cycle work and controlled end-to-end performance
separately; hot firmware loops do not measure game completion.

The separate game consumer owns campaign progression, title configuration and
its chosen hot/cold native policy. Use its focused, hash-pinned defect reports
and additional authored diagnostic programs to expand the general toolkit.
Broader audio source timing beyond the qualified scheduler/DAC vectors,
final reference mix/device parity, exact device access phases and the unknown
CD command's operation remain separate correctness tasks. The response-profile
opt-in does not resolve hardware behavior. CDDA sample-latch ports
`$1805/$1806` and the guest-clock ADPCM/CDDA source scheduler are implemented
with their scoped independent checks; broader drive timing, physical bus
phases and final output-device parity remain open. Static context discovery
does not yet perform general indirect or interprocedural recovery.

### Retained dispatch-batch closeout

That batch's seven protected input hashes match. No owner installation, original media,
saves or settings were modified. The final Geargrafx process stopped and its
temporary configuration was removed. The toolkit's test hosts have stopped;
the independently owned consumer chat may continue its own tests. Desktop
control was not used during this batch.

Existing SDKs and immutable inputs were reused. The full-route check reuses
retained images, creating zero new retail PNG files.

Contributor issues reviewed on 23 October 2026: #1 (RMB/SMB) and #2 (stack) are
closed; #3 (media fixtures) and #4 (cycle-aware traces/second oracle) remain
open. This batch adds an authored Geargrafx compilation-path probe and does
not close the second-oracle or bus-phase work.

Read [ARCHITECTURE.md](ARCHITECTURE.md), [REFERENCE.md](REFERENCE.md),
[CONSUMER.md](CONSUMER.md) and [ROADMAP.md](ROADMAP.md) before continuing.
