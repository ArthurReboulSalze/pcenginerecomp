import unittest
from scripts.vdc_queue_reference import firmware,plans,serialize,slot_literal,validate_records,compare_gear,race_firmware,race_plans,RACE_SPECS

class VdcQueueReferenceTests(unittest.TestCase):
    def test_synthetic_slot_matrix_is_finite(self):
        cases=plans();self.assertEqual(len(cases),615)
        self.assertEqual(sum(c['id'].startswith('actual-cpu')for c in cases),6)
        self.assertIn('q 1',serialize(cases))
    def test_authored_rom_and_reset_vector(self):
        raw,ops=firmware();self.assertEqual(len(raw),262144);self.assertEqual(raw[8190:8192],b'\0\xe1');self.assertGreater(len(ops),40)
    def test_guest_races_cover_speeds_dividers_and_driven_undriven_wrap(self):
        cases=race_plans();self.assertEqual(len(cases),24)
        self.assertEqual(RACE_SPECS,(('read',0x7FFF,32),('read',0xFFFF,128),('write',0x7FFF,64),('write',0xFFFF,32)))
        self.assertEqual({case['operations'][0]for case in cases},{('r',fast,control)for fast in(0,1)for control in range(3)})
        for case in cases:
            self.assertEqual([op[0]for op in case['operations']],['r','x','i','g','i','m'])
            self.assertEqual(sum(op[1]for op in case['operations']if op[0]=='i'),case['race']['steps'])
    def test_dma_and_request_are_guest_encodings_before_the_decisive_cr_write(self):
        raw,programs=race_firmware();self.assertEqual(raw[:0x600],firmware()[0][:0x600])
        for p in programs:
            code=b''.join(p['ops']);offset=p['entry']-0xE000
            self.assertEqual(raw[offset:offset+len(code)],code)
            self.assertIn(bytes.fromhex('03 12 13 FF 23 01'),code) # LENR=511 really starts512 words.
            self.assertEqual(p['ops'][p['prefix']-2:p['prefix']],[b'\x03\x05',b'\x13\0'])
            self.assertEqual(p['ops'][p['prefix']],bytes((0x23,(1,32,64,128).index(p['increment'])<<3)))
            self.assertLess(len(code),256)
    def test_pending_guard_window_record_is_typed_and_bounded(self):
        case=[dict(operations=[('g',)])];row=dict(kind='guard-window',values=[0]*37)
        self.assertEqual(validate_records([row],case),[row])
        for value in(True,-1,1.0,1<<64):
            bad=dict(kind='guard-window',values=[value]+[0]*36)
            with self.subTest(value=value),self.assertRaises(ValueError):validate_records([bad],case)
    def test_blank_and_hsync_literal_slots(self):
        self.assertEqual(slot_literal(('f',96,0,1,0,0,0,0,1365,0,0),0),1)
        self.assertEqual(slot_literal(('f',100,0,1,0,0,0,0,1365,0,0),0),0)
        self.assertEqual(slot_literal(('f',0,0,3,0,0,0,0,1365,0,0),0),0)
    def test_background_modes_and_sprite_window(self):
        self.assertEqual(slot_literal(('f',12,1,1,0,0,0,0,0,1365,0),0),1)
        self.assertEqual(slot_literal(('f',12,1,1,0,3,0,0,0,1365,0),0),0)
        self.assertEqual(slot_literal(('f',4,1,1,0,0,64,2,1365,0,0),0),0)
    def test_invalid_records_reject_boolean_numbers(self):
        with self.assertRaises(ValueError):validate_records([{'kind':'slot','values':[True]}],[{'operations':[('j',3)]}])
    def test_projection_is_restricted_to_named_bus_field_and_has_literal(self):
        case=[dict(id='active-background-0-3',operations=[('s',)])]
        a=dict(kind='device',values=[0]*37);a['values'][11]=44520
        b=dict(kind='device',values=list(a['values']));b['values'][11]=23374
        self.assertEqual(compare_gear([a],[b],case)[0]['field'],'vram_bus_latch')
        b['values'][5]=1
        with self.assertRaises(ValueError):compare_gear([a],[b],case)
        b['values'][5]=0;a['values'][11]=23374
        with self.assertRaises(ValueError):compare_gear([a],[b],case)
