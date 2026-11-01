"""Authored consumer descriptor/refusal/receipt checks without private inputs."""
import json
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import project


class ConsumerProjectTests(unittest.TestCase):
    def test_cd_timing_is_explicit_forwarded_and_checkpoint_bound(self):
        implicit = project.checkpoint_context(self.verify())
        contexts = set()
        for timing in ('fixed', 'gear-distance'):
            with self.subTest(timing=timing):
                self.replace('cd_unknown_status = "fault"',
                             f'cd_unknown_status = "fault"\ncd_timing = "{timing}"')
                checked = self.verify()
                command = project.command_for(checked, Path('runner'))
                self.assertEqual(command[command.index('--cd-timing') + 1], timing)
                contexts.add(project.checkpoint_context(checked))
        self.assertEqual(len(contexts), 2)
        self.assertNotIn(implicit, contexts)

    def test_cd_timing_rejects_untyped_and_unknown_profiles(self):
        for token in ('true', '0', '"fast"', '"measured"'):
            with self.subTest(token=token):
                self.replace('cd_unknown_status = "fault"',
                             f'cd_unknown_status = "fault"\ncd_timing = {token}')
                with self.assertRaises(ValueError):
                    self.verify()

    def test_unknown_cd_profiles_are_explicit_bound_and_forwarded(self):
        contexts = set()
        for policy in ('fault', 'gear-good', 'nec-invalid'):
            with self.subTest(policy=policy):
                self.replace('cd_unknown_status = "fault"', f'cd_unknown_status = "{policy}"')
                checked = self.verify()
                command = project.command_for(checked, Path('runner'))
                self.assertEqual(command[command.index('--cd-unknown-status') + 1], policy)
                contexts.add(project.checkpoint_context(checked))
        self.assertEqual(len(contexts), 3)

    def test_unknown_cd_profile_does_not_accept_guessed_or_untyped_values(self):
        for token in ('"good"', '"check-condition"', '"nec"', 'true', '2'):
            with self.subTest(token=token):
                self.replace('cd_unknown_status = "fault"', f'cd_unknown_status = {token}')
                with self.assertRaises(ValueError):
                    self.verify()

    def test_checkpoint_context_binds_exact_recipe_and_excludes_execution_limits(self):
        checked = self.verify()
        expected = project.checkpoint_context(checked)
        limited = copy.deepcopy(checked)
        limited['config']['limits'] = {'steps': 9, 'ticks': 10, 'wall_seconds': 4}
        limited['descriptor_sha256'] = 'f'*64
        self.assertEqual(project.checkpoint_context(limited), expected)
        for area, key, value in (('runtime', 'region', 'japan'),
                                 ('payload', 'pc', 42)):
            changed = copy.deepcopy(checked)
            changed['config'][area][key] = value
            self.assertNotEqual(project.checkpoint_context(changed), expected)
        for key in ('module_source', 'module_manifest', 'payload'):
            changed = copy.deepcopy(checked);changed['identities'][key] = 'c'*64
            self.assertNotEqual(project.checkpoint_context(changed), expected)
        changed = copy.deepcopy(checked);changed['tool_identity']['revision'] = 'c'*40
        self.assertNotEqual(project.checkpoint_context(changed), expected)
        changed = copy.deepcopy(checked);changed['tool_identity']['source_sha256'] = 'c'*64
        self.assertNotEqual(project.checkpoint_context(changed), expected)

    def test_checkpoint_command_requires_paused_tcp_and_direct_private_names(self):
        checked = self.verify()
        command = project.command_for(checked, Path('runner'), dev_port=0, start_paused=True,
                                      checkpoint_dir=self.root, checkpoint_load='frontier.pcec')
        self.assertEqual(command[-6:], ['--checkpoint-dir', str(self.root), '--checkpoint-context',
                                       project.checkpoint_context(checked), '--checkpoint-load', 'frontier.pcec'])
        for options in ({'checkpoint_load': 'x.pcec'}, {'checkpoint_dir': self.root},
                        {'checkpoint_dir': self.root, 'dev_port': 0},
                        {'checkpoint_dir': self.root/'missing', 'dev_port': 0, 'start_paused': True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                project.command_for(checked, Path('runner'), **options)
        for name in ('../x.pcec', 'x/y.pcec', 'x:stream.pcec', '.hidden.pcec', 'con.pcec',
                     'COM0.pcec', 'x..pcec', 'x.bin', 'a'*92+'.pcec'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                project.command_for(checked, Path('runner'), dev_port=0, start_paused=True,
                                    checkpoint_dir=self.root, checkpoint_load=name)
        with self.assertRaisesRegex(ValueError, 'persistent BRAM'):
            project.run(self.descriptor, self.root, self.root/'unwritten.json', checkpoint_load='x.pcec',
                        save_root=self.root/'save', save_namespace='fixture', save_contract='a'*64)

    def test_checkpoint_receipt_counts_only_new_suffix_and_matches_capture_origin(self):
        from tests.test_capture import capture, observation
        directory, binary = self.build_fixture()
        origin = {'sha256': 'a'*64, 'ticks': 1000, 'frame': 7, 'native_steps': 100, 'interpreter_steps': 20}
        state = {'native_steps': 107, 'interpreter_steps': 23, 'ticks': 1600,
                 'checkpoint': {'resumed': True, 'origin': origin,
                                'audio_origin': {'pending_pcm_frames': 5, 'source_wav_frames': 120},
                                'window': {'ticks': 600, 'native_steps': 7, 'interpreter_steps': 3}}}
        observed = capture([observation(native=7, interpreted=3)], capacity=4)
        observed.update(runtime_abi=project.ABI, checkpoint_origin=origin)
        actual_run = subprocess.run
        def execute_result(name, result, captured):
            capture_path = self.root/(name+'-capture.json')
            def execute(command, **kwargs):
                if command[0] == str(binary):
                    capture_path.write_text(json.dumps(captured), encoding='utf-8')
                    return subprocess.CompletedProcess(command, 0, json.dumps(result))
                return actual_run(command, **kwargs)
            with patch.object(project.subprocess, 'run', side_effect=execute):
                return project.run(self.descriptor, directory, self.root/(name+'-receipt.json'),
                    allow_revision_override=True, dev_port=0, start_paused=True,
                    checkpoint_dir=self.root, checkpoint_load='frontier.pcec',
                    code_capture=capture_path, capture_limit=4)
        receipt = execute_result('valid-window', state, observed)
        self.assertTrue(receipt['qualified'])
        self.assertEqual(receipt['work']['native'], 7)
        self.assertEqual(receipt['work']['interpreted'], 3)
        self.assertEqual(receipt['work']['total'], 10)
        self.assertEqual(receipt['work']['imported'], origin)
        self.assertEqual(receipt['work']['execution_window'], 'resumed-checkpoint-suffix')
        self.assertEqual(receipt['checkpoint_validation']['audio_origin'],
                         {'pending_pcm_frames': 5, 'source_wav_frames': 120})
        invalid = copy.deepcopy(state);invalid['checkpoint']['window']['native_steps'] = 107
        rejected = execute_result('promoted-window', invalid, observed)
        self.assertFalse(rejected['qualified']);self.assertIsNone(rejected['work'])
        for index, bad in enumerate((None, {}, {'pending_pcm_frames': 8193, 'source_wav_frames': 120},
                                    {'pending_pcm_frames': True, 'source_wav_frames': 120},
                                    {'pending_pcm_frames': 5, 'source_wav_frames': -1})):
            invalid = copy.deepcopy(state);invalid['checkpoint']['audio_origin'] = bad
            self.assertFalse(execute_result('bad-audio-'+str(index), invalid, observed)['qualified'])
        old_capture = copy.deepcopy(observed);old_capture.pop('checkpoint_origin')
        self.assertFalse(execute_result('missing-origin', state, old_capture)['qualified'])
        changed = copy.deepcopy(observed);changed['checkpoint_origin']['sha256'] = 'b'*64
        self.assertFalse(execute_result('foreign-origin', state, changed)['qualified'])
        full_capture = copy.deepcopy(observed)
        full_capture['observations'][0].update(native_hits=107, interpreted_hits=23)
        full_capture['retired_instructions'] = 130
        self.assertFalse(execute_result('imported-hits', state, full_capture)['qualified'])
        reset_state = {'native_steps': 7, 'interpreter_steps': 3, 'ticks': 600}
        self.assertFalse(execute_result('missing-checkpoint', reset_state, old_capture)['qualified'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tool = self.root / "tool"
        for name in project.SOURCE_DIRS:
            (self.tool / name).mkdir(parents=True)
        (self.tool / "runtime/include/pce").mkdir(parents=True)
        (self.tool / "runtime/include/pce/runtime.hpp").write_text(f"inline constexpr unsigned abi_version = {project.ABI};\n")
        (self.tool / "CMakeLists.txt").write_text("# authored stub\n")
        (self.tool / "pcerecomp/logic.py").write_text("VALUE = 1\n")
        (self.root / "program.bin").write_bytes(bytes([0xEA, 0x80, 0xFD]))
        (self.root / "module.cpp").write_text("// authored contract fixture\n")
        (self.root / "module.json").write_text(json.dumps({"schema": 1, "runtime_abi": project.ABI, "native_instructions_emitted": 2}))
        self.manifest_sha256 = project.sha256(self.root / "module.json")
        self.descriptor = self.root / "project.toml"
        self.text = f'''schema = 1
name = "fixture"
[tool]
path = "tool"
revision = "{'0' * 40}"
source_sha256 = "{project.source_identity(self.tool)['source_sha256']}"
runtime_abi = {project.ABI}
[module.source]
path = "module.cpp"
sha256 = "{project.sha256(self.root / 'module.cpp')}"
[module.manifest]
path = "module.json"
sha256 = "{project.sha256(self.root / 'module.json')}"
[payload]
path = "program.bin"
sha256 = "{project.sha256(self.root / 'program.bin')}"
physical_load = 1048576
pc = 16384
mpr = [255,248,128,129,130,131,132,0]
[runtime]
tier = "hybrid"
video = "continuous"
cd_unknown_status = "fault"
joypad = 2
region = "usa"
multitap = "off"
[limits]
steps = 200
ticks = 100000
wall_seconds = 5
'''
        self.descriptor.write_text(self.text, encoding="utf-8")

    def verify(self):
        return project.verify(self.descriptor, allow_revision_override=True)

    def reset_descriptor(self, profile="super"):
        bios = self.root / "authored.pce"
        bios.write_bytes(bytes(262144))
        prefix, rest = self.text.split("[payload]\n", 1)
        _, runtime = rest.split("[runtime]\n", 1)
        return (prefix + f'[boot]\nmode = "system-card-reset"\nprofile = "{profile}"\n'
                + "[runtime]\n" + runtime + '\n[bios]\npath = "authored.pce"\n'
                + f'sha256 = "{project.sha256(bios)}"\n')

    def test_reset_boot_has_no_payload_or_synthetic_pc_and_pins_firmware(self):
        for profile in ("standard", "super"):
            with self.subTest(profile=profile):
                self.descriptor.write_text(self.reset_descriptor(profile), encoding="utf-8")
                checked = self.verify()
                self.assertNotIn("payload", checked["files"])
                self.assertIn("bios", checked["identities"])
                command = project.command_for(checked, Path("runner"), dev_port=0, start_paused=True)
                self.assertEqual(command[:7], ["runner", "--system-card-reset", profile,
                                 str(self.root / "authored.pce"), "200", "100000", "hybrid"])
                self.assertNotIn("--bios", command)
                self.assertNotIn("255,248,128,129,130,131,132,0", command)
                self.assertEqual(command[-4:], ["--dev-start-paused", "on", "--dev-memory-write", "off"])

    def test_reset_profile_is_bound_without_changing_input_identity(self):
        self.descriptor.write_text(self.reset_descriptor("standard"), encoding="utf-8")
        before = self.verify()
        self.descriptor.write_text(self.reset_descriptor("super"), encoding="utf-8")
        after = self.verify()
        self.assertNotEqual(project._binding(before), project._binding(after))
        self.assertEqual(before["identities"], after["identities"])

    def test_reset_requires_explicit_profile_mode_and_hashed_bios(self):
        original = self.reset_descriptor()
        variants = (
            original.replace('mode = "system-card-reset"', 'mode = "snapshot"'),
            original.replace('profile = "super"', 'profile = "auto"'),
            original.replace('profile = "super"', 'profile = true'),
            original.replace('profile = "super"', 'profile = "super"\npc = 16384'),
            original.split("\n[bios]\n")[0],
            original.replace('profile = "super"\n', ''),
        )
        for text in variants:
            with self.subTest(text=text):
                self.descriptor.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.verify()

    def test_startup_modes_are_mutually_exclusive_and_required(self):
        both = self.text + '\n[boot]\nmode = "system-card-reset"\nprofile = "super"\n'
        neither = self.reset_descriptor().replace('[boot]\nmode = "system-card-reset"\nprofile = "super"\n', '')
        for text in (both, neither):
            with self.subTest(text=text):
                self.descriptor.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Exactly one"):
                    self.verify()

    def test_optional_audio_selection_is_bound_and_forwarded(self):
        checked = self.verify()
        self.assertNotIn("--audio-output", project.command_for(checked, Path("runner")))
        for mode in ("on", "off"):
            with self.subTest(mode=mode):
                self.replace('[runtime]', '[runtime]\naudio = "' + mode + '"')
                checked = self.verify()
                command = project.command_for(checked, Path("runner"))
                self.assertEqual(command[command.index("--audio-output") + 1], mode)

    def test_optional_audio_rejects_unknown_modes_and_types(self):
        for value in ('"auto"', 'true', '1', '["on"]'):
            with self.subTest(value=value):
                self.replace('[runtime]', '[runtime]\naudio = ' + value)
                with self.assertRaisesRegex(ValueError, "audio"):
                    self.verify()

    def test_audio_timing_is_optional_typed_forwarded_and_bound(self):
        before = self.verify()
        self.assertNotIn("--audio-timing", project.command_for(before, Path("runner")))
        for timing in ("gear", "legacy"):
            with self.subTest(timing=timing):
                self.replace('[runtime]', f'[runtime]\naudio = "on"\naudio_timing = "{timing}"')
                after = self.verify()
                command = project.command_for(after, Path("runner"))
                self.assertEqual(command[command.index("--audio-timing") + 1], timing)
                self.assertNotEqual(project._binding(before), project._binding(after))
                self.assertEqual(before["identities"], after["identities"])

    def test_audio_timing_refuses_invalid_values_and_disabled_or_implicit_audio(self):
        invalid = ['audio_timing = "gear"', 'audio = "off"\naudio_timing = "legacy"']
        invalid += ['audio = "on"\naudio_timing = ' + value
                    for value in ('"auto"', '"gear-v1"', 'true', '1', '["gear"]')]
        for fields in invalid:
            with self.subTest(fields=fields):
                self.replace('[runtime]', '[runtime]\n' + fields)
                with self.assertRaisesRegex(ValueError, "audio"):
                    self.verify()

    def test_audio_processing_optional_fields_are_explicit_typed_and_bound(self):
        plain = project.command_for(self.verify(), Path("runner"))
        self.assertNotIn("--audio-profile", plain)
        self.assertNotIn("--audio-rate", plain)
        for profile, rate in (("raw", 44100), ("filtered", 44100), ("filtered", 48000)):
            with self.subTest(profile=profile, rate=rate):
                self.replace('[runtime]', f'[runtime]\naudio = "on"\naudio_profile = "{profile}"\naudio_rate = {rate}')
                checked = self.verify()
                command = project.command_for(checked, Path("runner"))
                self.assertEqual(command[command.index("--audio-profile") + 1], profile)
                self.assertEqual(command[command.index("--audio-rate") + 1], str(rate))
        for fields in ('audio_profile = "filtered"', 'audio_rate = 44100'):
            self.replace('[runtime]', '[runtime]\naudio = "on"\n' + fields)
            self.verify()

    def test_audio_processing_rejects_implicit_disabled_or_invalid_profiles_and_rates(self):
        invalid = ('audio_profile = "filtered"', 'audio_rate = 44100',
                   'audio = "off"\naudio_profile = "raw"', 'audio = "off"\naudio_rate = 44100',
                   'audio = "on"\naudio_rate = 48000',
                   'audio = "on"\naudio_profile = "raw"\naudio_rate = 48000')
        invalid += tuple('audio = "on"\naudio_profile = ' + value for value in ('"auto"', 'true', '1', '["filtered"]'))
        invalid += tuple('audio = "on"\naudio_profile = "filtered"\naudio_rate = ' + value
                         for value in ('44100.0', '"44100"', 'true', '32000', '0', '[48000]'))
        for fields in invalid:
            with self.subTest(fields=fields):
                self.replace('[runtime]', '[runtime]\n' + fields)
                with self.assertRaisesRegex(ValueError, "audio"):
                    self.verify()

    def test_audio_profile_descriptor_changes_refuse_existing_build_binding(self):
        # Profile/rate are part of descriptor identity, even though native code
        # and every media hash remain the same.
        before = self.verify()
        self.replace('[runtime]', '[runtime]\naudio = "on"\naudio_profile = "filtered"\naudio_rate = 48000')
        after = self.verify()
        self.assertNotEqual(before["descriptor_sha256"], after["descriptor_sha256"])
        self.assertNotEqual(project._binding(before), project._binding(after))
        self.assertEqual(before["identities"], after["identities"])

    def replace(self, old, new):
        self.descriptor.write_text(self.text.replace(old, new), encoding="utf-8")

    def set_manifest(self, manifest):
        path = self.root / "module.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.replace(self.manifest_sha256, project.sha256(path))

    def multipart_manifest(self):
        for name in ("module_part_0000.cpp", "module_parts.hpp"):
            (self.root / name).write_text("// authored artifact fixture\n", encoding="utf-8")
        identity = lambda name: {"file": name, "sha256": project.sha256(self.root / name)}
        return {"schema": 1, "runtime_abi": project.ABI, "native_instructions_emitted": 2,
                "translation_units": [identity("module.cpp"), identity("module_part_0000.cpp")],
                "generated_headers": [identity("module_parts.hpp")]}

    def test_multipart_artifacts_are_all_bound_and_reverified(self):
        manifest = self.multipart_manifest()
        self.set_manifest(manifest)
        checked = self.verify()
        for key, name in (("module_unit:module.cpp", "module.cpp"),
                          ("module_unit:module_part_0000.cpp", "module_part_0000.cpp"),
                          ("module_header:module_parts.hpp", "module_parts.hpp")):
            self.assertEqual(checked["files"][key], self.root / name)
            self.assertEqual(project._binding(checked)["files"][key], project.sha256(self.root / name))
        # Changes outside the entry source must refuse before any build/run.
        for name in ("module_part_0000.cpp", "module_parts.hpp"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b"// stale\n")
                with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                    self.verify()
                path.write_bytes(original)

    def test_manifest_size_bound_before_json_read_without_large_output(self):
        manifest = self.root / "module.json"
        real_stat = Path.stat
        for size in (64 * 1024 * 1024, 64 * 1024 * 1024 + 1):
            def reported_size(path, *args, **kwargs):
                result = real_stat(path, *args, **kwargs)
                if path == manifest:
                    fields = list(result)
                    fields[6] = size
                    return os.stat_result(fields)
                return result
            with self.subTest(size=size), patch.object(Path, "stat", autospec=True, side_effect=reported_size):
                if size == 64 * 1024 * 1024:
                    self.verify()
                else:
                    with patch.object(project.json, "loads", side_effect=AssertionError("oversized manifest parsed")):
                        with self.assertRaisesRegex(ValueError, "manifest exceeds 64 MiB"):
                            self.verify()

    def test_multipart_lists_required_typed_and_bounded(self):
        baseline = self.multipart_manifest()
        for field, values in (("translation_units", (None, {}, [], [None], True)),
                              ("generated_headers", (None, {}, [None], True))):
            for value in values:
                with self.subTest(field=field, value=value):
                    self.set_manifest({**baseline, field: value})
                    with self.assertRaises(ValueError):
                        self.verify()
            missing = baseline.copy()
            del missing[field]
            self.set_manifest(missing)
            with self.assertRaises(ValueError):
                self.verify()
        for field, count in (("translation_units", 65538), ("generated_headers", 257)):
            self.set_manifest({**baseline, field: [{}] * count})
            with self.assertRaisesRegex(ValueError, "artifact entries"):
                self.verify()

    def test_multipart_portable_basenames_and_entry_required(self):
        baseline = self.multipart_manifest()
        for name in ("../outside.cpp", "sub/file.cpp", "sub\\file.cpp", "/absolute.cpp",
                     "C:drive.cpp", "a;inject.cpp", "a$.cpp", ".hidden.cpp", "NUL.cpp",
                     "com1.extra.cpp", "bad.hpp", "a" * 129 + ".cpp", "unicode\N{SNOWMAN}.cpp"):
            with self.subTest(name=name):
                entries = [{"file": name, "sha256": "0" * 64}]
                self.set_manifest({**baseline, "translation_units": entries})
                with self.assertRaisesRegex(ValueError, "portable"):
                    self.verify()
        self.set_manifest({**baseline, "translation_units": baseline["translation_units"][1:]})
        with self.assertRaisesRegex(ValueError, "include module source entry"):
            self.verify()

    def test_multipart_duplicate_fields_hashes_and_missing_files_refused(self):
        baseline = self.multipart_manifest()
        for entry in ({"file": "MODULE.cpp", "sha256": "0" * 64},
                      baseline["translation_units"][0]):
            self.set_manifest({**baseline, "translation_units": baseline["translation_units"] + [entry]})
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                self.verify()
        for entry in ({"file": "missing.cpp", "sha256": "0" * 64},
                      {"file": "module.cpp", "sha256": "x" * 64},
                      {"file": "module.cpp", "sha256": "0" * 64, "extra": 1}):
            self.set_manifest({**baseline, "translation_units": [entry]})
            with self.assertRaises(ValueError):
                self.verify()

    def test_multipart_headers_required_suffix_and_empty_list_supported(self):
        manifest = self.multipart_manifest()
        self.set_manifest({**manifest, "generated_headers": []})
        self.assertIn("module_unit:module_part_0000.cpp", self.verify()["files"])
        manifest["generated_headers"][0]["file"] = "module.cpp"
        self.set_manifest(manifest)
        with self.assertRaisesRegex(ValueError, "portable .hpp"):
            self.verify()

    def test_multipart_artifact_symlink_escape_refused(self):
        manifest = self.multipart_manifest()
        outside = self.root / "other"
        outside.mkdir()
        (outside / "escaped.cpp").write_text("// authored outside fixture\n")
        link = self.root / "escaped.cpp"
        try:
            link.symlink_to(outside / "escaped.cpp")
        except OSError:
            self.skipTest("Symlink creation unavailable")
        manifest["translation_units"].append({"file": link.name, "sha256": project.sha256(link)})
        self.set_manifest(manifest)
        with self.assertRaisesRegex(ValueError, "remain in manifest directory"):
            self.verify()
        # A same-directory alias is refused too: all listed inputs must be
        # ordinary files, matching CMake's artifact validation contract.
        link.unlink()
        link.symlink_to(self.root / "module_part_0000.cpp")
        manifest["translation_units"][-1]["sha256"] = project.sha256(link)
        self.set_manifest(manifest)
        with self.assertRaisesRegex(ValueError, "cannot be a symlink"):
            self.verify()

    def test_cmake_wrapper_passes_explicit_manifest(self):
        # Stop at configure, before any compiler invocation. Inspect the actual
        # generated project contract rather than mirroring its construction.
        actual_run = subprocess.run
        def execute(command, **kwargs):
            if command[0] == "cmake":
                raise subprocess.CalledProcessError(1, command)
            return actual_run(command, **kwargs)
        output = self.root / "wrapper-test"
        with patch.object(project.subprocess, "run", side_effect=execute):
            with self.assertRaises(subprocess.CalledProcessError):
                project.build(self.descriptor, output, allow_revision_override=True)
        wrapper = (output / "source/CMakeLists.txt").read_text()
        self.assertIn(' MANIFEST "' + (self.root / "module.json").as_posix() + '"', wrapper)

    def test_valid_identity_and_paths_independent_of_cwd(self):
        old = Path.cwd()
        try:
            os.chdir(self.root / "tool")
            checked = self.verify()
        finally:
            os.chdir(old)
        self.assertEqual(checked["files"]["payload"], self.root / "program.bin")
        self.assertTrue(checked["revision_override"])

    def test_revision_requires_explicit_override(self):
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            project.verify(self.descriptor)

    def test_dirty_or_untracked_source_refused_even_with_override(self):
        for name in ("pcerecomp/logic.py", "runtime/untracked.cpp"):
            path = self.tool / name
            old = path.read_bytes() if path.exists() else None
            path.write_bytes(b"// changed source\n")
            with self.assertRaisesRegex(ValueError, "source digest mismatch"):
                self.verify()
            if old is None:
                path.unlink()
            else:
                path.write_bytes(old)

    def test_doc_and_cache_changes_do_not_change_code_identity(self):
        before = project.source_identity(self.tool)
        (self.tool / "pcerecomp/__pycache__").mkdir()
        (self.tool / "pcerecomp/__pycache__/unused.py").write_text("ignored")
        (self.tool / "README.md").write_text("documentation only")
        self.assertEqual(before, project.source_identity(self.tool))

    def test_enclosing_git_repository_is_not_export_revision(self):
        with patch.object(project.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, str(self.root))):
            self.assertIsNone(project.source_identity(self.tool)["revision"])

    def test_strict_schema_abi_and_fields(self):
        for old, new in (("schema = 1", "schema = true"), (f"runtime_abi = {project.ABI}", f"runtime_abi = {project.ABI + 1}"), (f"runtime_abi = {project.ABI}", f"runtime_abi = {project.ABI - 1}"),
                         ('name = "fixture"', 'name = "fixture"\nunrecognized = 1'),
                         ("steps = 200", "steps = true"), ("joypad = 2", "joypad = true"),
                         ("wall_seconds = 5", "wall_seconds = 86401")):
            with self.subTest(new=new):
                self.replace(old, new)
                with self.assertRaises(ValueError):
                    self.verify()

    def test_finite_wall_limit_boundaries_are_bound_and_forwarded(self):
        identities = set()
        for seconds in (1, 600, 601, 900, 86400):
            with self.subTest(seconds=seconds):
                self.descriptor.write_text(self.text.replace("wall_seconds = 5", f"wall_seconds = {seconds}"))
                checked = self.verify()
                command = project.command_for(checked, Path("runner"))
                self.assertEqual(command[command.index("--wall-seconds") + 1], str(seconds))
                self.assertEqual(checked["config"]["limits"],
                                 {"steps": 200, "ticks": 100000, "wall_seconds": seconds})
                identities.add(project._binding(checked)["descriptor_sha256"])
        self.assertEqual(len(identities), 5)

    def test_wall_limit_requires_explicit_positive_finite_integer(self):
        for value in ("0", "-1", "86401", "18446744073709551616", "true", "1.5", '"900"', "inf"):
            with self.subTest(value=value):
                self.descriptor.write_text(self.text.replace("wall_seconds = 5", "wall_seconds = " + value))
                with self.assertRaises(ValueError):
                    self.verify()
        self.descriptor.write_text(self.text.replace("wall_seconds = 5\n", ""))
        with self.assertRaisesRegex(ValueError, "limits"):
            self.verify()

    def test_payload_mpr_and_extent_validation(self):
        for old, new in (("mpr = [255,248,128,129,130,131,132,0]", "mpr = [128]"),
                         ("physical_load = 1048576", "physical_load = 0"),
                         ("pc = 16384", "pc = 65536")):
            self.replace(old, new)
            with self.assertRaises(ValueError):
                self.verify()

    def test_file_hashes_and_manifest_abi_are_pinned(self):
        for name in ("program.bin", "module.cpp", "module.json"):
            path = self.root / name
            old = path.read_bytes()
            path.write_bytes(old + b" ")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                self.verify()
            path.write_bytes(old)
        path = self.root / "module.json"
        old_hash = project.sha256(path)
        path.write_text(json.dumps({"schema": 1, "runtime_abi": 25, "native_instructions_emitted": 2}))
        self.replace(old_hash, project.sha256(path))
        with self.assertRaisesRegex(ValueError, "Module schema/runtime ABI mismatch"):
            self.verify()

    def test_optional_bram_size_and_hash_validation(self):
        bram = self.root / "bram.bin"
        bram.write_bytes(b"short")
        self.descriptor.write_text(self.text + f'\n[bram]\npath = "bram.bin"\nsha256 = "{project.sha256(bram)}"\n')
        with self.assertRaisesRegex(ValueError, "exactly 2048"):
            self.verify()

    def test_manifest_rejects_nonobject_and_noninteger_abi(self):
        path = self.root / "module.json"
        old_hash = project.sha256(path)
        for manifest in ([], {"schema": 1, "runtime_abi": float(project.ABI), "native_instructions_emitted": 2}):
            path.write_text(json.dumps(manifest))
            self.replace(old_hash, project.sha256(path))
            with self.assertRaisesRegex(ValueError, "Module schema/runtime ABI mismatch"):
                self.verify()

    def test_command_is_vector_and_keeps_explicit_profiles(self):
        checked = self.verify()
        command = project.command_for(checked, self.root / "binary path.exe", dev_port=0, start_paused=True)
        self.assertEqual(command[0], str(self.root / "binary path.exe"))
        self.assertEqual(command[4], "255,248,128,129,130,131,132,0")
        self.assertEqual(command[command.index("--cd-unknown-status") + 1], "fault")
        self.assertEqual(command[-4:], ["--dev-start-paused", "on", "--dev-memory-write", "off"])
        with self.assertRaises(ValueError):
            project.command_for(checked, Path("test"), memory_write=True)
        with self.assertRaises(ValueError):
            project.command_for(checked, Path("test"), capture_limit=10)
        captured = project.command_for(checked, Path("test"), code_capture=self.root / "capture.json", capture_limit=4096)
        self.assertEqual(captured[-2:], ["--capture-limit", "4096"])

    def build_fixture(self):
        checked = self.verify()
        directory = self.root / "build"
        binary = directory / "bin/fixture.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"authored executable identity fixture")
        receipt = {"schema": 1, "kind": "pce-consumer-build", "binding": project._binding(checked),
                   "binary": str(binary), "binary_sha256": project.sha256(binary),
                   "output_files": {binary.name: project.sha256(binary)}, "desktop": False}
        (directory / "build-receipt.json").write_text(json.dumps(receipt))
        return directory, binary

    def test_stale_binary_or_descriptor_refused_before_execution(self):
        directory, binary = self.build_fixture()
        original = binary.read_bytes()
        binary.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "executable changed"):
            project.run(self.descriptor, directory, self.root / "run.json", allow_revision_override=True)
        binary.write_bytes(original)
        self.replace("steps = 200", "steps = 201")
        with self.assertRaisesRegex(ValueError, "does not match verified consumer"):
            project.run(self.descriptor, directory, self.root / "run.json", allow_revision_override=True)

    def test_receipt_preserves_actual_native_and_interpreted_work(self):
        directory, binary = self.build_fixture()
        # Mock only host execution; source identity Git queries remain real.
        actual_run = subprocess.run
        def execute(command, **kwargs):
            if command[0] == str(binary):
                return subprocess.CompletedProcess(command, 0, json.dumps({"stop": "step_limit", "native_steps": 7, "interpreter_steps": 93}))
            return actual_run(command, **kwargs)
        with patch.object(project.subprocess, "run", side_effect=execute):
            result = project.run(self.descriptor, directory, self.root / "run.json", allow_revision_override=True)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["work"], {"native": 7, "interpreted": 93, "total": 100, "native_fraction": 0.07})
        self.assertEqual(result["result"]["stop"], "step_limit")
        self.assertNotIn("boot_validation", result)
        with self.assertRaisesRegex(ValueError, "already exists"):
            project.run(self.descriptor, directory, self.root / "run.json", allow_revision_override=True)

    def test_cmake_path_injection_and_output_overwrite_refused(self):
        for value in ('folder;injection', 'folder$<expression>', 'folder"quote'):
            with self.assertRaises(ValueError):
                project._cmake_path(Path(value))
        with self.assertRaisesRegex(ValueError, "directory exists"):
            project.build(self.descriptor, self.root, allow_revision_override=True)

    def test_timeout_records_failure_instead_of_qualifying_partial_output(self):
        directory, binary = self.build_fixture()
        actual_run = subprocess.run
        def execute(command, **kwargs):
            if command[0] == str(binary):
                raise subprocess.TimeoutExpired(command, 15, output=b"{")
            return actual_run(command, **kwargs)
        with patch.object(project.subprocess, "run", side_effect=execute):
            result = project.run(self.descriptor, directory, self.root / "timeout.json", allow_revision_override=True)
        self.assertFalse(result["qualified"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["exit_code"], -1)

    def test_longer_official_run_keeps_explicit_wall_limit_and_outer_timeout(self):
        self.descriptor.write_text(self.text.replace("wall_seconds = 5", "wall_seconds = 900"))
        directory, binary = self.build_fixture()
        actual_run = subprocess.run
        observed = []
        def execute(command, **kwargs):
            if command[0] == str(binary):
                observed.append((command, kwargs))
                return subprocess.CompletedProcess(command, 0, json.dumps({
                    "stop": "step_limit", "native_steps": 7, "interpreter_steps": 0}))
            return actual_run(command, **kwargs)
        with patch.object(project.subprocess, "run", side_effect=execute):
            result = project.run(self.descriptor, directory, self.root / "long-run.json",
                                 allow_revision_override=True)
        self.assertTrue(result["qualified"])
        self.assertEqual(len(observed), 1)
        command, options = observed[0]
        self.assertEqual(command[command.index("--wall-seconds") + 1], "900")
        self.assertEqual(options["timeout"], 910)
        self.assertIs(options["shell"], False)

    def test_capture_receipt_checks_schema_and_retirement_total(self):
        directory, binary = self.build_fixture()
        actual_run = subprocess.run
        capture_path = self.root / "capture.json"
        capture = {"schema": 1, "runtime_abi": project.ABI, "capacity": 4, "dropped_instructions": 0,
                   "unreadable_instructions": 0, "retired_instructions": 7, "complete": True,
                   "observations": [{"pc": 16384, "mpr": [255,248,128,129,130,131,132,0],
                                     "physical": [1048576], "data": [234], "native_hits": 7, "interpreted_hits": 0}]}
        def execute(command, **kwargs):
            if command[0] == str(binary):
                capture_path.write_text(json.dumps(capture))
                return subprocess.CompletedProcess(command, 0, json.dumps({"native_steps": 7, "interpreter_steps": 0}))
            return actual_run(command, **kwargs)
        with patch.object(project.subprocess, "run", side_effect=execute):
            result = project.run(self.descriptor, directory, self.root / "captured.json", allow_revision_override=True,
                                 code_capture=capture_path, capture_limit=4)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["code_capture"]["observations"], 1)
        self.assertEqual(result["code_capture"]["sha256"], project.sha256(capture_path))

    def mock_execution(self, directory, binary, result, name, capture=None, capture_limit=None):
        actual_run = subprocess.run
        capture_path = self.root / f"{name}-capture.json"
        def execute(command, **kwargs):
            if command[0] == str(binary):
                if capture is not None:
                    capture_path.write_text(json.dumps(capture), encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, json.dumps(result))
            return actual_run(command, **kwargs)
        with patch.object(project.subprocess, "run", side_effect=execute):
            return project.run(self.descriptor, directory, self.root / f"{name}-receipt.json",
                               allow_revision_override=True,
                               code_capture=capture_path if capture is not None else None,
                               capture_limit=capture_limit)

    def reset_execution_fixture(self, profile="super", explicit_bram=False):
        descriptor = self.reset_descriptor(profile)
        bios = self.root / "authored.pce"
        original_hash = project.sha256(bios)
        rom = bytearray(bios.read_bytes())
        rom[8190:8192] = bytes([0x23, 0xE1])
        bios.write_bytes(rom)
        descriptor = descriptor.replace(original_hash, project.sha256(bios))
        if explicit_bram:
            bram = self.root / "authored-bram.bin"
            bram.write_bytes(bytes([0x5A]) * 2048)
            descriptor += f'\n[bram]\npath = "authored-bram.bin"\nsha256 = "{project.sha256(bram)}"\n'
        self.descriptor.write_text(descriptor, encoding="utf-8")
        directory, binary = self.build_fixture()
        # Literal expected startup fields are independent of the validator.
        boot = {"mode": "system-card-reset", "profile": profile,
                "initialization": "gear-deterministic-zero-v1", "vector_physical": 8190,
                "pc": 57635, "a": 0, "x": 0, "y": 0, "sp": 0, "p": 4,
                "clock_divisor": 12, "ticks": 0, "cycles": 0, "mpr": [0, 0, 0, 0, 0, 0, 0, 0],
                "bram": "explicit-image" if explicit_bram else "blank-unformatted"}
        return directory, binary, boot

    def test_reset_execution_checks_initial_metadata_not_final_cpu(self):
        directory, binary, boot = self.reset_execution_fixture("standard")
        report = self.mock_execution(directory, binary, {"boot": boot, "native_steps": 7,
                                     "interpreter_steps": 3, "pc": 0x4321, "a": 91}, "reset-valid")
        self.assertTrue(report["qualified"])
        self.assertEqual(report["boot_validation"], {"valid": True})
        self.assertEqual(report["result"]["pc"], 0x4321)
        self.assertEqual(report["result"]["boot"]["pc"], 57635)

    def test_reset_execution_requires_correct_explicit_bram_policy(self):
        directory, binary, boot = self.reset_execution_fixture("super", explicit_bram=True)
        result = {"boot": boot, "native_steps": 1, "interpreter_steps": 0}
        self.assertTrue(self.mock_execution(directory, binary, result, "bram-valid")["qualified"])
        boot["bram"] = "blank-unformatted"
        rejected = self.mock_execution(directory, binary, result, "bram-wrong")
        self.assertFalse(rejected["qualified"])
        self.assertIn("bram", rejected["boot_validation"]["error"])

    def test_reset_execution_rejects_missing_malformed_or_wrong_startup_fields(self):
        directory, binary, boot = self.reset_execution_fixture()
        variants = [None, [], {}, {key: value for key, value in boot.items() if key != "pc"},
                    boot | {"extra": 0}]
        for key, value in (("mode", "snapshot"), ("profile", "standard"), ("initialization", "guessed"),
                           ("vector_physical", 65534), ("pc", 0xE122), ("a", 1), ("x", 1), ("y", 1),
                           ("sp", 255), ("p", 0), ("clock_divisor", 3), ("ticks", 1), ("cycles", 1),
                           ("bram", "explicit-image"), ("mpr", [0] * 7), ("mpr", [0] * 7 + [1]),
                           ("mpr", [False] * 8), ("mpr", [0.0] * 8), ("ticks", False), ("pc", 57635.0)):
            variants.append(boot | {key: value})
        for index, variant in enumerate(variants):
            with self.subTest(index=index):
                result = {"native_steps": 7, "interpreter_steps": 0}
                if index != 0:
                    result["boot"] = variant
                report = self.mock_execution(directory, binary, result, f"reset-invalid-{index}")
                self.assertFalse(report["qualified"])
                self.assertFalse(report["boot_validation"]["valid"])
                self.assertEqual(report["work"]["native"], 7)

    @staticmethod
    def authored_capture(native=7, interpreted=0, dropped=0, unreadable=0, capacity=4):
        observations = []
        if native + interpreted:
            observations = [{"pc": 16384, "mpr": [255, 248, 128, 129, 130, 131, 132, 0],
                             "physical": [1048576], "data": [234],
                             "native_hits": native, "interpreted_hits": interpreted}]
        return {"schema": 1, "runtime_abi": project.ABI, "capacity": capacity,
                "dropped_instructions": dropped, "unreadable_instructions": unreadable,
                "retired_instructions": native + interpreted + dropped + unreadable,
                "complete": not (dropped + unreadable), "observations": observations}

    def test_fresh_capture_rejects_historical_abi_without_changing_offline_format(self):
        from pcerecomp.capture import validate_capture
        directory, binary = self.build_fixture()
        for abi in range(12, project.ABI):
            with self.subTest(abi=abi):
                capture = self.authored_capture() | {"runtime_abi": abi}
                self.assertEqual(len(validate_capture(capture)), 1)
                report = self.mock_execution(directory, binary, {"native_steps": 7, "interpreter_steps": 0},
                                             f"capture-abi-{abi}", capture, capture_limit=4)
                self.assertFalse(report["qualified"])
                self.assertIn("runtime ABI", report["code_capture"]["error"])

    def test_fresh_capture_requires_requested_or_default_capacity(self):
        directory, binary = self.build_fixture()
        for index, (declared, actual, valid) in enumerate(((4, 5, False), (4, 4, True),
                                                        (None, 4, False), (None, 16384, True))):
            with self.subTest(declared=declared, actual=actual):
                report = self.mock_execution(directory, binary, {"native_steps": 7, "interpreter_steps": 0},
                                             f"capture-capacity-{index}", self.authored_capture(capacity=actual), declared)
                self.assertEqual(report["qualified"], valid)

    def test_fresh_capture_rejects_wrong_tier_hits_and_total(self):
        directory, binary = self.build_fixture()
        for index, (capture, native, interpreted) in enumerate((
                (self.authored_capture(), 0, 7),
                (self.authored_capture(native=0, interpreted=7), 7, 0),
                (self.authored_capture(), 8, 0),
                (self.authored_capture(native=3, interpreted=2, dropped=2), 2, 5),
                (self.authored_capture(native=2, interpreted=3, unreadable=2), 5, 2))):
            with self.subTest(index=index):
                report = self.mock_execution(directory, binary, {"native_steps": native, "interpreter_steps": interpreted},
                                             f"capture-counters-{index}", capture, capture_limit=4)
                self.assertFalse(report["qualified"])
                self.assertFalse(report["code_capture"]["valid"])

    def test_fresh_lossful_and_zero_retirement_captures_retain_their_actual_scope(self):
        directory, binary = self.build_fixture()
        cases = ((self.authored_capture(native=3, interpreted=2, dropped=1, unreadable=1), 4, 3, 2),
                 (self.authored_capture(native=0, interpreted=0, unreadable=7), 4, 3, 7),
                 (self.authored_capture(native=0, interpreted=0), 0, 0, 0))
        for index, (capture, native, interpreted, lost) in enumerate(cases):
            with self.subTest(index=index):
                before = copy.deepcopy(capture)
                report = self.mock_execution(directory, binary, {"native_steps": native, "interpreter_steps": interpreted},
                                             f"capture-scope-{index}", capture, capture_limit=4)
                self.assertTrue(report["qualified"])
                self.assertEqual(capture, before)
                self.assertEqual(report["code_capture"]["unclassified_retirements"], lost)
                self.assertEqual(report["code_capture"]["complete"], lost == 0)
                self.assertEqual(report["code_capture"]["native_hits"], sum(i["native_hits"] for i in capture["observations"]))


    def test_save_identity_binds_media_boot_and_contract_not_native_coverage(self):
        self.descriptor.write_text(self.reset_descriptor(), encoding="utf-8")
        checked = self.verify()
        identity = project.save_identity(checked, "a" * 64)
        changed = copy.deepcopy(checked)
        changed["tool_identity"]["source_sha256"] = "b" * 64
        changed["identities"]["module_source"] = "c" * 64
        self.assertEqual(identity, project.save_identity(changed, "a" * 64))
        for field in ("bios", "disc", "toc", "disc_component:audio.bin", "disc_component:data.bin"):
            changed = copy.deepcopy(checked)
            changed["identities"][field] = "d" * 64
            self.assertNotEqual(identity, project.save_identity(changed, "a" * 64))
        changed = copy.deepcopy(checked)
        changed["config"]["boot"]["profile"] = "standard"
        self.assertNotEqual(identity, project.save_identity(changed, "a" * 64))
        self.assertNotEqual(identity, project.save_identity(checked, "e" * 64))
        for contract in (True, "", "A" * 64, "a" * 63):
            with self.assertRaises(ValueError):
                project.save_identity(checked, contract)

    def test_save_sessions_require_explicit_options_and_supported_recipe(self):
        for options in ({"save_root": self.root}, {"save_namespace": "test"},
                        {"save_contract": "a" * 64},
                        {"save_root": self.root, "save_namespace": "test", "save_contract": "a" * 64}):
            with self.assertRaises(ValueError):
                project.run(self.descriptor, self.root, self.root / "receipt.json",
                            allow_revision_override=True, **options)
        directory, binary, boot = self.reset_execution_fixture(explicit_bram=True)
        with self.assertRaisesRegex(ValueError, "descriptor BRAM seed"):
            project.run(self.descriptor, directory, self.root / "receipt.json", allow_revision_override=True,
                        save_root=self.root, save_namespace="test", save_contract="a" * 64)

    def test_consumer_save_session_two_launches_and_failed_runs_preserve_save(self):
        directory, binary, boot = self.reset_execution_fixture()
        saves = self.root / "saves"
        saves.mkdir()
        payload = bytes((i * 17 + 3) & 255 for i in range(2048))
        actual_run = subprocess.run
        launches = []
        stop = "dev_quit"
        returncode = 0
        write_export = True
        def execute(command, **kwargs):
            if command[0] != str(binary):
                return actual_run(command, **kwargs)
            seeded = "--bram" in command
            launches.append(seeded)
            if seeded:
                self.assertEqual(Path(command[command.index("--bram") + 1]).read_bytes(), payload)
            if write_export:
                Path(command[command.index("--bram-out") + 1]).write_bytes(payload)
            initial = dict(boot, bram="explicit-image" if seeded else "blank-unformatted")
            return subprocess.CompletedProcess(command, returncode, json.dumps(
                {"stop": stop, "boot": initial, "native_steps": 7, "interpreter_steps": 0}))
        def launch(name):
            with patch.object(project.subprocess, "run", side_effect=execute):
                return project.run(self.descriptor, directory, self.root / (name + ".json"),
                                   allow_revision_override=True, save_root=saves,
                                   save_namespace="authored", save_contract="a" * 64)
        first = launch("first")
        self.assertTrue(first["qualified"])
        self.assertTrue(first["bram_session"]["committed"])
        self.assertFalse(first["bram_session"]["seeded"])
        saved = (saves / "authored.bram.json").read_bytes()
        second = launch("second")
        self.assertTrue(second["qualified"])
        self.assertTrue(second["bram_session"]["seeded"])
        self.assertEqual((saves / "authored.bram.json").read_bytes(), saved)
        for index, (stop, returncode, write_export) in enumerate((
                ("bus_fault", 3, True), ("wall_limit", 0, True), ("dev_quit", 0, False))):
            failed = launch("failed" + str(index))
            self.assertFalse(failed["qualified"])
            self.assertFalse(failed["bram_session"]["committed"])
            self.assertEqual((saves / "authored.bram.json").read_bytes(), saved)
        self.assertEqual(launches, [False, True, True, True, True])
        self.assertNotIn("saves", first["binding"]["files"])

    def test_consumer_save_receipts_and_captures_stay_outside_store(self):
        directory, binary, _ = self.reset_execution_fixture()
        saves = self.root / "saves"
        saves.mkdir()
        for receipt, capture in ((saves / "run.json", None),
                                 (self.root / "run.json", saves / "capture.json")):
            with self.assertRaisesRegex(ValueError, "outside the save root"):
                project.run(self.descriptor, directory, receipt, allow_revision_override=True,
                            save_root=saves, save_namespace="test", save_contract="a" * 64,
                            code_capture=capture)


    def test_vdc_access_profile_is_explicit_validated_and_forwarded(self):
        checked = self.verify()
        self.assertNotIn("--vdc-access", project.command_for(checked, Path("runner")))
        original = self.descriptor.read_text()
        for value in ("queued", "immediate"):
            self.descriptor.write_text(original.replace("[runtime]", f'[runtime]\nvdc_access = "{value}"'), encoding="utf-8")
            selected = self.verify()
            command = project.command_for(selected, Path("runner"))
            self.assertEqual(command.count("--vdc-access"), 1)
            self.assertEqual(command[command.index("--vdc-access")+1], value)
            self.assertNotEqual(project._binding(checked), project._binding(selected))
        for value in ('"unknown"', 'true', '24', '["queued"]'):
            self.descriptor.write_text(original.replace("[runtime]", '[runtime]\nvdc_access = '+value), encoding="utf-8")
            with self.assertRaises(ValueError): self.verify()
        self.descriptor.write_text(original.replace("[runtime]", '[runtime]\nvdc_access = "queued"').replace('video = "continuous"', 'video = "snapshot"'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "clocked VDC"): self.verify()

    def test_vdc_access_report_requires_exact_profile_and_typed_queue_state(self):
        original = self.descriptor.read_text()
        self.descriptor.write_text(original.replace("[runtime]", '[runtime]\nvdc_access = "queued"'), encoding="utf-8")
        checked = self.verify()
        value = dict(profile="queued", pending_read=False, pending_write=False, delay=0, phase=0, wait_ticks=27)
        self.assertEqual(project._vdc_access_provenance(checked, {"vdc_access": value}), {"valid": True})
        variants = [None, {}, dict(value, profile="immediate"), dict(value, extra=0),
                    dict(value, pending_read=1), dict(value, pending_write=0), dict(value, delay=True),
                    dict(value, delay=1), dict(value, phase=3), dict(value, wait_ticks=True),
                    dict(value, wait_ticks=1), dict(value, wait_ticks=-3)]
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.assertFalse(project._vdc_access_provenance(checked, {"vdc_access": candidate})["valid"])
        self.descriptor.write_text(original.replace("[runtime]", '[runtime]\nvdc_access = "immediate"'), encoding="utf-8")
        checked = self.verify()
        immediate = dict(value, profile="immediate", wait_ticks=0)
        self.assertTrue(project._vdc_access_provenance(checked, {"vdc_access": immediate})["valid"])
        for field, invalid in (("pending_read", True), ("pending_write", True), ("delay", 1), ("phase", 1), ("wait_ticks", 3)):
            self.assertFalse(project._vdc_access_provenance(checked, {"vdc_access": dict(immediate, **{field: invalid})})["valid"])

    def test_explicit_vdc_profile_mismatch_does_not_qualify_execution(self):
        original = self.descriptor.read_text()
        self.descriptor.write_text(original.replace("[runtime]", '[runtime]\nvdc_access = "queued"'), encoding="utf-8")
        directory, binary = self.build_fixture()
        actual_run = subprocess.run
        value = dict(profile="queued", pending_read=False, pending_write=False, delay=0, phase=0, wait_ticks=9)
        for index, reported in enumerate((value, dict(value, profile="immediate"), None)):
            def execute(command, **kwargs):
                if command[0] != str(binary): return actual_run(command, **kwargs)
                self.assertEqual(command[command.index("--vdc-access")+1], "queued")
                return subprocess.CompletedProcess(command, 0, json.dumps({"native_steps": 7, "interpreter_steps": 0, "vdc_access": reported}))
            with patch.object(project.subprocess, "run", side_effect=execute):
                report = project.run(self.descriptor, directory, self.root / f"vdc-{index}.json", allow_revision_override=True)
            self.assertEqual(report["qualified"], index == 0)
            self.assertEqual(report["vdc_access_validation"]["valid"], index == 0)


if __name__ == "__main__":
    unittest.main()
