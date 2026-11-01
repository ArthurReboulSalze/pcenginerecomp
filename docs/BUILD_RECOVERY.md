# Verified interrupted-build recovery

Consumer builds can opt into recovery **before the first configure**. The first
supported producer is Windows 10/11 x64, LLVM-MinGW and Ninja, using the same audited
toolchain/SDK closure as the [package cache](BUILD_CACHE.md). Ordinary builds,
package-cache builds and [managed module updates](INCREMENTAL_BUILDS.md) retain
their separate contracts. Recovery does not change runtime ABI 28 or guest
semantics.

## Start and resume

Use a pinned consumer descriptor, a new build directory, an explicit complete
LLVM-MinGW bundle and explicit SDK roots. Put that bundle's `bin` on PATH so the
selected CMake also belongs to the bundle. For example, in PowerShell:

```powershell
$env:PATH = "$llvm/bin;$env:PATH"
python -m pcerecomp.project build game.toml --build-dir build-recoverable `
  --recoverable --generator Ninja --desktop `
  --recovery-toolchain-root $llvm --recovery-dependency-root $sdl `
  "--cmake-arg=-DCMAKE_CXX_COMPILER=$llvm/bin/clang++.exe" `
  "--cmake-arg=-DCMAKE_MAKE_PROGRAM=$llvm/bin/ninja.exe" `
  "--cmake-arg=-DSDL3_DIR=$sdl/lib/cmake/SDL3"

# After an interruption, with the original descriptor, paths and inputs:
python -m pcerecomp.project resume game.toml --build-dir build-recoverable
```

Set `$llvm` and `$sdl` to the actual complete bundle and target SDL SDK root.
For a headless build omit `--desktop`, the SDL root and `SDL3_DIR`. Only explicit
compiler, Ninja and SDL package path definitions are accepted. Ambient compiler
flags, external search paths, toolchain files, unsupported graphs/profiles and
combining recovery with package-cache options are refused. Resume restores the
original options; it does not reconfigure or admit a new descriptor/toolchain.

## What is verified

Before configure, an immutable contract binds the descriptor, toolkit identity,
module bytes, complete declared toolchain/SDK trees, paths, host and controlled
environment. A completed configure then seals the effective CMake File API
model, generated inputs, raw cache and Ninja graphs. Automatic CMake
regeneration is disabled for this producer.

Compilation runs actual audited C++ object targets in groups of 32. Each
completed group gets an atomically published, flushed checkpoint containing
object content hashes and actual Ninja compiler-dependency records. Checkpoints
form an immutable content-hash chain. Each checkpoint stores at most 32 new or
rebuilt object records; replay assembles the ledger without repeatedly storing
its complete history. Writer and reader enforce the same 64 MiB per-record
bound. Durable attempt admissions invalidate missing sealed objects before
cleanup. Those objects stay unsealed across further interruptions, including
attempts that commit no object checkpoint, until a replacement record commits.
These are build-artifact checkpoints,
separate from [guest developer checkpoints](DEVELOPER_CHECKPOINTS.md).

Resume checks the full input/configuration closure, metadata, safe paths,
exclusive ownership, object hashes and dependency records before removing any
unsealed output. Matching sealed objects are retained. Missing sealed objects
are rebuilt and reported; changed sealed objects are an integrity error.
Completed objects from an interrupted, unsealed group are rebuilt. Archives
and executables are freshly linked; packaged DLLs must match the declared
toolchain/SDK bytes. Interrupted Clang atomic-output temporaries are recognized
only beside an audited object with the exact target stem, eight hexadecimal
characters and `.obj.tmp` suffix; they are discarded after admission, never
reused. The receipt records their path, target, size and hash. This naming is
checked against [LLVM's output implementation](https://github.com/llvm/llvm-project/blob/llvmorg-22.1.8/llvm/lib/Support/VirtualOutputBackends.cpp).
Only audited artifact paths are removed. Foreign
files/directories, links, hardlinks and malformed metadata refuse recovery.

The Windows launcher assigns compiler processes to a non-breakaway job
atomically at process creation. A separate source-only guardian retains the
exclusive directory lease after CLI termination until the owned process tree
has exited. Recovery does not infer compiler termination from an abandoned
lock file or a missing named job. Cleanup failure quarantines the directory
and blocks automatic recovery; preserve it for review and use a new build
directory. There is no unmanaged subprocess fallback.

Success creates a new ordinary build receipt with attempt, contract, checkpoint,
retained/recompiled object and input-audit provenance. It explicitly records
`execution_evidence: false`. Run the official consumer command and qualify its
own TCP/checkpoint behavior separately; compilation never proves gameplay.

## Refusals and boundaries

- A directory originally built without `--recoverable` has no trusted recovery
  contract. Preserve its logs and build in a new directory.
- An interrupted configure has no complete configured seal and cannot resume.
  A finished build cannot be resumed, including after deleting its receipt.
- Source, module, SDK, toolchain, options, environment, configuration or path
  changes require a new build. Restoring a different Git revision with similar
  files is not an exception to the descriptor's pin.
- A busy directory is refused while its guardian drains. Retry after that
  process has finished; do not delete locks or kill unrelated processes.
- Preserve failed attempts and original metadata. Do not edit checksums,
  checkpoints or quarantine markers to manufacture eligibility.

This is a consistency/recovery protocol for trusted build sources and ordinary
filesystem ownership, not a sandbox for arbitrary CMake code or authentication
against an actor controlling the files, guardian or OS. Flushed atomic records
detect incomplete or inconsistent surviving data; they do not guarantee that
a storage device honors power-loss durability. Unsupported hosts and compiler
profiles have no recovery qualification.

The public authored integration fixture performs two real parent interruptions
during later compilation, independently observes owned descendant termination,
tests unchanged-size/timestamp input and artifact corruption, resumes through
the public CLI and executes translated code through the official consumer
runner. Retail media, saves, generated game code and TCP captures remain
private. The qualified interruption point is object compilation after a durable
group; final archive/executable links are subsequently executed and checked.
See [current verification status](STATUS.md).

The complete self-contained LLVM-MinGW test profile performs real native
builds and deliberate process interruptions. Use
`python scripts/check.py --python-timeout 1800` for that complete suite;
the finite deadline covers compilation and recovery tests, and is independent
of guest execution limits.
