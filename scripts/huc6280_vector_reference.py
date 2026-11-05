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
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pcerecomp.snapshots import SnapshotStore

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
    if p != len(data):
        raise ValueError('Corpus records do not consume the complete file')
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
    return dict(vector, original=vector, init=dict(vector['init'], ram=init), fin=dict(vector['fin'], ram=final))


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


def run_command(argv, timeout, cwd=None, *, log=None):
    """Argv only, no shell; output bounded; a timeout ends the process."""
    if log is not None:
        Path(str(log) + '.command.json').write_text(json.dumps(dict(argv=list(map(str, argv)), cwd=str(cwd) if cwd else None)), encoding='utf-8')
    with (Path(log).open('x+b') if log is not None else tempfile.TemporaryFile()) as output:
        process = subprocess.Popen(argv, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if os.fstat(output.fileno()).st_size > MAX_PROBE_OUTPUT:
                    process.kill(); process.wait()
                    raise RuntimeError('Command output exceeded its bound')
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(argv, timeout)
                time.sleep(0.02)
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


def requested_opcodes(text):
    if text is None or text == 'all':
        return list(range(256))
    parts = text.split(',')
    if not parts or any(not re.fullmatch(r'[0-9a-fA-F]{1,2}', p) for p in parts):
        raise ValueError('Opcodes must be comma-separated hex bytes')
    result = [int(p, 16) for p in parts]
    if len(set(result)) != len(result):
        raise ValueError('Duplicate requested opcode')
    return sorted(result)


def parse_lines(text):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('Duplicate probe JSON key')
            result[k] = v
        return result
    def constant(value):
        raise ValueError('Non-finite probe JSON')
    rows = [json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
            for line in text.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Probe rows must be objects')
    return rows


def validate_rows(rows, expected, tier):
    actual = {}
    counters = ('vectors', 'executed', 'refused', 'faulted', 'state_not_comparable',
                'state_equal', 'state_different', 'cycles_equal', 'cycles_different', 'both_equal')
    for row in rows:
        op = row.get('opcode')
        if row.get('tier') != tier or op not in expected or op in actual:
            raise ValueError('Unexpected, duplicate or wrong-tier probe row')
        if any(type(row.get(k)) is not int or row[k] < 0 for k in counters):
            raise ValueError('Invalid probe counter')
        if row['vectors'] != expected[op] or row['vectors'] != row['executed'] + row['refused'] + row['faulted']:
            raise ValueError('Probe vector accounting differs')
        if row['executed'] != row['state_equal'] + row['state_different'] + row['state_not_comparable'] or row['executed'] != row['cycles_equal'] + row['cycles_different']:
            raise ValueError('Probe state/cycle accounting differs')
        if row['both_equal'] > min(row['state_equal'], row['cycles_equal']):
            raise ValueError('Impossible fully-equal count')
        classes = row.get('classes')
        if not isinstance(classes, dict) or set(classes) != {'registers', 'flags', 'pc', 'mpr', 'memory'} or any(type(v) is not int or not 0 <= v <= row['state_different'] for v in classes.values()):
            raise ValueError('Invalid difference classes')
        if sum(classes.values()) < row['state_different']:
            raise ValueError('Missing difference classification')
        if bool(row['state_different'] or row['cycles_different']) != isinstance(row.get('first_difference'), dict):
            raise ValueError('Missing or unexpected first difference')
        actual[op] = row
    if not actual or set(actual) != set(expected):
        raise ValueError('Missing or empty probe results')
    return rows


def merge_rows(rows):
    merged = {}
    for row in rows:
        op = row['opcode']
        if op not in merged:
            merged[op] = json.loads(json.dumps(row))
            continue
        target = merged[op]
        for k, value in row.items():
            if type(value) is int:
                target[k] += value
        for k, value in row['classes'].items():
            target['classes'][k] += value
        if not target.get('first_difference') and row.get('first_difference'):
            target['first_difference'] = row['first_difference']
    return list(merged.values())


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
    excluded_all, sites = {}, []
    for op in range(256):
        if op not in isa.NATIVE or op not in requested_opcodes(args.ops):
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
        vectors = [v for v, _ in module['items']]
        write_cases(directory / 'cases.txt', vectors)
        (directory / 'selection.json').write_text(json.dumps(dict(canonical_mpr=CANONICAL_FRAME, cases=vectors)), encoding='utf-8')
        exe = directory / ('probe.exe' if os.name == 'nt' else 'probe')
        run_command([args.compiler, '-std=c++20', '-O1', '-I', str(ROOT / 'runtime' / 'include'), str(probe_source),
                     str(directory / 'module.cpp'), str(library), *system, '-o', str(exe)], args.timeout, log=directory / 'compile.log')
        lines = parse_lines(run_command([str(exe), 'native', str(directory / 'cases.txt')], args.timeout, log=directory / 'raw.jsonl'))
        expected = {}
        for v in vectors:
            op = f"{v['opcode']:02X}"
            expected[op] = expected.get(op, 0) + 1
        native_rows = validate_rows([r for r in lines if r.get('tier') == 'native'], expected, 'native')
        validate_rows([r for r in lines if r.get('tier') == 'interpreter-on-native-cases'], expected, 'interpreter-on-native-cases')
        summaries = [r for r in lines if set(r) == {'native_vs_interpreter_different', 'cases'}]
        if len(summaries) != 1 or len(lines) != 2 * len(expected) + 1:
            raise ValueError('Missing or unexpected native summary')
        summary = summaries[0]
        if type(summary['cases']) is not int or summary['cases'] != len(vectors) or type(summary['native_vs_interpreter_different']) is not int or not 0 <= summary['native_vs_interpreter_different'] <= len(vectors):
            raise ValueError('Native summary accounting differs')
        if any(r['faulted'] or r['refused'] or r['executed'] != r['vectors'] for r in lines if 'tier' in r):
            raise ValueError('Native sample did not execute all selected cases')
        rows += native_rows
        different += summary['native_vs_interpreter_different']; cases += summary['cases']
    merged = merge_rows(rows)
    result = summarize_tier(merged)
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
    ops = requested_opcodes(args.ops)
    bundle = Path(str(out) + '.artifacts')
    bundle.mkdir()  # Retain diagnostics even when execution fails.
    store = SnapshotStore()
    inputs = {}
    def bind(label, path):
        snap = store.bind(Path(path).absolute())
        inputs[label] = dict(path=str(snap.path), sha256=snap.sha256, size_bytes=snap.size_bytes)
    bind('manifest', MANIFEST)
    manifest = load_manifest()
    corpus_bytes = verify_corpus(args.corpus, manifest)
    for name, (digest, size) in manifest.items():
        bind('corpus/' + name, Path(args.corpus) / name)
        if inputs['corpus/' + name]['sha256'] != digest:
            raise ValueError('Corpus changed after admission')
    for base in ('pcerecomp', 'runtime', 'cmake'):
        for path in sorted((ROOT / base).rglob('*')):
            if path.is_file() and path.suffix in {'.py', '.cpp', '.hpp', '.h', '.cmake'}:
                bind('source/' + path.relative_to(ROOT).as_posix(), path)
    for name in ('CMakeLists.txt', 'scripts/huc6280_vector_reference.py', 'tests/huc6280_vector_probe.cpp'):
        bind('source/' + name, ROOT / name)
    started = time.monotonic()
    probe = find_probe(args.build).resolve()
    bind('probe', probe)
    bind('runtime_library', find_runtime_library(args.build))
    cache = Path(args.build) / 'CMakeCache.txt'
    if cache.is_file():
        bind('cmake_cache', cache)
    if args.compiler:
        compiler = shutil.which(args.compiler)
        if compiler is None:
            raise FileNotFoundError('Native compiler not found')
        args.compiler = str(Path(compiler).resolve())
        bind('compiler', args.compiler)
    expected = {f'{op:02X}': len(read_vectors(Path(args.corpus) / 'v1' / f'{op:02x}.json.bin')) for op in ops}
    store.revalidate()
    interpreter = validate_rows(parse_lines(run_command([str(probe), 'interp', str(Path(args.corpus).resolve() / 'v1'), ','.join(f'{op:02x}' for op in ops)], args.timeout, log=bundle / 'interpreter.jsonl')), expected, 'interpreter')
    store.revalidate()
    report = dict(
        schema=1, kind='huc6280-vector-reference', qualification=False, requested_opcodes=ops,
        corpus=dict(repository=REPOSITORY, commit=COMMIT, files=len(manifest), bytes=corpus_bytes,
                    digest_of_digests=digest_of_digests(manifest), generator='Mesen (revision not recorded by the corpus)',
                    nature='expectations from another emulator, not hardware measurements'),
        toolkit=dict(git_revision=git_revision(), inputs=inputs, build_source_correspondence='not_authenticated_by_adapter'),
        not_observed=list(NOT_OBSERVED),
        tiers=dict(interpreter=summarize_tier(interpreter)))
    if args.compiler:
        report['tiers']['native'] = run_native_tier(args, args.corpus, ROOT / 'tests' / 'huc6280_vector_probe.cpp', bundle)
    else:
        report['tiers']['native'] = dict(not_run='no --compiler given')
    store.revalidate()
    artifacts = {}
    for path in sorted(bundle.rglob('*')):
        if path.is_file():
            snap = store.bind(path.absolute())
            artifacts[path.relative_to(bundle).as_posix()] = dict(sha256=snap.sha256, size_bytes=snap.size_bytes)
    report['artifacts'] = artifacts
    store.revalidate()
    report['elapsed_seconds'] = round(time.monotonic() - started, 1)
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=1, sort_keys=True)
        stream.write('\n')
    store.revalidate()
    with Path(str(out) + '.closed.json').open('x', encoding='utf-8') as closed:
        json.dump(dict(schema=1, complete=True, report_sha256=sha256_file(out), qualification=False), closed)
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
    if hasattr(args, 'timeout') and not 1 <= args.timeout <= 86400:
        parser.error('--timeout must be in 1..86400')
    if args.command == 'run' and not 1 <= args.native_per_opcode <= 500:
        parser.error('--native-per-opcode must be in 1..500')
    return dict(fetch=command_fetch, verify=command_verify, run=command_run)[args.command](args)


if __name__ == '__main__':
    raise SystemExit(main())
