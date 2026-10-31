"""Independent authored head/Q literals and false-positive rejection checks."""
import copy
import unittest

from pcerecomp.abi import ABI
from scripts.read_head_reference import expected, expected_hits, plans, q_response, validate_capture, validate_execution, validate_rows
from generate_scsi_fixture import make_fixture


class ReadHeadReferenceTests(unittest.TestCase):
    def test_known_head_positions_and_track_boundary_q_are_literal(self):
        self.assertEqual(q_response(3,False),[1,0x41,1,1,0,0,3,0,2,3])
        self.assertEqual(q_response(4,True),[1,1,2,1,0,0,0,0,2,4])
        self.assertEqual(q_response(449849,False)[7:],[0x99,0x59,0x74])

    def test_success_multi_failure_clamp_and_held_buffer_expected_heads(self):
        for automatic in (0,1):
            for mixed in (False,True):
                cases=plans(mixed,automatic)
                per_case={case['id']:expected([case],mixed) for case in cases}
                heads=lambda key:[row['values'][0] for row in per_case[key] if row['kind']=='head']
                self.assertEqual(heads('single-sector-idle-Q'),[0,3,3])
                self.assertEqual(heads('multiple-sectors-idle-Q'),[3])
                self.assertEqual(heads('pending-buffer-does-not-advance-head'),[0,1,1,2])
                self.assertEqual(heads('last-data-sector-next-position'),[4 if mixed else 3])
                if not mixed:
                    self.assertEqual(heads('failed-second-sector-retains-head'),[3])
                    failed=per_case['failed-second-sector-retains-head'][0]
                    self.assertEqual((len(failed['data']),failed['status'],failed['message']),(2048,2,2))

    def test_old_loaded_lba_q_response_and_raw_status_changes_are_rejected(self):
        wanted=expected(plans(True,0),True)
        self.assertGreater(validate_rows(copy.deepcopy(wanted),wanted),10000)
        changes=[]
        old=copy.deepcopy(wanted);old[3]['data'][6]-=1;changes.append(old)
        bad=copy.deepcopy(wanted);bad[2]['values'][0]-=1;changes.append(bad)
        bad=copy.deepcopy(wanted);bad[0]['values'][0]=False;changes.append(bad)
        bad=copy.deepcopy(wanted);bad[1]['status']=2;changes.append(bad)
        bad=copy.deepcopy(wanted);bad[1]['data'][0]^=1;changes.append(bad)
        changes.append(wanted[:-1])
        for actual in changes:
            with self.assertRaises(ValueError):validate_rows(actual,wanted)

    def capture(self):
        snapshot,cases=make_fixture();pc=next(pc for pc,op,address in cases if op==0x8D and address==0x1800)
        physical=[0x1F0000+(pc&8191)+i for i in range(3)]
        return dict(schema=1,runtime_abi=ABI,capacity=1024,complete=True,dropped_instructions=0,unreadable_instructions=0,
            retired_instructions=7,observations=[dict(pc=pc,mpr=list(snapshot.mpr),physical=physical,
                data=[snapshot.memory[address] for address in physical],native_hits=7,interpreted_hits=0)])

    def test_capture_requires_full_source_context_exact_bytes_and_real_tier_hits(self):
        source=self.capture();work=dict(retired_instructions=7,pure_guards=4)
        hits={source['observations'][0]['pc']:7}
        self.assertEqual(validate_capture(source,work,True,hits),(7,1))
        for field in ('mpr','physical','data','native_hits','interpreted_hits','duplicate','loss','count','boolean-byte','boolean-mpr'):
            actual=copy.deepcopy(source)
            if field in ('mpr','physical','data'):actual['observations'][0][field][0]^=1
            elif field in ('native_hits','interpreted_hits'):actual['observations'][0][field]+=1
            elif field=='duplicate':actual['observations']*=2
            elif field=='loss':actual['dropped_instructions']=1
            elif field=='boolean-byte':actual['observations'][0]['data'][1]=False
            elif field=='boolean-mpr':actual['observations'][0]['mpr'][-1]=False
            else:actual['retired_instructions']+=1
            with self.subTest(field=field),self.assertRaises(ValueError):validate_capture(actual,work,True,hits)

    def test_independent_supervisor_counts_and_strict_execution_metadata(self):
        for mixed in (False,True):
            for automatic in (0,1):
                cases=plans(mixed,automatic);hits=expected_hits(cases,mixed)
                self.assertEqual(len(hits),6 if automatic else 4)
                self.assertGreater(sum(hits.values()),40000)
                work=dict(schema=1,tier='native',divisor=3,retired_instructions=sum(hits.values()),
                          pure_guards=4,cases=len(cases),records=len(expected(cases,mixed)))
                validate_execution(work,cases,work['records'],3,True,hits)
                for key,value in (('retired_instructions',1),('tier','interpreter'),('cases',True),('divisor',12),('records',0)):
                    bad=dict(work);bad[key]=value
                    with self.subTest(key=key),self.assertRaises(ValueError):validate_execution(bad,cases,work['records'],3,True,hits)


if __name__=='__main__':unittest.main()
