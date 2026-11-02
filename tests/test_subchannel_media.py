"""Authored metadata/storage-order expectations, independent of Q decoding."""
from pathlib import Path
import struct
import tempfile
import unittest

from pcerecomp.media import Chd, ChdReader, MediaError


def metadata(records):
    total = sum((int(row.split("FRAMES:")[1].split()[0])+3)//4*4 for row in records)
    header = bytearray(124)
    header[:8] = b"MComprHD"
    struct.pack_into(">II", header, 8, 124, 5)
    struct.pack_into(">QQQII", header, 32, total*2448, 0, 124, 4*2448, 2448)
    for index, row in enumerate(records):
        text = row.encode("ascii")+b"\0"
        next_offset = len(header)+16+len(text) if index+1 < len(records) else 0
        header.extend(struct.pack(">4sIQ", b"CHT2", len(text), next_offset)+text)
    return header


class CapturedSubchannelMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/"test.chd"

    def tearDown(self):
        self.temp.cleanup()

    def load(self, records):
        self.path.write_bytes(metadata(records))
        return Chd(self.path)

    def reader(self, disc):
        result = ChdReader.__new__(ChdReader)
        result.disc, result.handle = disc, True
        self.frames = {}
        self.queried = []
        def frame(number):
            self.queried.append(number)
            return self.frames[number]
        result.frame = frame
        return result

    def test_raw_metadata_visible_in_report_and_capability(self):
        disc = self.load(["TRACK:1 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:3 PREGAP:0 PGTYPE:AUDIO PGSUB:NONE POSTGAP:0"])
        self.assertTrue(disc.has_subchannel)
        self.assertEqual(disc.report()["tracks"][0]["subtype"], "RW_RAW")

    def test_original_symbols_and_payload_offsets(self):
        for kind, offset in (("MODE1", 2048), ("MODE1_RAW", 2352), ("AUDIO", 2352)):
            with self.subTest(kind=kind):
                disc = self.load([f"TRACK:1 TYPE:{kind} SUBTYPE:RW_RAW FRAMES:3"])
                reader = self.reader(disc)
                original = bytes((i*17+31) % 256 for i in range(96))
                frame = bytearray([0xED]*2448)
                frame[offset:offset+96] = original
                self.frames[1] = bytes(frame)
                self.assertEqual(reader.subchannel(1), original)
                self.assertEqual(self.queried, [1])

    def test_none_does_not_decode_or_synthesize(self):
        disc = self.load(["TRACK:1 TYPE:MODE1 SUBTYPE:NONE FRAMES:3"])
        reader = self.reader(disc)
        self.assertFalse(disc.has_subchannel)
        for lba in (0, 2, 3, 0xFFFFFFFF):
            self.assertIsNone(reader.subchannel(lba))
        self.assertEqual(self.queried, [])

    def test_cooked_rw_is_not_original_pq(self):
        disc = self.load(["TRACK:1 TYPE:AUDIO SUBTYPE:RW FRAMES:3"])
        self.assertFalse(disc.has_subchannel)
        reader = self.reader(disc)
        with self.assertRaisesRegex(MediaError, "Cooked"):
            reader.subchannel(0)
        self.assertEqual(self.queried, [])

    def test_padding_virtual_and_stored_pregaps(self):
        disc = self.load([
            "TRACK:1 TYPE:MODE1 SUBTYPE:NONE FRAMES:3 PREGAP:0 PGTYPE:MODE1 PGSUB:NONE POSTGAP:1",
            "TRACK:2 TYPE:MODE1_RAW SUBTYPE:NONE FRAMES:5 PREGAP:2 PGTYPE:VAUDIO PGSUB:RW_RAW POSTGAP:0",
            "TRACK:3 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:2 PGTYPE:AUDIO PGSUB:RW_RAW POSTGAP:0"])
        self.assertTrue(disc.has_subchannel)
        reader = self.reader(disc)
        for lba, frame_number in ((4, 4), (5, 5)):
            original = bytes([lba]*96)
            self.frames[frame_number] = bytes(2352)+original
            self.assertEqual(reader.subchannel(lba), original)
        for lba in (0, 3, 6, 8, 9, 10, 11, 13, 14, 0xFFFFFFFF):
            self.assertIsNone(reader.subchannel(lba))
        self.assertEqual(self.queried, [4, 5])
        report = disc.report()["tracks"][1]
        self.assertEqual((report["pregap_subtype"], report["pregap_type"]), ("RW_RAW", "AUDIO"))

    def test_unknown_and_ambiguous_pregap_representation_refused(self):
        for row in (
            "TRACK:1 TYPE:AUDIO SUBTYPE:ALIEN FRAMES:3",
            "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PGSUB:ALIEN",
            "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:V PGSUB:RW_RAW",
            "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VMODE2 PGSUB:RW_RAW",
            "TRACK:1 TYPE:AUDIO SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VMODE1 PGSUB:RW_RAW",
            "TRACK:1 TYPE:MODE1 SUBTYPE:NONE FRAMES:3 PREGAP:1 PGTYPE:VAUDIO PGSUB:RW_RAW"):
            with self.subTest(row=row), self.assertRaises(MediaError):
                self.load([row])

    def test_duplicate_and_malformed_metadata_cannot_declare_capture(self):
        for row in (
            "TRACK:1 TYPE:AUDIO SUBTYPE:NONE SUBTYPE:RW_RAW FRAMES:3",
            "TRACK:1 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:3 garbage",
            "TRACK:1 TYPE:AUDIO SUBTYPE: FRAMES:3",
        ):
            with self.subTest(row=row), self.assertRaisesRegex(MediaError, "metadata"):
                self.load([row])

    def test_source_drift_refused_even_when_query_would_be_absent(self):
        disc = self.load(["TRACK:1 TYPE:AUDIO SUBTYPE:RW_RAW FRAMES:3"])
        reader = self.reader(disc)
        self.path.write_bytes(self.path.read_bytes()+b"x")
        with self.assertRaisesRegex(MediaError, "changed"):
            _ = disc.has_subchannel
        for lba in (0, 0xFFFFFFFF):
            with self.assertRaisesRegex(MediaError, "changed"):
                reader.subchannel(lba)

    def test_zero_packet_preserved_closed_and_typed_lba_refused(self):
        disc = self.load(["TRACK:1 TYPE:MODE1 SUBTYPE:RW_RAW FRAMES:3"])
        reader = self.reader(disc)
        self.frames[0] = bytes(2448)
        self.assertEqual(reader.subchannel(0), bytes(96))
        for value in (True, False, -1, 1.0, "0", 0x100000000):
            with self.assertRaisesRegex(MediaError, "unsigned"):
                reader.subchannel(value)
        reader.handle = None
        with self.assertRaisesRegex(MediaError, "closed"):
            reader.subchannel(0)

    def test_decoder_error_and_short_frame_are_not_absence(self):
        disc = self.load(["TRACK:1 TYPE:MODE1_RAW SUBTYPE:RW_RAW FRAMES:3"])
        reader = self.reader(disc)
        self.frames[0] = bytes(2352)
        with self.assertRaisesRegex(MediaError, "Truncated"):
            reader.subchannel(0)
        def fault(_):
            raise MediaError("authored decoder failure")
        reader.frame = fault
        with self.assertRaisesRegex(MediaError, "decoder failure"):
            reader.subchannel(0)


if __name__ == "__main__":
    unittest.main()
