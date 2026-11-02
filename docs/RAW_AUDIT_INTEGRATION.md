# Integrating closed raw audits in a consumer project

A consumer's qualification combines protocol evidence, its exact executable
and inputs, saved machine state, retired source identities and the declared
comparison relation. Each layer needs its own evidence. A matching summary
or a completed metadata preflight cannot grant execution qualification.

## Shared pure relations

`scripts.dev_audit_relation` provides a file-free, guest-free layer for
same-ABI consumer adapters:

| Helper | Declared relation |
|---|---|
| `strict_loads`, `exact`, `uint` | Unique finite JSON, type-sensitive equality and unsigned 64-bit counters; booleans cannot become instruction counts |
| `checkpoint_origin`, `audio_origin` | Typed saved-counter and imported PCM/WAV metadata |
| `derive_window`, `validate_origin_status` | Exact own-origin subtraction and reported resumed-window equations |
| `compare_counter_roles` | Matching clocks/frames and explicit preserved or source-native-plus-interpreted-to-candidate-native counters |
| `encoded_map`, `compare_encoded_maps` | Complete positive-hit encoded identities, mapped fetch addresses and per-key retirement conservation |

For example, after admitting the two roles' original metadata and capture
files under the same supported ABI:

```python
from scripts.dev_audit_relation import encoded_map, compare_encoded_maps

source_keys = encoded_map(source_capture, source_metadata, expected_abi=28)
candidate_keys = encoded_map(candidate_capture, candidate_metadata, expected_abi=28)
relation = compare_encoded_maps(source_keys, candidate_keys, promote=True)
```

`promote=True` requires every candidate key to retire the source key's
native-plus-interpreted count natively, with zero interpreted hits.
`promote=False` preserves both tier counts. The default expected capture ABI
is 28; adapters must explicitly declare the supported common ABI and retain
their decoder identities. Counter inputs use `ticks`, `frame`,
`native_steps` and `interpreter_steps`; `derive_window` returns deltas with
those same names. A per-key comparison result describes that mathematical
relation. Role provenance, process closure, raw replies, saved files,
instruction semantics and final qualification remain the adapter's duties.

## Declare the roles before reading the run

Give the reference and candidate distinct roles and case directories. Bind
each role's original receipt, controller, descriptor, build, executable,
runtime profile, source identity and parent checkpoint. Preserve the original
producer and decoder identities, including when a diagnostic helper is newer
than the compiled runtime. A diagnostic update does not require changing an
otherwise qualified consumer's SDK or checkpoint fingerprint.

Declare the finite frame/control sequence, expected observation labels,
available saved cuts, permitted writes and required parent audits explicitly.
An extra initial candidate checkpoint can be checked against its actual own
parent even when the reference did not save that cut. Preserve the original
receipts and put additional role metadata in a separately bound contract.

## Admit the evidence in dependency order

1. **Freeze the inputs.** Hash the original files and the source-only decoder
   and validation helpers. Validate their identities before importing them.
   Keep retail assets, code captures, journals and checkpoints private.
2. **Admit each raw journal.** Use
   `scripts.dev_journal_audit.audit_wire_journal` with an externally supplied
   hash. Its visitor events remain provisional until EOF, file-stability and
   final hash checks succeed. Schema 1 has no close marker; process ownership,
   natural completion and client admission need separate recorded evidence.
3. **Join commands to observations.** Check the actual requests and replies
   for status, input, complete RAM, images, capture pages and save/load ACKs.
   Bind each recorded file to its actual response and its declared cut.
   A paired journal alone does not establish successful semantic acceptance.
4. **Check state and newly executed work.** Decode each checkpoint under its
   own exact context and file identity. Join the saved ACK, reported origin,
   final state and encoded capture. Keep imported lifetime counters, PCM and
   WAV prefixes separate from the new window. Declare any source-to-native
   counter promotion while retaining strict CPU, device, RAM and host fields.
5. **Validate every permitted edit.** Reconstruct the typed proof with
   `scripts.dev_write.validate_paused_write`, the complete before/after RAM,
   actual request/ACK/status and the declared memory topology. Independently
   establish authority and the complete compiled, original, live and future
   code footprint, including backing aliases. Equal proof summaries alone
   do not establish those obligations. Record the maximum authority and
   the number of actual writes separately.
6. **Close the dependency.** Admit a successor only after its exact parent
   audit passes. Its raw own-parent checkpoint must match the parent gate's
   saved cut. Bind the actual reference and candidate audits, comparison and
   unchanged final files in the qualification index. Missing or provisional
   dependencies remain unqualified.

## Preserve full source identity

Use logical PC, all eight MPR values, physical instruction addresses and
instruction bytes together. Live TCP source-counter rows omit the bytes;
their IDs and ordering differ from the closed encoded capture. Keep those
evidence types distinct. Never fill missing bytes from current RAM or join
the two formats by row number. Stop when the declared relation cannot
establish an unambiguous identity.

Check complete per-identity native/interpreted counts and block/window
conservation. A zero aggregate fallback count does not establish that every
compiled identity ran. Keep checkpoint/audio forks outside the canonical
route's frame totals and identity union.

## Verify the integration

Use authored negatives for swapped roles or parents, missing dependencies,
duplicate/non-finite JSON, boolean counters, changed mappings or bytes,
incorrect window deltas, missing cuts, altered write effects and incomplete
footprints. Verify both accepted and rejected evidence before consuming a
retail gate. Preserve failed receipts and create a new version after a fix.

After the raw gates close, test a fresh process from the newly admitted own
checkpoint and compare a direct continuation with a restored continuation.
Check complete state, RAM, pixels and encoded hit counts. Qualify paced
digital audio separately, subtracting imported work and distinguishing
planned clears, active loss and shutdown tails. This continuation extends
exact-build evidence; cold-reset and broader hardware qualification retain
their own scope. See [native migrations](NATIVE_MIGRATIONS.md),
[paused observations](PAUSED_OBSERVATIONS.md),
[typed writes](PAUSED_WRITES.md) and
[developer checkpoints](DEVELOPER_CHECKPOINTS.md).
