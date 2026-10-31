# Timer divider and interrupt behavior

The HuC6280 timer belongs to the guest clock. Its divider advances once per
3,072 master ticks, independently of CPU speed or host presentation. A running
counter decrements at each divider edge; zero reloads the seven-bit reload
value and asserts the timer request. Interrupt masks and acknowledgement are
separate from this count. See [CPU interrupt delivery](CPU_SEMANTICS.md).

The timer register window occupies physical bank `$FF`, offsets
`$0C00..$0FFF`. Every read returns the counter in bits 0..6 while preserving
the I/O latch's bit 7. Even writes set the reload value; odd writes set enable
from bit 0. Higher write bits do not select a different timer. Logical access
uses the current MPR translation, including aliases of the I/O bank.

## Disabled phase is observable

The selected Geargrafx profile returns `$7F` instead of zero when the stored
counter is zero and the remaining divider phase is at most 15 master ticks.
That rule also applies while the timer is disabled:

| State or write | Counter | Divider phase |
|---|---|---|
| Initial device reset | Zero | Zero, stopped |
| Reload write while disabled | Unchanged | Unchanged |
| Repeated disabled control write | Unchanged | Unchanged |
| Disabled → enabled | Current reload | Fresh 3,072 ticks |
| Repeated enabled control write | Unchanged | Existing running deadline |
| Enabled → disabled | Current counter | Fresh 3,072 ticks, stopped |

Consequently, the initial read returns `$7F` (plus latch bit 7). If the timer
was enabled with reload zero and then disabled before its first edge, it
returns zero instead. Advancing time while disabled does not change that
distinction. Writing a new reload while running affects subsequent reloads,
not the current counter or deadline. Disabling does not acknowledge a pending
timer interrupt; IRQ acknowledgement remains in the IRQ register window.

ABI 21 adds `Interrupts::timer_frozen_phase` for this explicit stopped phase.
Running timers retain their absolute guest deadline. This corrects the earlier
reset-read mismatch without changing the existing aggregate interrupt-delivery
profile. Neither reads nor diagnostic inspection enable or acknowledge the
timer. Pure native source guards continue to refuse MMIO instruction bytes.

## Compatibility and evidence

Generated modules and runtime must be rebuilt together for current ABI 27.
Retained ABI-12 through ABI-25 captures remain compiler inputs with their
original labels. ABI 21 itself introduced no save-state format. Later
exact-build [developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve the
stopped phase, counter/reload, enable and pending request alongside the running
deadline and guest clock. Portable or cross-build states remain unimplemented.

Tests distinguish literal timer expectations, interpreter/native agreement
and independent Geargrafx observations. Current run counts and source pins
are recorded in [STATUS.md](STATUS.md) and [REFERENCE.md](REFERENCE.md).
The rule above is the selected emulator profile; electrical bus phases,
sub-instruction sampling and physical hardware accuracy remain unqualified.

Primary reference: [Geargrafx timer clock, read and control
operations](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h).
