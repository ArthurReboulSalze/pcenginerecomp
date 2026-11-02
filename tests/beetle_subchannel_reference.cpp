// Authored adapter; complete unmodified private upstream TUs are included.
// This directly exercises decoding/latches and DD construction, not clocks,
// guest execution, a real image reader, or the PCE byte/IRQ FIFO.
#include <array>
#include <fstream>
#include <iostream>
#include "CDUtility.cpp"
#include "scsicd.cpp"
void CDIRQ(int){}
void StuffSubchannel(uint8_t,int){}
// These external data-sector services are outside this adapter. They fail
// explicitly if a future change accidentally enters them; Q CRC stays the
// actual original CDUtility.cpp implementation.
bool Init_LEC_Correct(){throw std::runtime_error("LEC outside captured-Q scope");}
void lec_encode_mode0_sector(uint32_t,uint8_t*){throw std::runtime_error("LEC outside captured-Q scope");}
void lec_encode_mode1_sector(uint32_t,uint8_t*){throw std::runtime_error("LEC outside captured-Q scope");}
void lec_encode_mode2_sector(uint32_t,uint8_t*){throw std::runtime_error("LEC outside captured-Q scope");}
void lec_encode_mode2_form1_sector(uint32_t,uint8_t*){throw std::runtime_error("LEC outside captured-Q scope");}
void lec_encode_mode2_form2_sector(uint32_t,uint8_t*){throw std::runtime_error("LEC outside captured-Q scope");}
int CheckEDC(const unsigned char*,bool){throw std::runtime_error("EDC outside captured-Q scope");}
int ValidateRawSector(unsigned char*,bool){throw std::runtime_error("ECC outside captured-Q scope");}
template<class T> void values(const T&v){for(auto b:v)std::cout<<','<<unsigned(b);}
int main(int argc,char**argv) {
    try {
        if(argc!=2)throw std::runtime_error("usage: beetle-subchannel PLAN");
        std::ifstream in(argv[1]);if(!in)throw std::runtime_error("missing plan");
        SimpleFIFO<uint8_t> fifo(8192);din=&fifo;
        std::string op;bool first=true;std::cout<<'[';
        while(in>>op) {
            if(op=="r"){std::memset(&cd,0,sizeof(cd));fifo.Flush();continue;}
            if(op!="q")throw std::runtime_error("unknown authored operation");
            unsigned status;if(!(in>>status)||status>2)throw std::runtime_error("status bound");
            for(auto&b:cd.SubPWBuf){unsigned v;if(!(in>>v)||v>255)throw std::runtime_error("raw96 extent");b=v;}
            std::array<uint8_t,12> decoded{};subq_deinterleave(cd.SubPWBuf,decoded.data());
            const bool valid=subq_check_checksum(decoded.data());GenSubQFromSubPW();
            cdda.CDDAStatus=status==0?CDDASTATUS_STOPPED:status==1?CDDASTATUS_PAUSED:CDDASTATUS_PLAYING;
            fifo.Flush();uint8_t command[10]={0xDD};DoNEC_PCE_READSUBQ(command);
            if(fifo.in_count!=10)throw std::runtime_error("DD extent");
            std::array<uint8_t,10> response{};for(auto&b:response)b=fifo.ReadByte();
            if(!first)std::cout<<',';first=false;std::cout<<'['<<int(valid);
            values(decoded);values(cd.SubQBuf_Last);values(cd.SubQBuf[1]);values(response);std::cout<<']';
        }
        std::cout<<"]\n";return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
