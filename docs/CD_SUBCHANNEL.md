# Captured CD subchannels

ABI 29 adds original captured P–W data to the read-only provider and an
explicit `captured-q` runtime profile. The default `synthesized` profile
preserves the existing TOC/program-position replies. No title detection,
media checksum exception or firmware service selects a different profile.

```toml
[runtime]
cd_subchannel = "captured-q"
```

This optional field belongs in a complete consumer descriptor with a pinned
`[disc]`. Both hosts accept `--cd-subchannel synthesized|captured-q`.
Captured mode requires an enabled transport and a provider with at least one
supported captured extent. Metadata-only TOCs, ordinary ISO/BIN/CUE and CHDs
without original raw subchannels do not satisfy that requirement. Custom
providers must declare their capability explicitly.

## Original media bytes

`SubchannelSector` contains exactly 96 symbols in disc order, excluding the
two synchronization symbols. Each byte contains P at bit 7, Q at bit 6,
through W at bit 0. `SectorProvider::read_subchannel(lba)` returns original
symbols or `nullopt` for explicit absence. It never creates Q from a TOC,
repairs CRC, swaps audio byte order or substitutes zeros for a failed read.
`has_subchannel()` means at least one supported captured extent exists; it
does not promise a packet at every LBA or a valid Q CRC.

CHDv5 `RW_RAW` is supported. The offset within each 2,448-byte decoded unit
is the stored payload size: 2,048 for MODE1 and 2,352 for MODE1_RAW/AUDIO.
Stored pregaps use their separate `PGTYPE`/`PGSUB`; an unstored gap has no
captured bytes. Captured pregaps with a different payload size from their
program track are refused; the reader does not guess a mixed-size storage
layout. Four-frame track storage padding is never exposed as disc
data. `NONE` means absent, even if padding contains nonzero bytes. Cooked
`RW` access faults explicitly; its format is not guessed to contain original
raw P–W. Unknown subtype metadata is refused. ISO and the supported BINARY
CUE profile have no captured subchannels.

Reads retain the existing pinned image identity, size/timestamp checks,
bounded one-hunk cache and fatal decoder-error policy. A decoder failure
invalidates its cache tag before it can partially overwrite cached storage.
Source/configuration/I/O errors do not become recoverable missing captures.

## Captured Q and command replies

Acquisition extracts Q from bit 6, most significant bit first, and validates
the complemented CRC-16 with polynomial `0x1021` over its first ten bytes.
The last CRC-valid packet and last CRC-valid ADR-1 position packet are
separate latches. Another ADR updates the first latch only. Missing capture
or bad CRC retains both earlier latches. BCD fields are preserved as captured;
the runtime does not repair or replace them with a calculated position.

Successful READ acquisition samples the loaded sector, separately from the
advanced drive head. CDDA acquisition follows the declared sector timeline.
Reading `$DD` inspects retained state and does not perform a fresh media read.
Before the first valid ADR-1 packet, position fields remain zero. Captured
`$DD` uses the Beetle-style ten-byte response: status 0/2/3 for playing,
paused/stopped, reserved byte 1 zero, then retained track/index, relative MSF
and absolute MSF. The synthesized default keeps its prior control/ADR byte
and calculated position behavior.

TCP/final JSON reports `cd_subchannel.profile`. Captured mode additionally
reports acquisition/missing/CRC counters, sampled LBA, validity flags and both
12-byte latches. These counters describe device acquisitions, not new guest
instructions or proof of hardware timing.

## State and migration

The profile and complete retained state are serialized and validated in CORE.
A checkpoint during a partially acknowledged `$DD` response retains the
ordinary response buffer, index, handshake and deadlines as well as Q state.
Restore checks the independently configured destination profile and media
capability before committing state. Host identity binds even an explicitly
selected default separately from omission.

Native modules must be regenerated for ABI 29 and their runtime rebuilt.
Original capture ABI labels remain unchanged; accepted old captures may be
re-emitted. Existing ABI 28 binaries/checkpoints cannot be imported into an
ABI 29 candidate. A consumer migration needs its own startup and qualification;
adding this feature does not silently move an already qualified project.

## References and limits

The media contract follows the payload-sized offset in
[MAME's original CD image implementation](https://github.com/mamedev/mame/blob/da9333a2a5123012a939e78c3f2df7175ea7d100/src/lib/util/cdrom.cpp).
The captured-Q retention/reply policy is compared with original
[Beetle PCE SCSI code](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/cdrom/scsicd.cpp).
[Geargrafx](https://github.com/drhelius/Geargrafx/tree/1c62a549328241518101f5be5bf3e6840b96ea5d) supplies an independent
captured-Q CRC/extraction check for its supported media path; its ordinary
position replies and the other cores' device interfaces are not identical.
Verification records pin the exact source revisions used, rather than treating
moving upstream branches as immutable evidence. GPL reference code is built
in separate opt-in executables and is not linked into the runtime.

The final isolated original-core comparison passes **315 authored raw96
records**, including 53 valid CRC packets across ADR modes. Toolkit CRC,
last/ADR-1 retention and every ten-byte `$DD` payload match original Beetle
exactly. Gear's separate decoder admits its seven valid ADR-1 records with
matching extraction. Noise in other bit lanes, checksum corruption, index 00,
leadout track and zero-before-first-valid retention remain explicit fixtures.
This comparison operates at the device layer, not through guest instructions.

`pce-subchannel-tests` separately checks acquisition/absence, fatal provider
failures, READ loaded-sector ordering and occupied-buffer retries, audio
start/advance/pause/resume/reset retention and ten partial-response checkpoint
cuts. Direct/restored complete CORE bytes agree without rereading captured
media; mismatched profiles and invalid retained state refuse atomically.
`pce-subchannel-sector-tests` checks the provider against an authored decoder
ABI double. It does not qualify real compression. Python frontend fixtures
check the same original-byte/absence and metadata-refusal contract.

To reproduce the optional original-core comparison, build with
`-DPCE_BUILD_REFERENCE_PROBE=ON`, then run:

```sh
python scripts/subchannel_reference.py --gear-source GEAR_CHECKOUT --beetle-source BEETLE_CHECKOUT --compiler clang++ --probe BUILD/pce-subchannel-reference-probe --out .local/subchannel-reference
```

Supply original checkouts at the pinned revisions and the static reference
libraries required by that toolchain using repeated `--library PATH` options.
Output must be a fresh private directory. The script records exact build/run
commands, refuses changed pinned source and preserves all bound inputs through
the final comparison. A failed or source-changing attempt remains a failed
receipt; matching rows alone do not override failed source preservation.

This milestone does not add the `$1807` subchannel byte FIFO, overflow policy,
subchannel IRQ source, R–W decoding, lead-in capture, electrical phases or
hardware consensus. The existing BRAM readback at that port remains the default.
Those interfaces differ between Geargrafx, Beetle and Mesen and need a separately
selected, independently verified device profile. A captured packet test is
separate from retail execution on media that declares no captured subchannels.
