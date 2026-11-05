# Sources and dependency terms

The original compiler/runtime code is MIT licensed. No SNESRecomp,
PSXRecomp, Mesen, Mednafen, HuC, or N64Recomp implementation is vendored or
linked into the baseline runtime. Architecture research does not change the
licenses of those projects.

The opcode/mode matrix in `pcerecomp/isa.py` follows the instruction facts and
layout of MAME's `src/devices/cpu/h6280/6280dasm.cpp`, checked at commit
`da9333a2a5123012a939e78c3f2df7175ea7d100`. Its attribution and BSD terms are
retained in [licenses/MAME-HuC6280.txt](licenses/MAME-HuC6280.txt).
Execution bodies were written for this project; the MAME CPU implementation
is not included.

CHD decompression is optional and uses a separately acquired **libchdr** at
`47d794151b2b64f6aba60304e6480f4f5a2bc24b` (BSD-3-Clause). Its bundled LZMA,
miniz, zstd and dr_flac dependencies keep their own notices. The source and
binary stay in ignored `.deps/` when the opt-in bootstrap script is used.
Any future binary distribution including this dependency must carry its
actual dependency notices. The baseline source repository ships no libchdr
binary or source archive.

The optional desktop host links a separately supplied **SDL3** SDK (zlib
license). The tested Windows x64 SDK is 3.4.18; default headless builds do
not require SDL. SDL source and binary archives remain in ignored `.deps/`.
The upstream license is retained in [licenses/SDL3.txt](licenses/SDL3.txt).
A binary distribution including SDL3 must preserve that notice and any
applicable dependency notices. No SDL binary is published in this repository.

Windows consumer packaging also collects the selected toolchain's linked
non-system runtime DLLs. For example, the tested LLVM/MinGW toolchain requires
libc++ and libunwind. These remain third-party binaries under their actual
upstream terms; a distributor must carry the applicable runtime notices.
The package builder does not fetch libraries or grant redistribution rights,
and this source repository contains no compiler-runtime DLLs. Dynamic modules
explicitly supplied as media dependencies are separate from linked imports.

The optional independent-reference harness controls a separately supplied
Geargrafx executable (GPL-3.0) through its MCP interface. The emulator is not
linked into this runtime or redistributed in this source repository. Use a
dedicated portable instance under `.deps/`; its own license remains in force.

The optional [HuC6280 vector adapter](docs/HUC6280_VECTORS.md) reads the
**SingleStepTests/huc6280** test corpus (MIT, Copyright (c) 2025 SingleStepTests)
at commit `4ce378e04e243437e6f74dfe76c3cb7c70e45bf1`. The vectors were generated with
Mesen (GPL-3.0); they are numeric test data only, fetched on demand into an ignored
folder and verified against `tests/huc6280_vectors.sha256`. No Mesen code, table or
binary is vendored, linked or executed. The notice is retained in
[licenses/SingleStepTests-huc6280.txt](licenses/SingleStepTests-huc6280.txt).

SNESRecomp and PSXRecomp currently use PolyForm Noncommercial 1.0.0.
N64Recomp uses MIT; N64ModernRuntime and Mesen use GPL terms. They are
research references, not an interchangeable pool of MIT code. See the
revision-linked [research register](docs/RESEARCH.md).

Disc images, System Card firmware, generated game translations, extracted
assets, traces containing code, and owner save data are not part of this
repository or covered by its license. No game compatibility or distribution
rights are implied by a successful build.
