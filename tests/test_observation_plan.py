"""Authored exact-size additive plans; no retail code or guest execution."""
import base64
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import observations as o
from pcerecomp.cli import main


MPR = [255, 248, 128, 129, 130, 131, 132, 0]


def row(pc, data, n, i, mpr=None):
    mapping = MPR.copy() if mpr is None else mpr
    physical = [(mapping[((pc+j)&65535)>>13]<<13)|((pc+j)&8191) for j in range(len(data))]
    return dict(pc=pc, mpr=mapping, physical=physical, data=data, native_hits=n, interpreted_hits=i)


def capture(rows, abi=27, origin=None):
    value = dict(schema=1, runtime_abi=abi, capacity=65536, complete=True,
                 dropped_instructions=0, unreadable_instructions=0,
                 retired_instructions=sum(r['native_hits']+r['interpreted_hits'] for r in rows), observations=rows)
    if origin is not None:
        value['checkpoint_origin'] = origin
    return value


class ObservationPlanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old_rows = [row(0x4000, [0xa9,42], 2,3), row(0x4002,[0xe8],1,0)]
        self.new_rows = [row(0x4000,[0xa9,42],4,1), row(0x4000,[0xa9,43],0,2), row(0x4003,[0x0b],0,1)]
        self.origin = dict(sha256='a'*64, ticks=100, frame=1, native_steps=5, interpreter_steps=0)
        self.old = self.write('old.json',capture(self.old_rows,18))
        self.new = self.write('new.json',capture(self.new_rows,27,self.origin))
        self.originals = {p:p.read_bytes() for p in (self.old,self.new)}

    def write(self,name,value):
        path=self.root/name;path.write_bytes(json.dumps(value,separators=(',',':')).encode());return path

    def invoke(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=main(list(map(str,args)))
        return code,stdout.getvalue(),stderr.getvalue()

    def expected(self, paths):
        # Independent tiny oracle from literal fixture rows and exact input bytes.
        inputs=[];merged={}
        for path in paths:
            raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            if any(x['sha256']==sha for x in inputs):continue
            inputs.append(dict(sha256=sha,size_bytes=len(raw),raw_base64=base64.b64encode(raw).decode()))
            source=json.loads(raw)
            for r in source['observations']:
                key=(tuple(r['mpr']),r['pc'],tuple(r['data']))
                if key not in merged:
                    merged[key]={k:copy.deepcopy(r[k]) for k in ('pc','mpr','physical','data')}
                    merged[key].update(native_hits=0,interpreted_hits=0,contributions=[])
                entry=merged[key];entry['native_hits']+=r['native_hits'];entry['interpreted_hits']+=r['interpreted_hits']
                entry['contributions'].append(dict(input_sha256=sha,native_hits=r['native_hits'],interpreted_hits=r['interpreted_hits']))
        rows=[merged[key] for key in sorted(merged)]
        for r in rows:r['contributions'].sort(key=lambda c:c['input_sha256'])
        n=sum(r['native_hits'] for r in rows);i=sum(r['interpreted_hits'] for r in rows)
        value=dict(format='pce-observation-profile-1',schema=1,execution_evidence=False,capacity=65536,
                   inputs=sorted(inputs,key=lambda x:x['sha256']),observations=rows,
                   historical_totals=dict(native_hits=n,interpreted_hits=i,retired_instructions=n+i))
        return value,(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

    def test_exact_additive_counts_bytes_hash_and_source_binding(self):
        plan=o.plan_observation_profile([self.new],baseline_inputs=[self.old])
        self.assertTrue(plan['fits']);self.assertIsNone(plan['refusal'])
        self.assertEqual((plan['baseline']['unique_inputs'],plan['baseline']['union_identities'],plan['baseline']['contributions']),(1,2,2))
        self.assertEqual((plan['combined']['unique_inputs'],plan['combined']['union_identities'],plan['combined']['contributions']),(2,4,5))
        self.assertEqual((plan['additive']['unique_inputs'],plan['additive']['union_identities'],plan['additive']['contributions']),(1,2,3))
        old,oldbytes=self.expected([self.old]);value,serialized=self.expected([self.old,self.new])
        self.assertEqual(plan['combined']['serialized_bytes'],len(serialized))
        self.assertEqual(plan['combined']['serialized_sha256'],hashlib.sha256(serialized).hexdigest())
        self.assertEqual(plan['baseline']['serialized_bytes'],len(oldbytes))
        self.assertEqual(plan['additive']['serialized_bytes'],len(serialized)-len(oldbytes))
        self.assertEqual(plan['additive']['raw_bytes'],self.new.stat().st_size)
        self.assertEqual(plan['headroom']['serialized_bytes'],o.MAX_PROFILE_BYTES-len(serialized))
        self.assertEqual(plan['producer_source_sha256']['observations.py'],hashlib.sha256(Path(o.__file__).read_bytes()).hexdigest())
        self.assertEqual(plan['new_inputs'][0]['runtime_abi'],27);self.assertEqual(plan['new_inputs'][0]['checkpoint_origin'],self.origin)
        self.assertEqual(o.serialize_observation_profile(value),serialized)

    def test_duplicate_sha_alias_and_existing_input_add_nothing(self):
        alias=self.root/'same-bytes.json';alias.write_bytes(self.old.read_bytes())
        plan=o.plan_observation_profile([alias,self.old],baseline_inputs=[self.old])
        self.assertTrue(plan['fits']);self.assertEqual(plan['new_inputs'],[])
        self.assertEqual(plan['duplicate_shas'][0]['argument_count'],3)
        self.assertEqual(plan['duplicate_shas'][0]['duplicate_arguments'],2)
        self.assertTrue(all(x==0 for x in plan['additive'].values()))
        self.assertEqual(plan['baseline']['serialized_sha256'],plan['combined']['serialized_sha256'])

    def test_unused_mpr_and_operand_variants_stay_distinct(self):
        mapping=MPR.copy();mapping[7]=3
        variant=self.write('variants.json',capture([row(0x4000,[0xa9,42],1,0,mapping),row(0x4000,[0xa9,43],1,0)]))
        plan=o.plan_observation_profile([variant],baseline_inputs=[self.old])
        self.assertEqual(plan['additive']['union_identities'],2)

    def test_different_original_json_bytes_add_provenance_but_no_keys(self):
        variant=self.root/'spaced.json'
        variant.write_text(json.dumps(json.loads(self.old.read_bytes()),indent=2),encoding='utf-8')
        plan=o.plan_observation_profile([variant],baseline_inputs=[self.old])
        self.assertTrue(plan['fits']);self.assertEqual(plan['additive']['unique_inputs'],1)
        self.assertEqual(plan['additive']['union_identities'],0)
        self.assertEqual(plan['additive']['contributions'],2)
        self.assertEqual(plan['new_inputs'][0]['sha256'],hashlib.sha256(variant.read_bytes()).hexdigest())
        self.assertEqual(plan['combined']['serialized_sha256'],hashlib.sha256(self.expected([self.old,variant])[1]).hexdigest())

    def test_source_changed_or_unavailable_refuses_without_payload(self):
        with patch.object(o,'_plan_producer',side_effect=[{'observations.py':'a'*64},{'observations.py':'b'*64}]):
            changed=o.plan_observation_profile([self.old])
        self.assertFalse(changed['fits']);self.assertEqual(changed['refusal']['code'],'producer_changed')
        with patch.object(o,'_plan_producer',side_effect=FileNotFoundError('private path')):
            missing=o.plan_observation_profile([self.old])
        self.assertFalse(missing['fits']);self.assertIsNone(missing['producer_source_sha256'])
        self.assertNotIn('private path',json.dumps(missing))

    def test_no_code_or_profile_payload_and_no_execution_claim(self):
        plan=o.plan_observation_profile([self.new],baseline_inputs=[self.old])
        self.assertFalse(plan['execution_evidence']);self.assertFalse(plan['equivalence_evidence']);self.assertFalse(plan['profile_payload_included'])
        def visit(v):
            if isinstance(v,dict):
                self.assertFalse({'data','mpr','physical','observations','raw_base64','historical_totals'} & set(v))
                for child in v.values():visit(child)
            elif isinstance(v,list):
                for child in v:visit(child)
        visit(plan)

    def test_cli_dry_run_never_creates_output_or_parent_and_matches_real_bytes(self):
        future=self.root/'not-created'/'profile.json'
        code,text,error=self.invoke('compose-observations',self.new,'--baseline-input',self.old,'--dry-run','--out',future)
        self.assertEqual(code,0,error);plan=json.loads(text);self.assertFalse(future.parent.exists())
        real=self.root/'real.json';code,text,error=self.invoke('compose-observations',self.new,'--baseline-input',self.old,'--out',real)
        self.assertEqual(code,0,error);self.assertEqual(real.read_bytes(),self.expected([self.old,self.new])[1])
        self.assertEqual(plan['combined']['serialized_sha256'],hashlib.sha256(real.read_bytes()).hexdigest())
        self.assertEqual(plan['combined']['serialized_bytes'],real.stat().st_size)
        self.assertTrue(all(p.read_bytes()==raw for p,raw in self.originals.items()))

    def test_cli_plan_without_out_and_refusal_is_valid_json_nonzero(self):
        code,text,error=self.invoke('compose-observations',self.new,'--dry-run')
        self.assertEqual(code,0,error);self.assertTrue(json.loads(text)['fits'])
        code,text,error=self.invoke('compose-observations',self.new,'--baseline-input',self.old,'--capacity',3,'--dry-run')
        self.assertEqual(code,2);self.assertFalse(json.loads(text)['fits']);self.assertEqual(error,'')
        self.assertIsNone(json.loads(text)['combined']['union_identities'])

    def test_existing_output_refuses_without_changes_even_in_dry_run(self):
        target=self.root/'owner.json';target.write_bytes(b'owner data')
        code,text,error=self.invoke('compose-observations',self.new,'--dry-run','--out',target)
        self.assertEqual(code,2);self.assertEqual(json.loads(text)['refusal']['code'],'output_admission');self.assertEqual(target.read_bytes(),b'owner data')

    def test_profile_serializer_boundary_uses_real_pretty_bytes_not_compact_estimate(self):
        value,raw=self.expected([self.old,self.new]);compact=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        limit=(len(compact)+len(raw))//2
        self.assertLess(len(compact),limit);self.assertLess(limit,len(raw))
        with patch.object(o,'MAX_PROFILE_BYTES',limit):
            plan=o.plan_observation_profile([self.old,self.new])
            self.assertFalse(plan['fits']);self.assertEqual(plan['refusal']['resource'],'serialized_bytes')
            self.assertIsNone(plan['combined']['serialized_bytes']);self.assertEqual(plan['combined']['union_identities'],4)
            self.assertEqual(plan['refusal']['required_at_least'],limit+1)
            code,text,error=self.invoke('compose-observations',self.old,self.new,'--dry-run')
            self.assertEqual(code,2);self.assertFalse(json.loads(text)['fits'])
        with patch.object(o,'MAX_PROFILE_BYTES',len(raw)):
            self.assertEqual(o.plan_observation_profile([self.old,self.new])['combined']['serialized_bytes'],len(raw))

    def test_all_other_bounds_refuse_without_unbounded_measurement(self):
        cases=[('MAX_INPUTS',1,[self.old,self.new],'input_paths'),
               ('MAX_CAPTURE_BYTES',10,[self.old],'individual_raw_bytes'),
               ('MAX_TOTAL_INPUT_BYTES',self.old.stat().st_size,[self.old,self.new],'raw_bytes'),
               ('MAX_CONTRIBUTIONS',4,[self.old,self.new],'contributions'),
               ('MAX_PROFILE_BYTES',1,[self.old],'serialized_bytes')]
        for name,limit,inputs,resource in cases:
            with self.subTest(bound=name),patch.object(o,name,limit):
                plan=o.plan_observation_profile(inputs)
                self.assertFalse(plan['fits']);self.assertEqual(plan['refusal']['resource'],resource)
                self.assertIsNone(plan['refusal']['exact_required'])
        for cap in (0,65537,True,1.0,{'data':'must-not-be-echoed'}):
            with self.subTest(capacity=cap):
                plan=o.plan_observation_profile([self.old],capacity=cap)
                self.assertFalse(plan['fits']);self.assertNotIn('must-not-be-echoed',json.dumps(plan))

    def test_bad_loss_future_abi_and_missing_input_refuse(self):
        for name,value in [('loss',dict(capture(self.new_rows),complete=False,dropped_instructions=1)),
                           ('future',dict(capture(self.new_rows),runtime_abi=999)),('malformed',{'data':'private payload'})]:
            path=self.write(name+'.json',value);plan=o.plan_observation_profile([path])
            self.assertFalse(plan['fits']);self.assertNotIn('private payload',json.dumps(plan))
        self.assertFalse(o.plan_observation_profile([self.root/'missing'])['fits'])

    def test_overflow_and_no_inputs_refuse_explicitly(self):
        huge=self.write('huge.json',capture([row(0x4000,[0xa9,42],2**64-1,0)]))
        self.assertFalse(o.plan_observation_profile([huge,self.old])['fits'])
        empty=o.plan_observation_profile([])
        self.assertFalse(empty['fits']);self.assertEqual(empty['refusal']['code'],'no_inputs')

    def test_infinite_path_arguments_stop_at_existing_cap(self):
        consumed=[]
        def forever():
            while True:consumed.append(1);yield self.old
        plan=o.plan_observation_profile(forever())
        self.assertFalse(plan['fits']);self.assertEqual(len(consumed),o.MAX_INPUTS+1)
        self.assertEqual(plan['refusal']['resource'],'input_paths')


if __name__=='__main__':unittest.main()
