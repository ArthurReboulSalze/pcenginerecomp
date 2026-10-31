"""Prepare every authored example through the official consumer verifier."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from pcerecomp.abi import ABI
from pcerecomp import project

ROOT = Path(__file__).resolve().parent.parent


def prepare_module(name):
    path = ROOT/'examples'/name/'prepare.py'
    spec = importlib.util.spec_from_file_location('authored_' + name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExampleConsumerTests(unittest.TestCase):
    def test_all_prepared_examples_verify_against_current_tool_and_emitter(self):
        cases = [('consumer', {}), ('reset-consumer', {'profile': 'standard'}),
                 ('reset-consumer', {'profile': 'super'}), ('persistent-consumer', {})]
        with tempfile.TemporaryDirectory() as temporary:
            for index, (name, options) in enumerate(cases):
                with self.subTest(example=name, options=options):
                    directory = Path(temporary)/str(index)
                    descriptor = prepare_module(name).prepare(directory, ROOT, **options)
                    checked = project.verify(descriptor)
                    manifest = json.loads((directory/'module/module.json').read_text(encoding='utf-8'))
                    self.assertEqual(checked['config']['tool']['runtime_abi'], ABI)
                    self.assertEqual(manifest['runtime_abi'], ABI)
                    self.assertEqual(checked['config']['tool']['source_sha256'],
                                     project.source_identity(ROOT)['source_sha256'])
                    self.assertEqual(checked['config']['runtime']['cd_unknown_status'], 'fault')
                    command = project.command_for(checked, directory/'runner')
                    if name == 'consumer':
                        self.assertNotIn('--system-card-reset', command)
                        self.assertEqual(checked['config']['payload']['pc'], 0x4000)
                    else:
                        self.assertEqual(command[1:3], ['--system-card-reset', options.get('profile', 'standard')])


if __name__ == '__main__':
    unittest.main()
