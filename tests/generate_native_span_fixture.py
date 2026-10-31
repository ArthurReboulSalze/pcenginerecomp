"""Wholly authored source identities for native-span boundary tests."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture

MPR = [255, 248, 128, 129, 130, 131, 132, 0]
PROGRAMS = {
    0x4000: [0xA2, 7], 0x4002: [0xE8], 0x4003: [0xE0, 10],
    0x4005: [0xD0, 0xFB], 0x4007: [0x4C, 0, 0x41],
    0x4100: [0xA9, 42], 0x4102: [0x80, 0xFE],
    0x4200: [0xA9, 0x0B], 0x4202: [0x8D, 5, 0x42], 0x4205: [0xEA],
    0x4300: [0xA9, 43], 0x4302: [0x8D, 6, 0x43],
    0x4305: [0xA2, 7], 0x4307: [0xEA],
    0x4400: [0xA9, 129], 0x4402: [0x53, 4],
    0x4404: [0xA9, 42], 0x4406: [0x43, 4], 0x4408: [0xEA],
    0x4500: [0x58], 0x4501: [0xEA], 0x4502: [0xEA], 0x4600: [0x40],
    0x4700: [0x73, 0, 0x48, 9, 0x47, 2, 0],
    0x4707: [0xA9, 1], 0x4709: [0xA2, 7],
    0x4900: [0xAD, 0, 0x80],
    0x4950: [0x58], 0x4951: [0xEA],
    0x4A00: [0x54], 0x4A01: [0xEA], 0x4A02: [0xD4], 0x4A03: [0xEA],
    0x5000: [0xA5, 0x10], 0x5002: [0x18], 0x5003: [0x69, 3],
    0x5005: [0x85, 0x10], 0x5007: [0xE8], 0x5008: [0xD0, 0xF6],
    0x500A: [0xE6, 0x11], 0x500C: [0x4C, 0, 0x50],
}


def fixture_capture():
    # These are authored fixtures, not claimed execution observations. Runtime
    # traces and actual CodeCapture files are produced separately by the test.
    rows = []
    for pc, data in PROGRAMS.items():
        mapping = MPR.copy()
        if 0x4404 <= pc <= 0x4408:
            mapping[2] = 129
        rows.append(dict(pc=pc, mpr=mapping,
            physical=[(mapping[((pc+i)&65535)>>13]<<13)|((pc+i)&8191) for i in range(len(data))],
            data=data, native_hits=0, interpreted_hits=1))
    return dict(schema=1, runtime_abi=ABI, capacity=1024, complete=True,
                retired_instructions=len(rows), dropped_instructions=0,
                unreadable_instructions=0, observations=rows)


def generate(output):
    return emit_capture(fixture_capture(), output, partition_layout='stable', native_span=True)


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
