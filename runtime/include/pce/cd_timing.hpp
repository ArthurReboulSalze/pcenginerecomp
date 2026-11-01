#pragma once
#include <cstdint>

namespace pce {
// Named drive models, independent of audio synthesis and CPU speed.
enum class CdTimingProfile : std::uint8_t { fixed, gear_distance };
inline constexpr std::uint32_t cd_distance_max_lba=333012;

// Seek only; READ adds its sector period separately. The distance profile is
// calibrated only within [0, cd_distance_max_lba] and refuses other locations.
// The fixed profile retains the historical 150 ms regardless of geometry.
std::uint64_t cd_seek_ticks(CdTimingProfile,std::uint32_t from,std::uint32_t to);
}
