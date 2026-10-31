"""Prepare an authored reset-vector consumer with a pinned toolkit checkout.

No firmware or media is downloaded. The generated 256 KiB card is entirely
authored here and belongs in the explicitly selected new output directory.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]


def prepare(output: Path, tool_root: Path = ROOT, profile: str = 'standard') -> Path:
    output = output.resolve()
    tool_root = tool_root.resolve()
    if output.exists():
        raise ValueError('Choose a new output directory')
    if profile not in ('standard', 'super'):
        raise ValueError('Choose standard or super System Card hardware')
    # Use the selected checkout for both generation and the exact build pin.
    sys.path.insert(0, str(tool_root))
    from pcerecomp.analysis import Snapshot, analyze
    from pcerecomp.emitter import emit
    from pcerecomp.project import ABI, sha256, source_identity
    identity = source_identity(tool_root)
    if identity['revision'] is None:
        raise ValueError('Example preparation requires a Git checkout with a commit')
    output.mkdir(parents=True)

    # LDA #41; INA (increment A); BRA back to INA. Every initial MPR is zero,
    # so logical $E000 maps to physical $0000. The actual little-endian reset
    # vector lives at physical $1FFE, not at the final two bytes of this file.
    raw = bytearray(262144)
    raw[:5] = bytes([0xA9, 41, 0x1A, 0x80, 0xFD])
    raw[0x1FFE:0x2000] = bytes([0, 0xE0])
    card = output/'authored-card.pce'
    card.write_bytes(raw)
    snapshot = output/'snapshot.toml'
    snapshot.write_text('schema = 1\nmpr = [0,0,0,0,0,0,0,0]\n'
                        'entry_points = [57344]\n[[segments]]\nphysical = 0\n'
                        'file = "authored-card.pce"\n'
                        f'sha256 = "{sha256(card)}"\n', encoding='utf-8')
    emit(analyze(Snapshot.load(snapshot)), output/'module')
    descriptor = output/'project.toml'
    descriptor.write_text(f'''schema = 1
name = "authored-reset-consumer"
[tool]
path = {json.dumps(tool_root.as_posix())}
revision = "{identity['revision']}"
source_sha256 = "{identity['source_sha256']}"
runtime_abi = {ABI}
[module.source]
path = "module/module.cpp"
sha256 = "{sha256(output/'module/module.cpp')}"
[module.manifest]
path = "module/module.json"
sha256 = "{sha256(output/'module/module.json')}"
[boot]
mode = "system-card-reset"
profile = "{profile}"
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
''', encoding='utf-8')
    return descriptor


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--tool-root', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=('standard', 'super'), default='standard')
    args = parser.parse_args()
    print(prepare(args.output, args.tool_root, args.profile))
