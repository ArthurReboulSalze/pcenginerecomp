import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from pcerecomp.abi import ABI
from tests.dma_irq_checkpoint_fixture import cases,program,pattern,expected_ram,MPR
from scripts.dma_irq_checkpoint_reference import validate_hits,validate_work,validate_observation,raw_differences,source_key,expected_stack,validate_report,validate_capture,requested_tier
from scripts.dma_irq_checkpoint_qualify import load,validate_stderr,full_hits

class DmaIrqCheckpointTests(unittest.TestCase):
    def masked_report(self):
        # Minimal authored admission data; full autonomy's one-shot ledger is separately checked by full_hits.
        c=cases()[2];_,m,plan=program(c);zero=hashlib.sha256(bytes(8192)).hexdigest()
        initial=dict(values=[m['post_dma'],0,255,0,255,3,3,24,0,0,7,1,12,12,0xd8,0,2048,2046,1,1,2048,0,1],stack=[0]*256,wram_sha256=zero)
        final=dict(values=[m['done'],0,255,0,255,7,3,39,0,0,7,0,0,12,0,0,2048,2046,1,1,2048,0,0],stack=[0]*256,wram_sha256=zero)
        before=dict(plan[0],hits=1);after=dict(next(s for s in plan if s['pc']==m['done']-3),hits=1)
        work=lambda ticks:dict(instructions=1,calls=1,clock_calls=0,clock_ticks=ticks,irqs=0,rtis=0)
        record={k:v for k,v in after.items()if k not in('data','hits')};record.update(bytes=after['data'],ticks=15,vector=0,after=final)
        r=dict(case=c['id'],cut_id=1,tier='native',cut=initial,final=final,prefix_work=work(24),window_work=work(15),prefix_hits=[before],window_hits=[after],prefix_journal=[],journal=[record],ram=expected_ram(),dma_counter_role='captured-bytes',mode='write',runtime_abi=ABI,prefix_native=1,prefix_interpreted=0,window_native=1,window_interpreted=0,guard_misses=0,provider_prefix=1,provider_suffix=0,origin_frame=0,checkpoint_sha256='0'*64,final_sha256='1'*64)
        cap=dict(schema=1,runtime_abi=ABI,capacity=4,dropped_instructions=0,unreadable_instructions=0,retired_instructions=1,complete=True,observations=[dict({k:v for k,v in after.items()if k!='hits'},native_hits=1,interpreted_hits=0)])
        return c,r,cap
    def test_twenty_authored_recipes_two_real_boundary_roles(self):
        matrix=cases();self.assertEqual(len(matrix),20);self.assertEqual(len({c['id']for c in matrix}),20)
        self.assertEqual(sum(c['kind']in('cpu-ack','cd-ack')for c in matrix),8)
        for c in matrix:
            rom,markers,plan=program(c);self.assertEqual(len(rom),262144);self.assertLess(markers['pre_cli'],markers['post_dma']);self.assertLess(markers['post_dma'],markers['done']);self.assertEqual(rom[0x1ff6:0x1ff8],b'\x00\xf8')
            self.assertTrue(all(bytes(rom[p]for p in s['physical'])==bytes(s['data'])for s in plan))
    def test_independent_entire_ram_pattern_wraps(self):
        ram=expected_ram();self.assertEqual(len(ram),65536);self.assertEqual(ram[65534:],pattern()[:2]);self.assertEqual(ram[:2046],pattern()[2:]);self.assertEqual(ram[2046:65534],[0]*63488)
    def test_actual_source_identity_all_mapping_and_bytes(self):
        c=cases()[0];r=dict(program(c)[2][-1],hits=1);self.assertEqual(sum(validate_hits([r],c).values()),1)
        for field in('pc','hits'):
            bad=copy.deepcopy(r);bad[field]=True
            with self.assertRaises(ValueError):validate_hits([bad],c)
        for field in('mpr','physical','data'):
            bad=copy.deepcopy(r);bad[field][0]^=1
            with self.assertRaises(ValueError):validate_hits([bad],c)
        bad=copy.deepcopy(r);bad['mpr'][0]=True
        with self.assertRaises(ValueError):validate_hits([bad],c)
        with self.assertRaises(ValueError):validate_hits([r,r],c)
    def test_independent_autonomous_one_shot_port_counts(self):
        for c in cases():
            _,markers,plan=program(c);rows=[dict(s,hits=1)for s in plan if s['pc']!=markers['done']and(s['pc']<0xf800 or c['kind']in('cpu-ack','cd-ack'))]
            self.assertTrue(full_hits(rows,[],c))
            bad=copy.deepcopy(rows);next(r for r in bad if r['data']==[0x8d,1,24])['hits']=2
            with self.assertRaises(ValueError):full_hits(bad,[],c)
    def test_counter_bool_extra_and_missing_fields_refused(self):
        c=cases()[0];r=dict(program(c)[2][0],hits=1);hits=validate_hits([r],c);w=dict(instructions=1,calls=1,clock_calls=1,clock_ticks=24,irqs=0,rtis=0);validate_work(w,hits,24,True)
        for key in w:
            bad=dict(w);bad[key]=True
            with self.assertRaises(ValueError):validate_work(bad,hits,24,True)
        bad=dict(w,extra=0)
        with self.assertRaises(ValueError):validate_work(bad,hits,24,True)
    def test_observation_requires_exact_typed_extent(self):
        values=[0]*23;values[6]=3;o=dict(values=values,stack=[0]*256,wram_sha256='0'*64);validate_observation(o)
        for where in('values','stack'):
            bad=copy.deepcopy(o);bad[where][0]=False
            with self.assertRaises(ValueError):validate_observation(bad)
        bad=dict(o,extra=0)
        with self.assertRaises(ValueError):validate_observation(bad)
    def test_cli_delayed_return_and_saved_status_are_independent(self):
        c=cases()[0];v=[0]*23;v[1]=0xc8;frame=expected_stack(c,dict(after=dict(values=v)));pc=program(c)[1]['pre_cli']+4
        self.assertEqual(frame[252:],[0xc8,0x81,pc&255,pc>>8]);self.assertEqual(frame[:252],[0]*252)
    def test_raw_counter_roles_and_clock_difference_are_retained(self):
        c=cases()[0];base=dict(cut=dict(values=[0]*23),final=dict(values=[0]*23),prefix_work=dict(calls=0),window_work=dict(calls=0));a=copy.deepcopy(base);b=copy.deepcopy(base);a['dma_counter_role']='committed-writes';b['dma_counter_role']='captured-bytes';a['cut']['values'][7]=21;b['cut']['values'][20]=1
        rows=raw_differences(a,b,c,0);self.assertEqual(len(rows),2);counter=next(r for r in rows if r['field']=='dma_counter');self.assertEqual(counter['original_role'],'committed-writes');self.assertEqual(counter['tool_role'],'captured-bytes')
    def test_duplicate_and_nonfinite_receipts_refused(self):
        with TemporaryDirectory()as folder:
            p=Path(folder)/'r.json'
            for text in('{"x":1,"x":2}','{"x":NaN}'):
                p.write_text(text)
                with self.assertRaises(ValueError):load(p)
    def test_build_warnings_are_separate_from_guest_stderr(self):
        validate_stderr('tool-configure','CMake warning')
        with self.assertRaises(ValueError):validate_stderr('cpu-ack-mode1-div3-cut0-gear','unexpected')
    def test_complete_report_capture_admission_and_mutations(self):
        c,r,cap=self.masked_report();validate_report(r,c,1);validate_capture(cap,r,c);requested_tier(r,'native')
        for field in('cut_id','prefix_native','provider_prefix','origin_frame'):
            bad=copy.deepcopy(r);bad[field]=True
            with self.assertRaises(ValueError):validate_report(bad,c,1)
        bad=copy.deepcopy(r);bad['cut']['values'][0]+=1
        with self.assertRaises(ValueError):validate_report(bad,c,1)
        bad=copy.deepcopy(r);bad['journal']=[]
        with self.assertRaises(ValueError):validate_report(bad,c,1)
        bad=copy.deepcopy(r);bad['tier']='interpreter';bad['prefix_native']=bad['window_native']=0;bad['prefix_interpreted']=bad['window_interpreted']=1
        validate_report(bad,c,1)
        with self.assertRaises(ValueError):requested_tier(bad,'native')
        for mutate in(lambda x:x.update(retired_instructions=True),lambda x:x['observations'][0]['mpr'].__setitem__(0,True),lambda x:x['observations'][0].update(native_hits=True)):
            bad=copy.deepcopy(cap);mutate(bad)
            with self.assertRaises(ValueError):validate_capture(bad,r,c)
    def test_handler_cut_full_p_is_checked_before_journal_join(self):
        _,r,_=self.masked_report();c=cases()[0];_,m,_=program(c);r.update(case=c['id']);r['cut']['values']=[0xf800,0xc8,255,0,252,0xc5,3,24,1,0,6,1,12,12,0x8a,1,1,65535,1,1,1,0,1]
        with self.assertRaisesRegex(ValueError,'complete handler-cut P'):validate_report(r,c,1)

if __name__=='__main__':unittest.main()
