from pathlib import Path
import importlib.util
import json
import sys
import types
import unittest

PKG = Path(__file__).resolve().parents[1] / 'custom_components' / 'lightshow_studio'
pkg = types.ModuleType('lightshow_studio')
pkg.__path__ = [str(PKG)]
sys.modules['lightshow_studio'] = pkg
for name in ('catalog', 'settings'):
    spec = importlib.util.spec_from_file_location('lightshow_studio.'+name, PKG/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from lightshow_studio.settings import (defaults, check_settings, migrate_v1, validate_pack, fixture)


class SettingsTest(unittest.TestCase):
    def test_builtin_catalog(self):
        v = check_settings(defaults())
        self.assertEqual(v['schema'], 2)
        self.assertEqual(len(v['packs']), 4)
        self.assertEqual(v['fixtures'], [])

    def test_legacy_migration(self):
        old = {'schedule': {'enabled':True,'start':'18:00','end':'23:00','scene_id':'castle'},
               'scenes':[{'id':'castle','name':'Gruselschloss','emoji':'🏰','lights':[
                   {'entity_id':'light.demo_top','mode':'candle', 'brightness':70,
                    'speed':50,'friendly_name':'dymera/garage','endpoint':'top'},
                   {'entity_id':'light.demo_entrance','mode':'candle','brightness':70,
                    'speed':50,'friendly_name':'','endpoint':'auto'}]}],
               'wind_enabled':True, 'shuffle_enabled':False,'shuffle_interval':180}
        new = migrate_v1(old)
        self.assertEqual(new['packs'][0]['scenes'][0]['overrides'][0]['mode'],'candle')
        self.assertEqual(new['fixtures'][0]['friendly_name'],'dymera/garage')
        self.assertTrue(new['packs'][0]['schedule']['enabled'])
        self.assertTrue(new['options']['wind'])

    def test_event_pack_import(self):
        p=json.loads((Path(__file__).parent.parent/'show_packs'/'Sommerparty.json').read_text(encoding='utf8'))
        validate_pack(p)
        data=defaults();data['packs'].append(p)
        check_settings(data)

    def test_reject_duplicate_fixtures(self):
        x=defaults();x['fixtures']=[fixture('light.demo'), fixture('light.demo')]
        with self.assertRaises(ValueError): check_settings(x)

    def test_reject_unknown_mode(self):
        x=defaults();x['packs'][0]['scenes'][0]['tracks']['upper']['mode']='fire_the_house'
        with self.assertRaises(ValueError):check_settings(x)

    def test_reject_unknown_override(self):
        x=defaults();x['packs'][0]['scenes'][0]['overrides']=[{'entity_id':'light.not_in_inventory','mode':'off','brightness':50,'speed':50,'color':'#112233'}]
        with self.assertRaises(ValueError):check_settings(x)

    def test_overlapping_schedules_rejected(self):
        x=defaults(); x['packs'][0]['schedule']['enabled']=True
        x['packs'][1]['schedule'].update({'enabled':True,'month':10,'day':31,'start':'20:00','end':'22:00'})
        with self.assertRaises(ValueError):check_settings(x)

    def test_non_overlapping_schedules_work(self):
        x=defaults(); x['packs'][0]['schedule']['enabled']=True
        x['packs'][1]['schedule'].update({'enabled':True,'month':10,'day':31,'start':'15:00','end':'17:00'})
        check_settings(x)

    def test_program_steps_and_schedule(self):
        x=defaults()
        x['packs'][1]['schedule']['program_id']='tour'
        x['packs'][1]['schedule']['enabled']=True
        self.assertEqual(check_settings(x)['packs'][1]['programs'][0]['steps'][0]['scene_id'],'advent')

    def test_invalid_program_step_rejected(self):
        x=defaults()
        x['packs'][0]['programs'][0]['steps'][0]['scene_id']='deleted'
        with self.assertRaises(ValueError):check_settings(x)

    def test_reject_script_like_id(self):
        x=defaults();x['packs'][0]['id']='../../../foo'
        with self.assertRaises(ValueError):check_settings(x)

    def test_reject_bad_color(self):
        x=defaults();x['packs'][0]['scenes'][0]['tracks']['upper']['color']='#GHIJKL'
        with self.assertRaises(ValueError):check_settings(x)

    def test_support_extra_light(self):
        x=defaults();x['fixtures'].append(fixture('light.gartenlampe',role='other'))
        check_settings(x)

if __name__=='__main__': unittest.main()
