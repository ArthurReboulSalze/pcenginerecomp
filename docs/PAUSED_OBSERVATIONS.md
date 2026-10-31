# Durable development replies and paused observations

The development client can retain the evidence needed to investigate a failed
inspection. This is independent of guest code capture and developer machine
checkpoints. Runtime ABI 26 and checkpoint schema 1 are unchanged.

## Raw wire journal

### Archiving a closed journal

Create a new lossless gzip archive only after the writer is closed:

```text
python scripts/dev_journal_archive.py .local/wire.jsonl .local/wire.jsonl.gz --offline --sha256 ORIGINAL_JOURNAL_SHA256
python scripts/dev_journal_audit.py .local/wire.jsonl.gz --encoding gzip --sha256 ORIGINAL_JOURNAL_SHA256 --storage-sha256 ARCHIVE_SHA256
```

`archive_wire_journal(source, destination, expected_sha256=..., offline=True)`
from `scripts.dev_journal_archive` audits the source, writes deterministic gzip
to an owned temporary file, flushes/fsyncs it, checks the compressed journal,
rechecks the source and publishes exclusively. An existing destination is
refused. The source is retained. Publication uses an atomic exclusive hard
link; an unsupported filesystem fails rather than replacing another file.
A crash can leave an owned temporary file or a complete destination. File
fsync does not promise directory durability or survival of every power loss.

The explicit offline declaration is a caller obligation. Schema 1 has no close
marker, so a stable snapshot and paired replies cannot prove that a writer has
closed. Never archive a live active journal. The helper does not delete logs,
change their original receipts or relabel failed discovery evidence.
Hash checks establish exact byte identity and each read checks file stability;
they provide no filesystem lock or snapshot across separate reads. Replacing
a source with identical bytes between those reads is not excluded.

The streaming reader defaults to plain input; select `encoding="gzip"`
explicitly for archives. `expected_sha256`, `sha256` and `bytes` always refer
to the exact decompressed journal. `expected_storage_sha256`,
`storage_sha256` and `storage_bytes` refer to the stored container; these
coincide with the journal values for plain files. Raw request/reply bytes,
record sequences and IDs retain the same validation and provisional callback
contract. Memory remains bounded per record, without a total journal quota.

Exactly one complete gzip member is admitted. CRC errors, container truncation,
trailing bytes, padding and concatenated members are refused. An intact gzip
member may contain an incomplete journal only with explicit `allow_incomplete`
or `--allow-incomplete`; the receipt then retains its forensic-prefix status.
This option never excuses damage to the gzip container or repairs journal bytes.

### Consumer archive adoption

Keep the diagnostic-tool pin separate from the game runtime and verify the
actual imported helper closure as described in
[consumer write adoption](PAUSED_WRITES.md#adopting-the-relation-in-a-consumer).
The runtime/compiler source digest does not fingerprint these Python scripts.

Archive only after the client/journal writer has closed and the owned game
process has actually exited with its output streams closed. Retain that
closure evidence separately. A quit ACK, paired journal, boolean declaration
or absence of a process with an old PID does not by itself prove closure.
If the route failed, preserve its failed result; successful compression must
not turn it into successful gameplay or trigger an input/write replay.

Add archive metadata alongside the original journal binding: raw path/hash,
archive path, `encoding="gzip"`, decompressed size/hash and stored size/hash.
Do not substitute a compressed digest into an existing raw-file hash field,
rewrite old receipts, or remove the original log. Audit both forms and compare
their exact raw events, IDs and replies after each streaming audit completes.
A forensic prefix stays a forensic prefix in either form. Keep actual process,
source, checkpoint and client-admission evidence outside the archive claim.
If closure is supplied as JSON, require unambiguous typed data: reject duplicate
keys and nonfinite numbers before interpreting process/client closure fields.
A hash authenticates exact bytes, not an ambiguous parser interpretation.

### Reading a retained journal

Use the offline streaming reader for an existing private journal:

```text
python scripts/dev_journal_audit.py .local/inspection-wire.jsonl --sha256 EXPECTED_SHA256
```

The reader opens the file read-only, verifies record order and request/reply
IDs, canonical base64, protocol framing and JSON types, and checks the entire
file digest and file identity at EOF. It bounds each protocol record and the
retained summary; total journal size has no quota. Known command counters have
fixed names, with extension commands counted in one additional bin. It never
replays requests or contacts a host. Invalid UTF-8, duplicate fields and
nonfinite numbers, including exponent overflow such as `1e9999`, cannot become
valid protocol replies. The live client now also rejects exponent overflow.

The Python interface is `audit_wire_journal(path, expected_sha256=...)` from
`scripts.dev_journal_audit`. Its optional `visit` callback receives immutable
raw events. Those events remain provisional until the function returns after
all EOF, digest and stability checks; callers own callback storage and effects.
The reader profile covers `DevClient` protocol frames with at most 64 KiB of
normalized nonpayload metadata per record. An unusually large recorded error
message is refused when it exceeds that bound; not every possible client
failure row is admitted. Arbitrary custom payloads passed directly to
`WireJournal.record` are outside this profile.

A paired raw ledger does **not** establish successful client admission, a
cleanly closed connection, a successful game process or native execution.
Replies are recorded before validation, and schema 1 has no close marker.
Recorded failures are preserved as negative diagnostic evidence. Incomplete
request or record tails are refused by default; `--allow-incomplete` explicitly
reports a forensic prefix and its unresolved evidence. Complete malformed
records and any bytes after a terminal failure remain errors. Keep process,
route, build and checkpoint receipts alongside the raw journal.

### Recording requests and replies

Pass a new private file to the client:

```python
from pathlib import Path
from scripts.dev_client import DevClient
from scripts.dev_observation import validate_paused_observation

with DevClient(port, journal=Path(".local/inspection-wire.jsonl")) as client:
    before = client.call("status")
    data = client.read_memory(0x1F0000, 16)
    after = client.call("status")
    proof = validate_paused_observation(before, after)
```

The caller creates the parent directory. An existing file is refused before
contacting the host. The CLI also supports:

```text
python scripts/dev_client.py --port PORT --wire-journal .local/status-wire.jsonl status
```

Each JSONL record has schema 1, a connection-local sequence and an event. The
session records its loopback endpoint. Request/response records retain the
request ID and exact line bytes as `wire_base64`, including the newline.
Requests are written, flushed and fsynced **before sending**; complete replies
are retained **before UTF-8, JSON, protocol or higher-level validation**. A
subsequent comparison exception cannot erase the received reply. Malformed
UTF-8, duplicate JSON fields, bad IDs and invalid memory replies remain useful
raw evidence even though the client refuses them.

A writable journal preserves a timeout/disconnect failure record and any
bounded incomplete
receive buffer as `partial_base64`. It does not invent a complete response.
Journaling failures close the connection and never return a successful ACK.
An ordinary server rejection retains the connection, as before. Default
clients create no journal and keep their existing API behavior.

An intent is not delivery proof, and a raw reply is not semantic acceptance.
The server may already have acted if response journaling fails; there is no
automatic retry or rollback. Synchronous filesystem flush/fsync cannot be
preempted by a socket deadline. An overrun is refused after the OS returns,
before response admission. File fsync is the implemented operation, not a
promise about directory durability, physical storage or every power-loss case.
Per-record I/O is opt-in and its effect on long consumer runs is unmeasured.
Journals can contain memory, image and command bytes; keep them private rather
than committing them or using their presence as capture qualification.

## Strict reported-status comparison

For the separately declared effects of a successful paused RAM CAS, use
[typed paused writes](PAUSED_WRITES.md). The ordinary strict comparator below
continues to require equality; its generation checks have not been relaxed.

`validate_paused_observation(before, after)` requires successful status ACKs,
a network pause without a local pause, typed IDs/frame/ticks and plain finite
JSON values. It compares **every reported field in value and type**, removing
only the top-level transport ID. This includes SDL presentation counters,
source bytes/mapping/generations, guest clocks, device fields and synthesis
counters. Unknown fields remain compared. Missing fields do not establish
unreported state: complete status/source schema validation and verified
build/input bindings belong to the caller.

The helper is pure and does not contact a host, advance frames, edit memory or
authorize a write. Reported equality is not proof of all RAM or hidden PCM
queue contents. Full encoded checkpoint comparison supplies separate machine
continuation evidence. The route runner's existing presentation-subtree
projection remains a separate interface; this default is stricter.

## Explicit legacy fresh-muted profile

An older host can drain already generated PCM after answering a TCP request,
even while paused. The reviewed
[ABI 18 host](https://github.com/rages4calm/pcenginerecomp/blob/6935e46ff8aefacf8ea058a385198299c4e2cd5c/runtime/src/headless.cpp)
polls before an unconditional audio drain. The
[current host](https://github.com/rages4calm/pcenginerecomp/blob/09ae2fae6fab90deacd3c19ea5876deb8abe6bfd/runtime/src/headless.cpp)
pump drains only when unpaused; shutdown finalization drains remaining audio
separately. The older pump behavior is not a new current-runtime defect.
No legacy profile is inferred automatically from an ABI field.

`profile=LEGACY_FRESH_MUTED_GEAR` explicitly declares
`abi18-fresh-muted-gear-v1`. The caller must bind that source/build/startup
recipe independently; choosing a string is not authentication. This profile
accepts only the exact legacy raw 44.1 kHz Gear-timing, enabled/open/muted audio
schema, with no checkpoint/import marker or discarded PCM. It refuses newer
filter/resampler fields rather than inventing an allowance for them.

Let `G` be cumulative generated frames, `S` submitted frames, `D` dropped
frames, and `P = G - S`. At each endpoint:

- `D == S`, `0 <= P <= 8192`, and SDL queue/peak are zero;
- the stream has been paused and cleared, and those counters stay exact;
- `G`, source/device state, synthesis hashes and all other fields stay exact;
- `delta(S) == delta(D)` is either zero or **the entire initial `P`**.

The main-thread drain processes its entire pending queue without yielding to
another TCP request. Intermediate, negative, asymmetric and excessive drains
are refused. This permits a change in pending delivery; it does **not** certify
hidden queue contents or complete paused-machine quiescence.

`wav_limit=None` declares no WAV output and requires zero/false output markers.
An explicitly verified fresh WAV frame bound requires
`wav_frames == min(S, bound)` and `wav_truncated == (S > bound)` at both
endpoints. Only those validated host-output markers may change with delivery.
They are distinct from newly synthesized guest PCM. Checkpoint imports are
refused: cumulative guest frames and fresh host submission counters require
different accounting. Keep strict HP/CAS/write-authorization checks separate.

## Evidence and consumer diagnosis

Frozen implementation `e08425ca6c607289a18ee6055999e22d4a7461d5` passes the
fresh full SDL check: **1,261 Python tests without skips, 64 C++ suites and 12
fresh-process audio checkpoint cases**. The legacy helper's exact source SHA
is `651c1ce75b1c9cc2252b877092d1ae0b359f5e3e94749a7b0d8a2a98b54f1f10`.

Fifteen authored wire tests cover durability ordering, exclusive files, short
writes, request/response fsync failures, deadlines, malformed/partial replies,
helper exceptions and reusable server rejections. Twenty observation vectors
cover strict equality, zero/full drains, exact WAV boundaries and refusal of
partial drains, restored counters, changed types/source/PCM and unknown fields.

A separate authored SDL fixture generates pending PCM, inspects RAM/source and
a blue guest image, deliberately fails a higher-level comparison after the
reply is retained, then saves and restores. Complete round-trip and continued
checkpoint files/core bytes match, and strict paused host telemetry remains
unchanged. Fresh host submission counters are validated separately from
imported synthesis counters. This fixture uses no retail input.

A separate read-only game-host check uses the new frozen client against the
retained d102 ABI 26 consumer: **89 wire records, 44 request/reply pairs**,
one strict paused pair and zero new ticks/instructions. Full WRAM, source
fetch bytes and screenshot pixels match the loaded endpoint. Initial SDL
pause/clear setup is retained as a separate bootstrap observation; it is not
silently excused inside the measured pair. Shutdown delivery is also outside
that pair. This validates the new client against an older host, not a rebuilt
consumer or a fresh complete machine reserialization. An earlier private
recorder closure bug remains a separate failed attempt with its wire evidence;
the corrected passing attempt does not overwrite it.

A private legacy consumer initially lost its AFTER object when its observer
threw before saving it. The durable BEFORE reported nine pending frames;
there is no retrospective exact delta for that failed run. A subsequent,
separate run retained 69 raw pairs: the shared legacy profile accepts all 69,
with one **observed 12-frame drain** and 68 zero drains. That supports the
declared reported-counter relation, not capture eligibility, hidden queue
contents or campaign qualification. Its separate post-exit receipt-reader
size failure belongs to consumer tooling and does not establish an SDK bug.

See [development server](DEV_SERVER.md), [state-aware routes](STATE_ROUTES.md)
and [developer checkpoints](DEVELOPER_CHECKPOINTS.md) for their separate
contracts and the latest executed source pin/counts in [STATUS.md](STATUS.md).
