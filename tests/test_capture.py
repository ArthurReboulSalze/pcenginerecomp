"""Authored observed-code identities and strict offline capture boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.capture import load_capture, validate_capture
from pcerecomp.emitter import emit_capture
from pcerecomp.isa import decode
from pcerecomp.cli import main

MPR = [255,248,128,129,130,131,132,0]


def observation(pc=0x4000, raw=(0xa9, 42), mpr=None, native=0, interpreted=1):
    mpr = MPR.copy() if mpr is None else mpr
    ins = decode(lambda address: raw[(address-pc)&65535], pc, tuple(mpr))
    return {'pc': pc, 'mpr': list(mpr), 'physical': list(ins.physical), 'data': list(raw),
            'native_hits': native, 'interpreted_hits': interpreted}


def capture(items=None, capacity=64, dropped=0, unreadable=0):
    items = [observation()] if items is None else items
    return {'schema': 1, 'runtime_abi': 13, 'capacity': capacity,
            'dropped_instructions': dropped, 'unreadable_instructions': unreadable,
            'retired_instructions': dropped+unreadable+sum(i['native_hits']+i['interpreted_hits'] for i in items),
            'complete': not (dropped or unreadable), 'observations': items}


class CaptureTests(unittest.TestCase):
    def test_checkpoint_origin_is_strict_and_retained_without_prefix_promotion(self):
        origin = {'sha256': 'a'*64, 'ticks': 1000, 'frame': 7,
                  'native_steps': 800, 'interpreter_steps': 200}
        current = capture([observation(native=3, interpreted=2)])
        current['runtime_abi'] = ABI
        current['checkpoint_origin'] = origin
        self.assertEqual(len(validate_capture(current)), 1)
        with tempfile.TemporaryDirectory() as temp:
            manifest = emit_capture(current, Path(temp)/'module')
        self.assertEqual(manifest['capture_checkpoint_origin'], origin)
        self.assertEqual(manifest['capture_execution_window'], 'resumed-checkpoint-suffix')
        self.assertEqual(manifest['capture_retired_instructions'], 5)
        self.assertEqual(manifest['captured_native_hits'], 3)
        self.assertFalse(manifest['execution_evidence'])
        variants = [None, {}, origin | {'extra': 1}, origin | {'ticks': True},
                    origin | {'frame': -1}, origin | {'sha256': 'A'*64},
                    origin | {'native_steps': 2**64}, origin | {'interpreter_steps': 0.0}]
        for invalid in variants:
            with self.subTest(origin=invalid), self.assertRaises(ValueError):
                validate_capture(current | {'checkpoint_origin': invalid})

    def test_current_abi_capture_is_preserved_and_future_abi_is_rejected(self):
        current = capture([observation()])
        current['runtime_abi'] = ABI
        original = copy.deepcopy(current)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'current'
            manifest = emit_capture(current, out)
            self.assertEqual(manifest['runtime_abi'], ABI)
            self.assertEqual(manifest['capture_runtime_abi'], ABI)
            self.assertIn(f'static_assert(abi_version == {ABI});', (out/'module.cpp').read_text())
        self.assertEqual(current, original)
        for value in (ABI + 1, True, float(ABI)):
            future = copy.deepcopy(current)
            future['runtime_abi'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_capture(future)

    def test_legacy_observations_rebuild_for_current_runtime(self):
        for abi in range(12, ABI):
            old=capture([observation()]);old['runtime_abi']=abi
            original=copy.deepcopy(old)
            with tempfile.TemporaryDirectory() as temp:
                manifest=emit_capture(old,Path(temp)/'new')
            self.assertEqual(manifest['runtime_abi'],ABI)
            self.assertEqual(manifest['capture_runtime_abi'],abi)
            self.assertEqual(old,original)

    def test_variants_contexts_overlap_and_wrap_preserved(self):
        second = MPR.copy(); second[3] = 140
        items = [observation(), observation(raw=(0xa9, 43)), observation(mpr=second),
                 observation(0x4001, (0xea,)), observation(0xffff, (0xa9, 29)),
                 observation(0x5fff, (0xad, 0x11, 0x22))]
        decoded = validate_capture(capture(items))
        self.assertEqual(len(decoded), 6)
        self.assertIn((8191, 0x1fe000), [tuple(i['physical']) for i in decoded])
        self.assertIn((0x101fff, 0x102000, 0x102001), [tuple(i['physical']) for i in decoded])

    def test_direct_emission_and_context_dispatch(self):
        second = MPR.copy(); second[3] = 140
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'new'
            manifest = emit_capture(capture([observation(), observation(raw=(0xa9, 43)), observation(mpr=second)]), out)
            code = (out/'module.cpp').read_text()
            self.assertEqual(manifest['native_instructions_emitted'], 3)
            self.assertEqual(manifest['native_contexts'], 2)
            self.assertEqual(code.count('case 16384:'), 2)
            self.assertIn('s.a=42;', code)
            self.assertNotIn('interpret_step(', code)
            self.assertIn('switch(mapping)', code)
            self.assertLess(code.index('if(s.ticks >= deadline)'), code.index('switch(mapping)'))

    def test_deterministic_order(self):
        items = [observation(), observation(raw=(0xa9, 43))]
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp)/'one', Path(temp)/'two'
            # Equal provenance yields equal generated text despite input order.
            emit_capture(capture(items), first, 'a'*64)
            emit_capture(capture(list(reversed(items))), second, 'a'*64)
            self.assertEqual((first/'module.cpp').read_bytes(), (second/'module.cpp').read_bytes())
            self.assertEqual((first/'module.json').read_bytes(), (second/'module.json').read_bytes())

    def test_unsupported_explicit_and_empty(self):
        for items in ([], [observation(raw=(0x0B,))]):
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp)/'new'
                manifest = emit_capture(capture(items), out)
                self.assertEqual(manifest['native_instructions_emitted'], 0)
                self.assertIn('return Exit::miss;', (out/'module.cpp').read_text())

    def test_exclusions_touch_any_byte_and_preserve_raw_accounting(self):
        items=[observation(native=3,interpreted=7),observation(raw=(0xa9,43),native=2,interpreted=4),
               observation(0x4002,(0xea,),native=1,interpreted=0)]
        report=capture(items,dropped=6,unreadable=2); original=copy.deepcopy(report)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'new'
            manifest=emit_capture(report,out,exclude_ranges=[(0x100001,1)])
            code=(out/'module.cpp').read_text()
        self.assertEqual(report,original)
        self.assertEqual(manifest['native_instructions_emitted'],1)
        self.assertEqual(manifest['excluded_physical_ranges'],[{'start':0x100001,'length':1}])
        self.assertEqual(manifest['excluded_observations'],2)
        self.assertEqual(manifest['excluded_retired_hits'],16)
        self.assertEqual(manifest['capture_retired_instructions'],25)
        self.assertEqual(manifest['captured_native_hits'],6)
        self.assertEqual(manifest['captured_interpreted_hits'],11)
        self.assertEqual(manifest['capture_dropped_instructions'],6)
        self.assertEqual(manifest['capture_unreadable_instructions'],2)
        self.assertFalse(manifest['capture_complete'])
        self.assertNotIn('case 16384:',code)
        self.assertIn('case 16386:',code)

    def test_exclusion_cross_page_wrap_context_and_boundaries(self):
        different=MPR.copy();different[2]=140
        items=[observation(0x5fff,(0xad,1,2)),observation(0xffff,(0xa9,29)),
               observation(),observation(mpr=different)]
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'new'
            manifest=emit_capture(capture(items),out,
                exclude_ranges=[(0x102000,1),(0x1fe000,1),(0x100002,1),(0x1fffff,1)])
            code=(out/'module.cpp').read_text()
        self.assertEqual(manifest['excluded_observations'],2)
        self.assertEqual(manifest['native_instructions_emitted'],2)
        self.assertEqual(manifest['native_contexts'],2)
        self.assertNotIn('case 24575:',code)
        self.assertNotIn('case 65535:',code)
        # An operand immediately after the two-byte LDA does not overlap it.
        self.assertEqual(code.count('case 16384:'),2)

    def test_excluded_unsupported_classification_and_determinism(self):
        report=capture([observation(raw=(0x0B,)),observation(0x4001,(0xea,))])
        with tempfile.TemporaryDirectory() as temp:
            one=Path(temp)/'one';two=Path(temp)/'two'
            first=emit_capture(report,one,exclude_ranges=[(0x100000,1),(0x100001,1),(0x100000,1)])
            second=emit_capture(report,two,exclude_ranges=[(0x100001,1),(0x100000,1)])
            self.assertEqual((one/'module.cpp').read_bytes(),(two/'module.cpp').read_bytes())
        self.assertEqual(first,second)
        self.assertEqual(first['excluded_observations'],2)
        self.assertEqual(first['unsupported_observations'],0)
        self.assertEqual(first['native_instructions_emitted'],0)
        self.assertEqual(first['native_contexts'],0)
        self.assertEqual(len(first['excluded_physical_ranges']),2)

    def test_exclusion_is_physical_across_contexts_not_logical_pc(self):
        different=MPR.copy();different[2]=140
        report=capture([observation(),observation(mpr=different),observation(0x4002,(0x0B,))])
        with tempfile.TemporaryDirectory() as temp:
            manifest=emit_capture(report,Path(temp)/'new',exclude_ranges=[(0x100000,1)])
        self.assertEqual(manifest['excluded_observations'],1)
        self.assertEqual(manifest['native_instructions_emitted'],1)
        self.assertEqual(manifest['native_contexts'],1)
        self.assertEqual(manifest['unsupported_observations'],1)

    def test_invalid_exclusion_ranges_create_no_output(self):
        malformed=[None,True,'0:1',[(1,)],[(1,2,3)],[(True,1)],[(1,False)],
                   [(-1,1)],[(0,0)],[(0x200000,1)],[(0x1fffff,2)],[(1,1.0)],
                   [(0,1)]*257]
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'new'
            for ranges in malformed:
                with self.subTest(ranges=ranges):
                    with self.assertRaises(ValueError):emit_capture(capture(),out,exclude_ranges=ranges)
                    self.assertFalse(out.exists())

    def test_cli_exclusion_hex_decimal_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'capture.json';raw=json.dumps(capture()).encode();source.write_bytes(raw)
            out=Path(temp)/'new'
            self.assertEqual(main(['emit-capture',str(source),'--out',str(out),
                                  '--exclude-range','0x100001:1','--exclude-range','2097151:1']),0)
            manifest=json.loads((out/'module.json').read_text())
            self.assertEqual(manifest['excluded_observations'],1)
            self.assertEqual(source.read_bytes(),raw)
            invalid=Path(temp)/'invalid'
            self.assertEqual(main(['emit-capture',str(source),'--out',str(invalid),
                                  '--exclude-range','0x1fffff:2']),2)
            self.assertFalse(invalid.exists())

    def test_partitioned_source_identity_and_size(self):
        import hashlib
        # Authored observations span a page split, a page gap, a second MPR
        # context and same-PC source variants. No captured retail bytes.
        other = MPR.copy(); other[4] = 140
        items = [observation(0x4000 + i, (0xea,)) for i in range(9)]
        items += [observation(0x4004, (0xa9, 17)), observation(0x4200, (0xea,)),
                  observation(0xffff, (0xa9, 29)), observation(mpr=other)]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'new'
            manifest = emit_capture(capture(items), out, partition_size=4)
            self.assertTrue(manifest['partitioned'])
            self.assertEqual(manifest['largest_partition_instructions'], 4)
            self.assertEqual(manifest['native_instructions_emitted'], len(items))
            self.assertEqual(manifest['translation_units'][0]['file'], 'module.cpp')
            units = {entry['file']: (out/entry['file']).read_text()
                     for entry in manifest['translation_units']}
            self.assertGreater(len(units), 2)
            self.assertNotIn('s.a=17;', units['module.cpp'])
            self.assertIn('switch(s.pc >> 8)', units['module.cpp'])
            self.assertIn('if(s.pc <= ', units['module.cpp'])
            variants = [text for name, text in units.items() if name != 'module.cpp' and 'case 16388:' in text]
            self.assertEqual(len(variants), 1)
            self.assertIn('s.a=17;', variants[0])
            for entry in manifest['translation_units'] + manifest['generated_headers']:
                self.assertEqual(Path(entry['file']).name, entry['file'])
                self.assertEqual(hashlib.sha256((out/entry['file']).read_bytes()).hexdigest(), entry['sha256'])
            self.assertTrue(all('#include "module_part_' not in text for text in units.values()))
            all_code = ''.join(units.values())
            self.assertNotIn('interpret_step(', all_code)
            self.assertIn('bus.peek(8191)', all_code)
            self.assertIn('bus.peek(2088960)', all_code)

    def test_partition_variant_group_can_exceed_target_and_single_unit(self):
        items = [observation(raw=(0xa9, n)) for n in range(7)]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = capture(items)
            manifest = emit_capture(report, root/'parts', partition_size=2)
            self.assertEqual(manifest['largest_partition_instructions'], 7)
            self.assertEqual(len(manifest['translation_units']), 2)
            one = emit_capture(report, root/'one', partition_size=2, single_unit=True)
            self.assertFalse(one['partitioned'])
            self.assertEqual(one['generated_headers'], [])
            self.assertEqual(len(one['translation_units']), 1)
            self.assertEqual((root/'one'/'module.cpp').read_text().count('case 16384:'), 1)
            # Part boundaries and provenance are deterministic under input order.
            again = emit_capture(capture(list(reversed(items))), root/'again',
                                 manifest['code_capture_sha256'], partition_size=2)
            self.assertEqual(manifest, again)
            for path in (root/'parts').iterdir():
                self.assertEqual(path.read_bytes(), (root/'again'/path.name).read_bytes())

    def test_exact_operand_keys_share_only_identical_translated_bodies(self):
        # Block operands are fetched live after stack writes: these distinct
        # exact source identities share one translated operation safely.
        items = [observation(raw=(0x73, 1, 2, 3, 4, 5, 6)),
                 observation(raw=(0x73, 6, 5, 4, 3, 2, 1))]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            blocks = emit_capture(capture(items), root/'blocks')
            code = (root/'blocks'/'module.cpp').read_text()
            self.assertEqual(blocks['native_instructions_emitted'], 2)
            self.assertEqual(blocks['translated_body_count'], 1)
            self.assertEqual(blocks['dispatch_strategy'], 'full_mpr_pc_opcode_operand_key')
            self.assertEqual(code.count('bus.begin_instruction(s);'), 1)
            self.assertIn('case 6618611909121ULL:', code)
            self.assertIn('case 1108152157446ULL:', code)
            # All seven source bytes are observed; only exact keys are cases.
            for address in range(0x100000, 0x100007):
                self.assertEqual(code.count(f'bus.peek({address})'), 1)
            self.assertIn('std::uint64_t(*operand_5) << 40', code)
            self.assertIn('if(!operand_5) return Exit::miss;', code)
            self.assertIn('default: return Exit::miss;', code)
            literals = emit_capture(capture([observation(raw=(0xa9,42)),
                                             observation(raw=(0xa9,43)),
                                             observation(raw=(0xad,0x34,0x12))]), root/'literals')
            code = (root/'literals'/'module.cpp').read_text()
            self.assertEqual(literals['translated_body_count'], 3)
            self.assertIn('s.a=42;', code)
            self.assertIn('s.a=43;', code)
            self.assertIn('case 42ULL:', code)
            self.assertIn('case 43ULL:', code)
            self.assertIn('case 4660ULL:', code)
            self.assertEqual(code.count('const auto opcode=bus.peek('), 1)
            self.assertEqual(code.count('bus.begin_instruction(s);'), 3)
            # Every source read precedes the corresponding translated body.
            self.assertLess(code.index('if(!opcode)'), code.index('bus.begin_instruction(s);'))

    def test_default_partition_threshold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            items = [observation(0x4000+i, (0xea,)) for i in range(257)]
            one = emit_capture(capture(items[:256], capacity=512), root/'one')
            parts = emit_capture(capture(items, capacity=512), root/'parts')
            self.assertFalse(one['partitioned'])
            self.assertEqual(len(one['translation_units']), 1)
            self.assertTrue(parts['partitioned'])
            self.assertEqual(parts['partition_size'], 256)
            self.assertEqual(parts['largest_partition_instructions'], 256)
            self.assertEqual(len(parts['translation_units']), 3)

    def test_invalid_partition_options_create_no_output(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'new'
            for size in (0, 4097, -1, True, 1.5, '256', None):
                with self.subTest(size=size):
                    with self.assertRaises(ValueError):
                        emit_capture(capture(), out, partition_size=size)
                    self.assertFalse(out.exists())
            for option in (0, 1, 'true', None):
                with self.assertRaises(ValueError):
                    emit_capture(capture(), out, single_unit=option)
                self.assertFalse(out.exists())

    def test_cli_partition_controls_and_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'capture.json'
            source.write_text(json.dumps(capture([observation(0x4000+i, (0xea,)) for i in range(5)])))
            self.assertEqual(main(['emit-capture', str(source), '--out', str(root/'parts'),
                                   '--partition-size', '2']), 0)
            self.assertTrue(json.loads((root/'parts'/'module.json').read_text())['partitioned'])
            self.assertEqual(main(['emit-capture', str(source), '--out', str(root/'one'),
                                   '--partition-size', '2', '--single-unit']), 0)
            self.assertFalse(json.loads((root/'one'/'module.json').read_text())['partitioned'])
            self.assertEqual(main(['emit-capture', str(source), '--out', str(root/'bad'),
                                   '--partition-size', '4097']), 2)
            self.assertFalse((root/'bad').exists())

    def test_runtime_length_table_matches_all_decoder_opcodes(self):
        import re
        header=(Path(__file__).resolve().parent.parent/'runtime/include/pce/code_capture.hpp').read_text()
        match=re.search(r'lengths\{([0-9,]+)\}',header)
        self.assertIsNotNone(match)
        lengths=[int(value) for value in match.group(1).split(',')]
        self.assertEqual(len(lengths),256)
        for opcode,length in enumerate(lengths):
            instruction=decode(lambda address: opcode if address==0x4000 else 0,
                               0x4000,tuple(MPR))
            self.assertEqual(length,len(instruction.data),f'opcode {opcode:02X}')

    def test_all_native_encodings_decode_emit(self):
        from pcerecomp.isa import NATIVE, _ROWS, _LENGTH
        items = [observation(0x4000+i*8, (i,)+tuple([0]*(_LENGTH[_ROWS[i].split('.')[1]]-1))) for i in NATIVE]
        with tempfile.TemporaryDirectory() as temp:
            manifest = emit_capture(capture(items, capacity=512), Path(temp)/'new')
        self.assertEqual(manifest['native_instructions_emitted'], len(NATIVE))

    def test_metadata_and_boolean_rejections(self):
        valid = capture()
        for field, value in [('schema', True), ('schema', 2), ('runtime_abi', True), ('runtime_abi', ABI + 1),
                             ('capacity', True), ('capacity', 0), ('capacity', 65537),
                             ('dropped_instructions', -1), ('retired_instructions', 0),
                             ('unreadable_instructions', 1<<64), ('complete', 1), ('complete', False)]:
            with self.subTest(field=field, value=value):
                broken=copy.deepcopy(valid);broken[field]=value
                with self.assertRaises(ValueError): validate_capture(broken)
        for field in valid:
            broken=copy.deepcopy(valid);del broken[field]
            with self.assertRaises(ValueError): validate_capture(broken)
        broken=copy.deepcopy(valid);broken['extra']=0
        with self.assertRaises(ValueError): validate_capture(broken)

    def test_identity_and_numeric_rejections(self):
        valid=capture()
        for field, value in [('pc', True), ('pc', 65536), ('mpr', [0]*7), ('mpr', [True]*8),
                             ('data', []), ('data', [0xa9]), ('data', [0xea, 0]),
                             ('data', [256]), ('physical', [0x200000, 0]),
                             ('physical', [0x100001, 0x100002]), ('native_hits', True),
                             ('native_hits', -1), ('interpreted_hits', 1<<64)]:
            with self.subTest(field=field,value=value):
                broken=copy.deepcopy(valid);broken['observations'][0][field]=value
                with self.assertRaises(ValueError): validate_capture(broken)
        for field in valid['observations'][0]:
            broken=copy.deepcopy(valid);del broken['observations'][0][field]
            with self.assertRaises(ValueError): validate_capture(broken)

    def test_zero_duplicate_and_capacity_rejected(self):
        with self.assertRaises(ValueError): validate_capture(capture([observation(),observation()]))
        with self.assertRaises(ValueError): validate_capture(capture([observation(interpreted=0)]))
        with self.assertRaises(ValueError): validate_capture(capture([observation(),observation(raw=(0xea,))],capacity=1))

    def test_incomplete_retirement_accounting(self):
        report=capture(dropped=42,unreadable=7)
        self.assertFalse(report['complete'])
        self.assertEqual(len(validate_capture(report)),1)
        report['retired_instructions']-=1
        with self.assertRaises(ValueError):validate_capture(report)

    def test_fresh_output_and_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'existing';out.mkdir()
            with self.assertRaises(ValueError):emit_capture(capture(),out)
            self.assertFalse(list(out.iterdir()))
            for digest in ('A'*64,'a'*63,False):
                with self.assertRaises(ValueError):emit_capture(capture(),Path(temp)/'new',digest)

    def test_load_digest_cli_and_duplicate_json(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'capture.json';raw=json.dumps(capture()).encode();source.write_bytes(raw)
            report,digest=load_capture(source)
            self.assertEqual(digest,hashlib.sha256(raw).hexdigest())
            out=Path(temp)/'module'
            self.assertEqual(main(['emit-capture',str(source),'--out',str(out)]),0)
            self.assertEqual(json.loads((out/'module.json').read_text())['code_capture_sha256'],digest)
            self.assertEqual(source.read_bytes(),raw)
            source.write_text('{"schema":1,"schema":1}')
            with self.assertRaises(ValueError):load_capture(source)

    def test_file_size_bound(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'capture.json';source.write_text(json.dumps(capture()))
            with patch('pcerecomp.capture.MAX_CAPTURE_BYTES',32):
                with self.assertRaises(ValueError):load_capture(source)


if __name__=='__main__':unittest.main()
