"""Read-only, bounded CD inspection; disc LBAs and CHD frames are distinct.

CHD layout facts follow MAME's chd.h and cdrom.cpp. libchdr is an optional,
separately built BSD library, not an implicit download or system installation.
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
import ctypes
import hashlib
import os
from pathlib import Path
import struct


class MediaError(ValueError):
    pass


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True)
class Track:
    number: int
    type: str
    frames: int
    pregap: int
    stored_pregap: bool
    postgap: int
    chd_start: int
    disc_start: int  # INDEX 01, LBA zero is start of disc, excludes lead-in
    subtype: str = "NONE"
    pregap_subtype: str = "NONE"
    pregap_type: str = ""

    @property
    def index1_frame(self) -> int:
        return self.chd_start + (self.pregap if self.stored_pregap else 0)

    @property
    def data_frames(self) -> int:
        return self.frames - (self.pregap if self.stored_pregap else 0)


class Chd:
    """CHDv5 header and CHTR/CHT2 metadata, without decompressing any hunks."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.tracks: list[Track] = []
        initial = self.path.stat()
        self._stamp = (initial.st_size, initial.st_mtime_ns)
        size = initial.st_size
        with self.path.open("rb") as stream:
            header = stream.read(124)
            if len(header) != 124 or header[:8] != b"MComprHD":
                raise MediaError("Not a complete CHD header")
            length, version = struct.unpack_from(">II", header, 8)
            if version != 5 or length != 124:
                raise MediaError("Only CHDv5 is supported by the metadata reader")
            self.codecs = [header[i:i+4].rstrip(b"\0").decode("ascii") for i in range(16, 32, 4)]
            self.logical_bytes, self.map_offset, offset = struct.unpack_from(">QQQ", header, 32)
            self.hunk_bytes, self.unit_bytes = struct.unpack_from(">II", header, 56)
            self.raw_sha1 = header[64:84].hex()
            self.combined_sha1 = header[84:104].hex()
            if any(header[104:124]):
                raise MediaError("Parent/delta CHDs require an explicit parent; unsupported")
            if not 0 < self.hunk_bytes <= 524288 or self.unit_bytes != 2448:
                raise MediaError("Expected CD CHD with 2448-byte units and bounded hunks")
            if self.hunk_bytes % self.unit_bytes or self.logical_bytes % self.unit_bytes:
                raise MediaError("Misaligned CD CHD geometry")
            seen: set[int] = set()
            chd_start = disc_cursor = 0
            while offset:
                if offset in seen or len(seen) >= 1024 or not 124 <= offset <= size-16:
                    raise MediaError("Invalid, cyclic, or excessive CHD metadata")
                seen.add(offset)
                stream.seek(offset)
                tag, flags_length, next_offset = struct.unpack(">4sIQ", stream.read(16))
                count = flags_length & 0xFFFFFF
                if count > 65536 or offset + 16 + count > size:
                    raise MediaError("Truncated or oversized metadata")
                data = stream.read(count)
                if tag in (b"CHT2", b"CHTR"):
                    try:
                        tokens = data.decode("ascii").split("\0", 1)[0].split()
                    except UnicodeDecodeError as exc:
                        raise MediaError("Malformed non-ASCII track metadata") from exc
                    fields = {}
                    for token in tokens:
                        key, separator, value = token.partition(":")
                        if not separator or not key or not value or key in fields:
                            raise MediaError("Malformed or duplicate track metadata")
                        fields[key] = value
                    try:
                        number, frames = int(fields["TRACK"]), int(fields["FRAMES"])
                        pregap, postgap = int(fields.get("PREGAP", "0")), int(fields.get("POSTGAP", "0"))
                        kind = fields["TYPE"]
                    except (KeyError, ValueError) as exc:
                        raise MediaError("Malformed track metadata") from exc
                    stored = fields.get("PGTYPE", "").startswith("V")
                    subtype, pgsub = fields.get("SUBTYPE", "NONE"), fields.get("PGSUB", "NONE")
                    pgtype = fields.get("PGTYPE", "")[1:] if stored else ""
                    if subtype not in ("NONE", "RW", "RW_RAW") or pgsub not in ("NONE", "RW", "RW_RAW"):
                        raise MediaError("Unsupported CHD subchannel metadata representation")
                    if stored and pregap and pgsub != "NONE" and pgtype not in ("MODE1", "MODE1_RAW", "AUDIO"):
                        raise MediaError("Captured CHD pregap requires a supported explicit PGTYPE")
                    if (stored and pregap and pgsub != "NONE"
                            and (2048 if pgtype == "MODE1" else 2352) != (2048 if kind == "MODE1" else 2352)):
                        raise MediaError("Captured CHD pregap payload size differs from program track")
                    if number != len(self.tracks)+1 or frames <= 0 or min(pregap, postgap) < 0:
                        raise MediaError("Invalid track ordering or length")
                    if stored and pregap >= frames:
                        raise MediaError("Stored pregap consumes track")
                    # MAME adds virtual gaps to disc time, but only stored gaps
                    # occupy CHD frames. Each track is padded to four frames.
                    index1 = disc_cursor + pregap
                    self.tracks.append(Track(number, kind, frames, pregap, stored, postgap, chd_start, index1,
                                             subtype, pgsub, pgtype))
                    chd_start += (frames + 3) // 4 * 4
                    disc_cursor += frames + postgap + (0 if stored else pregap)
                elif tag == b"CHCD" or tag in (b"CHGT", b"CHGD"):
                    raise MediaError("Legacy/GD-ROM track metadata is unsupported")
                offset = next_offset
        if not self.tracks or chd_start * self.unit_bytes != self.logical_bytes:
            raise MediaError("Track metadata and CHD logical size disagree")
        self._same_source()

    def _same_source(self):
        current = self.path.stat()
        if (current.st_size, current.st_mtime_ns) != self._stamp:
            raise MediaError("CHD source changed after metadata inspection")

    @property
    def has_subchannel(self) -> bool:
        """At least one original RW_RAW extent; not a Q-validity guarantee."""
        self._same_source()
        return any(t.subtype == "RW_RAW" or (t.stored_pregap and t.pregap and t.pregap_subtype == "RW_RAW")
                   for t in self.tracks)

    def report(self, hash_file: bool = False) -> dict:
        result = {"format": "chd-v5", "file_bytes": self.path.stat().st_size,
                  "logical_bytes": self.logical_bytes, "hunk_bytes": self.hunk_bytes,
                  "unit_bytes": self.unit_bytes, "codecs": self.codecs,
                  "raw_sha1_claim": self.raw_sha1, "combined_sha1_claim": self.combined_sha1,
                  "integrity": "metadata only; header SHA1 fields are not verification",
                  "tracks": [asdict(t) | {"index1_frame": t.index1_frame, "data_frames": t.data_frames} for t in self.tracks]}
        if hash_file:
            result["file_sha256"] = sha256(self.path)
        return result


class ChdReader:
    """One open CHD; at most four decompressed hunks retained in memory."""

    def __init__(self, disc: Chd, library: Path):
        self.disc = disc
        self.lib = ctypes.CDLL(str(Path(library).resolve()))
        self.lib.chd_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.chd_open.restype = ctypes.c_int
        self.lib.chd_read.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        self.lib.chd_read.restype = ctypes.c_int
        self.lib.chd_close.argtypes = [ctypes.c_void_p]
        self.lib.chd_close.restype = None
        self.lib.chd_error_string.argtypes = [ctypes.c_int]
        self.lib.chd_error_string.restype = ctypes.c_char_p
        self.handle = ctypes.c_void_p()
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.hunks_read = 0
        self._check(self.lib.chd_open(os.fsencode(disc.path.resolve()), 1, None, ctypes.byref(self.handle)))

    def _check(self, error: int):
        if error:
            raise MediaError(self.lib.chd_error_string(error).decode("utf-8", "replace"))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.handle:
            self.lib.chd_close(self.handle)
            self.handle = ctypes.c_void_p()
        self.cache.clear()

    def frame(self, number: int) -> bytes:
        if not self.handle:
            raise MediaError("CHD reader is closed")
        if not 0 <= number < self.disc.logical_bytes // 2448:
            raise MediaError("CHD frame is outside media")
        hunk, index = divmod(number * 2448, self.disc.hunk_bytes)
        if hunk not in self.cache:
            buffer = ctypes.create_string_buffer(self.disc.hunk_bytes)
            self._check(self.lib.chd_read(self.handle, hunk, buffer))
            self.hunks_read += 1
            self.cache[hunk] = buffer.raw
            if len(self.cache) > 4:
                self.cache.popitem(last=False)
        self.cache.move_to_end(hunk)
        return self.cache[hunk][index:index+2448]

    def sector(self, track: Track, relative_sector: int) -> bytes:
        if not 0 <= relative_sector < track.data_frames:
            raise MediaError("Sector outside track INDEX 01 data")
        raw = self.frame(track.index1_frame + relative_sector)
        if track.type == "MODE1_RAW":
            if raw[:12] != b"\x00" + b"\xff"*10 + b"\x00" or raw[15] != 1:
                raise MediaError("Invalid MODE1 raw sector header")
            return raw[16:2064]
        if track.type == "MODE1":
            return raw[:2048]
        raise MediaError("Only MODE1 and MODE1_RAW user sectors are supported")

    def lba(self, number: int) -> bytes:
        for track in self.disc.tracks:
            if track.disc_start <= number < track.disc_start + track.data_frames:
                return self.sector(track, number - track.disc_start)
        raise MediaError("LBA falls in a gap or outside disc")

    def subchannel(self, number: int) -> bytes | None:
        """Original 96 P-W symbols (bit7=P through bit0=W), or explicit absence.

        Never repairs Q CRC or substitutes TOC data. CHD RW cooked R-W is not
        an established original P-W representation and is refused explicitly.
        Stored pregaps use PGSUB and PGTYPE; virtual gaps/padding are absent.
        """
        if type(number) is not int or not 0 <= number <= 0xFFFFFFFF:
            raise MediaError("Subchannel LBA requires an unsigned 32-bit integer")
        self.disc._same_source()
        if not self.handle:
            raise MediaError("CHD reader is closed")
        for track in self.disc.tracks:
            program = track.disc_start <= number < track.disc_start + track.data_frames
            pregap = track.stored_pregap and track.disc_start - track.pregap <= number < track.disc_start
            if not program and not pregap:
                continue
            representation = track.subtype if program else track.pregap_subtype
            if representation == "NONE":
                return None
            if representation != "RW_RAW":
                raise MediaError("Cooked CHD RW subchannels are unsupported; original RW_RAW P-W is required")
            kind = track.type if program else track.pregap_type
            if kind not in ("MODE1", "MODE1_RAW", "AUDIO"):
                raise MediaError("Unsupported captured CHD payload type")
            frame = self.frame(track.index1_frame + number - track.disc_start)
            offset = 2048 if kind == "MODE1" else 2352
            result = frame[offset:offset+96]
            if len(result) != 96:
                raise MediaError("Truncated captured CHD subchannel frame")
            self.disc._same_source()
            return result
        return None


class IsoReader:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.stat().st_size % 2048:
            raise MediaError("ISO must contain complete 2048-byte sectors")

    def sector(self, number: int) -> bytes:
        if not 0 <= number < self.path.stat().st_size // 2048:
            raise MediaError("Sector outside ISO")
        with self.path.open("rb") as stream:
            stream.seek(number*2048)
            return stream.read(2048)


@dataclass(frozen=True)
class Ipl:
    start_sector: int  # boot-file sector coordinate; track-relative in Ys III
    sector_count: int
    load_address: int
    entry_address: int
    mpr_offsets: tuple[int, ...]
    opening_mode: int
    title: str

    @classmethod
    def parse(cls, sector: bytes):
        if len(sector) != 2048 or sector[32:56] != b"PC Engine CD-ROM SYSTEM\x00":
            raise MediaError("Missing PC Engine IPL signature in the second data sector")
        start = int.from_bytes(sector[:3], "big")
        load, entry = struct.unpack_from("<HH", sector, 4)
        if any(x > 0x7F for x in sector[8:13]):
            raise MediaError("IPL MPR offsets out of supported range")
        title = sector[0x6A:0x8A].split(b"\0", 1)[0].decode("shift_jis", "replace").strip()
        return cls(start, sector[3], load, entry, tuple(sector[8:13]), sector[13], title)

    def report(self):
        return asdict(self) | {"mpr": [0xFF, 0xF8, *[0x80 + x for x in self.mpr_offsets], 0],
                               "mpr7_note": "System Card bank zero assumed for analysis; BIOS not supplied"}
