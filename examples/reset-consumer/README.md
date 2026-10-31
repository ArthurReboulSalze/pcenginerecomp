# Authored reset-vector consumer

This example creates an entirely authored 256 KiB System Card image and a
direct C++ native module. Its actual reset vector at physical `$1FFE` selects
logical `$E000`, where a five-byte program loads A with 41, increments A, and
loops. No firmware, disc, extracted program, saved state or download is used.

From a committed toolkit checkout with Python 3.11+, CMake 3.20+ and a C++20
compiler:

```sh
python examples/reset-consumer/prepare.py .local/reset-consumer
python -m pcerecomp.project verify .local/reset-consumer/project.toml
python -m pcerecomp.project build .local/reset-consumer/project.toml --build-dir .local/reset-consumer-build
python -m pcerecomp.project run .local/reset-consumer/project.toml --build-dir .local/reset-consumer-build --receipt .local/reset-consumer-run.json
```

Preparation requires a new output directory. `--tool-root PATH` selects the
exact source checkout to pin and use for generation; `--profile super` selects
Super System Card memory instead of the default Standard profile. The strict
schema-1 descriptor uses `[boot]` and a hashed `[bios]`, with no `[payload]`,
load address, caller-supplied PC or initial MPR mapping. The descriptor and capture checks use the selected toolkit's current ABI (27).
Original capture producer labels remain unchanged; promotion requires the
current ABI for this authored execution proof.
The official consumer interface supports headless and optional SDL desktop
hosts; see [the consumer contract](../../docs/CONSUMER.md) for build and TCP
options.

The expected result is **200 native / zero interpreted instructions**, A = 141,
X = Y = SP = 0, PC = 57347 (`$E003`), and 7,176 master ticks. One two-cycle
LDA, 100 two-cycle INA instructions, and 99 four-cycle BRA instructions total
598 CPU cycles at the initial low-speed divisor of 12. Reset metadata retains
the initial PC `$E000`, rather than replacing it with the final PC.

The deterministic `gear-deterministic-zero-v1` initialization chooses zero
for otherwise undefined register/RAM/MPR state, sets P = 4, and starts the CPU
at low speed. It deliberately does not format BRAM; no BRAM image is attached
by this example. These choices support reproducible reference comparisons;
they are not a claim that physical hardware always powers on with zeros.

This is a synthetic reset-vector and native consumer proof. A successful run
does not qualify real System Card firmware, a CD boot, or a complete game.
Generated code/capture snapshot terminology retains its existing meaning:
the snapshot describes source identity for compilation, while `[boot]`
selects how the runtime starts the console.

## Capture mappings that a fixed CFG cannot discover

The second authored fixture changes MPRs during execution. It maps MMIO and
work RAM itself, moves the executing ROM through mirror banks `$20` and
`$40`, changes CPU speed, writes/increments/reads a RAM byte, then loops.
The compiler needs the actual retired contexts after those mapping changes;
a reset entry point alone does not discover them.

Use a headless runner built from the selected toolkit checkout. This example
first executes exactly 200 interpreted instructions, then validates and
promotes that actual capture:

```sh
python examples/reset-consumer/capture.py capture .local/reset-captured --runner build/pce-headless
python examples/reset-consumer/capture.py promote .local/reset-captured
python -m pcerecomp.project verify .local/reset-captured/project.toml
python -m pcerecomp.project build .local/reset-captured/project.toml --build-dir .local/reset-captured-build
python -m pcerecomp.project run .local/reset-captured/project.toml --build-dir .local/reset-captured-build --receipt .local/reset-captured-run.json --code-capture .local/reset-captured-native.json
```

Use executable suffixes on Windows. Both helper commands accept `--tool-root`;
capture accepts `--profile super` for Super hardware. The resulting descriptor
selects **native-only** execution. Add the consumer build's `--desktop` and
selected SDL package path to qualify that host separately. This workflow
explicitly disables PCM output in both capture and replay, keeping this
CPU/mapping proof separate from audio qualification. It validates recorded
successful exit, exact argv/profile/capacity, and retained stdout/stderr hashes
before promotion. This workflow
records the selected runner's hash; it does not authenticate its build or
substitute for independent emulator comparison.

The expected capture contains **16 instruction identities in five complete
MPR contexts**. The same ROM storage is fetched at mapped physical addresses
in banks `$00`, `$20` and `$40`; those addresses remain distinct identities.
Each fresh native replay must retire **200 native / zero interpreted
instructions**, end at PC `$E01D` with A = 64, X = 149, Y = SP = 0 and P = 132,
and preserve work RAM `$2000` = 56. MPR0 = `$FF`, MPR1 = `$F8`, MPR7 = `$40`;
the other MPRs remain zero. The guest takes **610 CPU cycles / 2,037 master
ticks** under the toolkit's documented CSH transition rule. These values
include fourteen setup instructions followed by 93 INX/BRA pairs. INC absolute
takes seven cycles; CSH's final cycle runs at the selected higher speed.

Promotion checks the actual PC, all eight MPRs, physical fetch addresses,
instruction bytes, tier hit counts and retained input/source pins before
creating a module or descriptor. It refuses incomplete/dropped/unreadable
captures and preserves previous outputs. The helper intentionally recognizes
only this authored program. For arbitrary privately supplied firmware, use
the general [capture interface](../../docs/CODE_CAPTURE.md), retain its exact
source provenance, and qualify the resulting module against its own route.
Emission alone remains separate from compilation and native execution.
