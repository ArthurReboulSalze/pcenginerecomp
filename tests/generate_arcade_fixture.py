"""Authored translated Arcade Card data operations and refusing source guards."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture
from pcerecomp.isa import physical

MPR = (255, 0xF8, 0x40, 0x41, 0x42, 0x43, 0x68, 0)
OPERATIONS = (
    (0xE100, (0xAD, 0, 0x40)),
    (0xE110, (0x8D, 0, 0x60)),
    (0xE120, (0xAD, 0x20, 0x1A)),
    (0xE130, (0x8D, 0x30, 0x1A)),
    (0xE140, (0xAD, 0xFE, 0x1A)),
    (0xE150, (0x8D, 0xE4, 0x1A)),
    (0xE160, (0xAD, 0xE0, 0x1A)),
    (0xE170, (0xEE, 0, 0x40)),
    (0xE200, (0x73, 0, 0x20, 0, 0x40, 16, 0)),
    (0xE210, (0x73, 0, 0x60, 0, 0x22, 16, 0)),
    (0x4000, (0xA9, 0x5A)),
    (0x3FFF, (0xA9, 0x7B)),
)


def generate(out):
    observations = [dict(pc=pc, mpr=list(MPR), data=list(data),
                         physical=[physical((pc+i)&65535, MPR) for i in range(len(data))],
                         native_hits=0, interpreted_hits=1) for pc, data in OPERATIONS]
    capture = dict(schema=1, runtime_abi=ABI, capacity=64, dropped_instructions=0,
                   unreadable_instructions=0, retired_instructions=len(observations),
                   complete=True, observations=observations)
    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='arcade-authored-', dir=out.parent) as scratch:
        generated = Path(scratch)/'module'
        emit_capture(capture, generated, single_unit=True)
        for source in generated.iterdir():
            (out/source.name).write_bytes(source.read_bytes())
    lines = ['#pragma once', '#include <array>', '#include <cstdint>',
             'inline constexpr std::array<std::uint8_t,8> arcade_mpr{'+','.join(map(str,MPR))+'};']
    for index, (pc, data) in enumerate(OPERATIONS):
        lines += [f'inline constexpr std::uint16_t arcade_pc_{index}={pc};',
                  f'inline constexpr std::array<std::uint8_t,{len(data)}> arcade_op_{index}'+
                  '{'+','.join(map(str,data))+'};']
    (out/'arcade_fixture.hpp').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
