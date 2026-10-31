"""Real authored fallback promotion and retained native compilation units."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp.abi import ABI
from pcerecomp import incremental, project
from pcerecomp.capture import load_capture
from pcerecomp.emitter import emit_capture
from scripts.build_config import cmake_cache
from test_queued_persistence import isolated_environment


ROOT = Path(__file__).resolve().parent.parent
MPR = [255, 248, 128, 129, 130, 131, 132, 0]


def retained_files(root, suffixes):
    return {path.relative_to(root).as_posix():
            (project.sha256(path), path.stat().st_mtime_ns)
            for path in root.rglob('*') if path.is_file() and path.suffix in suffixes}


class NativeManagedRebuildTests(unittest.TestCase):
    def compiler_bundle(self):
        if os.name != 'nt' or not shutil.which('cmake') or not shutil.which('ninja'):
            self.skipTest('Audited managed producer requires Windows LLVM-MinGW and Ninja')
        cache = cmake_cache(ROOT/'build', os.environ.get('PCE_TEST_CMAKE_CACHE'))
        compiler = None
        if cache:
            for line in cache.read_text(encoding='utf-8').splitlines():
                if line.startswith('CMAKE_CXX_COMPILER:'):
                    compiler = Path(line.split('=', 1)[1]).resolve()
                    break
        if compiler is None or compiler.name.lower() != 'clang++.exe':
            self.skipTest('Audited LLVM-MinGW bundle not selected')
        bundle = compiler.parent.parent
        if not (bundle/'x86_64-w64-mingw32/include').is_dir():
            self.skipTest('Selected compiler lacks the supported self-contained bundle')
        return compiler, bundle

    def test_actual_fallback_promotion_rebuilds_only_affected_bucket_then_noops(self):
        compiler, bundle = self.compiler_bundle()
        identity = project.source_identity(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root/'program.bin'
            program = bytearray([0xea]*260)
            # LDX #7; JMP $4100; ...; INX; JMP $4100.
            program[:5] = bytes([0xa2, 7, 0x4c, 0, 0x41])
            program[256:] = bytes([0xe8, 0x4c, 0, 0x41])
            payload.write_bytes(program)

            def observation(pc, data):
                return dict(pc=pc, mpr=MPR,
                    physical=[(MPR[(pc+i) >> 13] << 13) | ((pc+i) & 8191)
                              for i in range(len(data))], data=data,
                    native_hits=0, interpreted_hits=1)

            # Authored source identities, not a claimed runtime capture. INX is
            # deliberately absent, and its later promotion must come from a
            # real lossless execution capture of this unchanged payload.
            seed = dict(schema=1, runtime_abi=ABI, capacity=64,
                dropped_instructions=0, unreadable_instructions=0,
                retired_instructions=3, complete=True,
                observations=[observation(0x4000, [0xa2, 7]),
                              observation(0x4002, [0x4c, 0, 0x41]),
                              observation(0x4101, [0x4c, 0, 0x41])])
            initial = root/'initial'
            emit_capture(seed, initial, partition_layout='stable')

            def descriptor(module, name):
                config = dict(schema=1, name='authored-managed-promotion',
                    tool=dict(path=ROOT.as_posix(), revision=identity['revision'],
                        source_sha256=identity['source_sha256'], runtime_abi=ABI),
                    module={role: dict(path=(module/filename).as_posix(),
                            sha256=project.sha256(module/filename))
                        for role, filename in (('source', 'module.cpp'), ('manifest', 'module.json'))},
                    payload=dict(path=payload.as_posix(), sha256=project.sha256(payload),
                        physical_load=1048576, pc=16384, mpr=MPR),
                    runtime=dict(tier='hybrid', video='continuous',
                        cd_unknown_status='fault', joypad=2, region='usa', multitap='off'),
                    limits=dict(steps=200, ticks=100000, wall_seconds=5))
                path = root/name
                path.write_text(incremental._toml(config), encoding='utf-8')
                return path

            original = descriptor(initial, 'initial.toml')
            args = ('-DCMAKE_CXX_COMPILER='+str(compiler),
                    '-DCMAKE_MAKE_PROGRAM='+str(bundle/'bin/ninja.exe'))
            workspace = root/'managed'
            created = incremental.rebuild(original, workspace, create=True,
                toolchain_root=bundle, cmake_args=args)
            self.assertFalse(created['execution_evidence'])
            self.assertEqual(created['incremental']['generation'], 0)

            def execute(name, source, build):
                path = root/(name+'-capture.json')
                with patch.dict(os.environ, isolated_environment(), clear=True):
                    receipt = project.run(source, build, root/(name+'-run.json'),
                                          code_capture=path, capture_limit=64)
                self.assertTrue(receipt['qualified'], receipt)
                result = receipt['result']
                # 1 LDX, 100 JMPs and 99 INXs: 600 CPU cycles at divisor 3.
                self.assertEqual({key: result[key] for key in
                    ('a', 'x', 'y', 'sp', 'p', 'pc', 'cycles', 'ticks', 'mpr')},
                    dict(a=0, x=106, y=0, sp=255, p=4, pc=0x4100,
                         cycles=600, ticks=1800, mpr=MPR))
                capture, digest = load_capture(path)
                self.assertEqual((capture['runtime_abi'], capture['complete'],
                    capture['retired_instructions'], capture['dropped_instructions'],
                    capture['unreadable_instructions'], len(capture['observations'])),
                    (ABI, True, 200, 0, 0, 4))
                self.assertNotIn('bram_session', receipt)
                return receipt, capture, digest

            before, captured, digest = execute('before', workspace/'project.toml', workspace/'output')
            self.assertEqual((before['work']['native'], before['work']['interpreted']), (101, 99))
            old_objects = retained_files(workspace/'output', {'.obj', '.o'})
            old_module = retained_files(workspace/'module', {'.cpp', '.hpp'})
            promoted = root/'promoted'
            emitted = emit_capture(captured, promoted, digest, partition_layout='stable')
            self.assertEqual(emitted['native_instructions_emitted'], 4)
            selected = descriptor(promoted, 'promoted.toml')
            updated = incremental.rebuild(selected, workspace)
            objects = retained_files(workspace/'output', {'.obj', '.o'})
            self.assertEqual(old_objects.keys(), objects.keys())
            changed = [key for key in objects if objects[key] != old_objects[key]]
            self.assertEqual(len(changed), 1, changed)
            self.assertIn('_p4100.cpp.obj', changed[0])
            self.assertGreaterEqual(len(objects)-len(changed), 20)
            for name in ('module.cpp', 'module_parts.hpp',
                         next(name for name in old_module if name.endswith('_p4000.cpp'))):
                self.assertEqual(old_module[name], retained_files(workspace/'module', {'.cpp', '.hpp'})[name])
            after, after_capture, after_digest = execute('after', workspace/'project.toml', workspace/'output')
            self.assertEqual((after['work']['native'], after['work']['interpreted']), (200, 0))
            clean = project.build(selected, root/'clean', generator='Ninja', cmake_args=args)
            self.assertFalse(clean['execution_evidence'])
            fresh, fresh_capture, _ = execute('clean', selected, root/'clean')
            self.assertEqual(after['result'], fresh['result'])
            self.assertEqual(after_capture, fresh_capture)

            # A real later capture has the same source identities but different
            # native/interpreter hit provenance. Rebind the manifest without
            # recompiling or relinking the unchanged translated operations.
            metadata_module = root/'native-capture-module'
            emit_capture(after_capture, metadata_module, after_digest, partition_layout='stable')
            self.assertNotEqual(project.sha256(promoted/'module.json'),
                                project.sha256(metadata_module/'module.json'))
            self.assertEqual({path.name: project.sha256(path) for path in promoted.iterdir()
                              if path.suffix in {'.cpp', '.hpp'}},
                             {path.name: project.sha256(path) for path in metadata_module.iterdir()
                              if path.suffix in {'.cpp', '.hpp'}})
            metadata_descriptor = descriptor(metadata_module, 'native-capture.toml')
            unchanged_code = retained_files(workspace/'module', {'.cpp', '.hpp'})
            binary = Path(updated['binary'])
            unchanged_binary = (project.sha256(binary), binary.stat().st_mtime_ns)
            metadata_update = incremental.rebuild(metadata_descriptor, workspace)
            self.assertEqual(metadata_update['incremental']['generation'], 2)
            self.assertEqual(retained_files(workspace/'output', {'.obj', '.o'}), objects)
            self.assertEqual(retained_files(workspace/'module', {'.cpp', '.hpp'}), unchanged_code)
            self.assertEqual((project.sha256(binary), binary.stat().st_mtime_ns), unchanged_binary)
            self.assertEqual(metadata_update['incremental']['object_timestamps']['rebuilt'], [])
            self.assertEqual(metadata_update['incremental']['object_timestamps']['added'], [])

            unchanged_module = retained_files(workspace/'module', {'.cpp', '.hpp', '.json'})
            noop = incremental.rebuild(metadata_descriptor, workspace)
            self.assertEqual(retained_files(workspace/'output', {'.obj', '.o'}), objects)
            self.assertEqual(retained_files(workspace/'module', {'.cpp', '.hpp', '.json'}), unchanged_module)
            self.assertEqual((project.sha256(binary), binary.stat().st_mtime_ns), unchanged_binary)
            self.assertEqual(noop['incremental']['object_timestamps']['rebuilt'], [])
            self.assertEqual(noop['incremental']['object_timestamps']['added'], [])
            self.assertEqual(noop['incremental']['generation'], 3)
            self.assertFalse(noop['execution_evidence'])
            changed_fixed_input = root/'changed-fixed-input.toml'
            text = metadata_descriptor.read_text(encoding='utf-8')
            self.assertIn('joypad = 2', text)
            changed_fixed_input.write_text(text.replace('joypad = 2', 'joypad = 6'), encoding='utf-8')
            preserved = incremental._snapshot(workspace)
            with self.assertRaisesRegex(ValueError, 'Only module may change'):
                incremental.rebuild(changed_fixed_input, workspace)
            self.assertEqual(incremental._snapshot(workspace), preserved)
            # An unfinished update must invalidate official execution even
            # while the preceding generation's valid package is still there.
            marker = workspace/'in-progress.json'
            marker.write_text('{"generation":4}\n', encoding='utf-8')
            try:
                with self.assertRaisesRegex(ValueError, 'Incomplete generation'):
                    project.run(workspace/'project.toml', workspace/'output', root/'refused-run.json')
                self.assertFalse((root/'refused-run.json').exists())
                self.assertEqual(retained_files(workspace/'output', {'.obj', '.o'}), objects)
                self.assertEqual((project.sha256(binary), binary.stat().st_mtime_ns), unchanged_binary)
            finally:
                marker.unlink()


if __name__ == '__main__':
    unittest.main()
