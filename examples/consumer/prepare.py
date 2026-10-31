"""Create an authored six-byte consumer program and pinned descriptor.

Run from the tool checkout with `python examples/consumer/prepare.py NEW_DIR`.
Nothing is downloaded. Generated assets stay in the explicitly chosen directory.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pcerecomp.analysis import Snapshot, analyze
from pcerecomp.emitter import emit
from pcerecomp.project import ABI, sha256, source_identity


def prepare(output: Path, tool_root: Path = ROOT) -> Path:
    output = output.resolve()
    tool_root = tool_root.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory")
    identity = source_identity(tool_root)
    if identity["revision"] is None:
        raise ValueError("Example preparation requires a Git checkout with a commit")
    output.mkdir(parents=True)
    # Authored LDA #41; TAX; INX; BRA back to INX. No retail-derived data.
    payload = output / "program.bin"
    payload.write_bytes(bytes([0xA9, 41, 0xAA, 0xE8, 0x80, 0xFD]))
    snapshot = output / "snapshot.toml"
    snapshot.write_text('schema = 1\nmpr = [255,248,128,129,130,131,132,0]\nentry_points = [16384]\n'
                        '[[segments]]\nphysical = 1048576\nfile = "program.bin"\n'
                        f'sha256 = "{sha256(payload)}"\n', encoding="utf-8")
    emit(analyze(Snapshot.load(snapshot)), output / "module")
    descriptor = output / "project.toml"
    quote = json.dumps
    descriptor.write_text(f'''schema = 1
name = "authored-consumer"
[tool]
path = {quote(tool_root.as_posix())}
revision = "{identity['revision']}"
source_sha256 = "{identity['source_sha256']}"
runtime_abi = {ABI}
[module.source]
path = "module/module.cpp"
sha256 = "{sha256(output / 'module/module.cpp')}"
[module.manifest]
path = "module/module.json"
sha256 = "{sha256(output / 'module/module.json')}"
[payload]
path = "program.bin"
sha256 = "{sha256(payload)}"
physical_load = 1048576
pc = 16384
mpr = [255,248,128,129,130,131,132,0]
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
    return descriptor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tool-root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(prepare(args.output, args.tool_root))
