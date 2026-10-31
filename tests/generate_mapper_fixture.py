"""Authored mapper operations; emitted directly, never interpreter bridges."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture
from pcerecomp.isa import physical

MPR = (0, 0xF8, 0x40, 0x41, 0x42, 0x43, 0x7F, 0)


def generate(out):
    observations = []

    def add(pc, data):
        observations.append(dict(pc=pc, mpr=list(MPR), data=list(data),
            physical=[physical(pc+i, MPR) for i in range(len(data))],
            native_hits=0, interpreted_hits=1))

    for latch in range(16):
        add(0xE100, (0x8D, 0xF0+latch, 0x1F))
    for value in (0x20, 0x21, 0x22, 0x23, 0x71):
        add(0x4000, (0xA9, value))
    add(0x4100, (0x8D, 0xF2, 0x1F))
    for value in (0x40, 0x41, 0x42, 0x43):
        add(0x4103, (0xA9, value))
    add(0xE200, (0x73, 0, 0x20, 0xF0, 0x1F, 16, 0))
    add(0xE200, (0x73, 0, 0x20, 0, 0x40, 16, 0))
    capture = dict(schema=1, runtime_abi=ABI, capacity=64, dropped_instructions=0,
        unreadable_instructions=0, retired_instructions=len(observations),
        complete=True, observations=observations)
    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='mapper-authored-', dir=out.parent) as scratch:
        generated = Path(scratch)/'module'
        emit_capture(capture, generated, single_unit=True)
        for source in generated.iterdir():
            (out/source.name).write_bytes(source.read_bytes())
    (out/'mapper_fixture.hpp').write_text('#pragma once\n#include <array>\n#include <cstdint>\n'
        'inline constexpr std::array<std::uint8_t,8> mapper_mpr{'+
        ','.join(map(str, MPR))+'};\n', encoding='utf-8')


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
