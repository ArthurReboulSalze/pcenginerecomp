"""Independent arithmetic, payload, source and IRQ contracts for stall fixtures."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from generate_irq_stall_fixture import (
    authored_fixture,generate,BlankSlots,PAYLOAD,TAIL,DMA_DEST)


class IrqStallFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items,cls.images,cls.sources=authored_fixture()
        cls.cases={case['id']:case for case in cls.items}

    def example(self,divider,words=2,profile='runtime'):
        case=dict(divider=divider,words=words,first_phase=False,sources=3)
        clock=dict(dma_start=0,prefetch_issue=0,ticks=0,first_de_arm=0)
        return BlankSlots(case,clock,profile)

    def test_line_tail_does_not_invent_a_partial_dot(self):
        for divider,last,count in((4,1364,341),(3,1365,455),(2,1364,682)):
            k=self.example(divider)
            self.assertEqual(k.dots(last),count)
            self.assertEqual(k.dots(1365),count)
            self.assertEqual(k.dots(1365+divider),count+1)

    def test_DMA_completion_and_queue_grant_use_distinct_phases(self):
        # Two words require eight dots. CPU requests test the old dot parity
        # before advancing the next three ticks; HSW blocks its first 8 dots.
        for divider,dma_end,grant in((4,32,36),(3,24,27),(2,16,24)):
            k=self.example(divider);self.assertEqual(k.dma_dot_end,dma_end)
            k.advance(grant-3);self.assertTrue(k.pending)
            k.advance(grant);self.assertFalse(k.pending)
            self.assertEqual(k.grants[-1]['visible_ticks'],grant)
            self.assertGreater(k.grants[-1]['test_ticks'],dma_end-1)
            self.assertEqual(k.buffer,PAYLOAD)

    def test_ACK_release_arms_at_port_or_first_queued_clock(self):
        for profile,armed,request in(('runtime',0,900),('gear',3,903)):
            k=self.example(4,256,profile);k.write_cd(64);k.advance(903)
            arm=next(e for e in k.events if e['kind']=='cd-next-armed')
            edge=next(e for e in k.events if e['kind']=='cd-request')
            self.assertEqual((arm['ticks'],edge['ticks']),(armed,request))
            self.assertTrue(k.pending)
            self.assertEqual(k.requests(),1)

    def test_real_modes_lengths_and_source_edges_are_inside_stall(self):
        self.assertEqual(len(self.items),78)
        for case in self.items:
            self.assertEqual(case['words'],2048 if case['first_phase']else 256)
            self.assertIn(case['divider'],(4,3,2))
            for profile in('runtime','gear'):
                witness=case['kernel_'+profile];row=case['expected_'+profile][2]
                self.assertGreater(row['extra_ticks'],900)
                self.assertEqual(row['extra_ticks']%3,0)
                self.assertEqual(row['kernel_entry']['read_buffer'],TAIL)
                for kind,bit in(('dma-complete',2),('cd-request',1)):
                    if not case['sources']&bit:continue
                    event=next(e for e in witness['events']if e['kind']==kind)
                    self.assertLess(witness['dynamic_start_ticks'],event['ticks'])
                    self.assertLess(event['ticks'],witness['dynamic_end_ticks'])

    def test_known_source_and_last_destination_word_have_independent_hashes(self):
        for case in self.items:
            initial=bytearray(65536);final=bytearray(65536)
            for address,value in((0,PAYLOAD),(case['words']-1,TAIL),(DMA_DEST,PAYLOAD)):
                initial[2*address:2*address+2]=value.to_bytes(2,'little')
            final[:]=initial
            last=DMA_DEST+case['words']-1;final[2*last:2*last+2]=TAIL.to_bytes(2,'little')
            for profile in('runtime','gear'):
                self.assertEqual(case['expected_initial_'+profile]['vram_sha256'],hashlib.sha256(initial).hexdigest())
                self.assertEqual(case['expected_'+profile][-1]['vram_sha256'],hashlib.sha256(final).hexdigest())

    def test_independent_cpu_mask_priority_and_payload_expectations(self):
        for label in('low','high'):
            for divider in(4,3,2):
                for mask,wanted in((0,0xFFF8),(1,0xFFF8),(2,0xFFF6),(3,None)):
                    case=self.cases[f'read-mask{mask}-{label}-vce{divider}']
                    row=case['expected_runtime'][2]
                    self.assertEqual(row['irq_vector'],wanted)
                    self.assertEqual(row['state']['a'],0x5C)
                high=self.cases[f'read-high-{label}-vce{divider}']['expected_runtime'][2]
                self.assertEqual(high['state']['a'],0xA6)
                masked=self.cases[f'I-masked-{label}-vce{divider}']['expected_runtime']
                self.assertTrue(all(row['irq_count']==0 for row in masked))

    def test_absolute_primer_and_instruction_clock_partitions_remain_raw(self):
        for case in self.items:
            runtime=case['kernel_runtime']['absolute_primer_ticks']
            gear=case['kernel_gear']['absolute_primer_ticks']
            self.assertEqual(runtime-gear,18 if case['speed']==3 else 0)
            for profile in('runtime','gear'):
                previous=0
                for row in case['expected_'+profile]:
                    part=row['clock_partition']
                    internal=sum(part['prefix'])+3*part['stall_count']+sum(part['suffix'])
                    self.assertEqual(internal,row['internal_clocked_ticks'])
                    self.assertEqual(internal+part['drain'],row['state']['ticks']-previous)
                    self.assertEqual(row['extra_ticks'],3*part['stall_count'])
                    self.assertEqual(row['irq_return_pc']is not None,bool(row['irq_count']))
                    previous=row['state']['ticks']

    def test_full_source_identity_ledgers_cover_real_primers_and_loop(self):
        for case in self.items:
            raw=self.images[case['id']]
            for profile in('runtime','gear'):
                ledger=case['source_hits_'+profile]
                self.assertEqual(sum(item['hits']for item in ledger),case['primer_steps']+48)
                for item in ledger:
                    self.assertEqual(item['data'],[raw[address]for address in item['physical']])
                self.assertEqual(case['expected_'+profile][-1]['state']['pc'],case['end_pc'])
            self.assertEqual(case['initial']['wram_sha256'],hashlib.sha256(bytes(8192)).hexdigest())

    def test_authored_media_and_export_metadata_close_without_a_reference_core(self):
        with tempfile.TemporaryDirectory()as directory:
            out=Path(directory);metadata=generate(out,emit_module=False)
            self.assertEqual(metadata['runtime_abi'],ABI)
            self.assertEqual((out/'authored.bin').read_bytes(),bytes(16*2048))
            self.assertEqual(metadata['vram_encoding'],'32768 words serialized low-byte then high-byte; 65536 bytes')
            for case in metadata['cases']:
                self.assertEqual(hashlib.sha256((out/case['rom']).read_bytes()).hexdigest(),case['rom_sha256'])
            self.assertFalse((out/'module.cpp').exists())


if __name__=='__main__':unittest.main()
