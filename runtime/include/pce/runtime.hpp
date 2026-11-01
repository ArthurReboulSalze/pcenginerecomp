#pragma once

#include <array>
#include "pce/video.hpp"
#include "pce/cartridge.hpp"
#include "pce/arcade_card.hpp"
#include "pce/scanline.hpp"
#include "pce/audio.hpp"
#include "pce/pcm.hpp"
#include "pce/adpcm.hpp"
#include "pce/cdda.hpp"
#include "pce/cd_timing.hpp"
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>

namespace pce {
inline constexpr unsigned abi_version = 28;
enum Flag : std::uint8_t { C=1, Z=2, I=4, D=8, B=16, T=32, V=64, N=128 };
enum class Exit { executed, miss, unsupported, budget };
enum class BankKind { unmapped, ram, rom, io, bram };
enum class SystemCardProfile { none, standard, super };

struct Fault : std::runtime_error { using std::runtime_error::runtime_error; };

struct Cpu {
    std::uint8_t a=0, x=0, y=0, sp=0xFF, p=I;
    std::uint16_t pc=0;
    std::array<std::uint8_t,8> mpr{0xFF,0xF8,0x80,0x81,0x82,0x83,0x84,0};
    // Dedicated TAM/TMA transfer latch, not the general memory or I/O bus.
    // Zero is the deterministic sandbox initial value, not a power-on claim.
    std::uint8_t mpr_latch=0;
    std::uint64_t ticks=0, cycles=0, native_steps=0, interpreter_steps=0, guard_misses=0;
    // VRAM stalls clock at the fast 3-master-tick cadence even in low CPU speed.
    // They add elapsed guest time, not logical instruction cycles/retirements.
    std::uint64_t vdc_wait_ticks=0;
    // Completed block-instruction accounting, separate from transferred bytes.
    std::uint64_t native_block_steps=0, interpreter_block_steps=0, block_bytes=0;
    // Explicit sandbox initial speed; hardware reset/IRQ timing is separate.
    unsigned clock_divisor=3;
    std::uint8_t irq_sampled=0;
    std::uint16_t irq_vector=0;
    std::uint64_t irq_entries=0, rti_steps=0;
    void nz(std::uint8_t value) { p = (p & ~(N|Z)) | (value & N) | (value == 0 ? Z : 0); }
    void retire(unsigned count, bool native) {
        cycles += count;
        ticks += static_cast<std::uint64_t>(count)*clock_divisor;
        if(native) ++native_steps; else ++interpreter_steps;
    }
    void retire_speed(unsigned next_divisor, bool native) {
        // Two cycles at entry speed, final cycle at the selected speed.
        ticks += 2*clock_divisor;
        cycles += 2;
        clock_divisor = next_divisor;
        retire(1,native);
    }
};

// Disc INDEX 01 and leadout are LBAs without the 150-frame lead-in. Metadata
// attachment provides TOC replies, never permission to invent sector bytes.
struct CdTrack {
    std::uint32_t index1_lba=0;
    std::uint8_t type=4; // 0 audio, 4 data
};
struct CdToc {
    std::array<CdTrack,99> tracks{};
    unsigned track_count=0;
    std::uint32_t leadout_lba=0;
    std::string image_sha256; // Optional provenance for programmatic fixtures.
    void validate() const;
};
CdToc read_toc(const std::string& path); // Bounded PCE_TOC 1 descriptor, not media.

class SectorProvider;

// Clocked command transport with one bounded sector/response buffer.
struct Scsi {
    bool enabled=false, status_pending=false;
    unsigned phase=0;
    std::uint16_t signals=0;
    std::uint8_t latch=0, data=0;
    std::uint64_t master_ticks=0, deadline=0, auto_ack_deadline=0;
    unsigned event=0; // 0 none, 1 command, 2 REQ, 3 status, 4 message, 5 free, 6 data, 7 response REQ
    std::array<std::uint8_t,16> command{}, last_command{};
    std::array<std::uint8_t,2048> response{};
    bool read_active=false;
    std::uint32_t load_lba=0, current_lba=0;
    unsigned load_remaining=0;
    std::uint64_t load_deadline=0;
    unsigned response_size=0, response_index=0;
    unsigned command_size=0, last_command_size=0;
};

// Idle control and clocked transport are separate opt-in profiles.
struct CommandOrigin {
    bool valid=false;
    std::uint16_t pc=0;
    std::uint64_t ticks=0;
    std::array<std::uint8_t,8> mpr{};
    std::array<std::uint8_t,7> fetch{};
    std::uint8_t readable=0;
};
// Pending NEC-format error context is independent of the active SCSI response.
// failed_lba is host diagnostics only: the guest's information bytes stay zero.
struct CdSense {
    std::uint8_t key=0, asc=0, ascq=0, fru=0;
    std::optional<std::uint32_t> failed_lba;
};
// Explicit response profiles, not implementations of unrecognized operations.
enum class CdUnknownPolicy : std::uint8_t { fault, gear_good, nec_invalid };
struct CdControl {
    bool enabled=false, bram_unlocked=true, ack=false;
    std::uint8_t interrupt_enable=0, interrupt_active=0, reset=0;
    std::uint64_t reads=0, writes=0, toc_replies=0, data_bytes_acked=0;
    std::uint64_t read_commands=0, sectors_read=0, read_retries=0, read_errors=0;
    CdSense pending_sense;
    std::uint64_t sense_commands=0, sense_errors=0;
    bool audio_enabled=false;
    CdUnknownPolicy unknown_policy=CdUnknownPolicy::fault;
    CdTimingProfile timing_profile=CdTimingProfile::fixed;
    std::uint64_t unknown_commands=0;
    std::uint64_t invalid_commands=0; // Completed NEC-profile invalid CDB responses.
    // Bounded diagnostics. Counts dispatched attempts in all profiles; unknown_commands
    // continues to count only accepted reference-profile responses.
    std::array<std::uint64_t,256> unknown_opcodes{};
    std::array<std::uint8_t,16> last_unknown_command{};
    unsigned last_unknown_size=0;
    CommandOrigin pending_origin, last_unknown_origin;
    CdAudio audio;
    Scsi scsi;
    std::shared_ptr<SectorProvider> provider;
    std::optional<CdToc> toc;
    bool irq2() const { return (interrupt_enable & interrupt_active)!=0; }
    void audio_command();
    void audio_event();
    void write_fader(std::uint8_t);
    double fader_gain(bool adpcm) const;
    void advance_to(std::uint64_t ticks);
    void set_toc(const CdToc& value);
    void set_sector_provider(std::shared_ptr<SectorProvider> value);
    std::uint8_t transport_read(unsigned port);
    void transport_write(unsigned port, std::uint8_t value);
private:
    void phase(unsigned value);
    void handshake();
    void schedule(unsigned event, std::uint64_t delay);
    void update_irq();
    void start_status(std::uint8_t value, unsigned length=1);
    void check_condition(std::uint8_t key,std::uint8_t asc,std::uint8_t ascq=0,
                         std::optional<std::uint32_t> failed_lba=std::nullopt);
    void request_sense();
    void read_directory();
    void read_sectors();
    void load_sector();
    void schedule_load(std::uint64_t delay);
};

// Explicit timing state; counters are guest master ticks and VDC dots, never
// host presentation time. Enum order follows the hardware counter sequence.
struct RasterTiming {
    bool enabled=false, hsync=true, vsync=true, compare_pending=false, blank_consumed=false;
    std::uint8_t control=0;
    std::uint64_t master_ticks=0, frames=0, vblank_events=0, rcr_events=0;
    unsigned hclock=0, line=0, dot=0, vdc_line=0, raster_line=0;
    unsigned divider=4, total_lines=262, h_state=0, v_state=0;
    int h_remaining=1, v_remaining=2, event_remaining=0;
    unsigned event=0; // 0 none, 1 scroll-Y checkpoint, 2 scroll-X, 3 HDS, 4 compare
    std::array<unsigned,4> horizontal{}; // HDS/HDW/HDE/HSW lengths in dots
    std::array<unsigned,4> vertical{}; // VDS/VDW/VCR/VSW counter lengths
};

// Single VDC. Untimed functional accesses settle immediately. The timed profile
// queues CPU VRAM requests and arbitrates them on guest master-clock slots.
struct Vdc {
    bool enabled=false, irq1=false;
    std::uint8_t selected=0, status=0;
    std::array<std::uint16_t,20> reg{};
    std::unique_ptr<std::array<std::uint16_t,32768>> vram =
        std::make_unique<std::array<std::uint16_t,32768>>();
    std::uint16_t read_buffer=0, vram_bus_latch=0;
    bool queued_cpu_accesses=true;
    bool pending_vram_read=false, pending_vram_write=false;
    int vram_transfer_delay=0;
    unsigned vram_cpu_cycles=0;
    int load_bg_start_clock=1365, load_bg_end_clock=0;
    unsigned hsync_start_clock=0;
    std::uint64_t reads=0, writes=0, vram_changes=0;
    RasterTiming raster;
    VideoOutput video;
    std::array<std::uint16_t,256> satb{};
    // Guest sprite evaluation persists without a framebuffer or audio output.
    // Pattern words are captured at the raster-compare event for the next line.
    struct SpriteRow {
        int x=0;
        unsigned index=0;
        bool flip=false;
        unsigned palette=0;
        bool front=false;
        std::array<std::uint16_t,4> planes{};
    };
    std::array<SpriteRow,16> sprite_rows{};
    unsigned sprite_count=0;
    bool sprite_overflow=false, sprite_burst=false, sprite_active=false;
    std::uint16_t sprite_control=0, sprite_mode=0;
    bool dma_enabled=false, satb_armed=false;
    unsigned satb_pending=0, vram_dma_pending=0;
    std::uint16_t dma_source=0, dma_dest=0;
    std::uint64_t dma_words=0, satb_words=0;
    void dma_tick();
    void vblank_dma();
    unsigned increment() const { constexpr unsigned steps[]={1,32,64,128}; return steps[(reg[5]>>11)&3]; }
    void prefetch();
    bool has_pending_vram() const { return pending_vram_read || pending_vram_write; }
    bool vram_wait_required(unsigned port,bool write) const;
    bool cpu_vram_slot_available(unsigned elapsed_master_ticks=3) const;
    // Progress the shared request queue before the corresponding raster clocks.
    void process_cpu_vram_accesses(unsigned master_ticks);
    // Guest VRAM reads drive the retained bus only in the connected half.
    std::uint16_t read_vram(std::uint16_t address);
    // Inspection observes the same backing/held value without driving the bus.
    std::uint16_t peek_vram(std::uint16_t address) const;
    std::uint8_t read(unsigned port);
    void write(unsigned port, std::uint8_t value);
    void enable_raster(); // Reset clock phase, latch the current register values.
    void advance(std::uint64_t delta_master_ticks, const Vce* palette=nullptr);
    void write_vce_control(std::uint8_t value);
private:
    bool queues_vram() const { return raster.enabled && queued_cpu_accesses; }
    void queue_vram_read();
    void queue_vram_write();
    void complete_vram_read();
    void complete_vram_write();
    void update_vram_busy();
    void advance_raster(std::uint64_t delta_master_ticks,const Vce* palette);
    void latch_horizontal();
    void latch_vertical();
    void schedule_line_events();
    void compare_line();
    void horizontal_edge();
    void dot_tick();
    void line_tick();
    void raster_event();
    void fetch_sprite_rows();
    void sprite_collision();
};

// Deterministic Gear-reference controller protocol; host snapshots are active
// high, returned button nibbles active low. No host keyboard/turbo/accessories.
struct Joypad {
    struct Pad { unsigned buttons=2; std::uint16_t pressed=0; };
    bool enabled=false, japanese=true, cd=false, multitap=false;
    bool sel=true, clr=true, extra=false;
    unsigned selected=0;
    std::uint8_t latched=0xF0;
    std::array<Pad,5> pads{};
    std::uint64_t reads=0, writes=0;
    void reset(); // Release buttons/clear protocol; retain device configuration.
    void set_pressed(unsigned slot, unsigned mask);
    void set_type(unsigned slot, unsigned buttons);
    void set_multitap(bool value) { multitap=value; }
    std::uint8_t read();
    void write(std::uint8_t value);
};

struct Interrupts {
    bool enabled=false, timer_enabled=false, timer_pending=false;
    std::uint8_t mask=0, external=0, timer_reload=0, timer_counter=0;
    // The stopped divider retains its reset/control phase without following
    // master time. Reset starts at zero; an enable-state transition reloads
    // 3072. While running, timer_deadline is the authoritative next edge.
    std::uint16_t timer_frozen_phase=0;
    std::uint64_t master_ticks=0, timer_deadline=0, entries=0, reads=0, writes=0;
    void advance_to(std::uint64_t ticks);
};

struct Bus {
    // Explicit analysis sandbox, not a completed PC Engine memory/device model.
    std::array<BankKind,256> kind{};
    std::array<std::uint64_t,256> generation{};
    std::unique_ptr<std::array<std::uint8_t,0x200000>> bytes =
        std::make_unique<std::array<std::uint8_t,0x200000>>();
    CdControl cd;
    Vdc vdc;
    Vce vce;
    Psg psg;
    Adpcm adpcm;
    AudioOutput pcm;
    Joypad joypad;
    Interrupts irq;
    std::uint8_t io_latch=0;
    bool work_ram_mirrors=false;
    SystemCardProfile system_card=SystemCardProfile::none;
    bool system_card_powered=false;
    bool hucard=false, hucard_powered=false;
    std::uint32_t hucard_rom_bytes=0;
    std::array<std::uint8_t,128> hucard_banks{};
    HuCardProfile hucard_profile=HuCardProfile::none;
    std::uint8_t hucard_mapper_latch=0;
    // Guest ROM is read-only. SF2 retains the complete file here while bytes
    // holds only its current physical window. Loader patches update both.
    std::vector<std::uint8_t> hucard_mapper_rom;
    std::unique_ptr<ArcadeCard> arcade_card;
    // Preserve the mapped physical address in code identities. Only storage
    // resolution folds ROM mirrors, base WRAM and explicit cartridge RAM aliases.
    std::uint32_t backing_address(std::uint32_t address) const {
        if(hucard_profile==HuCardProfile::populous && address>=0x80000 && address<0xC0000 &&
           kind[address>>13]==BankKind::ram)
            return 0x80000|(address&0x7FFF);
        if(hucard && address<0x100000 && kind[address>>13]==BankKind::rom)
            return (std::uint32_t(hucard_banks[address>>13])<<13)|(address&0x1FFF);
        if(system_card!=SystemCardProfile::none && address<0x100000 &&
           kind[address>>13]==BankKind::rom) return address&0x3FFFF;
        return work_ram_mirrors && address>=0x1F0000 && address<0x1F8000
            ? 0x1F0000|(address&0x1FFF):address;
    }
    static std::uint32_t physical(const Cpu& cpu, std::uint16_t address) {
        return (static_cast<std::uint32_t>(cpu.mpr[address >> 13]) << 13) | (address & 0x1FFF);
    }
    // Native source locations are compile-time constants. Keep this exact,
    // side-effect-free RAM/ROM check visible to generated translation units so
    // their byte guards do not need an out-of-line call for every source byte.
    // Generations are deliberately not an authority: direct storage mutation
    // must invalidate the same guards as an ordinary guest/loader write.
    std::optional<std::uint8_t> peek(std::uint32_t address) const {
        if(address >= bytes->size()) return std::nullopt;
        if(arcade_card && address>=0x80000 && address<0x88000) return std::nullopt;
        const auto k=kind[address >> 13];
        if(k != BankKind::ram && k != BankKind::rom) return std::nullopt;
        return (*bytes)[backing_address(address)];
    }
    void enable_work_ram_mirrors(); // Configure before loading/execution; not SGX RAM.
    // Explicit deterministic reference-machine startup. Memory setup requires
    // a pristine Bus and a raw 256 KiB ROM. BRAM stays blank/unformatted until
    // the caller explicitly loads an image; no host persistence is implicit.
    void configure_system_card(SystemCardProfile,std::span<const std::uint8_t>,
                               std::uint8_t ram_fill=0);
    // Optional functional Duo expansion, before power-on and device clocks.
    // Physical banks $40..$43 become side-effecting ports, not source RAM.
    void configure_arcade_card_duo(std::uint8_t ram_fill=0);
    // Explicit base-board ROM profile. Decoder policy belongs to the caller;
    // this receives aligned decoded bytes and adds no CD/cartridge RAM.
    void configure_hucard(std::span<const std::uint8_t>,std::uint8_t ram_fill=0);
    // Explicit enhanced board: SF2 has a four-bit address latch and banked
    // ROM; Populous overlays 32 KiB of volatile mirrored cartridge RAM.
    void configure_hucard(HuCardProfile,std::span<const std::uint8_t>,std::uint8_t ram_fill=0);
    // SF2's four-bit address latch; called by translated physical bank-00 writes.
    void select_hucard_bank(std::uint8_t);
    // Setup-only CPU reset, not a live/warm-reset edge. Caller-selected fills
    // represent otherwise unspecified startup state; they are not hardware
    // power-on guarantees. One successful power-on is allowed per Bus; devices
    // must not have advanced their guest clocks before it.
    void power_on_cpu(Cpu&,std::uint8_t register_fill=0,std::uint8_t mpr_fill=0);
    void enable_cd_control(); // Volatile, unformatted BRAM; never loads/saves a file.
    void enable_cd_transport(); // Adds a bounded command/status handshake, no media.
    void enable_vdc(); // Opt-in functional profile, deterministic zero initial state.
    void enable_video(); // Full functional palette/DMA plus raster profile.
    void enable_continuous_video(); // Full video plus guest-clock frame publication.
    void enable_video_timing(); // Adds the master-clock raster profile.
    void enable_joypad(bool japanese=true, bool cd=false);
    void sync(const Cpu& cpu); // Absolute CPU time, rejects clock regression.
    void begin_instruction(Cpu& cpu);
    void enable_interrupts();
    void enable_psg();
    void enable_adpcm();
    void enable_audio_output(AudioProfile profile=AudioProfile::raw,unsigned output_rate=44100,
                             AudioTiming timing=AudioTiming::gear); // Before execution.
    std::uint8_t irq_requests() const;
    void service_interrupt(Cpu& cpu);
    void sample_interrupt(Cpu& cpu);
    void retire(Cpu& cpu, unsigned cycles, bool native);
    void clock_cpu(Cpu& cpu, unsigned cycles); // Progress inside one instruction; no retirement/IRQ entry.
    std::uint8_t read_block(Cpu&, std::uint16_t);
    void write_block(Cpu&, std::uint16_t, std::uint8_t);
    unsigned write_block_timed(Cpu&, std::uint16_t, std::uint8_t, unsigned remaining_base);
    void retire_speed(Cpu& cpu, unsigned divisor, bool native);
    void write_vdc(unsigned port, std::uint8_t value); // ST0/ST1/ST2 bypass MPRs.
    unsigned write_vdc(Cpu& cpu,unsigned port,std::uint8_t value); // Remaining ST base cycles.
    void wait_vdc(Cpu& cpu,unsigned port,bool writing);
    std::uint8_t read(Cpu& cpu, std::uint16_t address);
    void write(Cpu& cpu, std::uint16_t address, std::uint8_t value); // Immediate device access.
    unsigned write_timed(Cpu&, std::uint16_t, std::uint8_t, unsigned remaining_base);
    void load(std::uint32_t address, const std::uint8_t* source, std::size_t count);
};

void push(Bus&, Cpu&, std::uint8_t);
std::uint8_t pop(Bus&, Cpu&);
// Interpreter-only block operation. Generated modules emit their own copy loop.
void interpret_block(Bus&, Cpu&, std::uint8_t opcode);
Exit interpret_step(Bus&, Cpu&, std::uint64_t deadline);
// Defined either by generated code or by the no-module stub. Single-step ABI
// makes invalidation and every instruction boundary observable from day one.
Exit generated_step(Bus&, Cpu&, std::uint64_t deadline);
Exit step(Bus&, Cpu&, std::uint64_t deadline, bool allow_interpreter=true);
const char* exit_name(Exit);
} // namespace pce
