# Mixed-ABI observation profiles

An observation profile is a private catalogue of exact instruction identities
from one or more original capture files. Supported offline inputs retain their
original ABI 12 through 28 labels. The generated module targets current ABI 28.
Composition neither changes those historical labels nor converts checkpoints,
certifies an ABI migration, or establishes a newly executed run.

Profiles contain original game or firmware code bytes, including base64 copies
of the original files. Keep profiles, captures and generated modules private.
Public tests use authored instructions only.

## Compose and emit

```text
python -m pcerecomp compose-observations .local/capture/original.json .local/capture/new-run.json --out .local/profiles/combined.json
python -m pcerecomp emit-profile .local/profiles/combined.json --out .local/native/combined --partition-layout stable
```

Both destinations must be new. Composition admits all inputs and checks union
capacity before creating its output. Existing files, hard links and symlinks
are never overwritten. The source files remain unchanged. Emission accepts
the same exclusions, partitioning and opt-in native-span options as
[`emit-capture`](CODE_CAPTURE.md). A capture and a profile are different input
formats: each command refuses the other format.

Every union key includes logical PC, **all eight MPR bytes**, and every fetched
instruction byte. Physical addresses are checked against the decoder and MPR
mapping. Same-PC byte variants, otherwise-unused MPR differences, overlapping
instructions, page crossings and logical-address wrap remain distinct where
their complete keys differ. Exact duplicate raw inputs count once, even under
different filenames. Distinct files with identical decoded instructions remain
separate provenance inputs and contribute their own historical hits.

Input order does not affect the profile. Inputs sort by SHA256, identities by
MPR/PC/bytes, and contributions by input SHA256. There is no last-file-wins
policy or silent truncation. Version 1 composition accepts original captures;
version 2 below can explicitly extend an admitted retained profile.

## Add identities without duplicating overlapping contributions

```text
python -m pcerecomp compose-observations .local/capture/new-window.json --baseline-profile .local/profiles/retained.json --new-identities-only --dry-run
python -m pcerecomp compose-observations .local/capture/new-window.json --baseline-profile .local/profiles/retained.json --new-identities-only --out .local/profiles/extended.json
python -m pcerecomp emit-profile .local/profiles/extended.json --out .local/native/extended --partition-layout stable
```

This explicit selection produces `pce-observation-profile-2`, schema 2. It
retains every original raw capture byte and revalidates each input, including
its ABI, origin, physical mapping and loss/completeness metadata. It selects
contributions for compilation rather than rewriting captures or raising limits.
Original inputs remain execution claims from their respective producers; a
profile is still not evidence of a new execution.

The `selection_stages` ledger contains SHA-sorted input stages. Stage zero
retains all original baseline contributions. Each later stage contributes only
full instruction identities absent from previous stages; the lowest input SHA
in that stage wins when several new inputs contain the same new identity.
Extending a version 2 profile preserves all its prior stages and their winners.
Argument order within an extension cannot select a different winner. Exact
duplicate raw input SHAs add no stage; a distinct input containing no new keys
still consumes raw-byte/input capacity and is retained with no selected rows.

`historical_totals` continues to describe **all original input hits**, including
overlap. `selected_historical_totals` describes the retained contribution rows.
`selection_counts` separates original, selected and omitted contributions.
Omission is a declared catalogue policy, not execution deduplication. Original
per-input metadata stays separate. The loader independently reconstructs the
stage ledger's selected rows and totals from the hash-verified originals;
caller-supplied row lists, changed totals or incomplete ledgers refuse.

All version 1 bounds remain: 256 provenance inputs, 64 MiB distinct original
bytes, 65,536 union identities and 128 MiB serialized output. The 262,144
contribution bound applies to the selected rows in version 2. Every original
capture is validated even when its rows are omitted. Raw bytes and complete
original history still impose finite bounds; this is not unlimited history.

`--baseline-profile` requires `--new-identities-only` and is mutually exclusive
with `--baseline-input`. Repeated `--baseline-input` can instead establish a
raw baseline stage. Without `--capacity`, a retained profile's capacity is
inherited; a raw baseline uses 65,536. A smaller explicit capacity never prunes
retained keys. The Python entry points are
`compose_additive_observation_profile` and `plan_additive_observation_profile`,
with `baseline_profile=path` or `baseline_inputs=paths`.

Dry-run binds the exact retained profile bytes and producer source, reports
the selected and original contribution costs, and predicts exact output
bytes/hash without creating files or generating code. Real composition must
readmit inputs. Emission and bound consumer verification preserve the
selection ledger/policy/counts and distinguish original from selected totals.
Version 1 serialization and manifests retain their original contract. New
bound profiles require their own consumer build and exact-build checkpoints;
this feature does not migrate an existing checkpoint.

Planner `duplicate_shas` describes repeated explicit capture path arguments.
Raw SHAs already embedded in `--baseline-profile` are instead distinguished
through `existing_inputs` and `new_inputs`; the profile itself counts as one
operation path. An exact duplicate extension preserves canonical output bytes;
an independently reserialized profile has its own artifact SHA. Selection history
is declared provenance, not authenticated execution or proof that a particular
parent operation occurred; retain the exact baseline artifact and operation
receipt when that relationship matters.

## Preflight an extension before emission or build

```text
python -m pcerecomp compose-observations .local/capture/new-window.json --baseline-input .local/capture/retained-a.json --baseline-input .local/capture/retained-b.json --dry-run --out .local/profiles/combined.json
```

`--baseline-input` repeats for the retained original captures. `--dry-run`
reads and admits baseline plus additions without writing a profile, generating
code or starting a host. Exit 0 means the selected composition fits; exit 2
returns a code-free refusal report. If supplied, `--out` is also checked
against the existing destination policy, but is never created in dry-run mode.
Omit `--dry-run` to compose the same baseline and additions into that new path.

The Python API is
`plan_observation_profile(additions, baseline_inputs=retained, capacity=65536)`.
An empty additions list measures the baseline alone. Its report separates
existing/new/duplicate input SHAs, complete-key union growth, raw bytes,
contributions and their additive costs. Exact output byte size and SHA256
use the same sorted, indented UTF-8/LF serializer as real composition.
Successful reports include remaining capacity under every existing bound.

The planner stops at admission bounds; it does not relax them to count an
oversized union. Uncomputed refusal metrics remain null. Source hashes and
the serializer identifier bind the report's producer and output contract;
inputs must still be re-admitted when composition actually occurs. A plan
does not authenticate execution, prove equivalence, identify overlapping
sessions or change checkpoint identity. Input payloads and opcode rows are
excluded from the report. Profile-v1 bytes, raw provenance and limits are
unchanged. New observations with no new identities can add historical
contributions without requiring new translated code; callers should decide
whether that provenance update warrants a new bound consumer build.

## Version 1 contract

The `format` is `pce-observation-profile-1`, `schema` is 1, and
`execution_evidence` is always false. There is deliberately no top-level
capture ABI or checkpoint origin.

| Field | Meaning |
|---|---|
| `capacity` | Maximum unique identities in this union |
| `inputs` | SHA256-sorted `{sha256, size_bytes, raw_base64}` records holding exact original capture bytes |
| `observations` | Canonical capture identity fields, summed historical tier hits, and per-input `contributions` |
| `historical_totals` | Checked sums of original native/interpreted hits and retired counts |

Each contribution contains `input_sha256`, `native_hits` and
`interpreted_hits`. Reloading decodes canonical base64, rehashes exact bytes,
strictly validates every original capture, rebuilds the entire union, and
compares identities, contributions and totals. Original schema, ABI, capacity,
loss counters, completeness and optional checkpoint origin stay inside their
unchanged raw input. A reserialized capture has a different raw identity even
when its decoded observations are equal.

Admission requires complete, lossless captures. Unknown fields, unsupported
ABIs, duplicate JSON keys, noninteger numeric tokens, nonfinite values, invalid
physical mappings, mismatched raw hashes and fabricated contribution or total
fields refuse explicitly. All counts and checked additions fit unsigned
64-bit integers. Checkpoint-prefix counters remain input metadata and are not
added to historical suffix work.

| Bound | Version 1 limit |
|---|---|
| Input path arguments / distinct provenance inputs | 256 |
| Individual raw capture | 64 MiB |
| Total distinct original raw bytes | 64 MiB |
| Union identities | 1 through 65,536 capacity; an empty observed union is allowed |
| Per-input identity contributions | 262,144 total |
| Serialized profile file | 128 MiB |

`--capacity N` lowers the union bound; it never discards identities. Metadata
bounds apply even when many inputs share the same keys. Excess refuses before
output creation. The byte limits are format admission bounds, not a claim
about peak Python memory consumption.

## Emission and consumer projects

The emitter shares the established guarded translation core with
`emit-capture`: it generates direct C++ operations with full MPR, logical-PC,
source-byte and deadline guards. Unsupported operations still miss to the
configured dispatcher policy. Composition adds no interpreted runtime path,
guest patches or inferred control-flow edges.

The schema-1 module manifest records `observation_profile_sha256`, format and
schema, `observation_inputs` with code-free original input metadata, and
explicitly historical totals. Its `runtime_abi` describes generated code.
It does not manufacture `capture_runtime_abi`, a single capture checkpoint,
or current-ABI retirement evidence. Exclusion hit counts are historical input
sums as well. Retain the exact input profile alongside build evidence: its
hash binds all raw bytes and per-identity contributions. The module manifest
does not embed the full profile. Existing descriptors can keep retaining it
separately; the optional consumer binding below adds verification and managed
retention without changing the generated module.

An input SHA proves which bytes were supplied, not that the input's claimed
execution actually occurred. Historical sums can include overlapping sessions
or a preexisting catalogue; the composer cannot deduplicate execution events
across distinct files. A lossless input only describes its retained window,
not complete program coverage. Emission keeps `execution_evidence: false`.
Compilation, actual native/interpreted execution, game progression and audio
checks require separate receipts. New modules require their own cold execution
and exact-module checkpoint qualification.

## Bind the profile to a consumer build

Consumer TOML schema 1 accepts an optional profile table alongside the existing
`module.source` and `module.manifest` tables:

```toml
[module.observation_profile]
path = "private/combined.json"
sha256 = "<exact lowercase SHA256 of this profile file>"
```

Paths resolve relative to the descriptor. The profile may be outside the
generated module directory. `project verify`, `build` and `run` verify its raw
file hash and strict profile contract, then compare the module's profile hash,
original input metadata, historical totals and planned source-selection counts.
Exclusions are reconstructed from recorded physical ranges. Unsupported,
excluded and emitted counts must agree with the admitted catalogue. The check
does not regenerate C++ or independently prove its operations; generated source
hashes and separate compilation/execution checks retain that responsibility.

Build and execution receipts include `module_observation_profile` in their
file bindings. The profile is a build input, not an argument or asset delivered
to the guest. Changing or removing it invalidates an existing receipt. Binding
does not authenticate historical execution or make overlapping input windows
independent. A lossless union is still not complete program coverage.

The optional [managed rebuild producer](INCREMENTAL_BUILDS.md) copies the exact
profile into its owned module directory as `observation-profile.json`, rewrites
the owned descriptor to that path, and retains the raw bytes in immutable
generation history. It checks the candidate before modifying retained build
outputs. An unchanged profile keeps its bytes and modification time; changed
profile evidence participates in the module contract and package-cache
identity. Declared profile links and filename collisions refuse. The producer
does not edit the caller's profile, descriptor or module.

Existing unbound descriptors continue to work. **Opting in changes the exact
consumer checkpoint context**, even if generated C++ bytes are unchanged.
Create a fresh cold run and new checkpoints when adopting the binding. Runtime
Profile admission leaves checkpoint schema 1 unchanged, and no checkpoint importer or
identity override is introduced. Direct CMake embedding continues to verify
the generated module artifacts; it does not implement this optional Python
consumer profile admission by itself.

## Python API

```python
from pathlib import Path
from pcerecomp.observations import (
    compose_observation_profile, load_observation_profile,
    validate_observation_profile, observation_profile_provenance,
    load_observation_profile_details,
)
from pcerecomp.emitter import emit_observation_profile

profile = compose_observation_profile(
    [Path('.local/capture/original.json'), Path('.local/capture/new-run.json')],
    capacity=65536,
)
# Or load an already written profile and bind its exact original file bytes:
profile, digest = load_observation_profile(Path('.local/profiles/combined.json'))
manifest = emit_observation_profile(
    profile, Path('.local/native/combined'), digest, partition_layout='stable',
)
```

Validation returns canonical decoder-derived translation records. Provenance
inspection returns original per-input metadata without instruction bytes.
`load_observation_profile_details(path)` returns `(profile, raw_sha256,
decoded_instructions, input_provenance)` from one admission pass; consumer
verification uses it to avoid reconstructing large profiles repeatedly.
When an in-memory emitter call omits the digest, it hashes canonical compact
JSON; that digest is not the hash of an independently pretty-printed file.
Pass the loader's digest when binding a retained file. A caller-supplied digest
must identify the caller's actual artifact; the in-memory API cannot verify a
file it was not given.

## Verification scope

Staged profile-v2 implementation
`cd5bff67b323098979345f76d5b87075fc628e72` passes the complete required SDL
checker: **1,583 Python tests with no skips, 68 C++ suites and 12 fresh-process
audio checkpoint cases**. The source84 hash remains
`16679df8f6758cbac67e97dc2a3cb20d327ee80631e3cce25601dc0672b0734a`
before/after. Twenty-nine added public tests include independent literal
accounting, strict malformed/omitted-input refusal, stage-winner conservation,
unchanged bounds, exact planning/CLI bytes, consumer manifest admission and an
actually compiled/executed authored v2 consumer.

Independent checks retain 26 v1 artifacts across six configurations. A real
two-stage extension retains 58,035 existing identities and adds four, with
260,563 selected versus 264,174 original contributions. All original bytes,
ABI labels and origins remain; final serialization is 129,648,072 bytes within
the unchanged limit. Its 948 baseline code files reproduce exactly; only two
extended C++ partitions change, containing four added direct LDA cases.
Compilation and finite retail startup/checkpoint tests retain their separate
[current status](STATUS.md#staged-additive-observation-composition) scope;
the four later game identities and complete route are not execution-qualified
by those startup tests. ABI 28 and runtime/layout source remain unchanged.

The additive consumer-binding freeze
`40f44c843e29c72a39dc982ed59a2af2e7de5e6b` passes a fresh SDL Release build and
the required checker: **1,382 Python tests without skips, 65 C++ suites and
12 fresh-process audio checkpoint cases**. Twenty-two new tests cover profile
admission and actual normal/managed build behavior. Retained authored managed
runs promote 101 native/99 interpreted retirements to 200 native/zero
interpreted, rebuilding one object and preserving all 29 objects on a no-op.
Profile history, raw-file tampering, numeric types, selection counts and
bound-to-unbound downgrade refusals have separate authored checks. Fresh
emission also reproduces all 945 prior catalogue output files byte for byte.
No runtime/CMake/emitter, ABI or checkpoint schema change occurs.

The earlier composition/emission milestone below remains a separate epoch.
Frozen implementation `42910a2a9fdffb978d5eaafa713edc7dbd7ccc9f` passes the
fresh SDL Release build and required checker: 1,360 Python tests without skips,
65 C++ suites and 12 fresh-process audio checkpoint cases. Thirty-three new
authored tests cover the profile, CLI and emitter. A separately compiled
mixed-18/26 module executes all five supported identities as five native
instructions with zero interpretation; expected registers, 12 cycles, 36 ticks
and explicit mapping/source/deadline misses are checked. Its generated span
entry is compiled but not exercised by that test.

Frozen independent review rejects 25 altered profiles and confirms legacy
generated source preservation across six emission configurations. Private
consumer-input qualification preserves 57,545 older identities and adds 23,
with a 57,568-key union. That consumer check composes and emits only; its input
hit totals are historical and its new game module is not compiled or executed
by that check. See [current status](STATUS.md) for the exact proof boundaries.
