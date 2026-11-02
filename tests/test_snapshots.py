"""Authored content/alias/transaction fixtures; no SDK or retail evidence."""
from dataclasses import FrozenInstanceError
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.snapshots import FileSnapshot, JsonSnapshot, SnapshotError, SnapshotStore


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class GuardedRead:
    def __init__(self, stream, sizes):
        self.stream, self.sizes = stream, sizes

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def fileno(self):
        return self.stream.fileno()

    def read(self, size):
        if not 0 < size <= 1024 * 1024:
            raise AssertionError('Binary snapshot attempted an unbounded read')
        self.sizes.append(size)
        return self.stream.read(size)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).absolute()

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def rewrite_preserving_mtime(self, path, raw):
        old = path.stat()
        self.assertEqual(len(raw), old.st_size)
        path.write_bytes(raw)
        os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
        self.assertEqual(path.stat().st_mtime_ns, old.st_mtime_ns)
        self.assertEqual(path.stat().st_size, old.st_size)

    def junction(self, target, link):
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        else:
            link.symlink_to(target, target_is_directory=True)

    def unlink_junction(self, link):
        if os.name == 'nt':
            link.rmdir()
        else:
            link.unlink()

    def test_json_hash_and_value_use_exact_original_bytes(self):
        raw = b'{ "elapsed":1.25, "items":[null,true,7,7.0,{"label":"authored"}] }\n'
        path = self.write('input.json', raw)
        snapshot = SnapshotStore().read_json(path, expected_sha256=digest(raw))
        self.assertEqual(snapshot.raw, raw)
        self.assertEqual(snapshot.sha256, digest(raw))
        self.assertEqual(snapshot.size_bytes, len(raw))
        self.assertEqual(snapshot.path, path)
        self.assertEqual(snapshot.value, {'elapsed': 1.25, 'items': [None, True, 7, 7.0, {'label': 'authored'}]})
        self.assertIs(type(snapshot.value['items'][1]), bool)
        self.assertIs(type(snapshot.value['items'][2]), int)
        self.assertIs(type(snapshot.value['items'][3]), float)

    def test_unicode_and_finite_timing_values_preserved(self):
        raw = '{"name":"猫","elapsed":1e-3,"negative_zero":-0.0}'.encode('utf-8')
        snapshot = SnapshotStore().read_json(self.write('unicode.json', raw))
        self.assertEqual(snapshot.value['name'], '猫')
        self.assertEqual(snapshot.value['elapsed'], 0.001)
        self.assertEqual(math.copysign(1.0, snapshot.value['negative_zero']), -1.0)

    def test_detached_nested_values_cannot_poison_cached_parse(self):
        path = self.write('value.json', b'{"nested":[{"items":[1,2]}],"flag":true}')
        snapshot = SnapshotStore().read_json(path)
        value = snapshot.value
        value['nested'][0]['items'].append(3)
        value['flag'] = False
        value['new'] = 'changed'
        self.assertEqual(snapshot.value, {'nested': [{'items': [1, 2]}], 'flag': True})
        with self.assertRaises(TypeError):
            snapshot._frozen_value['flag'] = False
        with self.assertRaises(TypeError):
            snapshot._frozen_value['nested'][0]['items'][0] = 99
        with self.assertRaises(FrozenInstanceError):
            snapshot.raw = b'changed'

    def test_reference_and_epoch_maps_are_detached(self):
        path = self.write('binary.bin', b'abc')
        store = SnapshotStore()
        snapshot = store.bind(path)
        reference = snapshot.reference()
        reference['sha256'] = '0' * 64
        bindings = store.bindings()
        bindings.clear()
        self.assertEqual(snapshot.sha256, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(store.bindings(), {str(path): snapshot.sha256})
        self.assertEqual(snapshot.reference(), {'path': str(path), 'sha256': snapshot.sha256})

    def test_binary_empty_artifact_is_valid_but_empty_json_is_not(self):
        path = self.write('empty.bin', b'')
        store = SnapshotStore()
        self.assertEqual(store.bind(path).sha256, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        with self.assertRaises(SnapshotError):
            store.read_json(path)
        self.assertEqual(len(store.bindings()), 1)
        invalid = SnapshotStore()
        with self.assertRaises(SnapshotError):
            invalid.read_json(path)
        self.assertEqual(invalid.bindings(), {})

    def test_repeated_json_read_checks_bytes_but_parses_once(self):
        path = self.write('once.json', b'{"elapsed":2.5}')
        store = SnapshotStore()
        with patch('pcerecomp.snapshots.json.loads', wraps=json.loads) as parse:
            first = store.read_json(path)
            first.value['elapsed'] = 100
            second = store.read_json(path)
            self.assertIs(first, second)
            self.assertEqual(second.value, {'elapsed': 2.5})
            self.assertEqual(parse.call_count, 1)

    def test_binary_to_json_registration_joins_same_epoch(self):
        path = self.write('joined.json', b'[null,false,1,1.0]')
        store = SnapshotStore()
        binary = store.bind(path)
        parsed = store.read_json(path, expected_sha256=binary.sha256)
        self.assertEqual(parsed.reference(), binary.reference())
        self.assertEqual(parsed.value, [None, False, 1, 1.0])
        self.assertEqual(store.bind(path), binary)

    def test_json_re_read_refuses_same_size_restored_mtime_change(self):
        path = self.write('changed.json', b'{"value":1}')
        store = SnapshotStore()
        old = store.read_json(path)
        self.rewrite_preserving_mtime(path, b'{"value":2}')
        with self.assertRaisesRegex(SnapshotError, 'changed'):
            store.read_json(path)
        self.assertEqual(old.value, {'value': 1})
        self.assertEqual(store.bindings(), {str(path): old.sha256})

    def test_parse_and_digest_cannot_describe_different_file_versions(self):
        before, after = b'{"value":1}', b'{"value":2}'
        path = self.write('parse-race.json', before)
        original_parse = json.loads
        def mutate_while_parsing(text, **kwargs):
            self.rewrite_preserving_mtime(path, after)
            return original_parse(text, **kwargs)
        store = SnapshotStore()
        with patch('pcerecomp.snapshots.json.loads', side_effect=mutate_while_parsing):
            snapshot = store.read_json(path)
        self.assertEqual(snapshot.raw, before)
        self.assertEqual(snapshot.sha256, digest(before))
        self.assertEqual(snapshot.value, {'value': 1})
        self.assertEqual(path.read_bytes(), after)
        with self.assertRaises(SnapshotError):
            store.revalidate()

    def test_binary_epoch_cache_is_not_a_current_content_claim(self):
        path = self.write('binary.bin', b'first')
        store = SnapshotStore()
        old = store.bind(path)
        self.rewrite_preserving_mtime(path, b'other')
        self.assertIs(store.bind(path, expected_sha256=old.sha256), old)
        with self.assertRaises(SnapshotError):
            store.revalidate()
        self.assertEqual(store.bindings(), {str(path): old.sha256})

    def test_expected_digest_mismatch_never_registers(self):
        path = self.write('mismatch.json', b'{"ok":true}')
        for method in ('bind', 'read_json'):
            with self.subTest(method=method):
                store = SnapshotStore()
                with self.assertRaisesRegex(SnapshotError, 'SHA256'):
                    getattr(store, method)(path, expected_sha256='0' * 64)
                self.assertEqual(store.bindings(), {})

    def test_expected_digest_conflict_refuses_before_io(self):
        path = self.write('bound.json', b'{}')
        store = SnapshotStore()
        store.read_json(path)
        with patch('pcerecomp.snapshots._read', side_effect=AssertionError('Unexpected file read')):
            for method in ('bind', 'read_json'):
                with self.subTest(method=method), self.assertRaisesRegex(SnapshotError, 'conflicts'):
                    getattr(store, method)(path, expected_sha256='0' * 64)
            with self.assertRaisesRegex(SnapshotError, 'conflicts'):
                store.bind_all({str(path): '0' * 64})

    def test_invalid_digest_refuses_before_io(self):
        store = SnapshotStore()
        with patch('pcerecomp.snapshots._read', side_effect=AssertionError('Unexpected file read')):
            for value in (True, 7, '', 'A' * 64, 'f' * 63, 'g' * 64):
                with self.subTest(value=value), self.assertRaises(SnapshotError):
                    store.bind(self.root / 'missing', expected_sha256=value)
        self.assertEqual(store.bindings(), {})

    def test_strict_json_refusals_do_not_adopt_a_new_epoch(self):
        values = [b'{"x":1,"x":2}', b'{"nested":{"x":1,"x":2}}', b'{"a":1,"\\u0061":2}',
                  b'{"v":NaN}', b'[Infinity]', b'{"v":-Infinity}', b'{"nested":[1e9999]}',
                  b'\xff', b'\xef\xbb\xbf{}', '{}'.encode('utf-16'), '{}'.encode('utf-32'),
                  b'{', b'{} extra', b'   ']
        for number, raw in enumerate(values):
            with self.subTest(raw=raw):
                store = SnapshotStore()
                with self.assertRaises(SnapshotError):
                    store.read_json(self.write(f'bad-{number}.json', raw))
                self.assertEqual(store.bindings(), {})

    def test_json_byte_bound_is_explicit_and_adjustable(self):
        raw = b'{"text":"' + b'x' * 128 + b'"}'
        path = self.write('large.json', raw)
        store = SnapshotStore()
        with self.assertRaisesRegex(SnapshotError, 'byte limit'):
            store.read_json(path, max_bytes=16)
        self.assertEqual(store.bindings(), {})
        self.assertEqual(store.read_json(path, max_bytes=len(raw)).value['text'], 'x' * 128)
        for maximum in (0, -1, True, 1.5):
            with self.subTest(maximum=maximum), self.assertRaises(SnapshotError):
                SnapshotStore().read_json(path, max_bytes=maximum)

    def test_bind_all_failed_graph_is_transactional(self):
        a, b = self.write('a.bin', b'a'), self.write('b.bin', b'b')
        store = SnapshotStore()
        initial = store.bind(a)
        with self.assertRaises(SnapshotError):
            store.bind_all({str(b): digest(b'b'), str(self.root / 'missing.bin'): '0' * 64})
        self.assertEqual(store.bindings(), {str(a): initial.sha256})
        with self.assertRaises(SnapshotError):
            store.bind_all({str(b): digest(b'b'), str(a): '0' * 64})
        self.assertEqual(store.bindings(), {str(a): initial.sha256})

    def test_explicit_graph_rejects_relative_or_nested_bindings(self):
        for bindings in ({'relative.bin': 'a' * 64}, {str(self.root / 'a'): {'sha256': 'a' * 64}}, [], None):
            with self.subTest(bindings=bindings):
                store = SnapshotStore()
                with self.assertRaises(SnapshotError):
                    store.bind_all(bindings)
                self.assertEqual(store.bindings(), {})

    def test_normalized_graph_alias_conflict_refuses_before_io(self):
        path = self.root / 'a.bin'
        alias = str(self.root / 'unused' / '..' / 'a.bin')
        with patch('pcerecomp.snapshots._read', side_effect=AssertionError('Unexpected file read')):
            with self.assertRaisesRegex(SnapshotError, 'normalized'):
                SnapshotStore().bind_all({str(path): 'a' * 64, alias: 'b' * 64})

    def test_json_embedded_references_are_not_followed(self):
        missing = str(self.root / 'not-present.bin')
        path = self.write('metadata.json', json.dumps({'input_bindings': {missing: 'a' * 64}}).encode())
        store = SnapshotStore()
        store.read_json(path)
        self.assertEqual(set(store.bindings()), {str(path)})

    def test_streamed_overlapping_graph_hashes_each_new_file_once(self):
        raw = b'authored-binary-' * 220000
        paths = [self.write(name + '.bin', raw + name.encode()) for name in ('a', 'b', 'c')]
        hashes = [digest(raw + name.encode()) for name in ('a', 'b', 'c')]
        real_open = Path.open
        opens, sizes = [], []
        def counted(path, mode='r', *args, **kwargs):
            if mode == 'rb':
                opens.append(str(path))
                return GuardedRead(real_open(path, mode, *args, **kwargs), sizes)
            return real_open(path, mode, *args, **kwargs)
        store = SnapshotStore()
        with patch.object(Path, 'open', counted):
            store.bind_all({str(paths[0]): hashes[0], str(paths[1]): hashes[1]})
            store.bind_all({str(paths[1]): hashes[1], str(paths[2]): hashes[2]})
            store.bind(paths[0], expected_sha256=hashes[0])
            self.assertEqual(opens, list(map(str, paths)))
            store.revalidate()
            self.assertEqual(len(opens), 6)
        self.assertTrue(sizes and all(0 < n <= 1024 * 1024 for n in sizes))

    def test_case_only_spellings_remain_distinct_epoch_keys(self):
        lower = self.write('case.bin', b'same-content')
        upper = self.root / 'CASE.BIN'
        if not upper.exists():
            upper.write_bytes(b'same-content')
        store = SnapshotStore()
        store.bind_all({str(lower): digest(b'same-content'), str(upper): digest(b'same-content')})
        self.assertEqual(set(store.bindings()), {str(lower), str(upper)})
        self.assertNotEqual(store.bind(lower), store.bind(upper))
        real_open, opened = Path.open, []
        def counted(path, *args, **kwargs):
            opened.append(str(path))
            return real_open(path, *args, **kwargs)
        with patch.object(Path, 'open', counted):
            store.revalidate()
        self.assertEqual(set(opened), {str(lower), str(upper)})
        self.assertEqual(len(opened), 2)

    def test_directory_alias_retarget_to_identical_bytes_refused(self):
        a = self.write('target-a/data.json', b'{"same":true}')
        b = self.write('target-b/data.json', b'{"same":true}')
        alias = self.root / 'alias'
        self.junction(a.parent, alias)
        try:
            path = alias / 'data.json'
            store = SnapshotStore()
            snapshot = store.read_json(path)
            self.assertEqual(snapshot.reference()['path'], str(path))
            self.unlink_junction(alias)
            self.junction(b.parent, alias)
            with self.assertRaisesRegex(SnapshotError, 'alias target'):
                store.revalidate()
            with self.assertRaisesRegex(SnapshotError, 'alias target'):
                store.read_json(path)
            self.assertEqual(snapshot.value, {'same': True})
        finally:
            self.unlink_junction(alias)

    def test_every_alias_is_revalidated_instead_of_old_resolved_target(self):
        a = self.write('first/file.bin', b'first')
        b = self.write('other/file.bin', b'other')
        alias = self.root / 'alias'
        self.junction(a.parent, alias)
        try:
            path = alias / 'file.bin'
            store = SnapshotStore()
            store.bind(a)
            store.bind(path)
            self.assertEqual(set(store.bindings()), {str(a), str(path)})
            self.unlink_junction(alias)
            self.junction(b.parent, alias)
            with self.assertRaises(SnapshotError):
                store.revalidate()
        finally:
            self.unlink_junction(alias)

    def test_direct_snapshot_constructor_enforces_raw_binding(self):
        path = self.root / 'not-opened.json'
        with self.assertRaises(SnapshotError):
            JsonSnapshot(path, '0' * 64, 2, b'{}')
        with self.assertRaises(SnapshotError):
            JsonSnapshot(path, digest(b'{}'), 2, bytearray(b'{}'))
        with self.assertRaises(SnapshotError):
            FileSnapshot(path, digest(b''), True)

    def test_non_regular_or_missing_inputs_never_register(self):
        for path in (self.root, self.root / 'missing'):
            store = SnapshotStore()
            with self.subTest(path=path), self.assertRaises(SnapshotError):
                store.bind(path)
            self.assertEqual(store.bindings(), {})


if __name__ == '__main__':
    unittest.main()
