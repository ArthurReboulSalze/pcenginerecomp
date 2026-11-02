"""Actual CLI tests using authored current-emitter files, never compiled/game code."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import cli
from pcerecomp.emitter import emit_capture
from tests.test_native_gaps import capture, row


class NativeGapCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = Path(__file__).resolve().parents[1]
        self.source = self.root / 'authored-original.json'
        self.module = self.root / 'authored-module'
        original = capture([row(native=10000, interpreted=20000),
                            row(0x4010, (0xEA,), native=30000, interpreted=0)], abi=18)
        self.source.write_text(json.dumps(original), encoding='utf8')
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        emit_capture(original, self.module, self.source_hash)
        self.manifest = self.module / 'module.json'

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, separators=(',', ':')), encoding='utf8')
        return path

    def command(self, captures, output):
        return ['native-gaps', str(self.manifest), *map(str, captures),
                '--observations', str(self.source), '--out', str(output)]

    def run_cli(self, arguments):
        return subprocess.run([sys.executable, '-B', '-m', 'pcerecomp', *arguments],
                              cwd=self.repo, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                              text=True, capture_output=True, timeout=30)

    def test_actual_two_window_cli_preserves_hashes_and_keeps_code_out_of_stdout(self):
        first = self.write('first-window.json', capture([row(native=4, interpreted=0),
                                                       row(data=(0xA9, 43), interpreted=3)], abi=28))
        second = self.write('second-window.json', capture([row(native=2, interpreted=1),
                                                         row(data=(0xA9, 43), interpreted=5)], abi=29))
        output = self.root / 'private' / 'gap-report.json'
        completed = self.run_cli(self.command([second, first], output))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        summary = json.loads(completed.stdout)
        report = json.loads(output.read_text())
        self.assertEqual(summary['summary'], report['summary'])
        self.assertEqual(summary['summary']['emitted_observed'], 1)
        self.assertEqual(summary['summary']['emitted_unexercised'], 1)
        self.assertEqual(summary['summary']['uncompiled_observed'], 1)
        expected = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)}
        self.assertEqual({item['sha256'] for item in report['inputs']}, expected)
        self.assertEqual({item['sha256'] for item in summary['inputs']}, expected)
        self.assertEqual(sorted((item['native_steps'], item['interpreter_steps'])
                                for item in report['inputs']), [(2, 6), (4, 3)])
        for text in (completed.stdout, output.read_text()):
            self.assertNotIn(str(self.root), text)
        for field in ('"identities"', '"physical"', '"mpr"', '"data"'):
            self.assertNotIn(field, completed.stdout)
        for field in ('native_steps', 'interpreter_steps', 'retired_instructions', 'native_fraction'):
            self.assertNotIn(field, summary['summary'])
        self.assertIs(summary['qualification'], False)
        self.assertIs(report['catalog']['provenance']['linked_binary_verified'], False)

    def test_existing_output_refuses_before_loading_catalog_or_reading_captures(self):
        output = self.root / 'keep.json'
        original = b'owner-authored output must remain exact\n'
        output.write_bytes(original)
        arguments = ['native-gaps', str(self.root / 'missing-module.json'),
                     str(self.root / 'missing-capture.json'), '--observations',
                     str(self.root / 'missing-observations.json'), '--out', str(output)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch('pcerecomp.native_catalog.load_native_catalog') as loader, \
                patch('pcerecomp.native_gaps.report_native_gaps') as reporter, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(arguments), 2)
        loader.assert_not_called()
        reporter.assert_not_called()
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('new private output', stderr.getvalue())
        self.assertEqual(output.read_bytes(), original)

    def test_invalid_capture_does_not_create_the_destination_or_parent(self):
        invalid = self.root / 'invalid-capture.json'
        invalid.write_text('{"schema":1,"schema":1,"untrusted":NaN}', encoding='utf8')
        output = self.root / 'not-created' / 'report.json'
        completed = self.run_cli(self.command([invalid], output))
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, '')
        self.assertFalse(output.exists())
        self.assertFalse(output.parent.exists())

    def test_actual_alias_order_is_stable_and_existing_report_is_never_replaced(self):
        first = self.write('zeta.json', capture([row(data=(0xA9, 43), interpreted=7)]))
        alias = self.root / 'alpha.json'
        alias.write_bytes(first.read_bytes())
        one, two = self.root / 'one.json', self.root / 'two.json'
        for captures, output in (([first, alias], one), ([alias, first], two)):
            completed = self.run_cli(self.command(captures, output))
            self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        report = json.loads(one.read_text())
        self.assertEqual(report['inputs'][0]['aliases'], ['alpha.json', 'zeta.json'])
        self.assertEqual(report['inputs'][0]['sha256'], hashlib.sha256(first.read_bytes()).hexdigest())
        original = one.read_bytes()
        completed = self.run_cli(self.command([first], one))
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, '')
        self.assertEqual(one.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
