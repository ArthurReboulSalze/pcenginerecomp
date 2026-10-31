import copy
import unittest
from pcerecomp.abi import ABI
from tests.cd_read_checkpoint_fixture import cases,expected,hits,validate_payload,expected_cut,expected_timing,validate_gear_cut
from scripts.cd_read_checkpoint_reference import validate_execution
from scripts.cd_read_checkpoint_qualify import validate_stderr

class CdReadCheckpointReferenceTests(unittest.TestCase):
    def test_matrix_and_authored_counts(self):
        self.assertEqual(len(cases()),32)
        self.assertEqual(len({c['id'] for c in cases()}),32)
        for case in cases():
            result=expected(case);self.assertEqual(validate_payload(result,case),len(result['prefix'])+len(result['reply']['data'])+2)
            self.assertTrue(hits(case));self.assertTrue(hits(case,True))
    def test_literals_refuse_changed_payload_and_boolean(self):
        case=cases()[0];value=expected(case)
        for replacement in (True,123):
            changed=copy.deepcopy(value);changed['reply']['data'][0]=replacement
            with self.assertRaises(ValueError):validate_payload(changed,case)
    def test_new_suffix_is_separate_from_imported_prefix(self):
        for case in cases():
            prefix=sum(hits(case,True).values());suffix=sum(hits(case).values())
            before=0 if case['cut'] in (0,1) else (2 if case['cut']==4 else 1)
            for native in (False,True):
                row=dict(runtime_abi=ABI,prefix_native=prefix if native else 0,prefix_interpreted=0 if native else prefix,
                    suffix_native=suffix if native else 0,suffix_interpreted=0 if native else suffix,guard_misses=0,
                    provider_reads_before_suffix=0,provider_reads_suffix=1 if case['cut']>=6 else 2-before)
                self.assertEqual(validate_execution(row,case,native,True),(prefix,suffix))
                changed=copy.deepcopy(row);changed['suffix_native']=True
                with self.assertRaises(ValueError):validate_execution(changed,case,native,True)
    def test_auto_ack_edge_is_real_at_each_guest_speed(self):
        fast=dict(cut=3,automatic=1,divisor=3);slow=dict(fast,divisor=12)
        self.assertEqual(expected_cut(fast)[2],1);self.assertEqual(expected_timing(fast)[2],5)
        self.assertEqual(expected_cut(slow)[2],0);self.assertEqual(expected_timing(slow)[2],0)
        self.assertEqual(expected_cut(slow)[4],expected_cut(fast)[4]+1)
    def test_original_live_cut_literals_refuse_boolean_and_changed_head(self):
        for case in cases():
            cut=expected_cut(case);value=dict(cut=[cut[0],cut[1],cut[2],cut[5],cut[6],expected_timing(case)[4]])
            self.assertEqual(validate_gear_cut(value,case),6)
            for replacement in (True,999):
                changed=copy.deepcopy(value);changed['cut'][-1]=replacement
                with self.assertRaises(ValueError):validate_gear_cut(changed,case)
    def test_successful_build_warning_is_not_guest_execution_stderr(self):
        warning='CMake Warning in CMakeLists.txt:\n  The object file directory has 205 characters.\n'
        for label in ('tool-configure','tool-build','gear-link'):
            validate_stderr(label,warning)
        for label in ('partial-cdb-ack0-div3-gear','partial-cdb-ack0-div3-native-resume'):
            validate_stderr(label,'')
            with self.assertRaisesRegex(ValueError,'actual execution stderr'):
                validate_stderr(label,warning)

if __name__=='__main__':unittest.main()
