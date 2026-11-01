// Authored invocation of an externally supplied, unchanged reference header.
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include PCE_MESEN_SEEK_HEADER
int main(){std::uint32_t from,to;while(std::cin>>from>>to){const auto ms=PceCdSeekDelay::GetSeekTimeMs(from,to);std::cout<<from<<' '<<to<<' '<<ms<<' '<<std::uint64_t(ms)*21477273/1000<<'\n';}return std::cin.eof()?0:1;}
