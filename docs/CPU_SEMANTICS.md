# CPU execution contracts

The native emitter and interpreter implement the following HuC6280
instructions. Both use the same architectural state and bus, but independently
written operation bodies. These contracts describe instruction-level behavior;
full bus phases remain outside the sandbox. Clocked VDC queue waits are modeled
as described in [VDC_ACCESS.md](VDC_ACCESS.md). IRQ delivery
uses the instruction-boundary profile described below.
The functional VDC profile adds its documented fixed mapped-access wait.

| Instructions | Operation | Flags after retirement | CPU cycles |
|---|---|---|---|
| RMB0..RMB7 | Read logical `$2000 + operand`, clear selected bit, write that byte | T cleared; other flags preserved | 7 |
| SMB0..SMB7 | Read logical `$2000 + operand`, set selected bit, write that byte | T cleared; other flags preserved | 7 |
| PHA / PHX / PHY | Write register to `$2100 + SP`, then decrement the byte SP | T cleared; other flags preserved | 3 |
| PHP | Write `(P OR $10) AND $DF` to the stack, then decrement SP | T cleared; other live flags preserved | 3 |
| PLA / PLX / PLY | Increment byte SP, read `$2100 + SP`, store in register | N/Z from value; T cleared; others preserved | 4 |
| PLP | Increment byte SP, read status, restore `saved AND $EF` | T and other actual flags restored; live B represented as zero | 4 |
| BRK | Push PC+2 high, low, then (P OR B) AND ~T; read mapped $FFF6/$FFF7 | Live I set, D/T cleared; saved D preserved | 8 |
| RTI | Pop status, PC low, PC high; restore the exact saved PC | Saved status AND `$EF`; T restored, live B zero | 7 |

SP wraps modulo 256 in both directions. Stack and zero-page accesses go
through **MPR1**, including aliases and remapping; the physical work-RAM bank
is not hardcoded into instruction bodies. Ordinary instructions following
PLP clear T in the usual way. T-sensitive ALU operations consume the entry
T value as described below.

## Load/store and ALU addressing

All encodings of LDA/LDX/LDY, STA/STX/STY/STZ, ORA/AND/EOR, ADC/SBC and
CMP/CPX/CPY are implemented in both execution tiers (97 encodings, including
nine previously supported load/store encodings). The batch adds 88 opcodes,
bringing that batch's execution support to 159; the subsequent RMW/JMP batch
brings support to 191, the bit-test/branch/BSR batch to 221, TMA to 222 and
CSL/CSH to 224, then ST0/ST1/ST2 to 227, the five block transfers to 232 and
RTI to 233, and BRK to 234.

| Mode | Effective address / operand | Base CPU cycles |
|---|---|---|
| Immediate | Fetched operand byte | 2 |
| Zero page | `$2000 OR operand` | 4 |
| Zero page X/Y | `$2000 OR ((operand + index) AND $FF)` | 4 |
| Absolute | Fetched little-endian word | 5 |
| Absolute X/Y | `(word + index) AND $FFFF` | 5 |
| `(zp,X)` | Read word at zero-page `(operand + X) AND $FF` | 7 |
| `(zp),Y` | `(word read at zero-page operand + Y) AND $FFFF` | 7 |
| `(zp)` | Read word at zero-page operand | 7 |

Both pointer bytes remain in logical `$2000..$20FF`; the high byte following
`$20FF` comes from `$2000`. Every data/pointer access uses its actual MPR.
There is no extra page-crossing cycle for these HuC6280 forms. These modes
apply only where the instruction encoding provides them. Block transfers have
the contract below; IRQ delivery has its own contract. ST0/ST1/ST2 have the separate port contract
in [VDC.md](VDC.md).

Loads update N/Z; stores preserve flags except ordinary T clearing.
Comparisons update N/Z from byte subtraction and set C when the register
is at least the operand. They preserve V, ignore D and do not use T's memory
destination.

## Block transfers

TAI (`$F3`), TDD (`$C3`), TIA (`$E3`), TII (`$73`) and TIN (`$D3`) each encode
three little-endian words: source, destination and length. A zero length means
65,536 bytes. The seven-byte instruction retires once, advances PC by seven
modulo 65,536 and takes `17 + 6 * byte_count` base CPU cycles at the entry
clock speed. Device waits are additional; crossing a page adds no separate
surcharge. T clears on entry and all other flags are preserved, including D;
neither decimal nor T memory-destination mode changes the transfer.

| Instruction | Source for byte `i` | Destination for byte `i` |
|---|---|---|
| TAI | `source + (i AND 1)` | `destination + i` |
| TDD | `source - i` | `destination - i` |
| TIA | `source + i` | `destination + (i AND 1)` |
| TII | `source + i` | `destination + i` |
| TIN | `source + i` | `destination` |

Every address wraps to 16 bits and is translated through its actual MPR.
Each byte is read before it is written. This is an ordered bus transfer,
not `memcpy` or `memmove`: overlapping ranges can propagate newly written
values and repeated or alternating device accesses retain their side effects.

The CPU first pushes **Y, A, X**, then fetches all six operand bytes through
the ordinary bus, and finally restores **X, A, Y** by popping the guest stack.
The byte SP wraps normally. These are real guest stack writes and reads:
destination overlap can change the restored registers, and stack aliases can
change instruction operands before they are fetched. Both execution tiers
therefore fetch operands after pushing, even when the native source guard
already checked the original instruction bytes. No unobserved host copy of
the registers overrides modified stack contents. Writes also retain normal
bank generation and ROM/BRAM protection behavior.

Data-copy accesses use the selected Geargrafx block-transfer bus profile:

- Physical bank `$FF`, offsets `$0800..$17FF`: reads return zero without
  normal PSG, timer, joypad or IRQ-register read side effects. This rule
  applies to the data copy; instruction operands and stack reads remain
  ordinary accesses. Other unsupported device operations still fault.
- VDC offsets `$0000..$03FF`: two fixed CPU wait cycles per block read or
  write, compared with one for ordinary accesses. Supported VCE writes keep
  their one-cycle wait. Unsupported VDC/VCE accesses still fault.
- CD registers retain their normal semantics, including DATA IN auto-ACK
  reads at `$1808`; joypad writes also retain their normal semantics.

The sandbox uses Geargrafx's **aggregate clock profile**: 14 startup cycles,
then each byte's read/write at the current clock followed by six cycles,
then the final stack pops followed by three cycles. Device clocks synchronize
at those accesses and boundaries. Mesen instead models separate idle/read/
idle/write/idle/idle cycles within each byte and an initial dummy read. Exact
hardware access phases and this finer Mesen cadence are not claimed here.

Deadline eligibility is checked before the instruction. Once started, a
transfer completes as one bounded instruction, up to 65,536 bytes, and may
cross the requested deadline. There is no resumable partial-transfer state.
An IRQ becoming eligible during the transfer is deferred until the whole
transfer completes. A bus fault can leave earlier stack/data writes and elapsed clocks
visible; it does not retire a successful instruction or promise safe resume.
The [READ-fed block/DMA matrix](BLOCK_DMA_IRQ.md) independently witnesses an
ADPCM source arising inside incomplete original CPU continuations and IRQ2
delivery only after the whole instruction. Continuation calls, completed
instructions and natural-boundary checkpoint work are counted separately.

The active transfer's opcode is captured at dispatch. Subsequent writes to
its opcode or operands do not select another operation or refetch the
latched operands. Geargrafx internally refetches its opcode between transfer
chunks; self-overwriting opcode behavior is excluded from live agreement
claims. Mesen and Beetle retain the active operation instead. Native dispatch
checks the next instruction's source and full mapping afresh after retirement.
The block-transfer interface first required native ABI **10**; IRQ
state first required ABI **11**. Current shared runtime ABI is **27**. The retained block expectations
cover 1,600 transfers, 5,120 status/stack-pointer cases, four destructive-opcode
cases, 23 guard/deadline groups, 8,204 device checks and four deferred IRQ groups.
See REFERENCE.md for the independent live matrix and its exclusions.

## IRQ delivery and RTI

Interrupt-controller bit 0 selects CD IRQ2, bit 1 selects VDC IRQ1 and bit 2
selects the timer request. A set mask bit disables that source. Priority is
timer, then IRQ1, then IRQ2; their logical vectors are `$FFFA`, `$FFF8` and
`$FFF6`, respectively. Both vector bytes use the current MPR mapping, including
MPR7. Interrupt entry does not invent a fixed physical firmware bank.

An accepted IRQ pushes the completed instruction's next PC high byte, low
byte and current status with B cleared. It then sets I, clears D and T and
loads the selected little-endian vector. Entry costs eight CPU cycles at the
current speed, in addition to the completed instruction and mapped-access
waits. A/X/Y and MPRs are preserved. SP wraps as a byte; stack writes use
logical `$2100..$21FF` through MPR1. A stacked D or T value is preserved even
though the handler begins with both cleared.

RTI pops status, PC low and PC high in that order. It restores `saved P AND
$EF`, including I, D and T, and returns to the exact saved PC with no increment.
Its seven base CPU cycles use the entry speed. These are real bus accesses:
remapped stacks, aliases, ROM reads and faults retain the same behavior as
other stack instructions. Generated RTI code contains the translated pops and
status/PC operations; it does not dispatch to the interpreter.

The pinned Geargrafx and Mesen sources agree on these vectors, stack order,
status restoration and base totals. Their IRQ sampling also explains the
one-instruction delay after CLI, acceptance after SEI when the prior I was
clear, and the distinction between an acknowledged timer request and a
previously sampled VDC request. Exact sub-instruction device sampling remains
a separate qualification from completed-instruction state agreement.

The selected execution profile samples the entry I flag, controller mask and
IRQ lines, executes the instruction, then enters the sampled interrupt after
retirement. CLI therefore permits one further instruction before entry. SEI
does not cancel an IRQ already sampled with I clear. PLP and RTI use the same
entry-I rule, even when they restore a different I value. An acknowledged
timer request must still be asserted at delivery. A sampled IRQ1/IRQ2 remains
eligible only while a later access/wait path has not replaced that sample.
In particular, fixed/immediate VDC status reads resample after clearing the
device status and can cancel an earlier IRQ1 sample; queued reads sample while
waiting before the acknowledgement and retain that sample until a later
resampling point. This is a source-backed distinction between the existing
access profiles, not new sub-instruction hardware qualification. New IRQs
raised during a completed block transfer may be accepted at its end. This is
an explicit aggregate instruction profile, not a claim to reproduce every
physical penultimate-cycle sample or MMIO resampling in Geargrafx.

The [device IRQ suite](IRQ_DEVICES.md) independently checks competing genuine
timer/VDC-DMA/CD sources and their acknowledgements, including retained samples
and a later RMW wait cancelling IRQ1. Its original call journals qualify the
declared fixed-wait/IRQ/CD callback clocks. The separate
[dynamic-stall suite](IRQ_STALLS.md) checks DMA IRQ1 and CD IRQ2 during genuine
queued waits at both CPU speeds and all three VCE rates. It distinguishes
fixed and dynamic three-tick callbacks and retains the actual later CPU
sample. Other IRQ sources, active-display combinations, interrupted transfers
and electrical bus-phase behavior retain their separate limits.

In physical bank `$FF`, `$1400..$17FF` mirror four interrupt-register offsets.
Offset 2 reads/writes the three disable bits. Offset 3 reads the three request
bits; writing any value acknowledges only the timer request. IRQ1 and IRQ2
are acknowledged at their source device, not by this write. Reads at offsets
0/1 return the existing I/O latch, and their writes change no controller state.
Reads at offsets 2/3 preserve the I/O latch's upper five bits. Ordinary writes
update the latch with the full byte, including writes at unused offsets.
Block-copy reads retain their separate zero-return rule described above.

## T mode and decimal arithmetic

Incoming T affects **ADC, AND, EOR and ORA only**. The ordinary operand is
read first. The other input comes from logical `$2000 OR X`, and the result
is written there while A is preserved. N/Z and arithmetic flags describe
that result. T adds three cycles and clears at retirement. SBC always uses
A, even with T set. SET and PLP can supply T for exactly the next instruction;
an intervening ordinary instruction consumes it without invoking memory mode.

ADC/SBC use incoming C and update C/N/Z. Binary arithmetic also computes V.
With D set, they perform nibble adjustment, preserve incoming V, derive N/Z
from the adjusted byte and add one cycle. Decimal and T surcharges combine
for ADC. Non-BCD input nibbles have defined byte-level behavior here; they
are not rejected or converted through an assumed valid decimal number.
The two tiers use separate arithmetic bodies. The exhaustive tests include
all byte pairs, C/D/T/V combinations and both tiers, with a separate digit
model for expected decimal results.

## Shifts, rotates, INC/DEC and indirect JMP

The RMW/JMP batch adds 32 encodings: ASL/LSR/ROL/ROR each have accumulator,
zero-page, zero-page X, absolute and absolute X forms; INC/DEC have four
memory forms each plus accumulator INA/DEA; JMP adds `(absolute)` and
`(absolute,X)` forms. Previously supported INX/INY/DEX/DEY remain unchanged.

| Family | Result and flags | CPU cycles |
|---|---|---|
| ASL / LSR | Shift byte left/right; shifted-out bit goes to C; N/Z from byte result | Accumulator 2; zero-page forms 6; absolute forms 7 |
| ROL / ROR | Rotate through incoming C; shifted-out bit becomes new C; N/Z from result | Accumulator 2; zero-page forms 6; absolute forms 7 |
| INC / DEC / INA / DEA | Add/subtract one modulo 256; update N/Z and preserve C | Accumulator 2; zero-page forms 6; absolute forms 7 |
| JMP `(abs)` / `(abs,X)` | Read a little-endian target through the bus; assign PC without fetching target code | 7 |

These operations clear T and do not invoke T's memory destination. D does
not alter them; V and the remaining unrelated flags are preserved. RMW
indexing follows the same byte/word wrapping rules as load/store addressing,
with no indexed page-crossing surcharge. Memory forms read and write the
same effective byte and preserve A; accumulator forms do not access data RAM.
This is an instruction-level effect, not a claim about hardware dummy accesses.

JMP's pointer is the encoded word, plus X for the indexed form, modulo
65,536. Its high byte comes from `(pointer + 1) AND $FFFF`, with each byte
using its own MPR. There is no NMOS 6502 same-page high-byte wrap. Pointer
bytes stay live data in generated code, so table changes take effect without
regeneration. Static CFG discovery still reports an unresolved indirect edge;
runtime support does not establish a static target or compile that target.

## Bit tests, bit branches and BSR

| Family | Operation and flags | CPU cycles |
|---|---|---|
| BIT, including immediate | N/V from operand bits 7/6; Z from `(A AND operand)==0` | Immediate 2; zero-page forms 4; absolute forms 5 |
| TSB / TRB | Store `old OR A` / `old AND NOT A`; N/V from original memory; Z from the stored result | Zero page 6; absolute 7 |
| TST | N/V from memory; Z from `(immediate mask AND memory)==0`; A unchanged | Zero-page forms 7; absolute forms 8 |
| BBR0..7 / BBS0..7 | Read selected zero-page bit; branch if clear/set; flags preserved except T | Not taken 6; taken 8 |
| BSR | Push the operand address high byte then low byte; branch relative to next PC | 8 |

All clear T without invoking a T-mode destination; unrelated flags remain
unchanged. In particular, HuC6280 BIT immediate updates N/V, and TSB/TRB's Z
describes the stored result, unlike ordinary 65C02 expectations. Decimal mode
does not change these operations. TST uses three or four fetched bytes and
zero-page/absolute X wrapping as appropriate. Both tiers fetch/guard the
complete instruction before performing its operation.

Bit-branch displacement is signed and relative to PC after all three bytes.
BSR uses the same signed-byte convention with its two-byte length, preserves
registers, and wraps SP through the normal guest stack. RTS adds one to BSR's
saved operand address to recover the next instruction. Native CFG discovery
retains BSR call and return-site edges; it does not prove that a call returns.

## TMA, TAM and the MPR transfer latch

| Instruction | Operation | Flags after retirement | CPU cycles |
|---|---|---|---|
| TAM, nonzero mask | Copy A to every selected MPR and to the transfer latch | T cleared; all others preserved | 5 |
| TAM, zero mask | Preserve all MPRs and the latch | T cleared; all others preserved | 5 |
| TMA, nonzero mask | OR every selected MPR, store the result in the latch and A | T cleared; all others preserved, including N/Z | 4 |
| TMA, zero mask | Copy the previous latch into A; preserve MPRs and latch | T cleared; all others preserved, including N/Z | 4 |

`Cpu::mpr_latch` is the dedicated TAM/TMA transfer buffer. Ordinary memory
reads, writes and source peeks do not change it. It is distinct from I/O
open-bus state, which the IRQ/PSG profile now retains separately. The deterministic
sandbox starts the latch at zero; this does not establish hardware power-on
state or a post-BIOS state. Exact-build
[developer checkpoints](DEVELOPER_CHECKPOINTS.md) preserve it explicitly.

Multi-bit masks use OR, matching the pinned Geargrafx and Mesen implementations
and the live Geargrafx sequence checks. The pinned MAME implementation instead
selects the highest-numbered selected MPR; that discrepancy is documented
rather than silently treating these references as identical. No hardware
verification of these edge cases is claimed.

TAM's mapping change takes effect after its operand is fetched. It retires
normally even when it remaps the executing page. The next native dispatch
checks the full MPR context and yields if it changed; interpreter fallback
fetches through the new mapping. TMA preserves the mapping. All 256 masks
have dedicated native fixture sites; operands remain source guarded.

## CSL/CSH and speed transitions

CSL (`$54`) selects low speed, master-clock divisor 12. CSH (`$D4`) selects
high speed, divisor 3. Both are one byte and take three CPU cycles, preserve
A/X/Y/SP/MPRs/the transfer latch, preserve all flags except ordinary T
clearing, and advance PC by one modulo 65,536. D and T do not redirect them.
Selecting the current speed still retires normally.

The first two cycles use the **entry divisor**, and the final cycle uses
the **selected divisor**. Following instructions use that selected divisor.

| Entry speed | CSH ticks | CSL ticks |
|---|---|---|
| High, divisor 3 | 9 | 18 |
| Low, divisor 12 | 27 | 36 |

This split-cycle rule follows the pinned Mesen and Beetle implementations.
Geargrafx 1.8.4 instead charges all three cycles at the selected divisor:
live MCP traces show 36 ticks for high-to-low CSL and 9 for low-to-high CSH.
Its resulting CPU state/speed agrees, but those transition timestamps differ
from this runtime. The reference report records these differences explicitly;
they are not timing parity or hardware qualification.

The shared CPU retirement helper performs clock accounting; generated code
directly selects its literal target divisor without calling the interpreter.
Mapping/source guards and deadlines run before any speed change. A started
instruction finishes even if it crosses the deadline. No extra CPU layout
state was needed by that batch. The VDC-state batch first required ABI
4; the current shared bus/CPU contract requires ABI 27. Exact IRQ sampling,
full clock alignment, other dynamic device waits and hardware dummy reads remain
outside this instruction-level contract. Fixed VDC access waits are
specified in [VDC.md](VDC.md).

The [VDC phase investigation](VDC_PHASES.md) follows this known transition
difference through actual source ledgers into a queued-read entry phase. It
explains selected wait differences without changing the speed rule or aligning
the engines' raw timestamps.

## B and T representation

PHP clears T before creating the saved status byte and sets its B marker.
PLP may restore T; it is deliberately exempt from the ordinary retirement
clear. The restored status uses B=0 internally, matching Geargrafx 1.8.4 and
Mesen. MAME instead keeps B=1 internally. This representation difference was
detected by a failing Geargrafx comparison during implementation, investigated
in the pinned sources, and resolved without masking debugger status bits.
This is not a claim that an emulator's internal representation is a hardware
register implementation. Saved PHP status still contains B=1.

Adding the persistent transfer latch first changed `Cpu` and advanced the
native module ABI to 2. IRQ state advanced
ABI to **11** (CD-control state first required ABI 3, VDC state ABI 4,
video-clock execution ABI 5, clocked CD transport ABI 6 and TOC/DATA IN ABI 7,
joypad ABI 8, sector streaming ABI 9 and block transfers ABI 10).
ABI 12 added continuous video, ABI 13 digital audio state, ABI 14 held PSG DAC
outputs, ABI **15** the guest CDDA cursor and sample latch, ABI **16** cached
sprite evaluation, WRAM aliases and bounded CD diagnostics, and ABI
**17** explicit System Card memory profiles and one-shot reset-vector startup.
ABI 18 adds base HuCard startup, 19 mapper profiles, 20 Arcade Card Duo,
21 stopped timer phase, 22 pending CD sense, 23 retained VDC bus/fetched
rendering state, ABI **24** queued VRAM accesses and waits, ABI **25** live scroll-write history and program-range lookup, and current
ABI **26** guest PSG write phases.
Regenerate modules and rebuild their consumers together;
older generated source fails its compile-time assertion against ABI 26.
Old TAM bodies also lack the latch update, so keeping their source is unsafe
even if a particular host layout happens to match. The later
[developer checkpoint interface](DEVELOPER_CHECKPOINTS.md) retains this state
only for the exact reviewed build; it does not migrate checkpoints between
ABI versions, modules or builds.

## Faults and mutation safety

Unmapped or unsupported device stack/zero-page/data accesses remain explicit
fatal bus faults, and writes to ROM are rejected. The supported CD control,
clocked command-handshake and volatile-BRAM exceptions are specified in [CD_CONTROL.md](CD_CONTROL.md):
reads can lock BRAM, protected writes can be intentionally ignored and all
CPU addressing modes reach the same physical device. The additional
[VDC profile](VDC.md) implements mirrored ports, buffered VRAM and direct
ST0/ST1/ST2 writes; the extended video profile adds DMA. Undriven VRAM reads
return the retained VDC bus word; inspection never updates it. See
[VRAM_BUS.md](VRAM_BUS.md). Its opt-in
raster clock advances at instruction boundaries in both tiers. CPU accesses
sample device state at instruction-entry time plus preceding fixed waits;
base instruction cycles advance devices on retirement. The separate CD
transport clock follows the same retirement cadence and access approximation;
selection/REQ/ACK, TEST UNIT READY, TOC and sector DATA IN responses use the
bounded provider contract in [CD_CONTROL.md](CD_CONTROL.md). `$1808` auto-ACK advances guest state through the
same shared bus path in both tiers; its release deadline uses master ticks.
IRQ delivery and RTI use the contract above. A pull can
read ROM, as any ordinary
mapped read can. A fault does not retire an instruction; it is not a resumable
transaction and does not promise rollback of a partially advanced SP.

Native source and mapping guards run before the instruction body. Tests cover
modified bit operands, correct fallback to their current address, MPR1
stack remapping, a second logical alias of work RAM, and writes observed
through that alias. Per-bank generations change only when stored bytes change;
an unchanged bit value still retires the instruction with its normal cycles.
The data tests also cover T source/destination aliases, SET/PLP sequences,
ROM write refusal, mutated absolute operands and interpreter fallback across
a 16-bit indexed-address wrap. No fault retires an instruction; arithmetic
flags changed before a failed write are not rolled back.

## Evidence

The C++ suite checks 92,160 independently expected bit/stack cases in
addition to the full native/interpreter comparison matrix. It covers every
incoming status byte for bit operations, every byte to push/pull, SP
`$00/$01/$FE/$FF`, negative/zero preservation, cycle totals and both clock
divisors. Additional focused tests check faults, ROM access, aliases, source
guards and PLP → PHP / PLP → NOP sequences.

The data batch adds 7,340,032 independently expected arithmetic/logic cases
and 340 load/store addressing cases. ADC/SBC sweep every pair of operand
bytes and all 16 C/D/T/V combinations in each tier; logical operations and
comparisons sweep every byte pair under four flag contexts. The full
internal comparison matrix now has 14,528 cases across 227 opcodes.

The RMW/JMP batch checks 3,932,160 expected-value cases: every input byte
and incoming status byte for all 30 RMW encodings in both tiers. The matrix
covers zero-page wrapping, absolute page crossings, carry-in/out, unaffected
flags, T non-redirection, both clock divisors, neighbors and write generations.
Another 16,384 expected indirect-JMP cases cover status preservation,
multiple indices/targets and a deliberately different NMOS-style high byte.
Additional source-guarded native fixture sites exercise pointer and indexed
address wrap at `$FFFF`, crossing `$3FFF/$4000` between MPRs, mutable jump
tables, missing high-pointer bytes, RMW ROM/device faults and operand mutation.

The bit-test/branch/BSR batch adds 4,849,664 expected bit-test cases and
2,228,224 expected branch/BSR cases across both tiers. These cover all byte
pairs under four flag contexts for memory BIT/TSB/TRB, every byte/status
combination for TST's compiled mask and BIT's compiled immediate, every
zero-page byte/status for bit branches, and all SP/status pairs for BSR.
Additional tests cover mutable TST masks, ROM/device faults and interpreted
signed target/fetch wrap. Fixed native immediates/masks are `$20`/`$55`;
this does not claim all possible native immediate encodings were tested.

The MPR batch adds **1,114,112 independently expected cases**. Both tiers
test every mask and A/incoming-latch byte under four status contexts, with
both clock divisors. A separate interpreter sweep varies MPR contents and
all masks against a bit-column OR model. Directed sequences check zero-mask
preservation through ordinary memory traffic, native guard yields after
remapping the executing page, operand mutation and deadline preservation.
The independent sequence adapter observes Geargrafx's latch through TMA #0;
it does not read an unexposed emulator field.

The speed batch adds **524,288 independently expected cases** covering both
opcodes, both entry speeds, every status/latch byte and both tiers. The
literal transition table above supplies expected ticks. Directed tests cover
same-speed repeats, mixed sequences with NOPs, deadline entry/crossing,
mutated opcodes with fallback, mapping guards, PC wrap and failed fetches.
Geargrafx independently matches 120 instruction states per tier and 24
RAM/latch observations per tier. Its trace deltas match in 92 cases per tier;
the other 28 are exactly the documented speed-transition discrepancy.

The VDC batch adds ST0/ST1/ST2 and a separate synthetic module with 77,824
independently expected CPU cases, plus 8,192 register-width cases and 392,991
VRAM transfer/address cases. Status acknowledgement, mapping/source guards,
deadlines and explicit faults are covered locally. See [VDC.md](VDC.md) and
[REFERENCE.md](REFERENCE.md) for the functional profile and live-check limits.

The optional Geargrafx MCP suite uses four base vectors per opcode with
explicit zero-page and popped values. Each stack opcode has four more
directed vectors. The vector tests require both original states of every
bit and all four saved B/T combinations for PLP. See
[REFERENCE.md](REFERENCE.md) for the actual run results and limits.

## Primary references

- [HuC instruction reference](https://github.com/pce-devel/huc/wiki/HuC6280-Instruction-Set):
  opcode encodings, operation descriptions, flags and instruction cycle counts.
- [Geargrafx 1.8.4 opcode implementation](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_opcodes.cpp)
  and [CPU helpers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h):
  independent runtime behavior, T clearing and status restoration.
- [Geargrafx interrupt entry and controller](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h)
  and [Mesen interrupt processing](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceCpu.cpp):
  priority, mapped vectors, eight-cycle entry, stack flags and timer-acknowledge
  distinction. These sources describe finer sampling than the sandbox's
  aggregate instruction-boundary profile.
- [Geargrafx arithmetic helpers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_opcodes_inline.h):
  production HuC6280 T/decimal behavior; the `GG_TESTING` 65C02 alternatives
  are deliberately not the oracle configuration.
- [Geargrafx transfer helpers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_opcodes_inline.h)
  and [block-aware memory accesses](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory_inline.h):
  ordered Y/A/X saves and X/A/Y restores, live operands, 14/6/3 aggregate
  timing, alternate-address patterns, suppressed reads and VDC waits.
  [Mesen block instructions](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceCpu.Instructions.cpp)
  and [Beetle CPU source](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/pce/huc6280.cpp)
  cross-check stack ordering, zero length and overlap behavior, while showing
  finer clock phases and retained-operation alternatives to Geargrafx's
  per-chunk opcode fetch. Neither was executed live for this batch.
- [Geargrafx memory transfers](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/memory.cpp)
  and [Mesen memory manager](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceMemoryManager.cpp):
  selected-MPR OR, zero masks and the persistent transfer latch.
- [Geargrafx timing metadata](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_timing.h):
  all 97 data, 32 RMW/JMP, 30 bit-test/branch/BSR and TAM/TMA base totals agree
  in source-level checks; live cycle parity remains outside the reference
  adapter's scope.
- [Mesen speed instructions](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceCpu.Instructions.cpp)
  and [Beetle CPU source](https://github.com/libretro/beetle-pce-libretro/blob/b96c11e095b6a40a412d2da02766ae1c3f4fd539/mednafen/pce/huc6280.cpp):
  final-cycle speed transition. [Geargrafx instruction retirement](https://github.com/drhelius/Geargrafx/blob/1c62a549328241518101f5be5bf3e6840b96ea5d/src/huc6280_inline.h)
  explains its differing total. Only Geargrafx was executed live in this batch.
- [Mesen status setter](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceCpu.h)
  and [instructions](https://github.com/SourMesen/Mesen2/blob/b9fa69ddc6d0a331fb103fdb5eef6904305703c2/Core/PCE/PceCpu.Instructions.cpp):
  independent source cross-check; Mesen was not executed in this batch.
- [MAME HuC6280 source](https://github.com/mamedev/mame/blob/da9333a2a5123012a939e78c3f2df7175ea7d100/src/devices/cpu/h6280/h6280.cpp):
  instruction totals and the alternative live-B representation.

No GPL CPU implementation is copied or linked into this runtime. The
reference emulator remains a separately supplied process.
