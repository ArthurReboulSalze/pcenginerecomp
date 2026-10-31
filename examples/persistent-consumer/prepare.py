"""Author a native BRAM counter consumer, without any retail firmware/media.

The observations below are authored translation inputs, not emulator captures.
Each process increments one BRAM byte exactly once and leaves its value in X.
It does not fabricate a System Card filesystem or format signature.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]


def prepare(output: Path, tool_root: Path = ROOT) -> Path:
    output, tool_root = output.resolve(), tool_root.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory")
    sys.path.insert(0, str(tool_root))
    from pcerecomp.emitter import emit_capture
    from pcerecomp.isa import physical
    from pcerecomp.project import ABI, source_identity, sha256
    identity = source_identity(tool_root)
    if identity["revision"] is None:
        raise ValueError("Example requires a committed toolkit checkout")
    output.mkdir(parents=True)
    operations = [(0xA9, 0xFF), (0x53, 1), (0xA9, 0xF8), (0x53, 2),
                  (0xA9, 0xF7), (0x53, 8), (0xA9, 0x80), (0x8D, 7, 0x18),
                  (0xEE, 0, 0x60), (0xAD, 0, 0x60), (0xAA,),
                  (0xAD, 3, 0x18), (0x80, 0xFE)]
    raw = bytearray(262144)
    raw[0x1FFE:0x2000] = bytes((0, 0xE1))
    mpr, pc, observations = [0] * 8, 0xE100, []
    for data in operations:
        locations = [physical(pc + i, mpr) for i in range(len(data))]
        for address, value in zip(locations, data):
            raw[address] = value
        observations.append(dict(pc=pc, mpr=list(mpr), physical=locations,
                                 data=list(data), native_hits=0, interpreted_hits=1))
        if data[0] == 0x53:
            page = {1: 0, 2: 1, 8: 3}[data[1]]
            mpr[page] = {0: 255, 1: 248, 3: 247}[page]
        pc += len(data)
    card = output / "authored-card.pce"
    card.write_bytes(raw)
    authored = dict(schema=1, runtime_abi=ABI, capacity=32, complete=True,
                    dropped_instructions=0, unreadable_instructions=0,
                    retired_instructions=len(observations), observations=observations)
    emit_capture(authored, output / "module", single_unit=True)
    descriptor = output / "project.toml"
    descriptor.write_text(f'''schema = 1
name = "authored-persistent-counter"
[tool]
path = {json.dumps(tool_root.as_posix())}
revision = "{identity['revision']}"
source_sha256 = "{identity['source_sha256']}"
runtime_abi = {ABI}
[module.source]
path = "module/module.cpp"
sha256 = "{sha256(output / 'module/module.cpp')}"
[module.manifest]
path = "module/module.json"
sha256 = "{sha256(output / 'module/module.json')}"
[boot]
mode = "system-card-reset"
profile = "standard"
[bios]
path = "authored-card.pce"
sha256 = "{sha256(card)}"
[runtime]
tier = "native"
video = "continuous"
cd_unknown_status = "fault"
joypad = 2
region = "usa"
multitap = "off"
[limits]
steps = 200
ticks = 100000
wall_seconds = 5
''', encoding="utf-8")
    # The explicit contract describes this authored counter's save interpretation.
    import hashlib
    (output / "save-contract.txt").write_text(
        hashlib.sha256(b"authored-bram-counter-v1: unsigned-byte-at-offset-zero").hexdigest() + "\n")
    return descriptor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tool-root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(prepare(args.output, args.tool_root))
