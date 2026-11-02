# Independent RomAtlas decoder check

The optional `scripts/romatlas_reference.py` builds an isolated executable from
original [RomAtlas decoder source](https://github.com/weisserw/romatlas/blob/3d0d1393149491777626f5a8e4461f7c49b2d6df/crates/romatlas-pce/src/decode.rs)
at revision `3d0d1393149491777626f5a8e4461f7c49b2d6df` and its original vendored
HuC6280 core. The public adapter is authored synthetic test infrastructure;
original GPL code and its executable remain separate from the toolkit runtime.
No game image, BIOS, retail instruction bytes or consumer SDK is required.

```sh
python scripts/romatlas_reference.py --source ROMATLAS_CHECKOUT --out .local/romatlas-reference
```

The output directory must be new and private. Rust/Cargo and the dependencies
in the pinned upstream lock must already be available. Cargo metadata/build
run offline; no dependency installation or download is implicit. The driver
resolves and hashes the actual tools, disables compiler wrappers, authenticates
original Git blobs, and checks host dependency archives and unpacked source
against the original lock before building. Verbose build commands, input/output
bytes and source/artifact preservation remain part of the receipt.

## Actual comparison

The final run has **25,221 records**:

- **24,480 exact full decoder matches** in a matrix covering all 256 opcode
  slots, eight PC positions, three complete MPR layouts and four operand patterns.
- **96 explicitly named BRK signature-length differences** and one lone-BRK
  acceptance difference in the original frontend.
- **548 exact truncation/invalid-input refusals**.
- **96 separate original-core instruction calls** for authored NOP, immediate
  LDA, absolute JMP and BRK, with mapped bus reads, stack writes and registers.

The decoder comparison checks lengths, textual operands, assembly availability,
successors, control/memory/block references and mapping-context changes.
It includes cross-page/wrapped PC cases and signed branch extrema. Original
response identity/shape/types and record counts must match. Unknown differences
fail the check; known differences retain their exact fields and counts.

RomAtlas's frontend describes BRK as one byte and accepts a missing signature.
The toolkit decodes its two-byte encoding. The original HuC6280 core advances
the return PC by two and exposes the signature read and stack bytes in the
separate bounded CPU probe. The frontend discrepancy is retained; the runtime
is not changed to reproduce it. Bus-phase behavior and the toolkit's existing
Gear-based BRK access profile retain their separate verification scope.

RomAtlas's decoder itself does not return physical fetch addresses. Physical
address evidence comes from the original core's actual `BusInterface` callbacks,
compared with independent authored expectations and the toolkit's mapping.
The CPU adapter refuses every opcode outside its four-instruction authored set
and bounds operations; it never invokes the reference core's illegal-opcode
fallback as a successful toolkit result.

## Dependencies and scope

All 51 resolved registry entries retain versions/checksums from the original
lock. On the tested Windows host, 33 actual host packages have verified archives
and 1,549 source/cache files; 18 non-host entries are not claimed downloaded,
source-verified or built. Original source/license inputs and byte-identical
compiled crate copies are also pinned. Initial build-plumbing failures are
preserved separately from the successful final run.

These are decoder and narrow original-core functional checks. They execute
zero toolkit native/interpreted guest instructions. They do not qualify CPU
timing, T/decimal arithmetic, devices, all reference-core opcodes, physical
hardware, a retail game or campaign. RomAtlas's current image frontend remains
[HuCard-only](https://github.com/weisserw/romatlas/blob/3d0d1393149491777626f5a8e4461f7c49b2d6df/docs/pce.md).
Using its explicit-byte decoder does not establish CD image support.
