# File snapshots and qualification evidence

Consumer projects can share exact file reads and evidence admission through
`pcerecomp.snapshots` and `pcerecomp.qualification`. These host-side Python
helpers operate on explicit files and JSON receipts. Guest checkpoint decoding,
CPU/device comparisons and native execution qualification remain consumer checks.

## Read and bind the same bytes

```python
from pathlib import Path
from pcerecomp.snapshots import SnapshotStore

store = SnapshotStore()
source = store.read_json(Path(".local/closed-run/receipt.json"))
receipt = source.value
assert source.reference()["sha256"] == source.sha256
store.bind_all(receipt["input_bindings"])
store.revalidate()
```

`read_json` hashes and parses one bounded UTF-8 byte buffer. It rejects a BOM,
duplicate decoded object keys, invalid encoding and non-finite numbers,
including overflow such as `1e9999`. Finite elapsed-time floats are allowed.
An expected SHA256 can be supplied as `expected_sha256=`. The default JSON
limit is 64 MiB; use an explicit `max_bytes=128 * 1024 * 1024` for an admitted
larger profile. No source label or producer ABI is changed.

`JsonSnapshot.raw` is immutable, and each `.value` access returns a detached
ordinary JSON tree. Editing that tree, a reference dictionary or a binding map
cannot change the admitted snapshot. Repeated JSON reads check current bytes
and refuse a conflicting digest. Binary `bind` streams content without loading
disc images or packages into memory.

`bind_all` admits an explicit absolute-path-to-lowercase-SHA256 table. It does
not follow arbitrary nested JSON, historical QA metadata or path-shaped strings.
Matching binary bindings reuse their admitted snapshot within the epoch;
`revalidate` reads their contents again. Same-size edits with restored timestamps
still fail. Supplied path spellings and alias targets remain tracked, including
case-only spellings on Windows. The checks describe content at the checks;
they do not lock files or provide ongoing freshness or producer authentication.

All complete binding tables, receipts and closures belong in private experiment
directories. They can contain personal paths, instruction data or references to
game assets. The helpers perform no upload, SDK loading or code execution.

## Declare receipt policy explicitly

`DocumentSpec(reference, schema, kind, claims=None)` specifies a contract or
other JSON document. `ReceiptSpec(reference, schema, kind, contract, producer,
claims=None)` specifies a positive consumer receipt. References contain exactly
`path` and `sha256`; the producer reference names a caller-chosen immutable file.
Its meaning and authorship need independent consumer evidence.

A positive receipt has this envelope, with real file references and digests:

```json
{
  "schema": 1,
  "kind": "consumer-check",
  "passed": true,
  "role": "checkpoint",
  "contract": {"path": "ABSOLUTE_CONTRACT_PATH", "sha256": "LOWERCASE_SHA256"},
  "producer": {"path": "ABSOLUTE_PRODUCER_PATH", "sha256": "LOWERCASE_SHA256"},
  "input_bindings": {},
  "scope": "own-checkpoint-consistency"
}
```

The capitalized values above are explanatory placeholders. The helper refuses
them as actual references. Consumers adapt existing receipt formats explicitly;
existing historical records stay unchanged. A `passed` field alone establishes
no native execution, compiler authorship, hardware behavior or campaign result.

Optional claim expectations pin additional fields using exact JSON types.
Boolean `true`, integer `1` and float `1.0` remain distinct. Schema, kind,
contract, producer and mandatory pass fields cannot be replaced through claims.
Game-specific semantic validators run in trusted consumer code before that
consumer issues a positive receipt; JSON never names an executable validator.

An admitted document can carry an optional top-level `input_bindings` table;
receipts require their own explicit table. Shared contract dependencies therefore
need not be repeated in every child receipt. Only that declared table is read;
nested payloads and other provenance fields remain opaque.

## Resolve carried and current roles consistently

An `AdmissionLedger` declares one exact role universe and two disjoint maps:
new receipt specifications and explicit `CarriedAdmission(receipt, review)`
bridges. Every role must appear exactly once. New roles retain the current
contract and producer. Carried roles retain their original receipt, contract
and producer; an independently supplied positive review must explicitly pin
the original role admission and its dependency bytes.

The review's `admissions[role]` contains `receipt`, `contract` and `producer`
references, and its `input_bindings` pins all three. No current-contract mismatch
silently falls back to historical data. Parent lookup and final sealing use
the same role resolver, preventing one caller from accepting a carried result
while another rejects or relabels it.

Metadata resolution checks the receipt/document snapshots it reads. Explicit
process and output boundaries revalidate the entire admitted graph. Overlapping
dependency tables reuse binary admission work instead of rehashing the old
graph for every role. Preserve a consumer's original ABI and source identity
when the metadata helper and execution producer come from separate checkouts.

For trusted caller-controlled work, `with graph.boundary():` performs the full
content checks before the body and after it, including when the body raises.
The context launches nothing; the caller chooses any subprocess command and
validates its semantic result. `graph.snapshot()` also revalidates every input.
`parent()` and `admit_receipt()` resolve local metadata without a full scan of
previously bound binaries. Their returned snapshots must not be mistaken for
a fresh check of every dependency.

For already closed, consumer-validated receipts in the envelope above:

```python
from pcerecomp.qualification import (
    AdmissionLedger, DocumentSpec, EvidenceGraph, ReceiptSpec,
)

contract_file = store.read_json(Path(".local/contract.json"))
producer = store.bind(Path(".local/producer.json")).reference()
run_file = store.read_json(Path(".local/closed-run/receipt.json"))
contract = DocumentSpec(contract_file.reference(), 1, "consumer-contract")
run = ReceiptSpec(
    run_file.reference(), 1, "consumer-check", contract, producer,
    claims={"scope": "own-checkpoint-consistency"},
)
graph = EvidenceGraph(store)
ledger = AdmissionLedger(
    graph, current_contract=contract, producer=producer,
    roles=("checkpoint",), new={"checkpoint": run}, carried={},
)
admitted = ledger.parent("checkpoint")
closure = ledger.seal(
    Path(".local/evidence.json"), schema=1,
    kind="consumer-evidence", scope="own-checkpoint-consistency",
)
```

Production callers pin expected digests at their trusted input boundary. The
example builds references from local snapshots to show the API; it does not
independently establish those files' provenance.

## Seal a private consistency record

`AdmissionLedger.seal` resolves the complete plan and emits a new, exclusive
JSON output after full content revalidation. It returns the emitted file's
snapshot. The closure contains `evidence_consistent: true` and
`qualification: false`; it intentionally has no generic `passed` field.
Consumers compose their actual native or gameplay qualification separately.

The output parent must already exist. Existing files, including input aliases,
are never replaced. Writing and postwrite checks can fail; a newly created
artifact is preserved and `ReceiptEmissionError` reports its path and whether
creation began. Such an artifact is not an admitted closure or a positive
receipt. Revalidate its declared inputs when consuming any older closure;
stored consistency is a point-in-time observation.

## Separate metadata and execution domains

A new metadata supervisor can use these helpers before and after an old-SDK
actor subprocess. Keep source paths and exact helper bytes pinned. Exclude
the supervisor's import environment from the actor and preserve the actor's
source-only SDK checks. Loading the current helper package does not migrate
an older native module or make its checkpoints compatible with a newer build.

The Ys III integration uses this split with frozen current helpers in the
supervisor and the retained C51 ABI 28 SDK in an isolated child. It restores
an existing own-build checkpoint, immediately re-saves the identical whole
file, advances six neutral frames and validates the new ACK, capture and saved
state. The run retires 164,369 native instructions with zero interpreted work;
its shared ledger still emits `qualification: false`. This is a checkpoint and
helper-integration check, with no original-emulator comparison or new campaign
qualification.

These interfaces do not export guest physical memory, reinterpret a CPACK
format, optimize the recoverable-build producer or independently qualify a
game. See [native discovery](NATIVE_DISCOVERY.md),
[raw audit relations](RAW_AUDIT_INTEGRATION.md) and
[build recovery](BUILD_RECOVERY.md) for those separate contracts.
