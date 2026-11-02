import unittest
from scripts import subchannel_reference as reference


class SubchannelReferenceTests(unittest.TestCase):
    def test_known_complement_crc_literal(self):
        self.assertEqual(reference.packet(bytes(10)),bytes(10)+b'\xff\xff')
        self.assertTrue(reference.valid(bytes(10)+b'\xff\xff'))
        self.assertFalse(reference.valid(bytes(12)))

    def test_bit_lane_not_channel_major(self):
        q=bytes.fromhex('814224188142241881422418')
        raw=reference.raw96(q,0xff)
        self.assertEqual(reference.extract(raw),q)
        self.assertEqual([bool(b&64)for b in raw[:8]],[True,False,False,False,False,False,False,True])
        self.assertEqual(reference.extract(reference.raw96(q,0)),q)

    def test_valid_other_adr_preserves_position(self):
        q1=reference.packet(bytes.fromhex('41090003124500112233'))
        q2=reference.packet(bytes.fromhex('42080004135600223344'))
        _,beetle=reference.expected([('r',),('q',2,reference.raw96(q1)),('q',1,reference.raw96(q2))])
        row=beetle[-1]
        self.assertEqual(row[13:25],list(q2))
        self.assertEqual(row[25:37],list(q1))
        self.assertEqual(row[37:],[2,0,9,0,3,0x12,0x45,0x11,0x22,0x33])

    def test_invalid_crc_preserves_both_latches(self):
        q=reference.packet(bytes.fromhex('41090103124500112233'))
        _,rows=reference.expected([('r',),('q',2,reference.raw96(q)),('q',0,bytes(96))])
        self.assertEqual(rows[-1][0],0)
        self.assertEqual(rows[-1][13:25],list(q))
        self.assertEqual(rows[-1][25:37],list(q))
        self.assertEqual(rows[-1][37:39],[3,0])

    def test_declared_fixture_extent_and_reset(self):
        gear,beetle=reference.expected(reference.plans())
        self.assertEqual(len(gear),len(beetle))
        self.assertEqual(len(gear),315)
        self.assertEqual(beetle[-1][13:37],[0]*24)
        self.assertEqual(beetle[-1][37:],[3]+[0]*9)
        self.assertTrue(all(len(row)==47 for row in beetle))


if __name__=='__main__':unittest.main()
