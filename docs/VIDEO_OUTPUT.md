# Continuous video output

`Bus::enable_continuous_video()` selects the full palette/raster/DMA profile
and enables guest-clock video output. The ordinary `enable_video()` and
timing-only profiles remain available without rendering. The desktop host
selects continuous output; the headless runner can select it explicitly.
This is an original implementation, informed by the pinned Geargrafx and
Mesen sources listed in [VDC.md](VDC.md); their GPL implementations are not
copied or linked into this runtime.

## Guest history and publication

The output is produced by the existing guest raster clock, not by taking
periodic current-state snapshots. Each HDW entry decodes one line of color
indices from the then-current VRAM, SATB and latched VDC state. Every active
pixel dot converts its stored index using the VCE palette at that guest
instant. Earlier RGB pixels remain unchanged when a later write changes
scroll, VRAM, SATB or palette data. A palette write during a line can therefore
split that line into different colors. An ordinary end-of-run snapshot
cannot reconstruct this history and remains a separate inspection API.

The output follows the selected Geargrafx line-buffer profile:

- BYR is sampled at the existing scroll-Y raster event. The first active
  line loads BYR; later lines increment the counter, or reload BYR plus one
  after a guest register write. BXR is sampled two dots after that event.
- CR is latched at HDS while outside burst mode. Display-disabled burst mode
  is latched at the physical VDC frame boundary. MWR is latched at normal or
  forced vertical sync.
- Background tile planes, map size/wrapping, SATB attributes, sprite flips,
  transparent color zero, priority and the 16-cell line limit use the same
  decoder contracts as the separately tested snapshot inspector.
- Palette conversion occurs at each emitted dot, after DMA and raster events
  due at that dot. RGB uses the deterministic standard profile with each
  three-bit channel expanded by `value * 255 / 7`. VCE bit 7 selects the
  documented `mesen-standard-rgb-v1` digital monochrome conversion at that
  dot. Earlier RGB history is preserved.

Background access mode 3 selects two planes from CG0 or CG1 using MWR bit 7.
The other modes retain all four planes. CG selection follows the existing
vertical MWR latch; it adds no physical VRAM bus scheduling. See
[the decoding and luminance contracts](VDC.md#two-bit-background-and-digital-monochrome-profiles).

`bus.vdc.video.completed()` returns the last completed `VideoFrame`.
`sequence()` increases once at each physical VDC frame wrap, and
`completed_ticks()` records that guest master tick. An empty frame and
sequence zero mean no frame has completed. Host reads do not consume output,
advance simulation or change guest status. A returned frame reference is
valid until the next publication; a host that needs longer ownership copies
it. The current host runs simulation and presentation on one thread.

Two preallocated RGB buffers hold at most 1,024 × 512 × 3 bytes each, plus a
single 1,024-entry index line. There is no frame queue, per-frame file output
or growing history. The front buffer remains stable while the next frame is
built. The completed image uses the VDC active region rather than a fixed
analog viewport: width and height are latched at the start of each output
frame, absent pixels are black, and shorter later lines are padded. Geometry
changes take effect on the next output frame. The maximum RGB allocation is
3 MiB, independent of run duration. Enabling output after guest execution has
started is refused rather than presenting a partial first frame as complete.
Resetting the raster through `enable_raster()` also clears enabled output's
partial/completed buffers, sequence and counters before the new guest run.

## Reference path and state compatibility

Rendering is opt-in. Turning it off preserves the original raster/device path.
For qualified modes, independently authored tests compare clocks, raster
phases/events, status, IRQ state, registers, VRAM, SATB and palette with output
enabled and disabled. Output does not manufacture collision or overflow IRQs.
The desktop clock only decides when the next completed frame is presented;
it never changes guest dot or frame cadence.

Runtime ABI 12 introduced the video output owner. Current ABI 27 also includes
digital audio, held PSG DAC, guest CDDA sample-latch state, the explicit HuCard
mapper and later device timing/history. The video-mode additions themselves
changed no state layout or ABI; updated consumers still need fresh source
pins, builds and qualification. Rebuild generated modules and hosts together.
Later exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve
the scroll counters and pending reload, CR/MWR/burst latches, current decoded
line and pixel position, partial back buffer, completed-frame sequence and
its timestamp. A host GPU texture is recreated from restored guest output.
Portable or cross-build state migration remains unimplemented.

## Verification and limits

The current synthetic suite passes **6,403 expectations**, including
historical palette splits, VRAM and SATB changes between lines, BXR/BYR
latching, sprite priority, frame-latched burst, geometry changes, stable front
buffers, all eight VCE timing controls, partition-independent advancement,
maximum image bounds, two-bit CG latch transitions, live monochrome changes
and unchanged guest device state. Snapshot/palette tests separately pass
**1,735,358 expectations**, including every authored two-plane pattern and
all 512 grayscale colors.

The live Geargrafx comparison uses four authored patterns and four distinct
completed frames per pattern: **16 complete 256 × 192 RGB images, 786,432
pixels**, compared byte for byte. The plans include a palette write during an
active line, BXR and VRAM changes during an active frame, map scrolling/wrap and
sprites with priorities/flips and the two-bit sprite profile. Geargrafx's
256 × 242 debug viewport is cropped to the known 192-line active picture;
the runtime exposes that VDC active picture directly. This comparison was
rerun after the new modes; all 16 frames remain byte-identical. Source review and live
reference agreement do not establish hardware accuracy.

The following limits remain explicit:

- The optional [queued-access profile](VDC_ACCESS.md) models CPU VRAM waits
  and display/DMA contention; `immediate` retains synchronous service. The
  [VRAM read bus and fetched sprite words](VRAM_BUS.md) are retained.
  Physical background/sprite bus phases remain unqualified.
  Writes after HDW entry affect subsequent decoded lines;
  this deliberately matches the selected reference's line-buffer renderer,
  rather than a physical per-fetch pipeline.
- Fine writes inside Geargrafx's narrow post-scroll-latch rewrite windows
  are not qualified. Existing CPU access-phase approximation also applies.
- Sprite collision/overflow events use a separate guest-clock pipeline with
  cached previous-line fetches; see [COMPATIBILITY.md](COMPATIBILITY.md). The
  framebuffer still reads current SATB attributes and pattern words at HDW
  for its decoded line. Post-fetch mutation checks qualify cached event
  behavior, not corresponding pixel caching or physical per-fetch pixels.
- The new modes have a separate finite MesenCE function/filter comparison:
  1,048,576 palette indices and 512 RGB grayscale entries match exactly.
  Geargrafx ignores these settings and cannot qualify them. The extracted
  reference does not qualify complete emulation, latch edges or fetch timing.
- Undriven VRAM reads return the retained read-bus word. SuperGrafx dual-VDC composition, analog borders/filtering and
  mixed horizontal-resolution presentation require further work.
- A VDC active crop can include rows outside an emulator's fixed analog
  viewport for unusual geometry. The comparison above uses ordinary geometry
  fully inside that viewport. No full-frame claim covers such edge cases.

See [REFERENCE.md](REFERENCE.md) for the reproducible external adapter and
[STATUS.md](STATUS.md) for the separately bounded retail test result.
