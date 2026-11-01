// Authored caller of the independently implemented production timing profile.
#include "pce/cd_timing.hpp"
#include <cstdint>
#include <exception>
#include <iostream>
int main(){std::uint32_t from,to;while(std::cin>>from>>to){try{auto ticks=pce::cd_seek_ticks(pce::CdTimingProfile::gear_distance,from,to);std::cout<<from<<' '<<to<<" ok "<<ticks<<'\n';}catch(const std::exception&){std::cout<<from<<' '<<to<<" refused 0\n";}}return std::cin.eof()?0:1;}
