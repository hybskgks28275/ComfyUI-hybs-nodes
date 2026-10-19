"""Regression tests that run without installing ComfyUI or loading models."""

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_source(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selection = load_source('selection_helpers', 'hybs_selection.py')
metadata = load_source('metadata_helpers', 'hybs_prompt_metadata.py')


class SelectionTests(unittest.TestCase):
    def test_json_and_legacy_dictionary_preserve_order_and_duplicates(self):
        expected = [None, 'a', 'a', 1.5]
        self.assertEqual(selection.selection_values(json.dumps(expected)), expected)
        self.assertEqual(selection.selection_values({'selected': expected}), expected)

    def test_invalid_payloads_do_not_become_lists(self):
        for value in ('{', '{}', 'null', '42', '', None, [], {'selected': 'a'}):
            with self.subTest(value=value):
                self.assertEqual(selection.selection_values(value), [])


class MetadataTests(unittest.TestCase):
    def test_exact_id_takes_priority_over_suffix(self):
        workflow = {'nodes': [
            {'id': 2, 'widgets_values': ['wrong']},
            {'id': '10:2', 'widgets_values': ['right']},
        ]}
        self.assertEqual(metadata._prompt_from_workflow_id(workflow, '10:2'), 'right')

    def test_ambiguous_suffix_does_not_pick_an_arbitrary_subgraph(self):
        workflow = {'nodes': [], 'definitions': {'subgraphs': [
            {'nodes': [{'id': 2, 'widgets_values': ['one']}]},
            {'nodes': [{'id': 2, 'widgets_values': ['two']}]},
        ]}}
        self.assertEqual(metadata._prompt_from_workflow_id(workflow, '10:2'), '')

    def test_unique_subgraph_suffix_remains_compatible(self):
        workflow = {'nodes': [{'id': 10, 'subgraph': {'nodes': [
            {'id': 2, 'widgets_values': ['nested']}
        ]}}]}
        self.assertEqual(metadata._prompt_from_workflow_id(workflow, '10:2'), 'nested')

    def test_zero_is_a_valid_node_id(self):
        workflow = {'nodes': [{'id': 0, 'widgets_values': ['zero']}]}
        self.assertEqual(metadata._prompt_from_workflow_id(workflow, 0), 'zero')

    def test_api_prompt_fallback_and_ambiguity(self):
        prompt = {'10:2': {'inputs': {'text': 'prompt'}}}
        self.assertEqual(metadata._prompt_from_id(None, prompt, '2'), 'prompt')
        prompt['11:2'] = {'inputs': {'text': 'another'}}
        self.assertEqual(metadata._prompt_from_id(None, prompt, '2'), '')
        self.assertEqual(metadata._prompt_from_id(None, prompt, '10:2'), 'prompt')

    def test_json_metadata_and_missing_metadata(self):
        workflow = {'nodes': []}
        self.assertEqual(metadata._find_workflow({'workflow': json.dumps(workflow)}), workflow)
        self.assertEqual(metadata._find_workflow({'other': json.dumps(workflow).encode()}), workflow)
        self.assertIsNone(metadata._find_workflow({'workflow': 'invalid'}))
        self.assertEqual(metadata._find_prompt({'Prompt': '{"1":{}}'}), {'1': {}})


class LoRAFallbackTests(unittest.TestCase):
    def setUp(self):
        self.comfy = types.ModuleType('comfy')
        self.utils = types.ModuleType('comfy.utils')
        self.sd = types.ModuleType('comfy.sd')
        self.comfy.utils = self.utils
        self.comfy.sd = self.sd
        self.builtin = types.ModuleType('nodes')
        self.log = Mock()
        self.modules = patch.dict(sys.modules, {
            'comfy': self.comfy, 'comfy.utils': self.utils,
            'comfy.sd': self.sd, 'nodes': self.builtin,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.lora = load_source('lora_helpers', 'hybs_lora_common.py')

    def apply(self, clip='clip', sc=1.0):
        return self.lora.apply_lora('model', clip, '/lora.safetensors', 'lora.safetensors', 0.5, sc, log=self.log)

    def test_sd_loader_is_preferred(self):
        self.sd.load_lora = Mock(return_value=('new-model', 'new-clip'))
        self.assertEqual(self.apply(), ('new-model', 'new-clip', True))

    def test_builtin_loader_is_used_after_sd_failure(self):
        self.sd.load_lora = Mock(side_effect=RuntimeError('unsupported'))
        loader = Mock()
        loader.load_lora.return_value = ('builtin-model', 'builtin-clip')
        self.builtin.LoraLoader = Mock(return_value=loader)
        self.assertEqual(self.apply(), ('builtin-model', 'builtin-clip', True))
        self.log.assert_called()

    def test_low_level_success(self):
        self.utils.load_torch_file = Mock(return_value={})
        self.utils.apply_lora = Mock(return_value='low-model')
        self.utils.apply_lora_to_clip = Mock(return_value='low-clip')
        self.assertEqual(self.apply(), ('low-model', 'low-clip', True))
        self.utils.load_torch_file.assert_called_once_with('/lora.safetensors', safe_load=True)

    def test_failure_does_not_return_a_partially_replaced_model(self):
        self.utils.load_torch_file = Mock(return_value={})
        self.utils.apply_lora = Mock(return_value='partial-model')
        self.utils.apply_lora_to_clip = Mock(side_effect=RuntimeError('failed'))
        self.assertEqual(self.apply(), ('model', 'clip', False))

    def test_none_clip_and_zero_clip_strength(self):
        self.utils.load_torch_file = Mock(return_value={})
        self.utils.apply_lora = Mock(return_value='new-model')
        self.utils.apply_lora_to_clip = Mock()
        self.assertEqual(self.apply(clip=None), ('new-model', None, True))
        self.assertEqual(self.apply(sc=0), ('new-model', 'clip', True))
        self.utils.apply_lora_to_clip.assert_not_called()

    def test_all_loaders_unavailable_preserves_inputs(self):
        self.assertEqual(self.apply(), ('model', 'clip', False))

    def test_token_format(self):
        self.assertEqual(self.lora.lora_token('folder/example.safetensors', 0.5, 1.0), '<lora:example:0.5:1.0>')


class NodeSelectionTests(unittest.TestCase):
    def setUp(self):
        package = types.ModuleType('hybs_test_package')
        package.__path__ = [str(ROOT)]
        api = types.ModuleType('hybs_test_package.hybs_comfy_api')
        api.io = types.SimpleNamespace(ComfyNode=object, Schema=object, NodeOutput=lambda *values: values)
        api.resolve_type = lambda name: object()
        lora = types.ModuleType('hybs_test_package.hybs_lora_common')
        lora.apply_lora = Mock(return_value=('new-model', 'new-clip', True))
        lora.lora_token = Mock(return_value='applied-token')
        self.lora = lora
        paths = types.ModuleType('folder_paths')
        paths.get_filename_list = lambda kind: ['a', 'b']
        self.modules = patch.dict(sys.modules, {
            package.__name__: package, api.__name__: api, lora.__name__: lora, 'folder_paths': paths,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def node(self, module, name):
        loaded = load_source('hybs_test_package.nodes.' + module, 'nodes/' + module + '.py')
        return getattr(loaded, name)

    def test_integer_nonfinite_values_are_ignored(self):
        node = self.node('hybs_int_list', 'HYBS_IntList')
        self.assertEqual(node._parse_selection('[1, 2.9, "3", Infinity, -Infinity, NaN, "bad"]'), [1, 2, 3])
        self.assertEqual(node.execute(selection='[0,-3]'), ([0, -3], 2))
        with self.assertRaises(ValueError):
            node.execute(selection='[Infinity]')

    def test_double_nonfinite_values_are_ignored(self):
        node = self.node('hybs_double_list', 'HYBS_DoubleList')
        self.assertEqual(node._parse_selection('[0, 1.5, "2", Infinity, NaN, "bad"]'), [0.0, 1.5, 2.0])
        self.assertIsNot(node.validate_inputs(selection='[NaN]'), True)

    def test_model_list_keeps_duplicate_order_and_checks_unknown_names(self):
        node = self.node('hybs_diffusion_model_list', 'HYBS_DiffusionModelList')
        self.assertEqual(node.execute(selection='["b","a","b"]'), (['b', 'a', 'b'], 3))
        self.assertIs(node.validate_inputs(selection='["a"]'), True)
        self.assertIsInstance(node.validate_inputs(selection='["unknown"]'), str)

    def test_lora_none_is_only_allowed_in_first_position(self):
        node = self.node('hybs_lora_list', 'HYBS_LoRAList')
        self.assertEqual(node.execute(selection='["NONE","a"]'), ([None, 'a'], 2))
        self.assertEqual(node._parse_selection({'selected': [{'name': ' b '}, None]}), ['b', None])
        with self.assertRaises(ValueError):
            node.execute(selection='["a",null]')

    def test_malformed_toml_entries_pass_through_instead_of_crashing(self):
        import tempfile
        node = self.node('hybs_conditional_lora_loader', 'HYBS_ConditionalLoRALoader')
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'invalid.toml').write_text('lora = [1]', encoding='utf-8')
            with patch.object(node, 'CONFIG_DIR', directory):
                self.assertEqual(node.execute('model', 'clip', 'prompt', 'invalid.toml'), ('model', 'clip', ''))
        self.lora.apply_lora.assert_not_called()

    def test_invalid_strength_does_not_prevent_later_lora_entries(self):
        node = self.node('hybs_conditional_lora_loader', 'HYBS_ConditionalLoRALoader')
        entries = [
            {'trigger': 'prompt', 'name': 'a', 'strength_model': 'invalid'},
            {'trigger': 'prompt', 'name': 'b'},
        ]
        with patch.object(node, '_load_toml', return_value=entries), patch.object(sys.modules['folder_paths'], 'get_full_path', return_value='/b.safetensors', create=True):
            self.assertEqual(node.execute('model', 'clip', 'prompt', 'test.toml'), ('new-model', 'new-clip', 'applied-token'))
        self.lora.apply_lora.assert_called_once()
        self.assertFalse(node._match('prompt', 123))



class WebImportTests(unittest.TestCase):
    def test_all_browser_imports_match_the_exported_web_directory(self):
        import ast
        import re
        from urllib.parse import urljoin
        tree = ast.parse((ROOT / '__init__.py').read_text(encoding='utf-8'))
        web = next(ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'WEB_DIRECTORY' for t in n.targets))
        web_root = ROOT / web
        files = list(web_root.rglob('*.js'))
        self.assertTrue(files)
        for source in files:
            relative = source.relative_to(web_root).as_posix()
            base = 'https://comfy.test/extensions/package/' + relative
            for specifier in re.findall(r'from\s+["\']([^"\']+)["\']', source.read_text(encoding='utf-8-sig')):
                with self.subTest(source=relative, specifier=specifier):
                    resolved = urljoin(base, specifier)
                    if '/scripts/' in resolved:
                        self.assertEqual(resolved, 'https://comfy.test/scripts/app.js')
                    else:
                        prefix = 'https://comfy.test/extensions/package/'
                        self.assertTrue(resolved.startswith(prefix))
                        self.assertTrue((web_root / resolved[len(prefix):]).is_file())


if __name__ == '__main__':
    unittest.main()
