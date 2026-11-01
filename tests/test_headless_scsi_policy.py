"""Authored protocol traffic verifies the explicit unknown-command CLI policy."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
NAME = 'pce-headless.exe' if os.name == 'nt' else 'pce-headless'
CANDIDATES = ([Path(os.environ['PCE_TEST_HEADLESS'])] if 'PCE_TEST_HEADLESS' in os.environ else
              [ROOT/'build'/NAME, ROOT/'build/Release'/NAME])
BINARY = next((p for p in CANDIDATES if p.is_file()), None)


@unittest.skipUnless(BINARY, 'Build pce-headless for protocol policy checks')
class HeadlessScsiPolicyTests(unittest.TestCase):
    def test_cd_timing_defaults_and_explicit_profiles_are_reported(self):
        for extra, expected in (([], 'fixed'), (['--cd-timing', 'fixed'], 'fixed'),
                                (['--cd-timing', 'gear-distance'], 'gear-distance')):
            with self.subTest(profile=expected, arguments=extra):
                result = self.run_case(['--cd-unknown-status', 'gear-good', *extra])
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(json.loads(result.stdout)['cd_timing'], {'profile': expected})

    def test_cd_timing_refuses_invalid_and_duplicate_options(self):
        for extra in (['--cd-timing', 'fast'], ['--cd-timing', 'true'],
                      ['--cd-timing', 'fixed', '--cd-timing', 'gear-distance']):
            with self.subTest(arguments=extra):
                result = self.run_case(extra)
                self.assertEqual(result.returncode, 2, result.stdout+result.stderr)

    def run_case(self, options, command_bytes=1):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Select, poll REQ, submit the authored unknown bytes, raise/lower ACK,
            # then leave the returned status byte unacknowledged.
            code = [0xA9, 0, 0x8D, 0, 0x18]
            for _ in range(command_bytes):
                code += [0xAD, 0, 0x18, 0x29, 0x40, 0xF0, 0xF9,
                         0xA9, 0xFF, 0x8D, 1, 0x18,
                         0xA9, 0x80, 0x8D, 2, 0x18,
                         0xA9, 0, 0x8D, 2, 0x18]
            program = bytes(code+[0xAD, 0, 0x18, 0x80, 0xFE])
            image = root/'authored.bin'
            image.write_bytes(program)
            toc_text = 'PCE_TOC 1\nimage_sha256 ' + 'a'*64 + '\nleadout_lba 300\ntrack 1 0 4\n'
            toc = root/'metadata.toc'
            toc.write_text(toc_text, encoding='ascii')
            result = subprocess.run([str(BINARY), str(image), '0x100000', '0x4000',
                                     '255,248,128,129,130,131,132,0', '10000', '200000',
                                     'hybrid', '--toc', str(toc), *options],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(image.read_bytes(), program)
            self.assertEqual(toc.read_text(), toc_text)
            return result

    def test_strict_default_and_explicit_fault_refuse_unknown_command(self):
        for options in ([], ['--cd-unknown-status', 'fault']):
            with self.subTest(options=options):
                result = self.run_case(options)
                self.assertEqual(result.returncode, 3, result.stdout+result.stderr)
                state = json.loads(result.stdout)
                self.assertEqual(state['stop'], 'bus_fault')
                self.assertFalse(state['scsi']['reference_unknown_status'])
                self.assertEqual(state['scsi']['unknown_commands'], 0)
                self.assertEqual(state['scsi']['last_command'], [255])
                self.assertIn('unsupported CD command $FF', result.stderr)

    def test_reference_good_response_requires_explicit_selection(self):
        result = self.run_case(['--cd-unknown-status', 'gear-good'])
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        state = json.loads(result.stdout)
        self.assertTrue(state['scsi']['reference_unknown_status'])
        self.assertEqual(state['scsi']['unknown_commands'], 1)
        self.assertEqual(state['scsi']['last_command'], [255])
        self.assertEqual(state['scsi']['command_size'], 0)
        self.assertEqual((state['scsi']['phase'], state['scsi']['drive_data'], state['a']), (7, 0, 0xD8))

    def test_invalid_or_duplicate_policy_is_rejected(self):
        for options in (['--cd-unknown-status', 'good'],
                        ['--cd-unknown-status', 'gear-good', '--cd-unknown-status', 'fault']):
            with self.subTest(options=options):
                result = self.run_case(options)
                self.assertEqual(result.returncode, 2, result.stdout+result.stderr)

    def test_nec_invalid_waits_for_full_packet_and_reports_error(self):
        for count in (1, 9, 10):
            with self.subTest(command_bytes=count):
                result = self.run_case(['--cd-unknown-status', 'nec-invalid'], count)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                state = json.loads(result.stdout)
                diagnostic = state['cd_unknown']
                self.assertEqual(diagnostic['policy'], 'nec-invalid')
                self.assertFalse(state['scsi']['reference_unknown_status'])
                self.assertEqual(diagnostic['accepted_responses'], 0)
                if count < 10:
                    self.assertEqual(diagnostic['invalid_responses'], 0)
                    self.assertEqual(diagnostic['opcodes'], [])
                    self.assertEqual(state['scsi']['command_size'], count)
                    self.assertEqual(state['scsi']['phase'], 3)
                    self.assertNotIn('cd_sense', state)
                else:
                    self.assertEqual(diagnostic['invalid_responses'], 1)
                    self.assertEqual(diagnostic['opcodes'], [{'opcode': 255, 'attempts': 1}])
                    self.assertEqual(diagnostic['last_command'], [255]*10)
                    self.assertEqual(diagnostic['origin']['pc'], 0x400E)
                    self.assertEqual(diagnostic['origin']['physical_pc'], 0x10000E)
                    self.assertEqual(diagnostic['origin']['mpr'], [255,248,128,129,130,131,132,0])
                    self.assertEqual(diagnostic['origin']['fetch'], [0x8D,1,0x18,0xA9,0x80,0x8D,2])
                    self.assertEqual((state['scsi']['command_size'], state['scsi']['phase'],
                                      state['scsi']['drive_data']), (0, 7, 2))
                    self.assertEqual(state['cd_sense'], {
                        'commands': 0, 'errors': 1,
                        'pending': {'key': 5, 'asc': 32, 'ascq': 0, 'fru': 0, 'failed_lba': None}})


if __name__ == '__main__':
    unittest.main()
