"""Authored SCSI port sites plus readable CDDA latch instructions."""
from pathlib import Path
from generate_scsi_fixture import make_fixture as original_fixture
from pcerecomp.analysis import Snapshot,analyze
from pcerecomp.emitter import emit

def make_fixture():
    original,sites=original_fixture();memory=dict(original.memory);sites=[*sites,(0x2b00,0xad,0x1805),(0x2b08,0xad,0x1806)]
    for pc,op,address in sites[-2:]:
        for i,value in enumerate((op,address&255,address>>8,0x80,0xfe)):memory[0x1f0000+(pc&8191)+i]=value
    return Snapshot(original.mpr,memory,tuple(pc for pc,_,_ in sites),'authored-distance-cd-ports-v1'),sites

def generate(out):
    out=Path(out);snapshot,sites=make_fixture();emit(analyze(snapshot),out)
    header=['#pragma once','#include <array>','#include <utility>','#include <cstdint>',
      'inline constexpr std::array<std::uint8_t,8> scsi_mpr{'+','.join(map(str,snapshot.mpr))+'};',
      'struct ScsiCase {std::uint16_t pc;std::uint8_t op;std::uint16_t address;};',
      f'inline constexpr std::array<ScsiCase,{len(sites)}> scsi_cases{{{{'+','.join('{'+','.join(map(str,s))+'}'for s in sites)+'}};',
      f'inline constexpr std::array<std::pair<std::uint32_t,std::uint8_t>,{len(snapshot.memory)}> scsi_program{{{{'+','.join('{'+str(p)+','+str(v)+'}'for p,v in sorted(snapshot.memory.items()))+'}};']
    (out/'scsi_fixture.hpp').write_text('\n'.join(header)+'\n')
