"""Test-only adapter for the SingleStepTests/huc6280 corpus (Mesen-generated, MIT).

Plays the pinned vectors through the interpreter and through actual emitted,
compiled native code. It changes no runtime, CPU or ABI file and uses no game data.

    fetch   OUT                  fetch the pinned commit with git into a new directory, verify it
    verify  CORPUS               check every file against tests/huc6280_vectors.sha256
    run     CORPUS --build BUILD --out REPORT [--compiler CXX]

Reported separately: architectural state (registers, flags, PC, all eight MPRs, sparse
physical memory) and the CPU cycle total. Not observed, hence never inferred: bus-event
order, dummy accesses and master ticks. Vectors cut by the generator cap (500 cycles or
500 RAM pairs) have no comparable final state. The corpus is expectations from Mesen,
not hardware; the Mesen revision that generated it is not recorded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPOSITORY = 'https://github.com/SingleStepTests/huc6280'
COMMIT = '4ce378e04e243437e6f74dfe76c3cb7c70e45bf1'
MANIFEST = ROOT / 'tests' / 'huc6280_vectors.sha256'
GENERATOR_CAP = 500
CANONICAL_FRAME = tuple(range(0x20, 0x28))   # eight distinct RAM pages for the native tier
NOT_OBSERVED = ('bus_event_order', 'dummy_accesses', 'master_ticks')
MAX_PROBE_OUTPUT = 64 * 1024 * 1024
HEADER = 'PCE-HUC6280-NATIVE-CASES 1'


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path=MANIFEST):
    entries = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        digest, size, name = line.split()
        if len(digest) != 64 or not name.startswith('v1/') or name in entries:
            raise ValueError(f'Malformed or duplicate manifest line: {line}')
        entries[name] = (digest, int(size))
    if len(entries) != 256:
        raise ValueError('The manifest must list exactly 256 files')
    return entries


def digest_of_digests(manifest):
    result = hashlib.sha256()
    for name in sorted(manifest):
        result.update(manifest[name][0].encode())
    return result.hexdigest()


def verify_corpus(corpus, manifest):
    """Fail closed before any vector is read: exact file set, sizes and SHA-256."""
    corpus = Path(corpus)
    actual = sorted(p.name for p in (corpus / 'v1').glob('*') if p.is_file()) if (corpus / 'v1').is_dir() else []
    expected = sorted(Path(name).name for name in manifest)
    if actual != expected:
        raise ValueError('Corpus file set differs from the manifest (missing or extra files)')
    total = 0
    for name, (digest, size) in manifest.items():
        path = corpus / name
        if path.is_symlink() or path.stat().st_size != size or sha256_file(path) != digest:
            raise ValueError(f'Corpus file does not match the manifest: {name}')
        total += size
    return total


def read_vectors(path):
    """Decode one .json.bin file (layout of transcode_json.py in the corpus)."""
    data = Path(path).read_bytes()
    if len(data) > 64 << 20:
        raise ValueError('Corpus file exceeds the 64 MiB bound')

    def state(p):
        p += 4
        a, x, y, s, flags = struct.unpack_from('5B', data, p); p += 5
        pc = struct.unpack_from('<H', data, p)[0]; p += 2
        mpr = list(struct.unpack_from('8B', data, p)); p += 8
        count = struct.unpack_from('<i', data, p)[0]; p += 4
        if not 0 <= count <= 4096:
            raise ValueError('RAM pair count out of range')
        ram = []
        for _ in range(count):
            address, value = struct.unpack_from('<IB', data, p); p += 5
            ram.append((address, value))
        return p, dict(a=a, x=x, y=y, s=s, p=flags, pc=pc, mpr=mpr, ram=ram)

    count = struct.unpack_from('<I', data, 0)[0]
    if count > 100000:
        raise ValueError('Vector count out of range')
    p, vectors = 4, []
    for _ in range(count):
        p += 4
        name = data[p:p + 50].rstrip(b'\0 ').decode(); p += 50
        opcode = struct.unpack_from('<I', data, p)[0]; p += 4
        p, init = state(p)
        p, final = state(p)
        total, stored = struct.unpack_from('<II', data, p); p += 8
        if stored > 4096:
            raise ValueError('Cycle record count out of range')
        p += 4 * stored
        vectors.append(dict(name=name, opcode=opcode, init=init, fin=final, cycles=total, stored=stored))
    return vectors


def truncated(vector):
    return (vector['stored'] >= GENERATOR_CAP or len(vector['init']['ram']) >= GENERATOR_CAP
            or len(vector['fin']['ram']) >= GENERATOR_CAP)


def select_native(vectors, per_opcode, native_opcodes):
    """First `per_opcode` vectors in file order that can be moved to the canonical frame.

    Rule: opcode is native, not TAM/TMA, final state complete (not cut by the cap), eight
    pairwise-distinct MPR values, MPRs unchanged by the instruction, every listed cell in
    a mapped page. Returns (selected, excluded-with-reasons counters).
    """
    selected, excluded = [], {}

    def skip(reason):
        excluded[reason] = excluded.get(reason, 0) + 1

    for vector in vectors:
        if len(selected) >= per_opcode:
            break
        if vector['opcode'] not in native_opcodes:
            skip('opcode not native'); continue
        if vector['opcode'] in (0x43, 0x53):
            skip('TAM/TMA change or read the MPR latch'); continue
        if truncated(vector):
            skip('cut by the generator cap'); continue
        if len(set(vector['init']['mpr'])) != 8:
            skip('MPR values not pairwise distinct'); continue
        if vector['fin']['mpr'] != vector['init']['mpr']:
            skip('MPRs changed'); continue
        selected.append(vector)
    return selected, excluded


def to_canonical(vector):
    """Move a vector to the canonical MPR frame, keeping which logical window each cell belongs to."""
    window = {page: w for w, page in enumerate(vector['init']['mpr'])}

    def convert(cells):
        converted = []
        for address, value in cells:
            w = window.get(address >> 13)
            if w is None:
                return None
            converted.append(((CANONICAL_FRAME[w] << 13) | (address & 0x1FFF), value))
        return converted

    init, final = convert(vector['init']['ram']), convert(vector['fin']['ram'])
    if init is None or final is None:
        return None
    return dict(vector, init=dict(vector['init'], ram=init), fin=dict(vector['fin'], ram=final))


def site_bytes(vector, isa):
    memory = dict(vector['init']['ram'])

    def physical(pc):
        return (CANONICAL_FRAME[(pc & 0xFFFF) >> 13] << 13) | (pc & 0x1FFF)

    instruction = isa.decode(lambda pc: memory.get(physical(pc), 0), vector['init']['pc'], CANONICAL_FRAME)
    site = {physical(vector['init']['pc'] + k): None for k in range(len(instruction.data))}
    if any(address not in memory for address in site):
        return None
    flow = {instruction.next_pc} | ({instruction.target} if instruction.target is not None else set())
    span = {(vector['init']['pc'] + k) & 0xFFFF for k in range(len(instruction.data))}
    if flow & (span - {vector['init']['pc'] & 0xFFFF}):
        return None
    return {address: memory[address] for address in site}, span, flow


def group_modules(sites):
    """Greedy, deterministic grouping so that no two sites of one module overlap or flow into each other."""
    modules = []
    for vector, memory, span, flow in sites:
        for module in modules:
            if not (module['used'] & span) and not (module['flow'] & span) and not (flow & module['used']):
                module['used'] |= span; module['flow'] |= flow; module['items'].append((vector, memory)); break
        else:
            modules.append(dict(used=set(span), flow=set(flow), items=[(vector, memory)]))
    return modules


def write_cases(path, vectors):
    lines = [HEADER, 'MPR ' + ' '.join(str(m) for m in CANONICAL_FRAME)]
    for v in vectors:
        i, f = v['init'], v['fin']
        lines.append('T %s %d %d %d %d %d %d %d %d' % (v['name'].replace(' ', '_'), v['opcode'], v['cycles'],
                                                       i['a'], i['x'], i['y'], i['s'], i['p'], i['pc']))
        lines.append('F %d %d %d %d %d %d' % (f['a'], f['x'], f['y'], f['s'], f['p'], f['pc']))
        lines.append('I %d %s' % (len(i['ram']), ' '.join('%d %d' % cell for cell in i['ram'])))
        lines.append('O %d %s' % (len(f['ram']), ' '.join('%d %d' % cell for cell in f['ram'])))
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def run_command(argv, timeout, cwd=None):
    """Argv only, no shell; output bounded; a timeout ends the process."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(argv, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
            raise RuntimeError(f'Command exceeded {timeout} seconds: {argv[0]}')
        if output.tell() > MAX_PROBE_OUTPUT:
            raise RuntimeError('Command output exceeded its bound')
        output.seek(0)
        data = output.read()
    if process.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} exited {process.returncode}: {data[-2000:].decode(errors="replace")}')
    return data.decode()


def find_probe(build):
    for name in ('pce-huc6280-vector-probe.exe', 'pce-huc6280-vector-probe'):
        candidate = Path(build) / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('pce-huc6280-vector-probe not found in the build directory')


def find_runtime_library(build):
    for name in ('libpce-runtime.a', 'pce-runtime.lib'):
        candidate = Path(build) / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('The pce-runtime library was not found in the build directory')


def parse_lines(text):
    return [json.loads(line) for line in text.splitlines() if line.startswith('{')]


def totals(rows):
    keys = ('vectors', 'executed', 'refused', 'faulted', 'state_not_comparable', 'state_equal', 'state_different',
            'cycles_equal', 'cycles_different', 'both_equal')
    result = {k: sum(r[k] for r in rows) for k in keys}
    result['classes'] = {c: sum(r['classes'][c] for r in rows) for c in ('registers', 'flags', 'pc', 'mpr', 'memory')}
    return result


def summarize_tier(rows):
    return dict(totals=totals(rows),
                refused_opcodes=sorted(r['opcode'] for r in rows if r['refused']),
                opcodes_with_differences=sorted(r['opcode'] for r in rows if r['state_different'] or r['cycles_different']),
                per_opcode={r['opcode']: {k: r[k] for k in r if k not in ('tier', 'opcode')} for r in rows})


def run_native_tier(args, corpus, probe_source, work):
    from pcerecomp import analysis, emitter, isa
    library = find_runtime_library(args.build)
    selected_all, excluded_all, sites = [], {}, []
    for op in range(256):
        if op not in isa.NATIVE:
            continue
        vectors = read_vectors(Path(corpus) / 'v1' / f'{op:02x}.json.bin')
        selected, excluded = select_native(vectors, args.native_per_opcode, isa.NATIVE)
        for reason, count in excluded.items():
            excluded_all[reason] = excluded_all.get(reason, 0) + count
        for vector in selected:
            canonical = to_canonical(vector)
            site = site_bytes(canonical, isa) if canonical else None
            if site is None:
                excluded_all['cannot form a guarded site'] = excluded_all.get('cannot form a guarded site', 0) + 1
                continue
            sites.append((canonical, site[0], site[1], site[2]))
    modules = group_modules(sites)
    rows, different, cases = [], 0, 0
    system = ['-lws2_32'] if os.name == 'nt' else ['-ldl', '-pthread']
    for index, module in enumerate(modules):
        directory = Path(work) / f'native-{index}'
        directory.mkdir()
        memory = {}
        for _, site in module['items']:
            memory.update(site)
        entries = tuple(v['init']['pc'] for v, _ in module['items'])
        snapshot = analysis.Snapshot(CANONICAL_FRAME, memory, entries, f'huc6280-vectors-{index}')
        emitter.emit(analysis.analyze(snapshot, limit=len(entries) * 4 + 16), directory)
        write_cases(directory / 'cases.txt', [v for v, _ in module['items']])
        exe = directory / ('probe.exe' if os.name == 'nt' else 'probe')
        run_command([args.compiler, '-std=c++20', '-O1', '-I', str(ROOT / 'runtime' / 'include'), str(probe_source),
                     str(directory / 'module.cpp'), str(library), *system, '-o', str(exe)], args.timeout)
        lines = parse_lines(run_command([str(exe), 'native', str(directory / 'cases.txt')], args.timeout))
        rows += [r for r in lines if r.get('tier') == 'native']
        summary = [r for r in lines if 'native_vs_interpreter_different' in r][0]
        different += summary['native_vs_interpreter_different']; cases += summary['cases']
    merged = {}
    for r in rows:
        if r['opcode'] in merged:
            for k in r:
                if isinstance(r[k], int):
                    merged[r['opcode']][k] += r[k]
            for c in r['classes']:
                merged[r['opcode']]['classes'][c] += r['classes'][c]
            merged[r['opcode']].setdefault('first_difference', r.get('first_difference'))
        else:
            merged[r['opcode']] = r
    result = summarize_tier(list(merged.values()))
    result.update(modules=len(modules), cases=cases, native_vs_interpreter_different=different,
                  selection=dict(per_opcode=args.native_per_opcode, excluded=excluded_all,
                                 native_opcodes_with_sites=len(merged)))
    return result


def git_revision():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def command_run(args):
    out = Path(args.out)
    if out.exists():
        raise FileExistsError('The report path exists; choose a new file')
    manifest = load_manifest()
    corpus_bytes = verify_corpus(args.corpus, manifest)
    started = time.monotonic()
    probe = find_probe(args.build)
    ops = args.ops or 'all'
    interpreter = parse_lines(run_command([str(probe), 'interp', str(Path(args.corpus) / 'v1'), ops], args.timeout))
    report = dict(
        schema=1, kind='huc6280-vector-reference',
        corpus=dict(repository=REPOSITORY, commit=COMMIT, files=len(manifest), bytes=corpus_bytes,
                    digest_of_digests=digest_of_digests(manifest), generator='Mesen (revision not recorded by the corpus)',
                    nature='expectations from another emulator, not hardware measurements'),
        toolkit=dict(git_revision=git_revision()),
        not_observed=list(NOT_OBSERVED),
        tiers=dict(interpreter=summarize_tier(interpreter)))
    if args.compiler:
        with tempfile.TemporaryDirectory() as work:
            report['tiers']['native'] = run_native_tier(args, args.corpus, ROOT / 'tests' / 'huc6280_vector_probe.cpp', work)
    else:
        report['tiers']['native'] = dict(not_run='no --compiler given')
    report['elapsed_seconds'] = round(time.monotonic() - started, 1)
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=1, sort_keys=True)
        stream.write('\n')
    totals_ = report['tiers']['interpreter']['totals']
    print(f"interpreter: {totals_['vectors']} vectors, {totals_['both_equal']} fully equal, "
          f"{totals_['state_different']} state differences, {totals_['cycles_different']} cycle differences, "
          f"{totals_['state_not_comparable']} cut by the generator cap, {totals_['refused']} refused")
    return 0


def command_fetch(args):
    out = Path(args.out)
    if out.exists():
        raise FileExistsError('The output directory exists; choose a new one')
    manifest = load_manifest()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, ignore_cleanup_errors=True) as work:
        clone = Path(work) / 'clone'
        clone.mkdir()
        for argv in (['git', 'init', '-q'], ['git', 'remote', 'add', 'origin', REPOSITORY],
                     ['git', 'fetch', '-q', '--depth', '1', 'origin', COMMIT],
                     ['git', 'checkout', '-q', '--detach', 'FETCH_HEAD']):
            run_command(argv, args.timeout, cwd=clone)
        if run_command(['git', 'rev-parse', 'HEAD'], 30, cwd=clone).strip() != COMMIT:
            raise RuntimeError('The fetched commit is not the pinned commit')
        verify_corpus(clone, manifest)
        shutil.copytree(clone / 'v1', Path(work) / 'staged' / 'v1')
        shutil.move(str(Path(work) / 'staged'), str(out))
    print(f'Corpus verified at {out} ({len(manifest)} files, digest of digests {digest_of_digests(manifest)})')
    return 0


def command_verify(args):
    total = verify_corpus(args.corpus, load_manifest())
    print(f'Corpus matches the manifest: 256 files, {total} bytes')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    fetch = sub.add_parser('fetch'); fetch.add_argument('out'); fetch.add_argument('--timeout', type=int, default=900)
    verify = sub.add_parser('verify'); verify.add_argument('corpus')
    run = sub.add_parser('run')
    run.add_argument('corpus'); run.add_argument('--build', required=True, type=Path); run.add_argument('--out', required=True)
    run.add_argument('--compiler', help='GCC- or Clang-style C++20 compiler for the native tier (MSVC cl is not supported); without it the native tier is reported as not run')
    run.add_argument('--native-per-opcode', type=int, default=40); run.add_argument('--ops'); run.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args(argv)
    if args.command == 'run' and not 1 <= args.native_per_opcode <= 500:
        parser.error('--native-per-opcode must be in 1..500')
    return dict(fetch=command_fetch, verify=command_verify, run=command_run)[args.command](args)


if __name__ == '__main__':
    raise SystemExit(main())
