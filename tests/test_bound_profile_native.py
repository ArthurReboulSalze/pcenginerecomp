"""Actual consumer build/run with an external, explicitly bound authored profile."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import incremental, project
from pcerecomp.abi import ABI
from pcerecomp.emitter import emit_observation_profile
from pcerecomp.observations import compose_observation_profile, load_observation_profile
from tests.test_queued_persistence import isolated_environment

ROOT = Path(__file__).resolve().parent.parent
COMPILER = shutil.which('clang++') or shutil.which('g++')
MPR = [255, 248, 128, 129, 130, 131, 132, 0]


@unittest.skipUnless(shutil.which('cmake') and shutil.which('ninja') and COMPILER,
                     'CMake/Ninja/C++ compiler required for bound-profile execution')
class BoundProfileNativeTests(unittest.TestCase):
    def test_build_run_receipts_retain_profile_and_refuse_later_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = project.source_identity(ROOT)
            payload = root/'program.bin'
            # LDA #41; TAX; INX; BRA back to INX. All bytes are authored.
            payload.write_bytes(bytes([0xa9, 41, 0xaa, 0xe8, 0x80, 0xfd]))
            sources = []
            for abi, instructions in ((18, [(0x4000, [0xa9, 41]), (0x4002, [0xaa])]),
                                      (26, [(0x4003, [0xe8]), (0x4004, [0x80, 0xfd])])):
                observations = [dict(pc=pc, mpr=MPR, physical=[0x100000+pc-0x4000+i
                                    for i in range(len(data))], data=data,
                                    native_hits=0, interpreted_hits=7) for pc, data in instructions]
                source = root/f'authored-{abi}.json'
                source.write_text(json.dumps(dict(schema=1, runtime_abi=abi, capacity=4,
                    complete=True, dropped_instructions=0, unreadable_instructions=0,
                    retired_instructions=14, observations=observations)), encoding='utf-8')
                sources.append(source)
            profile_path = root/'external-catalogue.json'
            profile_path.write_text(json.dumps(compose_observation_profile(sources), sort_keys=True),
                                    encoding='utf-8')
            profile, digest = load_observation_profile(profile_path)
            module = root/'module'
            manifest = emit_observation_profile(profile, module, digest, partition_layout='stable')
            self.assertEqual(manifest['historical_totals']['retired_instructions'], 28)
            config = dict(schema=1, name='authored-bound-profile',
                tool=dict(path=ROOT.as_posix(), revision=identity['revision'],
                          source_sha256=identity['source_sha256'], runtime_abi=ABI),
                module={role: dict(path=path.as_posix(), sha256=project.sha256(path)) for role, path in
                        (('source', module/'module.cpp'), ('manifest', module/'module.json'),
                         ('observation_profile', profile_path))},
                payload=dict(path=payload.as_posix(), sha256=project.sha256(payload),
                             physical_load=0x100000, pc=0x4000, mpr=MPR),
                runtime=dict(tier='native', video='continuous', cd_unknown_status='fault',
                             joypad=2, region='usa', multitap='off'),
                limits=dict(steps=6, ticks=10000, wall_seconds=5))
            descriptor = root/'project.toml'
            descriptor.write_text(incremental._toml(config), encoding='utf-8')
            build = root/'build'
            built = project.build(descriptor, build, generator='Ninja',
                                  cmake_args=('-DCMAKE_CXX_COMPILER='+COMPILER,))
            self.assertFalse(built['execution_evidence'])
            self.assertEqual(built['binding']['files']['module_observation_profile'], digest)
            with patch.dict(os.environ, isolated_environment(), clear=True):
                executed = project.run(descriptor, build, root/'run.json')
            self.assertTrue(executed['qualified'], executed)
            self.assertEqual((executed['work']['native'], executed['work']['interpreted']), (6, 0))
            self.assertEqual((executed['result']['a'], executed['result']['x'],
                              executed['result']['pc']), (41, 43, 0x4003))
            self.assertEqual(executed['binding']['files']['module_observation_profile'], digest)
            self.assertTrue(executed['input_hashes_unchanged']['module_observation_profile'])
            original = profile_path.read_bytes()
            profile_path.write_bytes(original+b' ')
            refused_receipt = root/'refused-run.json'
            with self.assertRaises(ValueError):
                project.run(descriptor, build, refused_receipt)
            self.assertFalse(refused_receipt.exists())
            profile_path.write_bytes(original)
            self.assertEqual(project.verify(descriptor)['identities']['module_observation_profile'], digest)


if __name__ == '__main__':
    unittest.main()
