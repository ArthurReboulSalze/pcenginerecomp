"""Opt-in, content-verified resumable LLVM-MinGW/Ninja consumer builds.

Configuration and object checkpoints are immutable, create-new records.  A
checkpoint proves completed artifacts, never the execution of a guest program.
The operating-system lock and managed child-process barrier are both required:
an abandoned lock file alone is neither ownership nor evidence of quiescence.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

from . import build_inputs
from .build_cache import _canonical, _json


_META = '.pce-recovery'
_LOCK = '.pce-recovery.lock'
_CHUNK = 32
_MAX_METADATA_BYTES = 64 * 1024 * 1024
_CHECKPOINT_KIND = 'pce-object-checkpoint-delta-v1'
_ADMISSION_KIND = 'pce-object-attempt-admission-v1'


def _require(condition, message):
    if not condition:
        raise ValueError('Build recovery: ' + message)


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _directory(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        info = item.lstat()
        _require(stat.S_ISDIR(info.st_mode) and not _linked(info),
                 'paths and parents must be ordinary directories')
    return path


def _regular(path):
    _directory(path.parent)
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and not _linked(info) and info.st_nlink == 1,
             'files must be ordinary files without links or hardlinks')
    return info


def _scan(root):
    _directory(root)
    for path in root.rglob('*'):
        info = path.lstat()
        _require(not _linked(info), 'tree contains a link or reparse point')
        _require(stat.S_ISDIR(info.st_mode) or
                 (stat.S_ISREG(info.st_mode) and info.st_nlink == 1),
                 'tree contains a nonregular file or hardlink')


def _hash(path):
    before = _regular(path)
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        _require(signature(os.fstat(stream.fileno())) == signature(before), 'file changed while opening')
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
        _require(signature(os.fstat(stream.fileno())) == signature(before), 'file changed while hashing')
    _require(signature(_regular(path)) == signature(before), 'file changed after hashing')
    return dict(bytes=before.st_size, sha256=digest.hexdigest())


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _same(left, right):
    return _canonical(left) == _canonical(right)


def _sync_directory(path):
    # Windows FlushFileBuffers on the file is the durable publication boundary;
    # POSIX additionally permits syncing the containing directory entry.
    if os.name != 'nt':
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_new(path, value):
    """Flush complete bytes before atomically publishing a create-new name."""
    _directory(path.parent)
    data = _canonical(value) + b'\n'
    _require(len(data) <= _MAX_METADATA_BYTES, 'metadata exceeds JSON bound before publication')
    descriptor, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            move = kernel.MoveFileExW
            move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            move.restype = wintypes.BOOL
            # Write-through publication, deliberately without REPLACE_EXISTING.
            if not move(str(temporary), str(path), 0x8):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.link(temporary, path)
            temporary.unlink()
        _sync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read(path):
    _require(_regular(path).st_size <= _MAX_METADATA_BYTES, 'metadata exceeds JSON bound')
    raw = path.read_bytes()
    value = _json(raw)
    _require(raw == _canonical(value) + b'\n', 'metadata bytes differ from canonical durable format')
    return value


def _sealed(value):
    return dict(value, sha256=_digest(value))


def _check_seal(value):
    _require(type(value) is dict and value.get('sha256') ==
             _digest({key:item for key,item in value.items() if key != 'sha256'}),
             'metadata content checksum differs')
    return value


@contextmanager
def _locked(root):
    """Nonblocking OS lock, held across quiescence, verification and cleanup."""
    root = _directory(root)
    identity = (root.stat().st_dev, root.stat().st_ino)
    path = root/_LOCK
    if path.exists() or path.is_symlink():
        _regular(path)
    handle = None
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                           wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        # The process guardian inherits a duplicate of this share-zero lease.
        # Owner death cannot release exclusion until the guardian drains children.
        handle = create(str(path), 0xc0000000, 0, None, 4, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ValueError('Build recovery: directory is busy or its lease is unavailable')
        fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    else:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    stream = os.fdopen(fd, 'r+b', buffering=0)
    acquired = False
    try:
        lock_identity = (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        _require(lock_identity == (_regular(path).st_dev, path.stat().st_ino), 'lock identity changed')
        _require(_regular(path).st_size == 0,
                 'directory quarantined: process cleanup was not proven; explicit review required')
        try:
            if os.name != 'nt':
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as error:
            raise ValueError('Build recovery: directory is busy') from error
        def held():
            _directory(root)
            _require(identity == (root.stat().st_dev, root.stat().st_ino), 'build root identity changed')
            lock_info = _regular(path)
            _require(lock_identity == (lock_info.st_dev, lock_info.st_ino), 'held lock changed')
            _require(lock_info.st_size == 0,
                     'directory quarantined: process cleanup was not proven; explicit review required')
        if os.name == 'nt':
            from . import build_process
            lease = build_process.directory_lease(root, handle)
        else:
            lease = nullcontext()
        with lease:
            held()
            yield held
            held()
    finally:
        if acquired:
            if os.name != 'nt':
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        stream.close()


def _relative(root, name):
    _require(type(name) is str and name and '\\' not in name and '\x00' not in name,
             'unsafe artifact path')
    path = Path(name)
    _require(not path.is_absolute() and not path.drive and
             all(part not in ('', '.', '..') and ':' not in part for part in name.split('/')),
             'artifact path escapes build tree')
    result = root/path
    _directory(result.parent)
    _require(result.resolve().is_relative_to(root.resolve()), 'artifact path escapes build tree')
    if result.exists() or result.is_symlink():
        _regular(result)
    return result


def _target_name(name):
    # CMake inserts ./ in shortened Windows object paths. Only audited Ninja
    # target spellings may normalize this self-reference; parent traversal and
    # alternate separators are never admitted by the artifact-path interface.
    _require(type(name) is str and name and '\\' not in name and
             all(part not in ('', '..') for part in name.split('/')), 'unsafe Ninja target path')
    return '/'.join(part for part in name.split('/') if part != '.')


def _captured(context, binary, *arguments):
    result = subprocess.run([str(context['tools']['ninja']), '-C', str(binary), *arguments],
                            env=context['environment'], capture_output=True, text=True,
                            check=True, timeout=60)
    return result.stdout


def _graph(context, binary):
    """Join actual Ninja compilation-database outputs with actual graph rules."""
    rows = _json(_captured(context, binary, '-t', 'compdb').encode())
    targets = {}
    for line in _captured(context, binary, '-t', 'targets', 'all').splitlines():
        name, separator, rule = line.rpartition(': ')
        _require(bool(separator), 'invalid Ninja target inventory')
        normalized = _target_name(name)
        _require(normalized not in targets, 'duplicate normalized Ninja target')
        targets[normalized] = rule
    objects = []
    for row in rows:
        output = row.get('output')
        if not isinstance(output, str) or not output.endswith('.obj'):
            continue
        output = _target_name(output)
        _require(targets.get(output, '').startswith('CXX_COMPILER__'),
                 'object is not an audited CXX graph target')
        _relative(binary, output)
        _require(Path(row['directory']).resolve() == binary.resolve(), 'unexpected compile directory')
        source = Path(row['file'])
        source = source if source.is_absolute() else binary/source
        build_inputs._audit_paths(context, binary)(str(source))
        objects.append(output)
    _require(objects and len(objects) == len(set(objects)), 'missing or duplicate CXX object targets')
    actual = {name for name, rule in targets.items() if rule.startswith('CXX_COMPILER__')}
    _require(set(objects) == actual, 'compilation database does not cover the audited CXX graph')
    links = sorted(name for name, rule in targets.items()
                   if rule.startswith(('CXX_EXECUTABLE_LINKER__', 'CXX_STATIC_LIBRARY_LINKER__')))
    _require(links, 'missing audited link targets')
    for name in links:
        _relative(binary, name)
    response_files = set()
    for line in (binary/'build.ninja').read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'\s+RSP_FILE = (.+\.rsp)', line)
        if match:
            name = _target_name(match[1].replace('$ ', ' ').replace('$:', ':').replace('$$', '$').replace('\\', '/'))
            _relative(binary, name)
            response_files.add(name)
    return dict(objects=sorted(objects), links=links, response_files=sorted(response_files))


def _dependency_inventory(context, binary, outputs):
    """One Ninja observer and one content read per unique header per phase."""
    if not outputs:
        return {}
    # Asking for the complete dependency database avoids Windows command-line
    # length limits for large modules; only requested, audited targets are used.
    text = _captured(context, binary, '-t', 'deps')
    entries, current = {}, None
    requested = set(outputs)
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith('    '):
            _require(current is not None, 'orphan compiler dependency record')
            entries[current].append(line[4:])
        else:
            name, separator, record = line.partition(': #deps ')
            _require(separator, 'invalid actual Ninja dependency record')
            current = _target_name(name)
            if current in requested:
                _require(record.endswith('(VALID)'), 'object lacks a valid actual Ninja dependency record')
            _require(current not in entries, 'duplicate compiler dependency record')
            entries[current] = []
    _require(requested <= set(entries), 'missing actual compiler dependency record')
    result, memo = {}, {}
    allowed = build_inputs._audit_paths(context, binary)
    for output, names in entries.items():
        if output not in requested:
            continue
        _require(names, 'empty actual compiler dependency closure')
        dependencies = {}
        for name in names:
            path = allowed(name)
            key = str(path)
            if key not in memo:
                memo[key] = _hash(path)
            dependencies[key] = memo[key]
        result[output] = dependencies
    return result


def _dependencies(context, binary, output):
    return _dependency_inventory(context, binary, [output])[output]


def _snapshot(root):
    """Seal raw configure outputs, including generated compiler inputs/API."""
    files = {}
    for folder in (root/'source', root/'build'):
        _scan(folder)
        for path in sorted(folder.rglob('*')):
            if path.is_file() and path.name not in ('.ninja_log', '.ninja_deps'):
                files[path.relative_to(root).as_posix()] = _hash(path)
    for required in ('source/CMakeLists.txt', 'build/CMakeCache.txt', 'build/build.ninja',
                     'build/CMakeFiles/rules.ninja'):
        _require(required in files, 'missing immutable configuration input ' + required)
    return files


def _verify_snapshot(root, files):
    _scan(root)
    for name, expected in files.items():
        path = _relative(root, name)
        _require(path.exists() and _hash(path) == expected, 'immutable configuration changed: ' + name)


def _temporary_objects(binary, graph):
    """Recognize Clang atomic-output siblings of exact audited object targets.

    Clang derives its model from the destination stem, an eight-hex unique
    suffix, the destination extension and .tmp. Discovery is confined to the
    audited destination directories; neither a tree wildcard nor a source/RSP
    filename authorizes removal. Returned paths still require full immutable,
    checkpoint and retained-dependency verification before cleanup.

    Naming reference (LLVM 22.1.8 VirtualOutputBackends.cpp, lines 275-295):
    https://github.com/llvm/llvm-project/blob/llvmorg-22.1.8/llvm/lib/Support/VirtualOutputBackends.cpp
    """
    directories = {}
    for output in graph['objects']:
        target = _relative(binary, output)
        directories.setdefault(target.parent, {})[target.name[:-4]] = output
    result = {}
    for directory, stems in directories.items():
        for path in directory.iterdir():
            match = re.fullmatch(r'(.+)-[0-9a-f]{8}\.obj\.tmp', path.name)
            if match and match[1] in stems:
                _regular(path)
                result[path.relative_to(binary).as_posix()] = stems[match[1]]
    return dict(sorted(result.items()))


def _ownership(root, seal, package_outputs, dll_names=()):
    """Reject foreign paths before executing Ninja or removing owned outputs."""
    files = set(seal['files']) | {_LOCK}
    files.update('build/'+name for name in seal['graph']['objects'] + package_outputs)
    files.update('build/'+name for name in seal['graph'].get('response_files', []))
    files.update('build/'+name for name in _temporary_objects(root/'build', seal['graph']))
    for name in seal['graph']['objects']:
        files.update(('build/'+name+'.d', 'build/'+name+'.rsp'))
    files.update(('build/.ninja_log', 'build/.ninja_deps', 'build/.ninja_lock'))
    ninja_lock = root/'build/.ninja_lock'
    if ninja_lock.exists():
        _require(_regular(ninja_lock).st_size == 0, 'unexpected Ninja lock contents')
    # CMake/Ninja may retain response files for link commands interrupted by
    # termination; these are never command inputs in this audited profile.
    for name in seal['graph']['links']:
        files.add('build/'+name+'.rsp')
    directories = set(seal['directories']) | {_META}
    for name in files:
        directories.update(parent.as_posix() for parent in Path(name).parents if parent != Path('.'))
    analysis = re.compile(r'build/CMakeFiles/pce-consumer-runtime-Release/'
                          r'[0-9a-f]{64}(?:-[0-9a-f]{64})?(?:/[^/]+)?\Z')
    package_names = {Path(name).name.lower() for name in package_outputs if name.startswith('bin/')} | set(dll_names)
    for path in root.rglob('*'):
        name = path.relative_to(root).as_posix()
        if name in files or (path.is_dir() and name in directories):
            continue
        if name.startswith(_META+'/') and path.is_file():
            leaf = path.name
            _require('/' not in name[len(_META)+1:] and
                     (leaf in ('contract.json','configured.json') or
                      re.fullmatch(r'(?:checkpoint-\d{6}|attempt-\d{6}-(?:start|result|admission))\.json',leaf) or
                      leaf.startswith('.pending-')), 'foreign recovery metadata path: ' + name)
            continue
        if name.startswith('.pending-') and '/' not in name and path.is_file():
            continue  # Interrupted atomic receipt publication, kept for review.
        if name == 'build/CMakeFiles/pce-consumer-runtime-Release' and path.is_dir():
            continue
        if analysis.fullmatch(name):
            if path.is_dir() and name.count('/') == 3:
                continue
            if path.is_file() and name.count('/') == 4 and path.name.lower() in package_names:
                continue
        raise ValueError('Build recovery: foreign build path: '+name)


def _fingerprint(item):
    return (type(item) is dict and set(item) == {'bytes','sha256'} and
            type(item['bytes']) is int and item['bytes'] >= 0 and
            type(item['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',item['sha256']))


def _object_record(record):
    return (type(record) is dict and set(record) == {'artifact','dependencies'} and
            _fingerprint(record['artifact']) and type(record['dependencies']) is dict and
            bool(record['dependencies']) and all(type(path) is str and _fingerprint(identity)
                for path, identity in record['dependencies'].items()))


def _checkpoints(meta, contract_sha, outputs):
    """Replay bounded deltas and durable missing-object invalidations.

    Admissions with no completed compilation still invalidate a missing seal.
    A later attempt must rebuild its unsealed output even if that output happens
    to equal the historical record; it cannot be retained under the old seal.
    """
    previous, ledger, sequence, pending = None, {}, 0, {}
    outputs = set(outputs)
    paths = iter(sorted(meta.glob('checkpoint-*.json')))
    next_path = next(paths, None)
    next_value = _check_seal(_read(next_path)) if next_path else None
    for admission_path in sorted(meta.glob('attempt-*-admission.json')):
        admission = _check_seal(_read(admission_path))
        number = admission.get('attempt')
        _require(set(admission) == {'schema','kind','attempt','contract_sha256','attempt_start_sha256',
                 'base_sequence','base_checkpoint_sha256','new_objects','missing_objects','sha256'} and
                 type(admission['schema']) is int and admission['schema'] == 1 and
                 admission['kind'] == _ADMISSION_KIND and type(number) is int and number > 0 and
                 admission_path.name == f'attempt-{number:06d}-admission.json' and
                 admission['contract_sha256'] == contract_sha and type(admission['base_sequence']) is int and
                 admission['base_sequence'] == sequence and admission['base_checkpoint_sha256'] == previous,
                 'attempt admission provenance or base chain differs')
        start = _check_seal(_read(meta/f'attempt-{number:06d}-start.json'))
        _require(type(start.get('schema')) is int and start['schema'] == 1 and
                 type(start.get('attempt')) is int and start['attempt'] == number and
                 type(start.get('resume')) is bool and type(start.get('started_ns')) is int and
                 start.get('contract_sha256') == contract_sha and
                 _digest(start) == admission['attempt_start_sha256'], 'admission attempt start differs')
        new, missing = admission['new_objects'], admission['missing_objects']
        _require(type(new) is list and all(type(name) is str for name in new) and
                 len(new) == len(set(new)) and set(new) == outputs-set(ledger) and
                 type(missing) is dict and set(missing) <= set(ledger)-set(pending),
                 'invalid new/missing object admission')
        admission_sha = _digest(admission)
        for name, old_digest in missing.items():
            _require(type(old_digest) is str and old_digest == _digest(ledger[name]),
                     'missing-object admission differs from historical seal')
            pending[name] = dict(previous_record_sha256=old_digest, origin_attempt=number,
                                 admission_sha256=admission_sha)
        updated = set()
        while next_value is not None and next_value.get('attempt') == number:
            value = next_value
            sequence += 1
            _require(next_path.name == f'checkpoint-{sequence:06d}.json' and
                     set(value) == {'schema','kind','contract_sha256','sequence','attempt',
                                    'previous_sha256','admission_sha256','objects','operations','sha256'} and
                     type(value['schema']) is int and value['schema'] == 2 and
                     value['kind'] == _CHECKPOINT_KIND and value['contract_sha256'] == contract_sha and
                     type(value['sequence']) is int and value['sequence'] == sequence and
                     type(value['attempt']) is int and value['attempt'] == number and
                     value['previous_sha256'] == previous and value['admission_sha256'] == admission_sha,
                     'checkpoint provenance, schema or chain differs')
            objects, operations = value['objects'], value['operations']
            _require(type(objects) is dict and 1 <= len(objects) <= _CHUNK and
                     set(objects) <= outputs and type(operations) is dict and
                     set(operations) == set(objects) and not (set(objects) & updated),
                     'invalid, duplicate or oversized checkpoint delta')
            for name, record in objects.items():
                operation = operations[name]
                _require(_object_record(record) and type(operation) is dict and
                         set(operation) == {'kind','previous_record_sha256','origin_attempt'},
                         'invalid typed object checkpoint update')
                if operation['kind'] == 'new':
                    _require(name in new and name not in ledger and name not in pending and
                             operation['previous_record_sha256'] is None and operation['origin_attempt'] is None,
                             'new update would overwrite a historical object seal')
                else:
                    _require(operation['kind'] == 'rebuild-missing' and name in pending and
                             type(operation['origin_attempt']) is int and
                             operation['origin_attempt'] == pending[name]['origin_attempt'] and
                             operation['previous_record_sha256'] == pending[name]['previous_record_sha256'] and
                             operation['previous_record_sha256'] == _digest(ledger[name]),
                             'object replacement lacks matching missing-object admission')
                    del pending[name]
                ledger[name] = record
                updated.add(name)
            previous = _digest(value)
            next_path = next(paths, None)
            next_value = _check_seal(_read(next_path)) if next_path else None
        if next_value is not None:
            _require(type(next_value.get('attempt')) is int and next_value['attempt'] > number,
                     'checkpoint attempt has no matching ordered admission')
    _require(next_value is None, 'checkpoint has no matching attempt admission')
    return sequence, previous, ledger, pending


def _dll_inputs(context):
    candidates = {}
    for root in [Path(context['contract']['trees']['toolchain']['path']),
                 *(Path(item['path']) for item in context['contract']['trees']['dependencies'])]:
        for path in root.rglob('*.dll'):
            candidates.setdefault(path.name.lower(), []).append(path)
    return candidates


def _package_outputs(context, binary, graph, *, verify=False):
    """Only known linker outputs and declared SDK/toolchain DLL basenames."""
    package = binary/'bin'
    candidates = _dll_inputs(context)
    known = set(graph['links'])
    if package.exists():
        _directory(package)
        for path in package.iterdir():
            _regular(path)
            name = path.relative_to(binary).as_posix()
            _require(name in known or path.name.lower() in candidates,
                     'foreign package file: ' + path.name)
            if verify and path.name.lower().endswith('.dll'):
                _require(any(_hash(path) == _hash(source) for source in candidates.get(path.name.lower(), [])),
                         'packaged DLL differs from the declared toolchain/SDK')
            known.add(name)
    return sorted(known)


def _options(*, generator, desktop, cmake_args, toolchain_root, dependency_roots,
             allow_revision_override):
    _require(type(desktop) is bool and type(allow_revision_override) is bool,
             'desktop and allow_revision_override must be boolean')
    _require(generator is None or generator == 'Ninja', 'recoverable builds require Ninja')
    _require(isinstance(cmake_args, (list, tuple)), 'cmake_args must be a sequence of CMake options')
    keys = set()
    for argument in cmake_args:
        _require(type(argument) is str and re.fullmatch(
            r'-D(CMAKE_CXX_COMPILER|CMAKE_MAKE_PROGRAM|SDL3_DIR)=[^\r\n\x00]+',argument),
            'unsupported or malformed recoverable CMake argument')
        key = argument[2:].split('=',1)[0]
        _require(key not in keys, 'duplicate recoverable CMake option')
        keys.add(key)
    _require(isinstance(dependency_roots, (list, tuple)), 'dependency_roots must be a sequence of paths')
    for path in [*dependency_roots, *([toolchain_root] if toolchain_root is not None else [])]:
        _require(isinstance(path, (str, os.PathLike)) and str(path) and '\x00' not in str(path),
                 'toolchain and dependency roots require ordinary path values')
    return dict(generator=generator or 'Ninja', desktop=desktop, cmake_args=list(cmake_args),
                toolchain_root=str(Path(toolchain_root).absolute()) if toolchain_root else None,
                dependency_roots=[str(Path(path).absolute()) for path in dependency_roots],
                allow_revision_override=allow_revision_override)


def build(descriptor, build_dir, *, resume=False, allow_revision_override=False,
          generator=None, desktop=False, cmake_args=(), toolchain_root=None,
          dependency_roots=()):
    """Build a fresh recoverable tree, or verify and resume its configured seal.

    On resume omitted options are restored from the preconfiguration contract.
    Supplying a different option is refused; resume never reconfigures CMake.
    """
    from . import project as api
    from . import build_process
    _require(type(resume) is bool, 'resume must be boolean')
    root = Path(os.path.abspath(build_dir))
    descriptor = Path(os.path.abspath(descriptor))
    requested = _options(generator=generator, desktop=desktop, cmake_args=cmake_args,
        toolchain_root=toolchain_root, dependency_roots=dependency_roots,
        allow_revision_override=allow_revision_override)
    if resume:
        _directory(root)
    else:
        _directory(root.parent)
        _require(not root.exists(), 'fresh builds require a new directory')
        root.mkdir()
    with _locked(root) as held:
        build_process.quiesce(root)
        held()
        _scan(root)
        meta = root/_META
        attempt = None
        commands = []
        try:
            if resume:
                _require(not (root/'build-receipt.json').exists(), 'completed builds cannot be resumed')
                pre = _check_seal(_read(meta/'contract.json'))
                _require(type(pre.get('schema')) is int and pre.get('schema') == 1 and
                         pre.get('kind') == 'pce-recoverable-build-v1',
                         'unrecognized recovery contract')
                _require(pre['build_dir'] == str(root) and pre['descriptor'] == str(descriptor),
                         'descriptor/build directory differs from original contract')
                _require(pre['root_identity'] == [root.stat().st_dev, root.stat().st_ino],
                         'build directory identity differs from original contract')
                saved = pre['options']
                _require(type(saved) is dict and set(saved) == set(requested), 'invalid saved options')
                _require(_same(saved, _options(**saved)), 'saved option representation differs')
                for key, value in requested.items():
                    defaults = {'generator':generator is None, 'desktop':desktop is False,
                                'cmake_args':not cmake_args, 'toolchain_root':toolchain_root is None,
                                'dependency_roots':not dependency_roots,
                                'allow_revision_override':allow_revision_override is False}
                    _require(defaults[key] or value == saved[key], 'changed resume option: ' + key)
                options = saved
                seal = _check_seal(_read(meta/'configured.json'))
            else:
                _require(set(path.name for path in root.iterdir()) == {_LOCK}, 'foreign fresh build contents')
                meta.mkdir()
                options = requested
            _require(type(options['desktop']) is bool, 'desktop must be boolean')
            _regular(descriptor)
            if options['toolchain_root']:
                _directory(Path(options['toolchain_root']))
            for folder in options['dependency_roots']:
                _directory(Path(folder))
            project = api.verify(descriptor, allow_revision_override=options['allow_revision_override'])
            _require(not options['desktop'] or project['config']['runtime']['video'] == 'continuous',
                     'desktop requires continuous video')
            arguments = dict(generator=options['generator'], desktop=options['desktop'],
                cmake_args=options['cmake_args'], toolchain_root=options['toolchain_root'],
                dependency_roots=options['dependency_roots'], build_dir=root, cache_root=None)
            def prepare(current):
                _regular(descriptor)
                _regular(current['tool_root']/'CMakeLists.txt')
                _scan(current['tool_root']/'pcerecomp')
                for path in current.get('files', {}).values():
                    _regular(path)
                # verify() resolves entry paths. Audit their original spellings
                # as well, so resolving an alias never hides an unsafe parent.
                def declared(value, *, top=False):
                    if isinstance(value, dict):
                        if 'path' in value:
                            path = Path(os.path.abspath(descriptor.parent/value['path']))
                            if top:
                                _directory(path)
                            else:
                                _regular(path)
                        for key, child in value.items():
                            if key != 'path':
                                declared(child)
                    elif isinstance(value, list):
                        for child in value:
                            declared(child)
                for key, value in current['config'].items():
                    declared(value, top=key == 'tool')
                context = build_inputs.prepare(current, **arguments)
                for folder in context['roots']:
                    _scan(Path(folder))
                return context
            context = prepare(project)
            binding = api._binding(project)
            initial = _sealed(dict(schema=1, kind='pce-recoverable-build-v1', build_dir=str(root),
                descriptor=str(descriptor), root_identity=[root.stat().st_dev, root.stat().st_ino],
                options=options, binding=binding, input_contract=context['contract'],
                checkpoint_policy=dict(kind=_CHECKPOINT_KIND, schema=2, maximum_updates=_CHUNK,
                                       maximum_metadata_bytes=_MAX_METADATA_BYTES),
                environment=context['environment']))
            if resume:
                _require(_same(initial, pre), 'source, module, SDK, toolchain, environment or options changed')
            else:
                pre = initial
                _write_new(meta/'contract.json', pre)
            contract_sha = _digest(pre)
            starts = sorted(meta.glob('attempt-*-start.json'))
            next_attempt = len(starts)+1
            _require(all(path.name == f'attempt-{index:06d}-start.json'
                         for index, path in enumerate(starts, 1)), 'invalid attempt sequence')
            for index, path in enumerate(starts, 1):
                value = _check_seal(_read(path))
                _require(type(value.get('schema')) is int and value.get('schema') == 1 and
                         type(value.get('attempt')) is int and value.get('attempt') == index and
                         type(value.get('resume')) is bool and type(value.get('started_ns')) is int and
                         value.get('contract_sha256') == contract_sha, 'attempt provenance differs')
            for path in meta.glob('attempt-*-result.json'):
                value = _check_seal(_read(path))
                number = value.get('attempt')
                _require(type(value.get('schema')) is int and value.get('schema') == 1 and
                         type(number) is int and 1 <= number < next_attempt and
                         value.get('contract_sha256') == contract_sha and
                         value.get('status') in ('complete','failed') and
                         path.name == f'attempt-{number:06d}-result.json', 'foreign attempt result')
                _require(value['status'] != 'complete', 'completed attempt cannot be resumed')
            attempt_start = _sealed(dict(schema=1, attempt=next_attempt, resume=resume,
                                         contract_sha256=contract_sha, started_ns=time.time_ns()))
            _write_new(meta/f'attempt-{next_attempt:06d}-start.json', attempt_start)
            attempt = next_attempt
            def runner(command, **kwargs):
                commands.append(list(map(str, command)))
                return build_process.run(command, env=kwargs.get('env', context['environment']), cwd=root)
            context = dict(context, recovery=True, runner=runner)
            if not resume:
                api._configure_build(project, root, generator=options['generator'],
                    desktop=options['desktop'], cmake_args=options['cmake_args'], cache_context=context)
                build_process.quiesce(root)
                configured = build_inputs.configuration_identity(context, root/'build')
                graph = _graph(context, root/'build')
                seal = _sealed(dict(schema=1, contract_sha256=contract_sha,
                            configured=configured, files=_snapshot(root), graph=graph,
                            directories=sorted(path.relative_to(root).as_posix()
                                for folder in (root/'source',root/'build')
                                for path in [folder,*folder.rglob('*')] if path.is_dir())))
                _write_new(meta/'configured.json', seal)
            _require(type(seal.get('schema')) is int and seal.get('schema') == 1 and
                     seal.get('contract_sha256') == contract_sha,
                     'configured seal provenance differs')
            configured, graph = seal['configured'], seal['graph']
            metadata_hashes = {path.name:_hash(path) for path in meta.iterdir() if path.is_file()
                               and not path.name.startswith('.pending-')}
            def unchanged():
                held()
                build_process.quiesce(root)
                _verify_snapshot(root, seal['files'])
                _require(all(_hash(meta/name) == expected for name, expected in metadata_hashes.items()),
                         'durable contract or configuration metadata changed')
                current = api.verify(descriptor, allow_revision_override=options['allow_revision_override'])
                actual = prepare(current)
                _require(_same(api._binding(current), binding) and _same(actual['contract'], pre['input_contract'])
                         and _same(actual['environment'], pre['environment']),
                         'source, module, SDK, toolchain or environment changed')
                _require(_same(build_inputs.configuration_identity(context, root/'build'), configured),
                         'actual configuration differs from immutable seal')
                _require(_graph(context, root/'build') == graph, 'actual object/link graph differs')
                _ownership(root, seal, _package_outputs(context, root/'build', graph), _dll_inputs(context))
            unchanged()
            binary = root/'build'
            sequence, previous, ledger, invalidated = _checkpoints(meta, contract_sha, graph['objects'])
            continued_rebuilds = sorted(invalidated)
            retained, missing, removed, removed_temporaries = [], [], [], []
            for output in graph['objects']:
                path = _relative(binary, output)
                if output in ledger:
                    if output in invalidated:
                        continue
                    if not path.exists():
                        missing.append(output)
                        continue
                    _require(_hash(path) == ledger[output]['artifact'], 'sealed object integrity error: ' + output)
                    retained.append(output)
            dependencies = _dependency_inventory(context, binary, retained)
            for output in retained:
                _require(_same(dependencies[output], ledger[output]['dependencies']),
                         'sealed object dependency record changed: ' + output)
            # Complete all verification before removing any unsealed output.
            owned_links = _package_outputs(context, binary, graph)
            temporary_objects = _temporary_objects(binary, graph)
            pending = [output for output in graph['objects'] if output not in retained]
            admission = _sealed(dict(schema=1, kind=_ADMISSION_KIND, attempt=attempt,
                contract_sha256=contract_sha, attempt_start_sha256=_digest(attempt_start),
                base_sequence=sequence, base_checkpoint_sha256=previous,
                new_objects=sorted(set(graph['objects'])-set(ledger)),
                missing_objects={name:_digest(ledger[name]) for name in missing}))
            admission_name = f'attempt-{attempt:06d}-admission.json'
            _write_new(meta/admission_name, admission)
            metadata_hashes[admission_name] = _hash(meta/admission_name)
            admission_sha = _digest(admission)
            for name in missing:
                invalidated[name] = dict(previous_record_sha256=_digest(ledger[name]),
                                        origin_attempt=attempt, admission_sha256=admission_sha)
            for name, target in temporary_objects.items():
                path = _relative(binary, name)
                record = dict(path=name, target=target, **_hash(path))
                path.unlink()
                removed_temporaries.append(record)
            for output in pending + owned_links:
                path = _relative(binary, output)
                if path.exists():
                    path.unlink()
                    removed.append(output)
            for offset in range(0, len(pending), _CHUNK):
                unchanged()
                chunk = pending[offset:offset+_CHUNK]
                command = [str(context['tools']['ninja']), '-C', str(binary), '-j', '2', '--', *chunk]
                runner(command)
                unchanged()
                dependencies = _dependency_inventory(context, binary, chunk)
                objects, operations = {}, {}
                for output in chunk:
                    objects[output] = dict(artifact=_hash(_relative(binary, output)),
                                           dependencies=dependencies[output])
                    if output in invalidated:
                        operations[output] = dict(kind='rebuild-missing',
                            previous_record_sha256=invalidated[output]['previous_record_sha256'],
                            origin_attempt=invalidated[output]['origin_attempt'])
                    else:
                        _require(output not in ledger, 'refusing an unadmitted sealed-object overwrite')
                        operations[output] = dict(kind='new', previous_record_sha256=None, origin_attempt=None)
                sequence += 1
                checkpoint = _sealed(dict(schema=2, kind=_CHECKPOINT_KIND, sequence=sequence, attempt=attempt,
                    contract_sha256=contract_sha, previous_sha256=previous, admission_sha256=admission_sha,
                    objects=objects, operations=operations))
                _write_new(meta/f'checkpoint-{sequence:06d}.json', checkpoint)
                metadata_hashes[f'checkpoint-{sequence:06d}.json'] = _hash(meta/f'checkpoint-{sequence:06d}.json')
                ledger.update(objects)
                for output in objects:
                    invalidated.pop(output, None)
                previous = _digest(checkpoint)
            _require(not invalidated and set(ledger) == set(graph['objects']),
                     'final build lacks a complete committed object ledger')
            unchanged()
            # Unsealed archives/executable/DLLs must never survive into final link.
            for output in _package_outputs(context, binary, graph):
                path = _relative(binary, output)
                if path.exists():
                    path.unlink()
            receipt = api._compile_configured(project, root,
                allow_revision_override=options['allow_revision_override'], desktop=options['desktop'],
                commands=commands.copy(), cache_context=context, runner=runner)
            unchanged()
            audit = build_inputs.verify_closure(context, binary)
            dependencies = _dependency_inventory(context, binary, list(ledger))
            for output, record in ledger.items():
                _require(_hash(_relative(binary, output)) == record['artifact'] and
                         _same(dependencies[output], record['dependencies']),
                         'object changed during final build: ' + output)
            _package_outputs(context, binary, graph, verify=True)
            unchanged()
            receipt['commands'] = commands
            receipt['recovery'] = dict(schema=1, resumed=resume, attempt=attempt,
                contract_sha256=contract_sha, configured_sha256=_digest(seal),
                checkpoint_sha256=previous, checkpoint_sequence=sequence,
                checkpoint_format=_CHECKPOINT_KIND,
                verified_retained_objects=retained,
                missing_sealed_objects_rebuilt=sorted(set(missing)|set(continued_rebuilds)),
                continued_unsealed_rebuild_objects=continued_rebuilds,
                recompiled_unsealed_objects=pending, removed_unsealed_outputs=removed,
                removed_temporary_objects=removed_temporaries,
                input_contract=pre, configured=seal, input_audit=audit,
                scope='Verified compiled-artifact continuation; no guest execution evidence')
            receipt['execution_evidence'] = False
            # The ordinary receipt hashes precede several independent audits.
            # Bind publication to the package bytes present at this boundary.
            package = binary/'bin'
            actual_package = {path.name:_hash(path)['sha256'] for path in sorted(package.iterdir())}
            _require(_same(actual_package, receipt.get('output_files')) and
                     receipt.get('binary_sha256') == actual_package.get('pce-consumer.exe') and
                     receipt.get('binary') == str(package/'pce-consumer.exe'),
                     'final binary/package differs from the compilation receipt')
            _write_new(root/'build-receipt.json', receipt)
            _write_new(meta/f'attempt-{attempt:06d}-result.json',
                _sealed(dict(schema=1, attempt=attempt, status='complete', contract_sha256=contract_sha,
                     receipt_sha256=_hash(root/'build-receipt.json')['sha256'], commands=commands)))
            return receipt
        except BaseException as error:
            build_process.quiesce(root)
            if attempt is not None:
                _write_new(meta/f'attempt-{attempt:06d}-result.json',
                    _sealed(dict(schema=1, attempt=attempt, status='failed',
                         contract_sha256=contract_sha,
                         error_type=type(error).__name__, error=str(error), commands=commands)))
            raise
