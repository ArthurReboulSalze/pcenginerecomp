import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from .abi import ABI
from . import __version__
from .analysis import Snapshot, analyze
from .emitter import emit, emit_capture, emit_observation_profile
from .capture import load_capture
from .observations import compose_observation_profile, load_observation_profile, MAX_PROFILE_BYTES
from .isa import Instruction, listing
from .media import Chd, ChdReader, Ipl, IsoReader, MediaError, sha256
from .cue import Cue
from .toc import Toc
from .cartridge import Cartridge, HEADERS, ENCODINGS, PROFILES


def library_default():
    root = Path(__file__).resolve().parent.parent
    for name in ("libchdr.dll", "libchdr.so", "libchdr.dylib"):
        path = root / ".deps" / "libchdr-build" / name
        if path.exists():
            return path
    return None


def write_json(path: Path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")


def protect_input(source: Path, output: Path):
    if source.resolve() == output.resolve() or (output.exists() and os.path.samefile(source, output)):
        raise ValueError("Output aliases the input; refusing to replace source data")


def protect_media_input(source: Path, output: Path):
    """A CUE descriptor authorizes reads of a set, never writes to a BIN."""
    protect_input(source, output)
    if source.suffix.lower() == ".cue":
        for path in Cue(source).referenced_files.values():
            protect_input(path, output)


def boot(args):
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Boot output must be an empty directory")
    if args.image.suffix.lower() == ".chd":
        disc = Chd(args.image)
        tracks = [t for t in disc.tracks if t.type in ("MODE1", "MODE1_RAW")]
        if len(tracks) != 1:
            raise MediaError("Select a supported single-data-track disc for baseline boot discovery")
        if not args.libchdr:
            raise MediaError("CHD boot discovery needs --libchdr; see scripts/bootstrap_chd.py")
        track = tracks[0]
        with ChdReader(disc, args.libchdr) as reader:
            ipl = Ipl.parse(reader.sector(track, 1))
            validate_boot(ipl)
            # Boot-file coordinates are track-relative for this supported path.
            payload = b"".join(reader.sector(track, ipl.start_sector+n) for n in range(ipl.sector_count))
            transport = {"track": track.number, "disc_index1_lba": track.disc_start,
                         "chd_index1_frame": track.index1_frame,
                         "hunks_decompressed": reader.hunks_read,
                         "sector_coordinate": "relative to sole data track INDEX 01"}
    elif args.image.suffix.lower() == ".cue":
        disc = Cue(args.image)
        tracks = [t for t in disc.tracks if t.type in ("MODE1", "MODE1_RAW")]
        if len(tracks) != 1:
            raise MediaError("Select a supported single-data-track disc for baseline boot discovery")
        track = tracks[0]
        ipl = Ipl.parse(disc.sector(track, 1))
        validate_boot(ipl)
        payload = b"".join(disc.sector(track, ipl.start_sector+n) for n in range(ipl.sector_count))
        transport = {"track": track.number, "disc_index1_lba": track.disc_start,
                     "cue_index1_frame": track.file_index1, "cue_file": track.file,
                     "sector_coordinate": "relative to sole data track INDEX 01"}
    elif args.image.suffix.lower() == ".iso":
        reader = IsoReader(args.image)
        ipl = Ipl.parse(reader.sector(1))
        validate_boot(ipl)
        payload = b"".join(reader.sector(ipl.start_sector+n) for n in range(ipl.sector_count))
        transport = {"sector_coordinate": "relative to single-track ISO"}
    else:
        raise MediaError("Boot discovery accepts CHD, supported BIN/CUE or 2048-byte-sector ISO")
    mpr = tuple(ipl.report()["mpr"])
    # The loader can wrap banks in ways this milestone doesn't yet model.
    # Reject rather than map large programs through assumed MPRs.
    if ipl.load_address < 0x4000 or ipl.load_address+len(payload) > 0xE000:
        raise MediaError("Boot payload crosses unsupported loader/BIOS regions")
    if not ipl.load_address <= ipl.entry_address < ipl.load_address+len(payload):
        raise MediaError("IPL entry does not lie in the loaded program")
    segments = []
    occupied = set()
    for offset in range(0, len(payload), 1):
        logical = ipl.load_address+offset
        pa = (mpr[logical >> 13] << 13) | (logical & 8191)
        if pa in occupied:
            raise MediaError("Aliasing IPL load pages need a loader-aware profile; unsupported")
        occupied.add(pa)
        if not segments or pa != segments[-1][0]+len(segments[-1][1]):
            segments.append((pa, bytearray()))
        segments[-1][1].append(payload[offset])
    args.out.mkdir(parents=True, exist_ok=True)
    text = f"schema = 1\nmpr = {list(mpr)}\nentry_points = [{ipl.entry_address}]\n"
    for index, (pa, data) in enumerate(segments):
        name = f"boot-{index}.bin"
        (args.out / name).write_bytes(data)
        text += f'\n[[segments]]\nphysical = {pa}\nfile = "{name}"\nsha256 = "{hashlib.sha256(data).hexdigest()}"\n'
    (args.out / "snapshot.toml").write_text(text, encoding="utf-8")
    image_digest = disc.image_sha256() if args.image.suffix.lower() == ".cue" else sha256(args.image)
    result = {"schema": 1, "image_sha256": image_digest, "ipl": ipl.report(),
              "transport": transport, "payload_bytes": len(payload), "payload_sha256": hashlib.sha256(payload).hexdigest(),
              "scope": "boot-file extraction and explicit analysis snapshot; no BIOS execution or game boot"}
    write_json(args.out / "boot.json", result)
    print(json.dumps(result, indent=2))


def validate_boot(ipl):
    if not ipl.sector_count:
        raise MediaError("Embedded IPL execution (zero-sector programs) is not yet supported")
    if ipl.opening_mode:
        raise MediaError("IPL opening-mode media initialization needs a System Card loader; unsupported")
    if any(x > 7 for x in ipl.mpr_offsets):
        raise MediaError("Only standard CD RAM IPL mapping is supported in baseline extraction")


def hucard_snapshot(args):
    if args.out.exists() or args.out.is_symlink():
        raise ValueError('HuCard snapshot output must be a new directory')
    card = Cartridge(args.image, args.rom_header, args.rom_encoding, args.profile)
    mapped = card.mapped_rom()
    mapped_hash = hashlib.sha256(mapped).hexdigest()
    result = card.report() | dict(mapped_rom_sha256=mapped_hash,
                                 mapped_rom_bytes=len(mapped), runtime_abi=ABI,
                                 scope='HuCard reset source snapshot only; CFG discovery and execution remain separate')
    card.check_unchanged()
    args.out.mkdir(parents=True)
    (args.out/'mapped-rom.bin').write_bytes(mapped)
    snapshot = 'schema = 1\nmpr = [0,0,0,0,0,0,0,0]\n'+f'entry_points = [{card.reset_pc}]\n'
    for start, length in card.rom_ranges():
        data = mapped[start:start+length]
        name = 'mapped-rom.bin' if length == len(mapped) else f'rom-{start:06x}.bin'
        if name != 'mapped-rom.bin':
            (args.out/name).write_bytes(data)
        snapshot += (f'[[segments]]\nphysical = {start}\nfile = "{name}"\n'
                     f'sha256 = "{hashlib.sha256(data).hexdigest()}"\n')
    (args.out/'snapshot.toml').write_text(snapshot, encoding='utf-8')
    write_json(args.out/'cartridge.json', result)
    print(json.dumps(result, indent=2))


def physical_range(text):
    try:
        fields = text.split(":")
        if len(fields) != 2:
            raise ValueError()
        return tuple(int(field, 0) for field in fields)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected physical ADDRESS:LENGTH (decimal or 0x hexadecimal)") from None


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pcerecomp", description="Experimental PC Engine recompilation toolkit")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Report tool availability without installing anything")
    card = commands.add_parser('hucard', help='Create a private explicit-board HuCard reset source snapshot')
    card.add_argument('image', type=Path)
    card.add_argument('--out', type=Path, required=True)
    card.add_argument('--rom-header', choices=HEADERS, default='none')
    card.add_argument('--rom-encoding', choices=ENCODINGS, default='linear')
    card.add_argument('--profile', choices=PROFILES, default='base')
    inspect = commands.add_parser("inspect", help="Inspect CHDv5 or supported BIN/CUE metadata; no decompression needed")
    inspect.add_argument("image", type=Path)
    inspect.add_argument("--hash", action="store_true", help="Compute source SHA256s (complete-image identity for CUE); not CHD integrity verification")
    inspect.add_argument("--out", type=Path)
    toc = commands.add_parser("toc", help="Export bounded CD TOC metadata; no sectors or decompression")
    toc.add_argument("image", type=Path)
    toc.add_argument("--out", type=Path, required=True)
    load = commands.add_parser("boot", help="Extract bounded initial program into a private snapshot")
    load.add_argument("image", type=Path)
    load.add_argument("--libchdr", type=Path, default=library_default())
    load.add_argument("--out", type=Path, required=True)
    for name in ("analyze", "emit"):
        command = commands.add_parser(name, help="Analyze a pinned snapshot" if name == "analyze" else "Emit guarded native C++ from a snapshot")
        command.add_argument("snapshot", type=Path)
        command.add_argument("--limit", type=int, default=10000)
        command.add_argument("--follow-mappings", action="store_true",
                             help="Follow proven constant TAM mappings into context-qualified static analysis")
        command.add_argument("--context-limit", type=int, default=None,
                             help="Maximum distinct MPR contexts (1..4096, default 256); requires --follow-mappings")
        command.add_argument("--out", type=Path, required=True)
        if name == "analyze":
            command.add_argument("--listing", action="store_true")
    compose = commands.add_parser("compose-observations", help="Compose private original-ABI captures without relabeling execution evidence")
    compose.add_argument("inputs", nargs="+", type=Path)
    compose.add_argument("--out", type=Path, required=True)
    compose.add_argument("--capacity", type=int, default=65536,
                         help="Maximum union identities (1..65536); excess refuses without truncation")
    for name in ("emit-capture", "emit-profile"):
        capture = commands.add_parser(name, help="Emit guarded native C++ from a private capture or observation profile")
        capture.add_argument("capture", type=Path)
        emission_arguments(capture)
    args = parser.parse_args(argv)
    return run_command(args)


def emission_arguments(capture):
    """Identical guarded-emission options for single captures and profiles."""
    capture.add_argument("--out", type=Path, required=True)
    capture.add_argument("--exclude-range", type=physical_range, action="append", default=[],
                         help="Exclude any instruction touching physical ADDRESS:LENGTH; repeat at most 256 times")
    capture.add_argument("--partition-size", type=int, default=256,
                         help="Balanced-layout target identities per unit (1..4096; same-PC variants stay together)")
    capture.add_argument("--partition-layout", choices=("balanced", "stable"), default="balanced",
                         help="Stable keys each unit by full MPR mapping and fixed 256-byte logical-PC range")
    capture.add_argument("--single-unit", action="store_true",
                         help="Emit one translation unit for controlled build comparisons")
    capture.add_argument("--native-span", action="store_true",
                         help="Add opt-in per-instruction native span dispatch; requires stable layout")


def run_command(args):
    try:
        if args.command == "doctor":
            print(json.dumps({"version": __version__, "python": sys.version.split()[0],
                              "tools": {name: shutil.which(name) for name in ("cmake", "ninja", "clang++", "git")},
                              "libchdr": str(library_default()) if library_default() else None,
                              "status": "development foundation; no playable games certified"}, indent=2))
        elif args.command == 'hucard':
            hucard_snapshot(args)
        elif args.command == "inspect":
            report = (Cue(args.image) if args.image.suffix.lower() == ".cue" else Chd(args.image)).report(args.hash)
            if args.out:
                protect_media_input(args.image, args.out)
                write_json(args.out, report)
            print(json.dumps(report, indent=2))
        elif args.command == "toc":
            protect_media_input(args.image, args.out)
            descriptor = Toc.from_image(args.image).text()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(descriptor, encoding="ascii", newline="\n")
            print(descriptor, end="")
        elif args.command == "compose-observations":
            if args.out.exists() or args.out.is_symlink():
                raise ValueError("Observation composition requires a new output file")
            for source in args.inputs:
                protect_input(source, args.out)
            profile = compose_observation_profile(args.inputs, capacity=args.capacity)
            raw = (json.dumps(profile, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
            if len(raw) > MAX_PROFILE_BYTES:
                raise ValueError("Serialized observation profile exceeds its byte bound")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("xb") as stream:
                stream.write(raw)
            print(json.dumps({"format": profile["format"], "sha256": hashlib.sha256(raw).hexdigest(),
                              "inputs": len(profile["inputs"]), "identities": len(profile["observations"]),
                              "execution_evidence": False}, indent=2))
        elif args.command in ("emit-capture", "emit-profile"):
            loader = load_capture if args.command == "emit-capture" else load_observation_profile
            emitter = emit_capture if args.command == "emit-capture" else emit_observation_profile
            capture, digest = loader(args.capture)
            print(json.dumps(emitter(capture, args.out, digest, exclude_ranges=args.exclude_range,
                                          partition_size=args.partition_size, single_unit=args.single_unit,
                                          partition_layout=args.partition_layout, native_span=args.native_span), indent=2))
        elif args.command == "boot":
            boot(args)
        else:
            if args.context_limit is not None and not args.follow_mappings:
                raise ValueError("--context-limit requires --follow-mappings")
            result = analyze(Snapshot.load(args.snapshot), args.limit,
                             follow_mappings=args.follow_mappings,
                             context_limit=256 if args.context_limit is None else args.context_limit)
            if args.command == "emit":
                print(json.dumps(emit(result, args.out), indent=2))
            else:
                protect_input(args.snapshot, args.out)
                write_json(args.out, result)
                if args.listing:
                    for item in result["instructions"]:
                        prefix = ("MPR=" + ",".join(f"{bank:02X}" for bank in item["mpr"]) + " "
                                  if result["schema"] == 2 else "")
                        print(prefix + listing(Instruction(item["pc"], tuple(item["physical"]), tuple(item["data"]), item["mnemonic"], item["mode"], item["target"])))
                print(json.dumps(result["summary"], indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"pcerecomp: {exc}", file=sys.stderr)
        return 2
