"""Run production entry lifecycle with simulated HA registries and services."""
import ast
import asyncio
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import AsyncMock, Mock
from inline_async import immediate_tests, finish

PACKAGE = Path(__file__).resolve().parents[1] / 'custom_components/lightshow_studio'


@immediate_tests
class EntryLifecycleTest(TestCase):
    def setUp(self):
        self.studio=NS(load=AsyncMock(), stop=AsyncMock(), start=AsyncMock(), start_program=AsyncMock(),
                       preview_tasks={}, areas={}, got_devices=Mock(), tick=AsyncMock())
        self.unsubscribe=Mock()
        self.cancel=Mock()
        self.frontend=NS(add_extra_js_url=Mock(),remove_extra_js_url=Mock(),async_remove_panel=Mock())
        self.panel=NS(async_register_panel=AsyncMock())
        self.registry=NS(async_get_or_create=Mock())
        self.handlers={}
        self.entry=NS(data={'mqtt_mode':'manual','mqtt_base_topic':'House/Bridge'},options={},entry_id='example',
                      async_on_unload=Mock(),add_update_listener=Mock(return_value=lambda:None))
        self.hass=NS(data={},http=NS(async_register_static_paths=AsyncMock()),
                     config_entries=NS(flow=NS(async_init=AsyncMock()),async_reload=AsyncMock()),
                     bus=NS(async_listen_once=Mock(return_value=lambda:None)),
                     services=NS(async_register=lambda domain,name,handler,**kw:self.handlers.update({name:handler})),
                     async_create_task=finish)
        self.mqtt=NS(async_subscribe=AsyncMock(return_value=self.unsubscribe))
        self.namespace={'__file__':str(PACKAGE/'__init__.py'),'HomeAssistant':object,'ConfigEntry':object,
                        'ServiceCall':object,'datetime':object,'Path':Path,'DOMAIN':'lightshow_studio',
                        'CONFIG_PATH':'lightshow-studio-config','CONTROL_PATH':'lightshow-studio',
                        'MODULE_URL':'/lightshow_studio/lightshow-studio.js?v=dev','VERSION':'dev',
                        'StudioHub':lambda hass:self.studio,'mqtt':self.mqtt,'callback':lambda f:f,
                        'timedelta':timedelta,'async_track_time_interval':lambda *args:self.cancel,
                        'frontend':self.frontend,'panel_custom':self.panel,'dr':NS(async_get=lambda hass:self.registry),
                        'EVENT_HOMEASSISTANT_STOP':'stop','ConfigEntryNotReady':RuntimeError,
                        'StaticPathConfig':lambda *args:args,'websocket_api':NS(async_register_command=Mock()),
                        'vol':NS(Schema=lambda x:x,Required=lambda x:x,Optional=lambda x:x),'_LOGGER':Mock()}
        for name in ('ws_get','ws_save','ws_operate','ws_areas','ws_connection','ws_start','ws_program','ws_stop','ws_preview','ws_control'):
            self.namespace[name]=Mock()
        tree=ast.parse((PACKAGE/'__init__.py').read_text(encoding='utf-8'))
        nodes=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name in
               {'async_setup','async_setup_entry','async_unload_entry','_async_options_updated'}]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(PACKAGE/'__init__.py'),'exec'),self.namespace)

    async def test_ui_entry_registers_configuration_and_control_without_yaml(self):
        await self.namespace['async_setup'](self.hass,{})
        self.hass.config_entries.flow.async_init.assert_not_awaited()
        self.assertTrue(await self.namespace['async_setup_entry'](self.hass,self.entry))
        self.mqtt.async_subscribe.assert_awaited_once_with(self.hass,'House/Bridge/bridge/devices',self.studio.got_devices)
        panels=[call.kwargs for call in self.panel.async_register_panel.await_args_list]
        self.assertEqual(panels[0]['config_panel_domain'],'lightshow_studio')
        self.assertTrue(panels[0]['require_admin'])
        self.assertNotIn('sidebar_title',panels[0])
        self.assertEqual(panels[1]['config'],{'mode':'operation'})
        self.frontend.add_extra_js_url.assert_called_once()

    async def test_services_resolve_reloaded_instance(self):
        await self.namespace['async_setup'](self.hass,{})
        await self.namespace['async_setup_entry'](self.hass,self.entry)
        new=NS(start=AsyncMock(),start_program=AsyncMock(),stop=AsyncMock())
        self.hass.data['lightshow_studio']=new
        call=NS(data={'pack_id':'demo','scene_id':'scene','program_id':'tour'})
        for name in ('start','start_program','stop'):await self.handlers[name](call)
        new.start.assert_awaited_once_with('demo','scene')
        new.start_program.assert_awaited_once_with('demo','tour')
        new.stop.assert_awaited_once()
        self.studio.start.assert_not_awaited()

    async def test_disabled_mqtt_does_not_subscribe_and_unload_restores_lights(self):
        self.entry.options={'mqtt_mode':'disabled','mqtt_base_topic':''}
        await self.namespace['async_setup_entry'](self.hass,self.entry)
        self.mqtt.async_subscribe.assert_not_awaited()
        self.assertTrue(await self.namespace['async_unload_entry'](self.hass,self.entry))
        self.studio.stop.assert_awaited_once_with(manual=False)
        self.assertNotIn('lightshow_studio',self.hass.data)
        self.assertEqual(self.frontend.async_remove_panel.call_count,2)
        # HA invokes registered unload callbacks after a successful unload.
        for call in self.entry.async_on_unload.call_args_list:call.args[0]()
        for call in self.entry.async_on_unload.call_args_list:call.args[0]()
        self.assertEqual(self.cancel.call_count, 2)

    async def test_auto_mode_subscribes_to_case_preserving_discovery(self):
        self.entry.data={'mqtt_mode':'auto','mqtt_base_topic':''}
        await self.namespace['async_setup_entry'](self.hass,self.entry)
        self.assertEqual(self.mqtt.async_subscribe.await_args.args[1],'+/bridge/devices')

    async def test_mqtt_failure_retries_without_starting_scheduler_or_panel(self):
        self.mqtt.async_subscribe.side_effect=RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            await self.namespace['async_setup_entry'](self.hass,self.entry)
        self.assertNotIn('lightshow_studio',self.hass.data)
        self.panel.async_register_panel.assert_not_awaited()

    async def test_yaml_import_and_options_reload(self):
        await self.namespace['async_setup'](self.hass,{'lightshow_studio':{'mqtt_base_topic':'Legacy'}})
        self.hass.config_entries.flow.async_init.assert_awaited_once_with(
            'lightshow_studio',context={'source':'import'},data={'mqtt_base_topic':'Legacy'})
        await self.namespace['_async_options_updated'](self.hass,self.entry)
        self.hass.config_entries.async_reload.assert_awaited_once_with('example')
