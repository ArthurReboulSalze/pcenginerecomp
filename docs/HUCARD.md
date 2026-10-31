# HuCard startup and mapper profiles — ABI 19

HuCard and System Card startup are distinct hardware recipes. The base HuCard
profile maps a supplied cartridge ROM, initializes the named deterministic
reference state, reads its actual reset vector and executes guest code. It
supplies no BIOS, preloaded program, forced PC or firmware service.

## Explicit ROM input

```sh
build/pce-headless --hucard-reset base cartridge.pce 100000 30000000 hybrid --rom-header none --rom-encoding linear --video-output continuous
```

The SDL host accepts the same grammar and ordinary input, audio, TCP, capture
and limit options. All eight initial MPRs are zero; the vector at ROM offsets
`$1FFE/$1FFF` selects the logical entry. Initial A/X/Y/SP are zero, P is `$04`,
speed divisor is 12 and clocks are zero under `gear-deterministic-zero-v1`.
This is a reproducible emulator-reference policy, not an electrical power-on
or warm-reset claim. Startup metadata reports this initial state separately
from the final CPU and executed native/interpreted counts.

Dump interpretation is explicit:

| Option | Values | Meaning |
|---|---|---|
| `--rom-header` | `none` (default), `copier512` | Preserve all bytes, or skip exactly 512 opaque header bytes |
| `--rom-encoding` | `linear` (default), `bit-reversed` | Use each ROM byte directly, or reverse its eight bits independently |

There is no size-based header detection, padding, region-based conversion or
checksum database. Both options are rejected outside HuCard startup. Decoded
ROM data must match the explicitly selected profile below. The raw input hash
includes any declared header; decoded ROM identity is recorded separately.
Tests cover conversion independently. Gear comparisons use already decoded
authored ROMs and do not establish the dump-conversion policy.

## Selected memory map

| Profile | Decoded ROM size | Additional hardware |
|---|---|---|
| `base` | 8 KiB aligned, 8 KiB through 1 MiB | Selected standard ROM mirrors |
| `sf2` | Exactly 2.5 MiB | Four-bit address latch and switched 512 KiB ROM window |
| `populous` | Exactly 512 KiB | Volatile 32 KiB cartridge RAM |

Select the profile with `--hucard-reset PROFILE` or consumer `[boot].profile`.
The analysis frontend uses `hucard --profile PROFILE`. A large image does not
automatically select a mapper; a base-profile image over 1 MiB is refused.

### Base ROM map

ROM occupies physical banks `$00..$7F`. Storage aliases resolve to the original
ROM bank, while code captures and native guards retain the mapped physical
address, logical PC, full MPR context and exact instruction bytes.

| Decoded ROM | Physical bank `b < $40` | Physical bank `b >= $40` |
|---|---|---|
| 384 KiB / 48 banks | `b & $1F` | `$20 + (b & $0F)` |
| 512 KiB / 64 banks | `b & $3F` | `$20 + (b & $1F)` |
| 768 KiB / 96 banks | `b & $3F` | `$40 + (b & $1F)` |
| Other supported sizes | `b % ROM_bank_count` | `b % ROM_bank_count` |

This is the selected Geargrafx/Mesen standard compatibility map. In particular,
512 KiB cartridges have multiple physical board layouts; these formulas do
not certify a unique hardware decode. Loader patches advance every affected
ROM-alias generation, and native execution still checks current source bytes.

Banks `$F8..$FB` mirror one 8 KiB work RAM. Bank `$FF` routes base VDC/VCE,
PSG, timer, interrupt and controller ports. There is no CD RAM at `$80..$87`,
BRAM at `$F7`, CD transport or ADPCM. Absent memory reads return `$FF`; ROM and
absent-memory writes are ignored. HuCard `$1800..$1FFF` reads return `$FF` and
writes preserve the I/O latch. The controller's CD-absent bit is set. Base
PSG-only digital audio uses the existing mixer without enabling CD hardware.

`base` is an explicit board declaration. SuperGrafx and CD add-ons remain
unsupported by HuCard startup. [Arcade Card Duo](ARCADE_CARD.md) is a separate
optional Super System Card expansion. The tool does not infer requirements from a title or CRC.
Existing unsupported video/bus semantics still fault explicitly.

### SF2 bank switching

Physical banks `$00..$3F` expose the first 512 KiB. Banks `$40..$7F` expose
one of the four following 512 KiB blocks. A guest write to physical bank `$00`
at offsets `$1FF0..$1FFF` stores `address & 15`; data is ignored. The selected
block is that latch modulo four. Writes elsewhere retain normal ROM-write
behavior. All sixteen addresses matter, including aliases `$1FF4..$1FFF`.

The initial latch is zero. Setup-only `power_on_cpu` refuses a nonzero latch
before changing the CPU; this is not a warm-reset implementation. Host startup
reports initial `mapper_latch = 0` separately from live cartridge diagnostics.

The bus retains the full 2.5 MiB ROM and a mapped 1 MiB physical view without
widening the 21-bit guest address space. Changing the effective block refreshes
the switched window and advances its 64 bank generations. A different raw
latch selecting the same block does not invalidate unchanged bytes. Guest and
native source peeks see the new window immediately. Loader writes patch the
currently mapped file bytes and survive switching away and back; they do not
interpret file offsets beyond the guest address space as physical addresses.

### Populous cartridge RAM

Physical banks `$40..$5F` overlay four 8 KiB RAM pages repeated eight times:
canonical page is `$40 + (bank & 3)`. The 32 KiB is separate from ROM backing;
ROM windows `$60..$7F` continue to expose file banks `$20..$3F`. Default cold
setup fills cartridge RAM with zero; the low-level API accepts an explicit
fill byte. No file persistence, battery retention or owner save is implicit.

Guest writes, block transfers, loader writes, pure source peeks and paused
debug-memory access share the same aliases. A changed RAM byte advances all
eight alias generations. Loader writes retain the per-touched-bank convention.
The optional debug compare-and-write preflights the entire request and accounts
for every alias. Normal qualification keeps memory editing disabled.

### Native source identity and state compatibility

ABI **19** introduced the board, raw mapper latch and retained full ROM state.
ABI **20** introduced the optional Arcade expansion; ABI **21** added the
stopped timer phase. ABI **22** added pending CD sense state without attaching
CD hardware to HuCard recipes; the current runtime is ABI **25**. Retained
captures keep their original labels; re-emit for the current ABI and rebuild.
These board upgrades did not introduce a serialized save-state format. Later
exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve profile,
latch, cartridge RAM, patched immutable ROM identity and selected-window
consistency alongside CPU/device state. Cross-build migration remains
unimplemented.

A bank or logical PC alone cannot identify switched code. Guards continue to
check logical PC, all MPRs, original mapped physical fetch addresses and exact
current bytes before mutation. Observed-code modules can contain multiple
byte variants at the same PC/MPR/physical address. An unseen selected variant
must miss explicitly; source generations are not permission to skip guards.

## Analysis and native promotion

```sh
python -m pcerecomp hucard cartridge.pce --profile base --out .local/new-hucard --rom-header none --rom-encoding linear
python -m pcerecomp analyze .local/new-hucard/snapshot.toml --out .local/hucard-analysis.json
```

The first command writes private `mapped-rom.bin`, `snapshot.toml` and
`cartridge.json` with raw/decoded/mapped hashes, the selected map and reset
vector. Its output directory must be new. It neither boots a game nor treats
every ROM byte as executable. CFG discovery begins only at the vector; TAM
and unresolved indirect control flow retain their normal barriers.
For SF2 this is only the initial latch-zero view, not discovery of all switched
code. Populous snapshots omit RAM-overlaid ranges from source segments;
zero holes in the mapped inspection file are not invented executable ROM.

For actual mapping contexts observed during bounded execution:

```sh
build/pce-headless --hucard-reset base cartridge.pce 100000 30000000 hybrid --code-capture .local/hucard-observed.json --capture-limit 65536
python -m pcerecomp emit-capture .local/hucard-observed.json --out .local/hucard-module
```

Captures and translated source contain cartridge code and remain private.
Emission is separate from compilation and execution. Guard misses, unseen
source and unsupported semantics remain visible; a sampled route does not
establish full-game native coverage.

## Consumer schema 1

Keep the usual pinned `[tool]`, `[module]`, `[runtime]` and `[limits]` tables.
Use runtime ABI **22**, a matching rebuilt module, and this startup recipe:

```toml
[boot]
mode = "hucard-reset"
profile = "base"
header = "none"
encoding = "linear"

[cartridge]
path = "private/cartridge.pce"
sha256 = "RAW_FILE_SHA256"
```

`[payload]`, BIOS, disc/TOC/libchdr and BRAM assets conflict with this recipe.
`runtime.cd_unknown_status` must be `fault`; normal audio and input-script
settings remain available. Verification pins the raw file and independently
checks typed initial metadata against the decoded vector and declared profile.
The runtime cannot attach CD/ADPCM to any configured HuCard profile.

Retained ABI-12 through ABI-26 observations remain valid offline inputs with
their original labels. Re-emit for current ABI 27 and rebuild the module and
runtime; old binary objects are incompatible with the current bus/guest-write contract. Snapshot and System
Card recipes retain their startup contracts. No persistent save/state
migration, live installation or owner-save discovery is introduced.

See [enhanced mapper reference scope](REFERENCE.md#enhanced-hucard-mappers---abi-19),
[consumer builds](CONSUMER.md) and [current verification](STATUS.md).
