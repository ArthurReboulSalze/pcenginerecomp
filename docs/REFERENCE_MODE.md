# Same-build interpreter reference windows

A consumer can now opt into interpreter-only development runs using the same
executable, native module, device configuration and media as its native run.
This is useful for finding a first native translation difference. Agreement is
internal tier parity: both paths share toolkit devices and it is not independent
Geargrafx, hardware or campaign qualification.

## Enable the capability before making checkpoints

Add these host options to a valid bounded continuous-video recipe:

```text
--dev-port 0 --dev-start-paused on --dev-reference on
```

The Python consumer interface takes `reference_enabled=True` in `command_for`
and `run`. The consumer CLI exposes it explicitly:

```sh
python -m pcerecomp.project run project.toml --build-dir build \
  --receipt private-run.json --dev-port 0 --start-paused --reference-enabled \
  --checkpoint-dir private-checkpoints
```

The directory must already exist. Keep its contents and game captures private.
Use normal `step_frames` for the native counterpart and create its checkpoint
through `save_checkpoint`. Then launch a fresh process with the identical enabled
recipe and restore that checkpoint before any dispatch or instruction capture begins.
A configured `native` tier remains `native`; enabling the capability does not
change normal dispatch until a reference window is requested.

The capability is part of both the reviewed Python checkpoint context and the
host's independently computed fingerprint. Build bytes, configured tier/span,
module, source and media checks remain intact. Old builds and checkpoints made
without the capability cannot be imported. Rebuilding a module requires fresh
candidate checkpoints even when the runtime ABI number is unchanged.

## Run bounded reference segments

At the initial quiescent remote pause, request:

```json
{"id":1,"cmd":"reference_frames","frames":120}
```

The request takes 1 through 600 frames and replies with `target_frame`. Poll
`status` until that target is reached and `paused` is true. The standard client
performs the bounded wait:

```python
with DevClient(port, journal=private_journal) as client:
    client.call('load_checkpoint', name='own-origin.pcec')
    first = client.advance(120, reference=True)
    client.call('set_input', port=0, mask=0x8)
    second = client.advance(2, reference=True)
    client.call('clear_input', port=0)
    client.call('save_checkpoint', name='reference-end.pcec')
```

The CLI equivalent for one segment is
`python scripts/dev_client.py --port PORT reference-frames 120`.
Reference selection is irreversible for that process. Subsequent bounded
`reference_frames` segments preserve that policy; ordinary `resume`,
`step_frames` and checkpoint loads are refused after selection. Status,
input, paused inspection, captures and checkpoint saves remain available.
Initial selection after any dispatch or instruction capture is refused, even when no
instruction retired. A local desktop pause must be released before stepping.
Pure status, capture-history inspection and screenshots do not select or lock
the execution policy.
Finite guest frame, instruction, master-tick and host-wall limits still apply.
Reference-capable sessions cannot publish persistent BRAM.

## Observe work and compare results

Enabled status, final reports and code-capture metadata expose an exact object:

```json
{
  "schema": 1,
  "reference_enabled": true,
  "selected": true,
  "configured_tier": "native",
  "effective_policy": "interpreter",
  "effective_native_span": 0
}
```

Before selection, `selected` is false and effective policy/span describe the
configured native or hybrid path. Disabled sessions omit this extension.
Raw captures, profile input provenance, emitted manifests and execution receipts
retain the policy separately from original runtime ABI and checkpoint origin.
A profile may contain inputs from several policies; it has no aggregate
execution-policy claim. Live source pages remain code-free address/count views.

The reference host calls the scalar interpreter directly, bypassing generated
entry points, source-guard misses and native-span dispatch. Its new window must
report zero native retirements and actual interpreted work. Imported native,
interpreted and block counters remain unchanged. Configured native-dispatch
telemetry reports zero new batches/calls/completions; effective span zero means
that this dispatcher is disabled. Unsupported instructions and faults remain
explicit, and device timing follows the existing interpreter path.

Compare same-origin forks with identical input timing and observation points.
Keep whole checkpoint hashes and imported origins. Entire endpoint files differ
because honest tier counters and payload checksums differ. A decoded machine
comparison may exclude only these four tier-accounting fields:

- `native_steps`
- `interpreter_steps`
- `native_block_steps`
- `interpreter_block_steps`

Do not normalize guard misses, guest clocks, IRQ state, RAM, generations,
video, queued VRAM accesses, CD/audio state or source identity. Compare actual
completed RGB and PCM as well as CPU/device state; preserve unsuccessful
receipts and locate the first difference. Matching only instruction totals is
insufficient. A reference endpoint can seed a later same-build process, but its
imported interpreted prefix remains interpreted evidence.

Raw wire pairing alone does not establish route semantics. Qualification
adapters must explicitly admit `reference_frames` and join actual input/frame
requests, acknowledged targets, settled statuses and capture origins; existing
ordinary-step adapters cannot be reused by relabeling commands.

## Runtime API and compatibility

`step(..., ExecutionPolicy::interpreter_only)` explicitly bypasses generated
code. `native_only` and `hybrid` preserve their existing behavior; the bool API
remains source compatible. The matching `dispatch_span` policy overload supports
interpreter-only hooks and retirement bounds, although the production reference
host deliberately uses scalar stepping. Invalid enum values refuse before guest
mutation.

This capability does not change CPU/Bus layouts, checkpoint encoding or ABI 29.
The host identity change is intentional. It provides no in-process tier toggle,
checkpoint migration or foreign-emulator state importer. See
[developer checkpoints](DEVELOPER_CHECKPOINTS.md) and [TCP control](DEV_SERVER.md).
