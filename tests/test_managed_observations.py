"""Authored profile retention through managed builds; historical hits stay separate."""
import copy
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from pcerecomp.abi import ABI
from pcerecomp import incremental as inc, project
from pcerecomp.capture import load_capture
from pcerecomp.emitter import emit_observation_profile
from pcerecomp.observations import compose_observation_profile
from tests import test_build_inputs, test_capture, test_incremental_native, test_project
from test_queued_persistence import isolated_environment


PROFILE_NAME = 'observation-profile.json'
ROOT = Path(__file__).resolve().parent.parent
MPR = test_capture.MPR


def write_profile(paths, destination):
    profile = compose_observation_profile(paths)
    destination.write_text(json.dumps(profile, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    return profile


class ManagedProfileTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_project.ConsumerProjectTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.descriptor = self.fixture.root, self.fixture.descriptor
        original = test_capture.capture([test_capture.observation(0x4000, (0xea,))])
        original['runtime_abi'] = 18
        self.capture = self.root/'original.json'
        self.capture.write_text(json.dumps(original), encoding='utf-8')
        self.profile = self.root/'unusual-original-name.json'
        profile = write_profile([self.capture], self.profile)
        self.module = self.root/'emitted-profile'
        emit_observation_profile(profile, self.module, project.sha256(self.profile), partition_layout='stable')
        text = self.fixture.text.replace('path = "module.cpp"', 'path = "emitted-profile/module.cpp"')
        text = text.replace('path = "module.json"', 'path = "emitted-profile/module.json"')
        text = text.replace(project.sha256(self.root/'module.cpp'), project.sha256(self.module/'module.cpp'))
        text = text.replace(project.sha256(self.root/'module.json'), project.sha256(self.module/'module.json'))
        text += ('\n[module.observation_profile]\npath = "unusual-original-name.json"\n'
                 f'sha256 = "{project.sha256(self.profile)}"\n')
        self.descriptor.write_text(text, encoding='utf-8')
        self.workspace = self.root/'managed'

    def checked(self):
        return project.verify(self.descriptor, allow_revision_override=True)

    def test_owned_copy_uses_canonical_name_and_descriptor_hash(self):
        checked = self.checked()
        files = inc._module(checked)
        self.assertEqual(files[PROFILE_NAME], self.profile)
        self.assertNotIn(self.profile.name, files)
        owned = self.workspace/'module'
        owned.mkdir(parents=True)
        changes = inc._sync(files, owned)
        self.assertIn(PROFILE_NAME, changes['changed'])
        self.assertEqual((owned/PROFILE_NAME).read_bytes(), self.profile.read_bytes())
        before = (owned/PROFILE_NAME).stat().st_mtime_ns
        unchanged = inc._sync(files, owned, old={name: 0 for name in files})
        self.assertIn(PROFILE_NAME, unchanged['unchanged'])
        self.assertEqual((owned/PROFILE_NAME).stat().st_mtime_ns, before)
        config = inc._config(checked, self.workspace, files)
        actual = tomllib.loads(inc._toml(config))
        self.assertEqual(actual['module']['observation_profile'],
            dict(path=str(owned/PROFILE_NAME), sha256=project.sha256(self.profile)))
        changed = copy.deepcopy(config)
        changed['module']['observation_profile']['sha256'] = 'a'*64
        self.assertEqual(inc._fixed_config(config), inc._fixed_config(changed))
        self.assertIn('module_observation_profile', checked['identities'])

    def test_declared_profile_symlink_is_rejected_after_project_resolves_input(self):
        link = self.root/'linked-profile.json'
        try:
            link.symlink_to(self.profile)
        except OSError:
            return
        self.descriptor.write_text(self.descriptor.read_text().replace(self.profile.name, link.name))
        checked = self.checked()
        self.assertEqual(checked['files']['module_observation_profile'], self.profile)
        with self.assertRaisesRegex(ValueError, 'links or reparse'):
            inc._module(checked)
        self.assertFalse(self.workspace.exists())

    def retained(self):
        """Authored state only; the native test independently builds packages."""
        checked = self.checked()
        owned = self.workspace/'module'; owned.mkdir(parents=True)
        inc._sync(inc._module(checked), owned)
        output = self.workspace/'output'; output.mkdir()
        (output/'authored.obj').write_bytes(b'authored sentinel; not a compiled object')
        descriptor = self.workspace/'project.toml'; descriptor.write_text('schema=1\n')
        history = self.workspace/'history/000000'; history.mkdir(parents=True)
        archived = history/PROFILE_NAME; archived.write_bytes(self.profile.read_bytes())
        state = dict(schema=1, generation=0, build_tree=inc._snapshot(output),
            module_tree=inc._snapshot(owned), descriptor_sha256=project.sha256(descriptor),
            observation_profile=dict(file=PROFILE_NAME, sha256=project.sha256(self.profile)))
        project._write_new(history/'state.json', state)
        project._write_new(self.workspace/'current.json',
            dict(generation=0, sha256=project.sha256(history/'state.json')))
        return owned, archived

    def test_live_and_archived_profile_edits_invalidate_retained_state(self):
        owned, archived = self.retained()
        inc._state(self.workspace)
        for path in (owned/PROFILE_NAME, archived):
            raw, stamp = path.read_bytes(), path.stat().st_mtime_ns
            path.write_bytes(raw+b' ')
            os.utime(path, ns=(stamp, stamp))
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'changed outside'):
                inc._state(self.workspace)
            path.write_bytes(raw); os.utime(path, ns=(stamp, stamp))
        inc._state(self.workspace)

    def test_bound_workspace_cannot_downgrade_to_an_unbound_candidate(self):
        self.retained()
        config = tomllib.loads(self.descriptor.read_text(encoding='utf-8'))
        del config['module']['observation_profile']
        descriptor = self.root/'unbound-candidate.toml'
        descriptor.write_text(inc._toml(config), encoding='utf-8')
        before = inc._snapshot(self.workspace)
        with patch.object(inc, 'prepare') as compiler:
            with self.assertRaisesRegex(ValueError, 'binding cannot be removed'):
                inc.rebuild(descriptor, self.workspace, allow_revision_override=True)
            compiler.assert_not_called()
        self.assertEqual(inc._snapshot(self.workspace), before)

    def test_invalid_candidate_profile_refuses_before_workspace_creation(self):
        before = self.profile.read_bytes()
        self.profile.write_bytes(before+b' ')
        with patch.object(inc, 'prepare') as compiler:
            with self.assertRaises(ValueError):
                inc.rebuild(self.descriptor, self.workspace, create=True, allow_revision_override=True)
            compiler.assert_not_called()
        self.assertFalse(self.workspace.exists())
        self.assertEqual(self.capture.read_bytes(), json.dumps(
            test_capture.capture([test_capture.observation(0x4000, (0xea,))]) |
            {'runtime_abi': 18}).encode())

    @unittest.skipUnless(os.name == 'nt', 'Verified package-cache contract targets Windows LLVM-MinGW')
    def test_profile_identity_is_mutable_module_cache_input_not_fixed_external_contract(self):
        fixture = test_build_inputs.ProducerInputTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        before = fixture.context()['contract']
        fixture.project['identities']['module_observation_profile'] = project.sha256(self.profile)
        fixture.project['files']['module_observation_profile'] = self.profile
        bound = fixture.context()['contract']
        self.assertEqual(bound['module_inputs']['module_observation_profile'], project.sha256(self.profile))
        self.assertNotEqual(before, bound)
        self.assertEqual(inc._fixed_contract(dict(contract=before)), inc._fixed_contract(dict(contract=bound)))
        fixture.project['identities']['module_observation_profile'] = 'f'*64
        self.assertNotEqual(bound, fixture.context()['contract'])
        # The external profile's parent is never authorized as a compiler root.
        self.assertNotIn(self.root, fixture.context()['roots'])


class NativeManagedProfileTests(unittest.TestCase):
    def test_actual_profile_promotion_retains_provenance_and_unchanged_objects(self):
        compiler, bundle = test_incremental_native.NativeManagedRebuildTests.compiler_bundle(self)
        identity = project.source_identity(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root/'authored.bin'
            program = bytearray([0xea]*260)
            program[:5] = bytes([0xa2, 7, 0x4c, 0, 0x41])
            program[256:] = bytes([0xe8, 0x4c, 0, 0x41])
            payload.write_bytes(program)
            old = test_capture.capture([
                test_capture.observation(0x4000, (0xa2, 7)),
                test_capture.observation(0x4002, (0x4c, 0, 0x41)),
                test_capture.observation(0x4101, (0x4c, 0, 0x41))])
            old['runtime_abi'] = 18
            original = root/'original-18.json'; original.write_text(json.dumps(old))

            def emit(paths, name):
                profile_path = root/(name+'-source-history.json')
                profile = write_profile(paths, profile_path)
                module = root/name
                emit_observation_profile(profile, module, project.sha256(profile_path), partition_layout='stable')
                config = dict(schema=1, name='authored-managed-profile',
                    tool=dict(path=ROOT.as_posix(), revision=identity['revision'],
                        source_sha256=identity['source_sha256'], runtime_abi=ABI),
                    module={role: dict(path=(module/file).as_posix(), sha256=project.sha256(module/file))
                        for role,file in (('source','module.cpp'),('manifest','module.json'))},
                    payload=dict(path=payload.as_posix(), sha256=project.sha256(payload),
                        physical_load=0x100000, pc=0x4000, mpr=MPR),
                    runtime=dict(tier='hybrid', video='continuous', cd_unknown_status='fault',
                        joypad=2, region='usa', multitap='off'),
                    limits=dict(steps=200, ticks=100000, wall_seconds=5))
                config['module']['observation_profile'] = dict(path=profile_path.as_posix(),
                    sha256=project.sha256(profile_path))
                descriptor = root/(name+'.toml')
                descriptor.write_text(inc._toml(config), encoding='utf-8')
                return descriptor, profile_path

            descriptor, initial_profile = emit([original], 'initial')
            args = ('-DCMAKE_CXX_COMPILER='+str(compiler),
                    '-DCMAKE_MAKE_PROGRAM='+str(bundle/'bin/ninja.exe'))
            workspace = root/'managed'
            created = inc.rebuild(descriptor, workspace, create=True, toolchain_root=bundle, cmake_args=args)
            self.assertFalse(created['execution_evidence'])
            self.assertEqual(created['binding']['files']['module_observation_profile'], project.sha256(initial_profile))
            self.assertEqual((workspace/'module'/PROFILE_NAME).read_bytes(), initial_profile.read_bytes())
            self.assertEqual((workspace/'history/000000'/PROFILE_NAME).read_bytes(), initial_profile.read_bytes())

            def execute(name):
                captured = root/(name+'-actual.json')
                with patch.dict(os.environ, isolated_environment(), clear=True):
                    result = project.run(workspace/'project.toml', workspace/'output', root/(name+'-run.json'),
                                         code_capture=captured, capture_limit=64)
                self.assertTrue(result['qualified'], result)
                self.assertEqual({key:result['result'][key] for key in ('x','pc','cycles','ticks')},
                    dict(x=106, pc=0x4100, cycles=600, ticks=1800))
                return result, captured

            before, actual = execute('before')
            self.assertEqual((before['work']['native'], before['work']['interpreted']), (101,99))
            observation, _ = load_capture(actual)
            self.assertEqual((observation['runtime_abi'], observation['complete'],
                              observation['retired_instructions']), (26,True,200))
            objects = test_incremental_native.retained_files(workspace/'output', {'.obj','.o'})
            source_files = test_incremental_native.retained_files(workspace/'module', {'.cpp','.hpp'})
            selected, promoted_profile = emit([original, actual], 'promoted')
            updated = inc.rebuild(selected, workspace)
            self.assertEqual(updated['incremental']['generation'], 1)
            self.assertEqual(updated['binding']['files']['module_observation_profile'], project.sha256(promoted_profile))
            later_objects = test_incremental_native.retained_files(workspace/'output', {'.obj','.o'})
            self.assertEqual(objects.keys(), later_objects.keys())
            rebuilt = [name for name in objects if objects[name] != later_objects[name]]
            self.assertEqual(len(rebuilt), 1, rebuilt)
            self.assertIn('_p4100.cpp.obj', rebuilt[0])
            later_sources = test_incremental_native.retained_files(workspace/'module', {'.cpp','.hpp'})
            for name in source_files:
                if not name.endswith('_p4100.cpp'):
                    self.assertEqual(source_files[name], later_sources[name])
            self.assertEqual((workspace/'history/000000'/PROFILE_NAME).read_bytes(), initial_profile.read_bytes())
            self.assertEqual((workspace/'history/000001'/PROFILE_NAME).read_bytes(), promoted_profile.read_bytes())
            after, _ = execute('after')
            self.assertEqual((after['work']['native'], after['work']['interpreted']), (200,0))
            baseline = inc._snapshot(workspace)
            promoted_profile.write_bytes(promoted_profile.read_bytes()+b' ')
            with self.assertRaises(ValueError):
                inc.rebuild(selected, workspace)
            self.assertEqual(inc._snapshot(workspace), baseline)
            # A no-op uses the intact selected profile; profile bytes/mtime and
            # all object identities survive without counting compilation as work.
            promoted_profile.write_bytes((workspace/'module'/PROFILE_NAME).read_bytes())
            stamp = (workspace/'module'/PROFILE_NAME).stat().st_mtime_ns
            noop = inc.rebuild(selected, workspace)
            self.assertEqual(noop['incremental']['generation'], 2)
            self.assertEqual((workspace/'module'/PROFILE_NAME).stat().st_mtime_ns, stamp)
            self.assertEqual(test_incremental_native.retained_files(workspace/'output', {'.obj','.o'}), later_objects)
            self.assertEqual(noop['incremental']['object_timestamps']['rebuilt'], [])
            self.assertFalse(noop['execution_evidence'])


if __name__ == '__main__':
    unittest.main()
