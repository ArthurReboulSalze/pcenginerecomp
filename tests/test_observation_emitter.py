"""Authored mixed-ABI profile translation; historical counts are not execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture, emit_observation_profile
from pcerecomp.observations import compose_observation_profile, observation_profile_provenance
from tests.test_capture import MPR, capture, observation

ROOT = Path(__file__).resolve().parent.parent
COMPILER = shutil.which('clang++') or shutil.which('g++')


def inputs(root):
    other = MPR.copy(); other[3] = 140
    old = capture([observation(native=2, interpreted=3),
                   observation(0x4002, (0xe8,)),
                   observation(0x4003, (0x4c, 0, 0x40))])
    old['runtime_abi'] = 18
    new = capture([observation(native=4, interpreted=1),
                   observation(raw=(0xa9, 43)),
                   observation(mpr=other),
                   observation(0x4006, (0x0b,))])
    new['runtime_abi'] = 26
    new['checkpoint_origin'] = dict(sha256='a'*64, ticks=900,
        frame=7, native_steps=80, interpreter_steps=20)
    paths = []
    for name, value in (('old', old), ('new', new)):
        path = root/(name+'.json')
        path.write_text(json.dumps(value), encoding='utf-8')
        paths.append(path)
    return paths


class ObservationEmissionTests(unittest.TestCase):
    def test_provenance_counts_and_source_are_distinct_from_new_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); paths=inputs(root)
            profile=compose_observation_profile(paths); original=copy.deepcopy(profile)
            manifest=emit_observation_profile(profile, root/'generated', 'b'*64)
            self.assertEqual(manifest['runtime_abi'], ABI)
            self.assertEqual(manifest['observation_profile_sha256'], 'b'*64)
            self.assertEqual(manifest['observation_profile_format'], 'pce-observation-profile-1')
            self.assertEqual(manifest['observation_profile_schema'], 1)
            self.assertEqual(manifest['observation_inputs'], observation_profile_provenance(profile))
            self.assertEqual({p['runtime_abi'] for p in manifest['observation_inputs']}, {18,26})
            self.assertEqual([p['checkpoint_origin'] for p in manifest['observation_inputs']
                              if 'checkpoint_origin' in p], [dict(sha256='a'*64, ticks=900,
                                frame=7, native_steps=80, interpreter_steps=20)])
            self.assertEqual(manifest['historical_totals'], dict(native_hits=6,
                interpreted_hits=9, retired_instructions=15))
            self.assertEqual(manifest['observed_instructions'],6)
            self.assertEqual(manifest['native_instructions_emitted'],5)
            self.assertEqual(manifest['unsupported_observations'],1)
            self.assertFalse(manifest['execution_evidence'])
            for key in ('capture_runtime_abi', 'code_capture_sha256', 'capture_checkpoint_origin',
                        'capture_execution_window', 'capture_retired_instructions', 'captured_native_hits'):
                self.assertNotIn(key,manifest)
            source=(root/'generated/module.cpp').read_text()
            self.assertIn(f'static_assert(abi_version == {ABI});',source)
            self.assertIn('s.a=42;',source);self.assertIn('s.a=43;',source)
            self.assertNotIn('interpret_step(',source)
            self.assertEqual(profile,original)
            for path in paths:
                bound=next(p for p in manifest['observation_inputs']
                           if p['sha256']==hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(bound['size_bytes'],path.stat().st_size)

    def test_determinism_and_stable_capture_source_conservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); paths=inputs(root)
            first=compose_observation_profile(paths)
            second=compose_observation_profile(list(reversed(paths)))
            one=emit_observation_profile(first,root/'one',partition_layout='stable',native_span=True)
            two=emit_observation_profile(second,root/'two',partition_layout='stable',native_span=True)
            self.assertEqual(one,two)
            for path in (root/'one').iterdir():
                self.assertEqual(path.read_bytes(),(root/'two'/path.name).read_bytes())
            # Translation depends on admitted exact identities, never their historical
            # producer ABI or hit counts. This separate authored one-capture control
            # compares generated sources; it is not a profile-to-capture API.
            rows=[{k:v for k,v in item.items() if k!='contributions'} for item in first['observations']]
            single=capture(rows);single['runtime_abi']=26
            old=emit_capture(single,root/'single',partition_layout='stable',native_span=True)
            self.assertEqual(one['native_instructions_emitted'],old['native_instructions_emitted'])
            for path in (root/'one').iterdir():
                if path.suffix in ('.cpp','.hpp'):
                    self.assertEqual(path.read_bytes(),(root/'single'/path.name).read_bytes())

    def test_exclusions_preserve_original_provenance_and_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); profile=compose_observation_profile(inputs(root))
            manifest=emit_observation_profile(profile,root/'generated',
                exclude_ranges=[(0x100001,1)],partition_size=1)
            self.assertEqual(manifest['excluded_observations'],3)
            self.assertEqual(manifest['excluded_retired_hits'],12)
            self.assertEqual(manifest['native_instructions_emitted'],2)
            self.assertEqual(manifest['unsupported_observations'],1)
            self.assertEqual(manifest['historical_totals'],profile['historical_totals'])
            self.assertEqual(manifest['observation_inputs'],observation_profile_provenance(profile))

    def test_tampering_digest_options_and_existing_output_refuse_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); profile=compose_observation_profile(inputs(root))
            changed=copy.deepcopy(profile);changed['observations'][0]['native_hits']+=1
            for value,options in ((changed,{}),(profile,dict(profile_sha256='A'*64)),
                (profile,dict(partition_size=True)),(profile,dict(native_span=True)),
                (profile,dict(exclude_ranges=[(0x1fffff,2)]))):
                out=root/'refused'
                with self.subTest(options=options),self.assertRaises(ValueError):
                    emit_observation_profile(value,out,**options)
                self.assertFalse(out.exists())
            out=root/'existing';out.mkdir();(out/'sentinel').write_bytes(b'keep')
            with self.assertRaises(ValueError):emit_observation_profile(profile,out)
            self.assertEqual((out/'sentinel').read_bytes(),b'keep')
            self.assertEqual([p.name for p in out.iterdir()],['sentinel'])

    @unittest.skipUnless(shutil.which('cmake') and shutil.which('ninja') and COMPILER,
                         'CMake/Ninja/C++ compiler required for actual mixed-profile execution')
    def test_actual_native_module_preserves_variants_and_full_context_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);profile=compose_observation_profile(inputs(root))
            manifest=emit_observation_profile(profile,root/'module',partition_layout='stable',native_span=True)
            self.assertEqual(manifest['native_instructions_emitted'],5)
            (root/'guard.cpp').write_text(r'''// Independently specified authored dispatch results.
#include "pce/runtime.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    try {
        pce::Bus bus; bus.kind[0x80]=pce::BankKind::ram;
        const unsigned char program[]={0xa9,42,0xe8,0x4c,0,0x40,0x0b};
        for(unsigned i=0;i<sizeof(program);++i) (*bus.bytes)[0x100000+i]=program[i];
        pce::Cpu s; s.pc=0x4000;
        const auto deadline=std::numeric_limits<std::uint64_t>::max();
        unsigned checks=0;
        auto require=[&](bool value) {++checks;if(!value) throw std::runtime_error("mixed profile guard failure");};
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.a==42 && s.pc==0x4002 && s.native_steps==1 && s.interpreter_steps==0);
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.x==1 && s.pc==0x4003 && s.native_steps==2);
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.pc==0x4000 && s.native_steps==3);
        (*bus.bytes)[0x100001]=43;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.a==43 && s.pc==0x4002 && s.native_steps==4);
        s.pc=0x4000;s.mpr[3]=140;(*bus.bytes)[0x100001]=42;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.a==42 && s.pc==0x4002 && s.native_steps==5);
        require(s.interpreter_steps==0 && s.cycles==12 && s.ticks==36);
        s.pc=0x4000;(*bus.bytes)[0x100001]=43;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::miss);
        require(s.pc==0x4000 && s.native_steps==5 && s.cycles==12 && s.ticks==36);
        (*bus.bytes)[0x100001]=42;s.mpr[0]=254;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::miss);
        s.mpr[0]=255;s.mpr[3]=129;(*bus.bytes)[0x100000]=0xa2;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::miss);
        (*bus.bytes)[0x100000]=0xa9;s.pc=0x4006;
        require(pce::generated_step(bus,s,deadline)==pce::Exit::miss);
        s.pc=0x4000;
        require(pce::generated_step(bus,s,s.ticks)==pce::Exit::budget);
        require(s.native_steps==5 && s.interpreter_steps==0 && s.cycles==12 && s.ticks==36);
        std::cout<<"{\"checks\":"<<checks<<",\"native\":"<<s.native_steps
                 <<",\"interpreted\":"<<s.interpreter_steps<<",\"cycles\":"<<s.cycles
                 <<",\"ticks\":"<<s.ticks<<"}\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
''',encoding='utf-8')
            (root/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.20)
project(MixedProfileTests LANGUAGES CXX)
set(PCE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory("{ROOT.as_posix()}" tool)
pce_add_native_module(native_objects MODULE module/module.cpp MANIFEST module/module.json)
add_executable(mixed-profile guard.cpp)
target_link_libraries(mixed-profile PRIVATE pce-runtime ${{native_objects}})
''',encoding='utf-8')
            configured=subprocess.run(['cmake','-S',str(root),'-B',str(root/'build'),'-G','Ninja',
                '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+COMPILER],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(configured.returncode,0,configured.stdout+configured.stderr)
            compiled=subprocess.run(['cmake','--build',str(root/'build'),'--parallel','2','--target','mixed-profile'],
                capture_output=True,text=True,timeout=90)
            self.assertEqual(compiled.returncode,0,compiled.stdout+compiled.stderr)
            executable=root/'build'/('mixed-profile.exe' if os.name=='nt' else 'mixed-profile')
            result=subprocess.run([str(executable)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout),dict(checks=18,native=5,interpreted=0,cycles=12,ticks=36))


if __name__=='__main__':unittest.main()
