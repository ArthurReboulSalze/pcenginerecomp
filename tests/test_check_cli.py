"""Check-runner deadlines without recursively executing the real suites."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts import build_config

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/check.py'


class CheckRunnerCliTests(unittest.TestCase):
    def invoke(self, arguments, *, failure=None):
        with patch.object(sys, 'argv', [str(SCRIPT), *arguments]), \
             patch.dict(sys.modules, {'build_config': build_config}), \
             patch.object(build_config, 'cmake_cache', return_value=None) as cache, \
             patch.object(subprocess, 'run', side_effect=failure) as execute:
            runpy.run_path(str(SCRIPT), run_name='__main__')
            return execute.call_args_list, cache

    def test_default_suite_deadline_and_individual_native_deadlines(self):
        calls, cache = self.invoke([])
        cache.assert_called_once()
        self.assertEqual(calls[0].args[0], [sys.executable, '-m', 'unittest', 'discover',
                                          '-s', 'tests', '-p', 'test_*.py', '-v'])
        self.assertEqual(calls[0].kwargs['timeout'], 600)
        self.assertEqual(len(calls), 73)  # Python, 71 non-SDL native suites, fresh-process audio helper.
        vectors = [call for call in calls[1:] if Path(call.args[0][0]).stem == 'pce-huc6280-vector-probe']
        self.assertEqual([call.args[0][1:] for call in vectors], [['selftest']])
        self.assertTrue(any('pce-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-checkpoint-audio-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-cd-read-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-cd-adpcm-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-dma-irq-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-block-dma-irq-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-vdc-adpcm-irq-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-cdda-gap-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-vdc-latch-checkpoint-tests' in str(call.args[0][0]) for call in calls[1:]))
        self.assertTrue(any('pce-adpcm-irq-tests' in str(call.args[0][0]) for call in calls[1:]))
        for suite in ('pce-cd-timing-tests', 'pce-cd-timing-checkpoint-tests',
                      'pce-subchannel-tests', 'pce-subchannel-sector-tests',
                      'pce-reference-execution-tests', 'pce-reference-policy-tests'):
            selected = [call for call in calls[1:] if Path(call.args[0][0]).stem == suite]
            self.assertEqual(len(selected), 1)
        self.assertTrue(all(call.kwargs['check'] is True for call in calls))
        self.assertTrue(all(call.kwargs['timeout'] == 60 for call in calls[1:]))

    def test_unknown_cd_suite_runs_once_with_its_native_deadline(self):
        calls, _ = self.invoke([])
        unknown = [call for call in calls[1:]
                   if Path(call.args[0][0]).stem == 'pce-cd-unknown-tests']
        self.assertEqual(len(unknown), 1)
        suffix = '.exe' if sys.platform == 'win32' else ''
        self.assertEqual(unknown[0].args[0],
                         [str(ROOT/'build'/('pce-cd-unknown-tests' + suffix))])
        self.assertIs(unknown[0].kwargs['check'], True)
        self.assertEqual(unknown[0].kwargs['timeout'], 60)

    def test_explicit_finite_python_deadline_is_forwarded_without_changing_suites(self):
        baseline, _ = self.invoke([])
        for seconds in (1, 180, 600, 900, 86400):
            with self.subTest(seconds=seconds):
                calls, _ = self.invoke(['--python-timeout', str(seconds)])
                self.assertEqual(calls[0].kwargs['timeout'], seconds)
                self.assertEqual([call.args for call in calls], [call.args for call in baseline])
                self.assertTrue(all(call.kwargs['timeout'] == 60 for call in calls[1:]))

    def test_invalid_deadline_rejected_before_cache_or_execution(self):
        for value in ('0', '-1', '86401', '18446744073709551616', '1.5', 'inf', 'true'):
            with self.subTest(value=value), \
                 patch.object(sys, 'argv', [str(SCRIPT), '--python-timeout', value]), \
                 patch.dict(sys.modules, {'build_config': build_config}), \
                 patch.object(build_config, 'cmake_cache') as cache, \
                 patch.object(subprocess, 'run') as execute, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as rejected:
                    runpy.run_path(str(SCRIPT), run_name='__main__')
                self.assertEqual(rejected.exception.code, 2)
                cache.assert_not_called()
                execute.assert_not_called()

    def test_python_timeout_stops_before_any_native_suite(self):
        failure = subprocess.TimeoutExpired(['authored-suite'], 900)
        with patch.object(sys, 'argv', [str(SCRIPT), '--python-timeout', '900']), \
             patch.dict(sys.modules, {'build_config': build_config}), \
             patch.object(build_config, 'cmake_cache', return_value=None), \
             patch.object(subprocess, 'run', side_effect=failure) as execute:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                runpy.run_path(str(SCRIPT), run_name='__main__')
            self.assertIs(caught.exception, failure)
            execute.assert_called_once()
            self.assertEqual(execute.call_args.kwargs['timeout'], 900)
