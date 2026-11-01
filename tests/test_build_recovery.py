"""Authored recovery state, integrity, dependency and interruption controls."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pcerecomp import build_recovery as recovery


class RecoveryPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_atomic_new_publication_never_overwrites_and_requires_strict_json(self):
        path = self.root/'contract.json'
        recovery._write_new(path, {'authored':1})
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            recovery._write_new(path, {'authored':2})
        self.assertEqual(path.read_bytes(), original)
        path.write_text('{"duplicate":1,"duplicate":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            recovery._read(path)
        path.write_text('{"overflow":1e9999}')
        with self.assertRaisesRegex(ValueError, 'finite'):
            recovery._read(path)
        path.write_text('{ "authored": 1 }')
        with self.assertRaisesRegex(ValueError, 'canonical'):
            recovery._read(path)

    def test_same_size_same_mtime_tamper_and_hardlink_refused(self):
        path = self.root/'authored.obj'
        path.write_bytes(b'old')
        before = recovery._hash(path)
        stamp = path.stat()
        path.write_bytes(b'new')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertNotEqual(before, recovery._hash(path))
        os.link(path, self.root/'extra.obj')
        with self.assertRaisesRegex(ValueError, 'hardlink'):
            recovery._hash(path)

    def test_paths_and_linked_parents_refused(self):
        for name in ('../outside.obj', '/outside.obj', 'C:/outside.obj', 'sub\\object.obj',
                     'sub/../object.obj', 'sub//object.obj'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                recovery._relative(self.root, name)
        target = self.root/'target';target.mkdir()
        alias = self.root/'alias'
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            return
        with self.assertRaisesRegex(ValueError, 'ordinary'):
            recovery._relative(self.root, 'alias/object.obj')

    def test_os_lock_rejects_concurrent_holder_and_is_reusable(self):
        with recovery._locked(self.root):
            with self.assertRaisesRegex(ValueError, 'busy'):
                with recovery._locked(self.root):
                    self.fail('second holder acquired a live lock')
        with recovery._locked(self.root) as held:
            held()

    def test_unproven_process_cleanup_marker_quarantines_entry_and_live_session(self):
        lock = self.root/recovery._LOCK
        lock.write_bytes(b'PCERECOMP_UNPROVEN_PROCESS_CLEANUP_V1\n')
        with self.assertRaisesRegex(ValueError, 'quarantined'):
            with recovery._locked(self.root):
                self.fail('quarantined directory acquired')
        lock.write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'quarantined'):
            with recovery._locked(self.root) as held:
                if os.name == 'nt':
                    import ctypes
                    from ctypes import wintypes as w
                    from pcerecomp import build_process
                    handle=build_process._directory_leases[build_process._job_name(self.root)]
                    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                    kernel.WriteFile.argtypes=[w.HANDLE,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD),w.LPVOID]
                    kernel.WriteFile.restype=w.BOOL
                    raw=ctypes.create_string_buffer(b'quarantine')
                    written=w.DWORD()
                    self.assertTrue(kernel.WriteFile(handle,raw,10,ctypes.byref(written),None))
                else:
                    lock.write_bytes(b'quarantine')
                held()

    def test_checkpoint_chain_and_last_record_checksum_refuse_tampering(self):
        objects = ['authored.obj']
        first = recovery._sealed(dict(schema=1, contract_sha256='a'*64, sequence=1,
            previous_sha256=None, objects={}, attempt=1))
        recovery._write_new(self.root/'checkpoint-000001.json', first)
        second = recovery._sealed(dict(schema=1, contract_sha256='a'*64, sequence=2,
            previous_sha256=recovery._digest(first), objects={}, attempt=2))
        path = self.root/'checkpoint-000002.json'
        recovery._write_new(path, second)
        self.assertEqual(recovery._checkpoints(self.root, 'a'*64, objects)[0], 2)
        second['attempt'] = 999
        path.write_bytes(recovery._canonical(second)+b'\n')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            recovery._checkpoints(self.root, 'a'*64, objects)
        path.unlink()
        first['previous_sha256'] = 'b'*64
        first = recovery._sealed({k:v for k,v in first.items() if k != 'sha256'})
        (self.root/'checkpoint-000001.json').write_bytes(recovery._canonical(first)+b'\n')
        with self.assertRaisesRegex(ValueError, 'chain'):
            recovery._checkpoints(self.root, 'a'*64, objects)

    def test_actual_compdb_must_cover_actual_cxx_graph_and_confine_outputs(self):
        source = self.root/'source.cpp';source.write_text('/* authored */')
        (self.root/'build.ninja').write_text('  RSP_FILE = sub\\authored.rsp\n')
        (self.root/'sub').mkdir()
        context = dict(roots=[self.root])
        rows = [dict(output='authored.obj', directory=str(self.root), file=str(source))]
        def captured(context, binary, *arguments):
            return json.dumps(rows) if arguments[-1] == 'compdb' else (
                'authored.obj: CXX_COMPILER__authored_Release\n'
                'authored.exe: CXX_EXECUTABLE_LINKER__authored_Release\n')
        with patch.object(recovery, '_captured', side_effect=captured):
            self.assertEqual(recovery._graph(context, self.root)['objects'], ['authored.obj'])
            self.assertEqual(recovery._graph(context, self.root)['response_files'], ['sub/authored.rsp'])
            rows[0]['output'] = './authored.obj'
            self.assertEqual(recovery._graph(context, self.root)['objects'], ['authored.obj'])
            rows.append(dict(rows[0],output='authored.obj'))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                recovery._graph(context, self.root)
            rows.pop()
            rows[0]['output'] = '../outside.obj'
            with self.assertRaises(ValueError):
                recovery._graph(context, self.root)

    def test_ninja_dependencies_require_valid_nonempty_hashed_header_closure(self):
        header = self.root/'authored.hpp';header.write_text('/* authored */')
        context = dict(roots=[self.root])
        text = f'authored.obj: #deps 1, deps mtime 1 (VALID)\n    {header}\n\n'
        with patch.object(recovery, '_captured', return_value=text):
            self.assertEqual(recovery._dependencies(context, self.root, 'authored.obj'),
                             {str(header):recovery._hash(header)})
        for text in ('authored.obj: #deps 1, deps mtime 1 (STALE)\n',
                     'authored.obj: #deps 0, deps mtime 1 (VALID)\n',
                     f'other.obj: #deps 1, deps mtime 1 (VALID)\n    {header}\n'):
            with self.subTest(text=text), patch.object(recovery, '_captured', return_value=text), \
                    self.assertRaises(ValueError):
                recovery._dependencies(context, self.root, 'authored.obj')

    def test_batched_dependencies_hash_shared_headers_once_and_ignore_unsealed_stale_records(self):
        header = self.root/'authored.hpp';header.write_text('/* authored */')
        context = dict(roots=[self.root])
        text = ''.join(f'{output}: #deps 1, deps mtime 1 (VALID)\n    {header}\n\n'
                       for output in ('first.obj','second.obj'))
        text += f'unsealed.obj: #deps 1, deps mtime 1 (STALE)\n    {header}\n\n'
        with patch.object(recovery, '_captured', return_value=text) as capture, \
                patch.object(recovery, '_hash', wraps=recovery._hash) as hashed:
            result = recovery._dependency_inventory(context, self.root, ['first.obj','second.obj'])
        self.assertEqual(set(result), {'first.obj','second.obj'})
        self.assertEqual(capture.call_count, 1)
        self.assertEqual(hashed.call_count, 1)


class RecoveryProtocolTests(unittest.TestCase):
    """Mock the compiler, never the durable state or artifact hashing protocol."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base/'output'
        self.descriptor = self.base/'authored.toml';self.descriptor.write_text('authored fixture')
        self.tool = self.base/'tool'
        for name in ('runtime', 'cmake', 'pcerecomp'):
            (self.tool/name).mkdir(parents=True)
        (self.tool/'CMakeLists.txt').write_text('# authored')
        self.bundle = self.base/'bundle';self.bundle.mkdir()
        self.header = self.bundle/'header.hpp';self.header.write_text('old')
        self.module = self.base/'module';self.module.mkdir()
        self.source = self.module/'module.cpp';self.source.write_text('/* authored */')
        self.graph = dict(objects=['first.obj','second.obj'], links=['bin/pce-consumer.exe'])
        self.project = dict(config=dict(runtime=dict(video='continuous')), tool_root=self.tool,
                            files=dict(module_source=self.source))
        self.invocations = []
        self.interrupt = True
        self.quiescences = []
        def prepare(project, **kwargs):
            return dict(contract=dict(trees=dict(toolchain=dict(path=str(self.bundle)),dependencies=[]),
                                      source=recovery._hash(self.source), header=recovery._hash(self.header)),
                        environment={'PATH':'authored-controlled'}, tools=dict(ninja='ninja',cmake='cmake'),
                        roots=[self.bundle,self.module,self.tool], tool_root=self.tool)
        def configure(project, root, **kwargs):
            (root/'source').mkdir();(root/'build/CMakeFiles').mkdir(parents=True)
            (root/'build/bin').mkdir()
            for name in ('source/CMakeLists.txt','build/CMakeCache.txt','build/build.ninja',
                         'build/CMakeFiles/rules.ninja'):
                (root/name).write_text('# authored configuration ' + name)
            return [['configure']]
        def run(command, *, env, cwd):
            self.invocations.append(list(command))
            if command[0] == 'ninja':
                output = command[-1]
                (cwd/'build'/output).write_bytes(b'authored object ' + output.encode())
                if self.interrupt and output == 'second.obj':
                    (cwd/'build/.ninja_lock').touch()
                    raise KeyboardInterrupt('authored interrupted compile')
            else:
                (cwd/'build/bin/pce-consumer.exe').write_bytes(b'MZ-authored binary')
        def compile(project, root, *, commands, runner, **kwargs):
            runner(['cmake','--build',str(root/'build')])
            binary=root/'build/bin/pce-consumer.exe'
            return dict(schema=1,kind='pce-consumer-build',commands=commands,
                        binary=str(binary),binary_sha256=recovery._hash(binary)['sha256'],
                        output_files={binary.name:recovery._hash(binary)['sha256']},execution_evidence=False)
        patches = [patch('pcerecomp.project.verify', return_value=self.project),
                   patch('pcerecomp.project._binding', side_effect=lambda project:dict(
                       descriptor=recovery._hash(self.descriptor))),
                   patch('pcerecomp.project._configure_build', side_effect=configure),
                   patch('pcerecomp.project._compile_configured', side_effect=compile),
                   patch('pcerecomp.build_inputs.prepare', side_effect=prepare),
                   patch('pcerecomp.build_inputs.configuration_identity', return_value={'authored':True}),
                   patch('pcerecomp.build_inputs.verify_closure', return_value={'authored':True}),
                   patch('pcerecomp.build_process.run', side_effect=run),
                   patch('pcerecomp.build_process.quiesce', side_effect=lambda root:self.quiescences.append(root)),
                   patch.object(recovery, '_graph', return_value=self.graph),
                   patch.object(recovery, '_dependency_inventory', side_effect=lambda context,binary,outputs:{
                       output:{str(self.header):recovery._hash(self.header)} for output in outputs}),
                   patch.object(recovery, '_CHUNK', 1)]
        for patcher in patches:
            patcher.start();self.addCleanup(patcher.stop)

    def start_interrupted(self):
        with self.assertRaises(KeyboardInterrupt):
            recovery.build(self.descriptor, self.root, toolchain_root=self.bundle)
        self.assertFalse((self.root/'build-receipt.json').exists())
        self.assertTrue((self.root/'.pce-recovery/contract.json').exists())
        self.assertTrue((self.root/'.pce-recovery/configured.json').exists())
        self.assertTrue((self.root/'.pce-recovery/checkpoint-000001.json').exists())
        self.assertEqual(recovery._read(self.root/'.pce-recovery/attempt-000001-result.json')['status'], 'failed')
        self.interrupt = False
        self.invocations.clear()

    def test_resume_retains_only_sealed_object_and_rebuilds_unsealed_partial(self):
        self.start_interrupted()
        first = self.root/'build/first.obj'
        original = first.read_bytes()
        (self.root/'build/second.obj').write_bytes(b'unsealed partial output')
        receipt = recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(receipt['recovery']['verified_retained_objects'], ['first.obj'])
        self.assertEqual(receipt['recovery']['recompiled_unsealed_objects'], ['second.obj'])
        self.assertFalse(receipt['execution_evidence'])
        self.assertEqual([row[-1] for row in self.invocations if row[0] == 'ninja'], ['second.obj'])
        self.assertTrue((self.root/'.pce-recovery/attempt-000001-result.json').exists())
        with self.assertRaisesRegex(ValueError, 'completed'):
            recovery.build(self.descriptor,self.root,resume=True)

    def test_changed_sealed_object_refuses_before_any_compile_or_cleanup(self):
        self.start_interrupted()
        first = self.root/'build/first.obj';data=first.read_bytes();stamp=first.stat()
        first.write_bytes(bytes([data[0]^1])+data[1:])
        os.utime(first,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        partial = self.root/'build/second.obj';before=partial.read_bytes()
        with self.assertRaisesRegex(ValueError, 'integrity'):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(self.invocations, [])
        self.assertEqual(partial.read_bytes(),before)

    def test_missing_sealed_object_is_explicitly_rebuilt(self):
        self.start_interrupted()
        (self.root/'build/first.obj').unlink()
        receipt=recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(receipt['recovery']['missing_sealed_objects_rebuilt'], ['first.obj'])
        self.assertEqual(receipt['recovery']['verified_retained_objects'], [])

    def test_source_header_configuration_and_foreign_package_changes_fail_closed(self):
        for name in ('source','header','configuration','foreign','foreign-dir','foreign-file','hardlink'):
            with self.subTest(name=name):
                # Each negative leaves the original checkpoint available.
                if not self.root.exists():
                    self.start_interrupted()
                target = {'source':self.source,'header':self.header,
                          'configuration':self.root/'build/CMakeCache.txt'}.get(name)
                if target:
                    data=target.read_bytes();stamp=target.stat()
                    target.write_bytes(bytes([data[0]^1])+data[1:])
                    os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                elif name == 'foreign':
                    target=self.root/'build/bin/foreign.exe';target.write_bytes(b'MZ foreign')
                elif name == 'foreign-dir':
                    target=self.root/'build/foreign';target.mkdir()
                elif name == 'foreign-file':
                    target=self.root/'foreign.txt';target.write_text('not an owned output')
                else:
                    target=self.root/'extra-hardlink';os.link(self.root/'build/first.obj',target)
                before=(self.root/'build/second.obj').read_bytes()
                with self.assertRaises(ValueError):
                    recovery.build(self.descriptor,self.root,resume=True)
                self.assertEqual(self.invocations, [])
                self.assertEqual((self.root/'build/second.obj').read_bytes(),before)
                if name in ('source','header','configuration'):
                    target.write_bytes(data);os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                else:
                    target.rmdir() if target.is_dir() else target.unlink()

    def test_incomplete_configure_and_old_unsealed_directory_are_not_retrofitted(self):
        self.root.mkdir();(self.root/'build').mkdir()
        with self.assertRaises((ValueError,FileNotFoundError)):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(self.invocations, [])
        self.assertFalse((self.root/'.pce-recovery').exists())

    def test_different_explicit_resume_options_refused(self):
        self.start_interrupted()
        with self.assertRaisesRegex(ValueError, 'changed resume option'):
            recovery.build(self.descriptor,self.root,resume=True,desktop=True)
        self.assertEqual(self.invocations, [])

    def test_leaf_rejects_wrong_types_and_malformed_options_before_creating_output(self):
        for options in ({'resume':1}, {'allow_revision_override':1}, {'desktop':1},
                        {'cmake_args':['not-D=value']}, {'cmake_args':['-DCMAKE_CXX_COMPILER=x\n']},
                        {'cmake_args':['-DCMAKE_CXX_COMPILER=x\x00']}, {'cmake_args':[1]},
                        {'cmake_args':'-DCMAKE_CXX_COMPILER=x'},
                        {'cmake_args':['-DCMAKE_CXX_COMPILER=x','-DCMAKE_CXX_COMPILER=y']}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError,'Build recovery'):
                recovery.build(self.descriptor,self.root,**options)
            self.assertFalse(self.root.exists())

    def test_wrong_typed_saved_options_refuse_even_with_updated_checksum(self):
        self.start_interrupted()
        path=self.root/'.pce-recovery/contract.json'
        value=recovery._read(path);value['options']['desktop']=0
        value=recovery._sealed({key:item for key,item in value.items() if key != 'sha256'})
        path.write_bytes(recovery._canonical(value)+b'\n')
        with self.assertRaisesRegex(ValueError,'boolean'):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(self.invocations, [])

    def test_deleted_success_receipt_does_not_reopen_completed_attempt(self):
        self.start_interrupted()
        recovery.build(self.descriptor,self.root,resume=True)
        (self.root/'build-receipt.json').unlink()
        self.invocations.clear()
        with self.assertRaisesRegex(ValueError, 'completed attempt'):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(self.invocations, [])

    def test_prior_attempt_receipt_tamper_refuses_before_compile(self):
        self.start_interrupted()
        path=self.root/'.pce-recovery/attempt-000001-result.json'
        value=recovery._read(path);value['status']='complete'
        path.write_bytes(recovery._canonical(value)+b'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertEqual(self.invocations, [])

    def test_package_byte_change_after_compile_cannot_publish_stale_receipt(self):
        self.start_interrupted()
        def tamper(context,binary):
            (binary/'bin/pce-consumer.exe').write_bytes(b'MZ modified after receipt hashing')
            return {'authored':True}
        with patch('pcerecomp.build_inputs.verify_closure',side_effect=tamper), \
                self.assertRaisesRegex(ValueError,'final binary/package'):
            recovery.build(self.descriptor,self.root,resume=True)
        self.assertFalse((self.root/'build-receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
