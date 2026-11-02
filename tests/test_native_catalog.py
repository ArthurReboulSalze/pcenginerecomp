"""Authored catalogue authentication fixtures; never invoke an emitter or SDK."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import native_catalog as catalog

MPR = [255, 248, 128, 129, 130, 131, 132, 0]


def row(pc=0x4000, data=(0xEA,), *, mpr=None, native=0, interpreted=1):
    mpr = list(MPR if mpr is None else mpr)
    return dict(pc=pc, mpr=mpr,
        physical=[mpr[((pc+i)&65535)>>13]*8192+((pc+i)&8191) for i in range(len(data))],
        data=list(data), native_hits=native, interpreted_hits=interpreted)


def identity(value):
    return value['pc'], tuple(value['mpr']), tuple(value['physical']), tuple(value['data'])


class NativeCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = self.root/'module'
        self.module.mkdir()
        self.manifest_path = self.module/'module.json'
        self.input_path = self.root/'observations.json'

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')

    def fixture(self, rows=None, *, emitted=None, excluded=(), unsupported=(), spans=(),
                abi=29, source_abi=18, parts=(), partition_size=256, stable=False, profile=False):
        rows = [row()] if rows is None else rows
        emitted = list(range(len(rows))) if emitted is None else list(emitted)
        self.original = dict(schema=1, runtime_abi=source_abi, capacity=65536,
            dropped_instructions=0, unreadable_instructions=0, complete=True,
            retired_instructions=sum(r['native_hits']+r['interpreted_hits'] for r in rows), observations=rows)
        raw = json.dumps(self.original).encode()
        digest = hashlib.sha256(raw).hexdigest()
        selected = [rows[i] for i in emitted]
        units = ['module.cpp']+list(parts)
        headers = ['module_parts.hpp'] if parts or stable else []
        self.manifest = dict(schema=1, runtime_abi=abi, execution_evidence=False,
            code_capture_sha256=digest, capture_runtime_abi=source_abi, capture_complete=True,
            capture_retired_instructions=self.original['retired_instructions'],
            capture_dropped_instructions=0, capture_unreadable_instructions=0,
            captured_native_hits=sum(r['native_hits'] for r in rows),
            captured_interpreted_hits=sum(r['interpreted_hits'] for r in rows),
            partition_size=partition_size, partitioned=bool(parts) or stable,
            dispatch_strategy='full_mpr_pc_opcode_operand_key', translated_body_count=len(selected),
            largest_partition_instructions=1 if parts else len(selected),
            native_instructions_emitted=len(selected), native_contexts=len({tuple(r['mpr']) for r in selected}),
            observed_instructions=len(rows), excluded_physical_ranges=list(spans),
            excluded_observations=len(excluded),
            excluded_retired_hits=sum(rows[i]['native_hits']+rows[i]['interpreted_hits'] for i in excluded),
            unsupported_observations=len(unsupported),
            guards=['full_mpr_snapshot', 'exact_source_bytes_per_instruction', 'instruction_deadline'],
            unsupported_policy='return to dispatcher, then bounded interpreter or explicit trap',
            scope='Authored manifest declarations, not compiled/executed source proof')
        if stable:
            self.manifest.update(partition_layout='stable', pc_bucket_size=256,
                                 partition_identity='full_mpr_logical_pc_range_v1')
        if profile:
            totals=dict(native_hits=self.manifest['captured_native_hits'],
                interpreted_hits=self.manifest['captured_interpreted_hits'],
                retired_instructions=self.original['retired_instructions'])
            observations=[copy.deepcopy(r)|dict(contributions=[dict(input_sha256=digest,
                native_hits=r['native_hits'], interpreted_hits=r['interpreted_hits'])]) for r in rows]
            observations.sort(key=lambda r:(r['mpr'],r['pc'],r['data']))
            value=dict(format='pce-observation-profile-1',schema=1,execution_evidence=False,
                capacity=65536,inputs=[dict(sha256=digest,size_bytes=len(raw),
                    raw_base64=base64.b64encode(raw).decode())],observations=observations,historical_totals=totals)
            metadata={k:v for k,v in self.original.items() if k!='observations'}
            metadata.update(sha256=digest,size_bytes=len(raw),native_hits=totals['native_hits'],
                interpreted_hits=totals['interpreted_hits'],observation_count=len(rows))
            raw=json.dumps(value).encode()
            for key in list(self.manifest):
                if key.startswith(('capture_','captured_')) or key=='code_capture_sha256':
                    del self.manifest[key]
            self.manifest.update(observation_profile_sha256=hashlib.sha256(raw).hexdigest(),
                observation_profile_format=value['format'],observation_profile_schema=1,
                observation_inputs=[metadata],historical_totals=totals,
                historical_count_policy='sum of distinct raw inputs; overlapping execution windows are not deduplicated')
        self.input_path.write_bytes(raw)
        for field,names in (('translation_units',units),('generated_headers',headers)):
            self.manifest[field]=[]
            for name in names:
                payload=('// authored opaque artifact '+name+'\n').encode()
                (self.module/name).write_bytes(payload)
                self.manifest[field].append(dict(file=name,sha256=hashlib.sha256(payload).hexdigest()))
        self.save_manifest()
        return rows

    def load(self, **options):
        return catalog.load_native_catalog(self.manifest_path,self.input_path,**options)

    def test_declared_membership_and_public_provenance_are_not_execution(self):
        rows=self.fixture()
        value=self.load()
        self.assertEqual(value.emitted,frozenset({identity(rows[0])}))
        self.assertEqual(value.observed,value.emitted)
        self.assertFalse(value.excluded|value.unsupported)
        self.assertEqual(value.runtime_abi,29)
        self.assertEqual(value.provenance['membership_claim'],'reconstructed-declared-emission')
        self.assertIs(value.provenance['execution_evidence'],False)
        self.assertIs(value.provenance['linked_binary_verified'],False)
        self.assertEqual(value.provenance['original_inputs'][0]['runtime_abi'],18)
        text=json.dumps(value.provenance)
        self.assertNotIn(str(self.root),text)
        self.assertNotIn('raw_base64',text)

    def test_operand_exclusion_wrap_and_full_mapping_variants(self):
        other=MPR.copy();other[7]=1
        rows=[row(0x1FFF,(0xA9,0x2A)),row(),row(mpr=other),row(0x4001,(0x0B,))]
        self.fixture(rows,emitted=(1,2),excluded=(0,),unsupported=(3,),spans=[dict(start=0x1F0000,length=1)])
        value=self.load()
        self.assertEqual(value.emitted,frozenset({identity(rows[1]),identity(rows[2])}))
        self.assertEqual(value.excluded,frozenset({identity(rows[0])}))
        self.assertEqual(value.unsupported,frozenset({identity(rows[3])}))
        self.assertEqual(value.counts['native_contexts'],2)
        self.assertEqual(value.provenance['excluded_physical_ranges'],[dict(start=0x1F0000,length=1)])

    def test_abi28_selection_is_explicit_same_contract_without_sdk_import(self):
        self.fixture(abi=28,source_abi=26)
        value=self.load()
        self.assertEqual(value.runtime_abi,28)
        self.assertEqual(value.provenance['selection_contract'],'observed-abi28-29-v1')
        self.assertEqual(value.provenance['original_inputs'][0]['runtime_abi'],26)
        for abi in (27,30,True,28.0):
            self.manifest['runtime_abi']=abi;self.save_manifest()
            with self.subTest(abi=abi),self.assertRaises(ValueError):self.load()

    def test_later_capture_is_not_backdated_into_older_module_producer(self):
        for profile in (False,True):
            self.fixture(abi=28,source_abi=29,profile=profile)
            with self.subTest(profile=profile),self.assertRaisesRegex(ValueError,'producer ABI'):
                self.load()

    def test_profile_originals_and_manifest_provenance_are_reconstructed(self):
        rows=self.fixture(profile=True)
        value=self.load()
        self.assertEqual(value.emitted,frozenset({identity(rows[0])}))
        self.assertEqual(value.provenance['observations']['kind'],'profile')
        self.assertEqual(value.provenance['original_inputs'][0]['interpreted_hits'],1)
        self.manifest['observation_inputs'][0]['runtime_abi']=29;self.save_manifest()
        with self.assertRaisesRegex(ValueError,'observation_inputs'):self.load()

    def test_balanced_stable_single_unit_and_span_layouts(self):
        self.fixture([row(),row(0x4001)],parts=('module_part_0000.cpp','module_part_0001.cpp'),partition_size=1)
        self.assertEqual(len(self.load().emitted),2)
        self.manifest['largest_partition_instructions']=2;self.save_manifest()
        with self.assertRaisesRegex(ValueError,'largest_partition'):self.load()
        self.fixture([row(),row(0x4001)],partition_size=1)
        self.assertEqual(len(self.load().emitted),2) # explicit historical single-unit shape
        mapping=sum(x<<(8*i) for i,x in enumerate(MPR))
        self.fixture([row(),row(0x4100)],stable=True,
            parts=(f'module_m{mapping:016x}_p4000.cpp',f'module_m{mapping:016x}_p4100.cpp'))
        self.manifest.update(native_span=dict(schema=1,protocol='per_instruction_v1'),native_span_translated_body_count=2)
        self.save_manifest();self.assertEqual(len(self.load().emitted),2)
        self.manifest['native_span']['schema']=True;self.save_manifest()
        with self.assertRaisesRegex(ValueError,'native_span'):self.load()

    def test_every_artifact_and_observation_hash_is_checked(self):
        self.fixture();(self.module/'module.cpp').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'SHA256'):self.load()
        self.fixture();self.input_path.write_bytes(self.input_path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'SHA256'):self.load()

    def test_portable_names_case_duplicates_and_escaping_links_are_refused(self):
        self.fixture()
        for name in ('../outside.cpp','sub/module.cpp','a\\b.cpp','x:stream.cpp','CON.cpp'):
            self.manifest['translation_units'][0]['file']=name;self.save_manifest()
            with self.subTest(name=name),self.assertRaises(ValueError):self.load()
        self.fixture();self.manifest['translation_units'].append(self.manifest['translation_units'][0]|{'file':'MODULE.cpp'});self.save_manifest()
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.load()
        self.fixture();original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda p: p.name=='module.cpp' or original(p)):
            with self.assertRaises(ValueError):self.load()

    def test_static_legacy_or_ambiguous_membership_fails_explicitly(self):
        self.fixture();del self.manifest['code_capture_sha256'];self.save_manifest()
        with self.assertRaisesRegex(ValueError,'membership unavailable'):self.load()
        self.fixture();del self.manifest['translation_units'];self.save_manifest()
        with self.assertRaisesRegex(ValueError,'translation_units'):self.load()
        self.fixture();self.manifest['observation_profile_sha256']='a'*64;self.save_manifest()
        with self.assertRaisesRegex(ValueError,'exactly one'):self.load()

    def test_counts_boolean_tokens_duplicate_json_and_unknown_semantics_refused(self):
        self.fixture()
        for field in ('observed_instructions','native_instructions_emitted','native_contexts',
                      'excluded_observations','excluded_retired_hits','unsupported_observations','translated_body_count'):
            original=self.manifest[field];self.manifest[field]=True;self.save_manifest()
            with self.subTest(field=field),self.assertRaises(ValueError):self.load()
            self.manifest[field]=original
        self.save_manifest();raw=self.manifest_path.read_text()
        for bad in (raw.replace('"runtime_abi": 29','"runtime_abi": 29.0'),
                    raw.replace('"runtime_abi": 29','"runtime_abi": 1e9999'),
                    raw.replace('"schema": 1','"schema": 1,"schema": 1',1)):
            self.manifest_path.write_text(bad)
            with self.assertRaises(ValueError):self.load()
        self.manifest['invented_selection_rule']='ignore guards';self.save_manifest()
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.load()

    def test_changed_input_after_first_read_is_refused_even_with_restored_mtime(self):
        self.fixture();real=catalog._Files.read;changed=False
        def mutate(files,path,maximum,**options):
            nonlocal changed
            value=real(files,path,maximum,**options)
            if Path(path).name=='module.cpp' and not changed:
                changed=True;p=Path(path);before=p.stat();raw=p.read_bytes()
                p.write_bytes(bytes([raw[0]^1])+raw[1:]);os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
            return value
        with patch.object(catalog._Files,'read',mutate):
            with self.assertRaises(ValueError):self.load()

    def test_explicit_selection_contract_and_bounds(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError,'selection contract'):self.load(producer_contract='guess-current')
        with patch.object(catalog,'NATIVE',set(catalog.NATIVE)-{0xEA}):
            with self.assertRaisesRegex(ValueError,'selection contract'):self.load()
        with patch.object(catalog,'MAX_TOTAL_ARTIFACT_BYTES',1):
            with self.assertRaisesRegex(ValueError,'Total module artifact'):self.load()

    def test_current_emitter_parity_across_layouts_exclusions_and_variants(self):
        # Integration parity is separate from the independently authored
        # authentication fixtures above. No C++ compilation/execution occurs.
        from pcerecomp.emitter import emit_capture
        other=MPR.copy();other[4]=140
        wrap=MPR.copy();wrap[0]=1
        rows=[row(data=(0xA9,42)),row(data=(0xA9,43)),row(0x4001),row(0x4100),
              row(0xFFFF,(0xA9,44),mpr=wrap),row(0x5000,(0x0B,)),
              row(0x1FFF,(0xA9,45)),row(mpr=other)]
        original=dict(schema=1,runtime_abi=28,capacity=65536,dropped_instructions=0,
            unreadable_instructions=0,complete=True,retired_instructions=8,observations=rows)
        raw=json.dumps(original).encode();self.input_path.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        options=({},dict(partition_size=1),dict(partition_size=1,single_unit=True),
                 dict(partition_layout='stable'),dict(partition_layout='stable',native_span=True))
        expected=frozenset(identity(rows[i]) for i in (0,1,2,3,4,7))
        for index,selection in enumerate(options):
            with self.subTest(selection=selection):
                output=self.root/f'emitted-{index}'
                emit_capture(original,output,digest,exclude_ranges=((0x1F0000,1),),**selection)
                before={p.name:p.read_bytes() for p in output.iterdir()}
                actual=catalog.load_native_catalog(output/'module.json',self.input_path)
                self.assertEqual(actual.emitted,expected)
                self.assertEqual(actual.excluded,frozenset({identity(rows[6])}))
                self.assertEqual(actual.unsupported,frozenset({identity(rows[5])}))
                self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})
                self.assertEqual(self.input_path.read_bytes(),raw)


if __name__=='__main__':unittest.main()
