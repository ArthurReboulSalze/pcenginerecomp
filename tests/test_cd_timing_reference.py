"""Independent literal arithmetic and adversarial observation admission tests."""
import copy
import unittest
from scripts.cd_timing_reference import seek_ms,seek_ticks,math_vectors,cases,GROUPS
from scripts.cd_timing_qualify import integer,validate_admission,validate_reset,validate_initial_error,validate_latch

class CdTimingReferenceTests(unittest.TestCase):
    def test_literal_seek_boundaries(self):
        for target,ms,ticks in((0,150,3221590),(1,150,3221590),(2,216,4639090),(4,216,4639090),(5,366,7860681),(809,366,7860681),(810,432,9278181),(1609,432,9278181),(1610,432,9278181),(6449,533,11447386),(6450,800,17181818),(333012,2508,53865000)):
            with self.subTest(target=target):self.assertEqual((seek_ms(0,target),seek_ticks(0,target)),(ms,ticks))
    def test_direction_uses_target_rotation(self):
        self.assertEqual(seek_ms(12571,12574),223)
        self.assertEqual(seek_ms(12574,12571),216)
    def test_domain_and_type_are_explicit(self):
        for pair in((False,0),(0,True),(-1,0),(0,333013),(4294967295,0)):
            with self.subTest(pair=pair),self.assertRaises(ValueError):seek_ticks(*pair)
    def test_finite_vectors_and_authored_scenario_scope(self):
        vectors=math_vectors();self.assertGreaterEqual(len(vectors),9480);self.assertEqual(len(vectors),len(set(vectors)))
        for a,b in((0,0),(0,4),(0,5),(0,333012),(333012,0),(12572,12573),(12573,12572)):self.assertIn((a,b),vectors)
        for width,first,last,_ in GROUPS:
            for tracks in(80,81,160,161,644,645):
                target=first+tracks*width
                if target<=last:self.assertIn((first,target),vectors);self.assertIn((target,first),vectors)
        definitions=cases();self.assertEqual(len({c['id']for c in definitions}),len(definitions));self.assertTrue(any(c['profile']=='fixed'for c in definitions))
    def test_typed_counter_refuses_boolean(self):
        with self.assertRaises(ValueError):integer(False)
    def point(self):
        return dict(kind='admission',op=8,mode=0,lba=5,count=1,head_before=0,ack_entry=100,after=116),dict(ticks=116,load=8147144,seek=0,play=0,logical=[1,0,0,0,0,0,0,0,0,0,0])
    def test_exact_original_deadline_with_bounded_dispatch_phase(self):
        row,state=self.point();validate_admission(row,state,'gear-distance')
        state['load']+=500
        with self.assertRaises(ValueError):validate_admission(row,state,'gear-distance')
    def test_read_issue_must_not_advance_head(self):
        row,state=self.point();state['logical'][6]=1
        with self.assertRaises(ValueError):validate_admission(row,state,'gear-distance')
    def test_split_ack_and_playback_are_distinct(self):
        row,state=self.point();row.update(op=0xd8,lba=5,mode=1);state.update(load=0,seek=3049872,play=7860781,logical=[0,5,5,13999,0,0,5,0,0,0,0]);validate_admission(row,state,'gear-distance')
        state['play']=state['seek']
        with self.assertRaises(ValueError):validate_admission(row,state,'gear-distance')
    def test_exact_reset_reference_disagreement_is_positive_evidence(self):
        point=lambda t,s,p:dict(ticks=t,seek=s,play=p,load=0,phase=0,signals=0,logical=[0]*11)
        gear=dict(seeking=point(100,1000,1500),reset=point(200,1000,0),later=point(2000,0,0));gear['reset']['logical'][0]=gear['later']['logical'][0]=3;tool=copy.deepcopy(gear);tool['reset']['seek']=0
        validate_reset(gear,'gear');validate_reset(tool,'native')
        with self.assertRaises(ValueError):validate_reset(tool,'gear')
        with self.assertRaises(ValueError):validate_reset(gear,'native')
        for field,value in(('play',500),('load',500),('phase',8),('signals',128)):
            changed=copy.deepcopy(gear);changed['reset'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_reset(changed,'gear')
        for index in range(11):
            changed=copy.deepcopy(gear);changed['reset']['logical'][index]^=1
            with self.subTest(index=index),self.assertRaises(ValueError):validate_reset(changed,'gear')
    def test_invalid_read_retains_distinct_exact_reset_states(self):
        point=lambda state:dict(logical=[state]+[0]*10,seek=0,play=0,load=0)
        validate_initial_error([point(3)],'gear');validate_initial_error([point(1)],'native')
        with self.assertRaises(ValueError):validate_initial_error([point(1)],'gear')
        with self.assertRaises(ValueError):validate_initial_error([point(3)],'native')
    def test_source_latch_needs_real_strobe_interval_and_new_sample(self):
        p=dict(kind='latch',label='after-playback',ticks=1700,strobe_ticks=1655,interval_ticks=700,value=0x1234);validate_latch(p)
        for key,value in(('interval_ticks',699),('value',0),('ticks',1655),('value',False)):
            changed=dict(p);changed[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_latch(changed)
        p.update(label='before-playback',value=0);validate_latch(p)
        p['value']=0x1234
        with self.assertRaises(ValueError):validate_latch(p)

if __name__=='__main__':unittest.main()
