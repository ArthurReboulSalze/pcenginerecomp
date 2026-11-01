#include "pce/cd_timing.hpp"
#include "pce/runtime.hpp"
#include <array>

// Geometry and measured seek model derived from David Shadoff's PCECD_seek:
// https://github.com/pce-devel/PCECD_seek/tree/7b9a70702d2f5422b924ee3cf7d42ff3ae5436ad
// The named gear-distance policy uses the Gear/Mesen 18/48-frame constants
// and exclusive <2-sector branch, rather than the original program's 16/36
// constants and overlapping branches. Integer arithmetic below independently
// expresses that policy, including integer edge-track quotients and whole-ms
// truncation before conversion to master ticks. No GPL implementation is used.
//
// MIT License
// Copyright (c) 2019 David Shadoff
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

namespace pce {
namespace {
struct Zone {std::uint32_t first,last,sectors,rotation_hundredths;};
constexpr std::array<Zone,14> zones{{
    {0,12572,10,13347},{12573,30244,11,14682},
    {30245,49523,12,16017},{49524,70408,13,17351},
    {70409,92900,14,18686},{92901,116998,15,20021},
    {116999,142703,16,21356},{142704,170014,17,22690},
    {170015,198932,18,24025},{198933,229456,19,25360},
    {229457,261587,20,26695},{261588,295324,21,28029},
    {295325,330668,22,29364},{330669,333012,23,30699}
}};
unsigned zone(std::uint32_t lba) {
    for(unsigned i=0;i<zones.size();++i) if(lba<=zones[i].last)return i;
    throw Fault("CD gear-distance timing exceeds calibrated LBA range");
}
std::uint64_t milliseconds(std::uint32_t from,std::uint32_t to) {
    if(from>cd_distance_max_lba || to>cd_distance_max_lba)
        throw Fault("CD gear-distance timing exceeds calibrated LBA range");
    const auto source=zone(from),target=zone(to);
    const auto distance=from>to ? from-to:to-from;
    const auto& a=zones[source];const auto& b=zones[target];
    std::uint64_t tracks;
    if(source==target)tracks=std::uint64_t(distance/b.sectors)*100;
    else if(source<target)
        tracks=std::uint64_t((a.last-from)/a.sectors+(to-b.first)/b.sectors)*100+
               std::uint64_t(target-source-1)*160648;
    else
        tracks=std::uint64_t((from-a.first)/a.sectors+(b.last-to)/b.sectors)*100+
               std::uint64_t(source-target-1)*160648;
    const std::uint64_t rotation=b.rotation_hundredths;
    if(distance<2)return 150;
    if(distance<5)return (150*200+rotation)/200;
    if(tracks<=8000)return (300*200+rotation)/200;
    if(tracks<=16000)return (366*200+rotation)/200;
    if(tracks<=64400)return (366*800000+rotation*4000+(tracks-16100)*1666)/800000;
    return (800*1950000+(tracks-64400)*1666)/1950000;
}
}
std::uint64_t cd_seek_ticks(CdTimingProfile profile,std::uint32_t from,std::uint32_t to) {
    switch(profile) {
    case CdTimingProfile::fixed:return 3221590;
    case CdTimingProfile::gear_distance:return milliseconds(from,to)*21477273/1000;
    }
    throw Fault("invalid CD timing profile");
}
}
