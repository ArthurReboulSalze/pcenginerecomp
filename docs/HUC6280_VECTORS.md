# SingleStepTests HuC6280 vectors (test-only adapter)

A test-only adapter plays the published [SingleStepTests/huc6280](https://github.com/SingleStepTests/huc6280)
single-step vectors through the interpreter and through actual emitted, compiled native code. It changes no
runtime, CPU, emitter or ABI file and uses no game data. It is the first slice of issue #4; bus-event
instrumentation is a separate proposal.

## Corpus identity, licence and provenance

| Field | Value |
|---|---|
| Repository | https://github.com/SingleStepTests/huc6280 |
| Pinned commit | `4ce378e04e243437e6f74dfe76c3cb7c70e45bf1` (2025-07-06, single data commit) |
| Files | 256 `v1/XX.json.bin`, 2,500 vectors each (640,000), 185,548,937 bytes |
| Manifest | [tests/huc6280_vectors.sha256](../tests/huc6280_vectors.sha256): SHA-256 and size of every file; digest of the 256 digests `975fdd41fe27a62e6f145bc7d393d4ce4f1e31ea43fd64cbfda44ec789b6c7e0` |
| Licence | MIT, Copyright (c) 2025 SingleStepTests ([licenses/SingleStepTests-huc6280.txt](../licenses/SingleStepTests-huc6280.txt)) |
| Generator | Mesen (GPL-3.0). The corpus does not record the Mesen revision. |

These are expectations from another emulator, not hardware measurements; the corpus README itself says they are
only as good as Mesen and that its dummy accesses are not fully certain. The files hold numbers only (states,
sparse RAM cells, bus cycles). No Mesen code, table or binary is vendored, linked or executed. The corpus is
fetched on demand into an ignored folder and never copied into a tracked file.

Limits from the corpus README, kept visible in every report: flat 2 MiB RAM with only MPR translation (no I/O
page, no device side effects), lists capped at 500 RAM pairs and 500 cycles (block transfers are cut), opcode
fetch counted as cycle one.

## Reproduce

```sh
python scripts/huc6280_vector_reference.py fetch .local/huc6280-vectors
python scripts/huc6280_vector_reference.py verify .local/huc6280-vectors
python scripts/huc6280_vector_reference.py run .local/huc6280-vectors --build build --compiler clang++ --out .local/huc6280-report.json
```

`fetch` runs `git fetch --depth 1` of the pinned commit into a new directory, checks the commit and every file
against the manifest and stops on any difference. `run` verifies the corpus again before reading any vector,
refuses an existing report path, and needs the CMake-built `pce-huc6280-vector-probe` and the `pce-runtime`
library of `--build`. `--compiler` takes a GCC- or Clang-style command (MSVC `cl` is not supported); without it
the native tier is reported as not run. Commands are argv only, with
bounded output and a timeout. `--ops` selects the same opcode subset for both tiers.

Each run retains a new `REPORT.artifacts/` directory containing raw process output,
commands, generated modules, original/remapped selections and native case files and
executables. Input SHA-256 bindings cover the corpus, adapter/toolkit sources, probe,
runtime library, optional CMake cache and selected compiler. Content is revalidated
across execution/publication boundaries. Missing/duplicate/wrong-tier rows, invalid
counts and incomplete execution refuse publication; failed-run diagnostics stay in
the artifacts directory. A separate `REPORT.closed.json` binds the completed report.

These private diagnostics use `qualification: false`. Hashing a supplied executable
and library does not authenticate their compilation from the recorded current source;
`build_source_correspondence` explicitly remains `not_authenticated_by_adapter`.
A qualification runner must separately establish that build relationship. Compiler
subtools and dynamically loaded dependencies are not authenticated by this adapter.
The bundle is not a portable or independently authenticated execution receipt.

## What is compared, and what is not

Every vector runs on a flat bus (all banks RAM, functional VDC profile enabled so ST0/ST1/ST2 execute), entry
speed divisor 3, IRQs off, transfer latch 0. Two results are reported separately:

* **Architectural state**: A, X, Y, S, P, PC, all eight MPRs and every sparse physical cell of the final list,
  with the differing classes counted apart (registers, flags, PC, MPRs, memory).
* **Cycle total**: the toolkit's CPU cycle count against the vector's `num_cycles`.

Not observed, hence never inferred and listed in the report as `not_observed`: bus-event order, dummy accesses
and master ticks. The toolkit's trace formats are instruction-boundary only; master ticks are the documented
function of the entry divisor and are not checked by this corpus.

A vector cut by the generator cap has no comparable final state (`state_not_comparable`); its cycle total is
still compared. A refused opcode is counted as refused, never skipped. The first differing vector per opcode and
tier is kept with both states.

### Native tier

For each native opcode (`isa.NATIVE`), the first N vectors in file order (default 40) that are complete, have
eight pairwise-distinct MPR values, leave the MPRs unchanged and are not TAM/TMA are moved into one canonical MPR
frame (pages `$20..$27`); each cell stays in its logical window. Their instruction bytes become guarded entries of
snapshots that `analysis.analyze` and `emitter.emit` turn into real modules, grouped so that no two sites overlap
or flow into each other. The probe is compiled with each module and runs every case through `generated_step` and
through the interpreter. Exclusions are counted by reason in the report. A guard miss is reported as a fault.

## Result at `81b5c231e452c6879d58585c8863012e438f1d55`

Interpreter, 640,000 vectors: 585,000 executed, 55,000 refused (the 22 reserved opcodes
`0B 1B 2B 33 3B 4B 5B 5C 63 6B 7B 8B 9B AB BB CB DB DC E2 EB FB FC`, which the corpus gives as 2-cycle NOPs).
Of 572,519 executed vectors with a comparable state, 563,514 agree on state and cycle total. The differences:

| Opcodes | Vectors | Class | Note |
|---|---:|---|---|
| `04 0C 14 1C` TSB/TRB | 1,492 | flags (Z only) | the corpus sets Z from `(A AND M) == 0`; the toolkit from the stored result, as [CPU_SEMANTICS.md](CPU_SEMANTICS.md) states (MAME agrees with the toolkit). An emulator disagreement, not settled by this corpus |
| `03 13 23` ST0/ST1/ST2 | 7,500 | cycles (5 against 4) | state agrees; the functional VDC profile adds a fixed wait |
| `43` TMA with mask 0 | 13 | registers | the corpus does not carry the transfer latch |
| `73 C3 D3 E3 F3` block transfers | 12,481 | not comparable | cut by the generator cap; all 12,500 cycle totals (17 + 6n) agree |

Native tier (40 per opcode): 9,091 cases on 231 of the 234 native opcodes (TAM/TMA by rule, TII has no complete
vector; 6 selected vectors whose bytes cannot form a guarded site are counted as excluded), five modules, zero guard misses and **zero differences with the interpreter**; against the corpus the
same two differences (26 TSB/TRB, 120 ST0-2).

## Tests without the corpus

[tests/test_huc6280_vector_reference.py](../tests/test_huc6280_vector_reference.py) uses only authored vectors:
manifest identity, fail-closed verification (tamper, missing, extra), decoder bounds, cap detection, the
deterministic selection rule, window-preserving remap and module grouping. With the probe (`scripts/check.py`
sets `PCE_TEST_HUC6280_PROBE`) it also checks that a wrong register, a wrong flag and a wrong cycle total are each
reported in their own class, that a cut vector is neither a pass nor a failure, that a reserved opcode is listed
as refused, and that malformed or mismatched files stop the run. `pce-huc6280-vector-probe selftest` (a CTest
case) checks the same comparison on in-memory authored vectors.

## Maintainer hardening

Authored regression tests also reject empty/partial/duplicate result streams,
non-integer or inconsistent counters, malformed opcode selections, trailing binary
bytes and corpus mutation during execution. A three-module regression preserves the
first actual difference after earlier matching modules. Closed-report tests bind raw
output and actual supplied input hashes without treating mocked processes as runtime
qualification. Original mappings remain linked to canonical native selections.
