"""Capture and promote an authored reset program across MPR/ROM mirrors.

This bounded example handles only its own authored fixture, not arbitrary
firmware. General capture generation remains `pcerecomp emit-capture`.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
STEPS = 200
PROGRAM = bytes([0xA9, 0xFF, 0x53, 1, 0xA9, 0xF8, 0x53, 2,
                 0xA9, 0x20, 0x53, 0x80, 0xD4, 0xA9, 0x37,
                 0x8D, 0, 0x20, 0xEE, 0, 0x20, 0xAD, 0, 0x20,
                 0xAA, 0xA9, 0x40, 0x53, 0x80, 0xE8, 0x80, 0xFD])


def card_bytes():
    card = bytearray(262144)
    card[:len(PROGRAM)] = PROGRAM
    card[0x1FFE:0x2000] = bytes([0, 0xE0])
    return bytes(card)


def tools(tool_root):
    sys.path.insert(0, str(tool_root))
    from pcerecomp.capture import load_capture
    from pcerecomp.emitter import emit_capture
    from pcerecomp.project import ABI, sha256, source_identity
    identity = source_identity(tool_root)
    if identity['revision'] is None:
        raise ValueError('Choose a committed toolkit checkout')
    return load_capture, emit_capture, sha256, identity


def expected_observations():
    # Authored instruction boundaries and post-TAM mapping changes, not a
    # generic interpreter. All ROM aliases retain their mapped physical PCs.
    lengths = (2, 2, 2, 2, 2, 2, 1, 2, 3, 3, 3, 1, 2, 2, 1, 2)
    mpr = [0]*8
    result, offset = [], 0
    for index, length in enumerate(lengths):
        result.append(dict(pc=0xE000+offset, mpr=list(mpr),
                           physical=[(mpr[7] << 13)+offset+i for i in range(length)],
                           data=list(PROGRAM[offset:offset+length]),
                           native_hits=0, interpreted_hits=1 if index < 14 else 93))
        if index == 1: mpr[0] = 255
        if index == 3: mpr[1] = 248
        if index == 5: mpr[7] = 0x20
        if index == 13: mpr[7] = 0x40
        offset += length
    return sorted(result, key=lambda item: (item['mpr'], item['pc'], item['data']))


def check_state(state, profile, native):
    expected = dict(pc=0xE01D, a=64, x=149, y=0, sp=0, p=132,
                    mpr=[255, 248, 0, 0, 0, 0, 0, 64], cycles=610, ticks=2037,
                    native_steps=200 if native else 0, interpreter_steps=0 if native else 200)
    def exact(actual, expected):
        if type(actual) is not type(expected):
            return False
        if isinstance(expected, dict):
            return set(actual) == set(expected) and all(exact(actual[k], v) for k, v in expected.items())
        if isinstance(expected, list):
            return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
        return actual == expected
    if type(state) is not dict or any(not exact(state.get(key), value) for key, value in expected.items()):
        raise ValueError('Authored reset CPU, clocks or executed tiers differ')
    boot = dict(mode='system-card-reset', profile=profile,
                initialization='gear-deterministic-zero-v1', vector_physical=8190,
                pc=0xE000, a=0, x=0, y=0, sp=0, p=4,
                clock_divisor=12, ticks=0, cycles=0, mpr=[0]*8, bram='blank-unformatted')
    if not exact(state.get('boot'), boot):
        raise ValueError('Authored reset initial metadata differs')


def capture(output, runner, tool_root=ROOT, profile='standard', capacity=64):
    output, runner, tool_root = output.resolve(), runner.resolve(), tool_root.resolve()
    if output.exists():
        raise ValueError('Choose a new output directory')
    if profile not in ('standard', 'super'):
        raise ValueError('Choose standard or super hardware')
    if not runner.is_file():
        raise ValueError('Select an existing headless runner')
    if type(capacity) is not int or not 1 <= capacity <= 65536:
        raise ValueError('Capture capacity must be in 1..65536')
    load_capture, _, sha256, identity = tools(tool_root)
    output.mkdir(parents=True)
    card, trace = output/'authored-card.pce', output/'actual-capture.json'
    card.write_bytes(card_bytes())
    argv = [str(runner), '--system-card-reset', profile, str(card), str(STEPS),
            '100000', 'hybrid', '--video-output', 'continuous', '--audio-output', 'off', '--code-capture',
            str(trace), '--capture-limit', str(capacity), '--wall-seconds', '5']
    binary_hash, input_hash = sha256(runner), sha256(card)
    done = subprocess.run(argv, cwd=output, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=15)
    stdout, stderr = output/'run.stdout', output/'run.stderr'
    stdout.write_text(done.stdout, encoding='utf-8')
    stderr.write_text(done.stderr, encoding='utf-8')
    if done.returncode != 0:
        raise ValueError('Capture runner failed; original stdout/stderr retained')
    state = json.loads(done.stdout)
    check_state(state, profile, native=False)
    raw, trace_hash = load_capture(trace)
    if sha256(runner) != binary_hash or sha256(card) != input_hash:
        raise ValueError('Capture binary or authored input changed during execution')
    from pcerecomp.project import source_identity
    if source_identity(tool_root) != identity:
        raise ValueError('Toolkit source changed during capture')
    report = dict(schema=1, profile=profile, tool=identity, argv=argv, cwd=str(output),
                  runner_sha256=binary_hash, card_sha256=input_hash, capture_sha256=trace_hash,
                  stdout_sha256=sha256(stdout), stderr_sha256=sha256(stderr), capacity=capacity,
                  exit_code=done.returncode, state=state, complete=raw['complete'])
    (output/'capture-run.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return output/'capture-run.json'


def promote(output, tool_root=ROOT):
    output, tool_root = output.resolve(), tool_root.resolve()
    load_capture, emit_capture, sha256, identity = tools(tool_root)
    from pcerecomp.project import ABI
    if any(path.exists() or path.is_symlink() for path in (output/'module', output/'project.toml')):
        raise ValueError('Module/descriptor already exists; preserve the previous result')
    trace, card = output/'actual-capture.json', output/'authored-card.pce'
    raw, trace_hash = load_capture(trace)
    # Validate completely before emitting any module or descriptor. An incomplete
    # capture is useful diagnostics but cannot establish this bounded proof.
    if not raw['complete'] or raw['dropped_instructions'] or raw['unreadable_instructions']:
        raise ValueError('Refusing incomplete capture: dropped or unreadable instructions')
    if raw['runtime_abi'] != ABI or raw['retired_instructions'] != STEPS:
        raise ValueError('Capture ABI/retirement total differs from the authored run')
    if raw['observations'] != expected_observations():
        raise ValueError('Capture PC/MPR/physical source/bytes/hit identities differ')
    report = json.loads((output/'capture-run.json').read_text(encoding='utf-8'))
    fields = {'schema', 'profile', 'tool', 'argv', 'cwd', 'runner_sha256', 'card_sha256',
              'capture_sha256', 'stdout_sha256', 'stderr_sha256', 'capacity',
              'exit_code', 'state', 'complete'}
    if type(report) is not dict or set(report) != fields:
        raise ValueError('Invalid capture-run report fields')
    if type(report['schema']) is not int or report['schema'] != 1:
        raise ValueError('Invalid capture-run schema')
    if type(report['exit_code']) is not int or report['exit_code'] != 0:
        raise ValueError('Capture-run exit_code must be integer zero')
    if type(report['complete']) is not bool or report['complete'] != raw['complete']:
        raise ValueError('Capture-run completeness differs from actual capture')
    if type(report['capacity']) is not int or report['capacity'] != raw['capacity']:
        raise ValueError('Capture-run capacity differs from actual capture')
    if any(type(report[key]) is not str or re.fullmatch('[0-9a-f]{64}', report[key]) is None
           for key in ('runner_sha256', 'card_sha256', 'capture_sha256', 'stdout_sha256', 'stderr_sha256')):
        raise ValueError('Invalid capture-run SHA256 binding')
    if report['tool'] != identity or report['capture_sha256'] != trace_hash:
        raise ValueError('Capture provenance or toolkit pin changed')
    if card.read_bytes() != card_bytes() or report['card_sha256'] != sha256(card):
        raise ValueError('Authored card changed')
    profile = report['profile']
    if profile not in ('standard', 'super'):
        raise ValueError('Invalid recorded hardware profile')
    argv = report['argv']
    if type(argv) is not list or not argv or type(argv[0]) is not str or not Path(argv[0]).is_absolute():
        raise ValueError('Invalid capture-run argv')
    expected_argv = [argv[0], '--system-card-reset', profile, str(card), str(STEPS), '100000',
                     'hybrid', '--video-output', 'continuous', '--audio-output', 'off',
                     '--code-capture', str(trace), '--capture-limit', str(raw['capacity']),
                     '--wall-seconds', '5']
    if argv != expected_argv or type(report['cwd']) is not str or report['cwd'] != str(output):
        raise ValueError('Capture-run argv/profile/capacity or cwd differs from authored execution')
    stdout, stderr = output/'run.stdout', output/'run.stderr'
    if report['stdout_sha256'] != sha256(stdout) or report['stderr_sha256'] != sha256(stderr):
        raise ValueError('Actual runner stdout/stderr binding changed')
    if json.loads(stdout.read_text(encoding='utf-8')) != report['state']:
        raise ValueError('Recorded capture state differs from actual runner output')
    check_state(report['state'], profile, native=False)
    emit_capture(raw, output/'module', trace_hash)
    descriptor = output/'project.toml'
    text = f'''schema = 1
name = "authored-reset-capture"
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
audio = "off"
cd_unknown_status = "fault"
joypad = 2
region = "usa"
multitap = "off"
[limits]
steps = 200
ticks = 100000
wall_seconds = 5
'''
    with descriptor.open('x', encoding='utf-8') as stream:
        stream.write(text)
    return descriptor


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    training = sub.add_parser('capture')
    training.add_argument('output', type=Path)
    training.add_argument('--runner', required=True, type=Path)
    training.add_argument('--profile', choices=('standard', 'super'), default='standard')
    training.add_argument('--tool-root', type=Path, default=ROOT)
    training.add_argument('--capacity', type=int, default=64)
    promotion = sub.add_parser('promote')
    promotion.add_argument('output', type=Path)
    promotion.add_argument('--tool-root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == 'capture':
            print(capture(args.output, args.runner, args.tool_root, args.profile, args.capacity))
        else:
            print(promote(args.output, args.tool_root))
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
        parser.exit(2, f'authored reset example: {error}\n')
