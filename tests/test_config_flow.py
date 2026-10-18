"""Exercise production flow transitions against a minimal HA flow host."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from inline_async import immediate_tests
from test_discovery import discovery


class Abort(Exception):
    pass


class FlowHost:
    def __init_subclass__(cls, **kwargs):
        pass

    async def async_set_unique_id(self,value):
        self.unique_id=value

    def _abort_if_unique_id_configured(self):
        if getattr(self,'existing',False):raise Abort('already_configured')

    def async_create_entry(self, **kwargs):
        return {'type':'create_entry',**kwargs}

    def async_show_form(self, **kwargs):
        return {'type':'form',**kwargs}


@immediate_tests
class ConfigFlowTest(TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'custom_components/lightshow_studio/config_flow.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='connection_schema']
        self.ns={'config_entries':NS(ConfigFlow=FlowHost,OptionsFlow=FlowHost),'DOMAIN':'lightshow_studio',
                 'callback':lambda f:f,'base_topic':discovery.base_topic,
                 'connection_schema':lambda *args:args}
        exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),self.ns)
        self.hass=NS(data={},config_entries=NS(async_entries=lambda domain:['mqtt'] if domain=='mqtt' else []))
        self.flow=self.ns['StudioConfigFlow']();self.flow.hass=self.hass

    async def test_first_setup_and_duplicate_guard(self):
        result=await self.flow.async_step_user()
        self.assertEqual(result['type'],'form')
        self.assertEqual(result['step_id'],'user')
        result=await self.flow.async_step_user({'mqtt_mode':'manual','mqtt_base_topic':'Home/Zigbee/'})
        self.assertEqual(result['data'],{'mqtt_mode':'manual','mqtt_base_topic':'Home/Zigbee'})
        self.flow.existing=True
        with self.assertRaises(Abort):await self.flow.async_step_user()

    async def test_invalid_prefix_and_missing_mqtt_show_errors(self):
        result=await self.flow.async_step_user({'mqtt_mode':'manual','mqtt_base_topic':'home/#'})
        self.assertEqual(result['errors'],{'base':'invalid_topic'})
        self.hass.config_entries.async_entries=lambda domain:[]
        result=await self.flow.async_step_user({'mqtt_mode':'auto'})
        self.assertEqual(result['errors'],{'base':'mqtt_not_configured'})
        result=await self.flow.async_step_user({'mqtt_mode':'disabled'})
        self.assertEqual(result['type'],'create_entry')

    async def test_legacy_import_retains_prefix_and_guards_duplicates(self):
        result=await self.flow.async_step_import({'mqtt_base_topic':'Zigbee2mqtt'})
        self.assertEqual(result['data']['mqtt_base_topic'],'Zigbee2mqtt')
        self.flow.existing=True
        with self.assertRaises(Abort):await self.flow.async_step_import({})

    async def test_options_use_entry_and_refuse_change_during_show(self):
        flow=self.ns['StudioOptionsFlow']();flow.hass=self.hass
        flow.config_entry=NS(data={'mqtt_mode':'auto','mqtt_base_topic':''},options={})
        self.hass.data['lightshow_studio']=NS(running=True,preview_tasks={})
        result=await flow.async_step_init({'mqtt_mode':'disabled'})
        self.assertEqual(result['errors'],{'base':'show_running'})
        self.hass.data['lightshow_studio'].running=False
        result=await flow.async_step_init({'mqtt_mode':'disabled'})
        self.assertEqual(result['type'],'create_entry')
        self.assertEqual(result['data']['mqtt_mode'],'disabled')
