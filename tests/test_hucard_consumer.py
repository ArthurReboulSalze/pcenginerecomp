"""Authored HuCard schema, pinned input and typed initial-state receipt tests."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from pcerecomp.abi import ABI
from pcerecomp import project
import test_project as _project_tests


class HuCardConsumerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = _project_tests.ConsumerProjectTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.descriptor = self.fixture.root, self.fixture.descriptor
        self.snapshot_text = self.fixture.text
        self.rom = self.root/'authored.pce'
        image = bytearray(8192)
        image[8190:8192] = bytes((0x21, 0xE3))
        self.rom.write_bytes(image)
        boot = f'''[boot]
mode = "hucard-reset"
profile = "base"
header = "none"
encoding = "linear"
[cartridge]
path = "authored.pce"
sha256 = "{project.sha256(self.rom)}"
'''
        start, end = self.snapshot_text.index('[payload]'), self.snapshot_text.index('[runtime]')
        self.text = self.snapshot_text[:start]+boot+self.snapshot_text[end:]
        self.descriptor.write_text(self.text)

    def verify(self):
        return project.verify(self.descriptor, allow_revision_override=True)

    def boot(self):
        return dict(mode='hucard-reset', profile='base', initialization='gear-deterministic-zero-v1',
                    vector_physical=8190, pc=0xE321, a=0, x=0, y=0, sp=0, p=4,
                    clock_divisor=12, ticks=0, cycles=0, mpr=[0]*8,
                    header='none', encoding='linear', rom_bytes=8192, cd=False)

    def execute(self, directory, binary, name, boot, mutate=None):
        actual = project.subprocess.run

        def run(command, **arguments):
            if command[0] == str(binary):
                if mutate:
                    mutate()
                return subprocess.CompletedProcess(command, 0, json.dumps(
                    dict(native_steps=7, interpreter_steps=3, boot=boot)))
            return actual(command, **arguments)

        with patch.object(project.subprocess, 'run', side_effect=run):
            return project.run(self.descriptor, directory, self.root/(name+'.json'), allow_revision_override=True)

    def test_hucard_recipe_binds_raw_file_and_generates_only_explicit_entry_grammar(self):
        checked = self.verify()
        self.assertEqual(checked['identities']['cartridge'], project.sha256(self.rom))
        self.assertNotIn('payload', checked['files'])
        command = project.command_for(checked, self.root/'runner.exe', dev_port=0, start_paused=True)
        self.assertEqual(command[1:4], ['--hucard-reset', 'base', str(self.rom)])
        for option, value in (('--rom-header', 'none'), ('--rom-encoding', 'linear'), ('--cd-unknown-status', 'fault')):
            self.assertEqual(command[command.index(option)+1], value)
        self.assertNotIn('--bios', command)
        self.assertNotIn('--cartridge', command)
        self.assertEqual(checked['config']['tool']['runtime_abi'], ABI)

    def test_enhanced_recipes_pin_explicit_board_and_typed_initial_metadata(self):
        for profile, size, metadata in (('sf2', 0x280000, {'mapper_latch': 0}),
                                        ('populous', 0x80000, {'cartridge_ram_bytes': 32768})):
            with self.subTest(profile=profile):
                image = bytearray(size)
                image[8190:8192] = bytes((0x21, 0xE3))
                self.rom.write_bytes(image)
                text = self.text.replace('profile = "base"', f'profile = "{profile}"')
                old_hash = self.text.split('[cartridge]')[1].split('sha256 = "')[1].split('"')[0]
                self.descriptor.write_text(text.replace(old_hash, project.sha256(self.rom)))
                checked = self.verify()
                command = project.command_for(checked, self.root/'runner.exe')
                self.assertEqual(command[1:4], ['--hucard-reset', profile, str(self.rom)])
                boot = self.boot() | {'profile': profile, 'rom_bytes': size} | metadata
                self.assertEqual(project._boot_provenance(checked, {'boot': boot}), {'valid': True})
                key, value = next(iter(metadata.items()))
                for bad in (True, float(value), value+1):
                    self.assertFalse(project._boot_provenance(checked, {'boot': boot | {key: bad}})['valid'])
                missing = dict(boot)
                del missing[key]
                self.assertFalse(project._boot_provenance(checked, {'boot': missing})['valid'])
                self.assertFalse(project._boot_provenance(checked, {'boot': boot | {'extra': 0}})['valid'])

    def test_enhanced_wrong_size_or_inactive_rom_mutation_is_not_accepted(self):
        for profile in ('sf2', 'populous'):
            self.descriptor.write_text(self.text.replace('profile = "base"', f'profile = "{profile}"'))
            with self.assertRaisesRegex(ValueError, 'requires exactly'):
                self.verify()
        image = bytearray(0x280000)
        image[8190:8192] = bytes((0x21, 0xE3))
        self.rom.write_bytes(image)
        old_hash = self.text.split('[cartridge]')[1].split('sha256 = "')[1].split('"')[0]
        text = self.text.replace('profile = "base"', 'profile = "sf2"').replace(old_hash, project.sha256(self.rom))
        self.descriptor.write_text(text)
        checked = self.verify()
        image[-1] = 1
        self.rom.write_bytes(image)
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.verify()
        self.assertFalse(project._boot_provenance(checked, {'boot': self.boot() | {
            'profile': 'sf2', 'rom_bytes': len(image), 'mapper_latch': 0}})['valid'])

    def test_other_startup_recipes_cannot_attach_cartridge(self):
        cart = self.text[self.text.index('[cartridge]'):self.text.index('[runtime]')]
        self.descriptor.write_text(self.snapshot_text+cart)
        with self.assertRaisesRegex(ValueError, 'Cartridge requires'):
            self.verify()

    def test_hucard_rejects_cd_assets_and_missing_cartridge(self):
        for name in ('bios', 'bram', 'disc', 'toc', 'libchdr'):
            with self.subTest(name=name):
                self.descriptor.write_text(self.text+f'\n[{name}]\npath="missing"\nsha256="'+('0'*64)+'"\n')
                with self.assertRaisesRegex(ValueError, 'excludes'):
                    self.verify()
        self.descriptor.write_text(self.text[:self.text.index('[cartridge]')]+self.text[self.text.index('[runtime]'):])
        with self.assertRaisesRegex(ValueError, 'requires cartridge'):
            self.verify()

    def test_hucard_requires_declared_supported_board_and_dump_policy(self):
        for old, new in (('profile = "base"', 'profile = "super"'),
                         ('header = "none"', 'header = "auto"'),
                         ('encoding = "linear"', 'encoding = "usa"'),
                         ('cd_unknown_status = "fault"', 'cd_unknown_status = "gear-good"'),
                         ('cd_unknown_status = "fault"', 'cd_unknown_status = "nec-invalid"')):
            self.descriptor.write_text(self.text.replace(old, new))
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.verify()
        self.descriptor.write_text(self.text.replace('header = "none"\n', ''))
        with self.assertRaises(ValueError):
            self.verify()

    def test_opaque_copier_header_remains_hash_pinned(self):
        self.rom.write_bytes(bytes(512)+self.rom.read_bytes())
        text = self.text.replace('header = "none"', 'header = "copier512"')
        original_hash = self.text.split('sha256 = "')[-1].split('"')[0]  # module/input hashes are independent
        text = text.replace(original_hash, project.sha256(self.rom))
        self.descriptor.write_text(text)
        checked = self.verify()
        expected = self.boot() | {'header': 'copier512'}
        self.assertEqual(project._boot_provenance(checked, {'boot': expected}), {'valid': True})
        raw = self.rom.read_bytes()
        self.rom.write_bytes(bytes((1,))+raw[1:])
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.verify()

    def test_correct_typed_reset_report_qualifies_without_claiming_emission_is_execution(self):
        directory, binary = self.fixture.build_fixture()
        receipt = self.execute(directory, binary, 'valid-reset', self.boot())
        self.assertTrue(receipt['qualified'])
        self.assertEqual(receipt['boot_validation'], {'valid': True})
        self.assertEqual((receipt['work']['native'], receipt['work']['interpreted']), (7, 3))
        self.assertTrue(receipt['input_hashes_unchanged']['cartridge'])

    def test_metadata_mismatch_cannot_qualify_even_with_exit_zero_and_valid_work_counts(self):
        directory, binary = self.fixture.build_fixture()
        changes = [dict(pc=0), dict(profile='standard'), dict(cd=0), dict(cd=True),
                   dict(header='copier512'), dict(encoding='bit-reversed'), dict(rom_bytes=8192.0),
                   dict(clock_divisor=3), dict(ticks=True), dict(mpr=[0]*7+[False]), dict(extra='ignored')]
        for index, change in enumerate(changes):
            report = self.boot() | change
            result = self.execute(directory, binary, 'invalid-reset-'+str(index), report)
            self.assertFalse(result['qualified'])
            self.assertFalse(result['boot_validation']['valid'])
            self.assertEqual(result['result']['boot'], report)

    def test_cartridge_mutation_during_run_remains_visible_in_failed_receipt(self):
        directory, binary = self.fixture.build_fixture()
        def mutate():
            raw = self.rom.read_bytes()
            self.rom.write_bytes(bytes((raw[0]^255,))+raw[1:])
        receipt = self.execute(directory, binary, 'changed-input', self.boot(), mutate)
        self.assertFalse(receipt['qualified'])
        self.assertFalse(receipt['input_hashes_unchanged']['cartridge'])
