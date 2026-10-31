import copy
import unittest
from pcerecomp.abi import ABI
from tests.cd_adpcm_checkpoint_fixture import cases,expected,hits,validate_payload,validate_gear_cut,raw_differences
from scripts.cd_adpcm_checkpoint_reference import validate_execution
from scripts.cd_adpcm_checkpoint_qualify import validate_stderr
class CdAdpcmCheckpointTests(unittest.TestCase):
 def test_authored_matrix_and_complete_ram_literals(self):
  self.assertEqual(len(cases()),32)
  for case in cases():
   wanted=expected(case);self.assertEqual(len(wanted['reply']['ram']),65536)
   self.assertEqual(validate_payload(wanted,case),65553)
   self.assertTrue(hits(case));self.assertTrue(hits(case,True))
 def test_ram_order_and_boolean_are_refused(self):
  case=cases()[0]
  for replacement in (True,0):
   actual=expected(case);actual['reply']['ram'][65534]=replacement
   with self.assertRaises(ValueError):validate_payload(actual,case)
 def test_new_work_separate_from_imported(self):
  for case in cases():
   prefix=sum(hits(case,True).values());suffix=sum(hits(case).values())
   for native in (False,True):
    row=dict(runtime_abi=ABI,prefix_native=prefix if native else 0,prefix_interpreted=0 if native else prefix,suffix_native=suffix if native else 0,suffix_interpreted=0 if native else suffix,guard_misses=0,provider_reads_before_suffix=0,provider_reads_suffix=int(case['cut'] in (0,5,6,7)))
    self.assertEqual(validate_execution(row,case,native,True),(prefix,suffix))
    row['prefix_native']=True
    with self.assertRaises(ValueError):validate_execution(row,case,native,True)
 def test_build_diagnostics_never_admit_execution_stderr(self):
  validate_stderr('tool-configure','CMake Warning: long path')
  with self.assertRaises(ValueError):validate_stderr('pending-beat-mode1-div3-native-resume','unexpected')
 def test_original_clock_counts_require_one_master_tick_calls(self):
  case=cases()[0];actual=dict(cut=[100,136,0,0,0,65534,0,0,0,0,0,12,0],single_clock_calls=10,single_clock_ticks=11,coarse_clock_calls=1,coarse_clock_ticks=90)
  with self.assertRaises(ValueError):validate_gear_cut(actual,case)
 def test_raw_original_req_ack_disagreement_is_preserved(self):
  case=cases()[2];original=dict(cut=[100,0xca,1,0,9,65534,0,0,0,0,0,12,21]);tool=copy.deepcopy(original);tool['cut'][1]=0x8a
  self.assertEqual(raw_differences(original,tool,case),[dict(case=case['id'],field='signals',original=0xca,tool=0x8a)])
if __name__=='__main__':unittest.main()
