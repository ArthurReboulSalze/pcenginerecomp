"""Authored lossless archive/decoder checks; no game captures or live journals."""
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.dev_journal_archive import archive_wire_journal, main
from scripts.dev_journal_audit import JournalValidationError, MAX_LINE, audit_wire_journal
from tests.test_dev_journal_audit import frame, session, request, response, failure


class JournalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'wire.jsonl'
        self.target = self.root / 'wire.jsonl.gz'
        self.raw = b''.join(frame(x) for x in (session(), request(), response()))
        self.source.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()

    def archive(self, **options):
        return archive_wire_journal(self.source, self.target, expected_sha256=self.sha,
                                    offline=True, **options)

    def compressed(self, raw=None):
        self.target.write_bytes(gzip.compress(self.raw if raw is None else raw, mtime=0))
        return self.target

    def test_archive_preserves_exact_bytes_events_and_original(self):
        before = self.source.stat()
        receipt = self.archive()
        plain, compressed = [], []
        a = audit_wire_journal(self.source, visit=plain.append)
        b = audit_wire_journal(self.target, encoding='gzip', expected_sha256=self.sha,
                               expected_storage_sha256=receipt['archive_sha256'], visit=compressed.append)
        self.assertEqual(gzip.decompress(self.target.read_bytes()), self.raw)
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertEqual(self.source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(plain, compressed)
        for key in ('sha256', 'bytes', 'records', 'ending', 'commands', 'forensic_prefix'):
            self.assertEqual(a[key], b[key])
        self.assertEqual(receipt['journal_sha256'], self.sha)
        self.assertEqual(b['storage_encoding'], 'gzip')
        self.assertFalse(list(self.root.glob('.pce-wire-*')))
        self.assertNotIn('connection_closed', receipt)

    def test_offline_declaration_and_retained_hash_mandatory(self):
        for declaration in (False, None, 1, 'true'):
            with self.assertRaises(JournalValidationError):
                archive_wire_journal(self.source, self.target, expected_sha256=self.sha,
                                     offline=declaration)
        with self.assertRaises(JournalValidationError):
            archive_wire_journal(self.source, self.target, expected_sha256=None, offline=True)
        self.assertFalse(self.target.exists())

    def test_existing_destinations_including_source_and_hardlink_refused(self):
        self.target.write_bytes(b'owner data')
        with self.assertRaises(FileExistsError): self.archive()
        self.assertEqual(self.target.read_bytes(), b'owner data')
        with self.assertRaises(FileExistsError):
            archive_wire_journal(self.source, self.source, expected_sha256=self.sha, offline=True)
        self.target.unlink()
        self.target.hardlink_to(self.source)
        with self.assertRaises(FileExistsError): self.archive()
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_gzip_container_truncation_never_accepted_as_forensic_journal(self):
        whole = gzip.compress(self.raw, mtime=0)
        for raw in (b'', whole[:1], whole[:10], whole[:-1], whole[:-8], whole[:len(whole)//2]):
            with self.subTest(size=len(raw)):
                self.target.write_bytes(raw)
                with self.assertRaises(JournalValidationError):
                    audit_wire_journal(self.target, encoding='gzip', allow_incomplete=True)

    def test_crc_trailing_bytes_padding_and_second_member_refused(self):
        whole = gzip.compress(self.raw, mtime=0)
        corrupt = bytearray(whole); corrupt[-8] ^= 1
        for raw in (bytes(corrupt), whole+b'x', whole+b'\0', whole+whole):
            with self.subTest(size=len(raw)):
                self.target.write_bytes(raw)
                with self.assertRaises(JournalValidationError):
                    audit_wire_journal(self.target, encoding='gzip')

    def test_encoding_explicit_and_both_digests_checked(self):
        self.compressed()
        for options in ({}, {'encoding': 'auto'}, {'encoding': 'plain'},
                        {'encoding': 'gzip', 'expected_sha256': '0'*64},
                        {'encoding': 'gzip', 'expected_storage_sha256': '0'*64}):
            with self.subTest(options=options), self.assertRaises(JournalValidationError):
                audit_wire_journal(self.target, **options)
        with self.assertRaises(JournalValidationError):
            audit_wire_journal(self.source, encoding='gzip')

    def test_empty_valid_container_is_not_a_journal_and_optional_header_is_lossless(self):
        self.compressed(b'')
        with self.assertRaisesRegex(JournalValidationError, 'session is missing'):
            audit_wire_journal(self.target, encoding='gzip')
        original = gzip.compress(self.raw, mtime=123456)
        header = bytearray(original[:10]); header[3] |= 8  # Legal FNAME header.
        self.target.write_bytes(bytes(header) + b'authored-name.jsonl\0' + original[10:])
        result = audit_wire_journal(self.target, encoding='gzip', expected_sha256=self.sha)
        self.assertEqual(result['bytes'], len(self.raw))

    def test_digest_types_are_not_coerced(self):
        self.compressed()
        for key in ('expected_sha256', 'expected_storage_sha256'):
            for value in (True, 1, b'0'*64, 'A'*64, '0'*63):
                with self.subTest(key=key, value=value), self.assertRaises(JournalValidationError):
                    audit_wire_journal(self.target, encoding='gzip', **{key: value})

    def test_unpaired_prefix_requires_explicit_forensic_archive(self):
        self.raw = frame(session()) + frame(request())
        self.source.write_bytes(self.raw); self.sha = hashlib.sha256(self.raw).hexdigest()
        with self.assertRaises(JournalValidationError): self.archive()
        receipt = self.archive(allow_incomplete=True)
        self.assertTrue(receipt['forensic_prefix'])
        self.assertEqual(receipt['ending'], 'unpaired-intent')
        self.assertTrue(receipt['record_stream_complete'])
        with self.assertRaises(JournalValidationError): audit_wire_journal(self.target, encoding='gzip')

    def test_truncated_outer_record_preserved_exactly_only_as_forensic(self):
        self.raw += b'{"schema":1'
        self.source.write_bytes(self.raw); self.sha = hashlib.sha256(self.raw).hexdigest()
        receipt = self.archive(allow_incomplete=True)
        self.assertFalse(receipt['record_stream_complete'])
        self.assertTrue(receipt['forensic_prefix'])
        self.assertEqual(gzip.decompress(self.target.read_bytes()), self.raw)

    def test_invalid_response_with_failure_preserves_raw_diagnostic(self):
        self.raw = b''.join(frame(x) for x in (session(), request(), response(raw=b'\xff\n'), failure(3)))
        self.source.write_bytes(self.raw); self.sha = hashlib.sha256(self.raw).hexdigest()
        self.archive()
        events = []
        result = audit_wire_journal(self.target, encoding='gzip', visit=events.append)
        self.assertEqual(result['ending'], 'recorded-failure')
        self.assertEqual(events[2].wire, b'\xff\n')

    def test_source_mutation_after_initial_audit_refused_without_publication(self):
        import scripts.dev_journal_archive as module
        original = module.audit_wire_journal
        def mutate(path, **kwargs):
            result = original(path, **kwargs)
            if Path(path) == self.source:
                self.source.write_bytes(self.raw + b'\n')
            return result
        with patch.object(module, 'audit_wire_journal', mutate):
            with self.assertRaises(JournalValidationError): self.archive()
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.root.glob('.pce-wire-*')))

    def test_source_digest_mismatch_refused_before_output(self):
        self.sha = '0'*64
        with self.assertRaises(JournalValidationError): self.archive()
        self.assertFalse(self.target.exists())

    def test_fsync_failure_preserves_original_and_cleans_owned_temp(self):
        with patch('scripts.dev_journal_archive.os.fsync', side_effect=OSError('authored fsync failure')):
            with self.assertRaises(OSError): self.archive()
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.root.glob('.pce-wire-*')))

    def test_publication_failure_does_not_overwrite_racing_destination(self):
        def race(*_):
            self.target.write_bytes(b'new owner file')
            raise FileExistsError('racing destination')
        with patch('scripts.dev_journal_archive.os.link', side_effect=race):
            with self.assertRaises(FileExistsError): self.archive()
        self.assertEqual(self.target.read_bytes(), b'new owner file')
        self.assertFalse(list(self.root.glob('.pce-wire-*')))

    def test_large_compressed_record_limit_is_decompressed_limit(self):
        self.compressed(b'x'*(MAX_LINE+1))
        with self.assertRaisesRegex(JournalValidationError, 'record exceeds'):
            audit_wire_journal(self.target, encoding='gzip', allow_incomplete=True)

    def test_many_records_and_boundary_sized_payload_roundtrip(self):
        self.raw = b''.join(frame(x) for x in (session(), *[
            r for i in range(1, 401) for r in (request(i), response(i, raw=frame(dict(id=i, ok=True, x='a'*2048))))]))
        self.source.write_bytes(self.raw); self.sha = hashlib.sha256(self.raw).hexdigest()
        self.archive()
        result = audit_wire_journal(self.target, encoding='gzip', expected_sha256=self.sha)
        self.assertEqual(result['response_frames'], 400)
        self.assertLess(result['storage_bytes'], result['bytes'])

    def test_gzip_callback_remains_provisional_until_hash_and_stability(self):
        self.compressed()
        seen = []
        with self.assertRaisesRegex(JournalValidationError, 'SHA256'):
            audit_wire_journal(self.target, encoding='gzip', expected_sha256='0'*64, visit=seen.append)
        self.assertEqual(len(seen), 3)
        def append(_):
            with self.target.open('ab') as stream: stream.write(b'!')
        with self.assertRaises(JournalValidationError):
            audit_wire_journal(self.target, encoding='gzip', visit=append)

    def test_cli_explicit_archive_then_audit(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = main([str(self.source), str(self.target), '--sha256', self.sha, '--offline'])
        self.assertEqual(status, 0)
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt['journal_sha256'], self.sha)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.source), str(self.target), '--sha256', self.sha, '--offline']), 1)


if __name__ == '__main__':
    unittest.main()
