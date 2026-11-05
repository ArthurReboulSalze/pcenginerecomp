"""Boundaries of the test-only SingleStepTests/huc6280 adapter.

No corpus, ROM, BIOS or emulator is needed: every vector below is authored here, with
expectations written by hand from the instruction definitions. The probe-based cases
run when the CMake-built probe is available (PCE_TEST_HUC6280_PROBE, set by check.py).
"""
import json
import copy
from types import SimpleNamespace
from unittest import mock
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from scripts import huc6280_vector_reference as ref

MPR = [0xFF, 0xF8, 0x80, 0x81, 0x82, 0x83, 0x84, 0x00]
PROBE = os.environ.get('PCE_TEST_HUC6280_PROBE')


def encode_state(s):
    data = struct.pack('<i', 0) + struct.pack('5B', s['a'], s['x'], s['y'], s['s'], s['p'])
    data += struct.pack('<H', s['pc']) + bytes(s['mpr']) + struct.pack('<i', len(s['ram']))
    for address, value in s['ram']:
        data += struct.pack('<IB', address, value)
    return data


def encode_file(vectors):
    data = struct.pack('<I', len(vectors))
    for v in vectors:
        data += struct.pack('<i', 0) + v['name'].encode().ljust(50) + struct.pack('<I', v['opcode'])
        data += encode_state(v['init']) + encode_state(v['fin'])
        data += struct.pack('<II', v['cycles'], v['stored']) + b'\0\0\0\0' * v['stored']
    return data


def state(a=0, x=0, y=0, s=0, p=0, pc=0x4000, mpr=None, ram=()):
    return dict(a=a, x=x, y=y, s=s, p=p, pc=pc, mpr=list(mpr or MPR), ram=list(ram))


def lda(name='LDA #$80', **overrides):
    # Logical $4000 is MPR2 = page $80, physical $100000. LDA #$80 from P=$04: A=$80, N set.
    code = [(0x100000, 0xA9), (0x100001, 0x80)]
    v = dict(name=name, opcode=0xA9, init=state(p=0x04, ram=code), fin=state(a=0x80, p=0x84, pc=0x4002, ram=code),
             cycles=2, stored=2)
    v.update(overrides)
    return v


class CorpusIdentity(unittest.TestCase):
    def test_manifest_pins_all_256_files_and_their_digest_of_digests(self):
        manifest = ref.load_manifest()
        self.assertEqual(len(manifest), 256)
        self.assertEqual(ref.digest_of_digests(manifest),
                         '975fdd41fe27a62e6f145bc7d393d4ce4f1e31ea43fd64cbfda44ec789b6c7e0')
        self.assertTrue(all(name.startswith('v1/') and name.endswith('.json.bin') for name in manifest))

    def test_verification_fails_closed_on_tamper_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'v1').mkdir()
            good = Path(folder) / 'v1' / '00.json.bin'
            good.write_bytes(b'abc')
            manifest = {'v1/00.json.bin': (ref.hashlib.sha256(b'abc').hexdigest(), 3)}
            self.assertEqual(ref.verify_corpus(folder, manifest), 3)
            good.write_bytes(b'abd')
            with self.assertRaises(ValueError):
                ref.verify_corpus(folder, manifest)
            good.write_bytes(b'abc')
            (Path(folder) / 'v1' / '01.json.bin').write_bytes(b'x')
            with self.assertRaises(ValueError):
                ref.verify_corpus(folder, manifest)
            (Path(folder) / 'v1' / '01.json.bin').unlink()
            good.unlink()
            with self.assertRaises(ValueError):
                ref.verify_corpus(folder, manifest)

    def test_report_path_must_be_new_and_is_checked_before_any_work(self):
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / 'report.json'
            existing.write_text('{}')
            with self.assertRaises(FileExistsError):
                ref.main(['run', folder, '--build', folder, '--out', str(existing)])


class DecoderAndSelection(unittest.TestCase):
    def test_decoder_reads_what_the_documented_layout_encodes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'a9.json.bin'
            path.write_bytes(encode_file([lda(), lda('second')]))
            vectors = ref.read_vectors(path)
        self.assertEqual([v['name'] for v in vectors], ['LDA #$80', 'second'])
        self.assertEqual(vectors[0]['init']['mpr'], MPR)
        self.assertEqual(vectors[0]['fin']['a'], 0x80)
        self.assertEqual(vectors[0]['fin']['ram'], [(0x100000, 0xA9), (0x100001, 0x80)])
        self.assertEqual((vectors[0]['cycles'], vectors[0]['stored']), (2, 2))

    def test_decoder_refuses_truncated_files_and_out_of_range_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'a9.json.bin'
            path.write_bytes(struct.pack('<I', 1))
            with self.assertRaises(struct.error):
                ref.read_vectors(path)
            path.write_bytes(struct.pack('<I', 100001))
            with self.assertRaises(ValueError):
                ref.read_vectors(path)

    def test_cut_vectors_are_detected_by_cycle_or_ram_pair_cap(self):
        self.assertFalse(ref.truncated(lda()))
        self.assertTrue(ref.truncated(lda(stored=500)))
        many = [(0x100000 + i, 0) for i in range(500)]
        self.assertTrue(ref.truncated(lda(init=state(ram=many))))

    def test_native_selection_is_deterministic_and_explicit_about_exclusions(self):
        distinct = lda('a')
        repeated = lda('b', init=state(mpr=[1, 1, 2, 3, 4, 5, 6, 7]), fin=state(mpr=[1, 1, 2, 3, 4, 5, 6, 7]))
        moved = lda('c', fin=state(mpr=[0, 1, 2, 3, 4, 5, 6, 7]))
        cut = lda('d', stored=500)
        tma = lda('e', opcode=0x43)
        non_native = lda('f', opcode=0x0B)
        also_good = lda('g')
        selected, excluded = ref.select_native([non_native, repeated, moved, cut, tma, distinct, also_good], 1, {0xA9, 0x43})
        self.assertEqual([v['name'] for v in selected], ['a'])
        self.assertEqual(sum(excluded.values()), 5)
        selected, _ = ref.select_native([distinct, also_good], 5, {0xA9})
        self.assertEqual([v['name'] for v in selected], ['a', 'g'])

    def test_canonical_frame_keeps_each_cell_in_its_logical_window(self):
        converted = ref.to_canonical(lda())
        self.assertEqual([c[0] for c in converted['init']['ram']], [0x22 << 13, (0x22 << 13) + 1])
        self.assertEqual(converted['init']['mpr'], MPR)  # the original frame is kept for the record
        stray = lda(init=state(p=0x04, ram=[(0x0123456 & 0x1FFFFF, 0)]))
        self.assertIsNone(ref.to_canonical(stray))

    def test_groups_never_overlap_or_flow_into_each_other(self):
        sites = [(lda('a'), {}, {0x4000, 0x4001}, {0x4002}),
                 (lda('b'), {}, {0x4001, 0x4002}, {0x4003}),   # overlaps a
                 (lda('c'), {}, {0x5000}, {0x4000}),           # flows into a
                 (lda('d'), {}, {0x6000}, {0x6001})]
        modules = ref.group_modules(sites)
        self.assertEqual([[v['name'] for v, _ in m['items']] for m in modules], [['a', 'd'], ['b', 'c']])


class ClosedProbeReports(unittest.TestCase):
    def row(self):
        return dict(tier='interpreter', opcode='A9', vectors=1, executed=1, refused=0, faulted=0,
                    state_not_comparable=0, state_equal=1, state_different=0, cycles_equal=1,
                    cycles_different=0, both_equal=1,
                    classes=dict(registers=0, flags=0, pc=0, mpr=0, memory=0))

    def test_rows_require_complete_typed_conserved_results(self):
        row = self.row()
        self.assertEqual(ref.validate_rows([row], {'A9': 1}, 'interpreter'), [row])
        invalid = [[], [row, row]]
        for field, value in [('vectors', 2), ('executed', True), ('both_equal', 2),
                             ('state_equal', 0), ('opcode', 'A8'), ('tier', 'native')]:
            bad = copy.deepcopy(row); bad[field] = value; invalid.append([bad])
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                ref.validate_rows(rows, {'A9': 1}, 'interpreter')

    def test_strict_json_and_opcode_selection(self):
        for raw in ['noise', '{"tier":1,"tier":2}', '{"count":NaN}', '[]']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                ref.parse_lines(raw)
        for ops in ['', '100', '-1', 'a9,a9', 'a9,', 'a9xyz']:
            with self.subTest(ops=ops), self.assertRaises(ValueError):
                ref.requested_opcodes(ops)
        self.assertEqual(ref.requested_opcodes('a9,01'), [1, 169])

    def test_first_difference_survives_two_matching_modules(self):
        good = self.row(); good['tier'] = 'native'
        bad = copy.deepcopy(good)
        bad.update(state_equal=0, state_different=1, both_equal=0,
                   first_difference=dict(vector='third module', classes_mask=2))
        bad['classes']['flags'] = 1
        result = ref.merge_rows([good, good, bad])[0]
        self.assertEqual(result['state_different'], 1)
        self.assertEqual(result['first_difference']['vector'], 'third module')
        self.assertNotIn('first_difference', good)

    def run_report(self, folder, output, *, mutate=False):
        (folder / 'v1').mkdir()
        source = folder / 'v1/a9.json.bin'
        data = encode_file([lda()]); source.write_bytes(data)
        probe = folder / 'pce-huc6280-vector-probe.exe'; probe.write_bytes(b'authored probe placeholder')
        library = folder / 'libpce-runtime.a'; library.write_bytes(b'authored library placeholder')
        manifest = {'v1/a9.json.bin': (ref.hashlib.sha256(data).hexdigest(), len(data))}
        args = SimpleNamespace(out=folder / 'report.json', corpus=folder, build=folder,
                               ops='a9', timeout=5, compiler=None)
        def child(*a, **kw):
            kw['log'].write_text(output, encoding='utf-8')
            if mutate:
                source.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
            return output
        with mock.patch.object(ref, 'load_manifest', return_value=manifest), mock.patch.object(ref, 'find_probe', return_value=probe), mock.patch.object(ref, 'run_command', side_effect=child):
            return ref.command_run(args)

    def test_empty_probe_cannot_publish_a_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaises(ValueError):
                self.run_report(folder, '')
            self.assertFalse((folder / 'report.json').exists())
            self.assertFalse((folder / 'report.json.closed.json').exists())
            self.assertTrue((folder / 'report.json.artifacts/interpreter.jsonl').exists())

    def test_input_mutation_refuses_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaises(ValueError):
                self.run_report(folder, json.dumps(self.row()), mutate=True)
            self.assertFalse((folder / 'report.json').exists())

    def test_closed_report_binds_actual_inputs_and_raw_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(self.run_report(folder, json.dumps(self.row())), 0)
            report = json.loads((folder / 'report.json').read_text())
            closed = json.loads((folder / 'report.json.closed.json').read_text())
            self.assertEqual(closed['report_sha256'], ref.sha256_file(folder / 'report.json'))
            self.assertFalse(report['qualification'])
            self.assertEqual(report['toolkit']['inputs']['runtime_library']['sha256'], ref.sha256_file(folder / 'libpce-runtime.a'))
            self.assertIn('interpreter.jsonl', report['artifacts'])


@unittest.skipUnless(PROBE and Path(PROBE).is_file(), 'Build the huc6280 vector probe (set by scripts/check.py)')
class ProbeFlagsBadResults(unittest.TestCase):
    def run_probe(self, files, ops):
        with tempfile.TemporaryDirectory() as folder:
            for name, data in files.items():
                (Path(folder) / name).write_bytes(data)
            return subprocess.run([PROBE, 'interp', folder, ops], capture_output=True, text=True, timeout=60)

    def test_invalid_opcode_and_trailing_bytes_refuse(self):
        for ops in ['100', 'a9,a9', 'a9junk', '']:
            self.assertEqual(self.run_probe({}, ops).returncode, 2)
        self.assertEqual(self.run_probe({'a9.json.bin': encode_file([lda()]) + b'extra'}, 'a9').returncode, 2)

    def test_selftest_passes(self):
        self.assertEqual(subprocess.run([PROBE, 'selftest'], capture_output=True, timeout=60).returncode, 0)

    def test_good_and_bad_vectors_are_told_apart_and_reported_in_separate_classes(self):
        wrong_register = lda('wrong register', fin=state(a=0x81, p=0x84, pc=0x4002, ram=[(0x100000, 0xA9), (0x100001, 0x80)]))
        wrong_flag = lda('wrong flag', fin=state(a=0x80, p=0xC4, pc=0x4002, ram=[(0x100000, 0xA9), (0x100001, 0x80)]))
        wrong_cycles = lda('wrong cycles', cycles=3)
        cut = lda('cut at the cap', stored=500, fin=state(a=0x00, p=0x00, pc=0x4002))
        result = self.run_probe({'a9.json.bin': encode_file([lda(), wrong_register, wrong_flag, wrong_cycles, cut])}, 'a9')
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout.strip().splitlines()[0])
        self.assertEqual((row['vectors'], row['executed'], row['refused'], row['faulted']), (5, 5, 0, 0))
        self.assertEqual((row['state_equal'], row['state_different'], row['state_not_comparable']), (2, 2, 1))
        self.assertEqual((row['cycles_equal'], row['cycles_different'], row['both_equal']), (4, 1, 1))
        self.assertEqual(row['classes'], dict(registers=1, flags=1, pc=0, mpr=0, memory=0))
        self.assertEqual(row['first_difference']['vector'], 'wrong register')

    def test_reserved_opcode_is_listed_as_refused_not_skipped(self):
        reserved = lda('reserved', opcode=0x0B, init=state(p=0x04, ram=[(0x100000, 0x0B), (0x100001, 0x00)]))
        result = self.run_probe({'0b.json.bin': encode_file([reserved])}, '0b')
        row = json.loads(result.stdout.strip().splitlines()[0])
        self.assertEqual((row['vectors'], row['refused'], row['executed']), (1, 1, 0))

    def test_malformed_and_mismatched_files_stop_the_run(self):
        self.assertEqual(self.run_probe({'a9.json.bin': struct.pack('<I', 1)}, 'a9').returncode, 2)
        wrong_file = lda(opcode=0xA2)
        self.assertEqual(self.run_probe({'a9.json.bin': encode_file([wrong_file])}, 'a9').returncode, 2)


if __name__ == '__main__':
    unittest.main()
