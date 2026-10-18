"""Exercise the unchanged load path with fake storage, without importing HA."""
import ast
import copy
from pathlib import Path
import unittest
from test_settings import defaults, fixture

source = Path(__file__).resolve().parents[1] / 'custom_components/lightshow_studio/__init__.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
studio = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Studio')
load = next(node for node in studio.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'load')


class StorageCompatibility(unittest.TestCase):
    def test_existing_v2_data_loaded_without_overwrite_or_legacy_import(self):
        from lightshow_studio.settings import check_settings
        saved = defaults()
        saved['fixtures'] = [fixture('light.my_saved_lamp', role='entrance', friendly_name='demo-device')]
        saved['packs'][0]['scenes'][0]['name'] = 'My saved scene'
        original = copy.deepcopy(saved)

        class Store:
            async def async_load(self):
                return saved

            async def async_save(self, data):
                raise AssertionError('Existing settings must not be overwritten')

        def unexpected_legacy_store(*args):
            raise AssertionError('Existing v2 settings must bypass legacy migration')

        namespace = {'Store': unexpected_legacy_store, 'check_settings': check_settings}
        module = ast.Module(body=[load], type_ignores=[])
        exec(compile(module, str(source), 'exec'), namespace)
        obj = type('FakeStudio', (), {})()
        obj.store = Store()
        # Fake storage completes immediately; no HA event loop is involved.
        coroutine = namespace['load'](obj)
        with self.assertRaises(StopIteration):
            coroutine.send(None)
        self.assertEqual(obj.settings, original)
        self.assertEqual(saved, original)
        self.assertIsNot(obj.settings, saved)
