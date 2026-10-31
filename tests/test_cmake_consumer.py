"""Configure a real parent project without disabling its own tests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_capture
from tests.test_capture import capture, observation

ROOT = Path(__file__).resolve().parent.parent
COMPILER = shutil.which("clang++") or shutil.which("g++")


@unittest.skipUnless(shutil.which("cmake") and shutil.which("ninja") and COMPILER,
                     "CMake/Ninja/C++ compiler required for embedding configure check")
class CMakeConsumerTests(unittest.TestCase):
    def test_stale_and_future_module_abis_refused_before_compilation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'module.cpp').write_text('// Authored ABI refusal fixture.\n')
            (root/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.20)
project(AbiRefusal LANGUAGES CXX)
set(PCE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory("{ROOT.as_posix()}" tool)
pce_add_native_module(native_objects MODULE module.cpp MANIFEST module.json)
''', encoding='utf-8')
            for abi in (ABI - 1, ABI + 1):
                with self.subTest(abi=abi):
                    (root/'module.json').write_text(json.dumps(dict(schema=1, runtime_abi=abi)))
                    result = subprocess.run(['cmake', '-S', str(root), '-B', str(root/f'build-{abi}'),
                        '-G', 'Ninja', f'-DCMAKE_CXX_COMPILER={COMPILER}'],
                        capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Unsupported native module runtime_abi', result.stdout+result.stderr)

    def test_parent_testing_survives_without_tool_tests_or_runners(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module.cpp").write_text("// Authored configure-only module fixture.\n")
            (root / "CMakeLists.txt").write_text(f'''cmake_minimum_required(VERSION 3.20)
project(ParentConsumer LANGUAGES CXX)
set(BUILD_TESTING ON CACHE BOOL "" FORCE)
include(CTest)
add_subdirectory("{ROOT.as_posix()}" tool)
pce_add_consumer(parent-consumer MODULE module.cpp)
if(NOT BUILD_TESTING OR PCE_BUILD_TESTS OR PCE_BUILD_TOOLS)
  message(FATAL_ERROR "Embedding changed parent test policy or enabled tool extras")
endif()
if(NOT TARGET parent-consumer OR NOT TARGET pce-runtime OR TARGET pce-headless OR TARGET pce-runtime-tests)
  message(FATAL_ERROR "Unexpected embedding target graph")
endif()
''', encoding="utf-8")
            result = subprocess.run(["cmake", "-S", str(root), "-B", str(root / "build"),
                                     "-G", "Ninja", f"-DCMAKE_CXX_COMPILER={COMPILER}"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_partitioned_module_build_reuse_guards_and_pinned_artifacts(self):
        self.check_partitioned_module('balanced')

    def test_stable_module_build_reuse_guards_and_pinned_artifacts(self):
        self.check_partitioned_module('stable')

    def check_partitioned_module(self, layout):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = root/'generated'
            manifest = emit_capture(capture([
                observation(0x4000, (0xa9, 9)),
                observation(0x4002, (0xe8,)),
                observation(0x4003, (0x4c, 0, 0x40)),
            ]), generated, partition_size=1 if layout == 'balanced' else 256,
                partition_layout=layout)
            self.assertEqual(len(manifest['translation_units']), 4 if layout == 'balanced' else 2)
            (root/'program.bin').write_bytes(bytes([0xa9,9,0xe8,0x4c,0,0x40]))
            (root/'guard.cpp').write_text(r'''// Authored same-page partition routing and exact-source refusals.
#include "pce/runtime.hpp"
#include <limits>
#include <stdexcept>
int main() {
    pce::Bus bus; bus.kind[0x80]=pce::BankKind::ram;
    const unsigned char program[]={0xa9,9,0xe8,0x4c,0,0x40};
    for(unsigned i=0;i<sizeof(program);++i) (*bus.bytes)[0x100000+i]=program[i];
    pce::Cpu s; s.pc=0x4000;
    const auto deadline=std::numeric_limits<std::uint64_t>::max();
    auto require=[](bool value) {if(!value) throw std::runtime_error("partition guard failure");};
    for(unsigned loop=0;loop<2;++loop) {
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.pc==0x4002 && s.a==9);
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.pc==0x4003 && s.x==loop+1);
        require(pce::generated_step(bus,s,deadline)==pce::Exit::executed);
        require(s.pc==0x4000);
    }
    require(s.native_steps==6 && s.interpreter_steps==0);
    auto refused=[&](pce::Exit expected) {
        const auto before=s; const auto generations=bus.generation;
        const auto bytes=std::make_unique<std::array<std::uint8_t,0x200000>>(*bus.bytes);
        require(pce::generated_step(bus,s,expected==pce::Exit::budget?s.ticks:deadline)==expected);
        require(s.pc==before.pc && s.a==before.a && s.x==before.x && s.y==before.y &&
                s.sp==before.sp && s.p==before.p && s.mpr==before.mpr &&
                s.mpr_latch==before.mpr_latch && s.ticks==before.ticks && s.cycles==before.cycles &&
                s.native_steps==before.native_steps && s.interpreter_steps==before.interpreter_steps &&
                s.guard_misses==before.guard_misses && bus.generation==generations && *bus.bytes==*bytes);
    };
    (*bus.bytes)[0x100000]=0x02; refused(pce::Exit::miss); (*bus.bytes)[0x100000]=0xa9;
    (*bus.bytes)[0x100001]=10; refused(pce::Exit::miss); (*bus.bytes)[0x100001]=9;
    s.pc=0x4001; refused(pce::Exit::miss); s.pc=0x4000;
    s.mpr[7]^=1; refused(pce::Exit::miss); s.mpr[7]^=1;
    bus.kind[0x80]=pce::BankKind::io; refused(pce::Exit::miss);
    refused(pce::Exit::budget); bus.kind[0x80]=pce::BankKind::ram;
    return 0;
}
''', encoding='utf-8')
            (root/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.20)
project(PartitionedParent LANGUAGES CXX)
set(PCE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PCE_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_subdirectory("{ROOT.as_posix()}" tool)
pce_add_consumer(first-consumer MODULE generated/module.cpp)
pce_add_consumer(second-consumer MODULE generated/module.cpp MANIFEST generated/module.json)
pce_add_native_module(native_objects MODULE generated/module.cpp)
add_executable(partition-guards guard.cpp)
target_link_libraries(partition-guards PRIVATE pce-runtime ${{native_objects}})
''', encoding='utf-8')
            build = root/'build'
            configure = ['cmake', '-S', str(root), '-B', str(build), '-G', 'Ninja',
                         f'-DCMAKE_CXX_COMPILER={COMPILER}']
            configured = subprocess.run(configure, capture_output=True, text=True, timeout=30)
            self.assertEqual(configured.returncode, 0, configured.stdout+configured.stderr)
            compiled = subprocess.run(['cmake','--build',str(build),'--parallel','2',
                '--target','first-consumer','second-consumer','partition-guards'],
                capture_output=True,text=True,timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stdout+compiled.stderr)
            commands = json.loads((build/'compile_commands.json').read_text())
            for entry in manifest['translation_units']:
                selected = [command for command in commands
                            if Path(command['file']).resolve()==(generated/entry['file']).resolve()]
                self.assertEqual(len(selected),1,entry['file'])
            suffix = '.exe' if os.name=='nt' else ''
            result = subprocess.run([str(build/('partition-guards'+suffix))],
                                    capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            for target in ('first-consumer','second-consumer'):
                result = subprocess.run([str(build/(target+suffix)),str(root/'program.bin'),
                    '0x100000','0x4000','255,248,128,129,130,131,132,0','6','10000','hybrid'],
                    capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                state=json.loads(result.stdout)
                self.assertEqual((state['native_steps'],state['interpreter_steps'],state['a'],state['x'],state['pc']),
                                 (6,0,9,2,0x4000))
            for entry in (manifest['translation_units'][1], manifest['generated_headers'][0]):
                path=generated/entry['file']; original=path.read_bytes()
                try:
                    path.write_bytes(original+b'// Authored digest mismatch.\n')
                    rejected=subprocess.run(configure,capture_output=True,text=True,timeout=30)
                    self.assertNotEqual(rejected.returncode,0,rejected.stdout+rejected.stderr)
                    self.assertRegex(rejected.stdout+rejected.stderr,r'(?i)(digest|sha256|hash|mismatch)')
                finally:
                    path.write_bytes(original)
