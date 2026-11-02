import copy
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from scripts import romatlas_reference as reference


def case(opcode,operands=(),pc=0xffff,mpr=tuple(range(8))):
    return dict(id=1,phase='decode',tag='full',pc=pc,bytes=[opcode,*operands],mpr=list(mpr))


class RomAtlasReferenceTests(unittest.TestCase):
    def test_positive_branch_wrap_literal(self):
        self.assertEqual(reference.expected_instruction(case(0x10,[0x7f])),dict(
            opcode=0x10,length=2,text='bpl $0080',assembly=None,
            after=dict(mpr=list(range(8)),sf2_bank=None),successors=[1,0x80],
            references=[dict(cpu_address=0x80,kind='control',indirect=False,indexed=False)],terminal=False))

    def test_bit_branch_negative_wrap_literal(self):
        d=reference.expected_instruction(case(0x0f,[0x42,0x80]))
        self.assertEqual(d['text'],'bbr0 $42,$ff82')
        self.assertEqual(d['successors'],[2,0xff82])
        self.assertEqual(d['references'],[
            dict(cpu_address=0x2042,kind='memory',indirect=False,indexed=False),
            dict(cpu_address=0xff82,kind='control',indirect=False,indexed=False)])

    def test_block_encoded_length_zero_is_preserved(self):
        d=reference.expected_instruction(case(0x73,[0x34,0x12,0xcd,0xab,0,0],pc=0x1fff))
        self.assertEqual(d['text'],'tii $1234,$abcd,$0000')
        self.assertEqual(d['length'],7)
        self.assertEqual(d['references'],[
            dict(cpu_address=0x1234,kind='block_source',indirect=False,indexed=False,length=0),
            dict(cpu_address=0xabcd,kind='block_destination',indirect=False,indexed=False,length=0)])

    def test_tst_immediate_and_address_fields(self):
        d=reference.expected_instruction(case(0xb3,[0x80,0x78,0x56]))
        self.assertEqual(d['text'],'tst #$80,a:$5678,x')
        self.assertEqual(d['references'],[dict(cpu_address=0x5678,kind='memory',indirect=False,indexed=True)])

    def test_mpr_page_cross_literal(self):
        d=reference.expected_cpu(case(0xa9,[0x93],pc=0x1fff,mpr=(0x2a,0x81,0,0,0,0,0,0)))
        self.assertEqual(d,dict(pc=0x2001,a=0x93,s=255,reads=[[0x55fff,0xa9],[0x102000,0x93]],writes=[]))

    def test_brk_original_core_fetch_and_return_signature_literal(self):
        d=reference.expected_cpu(case(0,[0xa5]))
        self.assertEqual(d,dict(pc=0x4567,a=0,s=252,
            reads=[[0xffff,0],[0,0xa5],[0xfff6,0x67],[0xfff7,0x45]],
            writes=[[0x21ff,0],[0x21fe,1],[0x21fd,0x14]]))
        with self.assertRaises(ValueError):reference.expected_cpu(case(0x0b))

    def test_transport_rejects_duplicate_and_nonfinite_json(self):
        for data in ('{"id":1,"id":2}','{"x":NaN}','{"x":1e9999}'):
            with self.assertRaises(ValueError):reference.strict(data)

    def test_all_opcode_admission_refuses_unknown_or_bool_disagreements(self):
        requests=[dict(case(op,[0,0,0,0,0,0]),id=op+1)for op in range(256)]
        replies=[dict(id=r['id'],ok=True,instruction=reference.expected_instruction(r))for r in requests]
        replies[0]['instruction']['length']=1
        result=reference.compare(requests,replies)
        self.assertEqual(result['known_disagreement_counts'],dict(brk_signature_length=1))
        for index,field,value in ((1,'length',True),(0,'terminal',False),(0x0b,'text','nop')):
            bad=copy.deepcopy(replies);bad[index]['instruction'][field]=value
            with self.assertRaises(ValueError):reference.compare(requests,bad)

    def test_physical_comparison_checks_toolkit_fetches(self):
        r=dict(case(0xa9,[0x93]),phase='cpu')
        value=reference.expected_cpu(r);response=dict(id=1,ok=True,cpu=dict(value,operations=2))
        # Complete decode coverage is required separately; malformed core data
        # must fail before that coverage check, without executing a CPU.
        response['cpu']['reads'][0][0]=0
        with self.assertRaisesRegex(ValueError,'mapped fetch'):reference.compare([r],[response])

    def test_finite_fixture_extent_and_roles(self):
        rows=reference.plans()
        self.assertEqual(len(rows),25221)
        self.assertEqual(sum(r['phase']=='cpu'for r in rows),96)
        self.assertEqual(sum(r['tag']=='full'for r in rows),24576)
        self.assertEqual({r['bytes'][0]for r in rows if r['tag']=='full'},set(range(256)))

    def test_registry_source_admission_checks_archive_source_and_extras(self):
        with tempfile.TemporaryDirectory()as tmp:
            registry=Path(tmp)/'registry';folder=registry/'src/example/demo-1.0';folder.mkdir(parents=True)
            archive=registry/'cache/example/demo-1.0.crate';archive.parent.mkdir(parents=True)
            payload=b'fn marker() {}\n';(folder/'lib.rs').write_bytes(payload)
            with tarfile.open(archive,'w:gz')as tar:
                member=tarfile.TarInfo('demo-1.0/lib.rs');member.size=len(payload);tar.addfile(member,io.BytesIO(payload))
            expected=hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(len(reference.registry_binding(folder,expected)),2)
            (folder/'lib.rs').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Unpacked'):reference.registry_binding(folder,expected)
            (folder/'lib.rs').write_bytes(payload);(folder/'build.rs').write_bytes(b'fn main() {}')
            with self.assertRaisesRegex(ValueError,'extra'):reference.registry_binding(folder,expected)
            with self.assertRaisesRegex(ValueError,'archive checksum'):reference.registry_binding(folder,'0'*64)


if __name__=='__main__':unittest.main()
