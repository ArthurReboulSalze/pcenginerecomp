"""Versioned consumer contract, checked builds and bounded execution receipts.

No installation, dependency download or implicit media/save discovery.
All descriptor paths are relative to the descriptor, never the caller's cwd.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

from .abi import ABI
MAX_WALL_SECONDS = 86400
MAX_MODULE_MANIFEST_BYTES = 64 * 1024 * 1024
SOURCE_DIRS = ("pcerecomp", "runtime", "cmake")
ASSETS = {"bios", "bram", "toc", "disc", "libchdr", "input_script", "cartridge"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_identity(root: Path) -> dict:
    """Hash exact relevant source bytes, including untracked relevant files.

    Canonical encoding: sorted UTF-8 relative POSIX paths, NUL, ASCII decimal
    byte count, NUL, exact file bytes. Caches, docs and tests are not code inputs.
    """
    root = root.resolve()
    paths = [root / "CMakeLists.txt"]
    for directory in SOURCE_DIRS:
        base = root / directory
        if not base.is_dir():
            raise ValueError(f"Missing tool source directory: {directory}")
        paths.extend(p for p in base.rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts
                     and p.suffix in {".py", ".cpp", ".hpp", ".h", ".cmake"})
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        name = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(name + b"\0" + str(path.stat().st_size).encode() + b"\0")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=False)
    revision = None
    if top.returncode == 0 and Path(top.stdout.strip()).resolve() == root:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=False)
        if result.returncode == 0:
            revision = result.stdout.strip()
    return {"revision": revision, "source_sha256": digest.hexdigest(),
            "source_files": len(paths)}


def _table(value, required, optional=(), name="table"):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"Invalid {name} fields; required {sorted(required)}, optional {sorted(optional)}")
    return value


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be {low}..{high}")
    return value


def _digest(value, name):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _choice(value, values, name):
    if value not in values:
        raise ValueError(f"{name} must be one of {values}")


def _file(base, entry, name):
    _table(entry, {"path", "sha256"}, name=name)
    if not isinstance(entry["path"], str) or not entry["path"]:
        raise ValueError(f"Invalid {name} path")
    path = (base / entry["path"]).resolve()
    expected = _digest(entry["sha256"], name)
    if not path.is_file() or sha256(path) != expected:
        raise ValueError(f"{name} SHA256 mismatch or missing file")
    return path


def _module_artifacts(files, manifest):
    """Pin all authored/generated code inputs of a multi-unit module.

    Legacy manifests without either list still describe one source. Once a
    list is present, both lists are required, even for a single translation
    unit with no generated headers. Names are portable direct children of the
    manifest directory; a manifest never authorizes arbitrary extra paths.
    """
    if not ({"translation_units", "generated_headers"} & manifest.keys()):
        return
    base = files["module_manifest"].parent
    seen, units = set(), []
    for field, suffix, minimum, maximum, prefix in (
            ("translation_units", ".cpp", 1, 65537, "module_unit"),
            ("generated_headers", ".hpp", 0, 256, "module_header")):
        entries = manifest.get(field)
        if not isinstance(entries, list) or not minimum <= len(entries) <= maximum:
            raise ValueError(f"Module {field} requires {minimum}..{maximum} artifact entries")
        for entry in entries:
            _table(entry, {"file", "sha256"}, name=f"Module {field} artifact")
            name = entry["file"]
            if (not isinstance(name, str) or not 1 <= len(name) <= 128
                    or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) is None
                    or not name.endswith(suffix)
                    or name.split(".", 1)[0].upper() in {
                        "CON", "PRN", "AUX", "NUL",
                        *(f"COM{i}" for i in range(1, 10)),
                        *(f"LPT{i}" for i in range(1, 10))}):
                raise ValueError(f"Module {field} requires portable {suffix} basenames")
            if name.casefold() in seen:
                raise ValueError("Duplicate module artifact basename (case-insensitive)")
            seen.add(name.casefold())
            artifact = base / name
            path = artifact.resolve()
            if artifact.is_symlink() or path.parent != base:
                raise ValueError("Module artifact must remain in manifest directory and cannot be a symlink")
            expected = _digest(entry["sha256"], f"Module artifact {name}")
            if not path.is_file() or sha256(path) != expected:
                raise ValueError(f"Module artifact {name} SHA256 mismatch or missing file")
            files[f"{prefix}:{name}"] = path
            if field == "translation_units":
                units.append(path)
    if files["module_source"] not in units:
        raise ValueError("Module translation_units must include module source entry")


def _module_manifest(path):
    """Read one bounded manifest without ambiguous JSON fields or numbers."""
    if path.stat().st_size > MAX_MODULE_MANIFEST_BYTES:
        raise ValueError('Module manifest exceeds 64 MiB')
    with path.open('rb') as stream:
        raw = stream.read(MAX_MODULE_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MODULE_MANIFEST_BYTES:
        raise ValueError('Module manifest exceeds 64 MiB')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in module manifest')
            result[key] = value
        return result
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite number in module manifest')
        return result
    def no_constant(value):
        raise ValueError('Nonfinite number in module manifest')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_float=finite_float,
                          parse_constant=no_constant)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid module manifest JSON encoding or nesting') from error


def _module_observation_profile(base, entry, files, manifest):
    """Bind original profile provenance and selection facts, without code emission.

    Code artifact hashes remain the existing module contract. These checks do
    not authenticate original execution or claim to re-prove generated code.
    """
    from .capture import U64
    from .emitter import NATIVE
    from .observations import MAX_PROFILE_BYTES, load_observation_profile_details

    _table(entry, {'path', 'sha256'}, name='module.observation_profile')
    if not isinstance(entry['path'], str) or not entry['path']:
        raise ValueError('Invalid module.observation_profile path')
    path = (base / entry['path']).resolve()
    expected_digest = _digest(entry['sha256'], 'module.observation_profile')
    if not path.is_file():
        raise ValueError('module.observation_profile SHA256 mismatch or missing file')
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise ValueError('Observation profile exceeds 128 MiB')
    profile, digest, instructions, provenance = load_observation_profile_details(path)
    if digest != expected_digest:
        raise ValueError('module.observation_profile SHA256 mismatch or changed during verification')
    if (manifest.get('execution_evidence') is not False
            or any(key.startswith(('capture_', 'captured_')) for key in manifest)
            or {'code_capture_sha256', 'checkpoint_origin', 'execution_window'} & manifest.keys()):
        raise ValueError('Bound observation profile cannot declare capture execution evidence')

    def exact(key, expected):
        # Serialized equality preserves strict nested numeric types, unlike ==.
        actual = json.dumps(manifest.get(key), sort_keys=True, separators=(',', ':'), allow_nan=False)
        wanted = json.dumps(expected, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if actual != wanted:
            raise ValueError('Module observation profile disagrees with '+key)

    for key, value in {
        'observation_profile_sha256': digest,
        'observation_profile_format': profile['format'],
        'observation_profile_schema': profile['schema'],
        'observation_inputs': provenance,
        'historical_totals': profile['historical_totals'],
        'historical_count_policy': 'sum of distinct raw inputs; overlapping execution windows are not deduplicated',
    }.items():
        exact(key, value)
    spans = manifest.get('excluded_physical_ranges')
    if not isinstance(spans, list) or len(spans) > 256:
        raise ValueError('Module profile exclusions require at most 256 ranges')
    exclusions = []
    for span in spans:
        _table(span, {'start', 'length'}, name='module profile exclusion')
        start = _integer(span['start'], 0, 0x1fffff, 'excluded physical start')
        length = _integer(span['length'], 1, 0x200000-start, 'excluded physical length')
        exclusions.append((start, length))
    if exclusions != sorted(set(exclusions)):
        raise ValueError('Module profile exclusions require canonical sorted unique ranges')
    selected, excluded = [], []
    for ins in instructions:
        remove = any(start <= address < start+length
                     for address in ins['physical'] for start, length in exclusions)
        (excluded if remove else selected).append(ins)
    native = [ins for ins in selected if ins['data'][0] in NATIVE]
    counts = {
        'observed_instructions': len(instructions),
        'native_instructions_emitted': len(native),
        'native_contexts': len({ins['mpr'] for ins in native}),
        'excluded_observations': len(excluded),
        'excluded_retired_hits': sum(ins['native_hits']+ins['interpreted_hits'] for ins in excluded),
        'unsupported_observations': len(selected)-len(native),
    }
    for key, value in counts.items():
        _integer(manifest.get(key), 0, U64, 'module profile '+key)
        exact(key, value)
    files['module_observation_profile'] = path


def verify(descriptor: Path, *, allow_revision_override=False) -> dict:
    descriptor = descriptor.resolve()
    config = tomllib.loads(descriptor.read_text(encoding="utf-8"))
    _table(config, {"schema", "name", "tool", "module", "runtime", "limits"}, ASSETS | {"payload", "boot"}, "project")
    if ("boot" in config) == ("payload" in config):
        raise ValueError("Exactly one of payload or reset boot is required")
    reset_boot = "boot" in config
    hucard_boot = False
    if reset_boot:
        from .cartridge import HEADERS, ENCODINGS, PROFILES
        candidate = config['boot']
        hucard_boot = isinstance(candidate, dict) and candidate.get('mode') == 'hucard-reset'
        if hucard_boot:
            boot = _table(candidate, {'mode', 'profile', 'header', 'encoding'}, name='boot')
            _choice(boot['profile'], PROFILES, 'boot.profile')
            _choice(boot['header'], HEADERS, 'boot.header')
            _choice(boot['encoding'], ENCODINGS, 'boot.encoding')
            if 'cartridge' not in config or {'bios', 'bram', 'toc', 'disc', 'libchdr'} & config.keys():
                raise ValueError('HuCard boot requires cartridge and excludes CD/BIOS/BRAM assets')
        else:
            boot = _table(candidate, {"mode", "profile"}, optional={"arcade_card"}, name="boot")
            _choice(boot["mode"], ("system-card-reset",), "boot.mode")
            _choice(boot["profile"], ("standard", "super"), "boot.profile")
            if "arcade_card" in boot:
                _choice(boot["arcade_card"], ("duo",), "boot.arcade_card")
                if boot["profile"] != "super":
                    raise ValueError("Arcade Card Duo requires Super System Card reset boot")
            if "bios" not in config:
                raise ValueError("System Card reset boot requires hashed bios")
    if not hucard_boot and 'cartridge' in config:
        raise ValueError('Cartridge requires an explicit HuCard reset recipe')
    if type(config["schema"]) is not int or config["schema"] != 1:
        raise ValueError("Expected consumer schema = 1")
    if not isinstance(config["name"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", config["name"]):
        raise ValueError("Invalid consumer name")
    base = descriptor.parent
    tool = _table(config["tool"], {"path", "revision", "source_sha256", "runtime_abi"}, name="tool")
    if not isinstance(tool["path"], str) or not tool["path"]:
        raise ValueError("Invalid tool path")
    if not isinstance(tool["revision"], str) or re.fullmatch("[0-9a-f]{40}", tool["revision"]) is None:
        raise ValueError("tool.revision must be a complete Git commit")
    if type(tool["runtime_abi"]) is not int or tool["runtime_abi"] != ABI:
        raise ValueError("Unsupported runtime ABI")
    tool_root = (base / tool["path"]).resolve()
    identity = source_identity(tool_root)
    if identity["source_sha256"] != _digest(tool["source_sha256"], "tool.source_sha256"):
        raise ValueError("Tool source digest mismatch (including dirty or untracked source)")
    if identity["revision"] != tool["revision"] and not allow_revision_override:
        raise ValueError("Tool revision mismatch/unavailable; explicit --allow-revision-override still requires exact source digest")
    header = (tool_root / "runtime/include/pce/runtime.hpp").read_text(encoding="utf-8")
    if re.search(rf"\babi_version\s*=\s*{ABI}\s*;", header) is None:
        raise ValueError("Tool source ABI mismatch")
    module = _table(config["module"], {"source", "manifest"}, {'observation_profile'}, name="module")
    files = {"module_source": _file(base, module["source"], "module.source"),
             "module_manifest": _file(base, module["manifest"], "module.manifest")}
    manifest = _module_manifest(files['module_manifest'])
    if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int or manifest["schema"] != 1
            or type(manifest.get("runtime_abi")) is not int or manifest["runtime_abi"] != ABI):
        raise ValueError("Module schema/runtime ABI mismatch")
    _integer(manifest.get("native_instructions_emitted"), 1, 1000000, "native_instructions_emitted")
    _module_artifacts(files, manifest)
    if 'observation_profile' in module:
        _module_observation_profile(base, module['observation_profile'], files, manifest)
    if 'native_span' in manifest:
        span = _table(manifest['native_span'], {'schema', 'protocol'}, name='module.native_span')
        if (type(span['schema']) is not int or span['schema'] != 1
                or span['protocol'] != 'per_instruction_v1'
                or manifest.get('partition_layout') != 'stable'
                or manifest.get('partition_identity') != 'full_mpr_logical_pc_range_v1'
                or type(manifest.get('pc_bucket_size')) is not int or manifest['pc_bucket_size'] != 256):
            raise ValueError('Unsupported native span module contract')
    if not reset_boot:
        payload = _table(config["payload"], {"path", "sha256", "physical_load", "pc", "mpr"}, name="payload")
        files["payload"] = _file(base, {k: payload[k] for k in ("path", "sha256")}, "payload")
        load = _integer(payload["physical_load"], 0, 0x1fffff, "physical_load")
        _integer(payload["pc"], 0, 65535, "pc")
        if not isinstance(payload["mpr"], list) or len(payload["mpr"]) != 8:
            raise ValueError("mpr requires all eight bytes")
        for item in payload["mpr"]:
            _integer(item, 0, 255, "mpr byte")
        size = files["payload"].stat().st_size
        if not size or load + size > 0x200000 or any(bank not in {*range(0x80, 0x88), 0xf8}
                for bank in range(load >> 13, ((load + size - 1) >> 13) + 1)):
            raise ValueError("Payload must fit standard CD/work RAM")
    runtime = _table(config["runtime"], {"tier", "video", "cd_unknown_status", "joypad", "region", "multitap"}, optional={"audio", "audio_profile", "audio_rate", "audio_timing", "vdc_access", "native_span", "cd_timing"}, name="runtime")
    if 'native_span' in runtime:
        _integer(runtime['native_span'], 1, 256, 'native_span')
        if runtime['native_span'] > 1 and 'native_span' not in manifest:
            raise ValueError('native_span > 1 requires an opted-in generated module')
    if hucard_boot and runtime['cd_unknown_status'] != 'fault':
        raise ValueError('HuCard has no CD unknown-command response profile')
    if 'cd_timing' in runtime:
        _choice(runtime['cd_timing'], ('fixed', 'gear-distance'), 'cd_timing')
        if hucard_boot and runtime['cd_timing'] != 'fixed':
            raise ValueError('HuCard has no distance-aware CD timing profile')
    for key, values in (("tier", ("native", "hybrid")), ("video", ("snapshot", "continuous")),
                        ("cd_unknown_status", ("fault", "gear-good", "nec-invalid")), ("joypad", (2, 6)),
                        ("region", ("usa", "japan")), ("multitap", ("off", "on"))):
        _choice(runtime[key], values, key)
    if type(runtime["joypad"]) is not int:
        raise ValueError("joypad requires integer 2 or 6")
    if "vdc_access" in runtime:
        _choice(runtime["vdc_access"], ("queued", "immediate"), "vdc_access")
        if not (reset_boot or "bios" in config or runtime["video"] == "continuous"):
            raise ValueError("vdc_access requires an enabled clocked VDC profile")
    if "audio" in runtime:
        _choice(runtime["audio"], ("on", "off"), "audio")
    if {"audio_profile", "audio_rate", "audio_timing"} & runtime.keys():
        if runtime.get("audio") != "on":
            raise ValueError("audio_profile, audio_rate and audio_timing require explicit audio = on")
        if "audio_timing" in runtime:
            _choice(runtime["audio_timing"], ("gear", "legacy"), "audio_timing")
        if "audio_profile" in runtime:
            _choice(runtime["audio_profile"], ("raw", "filtered"), "audio_profile")
        if "audio_rate" in runtime:
            if type(runtime["audio_rate"]) is not int or runtime["audio_rate"] not in (44100, 48000):
                raise ValueError("audio_rate requires integer 44100 or 48000")
        if runtime.get("audio_profile", "raw") == "raw" and runtime.get("audio_rate", 44100) != 44100:
            raise ValueError("raw audio requires audio_rate = 44100")
    limits = _table(config["limits"], {"steps", "ticks", "wall_seconds"}, name="limits")
    _integer(limits["steps"], 1, 20000000000, "steps")
    _integer(limits["ticks"], 1, 2**64 - 1, "ticks")
    _integer(limits["wall_seconds"], 1, MAX_WALL_SECONDS, "wall_seconds")
    cue_disc = None
    for name in ASSETS & config.keys():
        entry = config[name]
        if name == "disc" and isinstance(entry, dict) and isinstance(entry.get("path"), str) and Path(entry["path"]).suffix.lower() == ".cue":
            from .cue import Cue
            _table(entry, {"path", "sha256"}, name="disc")
            disc = Cue(base / entry["path"])
            if disc.image_sha256() != _digest(entry["sha256"], "disc"):
                raise ValueError("disc complete BIN/CUE image SHA256 mismatch")
            # FILE names are relative to the declared CUE location. Passing
            # its symlink's resolved target could silently select other BINs.
            files[name] = disc.declared_path
            files.update({f"disc_component:{name}": path for name, path in disc.referenced_files.items()})
            cue_disc = disc
        else:
            files[name] = _file(base, entry, name)
    for name, expected_size in (("bios", 262144), ("bram", 2048)):
        if name in files and files[name].stat().st_size != expected_size:
            raise ValueError(f"{name} requires exactly {expected_size} bytes")
    if "libchdr" in files and "disc" not in files:
        raise ValueError("libchdr requires disc")
    if hucard_boot:
        from .cartridge import Cartridge
        card = Cartridge(files['cartridge'], boot['header'], boot['encoding'], boot['profile'])
        if card.raw_sha256 != config['cartridge']['sha256']:
            raise ValueError('Cartridge changed during verification')
    identities = {name: sha256(path) for name, path in sorted(files.items())}
    if ('observation_profile' in module
            and identities['module_observation_profile'] != module['observation_profile']['sha256']):
        raise ValueError('module.observation_profile changed during input binding')
    descriptor_hash = sha256(descriptor)
    if cue_disc is not None:
        cue_disc.check_unchanged()
    if hucard_boot:
        card.check_unchanged()
        if identities['cartridge'] != config['cartridge']['sha256']:
            raise ValueError('Cartridge changed during input binding')
    return {"descriptor": descriptor, "config": config, "tool_root": tool_root,
            "tool_identity": identity, "revision_override": identity["revision"] != tool["revision"],
            "files": files, "identities": identities, "descriptor_sha256": descriptor_hash}


def _binding(project):
    return {"descriptor_sha256": project["descriptor_sha256"],
            "tool": project["tool_identity"], "files": project["identities"],
            "revision_override": project["revision_override"]}


def _write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def _cmake_path(path):
    text = path.as_posix()
    if any(c in text for c in '\n\r";$'):
        raise ValueError("Path cannot be represented safely in generated CMake")
    return '"' + text + '"'


def build(descriptor: Path, build_dir: Path, *, allow_revision_override=False,
          generator=None, desktop=False, cmake_args=(), cache_root=None,
          cache_toolchain_root=None, cache_dependency_roots=()) -> dict:
    project = verify(descriptor, allow_revision_override=allow_revision_override)
    build_dir = build_dir.resolve()
    if build_dir.exists():
        raise ValueError("Build directory exists; choose a new directory")
    if type(desktop) is not bool:
        raise ValueError("desktop must be boolean")
    if desktop and project["config"]["runtime"]["video"] != "continuous":
        raise ValueError("Desktop requires continuous video")
    # Additional CMake options are intentionally only toolchain/package paths.
    for argument in cmake_args:
        if not isinstance(argument, str) or not re.fullmatch(r"-D(CMAKE_CXX_COMPILER|CMAKE_MAKE_PROGRAM|SDL3_DIR|CMAKE_TOOLCHAIN_FILE)=[^\r\n]+", argument):
            raise ValueError("Unsupported extra CMake argument")
    if cache_root is None and (cache_toolchain_root is not None or cache_dependency_roots):
        raise ValueError('Cache input roots require --cache-root')
    if cache_root is not None:
        return _cached_build(project, build_dir, allow_revision_override=allow_revision_override,
            generator=generator, desktop=desktop, cmake_args=cmake_args, cache_root=cache_root,
            cache_toolchain_root=cache_toolchain_root, cache_dependency_roots=cache_dependency_roots)
    return _compile_build(project, build_dir, allow_revision_override=allow_revision_override,
                          generator=generator, desktop=desktop, cmake_args=cmake_args)


def _compile_build(project, build_dir, *, allow_revision_override, generator, desktop,
                   cmake_args, cache_context=None):
    commands = _configure_build(project, build_dir, generator=generator, desktop=desktop,
                                cmake_args=cmake_args, cache_context=cache_context)
    return _compile_configured(project, build_dir, allow_revision_override=allow_revision_override,
        desktop=desktop, commands=commands, cache_context=cache_context)


def _configure_build(project, build_dir, *, generator, desktop, cmake_args, cache_context=None):
    wrapper = build_dir / "source"
    wrapper.mkdir(parents=True)
    source = ["cmake_minimum_required(VERSION 3.20)", "project(PCEConsumer LANGUAGES CXX)",
              "set(BUILD_TESTING OFF CACHE BOOL \"\" FORCE)",
              "set(PCE_BUILD_TESTS OFF CACHE BOOL \"\" FORCE)",
              "set(PCE_BUILD_TOOLS OFF CACHE BOOL \"\" FORCE)",
              "set(PCE_BUILD_REFERENCE_PROBE OFF CACHE BOOL \"\" FORCE)",
              f"set(PCE_BUILD_DESKTOP {'ON' if desktop else 'OFF'} CACHE BOOL \"\" FORCE)",
              f"add_subdirectory({_cmake_path(project['tool_root'])} tool)",
              f"pce_add_consumer(pce-consumer MODULE {_cmake_path(project['files']['module_source'])} MANIFEST {_cmake_path(project['files']['module_manifest'])}{' DESKTOP' if desktop else ''})",
              'set_target_properties(pce-consumer PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<0:>")', ""]
    if cache_context and desktop:
        source.append('file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/cache-sdl-runtime.txt" CONTENT "$<TARGET_PROPERTY:pce-desktop-host,PCE_DESKTOP_RUNTIME_DLL>")')
    (wrapper / "CMakeLists.txt").write_text("\n".join(source), encoding="utf-8")
    binary_dir = build_dir / "build"
    cmake = str(cache_context['tools']['cmake']) if cache_context else 'cmake'
    configure = [cmake, "-S", str(wrapper), "-B", str(binary_dir), "-DCMAKE_BUILD_TYPE=Release"]
    if generator:
        configure += ["-G", generator]
    configure += list(cmake_args)
    if cache_context:
        configure += ['-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF',
                      '-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF',
                      '-DCMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH=OFF',
                      '-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=OFF']
        query = binary_dir/'.cmake/api/v1/query'
        query.mkdir(parents=True)
        for name in ('codemodel-v2', 'toolchains-v1', 'cmakeFiles-v1'):
            (query/name).touch()
    options = {'env':cache_context['environment']} if cache_context else {}
    subprocess.run(configure, check=True, shell=False, **options)
    return [configure]


def _compile_configured(project, build_dir, *, allow_revision_override, desktop, commands,
                        cache_context=None):
    descriptor = project['descriptor']
    binary_dir = build_dir / 'build'
    cmake = str(cache_context['tools']['cmake']) if cache_context else 'cmake'
    compile_command = [cmake, "--build", str(binary_dir), "--config", "Release", "--target", "pce-consumer", "--parallel", "2"]
    options = {'env':cache_context['environment']} if cache_context else {}
    subprocess.run(compile_command, check=True, shell=False, **options)
    # The build may have raced a source modification: refuse to bless it.
    after = verify(descriptor, allow_revision_override=allow_revision_override)
    if _binding(after) != _binding(project):
        raise ValueError("Source/input identity changed during build")
    binary = binary_dir / "bin" / ("pce-consumer.exe" if os.name == "nt" else "pce-consumer")
    dependencies = {p.name: sha256(p) for p in sorted(binary.parent.iterdir()) if p.is_file()}
    receipt = {"schema": 1, "kind": "pce-consumer-build", "binding": _binding(project),
               "binary": str(binary), "binary_sha256": sha256(binary), "desktop": desktop,
               "output_files": dependencies, "commands": commands + [compile_command],
               "execution_evidence": False}
    if cache_context is None:
        _write_new(build_dir / "build-receipt.json", receipt)
    return receipt


def _cached_build(project, build_dir, *, allow_revision_override, generator, desktop,
                  cmake_args, cache_root, cache_toolchain_root, cache_dependency_roots):
    from .build_cache import BuildCache, contract_identity
    from .build_inputs import prepare, verify_closure, configuration_identity
    started = time.monotonic()
    arguments = dict(generator=generator, desktop=desktop, cmake_args=cmake_args,
        toolchain_root=cache_toolchain_root, dependency_roots=cache_dependency_roots,
        build_dir=build_dir, cache_root=cache_root)
    context = prepare(project, **arguments)
    initial_contract = context['contract']
    commands = _configure_build(project, build_dir, generator=generator, desktop=desktop,
                                cmake_args=cmake_args, cache_context=context)
    configured = configuration_identity(context, build_dir/'build')
    context = dict(context, contract=dict(initial_contract, configured=configured))
    def unchanged():
        current = verify(project['descriptor'], allow_revision_override=allow_revision_override)
        if (_binding(current) != _binding(project)
                or prepare(current, **arguments)['contract'] != initial_contract
                or configuration_identity(context, build_dir/'build') != configured):
            raise ValueError('Cache source, module, SDK or toolchain changed during build/reuse')
    # Keep every audited field in the receipt, but bind large source graphs by
    # their complete canonical identity rather than duplicating them in each
    # bounded package manifest. No field is omitted from the digest.
    key_contract = contract_identity(context['contract'])
    with BuildCache(cache_root, key_contract) as cache:
        package = build_dir/'build/bin'
        package.parent.mkdir(parents=True, exist_ok=True)
        # CMake creates the output directory during generation. Restore is
        # create-new: only remove that empty directory, never its contents.
        if package.exists():
            package.rmdir()
        manifest = cache.restore(package)
        hit = manifest is not None
        audit = None
        if hit:
            unchanged()
            binary = package/'pce-consumer.exe'
            receipt = dict(schema=1, kind='pce-consumer-build', binding=_binding(project),
                binary=str(binary), binary_sha256=sha256(binary), desktop=desktop,
                output_files={p.name:sha256(p) for p in sorted(package.iterdir()) if p.is_file()},
                commands=commands, execution_evidence=False)
        else:
            receipt = _compile_configured(project, build_dir, allow_revision_override=allow_revision_override,
                desktop=desktop, commands=commands, cache_context=context)
            audit = verify_closure(context, build_dir/'build')
            unchanged()
            manifest = cache.publish(package)
        manifest_path = cache.entry/'manifest.json'
        receipt['cache'] = dict(schema=1, hit=hit, key=cache.key,
            producer=context['contract']['producer'], manifest_sha256=sha256(manifest_path),
            manifest=dict(path=str(manifest_path), sha256=sha256(manifest_path), bytes=manifest_path.stat().st_size),
            input_contract=context['contract'], key_contract=key_contract, input_audit=audit,
            elapsed_seconds=time.monotonic()-started,
            scope='Verified exact binary-package reuse only; no cached execution receipt or native-coverage promotion')
        _write_new(build_dir/'build-receipt.json', receipt)
        return receipt


def checkpoint_context(project: dict) -> str:
    """Exact reviewed source/input/profile recipe, independent of run limits."""
    config = project['config']
    recipe = {'schema': 1, 'kind': 'pce-developer-checkpoint-context',
              'tool': {'revision': project['tool_identity']['revision'],
                       'source_sha256': project['tool_identity']['source_sha256'],
                       'runtime_abi': config['tool']['runtime_abi']},
              'inputs': project['identities'], 'runtime': config['runtime']}
    if 'boot' in config:
        recipe['boot'] = config['boot']
    else:
        recipe['payload'] = {key: value for key, value in config['payload'].items() if key not in {'path', 'sha256'}}
    return hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _checkpoint_name(name):
    if (not isinstance(name, str) or not 1 <= len(name) <= 96 or '..' in name or not name.endswith('.pcec')
            or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) is None
            or name.split('.', 1)[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}):
        raise ValueError('checkpoint_load requires a portable direct basename')
    return name


def command_for(project: dict, binary: Path, *, dev_port=None, start_paused=False, memory_write=False,
                code_capture=None, capture_limit=None, checkpoint_dir=None, checkpoint_load=None):
    config, files = project["config"], project["files"]
    limits, runtime = config["limits"], config["runtime"]
    if "boot" in config:
        if config['boot']['mode'] == 'hucard-reset':
            command = [str(binary), '--hucard-reset', config['boot']['profile'], str(files['cartridge']),
                       str(limits['steps']), str(limits['ticks']), runtime['tier'],
                       '--rom-header', config['boot']['header'], '--rom-encoding', config['boot']['encoding']]
        else:
            command = [str(binary), "--system-card-reset", config["boot"]["profile"], str(files["bios"]),
                       str(limits["steps"]), str(limits["ticks"]), runtime["tier"]]
            if "arcade_card" in config["boot"]:
                command += ["--arcade-card", config["boot"]["arcade_card"]]
    else:
        payload = config["payload"]
        command = [str(binary), str(files["payload"]), str(payload["physical_load"]), str(payload["pc"]),
                   ",".join(map(str, payload["mpr"])), str(limits["steps"]), str(limits["ticks"]), runtime["tier"]]
    for key, flag in (("video", "video-output"), ("cd_unknown_status", "cd-unknown-status"),
                      ("joypad", "joypad"), ("region", "joypad-region"), ("multitap", "multitap")):
        command += ["--" + flag, str(runtime[key])]
    command += ["--wall-seconds", str(limits["wall_seconds"])]
    if "audio" in runtime:
        command += ["--audio-output", runtime["audio"]]
    for field, flag in (("audio_profile", "audio-profile"), ("audio_rate", "audio-rate"), ("audio_timing", "audio-timing"), ("vdc_access", "vdc-access"), ("native_span", "native-span"), ("cd_timing", "cd-timing")):
        if field in runtime:
            command += ["--" + flag, str(runtime[field])]
    for name in sorted(ASSETS & files.keys()):
        if name == 'cartridge':
            continue
        if name == "bios" and "boot" in config:
            continue
        command += ["--" + name.replace("_", "-"), str(files[name])]
    if dev_port is not None:
        _integer(dev_port, 0, 65535, "dev_port")
        if runtime["video"] != "continuous":
            raise ValueError("TCP requires continuous video")
        command += ["--dev-port", str(dev_port), "--dev-start-paused", "on" if start_paused else "off",
                    "--dev-memory-write", "on" if memory_write else "off"]
    elif start_paused or memory_write:
        raise ValueError("Pause/memory writes require --dev-port")
    if code_capture is not None:
        command += ["--code-capture", str(Path(code_capture).resolve())]
        if capture_limit is not None:
            _integer(capture_limit, 1, 65536, "capture_limit")
            command += ["--capture-limit", str(capture_limit)]
    elif capture_limit is not None:
        raise ValueError("capture_limit requires code_capture")
    if checkpoint_dir is not None:
        directory = Path(checkpoint_dir).absolute()
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('checkpoint_dir requires an existing private directory without a symlink')
        if dev_port is None or not start_paused:
            raise ValueError('Developer checkpoints require paused TCP startup')
        command += ['--checkpoint-dir', str(directory), '--checkpoint-context', checkpoint_context(project)]
        if checkpoint_load is not None:
            command += ['--checkpoint-load', _checkpoint_name(checkpoint_load)]
    elif checkpoint_load is not None:
        raise ValueError('checkpoint_load requires checkpoint_dir')
    return command


def _checkpoint_provenance(result, *, requested=False):
    value = result.get('checkpoint') if isinstance(result, dict) else None
    if value is None and not requested:
        return None
    try:
        if not isinstance(value, dict) or type(value.get('resumed')) is not bool:
            raise ValueError('Missing checkpoint execution origin')
        if not value['resumed']:
            if requested or set(value) != {'resumed'}:
                raise ValueError('Requested checkpoint did not resume')
            return {'valid': True, 'resumed': False}
        _table(value, {'resumed', 'origin', 'window'}, optional={'audio_origin'}, name='checkpoint execution')
        from .capture import validate_checkpoint_origin
        origin = validate_checkpoint_origin(value['origin'])
        window = _table(value['window'], {'ticks', 'native_steps', 'interpreter_steps'}, name='checkpoint execution window')
        for key in window:
            _integer(window[key], 0, 2**64-1, 'checkpoint window '+key)
            _integer(result.get(key), 0, 2**64-1, 'checkpoint lifetime '+key)
            if result[key] < origin[key] or result[key]-origin[key] != window[key]:
                raise ValueError('Checkpoint imported/window counters disagree with lifetime '+key)
        report = {'valid': True, 'resumed': True, 'origin': origin, 'window': dict(window)}
        if 'audio_origin' in value:
            audio = _table(value['audio_origin'], {'pending_pcm_frames', 'source_wav_frames'}, name='checkpoint audio origin')
            _integer(audio['pending_pcm_frames'], 0, 8192, 'checkpoint pending PCM frames')
            _integer(audio['source_wav_frames'], 0, 2**64-1, 'checkpoint source WAV frames')
            report['audio_origin'] = dict(audio)
        return report
    except (ValueError, TypeError, KeyError) as error:
        return {'valid': False, 'error': str(error)}


def _boot_provenance(project, result, *, bram_seeded=None):
    """Validate reported initial reset state, independently of final CPU state."""
    if "boot" not in project["config"]:
        return None
    try:
        boot = project['config']['boot']
        card = None
        if boot['mode'] == 'hucard-reset':
            from .cartridge import Cartridge
            card = Cartridge(project['files']['cartridge'], boot['header'], boot['encoding'], boot['profile'])
            if card.raw_sha256 != project['identities']['cartridge']:
                raise ValueError('Reset vector is not from the pinned cartridge')
            pc = card.reset_pc
        else:
            with project["files"]["bios"].open("rb") as stream:
                stream.seek(0x1FFE)
                vector = stream.read(2)
            if len(vector) != 2:
                raise ValueError("Reset vector is unavailable in the pinned BIOS")
            pc = vector[0] | (vector[1] << 8)
        expected = {"mode": boot['mode'], "profile": boot['profile'],
                    "initialization": "gear-deterministic-zero-v1", "vector_physical": 8190,
                    "pc": pc, "a": 0, "x": 0, "y": 0, "sp": 0, "p": 4,
                    "clock_divisor": 12, "ticks": 0, "cycles": 0, "mpr": [0] * 8}
        if card is not None:
            expected.update(header=boot['header'], encoding=boot['encoding'], rom_bytes=len(card.rom), cd=False)
            if boot['profile'] == 'sf2':
                expected['mapper_latch'] = 0
            elif boot['profile'] == 'populous':
                expected['cartridge_ram_bytes'] = 32768
        else:
            seeded = "bram" in project["files"] if bram_seeded is None else bram_seeded
            expected['bram'] = "explicit-image" if seeded else "blank-unformatted"
            if "arcade_card" in boot:
                expected['arcade_card'] = boot['arcade_card']
        reported = result.get("boot") if isinstance(result, dict) else None
        if not isinstance(reported, dict) or set(reported) != set(expected):
            raise ValueError("Reset boot metadata fields differ from the declared startup recipe")
        for key, value in expected.items():
            actual = reported[key]
            if type(actual) is not type(value) or actual != value:
                raise ValueError(f"Reset boot metadata mismatch: {key}")
            if key == "mpr" and any(type(item) is not int for item in actual):
                raise ValueError("Reset boot MPR metadata requires integer bytes")
        if card is not None:
            card.check_unchanged()
        return {"valid": True}
    except (ValueError, OSError) as error:
        return {"valid": False, "error": str(error)}


def _vdc_access_provenance(project, result):
    """Validate an explicitly selected access profile without guessing legacy output."""
    expected = project["config"]["runtime"].get("vdc_access")
    if expected is None:
        return None
    try:
        value = result.get("vdc_access") if isinstance(result, dict) else None
        _table(value, {"profile", "pending_read", "pending_write", "delay", "phase", "wait_ticks"}, name="vdc_access report")
        if value["profile"] != expected:
            raise ValueError("Reported VDC access profile differs from the declared runtime")
        if type(value["pending_read"]) is not bool or type(value["pending_write"]) is not bool:
            raise ValueError("Reported VDC pending flags must be boolean")
        _integer(value["delay"], 0, 2**64-1, "VDC transfer delay")
        _integer(value["phase"], 0, 2, "VDC transfer phase")
        _integer(value["wait_ticks"], 0, 2**64-1, "VDC wait ticks")
        if value["wait_ticks"] % 3:
            raise ValueError("VDC waits must be whole fast master cycles")
        if not value["pending_read"] and not value["pending_write"] and (value["delay"] or value["phase"]):
            raise ValueError("Idle VDC access state retains a transfer countdown")
        if expected == "immediate" and any(value[key] for key in ("pending_read", "pending_write", "delay", "phase", "wait_ticks")):
            raise ValueError("Immediate VDC access profile cannot retain queued accesses or wait ticks")
        return {"valid": True}
    except (ValueError, TypeError, KeyError) as error:
        return {"valid": False, "error": str(error)}


def _native_dispatch_provenance(project, result):
    expected = project['config']['runtime'].get('native_span')
    if expected is None:
        return None
    try:
        value = result.get('native_dispatch') if isinstance(result, dict) else None
        fields = {'schema', 'protocol', 'supported', 'limit', 'batches', 'generated_calls',
                  'native_completed', 'interpreted_completed', 'local_continuations', 'max_completed'}
        _table(value, fields, name='native_dispatch report')
        if (type(value['schema']) is not int or value['schema'] != 1
                or value['protocol'] != 'per_instruction_v1'
                or type(value['supported']) is not bool):
            raise ValueError('Unsupported native dispatch report')
        manifest = json.loads(project['files']['module_manifest'].read_text(encoding='utf-8'))
        if value['supported'] != ('native_span' in manifest):
            raise ValueError('Reported native span support differs from the bound module')
        for key in fields - {'protocol', 'supported'}:
            _integer(value[key], 0, 2**64-1, 'native_dispatch.'+key)
        if value['limit'] != expected:
            raise ValueError('Reported native span limit differs from the declared runtime')
        n, i = result.get('native_steps'), result.get('interpreter_steps')
        checkpoint = _checkpoint_provenance(result)
        if checkpoint is not None:
            if not checkpoint['valid']:
                raise ValueError(checkpoint['error'])
            if checkpoint['resumed']:
                n, i = (checkpoint['window'][key] for key in ('native_steps', 'interpreter_steps'))
        if type(n) is not int or type(i) is not int or n < 0 or i < 0:
            raise ValueError('Missing native dispatch retirement counters')
        total = n+i
        if value['native_completed'] != n or value['interpreted_completed'] != i:
            raise ValueError('Native dispatch completions differ from actual retired work')
        if (not (total+expected-1)//expected <= value['batches'] <= total+1
                or value['generated_calls'] > total+1
                or value['generated_calls'] < i
                or n and (not value['generated_calls'] or value['local_continuations'] >= n)
                or value['local_continuations'] > n
                or value['generated_calls'] < n-value['local_continuations']
                or not (1 if total else 0) <= value['max_completed'] <= (min(expected,total) if total else 0)
                or expected == 1 and value['local_continuations']):
            raise ValueError('Inconsistent native dispatch boundary accounting')
        return {'valid': True, **value}
    except (ValueError, OSError, KeyError, TypeError) as error:
        return {'valid': False, 'error': str(error)}


def save_identity(project, contract: str) -> str:
    """Stable save binding: exact media/firmware plus an explicit mod/save contract.

    Compiler revisions, ABI numbers and native coverage are intentionally absent.
    Changes to game modifications or save layout require a new caller contract.
    """
    _digest(contract, "save_contract")
    if "bram" in project["files"]:
        raise ValueError("Persistent sessions cannot also use a descriptor BRAM seed")
    boot = project["config"].get("boot")
    if boot is None or boot.get("mode") != "system-card-reset":
        raise ValueError("Consumer persistence requires explicit System Card reset boot")
    binding = {"schema": 1, "kind": "pce-bram-compatibility", "contract": contract,
               "boot": boot, "media": {key: value for key, value in project["identities"].items()
                       if key in {"bios", "disc", "toc"} or key.startswith("disc_component:")}}
    return hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(descriptor: Path, build_dir: Path, receipt_path: Path, *, allow_revision_override=False,
        dev_port=None, start_paused=False, memory_write=False, code_capture=None, capture_limit=None,
        save_root=None, save_namespace=None, save_contract=None, checkpoint_dir=None, checkpoint_load=None) -> dict:
    options = dict(allow_revision_override=allow_revision_override, dev_port=dev_port,
                   start_paused=start_paused, memory_write=memory_write,
                   code_capture=code_capture, capture_limit=capture_limit,
                   checkpoint_dir=checkpoint_dir, checkpoint_load=checkpoint_load)
    requested = (save_root is not None, save_namespace is not None, save_contract is not None)
    if not any(requested):
        return _run(descriptor, build_dir, receipt_path, **options)
    if not all(requested):
        raise ValueError("Persistence requires save_root, save_namespace and save_contract together")
    if checkpoint_load is not None:
        raise ValueError('Checkpoint loading cannot publish a persistent BRAM session')
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ValueError("Execution receipt already exists")
    checked = verify(descriptor, allow_revision_override=allow_revision_override)
    identity = save_identity(checked, save_contract)
    root = Path(save_root).absolute()
    # Keep disposable outputs out of the dedicated mutable-save directory.
    for output in (receipt_path, code_capture):
        if output is not None and Path(output).resolve().is_relative_to(root.resolve()):
            raise ValueError("Execution receipt/capture must be outside the save root")
    from .saves import BramSession
    with BramSession(root, save_namespace, identity) as session:
        return _run(descriptor, build_dir, receipt_path, bram_session=session, bram_contract=save_contract, **options)


def _run(descriptor: Path, build_dir: Path, receipt_path: Path, *, allow_revision_override=False,
         dev_port=None, start_paused=False, memory_write=False, code_capture=None, capture_limit=None,
         bram_session=None, bram_contract=None, checkpoint_dir=None, checkpoint_load=None) -> dict:
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ValueError("Execution receipt already exists")
    project = verify(descriptor, allow_revision_override=allow_revision_override)
    built = json.loads((build_dir / "build-receipt.json").read_text(encoding="utf-8"))
    if 'incremental' in built:
        from .incremental import validate_run
        validate_run(build_dir, built)
    if built.get("schema") != 1 or built.get("kind") != "pce-consumer-build" or built.get("binding") != _binding(project):
        raise ValueError("Build receipt does not match verified consumer")
    binary = Path(built["binary"])
    if sha256(binary) != built["binary_sha256"]:
        raise ValueError("Built executable changed")
    outputs = {p.name: sha256(p) for p in sorted(binary.parent.iterdir()) if p.is_file()}
    if outputs != built["output_files"]:
        raise ValueError("Build output/dependency identities changed")
    if code_capture is not None:
        code_capture = Path(code_capture).resolve()
        if code_capture.exists() or code_capture.is_symlink() or not code_capture.parent.is_dir():
            raise ValueError("Code capture requires a new file in an existing directory")
        if code_capture == receipt_path.resolve():
            raise ValueError("Capture and execution receipt require separate paths")
    command = command_for(project, binary, dev_port=dev_port, start_paused=start_paused, memory_write=memory_write,
                          code_capture=code_capture, capture_limit=capture_limit,
                          checkpoint_dir=checkpoint_dir, checkpoint_load=checkpoint_load)
    if bram_session is not None:
        if save_identity(project, bram_contract) != bram_session.compatibility_sha256:
            raise ValueError("Consumer save binding changed before execution")
        if bram_session.seed_path is not None:
            command += ["--bram", str(bram_session.seed_path)]
        command += ["--bram-out", str(bram_session.output_path)]
    started = time.monotonic()
    # Inherit stderr so ephemeral TCP port discovery remains immediately visible.
    timed_out = False
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=False,
                                   timeout=project["config"]["limits"]["wall_seconds"] + 10)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        completed = subprocess.CompletedProcess(command, -1, output)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = None
    checkpoint_report = _checkpoint_provenance(result, requested=checkpoint_load is not None)
    counters = None
    if isinstance(result, dict) and all(type(result.get(k)) is int and result[k] >= 0 for k in ("native_steps", "interpreter_steps")):
        native, interpreted = result["native_steps"], result["interpreter_steps"]
        if checkpoint_report is not None and checkpoint_report['valid'] and checkpoint_report['resumed']:
            native, interpreted = (checkpoint_report['window'][key] for key in ('native_steps', 'interpreter_steps'))
        counters = {"native": native, "interpreted": interpreted, "total": native + interpreted,
                    "native_fraction": native / (native + interpreted) if native + interpreted else 0.0}
    if checkpoint_report is not None and not checkpoint_report['valid']:
        counters = None
    unchanged = {name: path.is_file() and sha256(path) == project["identities"][name] for name, path in project["files"].items()}
    source_unchanged = source_identity(project["tool_root"]) == project["tool_identity"]
    outputs_unchanged = all((binary.parent / name).is_file() and sha256(binary.parent / name) == digest
                            for name, digest in built["output_files"].items())
    boot_report = _boot_provenance(project, result, bram_seeded=(bram_session.seed_path is not None)
                                   if bram_session is not None else None)
    vdc_report = _vdc_access_provenance(project, result)
    dispatch_report = _native_dispatch_provenance(project, result)
    capture_report = None
    if code_capture is not None:
        from .capture import load_capture
        try:
            capture, capture_hash = load_capture(code_capture)
            if capture["runtime_abi"] != ABI:
                raise ValueError("Fresh code capture runtime ABI differs from the running tool")
            expected_origin = (checkpoint_report['origin'] if checkpoint_report and checkpoint_report['valid']
                               and checkpoint_report['resumed'] else None)
            if capture.get('checkpoint_origin') != expected_origin:
                raise ValueError('Code capture checkpoint origin differs from execution window')
            if capture["capacity"] != (capture_limit if capture_limit is not None else 16384):
                raise ValueError("Code capture capacity differs from the requested limit")
            if counters is None or capture["retired_instructions"] != counters["total"]:
                raise ValueError("Code capture total differs from final execution counters")
            native_hits = sum(item["native_hits"] for item in capture["observations"])
            interpreted_hits = sum(item["interpreted_hits"] for item in capture["observations"])
            if native_hits > counters["native"] or interpreted_hits > counters["interpreted"]:
                raise ValueError("Code capture tier hits exceed final execution counters")
            lost = capture["dropped_instructions"] + capture["unreadable_instructions"]
            if counters["total"] - native_hits - interpreted_hits != lost:
                raise ValueError("Code capture missing retirements differ from its recorded loss")
            # Loss counters have no execution tier. Retain that uncertainty;
            # a lossless capture must account for each tier exactly.
            if not lost and (native_hits != counters["native"] or interpreted_hits != counters["interpreted"]):
                raise ValueError("Complete code capture tier hits differ from final execution counters")
            capture_report = {"path": str(code_capture), "sha256": capture_hash,
                              "bytes": code_capture.stat().st_size, "valid": True,
                              "runtime_abi": capture["runtime_abi"], "native_hits": native_hits,
                              "interpreted_hits": interpreted_hits, "unclassified_retirements": lost,
                              **{key: capture[key] for key in ("capacity", "complete", "dropped_instructions",
                                   "unreadable_instructions", "retired_instructions")},
                              "observations": len(capture["observations"])}
            if expected_origin is not None:
                capture_report['checkpoint_origin'] = expected_origin
        except (ValueError, OSError, KeyError, TypeError) as error:
            capture_report = {"path": str(code_capture), "valid": False, "error": str(error)}
    receipt = {"schema": 1, "kind": "pce-consumer-execution", "binding": _binding(project),
               "binary_sha256": built["binary_sha256"], "command": command,
               "elapsed_seconds": time.monotonic() - started, "exit_code": completed.returncode,
               "timed_out": timed_out, "tool_source_unchanged": source_unchanged,
               "build_outputs_unchanged": outputs_unchanged, "code_capture": capture_report,
               "input_hashes_unchanged": unchanged, "work": counters, "result": result,
               "qualified": completed.returncode == 0 and counters is not None and all(unchanged.values())
                            and source_unchanged and outputs_unchanged and (capture_report is None or capture_report["valid"])
                            and (boot_report is None or boot_report["valid"])
                            and (vdc_report is None or vdc_report["valid"])
                            and (dispatch_report is None or dispatch_report['valid']),
               "limits": ["Execution receipt is reproducibility evidence, not independent emulator parity",
                          "Native site count is not executed native work; full host diagnostics retained",
                          "BRAM is volatile unless an explicit save session commits; unknown-command profile is explicit"]}
    if checkpoint_report is not None:
        receipt['checkpoint_validation'] = checkpoint_report
        receipt['qualified'] &= checkpoint_report['valid']
        if checkpoint_report['valid'] and checkpoint_report['resumed']:
            receipt['work']['execution_window'] = 'resumed-checkpoint-suffix'
            receipt['work']['imported'] = checkpoint_report['origin']
            receipt['limits'].append('Work counts describe only this resumed checkpoint suffix; imported prefix is separate')
    if boot_report is not None:
        receipt["boot_validation"] = boot_report
    if vdc_report is not None:
        receipt["vdc_access_validation"] = vdc_report
    if dispatch_report is not None:
        receipt['native_dispatch_validation'] = dispatch_report
    if bram_session is not None:
        save_report = {"namespace": bram_session.namespace,
                       "compatibility_sha256": bram_session.compatibility_sha256,
                       "seeded": bram_session.seed_path is not None,
                       "previous_payload_sha256": bram_session.previous_payload_sha256,
                       "committed": False}
        if receipt["qualified"]:
            try:
                if result.get("stop") not in {"step_limit", "budget", "dev_quit", "window_closed"}:
                    raise ValueError("Save session requires an orderly budget or quit stop")
                save_report.update(bram_session.commit(), committed=True)
            except (ValueError, OSError) as error:
                save_report["error"] = str(error)
                save_report["committed"] = bram_session.committed
                receipt["qualified"] = False
        receipt["bram_session"] = save_report
    _write_new(receipt_path, receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    identity_parser = commands.add_parser("identity")
    identity_parser.add_argument("tool_root", type=Path)
    for name in ("verify", "build", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("descriptor", type=Path)
        sub.add_argument("--allow-revision-override", action="store_true")
        if name in ("build", "run"):
            sub.add_argument("--build-dir", type=Path, required=True)
        if name == "build":
            sub.add_argument("--generator")
            sub.add_argument("--desktop", action="store_true")
            sub.add_argument("--cmake-arg", action="append", default=[])
            sub.add_argument('--cache-root', type=Path)
            sub.add_argument('--cache-toolchain-root', type=Path)
            sub.add_argument('--cache-dependency-root', type=Path, action='append', default=[])
        if name == "run":
            sub.add_argument("--receipt", type=Path, required=True)
            sub.add_argument("--dev-port", type=int)
            sub.add_argument("--start-paused", action="store_true")
            sub.add_argument("--memory-write", action="store_true")
            sub.add_argument("--code-capture", type=Path)
            sub.add_argument("--capture-limit", type=int)
            sub.add_argument("--save-root", type=Path)
            sub.add_argument("--save-namespace")
            sub.add_argument("--save-contract", help="SHA256 of the consumer's explicit save/mod compatibility contract")
            sub.add_argument('--checkpoint-dir', type=Path)
            sub.add_argument('--checkpoint-load', help='Private direct checkpoint basename to import at paused startup')
    args = parser.parse_args(argv)
    try:
        if args.command == "identity":
            result = source_identity(args.tool_root)
        elif args.command == "verify":
            checked = verify(args.descriptor, allow_revision_override=args.allow_revision_override)
            result = {"schema": 1, "verified": True, **_binding(checked)}
        elif args.command == "build":
            result = build(args.descriptor, args.build_dir, allow_revision_override=args.allow_revision_override,
                           generator=args.generator, desktop=args.desktop, cmake_args=args.cmake_arg,
                           cache_root=args.cache_root, cache_toolchain_root=args.cache_toolchain_root,
                           cache_dependency_roots=args.cache_dependency_root)
        else:
            result = run(args.descriptor, args.build_dir, args.receipt, allow_revision_override=args.allow_revision_override,
                         dev_port=args.dev_port, start_paused=args.start_paused, memory_write=args.memory_write,
                         code_capture=args.code_capture, capture_limit=args.capture_limit,
                         save_root=args.save_root, save_namespace=args.save_namespace, save_contract=args.save_contract,
                         checkpoint_dir=args.checkpoint_dir, checkpoint_load=args.checkpoint_load)
        print(json.dumps(result, indent=2))
        return 0 if args.command != "run" or result["qualified"] else 3
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
        print(f"consumer: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
