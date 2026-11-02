#pragma once

#include "pce/runtime.hpp"

namespace pce {
using Sector = std::array<std::uint8_t,2048>;
// One Red Book sector: 588 interleaved stereo frames, signed 16-bit values.
// Values are host numeric samples, independent of image or host byte order.
using AudioSector = std::array<std::int16_t,1176>;
// Original captured P-W symbols, excluding the two sync symbols: one byte
// per symbol, bit 7=P, bit 6=Q, through bit 0=W, in disc order. No channel
// deinterleave, CRC repair, TOC synthesis or data/audio byte swapping occurs.
using SubchannelSector = std::array<std::uint8_t,96>;

// Expected guest data-read outcomes are distinct from host/configuration
// faults. Source identity, setup, I/O and decoder-contract failures stay fatal
// Faults; callers must never infer a recoverable category from message text.
enum class SectorReadReason { out_of_range, wrong_data_track, unrecoverable_data, media_data_error };
struct SectorReadError : Fault {
    SectorReadReason reason;
    std::uint32_t lba;
    SectorReadError(SectorReadReason why,std::uint32_t address,const char* message)
        :Fault(message),reason(why),lba(address) {}
};

// Program-area classification, not captured subchannel Q. An absent index
// with known=true means a verified gap/out-of-disc location; known=false
// means this provider supplies no program-range metadata. Track indices are
// zero-based and refer to the provider's attached TOC.
struct ProgramTrackLookup {
    bool known=false;
    std::optional<unsigned> index;
};

// read() accepts user data only. Expected range/track/payload failures throw
// SectorReadError; all other unsupported or host failures retain fatal Fault.
// read_audio() returns stored AUDIO payload only. audio_playable() separately
// describes the reference playback gate, including deliberate data/gap silence.
// An attached provider is single-threaded and never modifies its source image.
class SectorProvider {
public:
    virtual ~SectorProvider() = default;
    virtual Sector read(std::uint32_t lba) = 0;
    virtual AudioSector read_audio(std::uint32_t) {
        throw Fault("Sector provider does not support raw audio sectors");
    }
    virtual bool audio_playable(std::uint32_t) const {
        throw Fault("Sector provider does not classify audio geometry");
    }
    // Pure inspection: no sector read, decoder/cache update or head movement.
    // Legacy/custom providers explicitly retain the TOC-only fallback by
    // leaving metadata unavailable; that is never interpreted as a real gap.
    virtual ProgramTrackLookup program_track(std::uint32_t) const {return {};}
    // Capability means at least one stored extent supplies original raw P-W.
    // It does not promise captured bytes at every LBA or valid Q packets.
    virtual bool has_subchannel() const {return false;}
    // nullopt is explicit absence (including an unstored gap/outside disc),
    // never a synthesized packet. Unsupported representation, decoder errors
    // and changed source identity throw fatal Fault, rather than absence.
    // Custom providers default to unavailable. Reads may update decoder cache
    // but must not move a guest drive head or modify media.
    virtual std::optional<SubchannelSector> read_subchannel(std::uint32_t) {return std::nullopt;}
    virtual const CdToc& toc() const = 0;
};

// ISO: single-track cooked MODE1. CHD: v5 MODE1/MODE1_RAW and AUDIO;
// CUE: bounded BINARY MODE1/2048, MODE1/2352 and little-endian AUDIO files.
// CHD decoding requires an explicitly selected optional libchdr shared library.
// The actual file is SHA256-pinned, metadata bounded, and only one decoded hunk
// (at most 512 KiB) is retained. Source size/mtime changes refuse further reads.
std::shared_ptr<SectorProvider> open_sector_provider(
    const std::string& image, const std::string& libchdr="");
// CUE returns the documented complete-image digest of the exact cue plus every
// referenced file; ISO/CHD retain their raw file SHA256 identity.
std::string image_sha256(const std::string& image);
} // namespace pce
