"""Independent arithmetic and causal payload contracts for active VRAM tests."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from generate_vram_active_fixture import (
    ActiveSlots,authored_fixture,definitions,generate,LINE,FRAME,DATA,DEST,SAT,PAYLOAD,SECOND,TAIL)


class VramActiveFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items,cls.images,cls.sources=authored_fixture()
        cls.cases={case['id']:case for case in cls.items}

    def example(self,divider=4,mwr=0,cells=0):
        case=dict(divider=divider,mwr=mwr,cells=cells,cr=64 if cells else 128,
            sat_sprites=cells//2 if cells>1 else cells,wide=cells>1)
        return ActiveSlots(case,64*LINE)

    def test_meaningful_matrix_has_distinct_bg_sprite_boundary_families(self):
        self.assertEqual(len(definitions()),138)
        self.assertEqual(len({case['id']for case in self.items}),138)
        self.assertEqual([sum(case['family']==family for case in self.items)
            for family in('bg','sprite','boundary')],[72,48,18])
        for case in self.items:
            self.assertEqual(case['cells'],case['sat_sprites']*(2 if case['wide']else 1))
            self.assertEqual(case['steps'],48)

    def test_source_derived_horizontal_windows_do_not_use_observed_phase(self):
        for divider,start,end in((4,128,1152),(3,120,888),(2,64,576)):
            k=self.example(divider)
            self.assertEqual(k.geometry(64*LINE)[3:],(start,end))
            self.assertEqual(k.geometry(64*LINE+end)[2],2)
            self.assertEqual(k.geometry(64*LINE+end-1)[2],1)
            with self.assertRaises(ValueError):k.geometry(100*LINE)

    def test_BG_mwr_residues_use_relative_dot_minus_one(self):
        for mode,allowed in((0,{0,2,4,6}),(1,{2,3}),(2,{2,3}),(3,set())):
            k=self.example(4,mode)
            for relative in range(8):
                ticks=64*LINE+128+(relative+1)*4
                self.assertEqual(k.slot(ticks)[0],relative in allowed)

    def test_BG_slots_apply_when_only_sprite_CR_is_enabled(self):
        k=self.example(4,3,1)
        self.assertEqual(k.slot(64*LINE+300),(False,'background'))

    def test_strict_fetch_end_discontinuity_is_explicit_reference_profile(self):
        k=self.example(4,15,16)
        self.assertEqual(k.slot(64*LINE+1149),(False,'background'))
        self.assertEqual(k.slot(64*LINE+1152),(True,'grant'))
        self.assertEqual(k.slot(64*LINE+1155),(False,'sprite'))

    def test_each_boundary_really_has_three_READY_candidates_and_read_priority(self):
        for case in self.items:
            if case['family']!='boundary':continue
            for profile in('runtime','gear'):
                a,b,c=case['kernel_'+profile]['boundary_candidates']
                self.assertEqual((a['ticks'],c['ticks']),(b['ticks']-3,b['ticks']+3))
                self.assertEqual([item['allowed']for item in(a,b,c)],[False,True,False])
                self.assertTrue(all(item['delay_before']<=3 for item in(a,b,c)))
                self.assertEqual((b['kind'],b['read_pending'],b['write_pending']),('read',1,1))
                self.assertEqual((c['kind'],c['read_pending'],c['write_pending']),('write',0,1))

    def test_real_wide_offscreen_SAT_words_and_payload_hashes(self):
        for case in self.items:
            raw=bytearray(65536)
            for index in range(case['sat_sprites']):
                for offset,value in enumerate((64,0,0,0x2100 if case['wide']else 0x2000)):
                    address=SAT+4*index+offset;raw[2*address:2*address+2]=value.to_bytes(2,'little')
            for address,value in((DATA,PAYLOAD),(DATA+1,SECOND),(DATA+2,TAIL)):
                raw[2*address:2*address+2]=value.to_bytes(2,'little')
            initial_hash=hashlib.sha256(raw).hexdigest()
            expected={'read':0,'write':0xA63E,'dual':0xA63E,'rmw':0x5B3E}[case['access']]
            raw[2*DEST:2*DEST+2]=expected.to_bytes(2,'little')
            for profile in('runtime','gear'):
                self.assertEqual(case['expected_initial_'+profile]['vram_sha256'],initial_hash)
                self.assertEqual(case['expected_'+profile][-1]['vram_sha256'],hashlib.sha256(raw).hexdigest())

    def test_high_port_RMW_snapshots_second_word_before_tail_prefetch(self):
        for case in self.items:
            if case['access']!='rmw':continue
            for profile in('runtime','gear'):
                row=case['expected_'+profile][1]
                read,write=row['mmio_stages']
                self.assertEqual((read['kind'],read['value']),('read-high',0x5A))
                self.assertEqual((write['kind'],write['value']),('write-high',0x5B))
                self.assertEqual(write['before']['read_buffer'],TAIL)
                self.assertEqual(len(row['clock_partition']['wait_runs']),2)
                self.assertLessEqual(read['span_index'],write['span_index'])

    def test_every_port_transition_has_exact_same_tick_causal_stage(self):
        fields={'kind','span_index','before','after','value'}
        for case in self.items:
            for profile in('runtime','gear'):
                for row in case['expected_'+profile]:
                    for stage in row['mmio_stages']:
                        self.assertEqual(set(stage),fields)
                        self.assertEqual(stage['before']['ticks'],stage['after']['ticks'])
                        if stage['kind'].startswith('read'):
                            expected=(stage['before']['read_buffer']>>(8 if stage['kind']=='read-high'else 0))&255
                            self.assertEqual(stage['value'],expected)

    def test_complete_guest_prefix_preserves_raw_CSH_epoch(self):
        for case in self.items:
            runtime=case['kernel_runtime']['absolute_primer_ticks'];gear=case['kernel_gear']['absolute_primer_ticks']
            self.assertEqual(runtime-gear,18 if case['speed']==3 else 0)
            planner=case['planner']
            self.assertEqual(runtime,planner['target_frame']*FRAME+64*LINE+planner['target_hpos'])
            for profile in('runtime','gear'):
                clocks=case['kernel_'+profile]['primer_clocks']
                self.assertEqual(clocks[0]['entry_ticks'],0)
                self.assertEqual(clocks[-1]['after_ticks'],case['kernel_'+profile]['absolute_primer_ticks'])
                self.assertTrue(all(a['after_ticks']==b['entry_ticks']for a,b in zip(clocks,clocks[1:])))

    def test_clock_partitions_preserve_two_RMW_groups_and_zero_controls(self):
        coverage=set()
        for case in self.items:
            for profile in('runtime','gear'):
                coverage.add(case['kernel_'+profile]['coverage']);previous=0
                for row in case['expected_'+profile]:
                    part=row['clock_partition'];extra=3*sum(part['wait_runs'])
                    internal=sum(part['prefix'])+extra+sum(part['suffix'])
                    self.assertEqual(row['extra_ticks'],extra)
                    self.assertEqual(row['internal_clocked_ticks'],internal)
                    self.assertEqual(row['state']['ticks']-previous,internal+part['drain']);previous=row['state']['ticks']
                    self.assertEqual(row['kernel_final']['vram_carry'],0)
        self.assertIn('zero-wait',coverage);self.assertIn('arbitration-denied',coverage)

    def test_full_byte_context_ledgers_cover_primer_and_all_retirements(self):
        for case in self.items:
            for profile in('runtime','gear'):
                ledger=case['source_hits_'+profile]
                self.assertEqual(sum(item['hits']for item in ledger),case['primer_steps']+48)
                for item in ledger:self.assertEqual(item['data'],[self.images[case['id']][i]for i in item['physical']])
                rows=case['expected_'+profile]
                self.assertEqual(rows[-1]['state']['pc'],case['end_pc'])
                self.assertTrue(all(row['irq_count']==0 and row['state']['p']&4 for row in rows))
                self.assertTrue(all(row['wram_sha256']==hashlib.sha256(bytes(8192)).hexdigest()for row in rows))

    def test_authored_export_remains_media_free_and_deterministic(self):
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory);meta=generate(out,emit_module=False)
            self.assertEqual(meta['runtime_abi'],ABI)
            self.assertEqual((out/'authored.bin').read_bytes(),bytes(32768))
            self.assertEqual(len(meta['cases']),138)
            self.assertFalse((out/'module.cpp').exists())
            self.assertIn('VramActiveCase',(out/'vram_active_fixture.hpp').read_text())


if __name__=='__main__':unittest.main()
