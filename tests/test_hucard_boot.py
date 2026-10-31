"""Authored HuCard ROMs exercise the real reset grammar and TCP hosts.

No game, firmware, save or installed application input is used. Expectations
are literal base-profile values, separate from the independent Gear adapter.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from pcerecomp.abi import ABI
from pcerecomp.capture import load_capture
from scripts.dev_client import DevClient, DevError

ROOT = Path(__file__).resolve().parent.parent
EXE = '.exe' if os.name == 'nt' else ''
HEADLESS = Path(os.environ.get('PCE_TEST_HEADLESS', ROOT/'build'/('pce-headless'+EXE)))
DESKTOP = Path(os.environ.get('PCE_TEST_DESKTOP', 'disabled'))


def authored_hucard(program=b'\xea', pc=0xE100, banks=1):
    """Distinct bank markers with the authored program at each mirror site."""
    rom = bytearray(b''.join(bytes((bank,))*8192 for bank in range(banks)))
    offset = pc & 8191
    if offset+len(program) > 8190:
        raise ValueError('Authored program overlaps its reset vector')
    for bank in range(banks):
        rom[bank*8192+offset:bank*8192+offset+len(program)] = program
    rom[8190:8192] = pc.to_bytes(2, 'little')
    return bytes(rom)


def tcp_program():
    # Guest sets IO/WRAM, writes a result, then actually changes its executing
    # MPR7 to ROM bank40. On the selected 512KiB map it fetches file bank20.
    return bytes.fromhex(
        'A9 FF 53 01 A9 F8 53 02 A9 5A 8D 00 20 EE 00 20 '
        'A9 40 53 80 AD 00 E0 8D 01 20 A9 80 53 04 AD 00 40 '
        '8D 02 20 AD 00 18 8D 03 20 AD 00 10 8D 04 20 '
        'A9 00 8D 00 10 AD 00 10 8D 05 20 80 F3')


def psg_program():
    # Constant positive DDA input, all channel/global gains fully enabled.
    return bytes.fromhex(
        'A9 FF 53 01 A9 00 8D 00 08 A9 FF 8D 01 08 8D 05 08 '
        'A9 DF 8D 04 08 A9 1F 8D 06 08 80 FE')


class HuCardHostChecks:
    desktop = False

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.card = self.root/'authored HuCard.pce'
        self.environment = os.environ.copy()
        self.environment.update(SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software', SDL_AUDIODRIVER='dummy')

    def command(self, profile='base', steps=1, ticks=10000, tier='hybrid', options=(), audio='off'):
        command = [str(self.binary), '--hucard-reset', profile, str(self.card),
                   str(steps), str(ticks), tier, '--audio-output', audio, *options]
        if self.desktop:
            command += ['--hidden', 'on', '--unthrottled', 'on', '--window-scale', '1']
        return command

    def invoke(self, program=b'\xea', *, banks=1, pc=0xE100, **arguments):
        raw = authored_hucard(program, pc, banks)
        self.card.write_bytes(raw)
        result = subprocess.run(self.command(**arguments), env=self.environment,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(self.card.read_bytes(), raw)
        return result

    def state(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def expected_boot(self, *, pc=0xE100, banks=1, header='none', encoding='linear'):
        return dict(mode='hucard-reset', profile='base', initialization='gear-deterministic-zero-v1',
                    vector_physical=8190, pc=pc, a=0, x=0, y=0, sp=0, p=4,
                    clock_divisor=12, ticks=0, cycles=0, mpr=[0]*8,
                    header=header, encoding=encoding, rom_bytes=banks*8192, cd=False)

    def test_vector_initial_metadata_and_base_devices(self):
        state = self.state(self.invoke())
        self.assertEqual(state['boot'], self.expected_boot())
        self.assertEqual((state['pc'], state['ticks'], state['cycles']), (0xE101, 24, 2))
        self.assertEqual((state['a'], state['x'], state['y'], state['sp'], state['p']), (0, 0, 0, 0, 4))
        self.assertEqual(state['mpr'], [0]*8)
        self.assertEqual((state['native_steps'], state['interpreter_steps']), (0, 1))
        self.assertTrue(state['vdc']['enabled'])
        self.assertTrue(state['joypad']['enabled'])
        self.assertFalse(state['joypad']['cd'])
        self.assertFalse(state['cd_control']['enabled'])
        self.assertFalse(state['scsi']['enabled'])
        self.assertFalse(state['adpcm']['enabled'])
        self.assertFalse(state['toc']['attached'])

    def test_different_vector_is_not_an_injected_entry(self):
        state = self.state(self.invoke(bytes((0xA9, 0xC6)), pc=0xE6B2))
        self.assertEqual(state['boot'], self.expected_boot(pc=0xE6B2))
        self.assertEqual((state['pc'], state['a']), (0xE6B4, 0xC6))

    def test_special_rom_maps_and_absent_cd_ram(self):
        program = bytes.fromhex('A9 40 53 04 AD 00 40 AA A9 80 53 04 AD 00 40')
        for banks, marker in ((1, 0), (48, 32), (64, 32), (96, 64), (128, 64)):
            with self.subTest(banks=banks):
                state = self.state(self.invoke(program, banks=banks, steps=7))
                self.assertEqual((state['x'], state['a']), (marker, 255))
                self.assertFalse(state['cd_control']['enabled'])

    def test_absent_cd_and_unused_io_pullups_and_controller_presence(self):
        program = bytes.fromhex('A9 FF 53 01 AD 00 18 AA AD 00 1C A8 AD 00 10')
        for region, value in (('usa', 0xB0), ('japan', 0xF0)):
            with self.subTest(region=region):
                state = self.state(self.invoke(program, steps=7, options=['--joypad-region', region]))
                self.assertEqual((state['x'], state['y'], state['a']), (255, 255, value))

    def test_ignored_rom_and_absent_memory_writes(self):
        program = bytes.fromhex('A9 7B 8D 00 E1 AD 00 E1 AA A9 F7 53 04 A9 56 8D 00 40 AD 00 40')
        state = self.state(self.invoke(program, steps=9))
        self.assertEqual((state['x'], state['a']), (0xA9, 255))
        self.assertFalse(state['cd_control']['enabled'])

    def test_explicit_header_and_bit_encoding_are_not_inferred(self):
        decoded = authored_hucard(bytes.fromhex('A9 96'))
        reverse = lambda data: bytes(int(f'{value:08b}'[::-1], 2) for value in data)
        for header in ('none', 'copier512'):
            for encoding in ('linear', 'bit-reversed'):
                with self.subTest(header=header, encoding=encoding):
                    raw = (bytes((i*17+91) & 255 for i in range(512)) if header == 'copier512' else b'')
                    raw += reverse(decoded) if encoding == 'bit-reversed' else decoded
                    self.card.write_bytes(raw)
                    result = subprocess.run(self.command(options=['--rom-header', header, '--rom-encoding', encoding]),
                                            env=self.environment, capture_output=True, text=True, timeout=10)
                    state = self.state(result)
                    self.assertEqual((state['pc'], state['a']), (0xE102, 0x96))
                    self.assertEqual(state['boot'], self.expected_boot(header=header, encoding=encoding))
                    self.assertEqual(self.card.read_bytes(), raw)
        # A headered image is not stripped by size heuristics.
        result = subprocess.run(self.command(), env=self.environment, capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout), (2, ''))

    def test_actual_code_capture_retains_hucard_source_identity(self):
        capture_path = self.root/'actual.json'
        state = self.state(self.invoke(options=['--code-capture', str(capture_path)]))
        capture, _ = load_capture(capture_path)
        self.assertEqual(capture['runtime_abi'], ABI)
        self.assertEqual(capture['retired_instructions'], 1)
        self.assertEqual(capture['observations'], [dict(pc=0xE100, mpr=[0]*8, physical=[0x100],
                                                     data=[0xEA], native_hits=0, interpreted_hits=1)])
        self.assertEqual(state['boot'], self.expected_boot())

    def test_native_guard_miss_does_not_execute_reset_instruction(self):
        result = self.invoke(tier='native')
        state = json.loads(result.stdout)
        self.assertEqual((result.returncode, state['stop']), (3, 'guard_miss'))
        self.assertEqual((state['ticks'], state['pc'], state['native_steps'], state['interpreter_steps']), (0, 0xE100, 0, 0))
        self.assertEqual(state['boot'], self.expected_boot())

    def test_rejects_profiles_cd_inputs_duplicate_flags_and_snapshot_positionals(self):
        self.card.write_bytes(authored_hucard())
        for options in (['--bios', str(self.card)], ['--disc', 'unused.iso'], ['--toc', 'unused.toc'],
                        ['--bram', 'unused.bram'], ['--libchdr', 'unused.dll'],
                        ['--cd-unknown-status', 'gear-good'], ['--rom-header', 'auto'],
                        ['--rom-encoding', 'auto'], ['--rom-header', 'none', '--rom-header', 'none'],
                        ['0x100000', '0x4000']):
            with self.subTest(options=options):
                result = subprocess.run(self.command(options=options), env=self.environment,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual((result.returncode, result.stdout), (2, ''))
        for profile in ('standard', 'super', 'sgx', 'sf2', 'populous', 'BASE'):
            result = subprocess.run(self.command(profile=profile), env=self.environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
        # The consumer's strict default CD option is accepted without enabling CD.
        state = self.state(subprocess.run(self.command(options=['--cd-unknown-status', 'fault']),
                                         env=self.environment, capture_output=True, text=True, timeout=10))
        self.assertFalse(state['cd_control']['enabled'])

    def test_rejects_bad_sizes_before_creating_outputs(self):
        output = self.root/'must-not-exist.wav'
        for size in (0, 512, 8191, 8193, 1048577, 1049089):
            with self.subTest(size=size):
                self.card.write_bytes(bytes(size))
                result = subprocess.run(self.command(audio='on', options=['--audio-out', str(output), '--audio-frames', '64']),
                                        env=self.environment, capture_output=True, text=True, timeout=10)
                self.assertEqual((result.returncode, result.stdout), (2, ''))
                self.assertFalse(output.exists())
                self.assertEqual(self.card.stat().st_size, size)

    def test_rom_options_refused_outside_hucard_and_outputs_protect_input(self):
        self.card.write_bytes(authored_hucard())
        for flag, value in (('--rom-header', 'none'), ('--rom-encoding', 'linear')):
            for startup in ([str(self.card), '0x100000', '0x4000',
                             '255,248,128,129,130,131,132,0', '1', '1000', 'hybrid'],
                            ['--system-card-reset', 'standard', str(self.card), '1', '1000', 'hybrid']):
                result = subprocess.run([str(self.binary), *startup, flag, value], env=self.environment,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual((result.returncode, result.stdout), (2, ''))
                self.assertIn('require --hucard-reset', result.stderr)
        before = self.card.read_bytes()
        for options in (['--frame-out', str(self.card)], ['--code-capture', str(self.card)],
                        ['--audio-out', str(self.card)]):
            result = subprocess.run(self.command(audio='on', options=options), env=self.environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
            self.assertEqual(self.card.read_bytes(), before)

    def test_psg_only_audio_preserves_guest_state_and_never_enables_cd(self):
        self.card.write_bytes(authored_hucard(psg_program()))
        off = self.state(subprocess.run(self.command(steps=6000, ticks=1000000), env=self.environment,
                                       capture_output=True, text=True, timeout=10))
        output = self.root/'authored.wav'
        on = self.state(subprocess.run(self.command(steps=6000, ticks=1000000, audio='on',
                                                   options=['--audio-out', str(output), '--audio-frames', '1000']),
                                      env=self.environment, capture_output=True, text=True, timeout=10))
        keys = ('pc', 'a', 'x', 'y', 'sp', 'p', 'mpr', 'ticks', 'cycles', 'native_steps', 'interpreter_steps', 'boot')
        self.assertEqual({k: off[k] for k in keys}, {k: on[k] for k in keys})
        self.assertGreater(on['audio_output']['frames'], 0)
        self.assertGreater(on['audio_output']['psg_nonzero'], 0)
        self.assertEqual((on['audio_output']['adpcm_nonzero'], on['audio_output']['cdda_nonzero'],
                          on['audio_output']['discarded_frames']), (0, 0, 0))
        self.assertFalse(on['cd_control']['enabled'])
        self.assertFalse(on['scsi']['enabled'])
        self.assertFalse(on['adpcm']['enabled'])
        with wave.open(str(output), 'rb') as source:
            self.assertEqual((source.getnchannels(), source.getsampwidth(), source.getframerate()), (2, 2, 44100))
            self.assertGreater(source.getnframes(), 0)
            self.assertNotEqual(source.readframes(source.getnframes()), bytes(source.getnframes()*4))

    def test_tcp_initial_pause_mirrored_fetch_input_and_capture_without_ram_edits(self):
        raw = authored_hucard(tcp_program(), banks=64)
        self.card.write_bytes(raw)
        before_hash = hashlib.sha256(raw).hexdigest()
        process = subprocess.Popen(self.command(steps=10000000, ticks=10000000,
                                               options=['--dev-port', '0', '--dev-start-paused', 'on', '--wall-seconds', '10']),
                                   env=self.environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stderr.readline()
            self.assertTrue(line.startswith('PCE_DEV_PORT='), line)
            with DevClient(int(line.strip().split('=')[1]), timeout=5) as client:
                initial = client.call('status')
                self.assertEqual((initial['ticks'], initial['frame'], initial['paused']), (0, 0, True))
                self.assertEqual(initial['host']['boot'], self.expected_boot(banks=64))
                self.assertTrue(initial['host']['interrupts']['enabled'])
                self.assertFalse(initial['host']['cd_control']['enabled'])
                self.assertFalse(initial['host']['scsi']['enabled'])
                self.assertFalse(initial['host']['debug_memory']['write_enabled'])
                self.assertEqual(client.read_memory(0x80000, 1), bytes((32,)))
                self.assertEqual(client.read_memory(0x1F0000, 6), bytes(6))
                self.assertEqual(client.read_memory(0x1F6000, 6), bytes(6))
                client.call('set_input', mask=8, port=0)
                advanced = client.advance(2)
                self.assertEqual((advanced['frame'], advanced['paused']), (2, True))
                self.assertEqual(advanced['host']['buttons'][0], 8)
                self.assertEqual(advanced['host']['cpu']['mpr'], [255, 248, 128, 0, 0, 0, 0, 64])
                self.assertEqual(client.read_memory(0x1F0000, 6), bytes((0x5B, 32, 255, 255, 0xB0, 0xB7)))
                self.assertEqual(client.read_memory(0x1F6000, 6), bytes((0x5B, 32, 255, 255, 0xB0, 0xB7)))
                metadata, rgb = client.capture()
                self.assertEqual((metadata['width'], metadata['height'], metadata['frame']), (256, 240, 2))
                self.assertEqual(len(rgb), 256*240*3)
                client.call('set_input', mask=0, port=0)
                client.advance(1)
                self.assertEqual(client.call('status')['host']['buttons'][0], 0)
                self.assertEqual(client.read_memory(0x1F0005, 1), bytes((0xBF,)))
                client.call('quit')
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
            state = json.loads(stdout)
            self.assertEqual(state['stop'], 'dev_quit')
            self.assertEqual(state['boot'], self.expected_boot(banks=64))
            self.assertEqual((state['development']['memory_write_requests'], state['development']['memory_bytes_changed']), (0, 0))
            self.assertFalse(state['development']['memory_write_enabled'])
            self.assertEqual(hashlib.sha256(self.card.read_bytes()).hexdigest(), before_hash)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)


@unittest.skipUnless(HEADLESS.is_file(), 'Build headless for authored HuCard tests')
class HeadlessHuCardBootTests(HuCardHostChecks, unittest.TestCase):
    binary = HEADLESS


@unittest.skipUnless(DESKTOP.is_file(), 'Enable desktop for authored HuCard tests')
class DesktopHuCardBootTests(HuCardHostChecks, unittest.TestCase):
    binary = DESKTOP
    desktop = True
