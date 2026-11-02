# Native discovery reports

`native-gaps` joins complete instruction captures to the declared emitted
identities of an observed native module. It helps batch missing variants and
choose useful test windows without repeatedly building or replaying an already
admitted prefix. It does not select a consumer package or qualify execution.

Run from the pinned diagnostic toolkit checkout:

```sh
python -m pcerecomp native-gaps MODULE/module.json DISCOVERY.json --observations PROFILE.json --out .local/native-gaps.json
```

Supply more capture paths after the manifest to inspect several windows.
`--observations` is the exact original capture or composed profile recorded in
the module manifest. The output must be a new file; it is never overwritten.
Invalid input does not create an output directory. The full report contains
instruction bytes and must remain private. Console JSON contains compact
counts and input digests, with no instruction bytes or absolute source paths.

## What the catalog establishes

The named `observed-abi28-29-v1` selection contract supports the byte-identical
ISA/emission selection of the known ABI 28 and ABI 29 observed emitters.
It authenticates the original input hash/provenance and every listed generated
source/header artifact, checks layout and exact selection counts, and applies
physical exclusions to every fetched instruction byte. Unsupported observations
are separate from emitted instructions. Balanced, single-unit, stable and
opted-in native-span layouts retain their declared contracts.

This reconstructs **declared emitted membership**. Hash-bound generated files
and a self-describing manifest do not independently establish producer authorship,
C++ semantics, successful compilation, linkage or instruction execution.
Those remain the consumer's build and qualification obligations. Static-only
manifests and unknown selection contracts refuse explicitly. Original capture
ABIs are preserved; a later-ABI input cannot be backdated into an older module.

The loader checks the exact admitted ISA/emitter selection hashes and native
opcode set. A future selection change requires a separately reviewed contract;
it is not permission to reinterpret historical module membership silently.

## Reading the report

Full identity means logical PC, all eight MPRs, every mapped physical fetch
address and exact bytes. Different operands or an otherwise unused MPR still
produce distinct identities. Logical wrapping and cross-page operands remain
explicit. Nothing is inferred from live RAM, a physical bank interval or a
live TCP row number.

| Category | Meaning |
|---|---|
| `emitted` | Exact identity appears in the admitted declared emitted set |
| `excluded` | Identity is excluded, including a newly seen instruction whose operand touches a configured excluded physical range |
| `unsupported` | The selected translator does not support the encoding; it is not an automatic compile candidate |
| `uncompiled` | Supported observed identity is absent from the declared emitted set and outside exclusions |
| `emitted_unexercised` | Declared emitted identity is absent from the provided captures; this is a window-relative observation |

An emitted identity with interpreted hits can be historical evidence from an
older package. Native hits outside this catalog can come from a different
module selection. Neither alone establishes a dispatch defect. Keep the exact
producer/package and window relation when investigating either case.

Each input retains its original SHA256, size, ABI, checkpoint origin and
native/interpreted counts. Imported checkpoint counters are not added to its
new-window observations. Catalog historical hits are not borrowed as new work.
Byte-identical inputs are deduplicated by digest, preserving basename aliases.
The identity union is deterministic regardless of input order.

Different captures can overlap. The report deliberately supplies **no combined
retirement count, campaign percentage or cross-input hotness sum**. Each input's
`uncompiled_by_interpreted_hits` ranks its own missing identities by interpreted
hits, then full identity; zero-interpreted entries remain visible at the bottom.
Join an independently proved nonoverlapping route outside this diagnostic if a
consumer needs execution totals.

Inputs require strict duplicate-free integer JSON, valid complete lossless
captures and bounded positive hit counts. Existing admission limits are
256 input occurrences, 64 MiB of distinct raw capture content and 65,536 union
identities. Catalog/profile/artifact admission has its own explicit bounds.
Source files are rehashed before returning, including distinct aliases and
same-size, restored-timestamp changes. Schema consistency and content stability
do not establish process closure or genuine execution by themselves.

## Python interface

```python
from pathlib import Path
from pcerecomp.native_catalog import load_native_catalog
from pcerecomp.native_gaps import report_native_gaps

catalog = load_native_catalog(Path("module/module.json"), Path("profile.json"))
report = report_native_gaps(catalog, [Path("discovery.json")])
assert report["qualification"] is False
```

These are offline diagnostics. They neither import a consumer's old SDK nor
execute its emitter, generated source or game. A consumer can pin the diagnostic
separately from its execution producer, including an unchanged ABI 28 package.
No runtime ABI or checkpoint compatibility is changed by adopting this report.

## Evidence and next interface

Authored tests independently check byte/MPR variants, wrapped physical fetches,
operand exclusions, unsupported encodings, tier counts, duplicate aliases,
overlapping windows, source mutation, malformed metadata and exclusive CLI output.
Current-emitter fixtures cover all supported layout modes.

The real Ys III comparison reconstructs the 58,039-identity baseline and
58,041-identity candidate from their exact profiles/manifests and 948 artifacts
each. The same closed discovery capture reports two missing variants against
the baseline and none against the candidate. Its original two interpreted
retirements remain two in both reports. This demonstrates catalog/discovery
integration; it does not demonstrate execution of those candidate translations.

Authenticated paused physical-snapshot export remains separate planned work.
Use [native discovery guidance](NATIVE_DISCOVERY.md) for the existing bounded
mapping-aware analyzer and the required contemporaneous source provenance.
