"""Authored guest port/DMA programs through both real TCP hosts.

Only controller input advances the second phase. Screenshots, source inspection
and debugger RAM reads are observational; no guest state is injected.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from pcerecomp.abi import ABI
from scripts.dev_client import DevClient
from test_reset_boot import authored_card

ROOT = Path(__file__).resolve().parent.parent
EXE = '.exe' if os.name == 'nt' else ''
HEADLESS = Path(os.environ.get('PCE_TEST_HEADLESS', ROOT/'build'/('pce-headless'+EXE)))
DESKTOP = Path(os.environ.get('PCE_TEST_DESKTOP', 'disabled'))


def authored_program(dma=False):
    # IRQ disabled; high speed; IO in logical pages0/5, WRAM in page1.
    code = bytearray(bytes.fromhex('78 D8 D4 A9 FF 53 01 53 20 A9 F8 53 02'))

    def reg(index, value):
        code.extend((3, index, 0x13, value & 255, 0x23, value >> 8))

    def word(address, value):
        reg(0, address)
        reg(2, value)

    def read_word(address, destination, alias=0xA002):
        reg(1, address)
        code.extend((3, 2))
        sample(destination, alias)

    def sample(destination, alias=0xA002):
        for port, target in ((alias, destination), (alias+1, destination+1)):
            code.extend((0xAD, port & 255, port >> 8, 0x8D, target & 255, target >> 8))

    if dma:
        word(0x7FFF, 0xF3FF)
        word(0x7FFE, 0x9B7D)
        reg(1, 0x7FFF)  # Seed the bus from a real read, not a write.
        reg(16, 0x8000)
        reg(17, 0x10)
        reg(18, 0)  # One undriven-source DMA word -> heldF3FF.
        read_word(0x10, 0x2000)
        reg(1, 0x7FFF)
        reg(16, 0x7FFE)
        reg(17, 0x8000)
        reg(18, 0)  # Undriven destination skips the source read.
        read_word(0x8000, 0x2002)
        read_word(0x7FFE, 0x2004)
        reg(1, 0x10)  # Restore heldF3FF.
        expected = bytes.fromhex('FF F3 FF F3 7D 9B') + bytes(4)
        held = bytes.fromhex('FF F3')
    else:
        word(0x7FFF, 0xABCD)
        reg(2, 0x5566)  # MAWR advanced8000: ignored, no latch update.
        reg(1, 0x7FFF)
        code.extend((3, 2))
        sample(0x2000)
        sample(0x2002, 2)  # Same ports through the other IO MPR alias.
        read_word(0xFFFF, 0x2004)  # Undriven prefetch wraps MARR to0.
        sample(0x2006)  # Previous high read fetched the zero word at0.
        read_word(0x7FFF, 0x2008)  # Ignored high write did not mirror.
        expected = bytes.fromhex('CD AB CD AB CD AB 00 00 CD AB')
        held = bytes.fromhex('CD AB')
    # Leave a known undriven read pending while TCP performs pure inspection.
    reg(1, 0x8000)
    code.extend((3, 2, 0xA9, 0x5A, 0x8D, 0x0A, 0x20))
    waiting = len(code)
    # The guest relatches its ordinary two-button action nibble. Run is bit3.
    code.extend(bytes.fromhex('A9 01 8D 00 10 A9 00 8D 00 10 AD 00 10 29 08'))
    branch = len(code)
    code.extend((0xD0, (waiting-(branch+2)) & 255))
    if dma:
        # The initial frame's source-backed non-burst phase is finished now.
        # Seed and arm through guest ports after Run, isolating SATB's held
        # source from those separate initial background fetches.
        reg(1, 0x10)
        reg(19, 0x8000)  # Y=1023 remains offscreen after the copy.
        reg(1, 0x8000)
        code.extend((3, 2))
    sample(0x2010)
    code.extend(bytes.fromhex('A9 A5 8D 12 20 80 FE'))
    return bytes(code), expected+bytes((0x5A,))+bytes(5), held+bytes((0xA5,))


def no_id(value):
    result = copy.deepcopy(value)
    del result['id']
    return result


class VramLatchHostChecks:
    desktop = False

    def route(self, dma):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            program, prefix, completed = authored_program(dma)
            bios = directory/'authored-vram-card.pce'
            original = authored_card(program)
            bios.write_bytes(original)
            capture = directory/'private-code.json'
            command = [str(self.binary), '--system-card-reset', 'standard', str(bios),
                       '10000000', '10000000', 'hybrid', '--audio-output', 'off',
                       '--video-output', 'continuous', '--dev-port', '0', '--dev-start-paused', 'on',
                       '--code-capture', str(capture), '--capture-limit', '512', '--wall-seconds', '15']
            if self.desktop:
                command += ['--hidden', 'on', '--unthrottled', 'on', '--window-scale', '1']
            environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software',
                               SDL_AUDIODRIVER='dummy')
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=environment)
            try:
                startup = process.stderr.readline()
                self.assertTrue(startup.startswith('PCE_DEV_PORT='), startup)
                with DevClient(int(startup.split('=')[1]), timeout=8) as client:
                    initial = client.call('status')
                    self.assertEqual((initial['frame'], initial['ticks']), (0, 0))
                    waiting = client.advance(2)
                    self.assertEqual(client.read_memory(0x1F0000, len(prefix)), prefix)
                    self.assertEqual(client.read_memory(0x1F0010, 3), bytes(3))
                    self.assertEqual(waiting['host']['debug_memory']['write_requests'], 0)
                    self.assertEqual(waiting['host']['debug_memory']['bytes_changed'], 0)
                    before = client.call('status')
                    metadata, pixels = client.capture()
                    self.assertEqual(len(pixels), metadata['width']*metadata['height']*3)
                    history = client.capture_history()
                    self.assertEqual(history['runtime_abi'], ABI)
                    self.assertTrue(history['complete'])
                    self.assertEqual(history['unreadable_instructions'], 0)
                    after = client.call('status')
                    self.assertEqual(no_id(before), no_id(after))
                    self.assertEqual(capture.stat().st_size, 0)
                    client.call('set_input', port=0, mask=8)
                    finished = client.advance(2)
                    self.assertEqual(client.read_memory(0x1F0010, 3), completed)
                    if dma:
                        self.assertEqual(finished['host']['vdc']['satb'], [0xF3FF]*256)
                        self.assertEqual(finished['host']['vdc']['satb_pending'], 0)
                    client.call('clear_input')
                    client.call('quit')
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr)
                result = json.loads(stdout)
                self.assertEqual(result['stop'], 'dev_quit')
                self.assertEqual(result['development']['memory_write_requests'], 0)
                self.assertEqual(result['development']['memory_bytes_changed'], 0)
                observed = json.loads(capture.read_text())
                self.assertEqual(observed['runtime_abi'], ABI)
                self.assertEqual(observed['retired_instructions'],
                                 result['native_steps']+result['interpreter_steps'])
                self.assertTrue(observed['complete'])
                self.assertEqual(bios.read_bytes(), original)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=5)

    def test_cpu_undriven_prefetch_wrap_aliases_ignored_write_and_pure_inspection(self):
        self.route(False)

    def test_dma_undriven_source_destination_and_satb_follow_held_bus(self):
        self.route(True)


@unittest.skipUnless(HEADLESS.is_file(), 'Build the headless runner first')
class HeadlessVramLatchChecks(VramLatchHostChecks, unittest.TestCase):
    binary = HEADLESS


@unittest.skipUnless(DESKTOP.is_file(), 'Enable the SDL desktop runner')
class DesktopVramLatchChecks(VramLatchHostChecks, unittest.TestCase):
    binary = DESKTOP
    desktop = True


if __name__ == '__main__':
    unittest.main()
