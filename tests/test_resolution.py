"""Resolution configuration and selection behavior, without a ComfyUI install."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load_source('resolution_config', ROOT / 'hybs_resolution_common.py')


class ResolutionTests(unittest.TestCase):
    def test_legacy_files_remain_supported(self):
        pairs = [[896, 1152], [1024, 1024], [896, 1152]]
        self.assertEqual(common._validate_pairs(pairs), [tuple(pair) for pair in pairs])

    def test_headings_preserve_order_and_duplicate_pairs(self):
        data = ['1024 equivalent', [896, 1152], 'other', [896, 1152], [1280, 1280]]
        self.assertEqual(common._validate_entries(data), ['1024 equivalent', (896, 1152), 'other', (896, 1152), (1280, 1280)])
        self.assertEqual(common._validate_pairs(data), [(896, 1152), (896, 1152), (1280, 1280)])

    def test_missing_file_uses_defaults_without_sharing_mutable_list(self):
        with patch.object(common, 'resolution_config_path', return_value='this-file-does-not-exist.json'):
            entries = common.load_resolution_entries()
            self.assertEqual(entries, common.DEFAULT_COMBOS)
            entries.clear()
            self.assertTrue(common.DEFAULT_COMBOS)

    def test_invalid_entries_and_header_only_files_are_rejected(self):
        for data in [[], {}, ['heading'], ['', [1, 2]], [None], [[0, 1024]], [[True, 1024]], [[1.5, 2]], [[1, 2, 3]]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                common._validate_entries(data)

    def test_json_loading_and_random_selector_ignore_only_headings(self):
        pairs = [[896, 1152], [1152, 896], [1024, 1024], [896, 1152]]
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory, 'resolutions.json')
            with patch.object(common, 'resolution_config_path', return_value=str(config)):
                config.write_text(json.dumps(pairs), encoding='utf-8')
                original = common.load_resolution_combos()
                config.write_text(json.dumps(['first', *pairs[:2], 'next', *pairs[2:]]), encoding='utf-8')
                self.assertEqual(common.load_resolution_combos(), original)
                random_node = self.node('hybs_random_resolution_selector', 'HYBS_RandomResolutionSelector')
                for seed in range(40):
                    self.assertEqual(random_node.execute(seed), original[seed % len(original)])

    def node(self, filename, class_name):
        package = types.ModuleType('resolution_test_package')
        package.__path__ = [str(ROOT)]
        api = types.ModuleType(package.__name__ + '.hybs_comfy_api')
        make_input = lambda name, **kwargs: dict(id=name, **kwargs)
        make_output = lambda **kwargs: kwargs
        api.io = types.SimpleNamespace(
            ComfyNode=object, NodeOutput=lambda *args: args, Schema=lambda **kwargs: kwargs,
            Combo=types.SimpleNamespace(Input=make_input),
            Int=types.SimpleNamespace(Input=make_input, Output=make_output),
        )
        modules = {package.__name__: package, api.__name__: api, package.__name__ + '.hybs_resolution_common': common}
        with patch.dict(sys.modules, modules):
            loaded = load_source(package.__name__ + '.nodes.' + filename, ROOT / 'nodes' / (filename + '.py'))
        return getattr(loaded, class_name)

    def test_schema_exposes_headings_only_as_display_metadata(self):
        node = self.node('hybs_resolution_selector', 'HYBS_ResolutionSelector')
        with patch.dict(node.define_schema.__func__.__globals__, load_resolution_entries=lambda: ['header', (896, 1152), 'next', (1280, 1280)]):
            schema = node.define_schema()
        resolution = schema['inputs'][0]
        self.assertEqual(resolution['options'], ['896x1152', '1280x1280'])
        self.assertEqual(resolution['extra_dict']['hybs_resolution_entries'], ['header', [896, 1152], 'next', [1280, 1280]])
        self.assertEqual(node.execute('1280x1280'), (1280, 1280))

    def test_sample_contains_five_groups_and_twenty_five_pairs(self):
        data = json.loads((ROOT / 'config/resolution_combos.json.example').read_text(encoding='utf-8'))
        entries = common._validate_entries(data)
        self.assertEqual(sum(isinstance(entry, str) for entry in entries), 5)
        self.assertEqual(len(common._validate_pairs(data)), 25)


if __name__ == '__main__':
    unittest.main()
