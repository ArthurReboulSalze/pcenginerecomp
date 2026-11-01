#include "pce/cdda.hpp"
#include "pce/runtime.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <limits>

namespace pce {
namespace {
constexpr unsigned busy_phase=8;
constexpr std::uint64_t resume_ticks=4810909;
std::uint64_t after(std::uint64_t now,std::uint64_t delta) {
    if(delta>std::numeric_limits<std::uint64_t>::max()-now) throw Fault("CD audio clock overflow");
    return now+delta;
}
unsigned from_bcd(unsigned value) {
    if((value&15)>9 || (value>>4)>9) throw Fault("invalid BCD CD audio address");
    return (value>>4)*10+(value&15);
}
unsigned bcd(unsigned value) {return (value/10)*16+value%10;}
std::uint32_t audio_lba(const CdToc& toc,const Scsi& scsi) {
    const auto& c=scsi.command;
    switch(c[9]&192) {
    case 0: return (unsigned(c[3])<<16)|(unsigned(c[4])<<8)|c[5];
    case 64: {
        const auto m=from_bcd(c[2]),s=from_bcd(c[3]),f=from_bcd(c[4]);
        if(s>=60 || f>=75) throw Fault("invalid CD audio MSF range");
        const auto frames=(m*60+s)*75+f;
        if(frames<150) throw Fault("CD audio lead-in addressing is not implemented");
        return frames-150;
    }
    case 128: {
        const auto track=from_bcd(c[2]);
        if(!track) return 0;
        if(track>toc.track_count) throw Fault("CD audio track is outside attached TOC");
        return toc.tracks[track-1].index1_lba;
    }
    default: throw Fault("unsupported CD audio address mode");
    }
}
void next_sector(CdAudio& audio,std::uint64_t now) {
    auto delta=std::uint64_t{286363};
    audio.sector_fraction+=48;
    if(audio.sector_fraction>=75) {audio.sector_fraction-=75;++delta;}
    audio.sector_deadline=after(now,delta);
}
void msf(std::array<std::uint8_t,2048>& response,unsigned offset,std::uint32_t frames) {
    response[offset]=static_cast<std::uint8_t>(bcd(frames/4500));
    response[offset+1]=static_cast<std::uint8_t>(bcd(frames/75%60));
    response[offset+2]=static_cast<std::uint8_t>(bcd(frames%75));
}
ProgramTrackLookup program_location(const CdToc& toc,const std::shared_ptr<SectorProvider>& provider,
                                   std::uint32_t lba) {
    const auto result=provider ? provider->program_track(lba):ProgramTrackLookup{};
    if(!result.known && result.index)
        throw Fault("CD provider returned an unknown program position with a track");
    if(result.index) {
        const auto index=*result.index;
        if(index>=toc.track_count || lba>=toc.leadout_lba || toc.tracks[index].index1_lba>lba ||
           (index+1<toc.track_count && lba>=toc.tracks[index+1].index1_lba))
            throw Fault("CD provider program track disagrees with attached TOC");
    }
    return result;
}
}
void CdAudio::reschedule() {
    deadline=0;
    for(auto time:{seek_deadline,sector_deadline,playback_deadline})
        if(time && (!deadline || time<deadline)) deadline=time;
}
void CdAudio::stop(bool idle) {
    state=idle ? 1:3;
    deadline=seek_deadline=sector_deadline=playback_deadline=0;
    sector_fraction=0;
}
void CdAudio::latch_sample(std::uint64_t ticks) {
    if(ticks<sample_last_latch) throw Fault("CD sample latch clock regression");
    if(ticks-sample_last_latch<700) return;
    if(!sample_valid) throw Fault("CD sample latch requires a sector provider for the held sample");
    sample_last_latch=ticks;
    sample_right=!sample_right;
    sample_latch=static_cast<std::uint16_t>(sample_held[sample_right ? 1:0]);
}
void CdControl::write_fader(std::uint8_t value) {
    audio.fader=value;audio.fade_start=scsi.master_ticks;
    audio.fade_duration=(value&4) ? 53693182:139602274;
}
double CdControl::fader_gain(bool adpcm) const {
    if(!(audio.fader&8) || bool(audio.fader&2)!=adpcm) return 1.0;
    if(scsi.master_ticks<audio.fade_start) throw Fault("CD fader clock regression");
    const auto elapsed=scsi.master_ticks-audio.fade_start;
    if(!audio.fade_duration || elapsed>=audio.fade_duration) return 0.0;
    return 1.0-static_cast<double>(elapsed)/static_cast<double>(audio.fade_duration);
}
void CdControl::audio_command() {
    const auto op=scsi.command[0];
    std::optional<std::uint32_t> start;
    std::uint64_t seek_end=0,playback_end=0;
    if(toc && op==0xD8) {
        start=audio_lba(*toc,scsi);
        if(*start<toc->leadout_lba) {
            const auto location=program_location(*toc,provider,*start);
            if(location.known && !location.index) {
                // A non-program start is not admitted by the selected Gear
                // profile. Preserve the entire audio/source timeline, including
                // its command sequence: that sequence also controls PCM tails.
                // The controller still applies its ordinary mode/retained-seek
                // decision; a playing request can remain BUSY without an event.
                if(!scsi.command[1] && !audio.seek_deadline)start_status(0);
                else phase(busy_phase);
                return;
            }
            const auto duration=cd_seek_ticks(timing_profile,scsi.current_lba,*start);
            const bool split=timing_profile==CdTimingProfile::gear_distance && duration>resume_ticks;
            // Admission is transactional with respect to the active audio
            // timeline: both deadline sums must fit before stop()/head writes.
            seek_end=after(scsi.master_ticks,split ? duration-resume_ticks:duration);
            if(split && scsi.command[1])playback_end=after(scsi.master_ticks,duration);
        }
    }
    // A paused resume starts its fixed playback delay after any remaining
    // physical seek. Validate overflow before changing the end/mode/state.
    if(toc && op==0xD9 && scsi.command[1]>=1 && scsi.command[1]<=3 && audio.state==2)
        playback_end=after(std::max(scsi.master_ticks,audio.seek_deadline),resume_ticks);
    ++audio.commands;
    if(!toc) {check_condition(2,0x0B);return;}
    const auto now=scsi.master_ticks;
    if(op==0xDA) {
        audio.state=2;audio.sector_deadline=audio.playback_deadline=0;
        audio.reschedule();start_status(0);return;
    }
    if(op==0xDD) {
        const auto lba=audio.state==1 ? scsi.current_lba:
            (audio.state==0 && audio.seek_deadline ? audio.seek_start_lba:audio.current_lba);
        int track=-1;
        const auto location=program_location(*toc,provider,lba);
        if(location.known) {
            if(location.index)track=static_cast<int>(*location.index);
        } else {
            // A metadata-only TOC or legacy custom provider cannot distinguish
            // gaps. Preserve that declared approximation, not an invented gap.
            for(unsigned i=0;i<toc->track_count && toc->tracks[i].index1_lba<=lba;++i) track=static_cast<int>(i);
        }
        scsi.response.fill(0);scsi.response_size=10;scsi.response_index=0;
        scsi.response[0]=static_cast<std::uint8_t>(audio.state==0 && audio.seek_deadline ? 2:audio.state);
        scsi.response[1]=static_cast<std::uint8_t>(track>=0 && toc->tracks[track].type==4 ? 0x41:1);
        scsi.response[2]=static_cast<std::uint8_t>(bcd(static_cast<unsigned>(track+1)));
        scsi.response[3]=1;
        msf(scsi.response,4,track>=0 ? lba-toc->tracks[track].index1_lba:0);
        msf(scsi.response,7,lba+150);
        schedule(6,3000);return;
    }
    const auto lba=start ? *start:audio_lba(*toc,scsi);
    if(op==0xD8) {
        if(lba>=toc->leadout_lba) {check_condition(5,0x25,0,lba);return;}
        audio.stop();audio.start_lba=audio.current_lba=lba;
        audio.seek_start_lba=scsi.current_lba;scsi.current_lba=lba;
        audio.stop_lba=toc->leadout_lba-1;audio.stop_mode=0;
        audio.state=scsi.command[1]==0 ? 2:0;
        audio.seek_deadline=seek_end;audio.playback_deadline=playback_end;
        audio.reschedule();phase(busy_phase);return;
    }
    if(op!=0xD9) throw Fault("unsupported CD audio command");
    const auto mode=scsi.command[1];
    if(mode>3) throw Fault("unsupported CD audio stop mode");
    if(mode==0) {
        // StopAudio leaves an already pending physical seek countdown intact;
        // bus reset and READ's SetIdle use the stronger stop() cancellation.
        audio.state=3;audio.sector_deadline=audio.playback_deadline=0;
        audio.reschedule();start_status(0);return;
    }
    audio.stop_lba=std::min(lba,toc->leadout_lba-1);
    audio.stop_mode=mode==1 ? 1:mode==2 ? 2:0;
    const bool paused=audio.state==2;
    audio.state=0;
    if(paused) {
        audio.sector_deadline=0;
        audio.playback_deadline=playback_end;
    } else if(!audio.seek_deadline && !audio.sector_deadline && !audio.playback_deadline)
        next_sector(audio,now);
    audio.reschedule();
    if(mode==1 || mode==2) phase(busy_phase);else start_status(0);
}
void CdControl::audio_event() {
    const auto now=scsi.master_ticks;
    if(audio.seek_deadline && audio.seek_deadline<=now) {
        audio.seek_deadline=0;
        if(scsi.phase==busy_phase) start_status(0);
        if(audio.state==0 && !audio.playback_deadline) next_sector(audio,now);
    }
    if(audio.playback_deadline && audio.playback_deadline<=now) {
        audio.playback_deadline=0;
        if(audio.state==0 && !audio.seek_deadline) next_sector(audio,now);
    }
    if(audio.sector_deadline && audio.sector_deadline<=now) {
        audio.sector_deadline=0;
        if(audio.state==0) {
            ++audio.sectors_played;++audio.current_lba;
            if(audio.current_lba>audio.stop_lba) {
                if(toc && audio.current_lba>=toc->leadout_lba) audio.current_lba=toc->leadout_lba-1;
                if(audio.stop_mode==1) audio.current_lba=audio.start_lba;
                else {
                    audio.state=3;
                    if(audio.stop_mode==2) start_status(0);
                }
            }
            scsi.current_lba=audio.current_lba;
            if(audio.state==0) next_sector(audio,now);
        }
    }
    audio.reschedule();
}
} // namespace pce
