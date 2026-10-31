"""Independent literal contracts for original guest-only device IRQ programs."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from generate_irq_device_fixture import authored_fixture, generate, LITERAL_COLUMNS


class IrqDeviceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.images, cls.sources = authored_fixture()
        cls.cases = {item['id']:item for item in cls.items}

    def test_all_masks_at_both_speeds_choose_independent_priority(self):
        expected = [0xFFFA,0xFFFA,0xFFFA,0xFFFA,0xFFF8,0xFFF8,0xFFF6,None]
        for speed in ('low','high'):
            for mask, vector in enumerate(expected):
                case = self.cases[f'priority-mask{mask}-{speed}']
                first = case['expected_runtime'][1]
                self.assertEqual(first['irq_vector'],vector)
                self.assertEqual(case['initial']['values'][20:23],[1,mask,0])
                self.assertEqual(case['initial']['values'][26:35],[7,16,64,64,0,200,4,1,1])
        self.assertEqual(len(self.items),44)
        self.assertEqual(len(LITERAL_COLUMNS),39)
        self.assertEqual(len(set(LITERAL_COLUMNS)),39)

    def test_priority_chain_exact_stack_return_addresses_and_live_levels(self):
        case = self.cases['priority-mask0-low'];rows = case['expected_runtime']
        entries = [row for row in rows if row['irq_count']]
        self.assertEqual([(r['ordinal'],r['irq_vector'],r['irq_return_pc'])for r in entries],
                         [(2,0xFFFA,0xE188),(7,0xFFF8,0xE189),(11,0xFFF6,0xE18A)])
        self.assertEqual(entries[0]['values'][:8],[0xF800,1,0,0,252,4,12,144])
        ram = bytearray(8192);ram[0x1FF]=0xE1;ram[0x1FE]=0x88
        self.assertEqual(entries[0]['wram_sha256'],hashlib.sha256(ram).hexdigest())
        self.assertEqual(entries[0]['values'][26:35],[7,16,64,64,0,200,4,1,1])
        self.assertEqual(rows[-1]['values'][23:30],[1,1,1,0,0,0,0])
        self.assertEqual(rows[-1]['values'][30:35],[1,138,4,1,1])

    def test_VDC_read_and_RMW_resampling_have_exact_distinct_contracts(self):
        for label, divisor in (('low',12),('high',3)):
            queued=self.cases['vdc-queued-retain-'+label]['expected_runtime'][1]
            immediate=self.cases['vdc-immediate-cancel-'+label]
            fixed=immediate['expected_runtime'][1]; original=immediate['expected_gear'][1]
            rmw=self.cases['vdc-rmw-cancel-'+label]['expected_runtime'][1]
            self.assertEqual((queued['irq_vector'],queued['values'][7]),(0xFFF8,16*divisor))
            self.assertEqual((fixed['irq_vector'],fixed['values'][7]),(None,8*divisor))
            self.assertEqual((original['irq_vector'],original['values'][7]),(0xFFF8,16*divisor))
            self.assertEqual((rmw['irq_vector'],rmw['values'][7]),(None,11*divisor))
            self.assertEqual([r['fixed_wait_count']for r in(queued,fixed,rmw)],[1,1,2])
            self.assertEqual([r['values'][27]for r in(queued,fixed,rmw)],[0,0,0])
            self.assertNotEqual(immediate['source_hits_runtime'],immediate['source_hits_gear'])

    def test_CD_ack_disable_reset_and_status_read_do_not_forge_an_idle_bus(self):
        for label in ('low','high'):
            ack=self.cases['cd-ack-retain-'+label]['expected_runtime'][1]
            disabled=self.cases['cd-disable-retain-'+label]['expected_runtime'][1]
            reset=self.cases['cd-reset-retain-'+label]['expected_runtime'][1]
            status=self.cases['cd-status-not-ack-'+label]['expected_runtime'][1]
            for row in(ack,disabled,reset,status):self.assertEqual(row['irq_vector'],0xFFF6)
            self.assertEqual(ack['values'][28:35],[64,0,1,138,4,1,1])
            self.assertEqual(disabled['values'][28:35],[0,64,0,200,4,1,1])
            self.assertEqual(reset['values'][28:35],[64,0,0,256,0,0,0])
            self.assertEqual(status['state']['a'],0x52)
            self.assertEqual(status['values'][28:35],[64,64,0,200,4,1,1])

    def test_timer_ack_fallback_and_source_held_across_RTI(self):
        for label in ('low','high'):
            fallback=self.cases['timer-ack-fallback-'+label]['expected_runtime'][1]
            self.assertEqual((fallback['irq_vector'],fallback['values'][20],fallback['values'][26]),(0xFFF8,0,3))
            for name,vector,cell in(('held-irq1-rti',0xFFF8,24),('held-irq2-rti',0xFFF6,25)):
                rows=self.cases[name+'-'+label]['expected_runtime']
                self.assertEqual([(r['ordinal'],r['irq_vector'])for r in rows if r['irq_count']],[(2,vector),(8,vector)])
                self.assertEqual(rows[-1]['values'][cell],2)

    def test_status_phase_is_real_IRQ20_and_mapping_wrap_is_independent(self):
        for label in ('low','high'):
            initial=self.cases['cd-status-phase-'+label]['initial']
            self.assertEqual(initial['values'][28:35],[32,32,0,216,7,0,0])
            case=self.cases['priority-remap-'+label];entry=case['expected_runtime'][1]
            self.assertEqual((entry['state']['pc'],entry['state']['physical_pc'],entry['state']['sp']),(0xF900,0x3900,254))
            ram=bytearray(8192);ram[0x101]=case['marker']>>8;ram[0x100]=(case['marker']+2)&255
            self.assertEqual(entry['wram_sha256'],hashlib.sha256(ram).hexdigest())

    def test_every_profile_has_exact_byte_aware_source_and_retirement_ledgers(self):
        for case in self.items:
            image=self.images[case['id']]
            self.assertEqual(int.from_bytes(image[8190:8192],'little'),0xE000)
            self.assertEqual(case['initial']['wram_sha256'],hashlib.sha256(bytes(8192)).hexdigest())
            for profile in('runtime','gear'):
                self.assertEqual(sum(x['hits']for x in case['source_hits_'+profile]),case['primer_steps']+48)
                for item in case['source_hits_'+profile]:
                    self.assertEqual(item['data'],[image[p]for p in item['physical']])
                for row in case['expected_'+profile]:
                    self.assertEqual(row['irq_return_pc']is not None,bool(row['irq_count']))
                    self.assertEqual(row['internal_clocked_ticks'],row['fixed_wait_count']*case['speed'])
                self.assertEqual(case['expected_'+profile][-1]['state']['pc'],case['end_pc'])

    def test_generated_media_and_BIOS_hashes_are_authored_and_complete(self):
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory);manifest=generate(out,emit_module=False)
            self.assertEqual(manifest['runtime_abi'],ABI)
            self.assertEqual((out/'authored.bin').read_bytes(),bytes(16*2048))
            self.assertEqual(manifest['cue'],'authored.cue')
            for item in manifest['media_files']:
                raw=(out/item['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
            for case in manifest['cases']:
                self.assertEqual(hashlib.sha256((out/case['rom']).read_bytes()).hexdigest(),case['rom_sha256'])
            self.assertFalse((out/'module.cpp').exists())


if __name__=='__main__':unittest.main()
