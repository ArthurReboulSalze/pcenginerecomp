"""Authored guest PSG writes with exact logical PC, full MPR and source bytes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture
from pcerecomp.isa import physical
MPR=(255,248,248,248,248,255,248,0)

def generate(out):
    # opcode, effective base cycles, old DDA, new DDA. Pointer and X/Y=1
    # resolve all indirect/indexed forms to physical PSG port6.
    cases=[('sta-abs',[0x8d,6,8],5,0,31),('stx-abs',[0x8e,6,8],5,0,1),
      ('sty-abs',[0x8c,6,8],5,0,1),('stz-abs',[0x9c,6,8],5,31,0),
      ('sta-abx',[0x9d,5,8],5,0,31),('sta-aby',[0x99,5,8],5,0,31),
      ('sta-idx',[0x81,0x1f],7,0,31),('sta-idy',[0x91,0x22],7,0,31),
      ('sta-zpi',[0x92,0x20],7,0,31),('stz-abx',[0x9e,5,8],5,31,0),
      ('sta-mirror',[0x8d,6,11],5,0,31),('sta-mpr-alias',[0x8d,6,0xa8],5,0,31),
      ('asl',[0x0e,6,8],7,0,30),('rol',[0x2e,6,8],7,0,31),
      ('lsr',[0x4e,6,8],7,0,15),('ror',[0x6e,6,8],7,0,15),
      ('inc',[0xee,6,8],7,31,0),('dec',[0xce,6,8],7,0,30),
      ('asl-abx',[0x1e,5,8],7,0,30),('rol-abx',[0x3e,5,8],7,0,31),
      ('lsr-abx',[0x5e,5,8],7,0,15),('ror-abx',[0x7e,5,8],7,0,15),
      ('inc-abx',[0xfe,5,8],7,31,0),('dec-abx',[0xde,5,8],7,0,30),
      ('tsb',[0x0c,6,8],7,0,31),('trb',[0x1c,6,8],7,31,0)]
    for op,name in [(0x73,'tii'),(0xc3,'tdd'),(0xd3,'tin'),(0xe3,'tia'),(0xf3,'tai')]:
        cases.append((name,[op,0,0x22,6,8,3,0],35,0,31))
        cases.append((name+'-vdc-source',[op,2 if op==0xc3 else 0,0,6,8,3,0],41,31,0))
    observations=[];rows=[]
    for i,(name,data,cycles,old,new) in enumerate(cases):
        pc=0xe100+i*8
        observations.append(dict(pc=pc,mpr=list(MPR),data=data,physical=[physical(pc+j,MPR) for j in range(len(data))],native_hits=0,interpreted_hits=1))
        rows.append('{"%s",%d,%d,%d,%d,%d,{%s}}'%(name,pc,len(data),cycles,old,new,','.join(map(str,data))))
    out.mkdir(parents=True,exist_ok=True)
    capture=dict(schema=1,runtime_abi=ABI,capacity=64,dropped_instructions=0,unreadable_instructions=0,retired_instructions=len(observations),complete=True,observations=observations)
    with TemporaryDirectory(prefix='psg-phase-authored-',dir=out.parent) as scratch:
        generated=Path(scratch)/'module';emit_capture(capture,generated,single_unit=True)
        for source in generated.iterdir():(out/source.name).write_bytes(source.read_bytes())
    (out/'psg_phase_fixture.hpp').write_text('#pragma once\n#include <array>\n#include <cstdint>\ninline constexpr std::array<std::uint8_t,8> phase_mpr{'+','.join(map(str,MPR))+'};\nstruct PhaseCase {const char* name;unsigned pc,size,cycles,old_dda,new_dda;std::array<std::uint8_t,7> data;};\ninline constexpr std::array<PhaseCase,'+str(len(rows))+'> phase_cases{{'+','.join(rows)+'}};\n')
if __name__=='__main__':generate(Path(sys.argv[1]))
