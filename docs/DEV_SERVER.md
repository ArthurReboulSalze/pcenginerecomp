# Development control over TCP

Both runners have an optional development server for controller input, bounded
frame advancement, status, screenshots and paused physical-memory inspection.
An explicit [same-build interpreter reference capability](REFERENCE_MODE.md)
adds bounded `reference_frames` windows from a fresh paused run or own checkpoint.
RAM editing additionally requires `--dev-memory-write on`. The server is disabled unless `--dev-port`
is present. This uses the runner's own video and SDL targets; it never captures
the owner's desktop or accesses other applications.

The client now supports an opt-in [raw wire journal and strict paused-status
comparison](PAUSED_OBSERVATIONS.md). Replies are flushed/fsynced before parsing
or caller validation; an inspection failure need not lose its AFTER evidence.
The explicit legacy audio-drain profile is separate from the default exact
comparison and does not change guest execution or checkpoint compatibility.
The [offline journal reader](PAUSED_OBSERVATIONS.md#reading-a-retained-journal)
checks retained raw records without contacting a host or replaying requests.
Both live and offline JSON parsing reject exponent overflow as well as NaN
and infinity. A paired raw ledger alone is not a successful session receipt.

Append these options to an otherwise valid runner invocation:

```text
--video-output continuous --dev-port 0 --dev-start-paused on --wall-seconds 120
```

Port zero selects an available port. The runner prints `PCE_DEV_PORT=N` to
standard error after initialization. A fixed port from 1 through 65535 can also
be requested. `--dev-start-paused` defaults to `off`; `--wall-seconds`, if set,
stops the process after 1 through 86,400 host seconds even when paused. Omitting
the flag keeps the raw host's wall timer disabled; explicit zero is refused.
Consumer descriptors require an explicit finite limit; see
[finite host sessions](SESSION_LIMITS.md). The normal
guest instruction and master-tick limits still apply. Continuous output is
required when the server is enabled, so a screenshot always refers to a
completed historical frame rather than a newly synthesized snapshot.

Clocked hosts also report a pure `host.vdc_access` object in status, with
`profile`, `pending_read`, `pending_write`, `delay`, `phase` and cumulative
`wait_ticks`. Status and captures cannot advance pending VRAM work. See
[VDC_ACCESS.md](VDC_ACCESS.md) for timing and profile selection.

The standard-library Python client supports both runners:

```sh
python scripts/dev_client.py --port 4370 status
python scripts/dev_client.py --port 4370 screenshot new-frame.png --source guest
python scripts/dev_client.py --port 4370 screenshot new-window.png --source present
python scripts/dev_client.py --port 4370 frames 2
python scripts/dev_client.py --port 4370 input 0x8 --slot 0 --frames 2 --resume
```

PNG and PPM capture paths are selected by the local Python caller, created
exclusively, and never overwritten. The server receives no file paths. Screenshots
are emitted only when requested. `present` requires the SDL desktop runner;
`guest` works in either runner after the first complete frame.

For finite state predicates and guarded input sequences, use the
[state-aware route runner](STATE_ROUTES.md). It preflights the whole plan,
requires an already settled network pause, preserves raw before/after status
and memory observations, and releases only its acquired controller port.
Accepted host masks and guest-write controller sampling remain separate.

For a manually authored sequence, retain one connection:

```python
from scripts.dev_client import DevClient, write_capture

with DevClient(4370) as client:
    client.call("pause")
    client.call("set_input", port=0, mask=0x8)  # Run, using normal joypad semantics
    client.advance(2)
    client.call("clear_input")
    metadata, rgb = client.capture("guest")
    write_capture("new-frame.png", metadata, rgb)
    client.call("resume")
```

Input is a held 12-bit host mask for each of five controller slots. It is ORed
with the configured script/desktop input and reaches the existing joypad
snapshot; it does not force a guest controller latch or alter input hardware
semantics. The relevant six-button/multitap profile must still be enabled if
needed. Disconnect clears all network-held masks, so a one-shot `set_input`
followed by closing the socket is not an input pulse. The CLI `input` command
holds its connection for a selected number of frames or seconds, then clears
the masks. A seconds-based hold preserves the current run/pause state.

## Wire contract: `pce-dev-1`

IPv4 TCP, `127.0.0.1` only. Each request is one flat ASCII JSON object followed
by LF; CRLF is accepted. Responses use the same connection and one JSON object
per line. Request fields use ASCII strings or unsigned decimal integers;
JSON string escapes for ASCII are accepted. Duplicate or unknown fields,
objects/arrays/booleans/null, negative/floating-point/exponent numbers, invalid
escapes, non-ASCII text, leading-zero integers, and trailing text are rejected.

```json
{"id":1,"cmd":"ping"}
{"id":1,"ok":true,"protocol":"pce-dev-1"}
```

`id` is required and ranges from 0 through 9,007,199,254,740,991, the largest
integer exactly representable in JavaScript. Successful and rejected valid
requests echo it. Malformed requests whose ID cannot safely be established
return `"id":null`. Errors have `"ok":false,"error":"reason"`; they do not
silently fall back to another operation.

| Command | Additional request fields | Result or effect |
| --- | --- | --- |
| `ping` | None | Protocol identifier; also refreshes the idle lease |
| `status` | None | `frame`, current CPU `ticks`, aggregate `paused`, `local_paused`, and a trusted `host` status object |
| `set_input` | Required `mask` 0..4095; optional `port` 0..4, default 0 | Holds that slot's network mask |
| `clear_input` | Optional `port` 0..4 | Clears one slot, or all slots when omitted |
| `pause` | None | Pauses simulation at the next host polling safe point; cancels pending frame advancement |
| `resume` | None | Releases the network pause and cancels pending advancement |
| `step_frames` | Required `frames` 1..600 | Sets `target_frame`, runs toward it, then leaves the network pause engaged |
| `reference_frames` | Required `frames` 1..600 | Opt-in interpreter-only segment; initially selects before first dispatch/capture, then allows bounded continuation under the same policy |
| `screenshot` | Optional `source`: `guest` (default) or `present` | Inline RGB24 capture |
| `present_shot` | None | Alias for a `present` screenshot |
| `read_memory` | Required physical `address` 0..2097151 and `length` 1..256 | Paused RAM/ROM bytes as lowercase hex, with echoed `address` and `length` |
| `write_memory` | Required physical `address`, `data` and `expected` hex strings | Paused compare-and-write of 1..256 RAM bytes; echoes `address` and `length`; requires launch opt-in |
| `save_checkpoint` | Required portable `name` ending in `.pcec` | Paused exclusive save inside the startup-selected private directory; requires checkpoint opt-in |
| `load_checkpoint` | Required portable `name` ending in `.pcec` | Transactional exact-build restore into a fresh paused window; leaves it paused |
| `capture_summary` | None | Paused code-free capture window, exact execution counts, capacity and completeness/loss |
| `capture_sources` | Required `offset` 0..65536, `limit` 1..256 and `retired` 0..9007199254740991 | Paused page of retained source addresses, bound to the summary's retirement token |
| `quit` | None | Requests an orderly runner exit and clears network input |

Input acknowledgements accept the network mask and immediately update the
host's held pad snapshot, without sampling the guest output latch. Several
requests can be handled within one poll;
`status.host.buttons` computes the current combined host masks directly, so
an immediate status after `set_input` or `clear_input` reports the new masks
even in the same poll. Reporting does not mutate guest state or advance time.
The guest's sampled joypad latch still changes only through guest port writes.
These are three distinct phases: accepted effective host intent in
`status.host.buttons`, application to the runtime's held pad snapshot, and
guest-write sampling into the joypad output latch. A
successful input acknowledgement proves acceptance of the request, not a new
guest controller sample. The immediate combined-mask reporting is the current
host contract; older consumer binaries may report the previously applied mask
at an immediate same-tick paused observation. Preserve those raw records and
their binary/source epoch rather than treating them as current-host behavior.
For replay qualification, retain the raw observations and requested mask, then
also check input at the next guest advance. Historical captures can retain the
older same-tick reporting phase. Any comparison allowance for those records
must be explicit and bounded; it must not remove button comparisons from
subsequent guest execution.

Checkpoint commands additionally require `--checkpoint-dir EXISTING_DIRECTORY`
and a reviewed `--checkpoint-context SHA256` at startup. Socket requests accept
only basenames. Responses return `checkpoint` metadata with file/payload SHA256,
absolute ticks/frame/native/interpreted counts, `source_wav_frames` and
`pending_pcm_frames`. Loading binds the actual binary/DLL/media/profile and
reviewed source/module context, and refuses an already-executed window or BRAM
export. Saving and inspection do not drain paused PCM. Resumed status adds
`host.checkpoint` with imported `origin`, newly executed `window` and
`audio_origin`; live/file captures retain optional `checkpoint_origin`.
See [DEVELOPER_CHECKPOINTS.md](DEVELOPER_CHECKPOINTS.md) for complete identity,
state, private-file and evidence rules.

Frame advancement is asynchronous. The immediate response contains
`target_frame`; poll `status` until `frame >= target_frame` and `paused` is true.
Simulation stops at instruction/host polling boundaries, so this is not a
sub-instruction debugger and a single long instruction can span the target.
Desktop local pause is independent; frame-step requests are rejected until it
is released. Network `resume` never overrides the owner's local pause.
Disconnect retains the pause/step state, allowing a new client to
inspect and resume a deliberately paused runner.

## Paused memory debugging

Memory commands require a settled pause, with no frame advancement pending.
Addresses are **physical**, without an MPR translation. Use
`(mpr[logical >> 13] << 13) | (logical & 0x1fff)` for a logical address.
This describes the current mapping. A later function can remap banks before
executing: a published logical address cannot be resolved using an unrelated
paused context. Verify the intended physical source identity and expected
bytes before an edit.
Reads accept only RAM/ROM banks, without invoking bus reads, advancing time,
acknowledging interrupts or consuming device data. BRAM, MMIO and unmapped
ranges are rejected, including ranges that cross into those banks.

Writes are disabled by default. Start either host with
`--dev-memory-write on` alongside `--dev-port` to enable them. `off` is also
accepted; using either value without a development server is rejected. Writes
accept only existing RAM banks. ROM, BRAM, MMIO, CPU registers and device
state cannot be edited through this command. There is no file writeback.

`data` and `expected` must contain equal nonempty sequences of contiguous
hex pairs, at most 256 bytes each. Uppercase input is accepted; prefixes,
spaces and odd-length strings are rejected. The host checks the **whole**
range and every expected byte before changing anything. A stale expected
value or invalid bank rejects the entire operation. Changed bytes advance
their physical bank's source generation, including corresponding alias banks
for the configured WRAM or Populous mirrors, preserving dispatch invalidation.
An unchanged-byte write leaves generations unchanged.

The Python client provides `read_memory(address, length)` returning bytes and
`write_memory(address, data, expected)` accepting byte strings. The CLI has
`read-memory ADDRESS LENGTH` and
`write-memory ADDRESS HEX --expected HEX`; addresses accept `0x` notation.
Requests use integer addresses on the wire. These commands do not implicitly
pause, resume or advance the guest. A capture still represents the last
completed frame; editing RAM does not regenerate historical video.

`host.debug_memory` reports `write_enabled`, successful `write_requests`
(including unchanged-byte writes), and `bytes_changed`. Final runner JSON
records the corresponding `memory_write_enabled`, `memory_write_requests`
and `memory_bytes_changed` fields under `development`. Rejected edits change
neither counters nor guest state. A test harness should retain each edit's
frame, address, expected bytes, replacement bytes and readback. Report
cheat-assisted progression separately from ordinary gameplay and preserve
unmodified checkpoints. Title-specific cheats belong in private test or
consumer configuration, rather than the shared runtime.

A frame pause is a host safe point; the guest can be partway through a
subroutine. Game code can retain working copies of RAM values in other RAM
or CPU registers and overwrite an edit when execution resumes. A title-specific
editor must establish those invariants and any required room/event setup;
the generic server does not infer them.

The pure [typed paused-write validator](PAUSED_WRITES.md) checks retained
request/ACK objects, full backing readbacks and exactly declared counter and
alias-generation effects. It permits a disjoint data write while code executes
from the same bank, while keeping fetched bytes and other reported state strict.
Its supplied code footprint and topology require independent consumer bindings;
it neither authorizes an edit nor relaxes the ordinary paused-status comparator.

## Paused code-capture inspection

For replay across execution tiers, use the separate
[semantic frame-step relation](SEMANTIC_STEPS.md) to validate pending status
polls and the exact observed paused endpoint. `advance` can complete beyond a
requested frame when a whole instruction spans the target; intermediate poll
count and snapshots are not deterministic replay checkpoints. Full guest-state
and source/tier comparisons remain separate from that cadence proof.

With `--code-capture NEW_FILE`, the host keeps a bounded set of retired source
identities until orderly exit. `capture_summary` and `capture_sources` inspect
that stored set while settled at a pause. They do not read the guest bus,
advance clocks, alter code generations or debug-write counters, acknowledge
devices, finalize the capture or flush its output file. No new start/stop or
clear command is introduced. Without capture, the summary explicitly reports
`enabled: false`; source pages are unavailable.

Both replies contain a `capture` object with schema 1 and the actual runtime
ABI. An enabled summary reports capacity, `identity_count`,
`retired_instructions`, actual `native_instructions`/`interpreted_instructions`,
retained counts for each tier, `dropped_instructions`,
`unreadable_instructions`, `complete` and `window`. Actual counts include lost
observations: retained hits plus dropped and unreadable retirements must equal
the total. Completeness means both loss counters are zero.

The window reports the requested start frame, whether capture has started,
current frame/ticks and lifetime execution counts. Once started, it also
reports actual start frame/ticks and lifetime counter baselines. Subtracting
those baselines gives the exact captured execution counts. A deferred capture
that has not started is explicit; an empty, loss-free set alone does not prove
that a desired interval was observed.

Pass the summary's `retired_instructions` as `retired` on every source-page
request. Any intervening retirement makes that token stale and the request
fails. Pages use append order, return at most 256 rows and echo `offset`,
`limit`, `next_offset` and `done`; offset equal to the identity count is a valid
empty terminal page. Each row has capture-local `source_id`, logical `pc`,
all eight `mpr` values, 1..7 physical source-byte addresses, and native and
interpreted hit counts. Instruction bytes are omitted. Internally, different
byte variants remain separate identities even if their visible PC/MPR/address
spans match. A source ID is a local append index, not a cross-run content hash.

Final capture files use canonical source ordering and include instruction
bytes; live source IDs do not establish a mapping to those final byte
variants. Multiple variants can share the same visible PC, full MPR and
physical addresses. Preserve their multiplicity when checking live metadata
and hits, using a multiset/Counter instead of a dictionary that overwrites
matching visible keys. Compare finalized native/interpreter captures using
the full identity including instruction bytes and combined per-key hits.
Keep cardinality, local-ID continuity and loss/window checks separate; a
code-free live view cannot certify an ID-to-byte-variant association.

This is accumulated **retired instruction source-span history**, not a chronological
trace, speculative/failed fetch log or record of data accesses. Safe peeks
sample the encoded source span before retirement; this is not a bus-read log.
For example, BRK's two-byte span includes its skipped signature byte. It observes only the
stated capture window. Capacity loss or unreadable source makes absence
inconclusive. To establish that an address range was absent, require a started,
complete window covering the relevant interval and collect every page at the
same token. Physical source mappings are preserved: callers must expand backing
aliases such as `$F8..$FB` work-RAM mirrors when checking a proposed edit.
These facts do not by themselves establish that an edit is safe for game logic.

The standard Python client validates window accounting, per-byte PC/MPR
translation, pagination and tier totals:

```python
summary = client.capture_summary()
page = client.capture_sources(0, 256, summary["retired_instructions"])
history = client.capture_history()  # At most 256 pages, with explicit loss data.
```

CLI commands `capture-summary`, `capture-sources OFFSET LIMIT --retired TOKEN`
and `capture-history` print JSON. They do not implicitly pause, resume or write
a file. Final offline captures keep their existing schema and instruction-byte
contract; live inspection does not replace private inputs for native emission.

The runner's `host` object retains its flat `pc`, execution/IRQ/sector counters,
`adpcm_dma_bytes`, and five `buttons` masks. Additional bounded objects expose
stored state for debugging a stalled guest:

| Object | Stored observations |
| --- | --- |
| `debug_memory` | Write opt-in, successful request count and actually changed byte count |
| `cpu` | A/X/Y/SP/P, clock divisor, MPR transfer latch, sampled IRQ/vector, eight MPRs, physical PC, seven nullable instruction bytes with corresponding physical addresses and bank generations |
| `cd_control` | Enable, `bram_seeded` initial-input presence, interrupt enable/active bits, ACK/reset and port read/write counters |
| `cd_sense` | Present after sense/error activity: command/error counts and stored pending key/ASC/ASCQ/FRU plus nullable host-only failed LBA; inspection never consumes the context |
| `scsi` | Phase/signals, pending status, host/drive latches, event and ACK deadlines, response length/index, acknowledged bytes, TOC replies, sector-provider presence, read/load positions and retries, current command size and last CDB (at most 16 bytes) |
| `cd_audio` | Enable, state and stop mode, start/current/stop/seek positions, seek/sector/playback deadlines, played sectors, command count and fade state |
| `adpcm` | Enable/play/pending/nibble and IRQ state, control/DMA/rate, addresses/length, transaction deadlines, sample phase/count, port and DMA counters |
| `vdc`, `raster`, `interrupts` | VDC status/IRQ, 20 registers, current SATB words, DMA progress, raster clocks/phases/events and interrupt mask/timer progress |

`host.vdc.satb` is a fixed array of 256 unsigned 16-bit words in current stored
SATB order. Sprite entry `n` occupies words `4*n` through `4*n+3` (64 entries).
These are raw words, without game-specific coordinate or visibility
interpretation. They observe the VDC's current internal SATB, including partial
DMA progress; they do not read its VRAM source or a historical rendered frame.
Status exposes no VRAM or general RAM dump. Separate paused memory commands
are bounded to 256 bytes per request. The array adds at most 1,537 JSON
bytes, independent of guest activity.

These observations use direct stored values and non-mutating instruction
peeks. They never read MMIO ports, acknowledge an IRQ, consume CD response
data, or advance a device clock. Instruction peeks return `null` for I/O,
unmapped or other non-RAM/ROM banks. Each of the seven bytes is translated
separately through the current MPRs, including logical address wrap; generations
are invalidation hints, while mapping and exact bytes identify the source.
Status itself performs no memory edit or general dump. Repeated status requests while
paused preserve all reported guest state. The final runner JSON also includes
the same `cd_audio` and `adpcm` objects.

CD audio states are `0` playing, `1` idle, `2` paused and `3` stopped; stop modes
remain the numeric command modes. Timeline progress does not imply decoded PCM
or audible output. Ticks and deadlines are guest master ticks, not wall time.

Screenshot responses additionally contain:

```json
{"id":2,"ok":true,"source":"guest","width":2,"height":1,"frame":12,"ticks":345,"frame_ticks":340,"encoding":"rgb24-base64","data":"AAEC/f7/"}
```

Decoded `data` contains exactly `width * height * 3` bytes, RGB row-major with
no padding. `frame_ticks` identifies publication of the captured guest frame;
`ticks` identifies the current CPU safe point and can be later. A `present`
capture includes the current SDL composition/letterbox. It is not a screenshot
of the complete operating-system window or desktop. Capturing before the first
complete guest frame returns an error.

## Bounds and ownership

- One active client; the listener is nonblocking and exclusively bound on
  Windows. No remote address or configurable bind interface is supported.
- Requests including LF are at most 8,192 bytes. Response storage is capped at
  17 MiB; each `poll` moves at most 64 KiB over the socket.
- Guest images are at most 1,024 × 512 pixels. SDL composition captures are at
  most 4,000,000 pixels. Only one RGB copy and one encoded response are needed;
  large response storage is released after transmission or disconnect.
- Idle connections, incomplete requests, and outgoing responses have five-second
  bounds. An active script should issue a command at least once every five
  seconds; the CLI's timed hold sends a ping each second. Slow peers cannot
  indefinitely retain the response buffer or block simulation.
- Socket polling, command handling, SDL readback, and input snapshot application
  happen on the main thread. There is no unsynchronized worker touching guest
  memory. Paused RAM edits use the guarded command above; there is no host-language
  evaluation, file upload or automatic trace dump.
- This is an opt-in local development interface, without authentication. It is
  not an internet service. Loopback access has the same user-session trust
  boundary as launching the development runner locally.

## Verification and source lineage

The authored TCP suite exercises actual loopback sockets: fragmented/pipelined
requests, strict parser refusals and integer limits, all five input slots,
pause/resume/frame targets, exact RGB/base64 bytes and capture metadata,
capture failures, reconnect/input release, bounded memory hex/range checks,
paused/stepping gates and disabled/callback failures, maximum request length, stalled
partial requests, and a stalled maximum-size presentation response. The runner
integration tests separately verify that input/status/screenshots control the
real headless and optional SDL host, atomic compare refusal across invalid
banks, source generation changes, unchanged writes and edit counters.
A TCP transport check is not an independent
PC Engine video or gameplay oracle; those results retain their separate scopes.

The newline JSON envelope and useful development operations were reviewed from
[psxrecomp's TCP documentation](https://github.com/RetroPortingToolKit/psxrecomp/blob/31df2e1e0e0a6525733e68ff70e72ecbef84bb09/docs/TCP_COMMANDS.md)
and the
[snesrecomp server interface](https://github.com/RetroPortingToolKit/snesrecomp/blob/a410b7be2620b20d7ee03a031db54e97b5854b7b/runner/src/debug_server.c).
This server and its strict parser are original C++ implementations. Reference
implementation code was not copied across the projects' license boundaries.
Only the documented subset above is supported; command compatibility with
either reference server is not implied.
