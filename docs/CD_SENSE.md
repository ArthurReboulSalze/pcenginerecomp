# CD error recovery and REQUEST SENSE

The CD transport implements the NEC six-byte REQUEST SENSE command (`$03`)
through its existing bounded DATA IN handshake. It returns an actual error
response, rather than treating the command as successful without data.
Successful READ cadence, the selected Gear-style status/message handshake,
unknown-command policy and CDDA playback profile remain separate contracts.
ABI 27's explicit [invalid-command profile](CD_UNKNOWN.md) adds pending sense
`$05/$20/$00` after a complete invalid CDB. The strict default and legacy
GOOD-only unknown response remain selectable independently of real SENSE data.

## Fixed response and lifetime

The selected NEC response always contains **18 bytes**, including when CDB
allocation byte 4 is zero, smaller than 18 or larger than 18. This follows
the independently executed Beetle implementation; it is not a general SCSI
allocation-length promise. All bytes start zero, with these fields:

| Byte | Value |
|---|---|
| 0 | `$70`, current error with no valid information field |
| 2 | Pending sense key |
| 7 | `$0A`, additional length |
| 12 | Additional sense code (ASC) |
| 13 | ASC qualifier |
| 14 | Field-replaceable-unit value, currently zero |

REQUEST SENSE works without a TOC or provider. It snapshots the pending
context into the response and clears that context **when the complete CDB
is dispatched**, including when the subsequent transfer is aborted. A second
request returns the no-error response. Successful unrelated commands preserve
an outstanding context; a later error replaces it. Warm SCSI reset preserves
the pending context, while cold `CdControl` initialization clears it.

The first byte settles through the aggregate DATA IN handshake without a
new scheduled drive delay. Subsequent bytes retain the selected transport's
900-master-tick short-response pacing, 21-tick automatic ACK and existing
status/message completion. Beetle enters DATA IN before its next service pass
asserts the first REQ. These are functional response/lifecycle comparisons,
not electrical phase or exact transport timing parity.

## Recoverable media outcomes

Only explicit `SectorReadError` outcomes are converted to guest CHECK
CONDITION. They carry a typed reason and the requested LBA. The following
bounded mappings are implemented:

| Outcome | Key / ASC / ASCQ |
|---|---|
| Missing TOC for an existing directory/audio command | `$02 / $0B / $00` |
| Starting READ outside the volume or crossing leadout | `$05 / $25 / $00` |
| Starting READ on an audio track, or provider rejects non-data | `$03 / $1D / $00` |
| Explicit unavailable data payload or unsupported gap read | `$05 / $00 / $00` |
| Validated malformed MODE1 raw header | `$03 / $11 / $05` |

Starting READ uses the attached TOC's track classification. Later sector
classification belongs to the provider. A mid-stream audio/gap rejection is
an explicit provider policy; it is not a claim of exact Beetle raw-sector
validation behavior across a track boundary. No ECC/EDC repair or physical
media-error model is introduced.

The toolkit rejects a starting LBA at or beyond leadout. Pinned Beetle's
starting READ check uses `>` rather than `>=`; exactly at leadout it can instead
classify the leadout TOC entry as non-data. The finite independent vector uses
LBA 25 on a 20-sector volume, plus a read from 19 crossing leadout. Exact
starting-at-leadout equivalence is not claimed.

A failed sector is never partially published. The transport cancels remaining
loads and presents CHECK CONDITION; a subsequent command can request sense
and retry an independently valid read. CHD caches invalidate their previous
hunk identity before decoding, so a failed decoder that overwrites its output
cannot leave that memory mislabeled as an older successful hunk.

Source identity changes, missing/unsupported configuration, host open or short
reads, unknown decoder failures and malformed provider error contracts remain
terminal `Fault` outcomes. They do not become a plausible guest media error.
Built-in provider identity guards run before recoverable classification and are checked
again before a typed error escapes. Missing READ providers remain configuration
faults, including TOC-only recipes; metadata never fabricates readable media.

## Inspection, ABI and reference boundaries

After a sense request or latched error, paused `status.host` and final runner
JSON include `cd_sense` with `commands`, `errors` and `pending`. The pending
object contains `key`, `asc`, `ascq`, `fru` and nullable `failed_lba`.
These diagnostics do not acknowledge, clear or clock the device. Failure LBAs
are host diagnostics only; guest response bytes 3..6 remain zero with no valid
information bit. Runs with no sense/error activity retain their previous
metadata shape.

Runtime ABI **22** adds the pending context and counters. Re-emit retained
ABI-12 through ABI-21 captures with their original labels, then rebuild the
module and runtime together. ABI 22 itself added no serialized state format.
Later exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve
the pending context separately from the active response snapshot, CDB/data
position, ACK and scheduled transitions. Cross-build state migration remains
unimplemented.

Geargrafx supplies a delayed GOOD-only REQUEST SENSE shortcut with no payload.
This implementation deliberately differs. Beetle supplies the independently
executed payload/lifecycle reference. Its error status byte is `$01`; the
toolkit retains the existing Gear-style `$02` status/message encoding.
Comparisons distinguish status classes and sense payload from raw wire
agreement. See [REFERENCE.md](REFERENCE.md) and [STATUS.md](STATUS.md) for
the actual compiled adapters, checks and limits. No hardware, complete CD
protocol or campaign compatibility is certified by this finite scope.

Primary sources: [Beetle NEC SCSI implementation](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/cdrom/scsicd.cpp),
[Geargrafx SCSI implementation](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/scsi_controller.cpp).
