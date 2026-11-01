"""Original firmware for static discovery across proven executing/data TAMs.

Expected states below are independent literal instruction effects/cycle counts;
they are not obtained by decoding or running the runtime under test.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PATCHES = (
    (0, bytes.fromhex('78 A9 F8 53 02 A2 03 A9 01 53 84')),
    (0x2000, b'\x3c'), (0x4000, b'\xc7'),
    (0x200B, bytes.fromhex('AD 00 40 8D 10 20 A9 02 53 04 AD 00 40 8D 11 20 CA D0 FD A9 00 53 80')),
    (0x22, bytes.fromhex('4C 30 E0')),
    (0x30, bytes.fromhex('A9 01 53 80')),
    (0x2030, bytes.fromhex('A9 02 53 84 4C 30 E0')),
    (0x4034, bytes.fromhex('4C 50 E0')),
    (0x4050, bytes.fromhex('A9 00 53 80')),
    (0x54, bytes.fromhex('80 FE')),
    (0x1FFE, bytes.fromhex('00 E0')),
)
STEPS = 40


def fixture_patches(spread=False):
    """Opt-in separated logical pages; the original fixture is unchanged."""
    if type(spread) is not bool:
        raise ValueError('Spread fixture selection must be boolean')
    if not spread:
        return PATCHES
    return PATCHES[:3] + (
        PATCHES[3],
        (0x22, bytes.fromhex('4C 00 E3')),
        (0x300, PATCHES[5][1]),
        (0x2300, bytes.fromhex('A9 02 53 84 4C 00 E3')),
        (0x4304, bytes.fromhex('4C 00 E5')),
        (0x4500, PATCHES[8][1]),
        (0x504, PATCHES[9][1]),
        PATCHES[10],
    )


def firmware(*, spread=False):
    rom = bytearray([0xEA]*262144)
    for offset, data in fixture_patches(spread):
        rom[offset:offset+len(data)] = data
    return bytes(rom)


def expected_rows(divisor, *, spread=False):
    # PC,A,X,Y,S,P,divisor,ticks,MPR[8],TMA-latch,RAM10,RAM11,physicalPC.
    mpr = [0]*8
    a = x = ticks = latch = low = high = 0
    p = 4
    rows = []
    def add(pc, cycles, *, acc=None, index=None, flags=None, maps=None, transfer=None, ram=None):
        nonlocal a,x,p,ticks,latch,low,high
        if acc is not None: a = acc
        if index is not None: x = index
        if flags is not None: p = flags
        if maps:
            for page,bank in maps.items(): mpr[page] = bank
        if transfer is not None: latch = transfer
        if ram:
            low,high = ram
        ticks += cycles*divisor
        rows.append([pc,a,x,0,0,p,divisor,ticks,*mpr,latch,low,high,(mpr[pc>>13]<<13)|(pc&8191)])
    add(0xE001,2)
    add(0xE003,2,acc=0xF8,flags=0x84)
    add(0xE005,5,maps={1:0xF8},transfer=0xF8)
    add(0xE007,2,index=3,flags=4)
    add(0xE009,2,acc=1)
    add(0xE00B,5,maps={2:1,7:1},transfer=1)
    add(0xE00E,5,acc=0x3C)
    add(0xE011,5,ram=(0x3C,0))
    add(0xE013,2,acc=2)
    add(0xE015,5,maps={2:2},transfer=2)
    add(0xE018,5,acc=0xC7,flags=0x84)
    add(0xE01B,5,ram=(0x3C,0xC7))
    for index in (2,1,0):
        add(0xE01C,2,index=index,flags=4 if index else 6)
        add(0xE01B if index else 0xE01E,4 if index else 2)
    add(0xE020,2,acc=0,flags=6)
    add(0xE022,5,maps={7:0},transfer=0)
    add(0xE030,4)
    add(0xE032,2,acc=1,flags=4)
    add(0xE034,5,maps={7:1},transfer=1)
    add(0xE030,4)
    add(0xE032,2,acc=2)
    add(0xE034,5,maps={2:2,7:2},transfer=2)
    add(0xE050,4)
    add(0xE052,2,acc=0,flags=6)
    add(0xE054,5,maps={7:0},transfer=0)
    for _ in range(STEPS-len(rows)):
        add(0xE054,4)
    assert len(rows) == STEPS
    if spread:
        for row in rows:
            pc = row[0]
            if 0xE030 <= pc <= 0xE034:
                row[0] += 0x2D0
            elif 0xE050 <= pc <= 0xE054:
                row[0] += 0x4B0
            row[-1] = (row[8+(row[0]>>13)]<<13)|(row[0]&8191)
    return rows


def generate(out, *, emit_module=True, spread=False):
    from pcerecomp.analysis import Snapshot, analyze
    from pcerecomp.emitter import emit
    raw = firmware(spread=spread)
    out.mkdir(parents=True,exist_ok=True)
    (out/'authored.pce').write_bytes(raw)
    identity = hashlib.sha256(raw).hexdigest()
    text = ('schema = 1\nmpr = [0,0,0,0,0,0,0,0]\nentry_points = [57344]\n'
            '[[segments]]\nphysical = 0\nfile = "authored.pce"\nsha256 = "'+identity+'"\n')
    snapshot_path = out/'snapshot.toml'
    snapshot_path.write_text(text,encoding='utf-8',newline='\n')
    if emit_module:
        graph = analyze(Snapshot.load(snapshot_path),follow_mappings=True)
        if graph['schema'] != 2 or graph['unresolved']:
            raise ValueError('Authored multi-context graph must close without unresolved semantics')
        (out/'analysis.json').write_text(json.dumps(graph,indent=2)+'\n',encoding='utf-8',newline='\n')
        # The public emitter requires fresh destinations. CMake can regenerate
        # this owned fixture after an emitter dependency changes.
        with tempfile.TemporaryDirectory(prefix='context-module-', dir=out) as stage:
            staged = Path(stage)
            emit(graph, staged)
            for name in ('module.cpp', 'module.json'):
                (out/name).write_bytes((staged/name).read_bytes())
    header = ['#pragma once','#include <array>','#include <algorithm>','#include <cstdint>','#include <vector>',
              'inline std::vector<std::uint8_t> context_rom() { std::vector<std::uint8_t> v(262144,0xEA);']
    for offset,data in fixture_patches(spread):
        header += ['{ const std::uint8_t bytes[]{'+','.join(map(str,data))+'}; std::copy(std::begin(bytes),std::end(bytes),v.begin()+'+str(offset)+'); }']
    header += ['return v; }',f'inline constexpr unsigned context_steps={STEPS};']
    for divisor in (3,12):
        rows = expected_rows(divisor, spread=spread)
        header += [f'inline constexpr std::array<std::array<std::uint64_t,20>,{STEPS}> context_expected_{divisor}'+'{{']
        header += ['{{'+','.join(map(str,row))+'}},' for row in rows]
        header += ['}};']
    (out/'context_fixture.hpp').write_text('\n'.join(header)+'\n',encoding='utf-8',newline='\n')


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
