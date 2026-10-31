"""Authored queued-VRAM guests through the two actual TCP hosts.

These guests execute through the hybrid sandbox. Independent native and exact
wait-clock verification belong to the separate Gear reference probe.
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


def authored_program(block):
    code = bytearray(bytes.fromhex('78 D8 D4 A9 FF 53 01 53 20 A9 F8 53 02'))
    def reg(index, value):
        code.extend((3,index,0x13,value&255,0x23,value>>8))
    def store(destination):
        code.extend((0x8D,destination&255,destination>>8))
    def sample_status(destination):
        code.extend((0xAD,0,0xA0,0x29,0x40));store(destination)
    reg(0,0)
    reg(2,0xA565);reg(2,0x8C19);reg(2,0xF5B2)
    reg(1,0) # Complete the pending write before configuring the copy.
    # 128 words occupy 512 VDC dots (~2048 master ticks at divider 4). This exceeds
    # the short register/status sequence in either access profile. CPU VRAM
    # slots are blocked for the copy, independently of background phase.
    reg(16,0);reg(17,0x0100);reg(18,127)
    reg(1,0);code.extend((3,2))
    sample_status(0x2000)
    if block:
        # TAI alternates VRR low/high ports; each high read requests the next
        # word. The next low read must await that read, including inside TAI.
        code.extend((0xF3,2,0xA0,1,0x20,6,0))
    else:
        for index in range(6):
            alias=2 if index//2==1 else 0xA002
            address=alias+(index&1)
            code.extend((0xAD,address&255,address>>8));store(0x2001+index)
    sample_status(0x2007)
    code.extend((0xA9,0x5A));store(0x2008)
    waiting = len(code)
    code.extend(bytes.fromhex('A9 01 8D 00 10 A9 00 8D 00 10 AD 00 10 29 08'))
    branch = len(code);code.extend((0xD0,(waiting-(branch+2))&255))
    code.extend((0xA9,0xA5));store(0x2009)
    code.extend((0x80,0xFE))
    return bytes(code)


def without_id(value):
    value=copy.deepcopy(value);value.pop('id');return value


class VdcQueueHostChecks:
    desktop=False

    def route(self, block, profile, explicit=True):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bios=root/'authored-queue-card.pce'
            raw=authored_card(authored_program(block));bios.write_bytes(raw)
            capture=root/'private-code.json'
            command=[str(self.binary),'--system-card-reset','standard',str(bios),
                     '10000000','10000000','hybrid','--audio-output','off',
                     '--video-output','continuous',
                     '--dev-port','0','--dev-start-paused','on','--wall-seconds','15',
                     '--code-capture',str(capture),'--capture-limit','512']
            if explicit:command+=['--vdc-access',profile]
            if self.desktop:command+=['--hidden','on','--unthrottled','on','--window-scale','1']
            environment=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_RENDER_DRIVER='software',SDL_AUDIODRIVER='dummy')
            process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,text=True,env=environment)
            try:
                startup=process.stderr.readline()
                self.assertTrue(startup.startswith('PCE_DEV_PORT='),startup)
                with DevClient(int(startup.split('=')[1]),timeout=8) as client:
                    initial=client.call('status')
                    self.assertEqual((initial['frame'],initial['ticks']),(0,0))
                    self.assertEqual(initial['host']['vdc_access'],dict(profile=profile,
                        pending_read=False,pending_write=False,delay=0,phase=0,wait_ticks=0))
                    before=client.advance(2)
                    expected=bytes((0x40 if profile=='queued' else 0,))+bytes.fromhex('65 A5 19 8C B2 F5 00 5A 00')
                    self.assertEqual(client.read_memory(0x1F0000,len(expected)),expected)
                    state=before['host']['vdc_access']
                    self.assertEqual(state['profile'],profile)
                    self.assertEqual((state['pending_read'],state['pending_write'],state['delay'],state['phase']),
                                     (False,False,0,0))
                    self.assertEqual(state['wait_ticks']%3,0)
                    if profile=='queued':self.assertGreater(state['wait_ticks'],0)
                    else:self.assertEqual(state['wait_ticks'],0)
                    # Full paused host/CPU state remains unchanged by status,
                    # pixels, RAM inspection and stored capture pagination.
                    settled=client.call('status');metadata,pixels=client.capture()
                    self.assertEqual(len(pixels),metadata['width']*metadata['height']*3)
                    history=client.capture_history()
                    self.assertEqual(history['runtime_abi'],ABI)
                    self.assertTrue(history['complete'])
                    self.assertEqual(without_id(client.call('status')),without_id(settled))
                    self.assertEqual(capture.stat().st_size,0)
                    client.call('set_input',port=0,mask=8)
                    after=client.advance(1)
                    self.assertEqual(client.read_memory(0x1F0009,1),b'\xA5')
                    self.assertEqual(after['host']['vdc_access'],state)
                    self.assertEqual(after['host']['debug_memory']['write_requests'],0)
                    self.assertEqual(after['host']['debug_memory']['bytes_changed'],0)
                    client.call('clear_input');client.call('quit')
                stdout,stderr=process.communicate(timeout=5)
                self.assertEqual(process.returncode,0,stderr)
                final=json.loads(stdout)
                self.assertEqual(final['stop'],'dev_quit')
                self.assertEqual(final['vdc_access'],state)
                observed=json.loads(capture.read_text(encoding='utf-8'))
                self.assertEqual(observed['runtime_abi'],ABI)
                self.assertEqual(observed['retired_instructions'],final['native_steps']+final['interpreter_steps'])
                self.assertTrue(observed['complete'])
                self.assertEqual(bios.read_bytes(),raw)
                return final
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill();process.communicate(timeout=5)

    def test_queued_data_reads_and_busy_wait_through_both_io_mpr_aliases(self):
        self.route(False,'queued')

    def test_queued_alternating_block_reads_finish_pending_transfers(self):
        self.route(True,'queued')

    def test_explicit_immediate_profile_keeps_reference_data_without_dynamic_waits(self):
        self.route(True,'immediate')

    def test_clocked_video_defaults_to_queued_accesses(self):
        self.route(False,'queued',explicit=False)


@unittest.skipUnless(HEADLESS.is_file(),'Build the headless runner first')
class HeadlessVdcQueueChecks(VdcQueueHostChecks,unittest.TestCase):
    binary=HEADLESS


@unittest.skipUnless(DESKTOP.is_file(),'Enable the SDL desktop runner')
class DesktopVdcQueueChecks(VdcQueueHostChecks,unittest.TestCase):
    binary=DESKTOP;desktop=True


if __name__=='__main__':unittest.main()
