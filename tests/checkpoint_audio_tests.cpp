// Authored checkpoint fixtures: no firmware, media excerpts or external saves.
#include "pce/checkpoint_audio.hpp"
#include "pce/checkpoint_archive.hpp"
#include "pce/sector.hpp"
#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
unsigned checks=0;
void require(bool ok,const char* message) {++checks;if(!ok)throw std::runtime_error(message);}
template<class F> void refuses(F operation) {
    bool rejected=false;try {operation();}catch(const std::exception&) {rejected=true;}
    require(rejected,"invalid audio checkpoint was accepted");
}
struct Media final:pce::SectorProvider {
    pce::CdToc geometry;
    unsigned audio_reads=0,data_reads=0;
    Media() {geometry.track_count=2;geometry.tracks[0]={0,0};geometry.tracks[1]={10,4};geometry.leadout_lba=30;}
    const pce::CdToc& toc() const override {return geometry;}
    bool audio_playable(std::uint32_t lba) const override {return lba<10;}
    pce::AudioSector read_audio(std::uint32_t lba) override {
        ++audio_reads;pce::AudioSector out{};
        for(unsigned i=0;i<out.size();++i)out[i]=static_cast<std::int16_t>((i*53+lba*997)%65536-32768);
        return out;
    }
    pce::Sector read(std::uint32_t lba) override {
        ++data_reads;pce::Sector out{};
        for(unsigned i=0;i<out.size();++i)out[i]=static_cast<std::uint8_t>(i*7+lba);
        return out;
    }
};
std::shared_ptr<Media> configure(pce::Bus& bus,pce::AudioProfile profile,unsigned rate,pce::AudioTiming timing) {
    bus.enable_adpcm();auto media=std::make_shared<Media>();bus.cd.set_sector_provider(media);
    bus.enable_audio_output(profile,rate,timing);
    bus.psg.write(1,255);bus.psg.write(0,0);bus.psg.write(5,255);
    for(unsigned i=0;i<32;++i)bus.psg.write(6,static_cast<std::uint8_t>((i*13)&31));
    bus.psg.write(2,71);bus.psg.write(3,1);bus.psg.write(4,159);
    bus.psg.write(0,1);bus.psg.write(5,255);
    for(unsigned i=0;i<32;++i)bus.psg.write(6,static_cast<std::uint8_t>((i*7+3)&31));
    bus.psg.write(2,137);bus.psg.write(4,159);bus.psg.write(8,3);bus.psg.write(9,1);
    bus.psg.write(0,4);bus.psg.write(5,255);bus.psg.write(4,159);bus.psg.write(7,137);
    auto& ad=bus.adpcm;ad.playing=true;ad.control=32;ad.length=4000;ad.sample_rate=13;
    for(unsigned i=0;i<ad.ram.size();++i)ad.ram[i]=static_cast<std::uint8_t>(i*37+0x73);
    auto& cd=bus.cd.audio;cd.state=0;cd.start_lba=0;cd.current_lba=0;cd.stop_lba=9;
    cd.stop_mode=1;cd.sector_deadline=286363;cd.reschedule();
    return media;
}
std::vector<std::uint8_t> encode(const pce::Bus& bus) {
    pce::checkpoint::Writer out;pce::checkpoint::write_audio(out,bus);return std::move(out.data);
}
void restore(const std::vector<std::uint8_t>& data,pce::Bus& bus) {
    pce::checkpoint::Reader in(data);pce::checkpoint::read_audio(in,bus);in.finish();
}
void continuation(pce::AudioProfile profile,unsigned rate,pce::AudioTiming timing) {
    auto original=std::make_unique<pce::Bus>();auto source=configure(*original,profile,rate,timing);
    original->pcm.advance_to(*original,100000);
    original->cd.write_fader(10);
    original->adpcm.read(10);original->adpcm.write(10,0x5b,&original->cd);
    // A held automatic DATA IN ACK, a partial CDB and a future occupied-buffer
    // retry are independent of the already active CDDA sample cursor/cache.
    auto& scsi=original->cd.scsi;
    scsi.phase=4;scsi.signals=0x8a;original->cd.ack=true;
    scsi.auto_ack_deadline=100021;scsi.response_size=2048;scsi.response_index=17;
    scsi.data=113;scsi.load_lba=10;scsi.load_remaining=2;scsi.load_deadline=101000;scsi.read_active=true;
    scsi.command={8,0,0,10,2,0};scsi.command_size=3;
    for(unsigned i=0;i<scsi.response.size();++i)scsi.response[i]=static_cast<std::uint8_t>(i*7+1);
    original->adpcm.write(11,3,&original->cd);
    original->cd.pending_sense={3,0x11,5,7,13};
    const auto before=encode(*original);
    const auto reads=source->audio_reads;
    require(encode(*original)==before,"saving changed audio state");
    require(source->audio_reads==reads && source->data_reads==0,"saving read external media");
    auto resumed=std::make_unique<pce::Bus>();auto destination=configure(*resumed,profile,rate,timing);
    restore(before,*resumed);
    require(destination->audio_reads==0 && destination->data_reads==0,"loading read external media");
    require(encode(*resumed)==before,"audio state did not round-trip exactly");
    original->pcm.advance_to(*original,100500);resumed->pcm.advance_to(*resumed,100500);
    require(destination->audio_reads==0,"restored CDDA cache was discarded");
    require(encode(*resumed)==encode(*original),"next audio edge changed after restoration");
    require(resumed->pcm.drain()==original->pcm.drain(),"pending output queue changed after restoration");
    for(auto tick:{101010ULL,286363ULL,300007ULL,900001ULL,5000000ULL}) {
        original->pcm.advance_to(*original,tick);resumed->pcm.advance_to(*resumed,tick);
        require(encode(*resumed)==encode(*original),"CD/ADPCM/PSG/DSP continuation differs");
    }
    require(resumed->pcm.queued_frames()==pce::AudioOutput::capacity,"fixture did not wrap PCM ring");
    const auto wrapped=encode(*resumed);
    auto third=std::make_unique<pce::Bus>();configure(*third,profile,rate,timing);restore(wrapped,*third);
    require(third->pcm.drain()==resumed->pcm.drain(),"wrapped PCM queue was not preserved");
    require(resumed->pcm.drain().empty(),"queue draining manufactured output");
    original->pcm.drain();
    resumed->pcm.advance_to(*resumed,5100000);third->pcm.advance_to(*third,5100000);
    require(encode(*third)==encode(*resumed),"wrapped queue/DSP state diverged after next samples");
    // Presence, quirk, DAC profile and output timing are immutable bindings.
    auto configured=std::make_unique<pce::Bus>();configure(*configured,profile,rate,timing);
    pce::checkpoint::validate_audio_configuration(*resumed,*configured);
    configured->psg.centered_dac=false;
    refuses([&]{pce::checkpoint::validate_audio_configuration(*resumed,*configured);});
    configured->psg.centered_dac=true;configured->cd.unknown_policy=pce::CdUnknownPolicy::gear_good;
    refuses([&]{pce::checkpoint::validate_audio_configuration(*resumed,*configured);});
    auto truncated=before;truncated.pop_back();
    refuses([&]{restore(truncated,*configured);});
}
void binding_and_bounds() {
    auto bus=std::make_unique<pce::Bus>();auto media=configure(*bus,pce::AudioProfile::raw,44100,pce::AudioTiming::gear);
    bus->pcm.advance_to(*bus,1000);
    const auto bytes=encode(*bus);
    auto unbound=std::make_unique<pce::Bus>();
    refuses([&]{restore(bytes,*unbound);});
    auto foreign=std::make_shared<Media>();bus->cd.audio.source_cursor.source=foreign;
    refuses([&]{encode(*bus);});
    foreign.reset();refuses([&]{encode(*bus);});
    bus->cd.audio.source_cursor.source=media;
    bus->adpcm.decoder_index=49;refuses([&]{encode(*bus);});bus->adpcm.decoder_index=0;
    bus->psg.channels[0].wave_index=32;refuses([&]{encode(*bus);});bus->psg.channels[0].wave_index=0;
    bus->cd.scsi.response_index=2049;refuses([&]{encode(*bus);});
    bus->cd.scsi.response_index=0;bus->adpcm.read_deadline=bus->adpcm.master_ticks;
    refuses([&]{encode(*bus);});bus->adpcm.read_deadline=0;
    bus->cd.scsi.event=2;refuses([&]{encode(*bus);});bus->cd.scsi.event=0;
    bus->cd.audio.sample_next_tick=bus->cd.audio.sample_clock_ticks;
    refuses([&]{encode(*bus);});
    // CDDA-only mode creates an opaque cache despite PCM output being disabled.
    auto silent=std::make_unique<pce::Bus>();silent->enable_adpcm();silent->cd.set_sector_provider(std::make_shared<Media>());
    silent->cd.audio.state=0;silent->cd.audio.stop_lba=9;silent->cd.audio.sector_deadline=286363;silent->cd.audio.reschedule();
    silent->pcm.advance_to(*silent,10000);
    auto other=std::make_unique<pce::Bus>();other->enable_adpcm();other->cd.set_sector_provider(std::make_shared<Media>());
    restore(encode(*silent),*other);silent->pcm.advance_to(*silent,11000);other->pcm.advance_to(*other,11000);
    require(encode(*silent)==encode(*other),"disabled-output CDDA source continuation differs");
    auto empty=std::make_unique<pce::Bus>();auto empty_copy=std::make_unique<pce::Bus>();
    restore(encode(*empty),*empty_copy);require(encode(*empty)==encode(*empty_copy),"default audio state differs");
}
}
int main() {try {
    continuation(pce::AudioProfile::raw,44100,pce::AudioTiming::gear);
    continuation(pce::AudioProfile::raw,44100,pce::AudioTiming::legacy);
    continuation(pce::AudioProfile::filtered,44100,pce::AudioTiming::gear);
    continuation(pce::AudioProfile::filtered,48000,pce::AudioTiming::gear);
    continuation(pce::AudioProfile::filtered,48000,pce::AudioTiming::legacy);
    binding_and_bounds();
    std::cout<<checks<<" authored audio/CD checkpoint round-trip and continuation checks passed\n";
}catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}}
