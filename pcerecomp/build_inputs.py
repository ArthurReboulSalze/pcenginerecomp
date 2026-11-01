"""Conservative input closure for the opt-in Windows LLVM-MinGW package cache.

Ordinary CMake builds remain independent of this producer. Every declared SDK,
toolchain and module tree is content hashed. Every request freshly configures;
hits skip consumer compilation and linking.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import stat
import struct
import subprocess
from concurrent.futures import ThreadPoolExecutor

from .abi import ABI


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def tree_identity(path: Path) -> dict:
    root = Path(path).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError('Cache input requires a specific toolchain, SDK or module directory')
    digest, count = hashlib.sha256(), 0
    paths = sorted(root.rglob('*'), key=lambda item: item.relative_to(root).as_posix())
    def record(item):
        before = item.lstat()
        if _linked(before):
            raise ValueError('Cache inputs cannot contain symbolic links or reparse points')
        name = item.relative_to(root).as_posix().encode('utf-8')
        if stat.S_ISDIR(before.st_mode):
            return b'd\0'+name+b'\0', 0
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Cache inputs must be regular files and directories')
        content = hashlib.sha256()
        with item.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise ValueError('Cache input changed before hashing')
            for block in iter(lambda: stream.read(1024*1024), b''):
                content.update(block)
            after = os.fstat(stream.fileno())
        current = item.lstat()
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if signature(before) != signature(after) or signature(before) != signature(current):
            raise ValueError('Cache input changed while hashing')
        return b'f\0'+name+b'\0'+str(before.st_size).encode()+b'\0'+content.digest(), 1
    if len(paths) > 128:
        # Independent reads run concurrently; map retains the canonical order.
        with ThreadPoolExecutor(max_workers=8) as pool:
            for encoded, files in pool.map(record, paths):
                digest.update(encoded);count += files
    else:
        for encoded, files in map(record, paths):
            digest.update(encoded);count += files
    if [p.relative_to(root).as_posix() for p in paths] != [
            p.relative_to(root).as_posix() for p in sorted(root.rglob('*'), key=lambda p: p.relative_to(root).as_posix())]:
        raise ValueError('Cache input directory changed while hashing')
    return dict(path=str(root), sha256=digest.hexdigest(), files=count)


def prepare(project, *, generator, desktop, cmake_args, toolchain_root, dependency_roots,
            build_dir, cache_root=None):
    """Return a content contract, controlled environment and audited roots."""
    if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64') or struct.calcsize('P') != 8:
        raise ValueError('Verified package-cache producer currently requires Windows x64 LLVM-MinGW')
    if generator != 'Ninja' or toolchain_root is None:
        raise ValueError('Package cache requires Ninja and an explicit toolchain root')
    external = ('CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','CPLUS_INCLUDE_PATH',
        'C_INCLUDE_PATH','LIBRARY_PATH','INCLUDE','LIB','LIBPATH','SDKROOT',
        'CMAKE_PREFIX_PATH','CMAKE_TOOLCHAIN_FILE','CMAKE_PROJECT_TOP_LEVEL_INCLUDES',
        'CMAKE_GENERATOR_PLATFORM','CMAKE_GENERATOR_TOOLSET')
    if any(os.environ.get(name) for name in external):
        raise ValueError('Cache profile refuses ambient compiler flags and external build search paths')
    options = {}
    for argument in cmake_args:
        key, value = argument[2:].split('=', 1)
        if key in options:
            raise ValueError('Duplicate cache CMake option')
        options[key] = value
    if set(options) - {'CMAKE_CXX_COMPILER', 'CMAKE_MAKE_PROGRAM', 'SDL3_DIR'}:
        raise ValueError('Cache cannot infer external CMake toolchain-file dependencies')
    if not {'CMAKE_CXX_COMPILER', 'CMAKE_MAKE_PROGRAM'} <= options.keys():
        raise ValueError('Cache requires explicit compiler and Ninja paths')
    bundle = Path(toolchain_root).resolve(strict=True)
    tools = dict(compiler=Path(options['CMAKE_CXX_COMPILER']).resolve(strict=True),
                 ninja=Path(options['CMAKE_MAKE_PROGRAM']).resolve(strict=True),
                 cmake=Path(shutil.which('cmake') or '').resolve(strict=True))
    for name, filename in (('compiler', 'clang++.exe'), ('ninja', 'ninja.exe'), ('cmake', 'cmake.exe')):
        if tools[name].name.lower() != filename or tools[name].parent != bundle/'bin' or not tools[name].is_file():
            raise ValueError('Cache tools must be the declared LLVM-MinGW bundle binaries')
    for folder in ('include', 'lib', 'x86_64-w64-mingw32/include', 'x86_64-w64-mingw32/lib'):
        if not (bundle/folder).is_dir():
            raise ValueError('Incomplete LLVM-MinGW toolchain bundle')
    roots = [Path(path).resolve(strict=True) for path in dependency_roots]
    if len(roots) > 16 or len(set(roots)) != len(roots):
        raise ValueError('Cache requires at most 16 distinct explicit SDK roots')
    if desktop:
        if 'SDL3_DIR' not in options:
            raise ValueError('Desktop cache requires explicit SDL3_DIR and its SDK root')
        sdl = Path(options['SDL3_DIR']).resolve(strict=True)
        if not (sdl/'SDL3Config.cmake').is_file() or not any(sdl.is_relative_to(root) for root in [bundle, *roots]):
            raise ValueError('Selected SDL package must be within a declared hashed SDK')
    elif 'SDL3_DIR' in options:
        raise ValueError('Headless cache does not accept an unused SDL package')
    module_root = project['files']['module_source'].parent.resolve()
    tool_root = project['tool_root'].resolve()
    compile_roots = [tool_root/'runtime', tool_root/'cmake']
    hashed_roots = [bundle, *roots, module_root, *compile_roots]
    outputs = [Path(build_dir).resolve()]
    if cache_root is not None:
        outputs.append(Path(cache_root).resolve())
    for output in outputs:
        if any(output.is_relative_to(root) or root.is_relative_to(output) for root in hashed_roots):
            raise ValueError('Cache/build outputs must be separate from hashed input trees')
    system = Path(os.environ['SystemRoot']).resolve(strict=True)
    environment = {name: os.environ[name] for name in ('SystemRoot', 'SystemDrive', 'ComSpec',
        'TEMP', 'TMP', 'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS') if name in os.environ}
    environment['PATH'] = os.pathsep.join(map(str, (bundle/'bin', system/'System32', system)))
    identities = dict(toolchain=tree_identity(bundle), module=tree_identity(module_root),
                      dependencies=[tree_identity(root) for root in roots],
                      tool_compile=[tree_identity(root) for root in compile_roots])
    contract = dict(schema=1, producer='windows-x64-llvm-mingw-ninja-v1',
        tool=dict(path=str(project['tool_root']), source_sha256=project['tool_identity']['source_sha256'],
                  runtime_abi=ABI), module_inputs={key:value for key,value in project['identities'].items()
                                               if key.startswith('module_')},
        trees=identities, desktop=desktop, configuration='Release', generator=generator,
        options=options, target='x86_64-w64-windows-gnu',
        host=dict(system=str(system), machine=platform.machine(), version=platform.version()),
        environment_policy='minimal-windows-toolchain-v1')
    return dict(contract=contract, environment=environment, tools=tools,
                roots=hashed_roots, tool_root=project['tool_root'].resolve())


def _audit_paths(context, build_dir):
    roots = context['roots']
    def allowed(value):
        path = Path(value)
        path = (build_dir/path).resolve() if not path.is_absolute() else path.resolve()
        if any(path.is_relative_to(root) for root in roots):
            return path
        raise ValueError('Compiled dependency is outside hashed cache inputs: '+str(path))
    return allowed


def _flags(fragment):
    # This first producer supports the toolkit's ordinary Release flags. Reject
    # response/config/plugin/script inputs rather than guessing their closure.
    safe = r'-(?:O[0-3szg]|D[A-Za-z_][A-Za-z0-9_]*(?:=.*)?|std=(?:c|gnu)\+\+\d+|W(?:all|extra|pedantic|error(?:=[A-Za-z0-9_-]+)?|no-[A-Za-z0-9_-]+)|ffp-contract=(?:off|on|fast)|fno-exceptions|fno-rtti|static-libgcc|static-libstdc\+\+|mwindows|mconsole|pthread)'
    for token in shlex.split(fragment, posix=False):
        if not re.fullmatch(safe, token):
            raise ValueError('Unsupported cached compile/link flag dependency: '+token)


def configuration_identity(context, build_dir: Path) -> dict:
    """Audit a freshly configured, trusted toolkit/SDL graph before cache lookup.

    This is deliberately not a sandbox for arbitrary third-party CMake code.
    Fresh configuration captures file(READ)-derived options; only the known
    target graph, pinned sources and ordinary Release flags are supported.
    """
    env, tools = context['environment'], context['tools']
    target = subprocess.run([str(tools['compiler']), '-dumpmachine'], env=env,
                            capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if target != context['contract']['target']:
        raise ValueError('Cache compiler target differs from verified producer')
    build_dir = Path(build_dir).resolve()
    allowed = _audit_paths(context, build_dir)
    wrapper = build_dir.parent/'source'
    def normalized(text):
        # CMake emits native, POSIX and Ninja-escaped spellings of these roots.
        for path, marker in ((build_dir, '<BUILD>'), (wrapper, '<WRAPPER>')):
            for spelling in (str(path), path.as_posix(), path.as_posix().replace(':', '$:')):
                text = text.replace(spelling, marker)
        return text
    def fingerprint(path, *, normalize=False):
        data = path.read_bytes()
        if normalize:
            data = normalized(data.decode('utf-8')).encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    reply = build_dir/'.cmake/api/v1/reply'
    indices = sorted(reply.glob('index-*.json'))
    if not indices:
        raise ValueError('Missing CMake File API cache input audit')
    index = json.loads(indices[-1].read_text(encoding='utf-8'))
    objects = index['reply']
    toolchains = json.loads((reply/objects['toolchains-v1']['jsonFile']).read_text(encoding='utf-8'))
    for toolchain in toolchains['toolchains']:
        language, compiler = toolchain['language'], toolchain['compiler']
        if language not in ('CXX', 'RC') or (language == 'CXX' and compiler.get('id') != 'Clang'):
            raise ValueError('Unsupported cached compiler')
        allowed(compiler['path'])
        if language == 'CXX' and Path(compiler['path']).resolve() != tools['compiler']:
            raise ValueError('Actual cached compiler differs from explicit selection')
        for key in ('includeDirectories', 'linkDirectories'):
            for path in toolchain['compiler'].get('implicit', {}).get(key, []):
                allowed(path)
    cmake_files = json.loads((reply/objects['cmakeFiles-v1']['jsonFile']).read_text(encoding='utf-8'))
    configure_inputs = []
    for item in cmake_files['inputs']:
        path = Path(item['path'])
        if not path.is_absolute():
            path = wrapper/path
        path = path.resolve()
        if path == (wrapper/'CMakeLists.txt').resolve():
            pass
        elif item.get('isGenerated') and path.is_relative_to(build_dir/'CMakeFiles'):
            pass
        elif path == context['tool_root']/'CMakeLists.txt':
            pass  # Included in canonical toolkit source identity.
        else:
            allowed(path)
        if not path.is_file() or _linked(path.lstat()):
            raise ValueError('Missing or linked CMake configuration input')
        configure_inputs.append(dict(path=normalized(str(path)), sha256=fingerprint(path, normalize=True)))
    model = json.loads((reply/objects['codemodel-v2']['jsonFile']).read_text(encoding='utf-8'))
    if len(model['configurations']) != 1 or model['configurations'][0]['name'] != 'Release':
        raise ValueError('Cache requires exactly the Release configuration')
    targets = [json.loads((reply/entry['jsonFile']).read_text(encoding='utf-8'))
               for entry in model['configurations'][0]['targets']]
    expected = {'pce-consumer':'EXECUTABLE', 'pce-runtime':'STATIC_LIBRARY'}
    if context['contract']['desktop']:
        expected['pce-desktop-host'] = 'STATIC_LIBRARY'
    names = [target['name'] for target in targets]
    modules = [name for name in names if re.fullmatch(r'pce-module-[0-9a-f]{64}', name)]
    if len(modules) != 1:
        raise ValueError('Unsupported cached native module target graph')
    expected[modules[0]] = 'OBJECT_LIBRARY'
    if len(names) != len(expected) or set(names) != set(expected):
        raise ValueError('Unsupported cached target graph')
    artifacts = set()
    for data in targets:
        if data['type'] != expected[data['name']]:
            raise ValueError('Unsupported cached target type')
        for item in data.get('artifacts', []):
            path = (build_dir/item['path']).resolve()
            if not path.is_relative_to(build_dir):
                raise ValueError('Cached artifact is outside build directory')
            artifacts.add(path)
    inputs, target_model = set(), []
    for data in sorted(targets, key=lambda item:item['name']):
            sources = []
            for source in data.get('sources', []):
                path = Path(source['path'])
                path = (wrapper/path).resolve() if not path.is_absolute() else path.resolve()
                if source.get('isGenerated'):
                    if 'compileGroupIndex' in source or path not in artifacts or path.suffix != '.obj':
                        raise ValueError('Generated compile inputs are unsupported by cache')
                else:
                    allowed(path)
                sources.append(normalized(str(path)))
            for group in data.get('compileGroups', []):
                if group['language'] != 'CXX':
                    raise ValueError('Unsupported cached compile language')
                for include in group.get('includes', []):
                    inputs.add(str(allowed(include['path'])))
                for fragment in group.get('compileCommandFragments', []):
                    _flags(fragment['fragment'])
            for fragment in data.get('link', {}).get('commandFragments', []):
                if fragment['role'] == 'flags':
                    _flags(fragment['fragment'])
                    continue
                if fragment['role'] not in ('libraries', 'libraryPath'):
                    raise ValueError('Unsupported cached link fragment')
                for token in shlex.split(fragment['fragment'], posix=False):
                    text = token.strip('"')
                    if re.fullmatch(r'-l[A-Za-z0-9_+.-]+', text):
                        continue
                    if text.startswith('-L'):
                        text = text[2:].strip('"')
                    path = Path(text)
                    path = (build_dir/path).resolve() if not path.is_absolute() else path.resolve()
                    if path not in artifacts:
                        allowed(path)
                    inputs.add(normalized(str(path)))
            target_model.append(dict(name=data['name'], type=data['type'], sources=sources,
                compile_groups=data.get('compileGroups', []), link=data.get('link', {})))
    sdl = None
    if context['contract']['desktop']:
        path = allowed((build_dir/'cache-sdl-runtime.txt').read_text(encoding='utf-8').strip())
        if not path.is_file() or path.suffix.lower() != '.dll' or _linked(path.lstat()):
            raise ValueError('Desktop runtime must be an actual hashed SDK DLL')
        sdl = dict(path=str(path), sha256=fingerprint(path))
    graphs = {}
    for name in ('build.ninja', 'CMakeFiles/rules.ninja'):
        text = (build_dir/name).read_text(encoding='utf-8')
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(('include ', 'subninja ')) and stripped != 'include CMakeFiles/rules.ninja':
                raise ValueError('External Ninja graph inputs are unsupported by cache')
            if re.match(r'(?:LAUNCHER|CODE_CHECK)\s*=', stripped) and stripped.split('=',1)[1].strip():
                raise ValueError('Compiler launchers and code-check commands are unsupported by cache')
        if name == 'build.ninja':
            for line in text.splitlines():
                if line.startswith('build ') and ': CUSTOM_COMMAND' in line:
                    output = line[6:].split(': CUSTOM_COMMAND', 1)[0]
                    if not re.fullmatch(r'(?:tool/)?CMakeFiles/(?:edit_cache|rebuild_cache)\.util', output):
                        raise ValueError('Custom generated inputs are unsupported by cache')
                if line.strip().startswith(('PRE_LINK =', 'PRE_BUILD =')) and line.split('=',1)[1].strip() != 'cd .':
                    raise ValueError('Custom pre-build commands are unsupported by cache')
                if line.strip().startswith('POST_BUILD ='):
                    command = line.split('=',1)[1].strip()
                    if command != 'cd .' and (command.count('&&') != 1 or '|' in command or '>' in command
                            or not command.endswith('PCERuntimeDependencies.cmake"')):
                        raise ValueError('Custom post-build commands are unsupported by cache')
                    if command != 'cd .':
                        prefix, invocation = command.split('&&')
                        prefix_parts = prefix.strip().split(' /C "cd /D ')
                        shell = Path(context['environment']['SystemRoot'])/'System32/cmd.exe'
                        if len(prefix_parts) != 2 or Path(prefix_parts[0]).resolve() != shell.resolve() or prefix_parts[-1].strip('" ') != str(build_dir):
                            raise ValueError('Unsupported cache post-build working directory')
                        tokens = [token.strip('"') for token in shlex.split(invocation.strip()[:-1], posix=False)]
                        if not tokens or Path(tokens[0]).resolve() != tools['cmake']:
                            raise ValueError('Unsupported cache post-build command')
                        parameters = {}
                        for token in tokens[1:-2]:
                            if not token.startswith('-D') or '=' not in token:
                                raise ValueError('Unsupported cache post-build argument')
                            key, value = token[2:].split('=',1)
                            if key in parameters:
                                raise ValueError('Duplicate cache post-build argument')
                            parameters[key] = value
                        required = {'PCE_EXECUTABLE', 'PCE_ANALYSIS_DIR', 'PCE_COMPILER_DIRECTORY',
                            'PCE_LINK_DIRECTORIES', 'PCE_SDL_RUNTIME', 'PCE_DEPENDENCY_TOOL', 'PCE_DEPENDENCY_COMMAND'}
                        if set(parameters) != required or tokens[-2] != '-P' or Path(tokens[-1]).resolve() != context['tool_root']/'cmake/PCERuntimeDependencies.cmake':
                            raise ValueError('Unsupported cache dependency-copy script')
                        if Path(parameters['PCE_EXECUTABLE']).resolve() != build_dir/'bin/pce-consumer.exe' or Path(parameters['PCE_ANALYSIS_DIR']).resolve() != build_dir/'CMakeFiles/pce-consumer-runtime-Release':
                            raise ValueError('Unsupported cache package output')
                        if Path(parameters['PCE_COMPILER_DIRECTORY']).resolve() != tools['compiler'].parent or parameters['PCE_DEPENDENCY_TOOL'] != 'objdump':
                            raise ValueError('Unsupported cache dependency observer')
                        allowed(parameters['PCE_DEPENDENCY_COMMAND'])
                        for directory in parameters['PCE_LINK_DIRECTORIES'].split(';'):
                            allowed(directory)
                        if parameters['PCE_SDL_RUNTIME'] != (sdl['path'].replace('\\','/') if sdl else ''):
                            raise ValueError('Cache post-build SDL runtime differs from selected SDK')
        canonical = '\n'.join(line.rstrip() for line in normalized(text).splitlines()
                              if line.strip() and not line.lstrip().startswith('#'))
        graphs[name] = hashlib.sha256(canonical.encode()).hexdigest()
    # Backtrace indices/files are retained: source roots are fixed, while only
    # newly generated wrapper/build paths are normalized.
    def normalize_model(value):
        if isinstance(value, str):
            return normalized(value)
        if isinstance(value, list):
            return [normalize_model(item) for item in value]
        if isinstance(value, dict):
            return {key:normalize_model(item) for key,item in value.items()}
        return value
    actual_model = normalize_model(target_model)
    return dict(schema=1, target=target, configure_inputs=sorted(configure_inputs,key=lambda item:item['path']),
        targets=actual_model, toolchains=toolchains, ninja=graphs, sdl_runtime=sdl,
        dependency_count=len(inputs), policy='trusted-toolkit-sdl-release-v1')


def verify_closure(context, build_dir: Path) -> dict:
    """Recheck configuration and actual cold-build headers before publish."""
    build_dir = Path(build_dir).resolve()
    configuration = configuration_identity(context, build_dir)
    allowed = _audit_paths(context, build_dir)
    deps = subprocess.run([str(context['tools']['ninja']), '-C', str(build_dir), '-t', 'deps'],
        env=context['environment'], capture_output=True, text=True, check=True, timeout=30).stdout
    headers = {str(allowed(line.strip())) for line in deps.splitlines() if line.startswith('    ')}
    if not headers:
        raise ValueError('Missing actual compiler dependency closure')
    return dict(schema=1, target=configuration['target'], header_count=len(headers),
        dependency_count=configuration['dependency_count']+len(headers), configuration=configuration,
        cmake_file_api=True, ninja_dependencies=True)
