// Authored wiring only: unchanged GPL reference objects stay in this executable.
#define Adapter TimingGearBase
#define main prior_authored_timing_sense_main
#include "geargrafx_sense_probe.cpp"
#undef main
#undef Adapter
struct TimingSeekStart {using type=u32 CdRomAudio::*;friend type member(TimingSeekStart);};
template struct Access<TimingSeekStart,&CdRomAudio::m_seek_start_lba>;
#define PCE_TIMING_GEAR
#include "cd_timing_probe.cpp"
