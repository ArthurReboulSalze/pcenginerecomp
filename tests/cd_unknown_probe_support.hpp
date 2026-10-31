#pragma once
// Authored register supervisor. Third-party device logic stays in separate binaries.
#include "sense_probe_support.hpp"
#include <sstream>
namespace cd_unknown_probe {
template<class A>std::vector<unsigned> pins(const A& a) {
    return {unsigned(a.busy()),unsigned(a.request()),unsigned(a.input()),unsigned(a.control()),unsigned(a.message())};
}
inline void array(const std::vector<unsigned>& v) {
    std::cout<<'[';for(unsigned i=0;i<v.size();++i)std::cout<<(i?",":"")<<v[i];std::cout<<']';
}
inline void begin(bool& first,const char* kind) {
    if(!first)std::cout<<',';first=false;std::cout<<"{\"kind\":\""<<kind<<'"';
}
template<class A>auto send(A& a,const std::vector<unsigned>& cdb) {
    if(a.busy())throw std::runtime_error("unknown probe requires idle bus");
    a.select();sense_probe::wait_request(a);std::vector<std::vector<unsigned>> edges;
    for(auto byte:cdb) {
        sense_probe::wait_request(a);
        const auto before=pins(a);
        if(before!=std::vector<unsigned>{1,1,0,1,0})throw std::runtime_error("partial CDB left command input");
        a.write_data(byte);a.ack(true);a.advance(1);const auto high=pins(a);
        a.ack(true);a.advance(1);const auto held=pins(a);
        if(high!=std::vector<unsigned>{1,0,0,1,0}||held!=high)throw std::runtime_error("held ACK recaptured or changed command phase");
        a.ack(false);a.advance(1);const auto fall=pins(a);
        auto row=before;row.insert(row.end(),high.begin(),high.end());row.insert(row.end(),held.begin(),held.end());row.insert(row.end(),fall.begin(),fall.end());edges.push_back(row);
    }
    return edges;
}
inline void edge_rows(const std::vector<std::vector<unsigned>>& rows) {
    std::cout<<",\"edges\":[";for(unsigned i=0;i<rows.size();++i){if(i)std::cout<<',';array(rows[i]);}std::cout<<']';
}
template<class A>void pending(A& a,bool& first) {
    if constexpr(requires {a.pending();})reset_probe::record(first,"pending",a.pending());
    else throw std::runtime_error("this reference does not expose pending sense");
}
template<class A>bool operation(A& a,std::istream& plan,const std::string& op,bool& first) {
    if(op=="r") {unsigned mode;if(!(plan>>mode))throw std::runtime_error("reset mode");a.reset(mode);return true;}
    if(op=="p"){pending(a,first);return true;}
    if(op=="z"){a.warm_reset();begin(first,"reset");std::cout<<",\"pins\":";array(pins(a));std::cout<<'}';return true;}
    if(op=="u"||op=="a") {
        unsigned opcode,count,automatic;if(!(plan>>opcode>>count>>automatic)||opcode>255||count>16||automatic>1||(op=="u"&&!count))throw std::runtime_error("unknown CDB operation bound");
        std::vector<unsigned> cdb(count);for(unsigned i=0;i<count;++i)cdb[i]=i?((opcode+37*i)&255):opcode;
        auto edges=send(a,cdb);
        if(op=="a") {
            sense_probe::wait_request(a);if(pins(a)!=std::vector<unsigned>{1,1,0,1,0})throw std::runtime_error("partial CDB dispatched prematurely");
            unsigned buffered=0;if constexpr(requires {a.buffered();})buffered=a.buffered();
            a.warm_reset();begin(first,"abort");std::cout<<",\"opcode\":"<<opcode<<",\"count\":"<<count<<",\"pins\":";array(pins(a));
            if constexpr(requires {a.buffered();})std::cout<<",\"buffered_before_reset\":"<<buffered<<",\"buffered_after_reset\":"<<a.buffered();
            edge_rows(edges);std::cout<<'}';return true;
        }
        const auto reply=sense_probe::drain(a,automatic);begin(first,"unknown");std::cout<<",\"opcode\":"<<opcode<<",\"count\":"<<count<<",\"automatic\":"<<automatic<<",\"status\":"<<reply.status<<",\"message\":"<<reply.message<<",\"data\":";array(reply.data);std::cout<<",\"pins\":";array(pins(a));edge_rows(edges);std::cout<<'}';return true;
    }
    if(op=="c") {
        unsigned automatic,count;if(!(plan>>automatic>>count)||automatic>1||!count||count>16)throw std::runtime_error("CDB shape");
        std::vector<unsigned> cdb(count);for(auto& byte:cdb)if(!(plan>>byte)||byte>255)throw std::runtime_error("CDB byte");
        send(a,cdb);sense_probe::record(first,cdb,automatic,sense_probe::drain(a,automatic));return true;
    }
    return false;
}
}
