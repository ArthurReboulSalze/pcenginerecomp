# CD commands, sector streaming and volatile BRAM

BRAM remains volatile guest storage by default. Explicit host export and checked
consumer sessions can persist its raw 2 KiB contents without changing the device
semantics below; see [PERSISTENCE.md](PERSISTENCE.md).

For restoration during an active READ handshake, see
[CD READ checkpoints](CD_READ_CHECKPOINTS.md). Those fixtures qualify partial
command/data/status continuation and preserve exact-build restrictions.
The [coupled CD/ADPCM qualification](CD_ADPCM_CHECKPOINTS.md) adds DMA captures,
pending audio-RAM writes, paused timers and distinct reset behavior.
The [guest-driven DMA/IRQ qualification](DMA_IRQ_CHECKPOINTS.md) separately
tests autonomous READ polling interrupted by an actual IRQ2 handler and RTI.

The baseline has two explicit profiles: idle CD control/BRAM through
`Bus::enable_cd_control()`, and a clocked command handshake through
`Bus::enable_cd_transport()`. Supplying `--bios`, `--toc` or `--disc` enables the latter
in the headless sandbox. Without either profile, CD accesses still fault.
The transport implements selection, command reception, TEST UNIT READY,
directory/TOC responses, DATA IN acknowledgement, status and message completion.
The TOC descriptor supplies metadata only. `--disc` separately attaches a
read-only sector provider. The extended BIOS-backed profile adds ADPCM RAM,
ports/playback consumption and DMA, CDDA control/position responses and a
fader. The guest CDDA sample latch reads actual audio sectors even with PCM
disabled. Separately enabled [audio output](AUDIO_OUTPUT.md) adds digital PCM
decoding/mixing and SDL/WAV presentation.
REQUEST SENSE now returns the fixed NEC error response with retained error
context and typed read recovery; see [CD_SENSE.md](CD_SENSE.md). Raw subchannel
capture remains unfinished. Explicit
[System Card reset-vector boot](SYSTEM_CARD_BOOT.md) is implemented separately. See [CD_AUDIO.md](CD_AUDIO.md) for the explicit control-timeline scope.

## Implemented contract

Hardware routing uses the physical bank after MPR translation. The control
registers below occupy bank `$FF`, offsets `$1800..$1BFF`. Addresses in another
logical page can therefore alias them through another MPR. These registers
are not mirrored every 16 bytes: `$1817` and `$1907` are unassigned read
locations, rather than aliases of `$1807`. They return `$FF` on the selected
standard-CD hardware profile. Writes to these decoded holes are accepted and
ignored, preserving the general I/O latch, BRAM gate and device registers.
Accepted accesses still increment the CD read/write diagnostic counters.

| Offset | Read | Write |
|---|---|---|
| `$1800` | SCSI BSY/REQ/MSG/CD/IO in bits 7..3; transport profile only | Begin selection; value is ignored; transport profile only |
| `$1801` | Drive byte in DATA IN/STATUS/MESSAGE IN, host latch otherwise; transport profile only | Set host data latch; does not itself acknowledge a byte; transport profile only |
| `$1802` | IRQ-enable bits 0..6 and current ACK in bit 7 | Set enable bits and ACK; asserted reset keeps ACK clear |
| `$1803` | Lock BRAM; active IRQ bits OR `$10`, plus bit 1 when the latch selects left | Read-only; ignore the write without locking BRAM |
| `$1804` | Stored low nibble of reset register | Store low nibble; bit 1 asserts reset, clears ACK and active IRQ bits `$70` |
| `$1805` | Low byte of the held signed CDDA sample latch | At least 700 master ticks after the last accepted write, alternate channel and capture its latest post-fader sample; first accepted capture selects right |
| `$1806` | High byte of the same latch | Ignore |
| `$1807` | Gear-reference BRAM unlock state: `$80` unlocked, `$00` locked; reading preserves state | Bit 7 selects unlocked/locked BRAM access |
| `$1808` | Sample the data byte; DATA IN with REQ/IO and CD clear asserts ACK, which releases after 21 master ticks | ADPCM address low byte in the extended profile |
| `$1809` | Zero in the selected reference profile | ADPCM address high byte |
| `$180A` | Return old ADPCM read latch and queue a RAM read | Queue ADPCM RAM data write |
| `$180B` | ADPCM DMA control | ADPCM CD DATA IN DMA control |
| `$180C` | ADPCM playing/end/read-busy/write-busy status | Source-documented ignored write |
| `$180D` | ADPCM control | Address/length/play/reset control |
| `$180E` | ADPCM rate | ADPCM sample-rate selection |
| `$180F` | Retained fader register | Restart clocked CDDA/ADPCM fade configuration |
| `$18C0..$18C3` | `$FF` on standard hardware; `$00,$AA,$55,$03` with an explicitly configured Super System Card | Ignore; read-only identification pins |
| Other unassigned offsets within `$1800..$1BFF` | `$FF` pull-ups, preserving the general I/O latch and BRAM gate | Ignore, preserving latch/gate/device state; increment the accepted CD-write counter |

Known CD ports still require their declared profiles: selection/data transport,
ADPCM and the fader do not become available through the ignored-write rule.
The rule is restricted to the CD decoder's `$1800..$1BFF` window. Enabling CD
control alone does not silently enable VDC, VCE, PSG, joypad or interrupt ports.
The separately enabled [VDC profile](VDC.md)
handles video ports. ADPCM ports require their extended profile. The CDDA
sample latch works with either CD profile, independently of PCM output;
see [sample-latch semantics](CD_AUDIO.md#guest-sample-latch). A decoded unassigned read is a
source-backed bus response, not a fabricated device service. In the ordinary
HuCard and System Card hardware maps, the unused bank-`$FF` window
`$1C00..$1FFF` also reads `$FF` and ignores writes, preserving the general
I/O latch and storage generations. A bare sandbox, including one with only
functional CD control enabled, retains explicit faults there. Existing
Arcade Card interception and known identification ports keep their own
semantics. These decode changes add no state fields and retain runtime ABI 24.
Unknown command IDs use
the strict default or explicit reference-response policy described below.
The IRQ2 level is the intersection of active and enabled sources. Its
transport source `$20` follows a requested STATUS/MESSAGE byte; `$40` follows
a requested DATA IN byte. ACK clears REQ and its source. ADPCM adds half/end
sources `$04/$08`. With IRQ support enabled, eligible IRQ2 uses the delivery
contract in [CPU_SEMANTICS.md](CPU_SEMANTICS.md); the legacy transport-only
profile retains its explicit unsupported-delivery exit. Device changes are
observed at instruction boundaries, with the
same access-phase approximation as video timing; this does not establish
cycle-exact CPU bus phases.

## Clocked transport

The host latch and drive data byte are separate. Writing `$1801` does not
advance the command or overwrite the drive's status byte. The host sets ACK
through `$1802` bit 7 only after observing REQ. A requested command byte is
captured once when REQ and ACK are both high, and REQ falls. Repeated high ACK
writes cannot capture extra bytes. Dropping ACK allows the next command-byte
request or dispatch of a complete command. Reads of `$1801` never acknowledge
it automatically. `$1808` samples the same byte and additionally acknowledges
a requested DATA IN byte. Its auto-ACK release schedules the next byte like a
manual ACK falling edge. Outside DATA IN it samples without acknowledging;
the extended profile handles write-side ADPCM semantics separately.

Six-byte **TEST UNIT READY (`$00`)** produces GOOD status (`$00`) followed by
COMMAND COMPLETE message (`$00`). Ten-byte **GET DIRECTORY INFO (`$DE`)**
returns metadata through the bounded DATA IN path described below.
Unsupported commands stop explicitly when dispatched; the captured command
remains useful diagnostic state. REQUEST SENSE (`$03`) returns the fixed
18-byte NEC response through DATA IN, then GOOD status and completion.
The extended audio profile implements D8/D9/DA/DD control/position responses,
with explicit seek/end/loop events rather than immediate successful stubs.
READ `$08` requires actual readable
media; TEST UNIT READY still only certifies its control transaction.

| Transition | Geargrafx-reference delay in master ticks |
|---|---:|
| Selection write → COMMAND with REQ | 75,000 |
| Intermediate command byte ACK falls → next REQ | 3,000 |
| Complete TEST UNIT READY ACK falls → GOOD status with REQ | 450,000 |
| Complete supported directory command ACK falls → DATA IN with first REQ | 9,000 |
| DATA IN byte ACK falls → next response byte REQ | 900 |
| `$1808` auto-ACK assertion → ACK release | 21 |
| Last DATA IN byte ACK falls → GOOD status with REQ | 3,000 |
| Status byte ACK falls → MESSAGE IN with REQ | 1,500 |
| Message byte ACK falls → BUS FREE | 1,500 |

The command remains in COMMAND with REQ clear during its completion delay.
STATUS and MESSAGE IN drop REQ while ACK is asserted, clearing the transport
IRQ source. The delayed phase transitions then request the next byte. A held
ACK is observable at a delayed REQ edge and consumes that request once.
Reset bit 1 cancels pending transitions, clears transport latches/command
state and ACK, returns the bus to idle, and clears active IRQ bits `$70`;
the IRQ-enable mask, attached TOC metadata and sector provider are preserved. Releasing reset
does not resurrect a partial command, response or auto-ACK timer.

Selection during DATA IN follows Geargrafx's separate abort profile: eight
GOOD status bytes are exposed and COMMAND is scheduled after 900,000 ticks.
Status/message ACKs can replace that pending transition as in the reference.
The local tests cover both consuming this response and leaving it pending;
the live suite checks settled abort sequences.

These are a deterministic **reference-emulator timing profile**, not measured
drive timing. The pinned Mesen source calls its delays approximations and
deliberately shortens TEST UNIT READY. It corroborates the initial selection,
byte and completion delays after conversion from CPU ticks, but changes
STATUS/MESSAGE phases immediately. The runtime follows Geargrafx's delayed
phase profile. Live checks compare settled transactions; they do not qualify
the exact instant of a CPU register access or physical drive accuracy.

## READ `$08` and the read-only provider

The six-byte CDB selects LBA `((byte1 & $1F) << 16) | (byte2 << 8) | byte3`.
Byte 4 requests 1..255 sectors; zero means 256. DATA IN begins immediately
without REQ until a sector is loaded. There is one 2 KiB buffer, never an
unbounded command-sized allocation. Sector bytes request immediately on ACK
release, while short directory responses retain their 900-tick interbyte delay.
The final sector byte's ACK release schedules GOOD after 3,000 ticks, then the
existing status/message completion. `$1808` pulses ACK for 21 master ticks;
ordinary `$1801` reads only sample DB. IRQ sources remain `$40` data and `$20`
status/message; `$1803`'s forced `$10` bit is not a new transfer-complete IRQ.

The buffer becomes available when its last byte is placed on DB, before that
byte's ACK. A new sector can fill the backing buffer without overwriting that
outstanding DB byte. An occupied buffer postpones the next load by 290 ms.
Phase, load and auto-ACK events have separate guest deadlines; ties process in
that order. No wall-clock timers are used.

After a sector loads successfully, the retained data head advances to the
following sector, clamped to the last disc sector in the selected Gear
profile. This occurs when the backing buffer fills, before its payload has
necessarily been acknowledged. A failed load or a retry caused by an occupied
buffer leaves the head unchanged. Idle `$DD` position responses and a later
audio seek use this retained head. The queued load address remains separate;
clamping the head does not repeat the last data sector or hide a later
past-leadout read error.

The explicit deterministic **1x profile** uses a 150 ms first access plus one
75 Hz sector period: 3,507,953 master ticks. Later loads use 286,363 ticks;
backpressure retries use 6,228,408 ticks. Geargrafx instead uses seek distance
and a one-time randomized reset phase. Local literal edge tests qualify these
chosen constants; live comparisons qualify settled payload/handshake behavior,
not physical drive timing or exact CPU access phases. Accelerated drive speeds
and CDDA interaction are not implemented.

Missing providers fault explicitly. Invalid starting LBA returns CHECK CONDITION
`$02`, deliberately differing from Geargrafx's immediate GOOD shortcut. Crossing
leadout, audio/gap reads and provider failures return CHECK CONDITION, increment
`read_errors`, cancel further loads and expose no partial sector. They retain
a typed sense context. Source/configuration/host/opaque decoder faults instead
remain terminal; see [CD_SENSE.md](CD_SENSE.md). Successful sectors and DATA IN
ACKs have separate counters.
Reset cancels load/phase/auto-ACK work while retaining provider ownership.
Selection during DATA IN retains the reference's delayed COMMAND abort profile;
loads already due before that transition can still occur. COMMAND cancels the
load timer and remaining count. The count cleanup deliberately avoids the pinned
Geargrafx source's stale-count behavior contaminating a subsequent TOC command.
That mixed abort edge is covered locally, not claimed as live Gear parity.

`SectorProvider` is a single-threaded read-only interface whose data reads
return exactly 2,048 user bytes or a typed read error/terminal `Fault`. The
factory accepts cooked ISO, supported CHDv5 MODE1/MODE1_RAW/AUDIO and bounded
BIN/CUE layouts. Stored audio has a separate raw-sample interface and playback
gate. It hashes the actual image/components, derives track geometry, and checks exact TOC/hash agreement on
attachment. A source size/mtime change refuses further reads; this is a local
integrity guard, not protection against hostile same-size/same-timestamp edits.
CHD decoding requires an explicitly selected optional libchdr shared library.
One hunk (at most 512 KiB) is cached. Metadata is bounded to 1 MiB / 99 tracks;
parent/legacy/GD-ROM CHDs, data reads from gaps/audio and invalid raw MODE1 headers are
refused. Read-only libchdr errors are never replaced with zero-filled data sectors.
No ECC/EDC correction, public raw-sector API or full image extraction is
implemented. Hashing does not certify an image against an external dump database.

Local READ checks cover both execution tiers/speeds, ACK modes, every byte of a
256-sector request, deadlines/guards, backpressure, reset and failures. Provider
checks use known SHA256 answers, authored ISO sectors and a clearly labeled
libchdr ABI double for CHD mapping. Six private real-CHD sector slices separately
agree with the Python reader using the same libchdr decoder; that corroborates
mapping/slicing, not independent decompression correctness. Live Gear checks
use entirely authored sectors; see [REFERENCE.md](REFERENCE.md).

## Directory response and metadata boundary

The command's byte 1 selects one of three implemented modes. Every response
has four bytes in the selected Geargrafx/Mesen profile:

| Mode | Response |
|---|---|
| `$00` | `$01`, last track number in BCD, `$00`, `$00` |
| `$01` | Absolute leadout minute/second/frame in BCD, `$00` |
| `$02` | Requested track's absolute INDEX 01 minute/second/frame in BCD, type `$00` audio or `$04` data |

Mode `$02` reads the track selector from command byte 2. Track zero aliases
track 1. BCD track numbers above the last track and the explicit `$AA` leadout
sentinel return the absolute leadout position with type `$00`. Other malformed
BCD selectors and unsupported modes fault explicitly with attached metadata.
Without a TOC, the command returns CHECK CONDITION (`$02`) through the
Geargrafx status/message path; it does not invent tracks. This reference path
also presents `$02` as its message byte. REQUEST SENSE can retrieve the
retained no-medium context without requiring fabricated TOC metadata.

`CdControl::set_toc()` validates 1..99 consecutive tracks, strictly increasing
nonnegative INDEX 01 LBAs before leadout, and type values 0/4. Leadout is bounded
to 449,849 so adding the 150-frame lead-in fits absolute BCD `99:59:74`.
Attachment requires an idle enabled transport; reset preserves the metadata.
The runtime converts disc LBAs to absolute MSF only when constructing replies.

The frontend exports a descriptor without decompression or sector extraction:

```sh
python -m pcerecomp toc "/path/to/disc.chd" --out .local/title/disc.toc
build/pce-headless .local/title/boot.bin 0x100000 0x4000 255,248,128,129,130,131,132,0 100000 2000000 hybrid --bios .local/firmware/syscard3-usa.pce --toc .local/title/disc.toc
```

Use `.exe` on Windows. The exporter also accepts a single-track cooked
2048-byte-sector ISO. CHD metadata supports AUDIO, MODE1 and MODE1_RAW;
unsupported formats/types fault. Stored and virtual pregaps affect disc time
according to the metadata; four-frame CHD storage padding does not. Inter-track
postgaps move following INDEX 01 positions. The chosen Geargrafx CHD profile
reports leadout at the end of the final track's program frames, excluding a
trailing POSTGAP. This last rule is explicit reference compatibility, without
console qualification. No implicit 150-frame correction changes exported LBAs.
The supported CUE subset also accepts explicit POSTGAP; its leadout includes
a trailing postgap, matching the independently checked Beetle CUE profile.
Gear's CUE loader does not implement that directive. Equivalent-PREGAP Gear
fixtures therefore corroborate only their declared inter-track geometry and
playback classification, not direct POSTGAP parsing. See [MEDIA.md](MEDIA.md).

The canonical ASCII format is bounded to 8 KiB:

```text
PCE_TOC 1
image_sha256 <64 lowercase hex digits>
leadout_lba <decimal disc LBA>
track <consecutive number> <decimal INDEX 01 LBA> <0 or 4>
```

Each track has one line. The parser rejects bad versions/fields, trailing
tokens, invalid characters/numbers/hashes, ordering violations and excessive
tracks. The exporter hashes the source image and refuses an output alias of
that source. **Headless trusts the descriptor's hash as provenance; it does
not reopen or authenticate the original disc.** `--toc` alone enables transport
and volatile BRAM, without firmware or video timing; it supplies no readable
sector backend. Both optional argument orders with `--bios` are supported.

The profile starts idle with BRAM unlocked, ACK/reset/IRQ fields zero and,
by default, unformatted, zero-filled **volatile** storage. An explicit
`--bram` input can supply a read-only initial 2 KiB snapshot; see
[FIRMWARE.md](FIRMWARE.md). Bank `$F7` has exactly 2 KiB
of writable BRAM at offsets `$0000..$07FF`. Locked reads and the remaining
6 KiB return `$FF`; locked/upper-hole writes are ignored. The hole does not
mirror the first 2 KiB. MPR aliases observe the same storage. Loading an
explicit initial snapshot advances the bank generation once; subsequent
changed BRAM bytes advance its write generation. Control writes and lock
changes do not count as RAM writes. Guest writes remain volatile: there is
no implicit save loading, writeback or export.

`Bus::read` can now produce device side effects. `peek` remains a pure source
inspection operation: it returns no value for I/O or BRAM, so source guards
cannot lock BRAM or dispatch stale BRAM code across a protection change.
CPU loads/stores/indexing/RMW all use the same bus path. A fault does not
retire the instruction; it is still a fatal, non-transactional exit.

The current native-module ABI is **25**, including live scroll-write history,
queued VDC state, pending sense context,
guest CDDA sample-latch state,
held PSG DAC values, digital audio state,
IRQ/timer and palette/DMA alongside joypad and CD sector/TOC/response state.
Regenerate older modules and rebuild all consumers. Exact-build
[developer checkpoints](DEVELOPER_CHECKPOINTS.md) retain both data latches,
phase, ACK, command and response bytes/positions, pending event and auto-ACK
deadlines, checked provider/TOC identity and geometry, IRQ state and BRAM
contents. They require fresh startup with the same reviewed build and media;
portable or cross-build state migration remains unimplemented.

## Reference choices and limits

The register/profile behavior follows pinned Geargrafx 1.8.4 where explicitly
implemented. It is not a claim that all independently developed references
agree on undocumented hardware details:

- Geargrafx and Mesen decode CD register offsets with `address & $3FF` and
  ignore unassigned writes. Thus `$1811` does not write the `$1801` host latch,
  and `$1817` does not write the `$1807` BRAM gate. Beetle's pinned CD interface
  instead switches on `address & $F`; its top-level hardware router separately
  handles `$1A00..$1BFF` as Arcade Card space and returns zero there when the
  card is absent. These source differences are retained explicitly. The
  toolkit selects the Geargrafx/Mesen decoder for its declared CD profiles;
  the new decode suite does not establish live Mesen or Beetle CD parity.
- Mesen/Beetle treat `$1807` reads as CD subcode. Geargrafx instead reads back
  BRAM access state. This runtime selects Geargrafx's `$80` unlocked / `$00`
  locked response and preserves the gate on reads. Reading `$1803` still
  locks BRAM, and its changed state is visible through the next `$1807` read.
  This is an explicit emulator-profile disagreement; hardware behavior and
  the alternate subcode interface remain unqualified.
- Geargrafx includes `$10` in `$1803` status and keeps its audio-channel bit
  stable without sample-latch writes; Mesen differs. Accepted `$1805` writes
  alternate this bit through the implemented right-first sample latch.
- Geargrafx clears active SCSI IRQ bits on reset; Mesen clears enable bits
  instead. The runtime follows Geargrafx's active-bit rule. The retained idle
  suite did not generate live IRQ sources; transport checks have separate scope.
- Geargrafx/Mesen use bit 7 to lock or unlock on every `$1807` write; Beetle's
  pinned implementation only enables on a set bit. Hardware confirmation
  remains useful before calling these edge cases console conformance.
- Geargrafx/Mesen return immediate GOOD status after the first byte of an
  unknown command is acknowledged. There is no special `$FF` command handler.
  Strict mode retains an explicit fault. The optional
  `--cd-unknown-status gear-good` profile reproduces this specific protocol
  response for unknown command lengths, records their count and retains the
  last captured CDB. It does not implement or execute an unknown operation.
  Hardware behavior has not been qualified. `--cd-unknown-status fault` selects
  the default strict behavior. Known commands whose semantics remain absent
  still fault under either setting. ABI 27 additionally offers the explicit
  `nec-invalid` profile: complete NEC-framed unknown packets receive CHECK
  CONDITION and sense `$05/$20`, rather than GOOD. Raw error wire and reset
  differences remain documented under [unknown CD profiles](CD_UNKNOWN.md).
  REQUEST SENSE has a known six-byte CDB
  and now returns the fixed NEC payload documented separately. Geargrafx returns
  delayed GOOD without data; this runtime does not adopt that shortcut.
- Geargrafx/Mesen send four bytes for each supported directory mode. Beetle
  sends two, three and four respectively, and its source notes that physical
  response lengths were not confirmed. It also treats unknown modes as mode
  zero; this runtime refuses them. The four-byte profile is reference evidence,
  not a hardware-conformance claim. The `$AA` leadout sentinel agrees with
  Beetle and Geargrafx's above-last-track result.
- On the observed DATA IN selection-abort transition, Geargrafx retains the
  old DATA IRQ `$40` while adding STATUS IRQ `$20`, producing active `$60`
  until ACK clears REQ and both sources. The runtime preserves this reference
  behavior. Ordinary requested data/status bytes expose `$40`/`$20` respectively.
  Mesen's intermediate phase-clear IRQ update appears to differ in source;
  it was not run live. This edge is emulator compatibility, without hardware
  confirmation.

The original idle-control fixture is entirely authored RAM code. Its initial
scope checked 61,440 expected
native/interpreter load/store cases, all input bytes under four flag contexts,
the whole BRAM extent, MPR aliases, RMW read side effects, indexed hole
crossings, operand mutation, deadlines and explicit faults. The independent
MCP suite uses an authored 256 KiB bootstrap and blank 300-sector CUE/BIN,
then requires `is_cdrom_hardware_enabled=true`. This avoids comparing against
an emulator with CD hardware disabled. No retail BIOS/disc/save is needed.
See [REFERENCE.md](REFERENCE.md) for measured results and reproduction.

The new authored `pce-cd-decode-tests` suite passes **31,464,248 checks** across
**5,230,464 native and 5,230,464 interpreted instructions**. It sweeps every
decoded CD hole and ordinary unused-window address with all 256 write bytes,
both CPU speeds and two logical-page aliases. Standard/Super System Card
profiles and the base HuCard unused window are covered. Literal checks assert
normal load/store retirement, pull-ups or selected identification bytes,
accepted-access counters and unchanged latch, gate, control state, storage
and generations. Disabled known devices and the unconfigured sandbox still
fault. Four negative guards cover the deadline, a full-MPR mismatch and both
source bytes with an armed timer; they preserve guest/device state.

An independent **frozen-candidate run** compiles the original pinned
Geargrafx core separately and executes authored System Card/CUE and HuCard
fixtures: **20 cases, 82,144 instructions per tier and 82,224 records**, with
**2,038,488 independent literal scalar checks per tier**. Native execution has
zero interpreter work; complete logical PC, MPR, physical-source bytes and
per-key hits agree across tiers. CPU/device records and WRAM/BRAM hashes match
Gear without field projections. The explicit zero RAM/register setup is a
synthetic test contract, not BIOS formatting or hardware reset parity. This
run uses implementation `8add7506f75018d9b3b7517ada0b99db30bed16e`, canonical
source `466e7e20c1691ee54bd6b32f52a76e402c32eeda7b8ae4a84ca49ba8f142b6e8`
over 68 files. All 453 bound inputs/artifacts rehash unchanged; 36 material
evidence mutations are rejected. No retail input, ADPCM/CDDA streaming, physical open-bus
behavior or unimplemented expansion is qualified by this suite. Existing I/O
and transport tests now assert ignored-write invariants in place of their
older hole-write refusal expectations; the other refusal checks remain.

The transport suite passes 8,369 groups, including 4,096 independently expected
latch/control groups and 4,096 TSB/TRB control groups, plus directed edge/refusal checks. Byte
groups cover all 256 latch/control values, four status contexts, two speeds
and both execution tiers. Literal 75,000/3,000/450,000/1,500-tick edges,
held ACK, repeated selection within COMMAND, reset cancellation, IRQ2 refusal, operand mutation and
deadlines are local expectations. They are distinct from settled emulator
observations and do not qualify a media backend.

The TOC extension adds 418 independent groups for literal response/BCD,
DATA IN, auto-ACK, reset/abort and refusal in the same synthetic test binary. Frontend
geometry tests and headless parser-boundary tests separately cover descriptor
construction, source protection and untrusted metadata. See REFERENCE.md for
the independent mixed-track sequence scope. One pending-response/auto-ACK
reset plan remains unqualified after reproducible crashes of the isolated
Geargrafx reference process; local reset expectations are separate evidence.

## Sources

- [Geargrafx CD registers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/cdrom.cpp),
  [memory routing](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory_inline.h)
  and [SCSI phases/commands](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.cpp),
  [signals](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.h)
  and [clock/IRQ helpers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller_inline.h).
- [Mesen CD interface](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/CdRom/PceCdRom.cpp)
  and [memory routing](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceMemoryManager.cpp).
- [Mesen SCSI implementation](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/CdRom/PceScsiBus.cpp):
  latch separation, handshake and deliberately approximate timing.
- [Beetle CD interface](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/pce/pcecd.cpp)
  and [hardware I/O routing](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/pce/pce.cpp).
- [Geargrafx CHD geometry](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/cdrom_chd_image.cpp)
  and [TOC getters](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/cdrom_media_inline.h):
  INDEX 01, pregaps/postgaps and absolute leadout conversion.
- [Beetle directory commands](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/cdrom/scsicd-pce-commands.inc):
  response-length differences and the `$AA` leadout selector.

These are research references, not linked or copied CPU/device implementations.

## Bounded unknown-command diagnostics

ABI 16 adds the `cd_unknown` status/final-JSON object, preserving opcode attempt
counts and the last unknown CDB plus mapped source context when available. The
record survives later known commands and transport resets. This does not add a
command implementation or change the strict default. See
[the diagnostic contract](COMPATIBILITY.md#unknown-cd-command-diagnostics).
