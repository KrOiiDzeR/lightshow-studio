"""Production area runners: simultaneous playback, isolated restore and migration."""
import ast
import asyncio
import copy
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from inline_async import immediate_tests, finish
from test_settings import defaults, check_settings, fixture, migrate_v1
from lightshow_studio.areas import area_configuration
from lightshow_studio.shuffle import shuffle_candidates


def settings(entity, color):
    data=defaults()
    data['fixtures']=[fixture(entity,friendly_name='generic-light',role='other')]
    data['packs'][0]['scenes'][0]['tracks']['other']['mode']=color
    return data


def configuration():
    return {'schema':3,'areas':[
        {'id':'wall','name':'Außenwand','icon':'🏠','settings':settings('light.wall','red')},
        {'id':'garden','name':'Garten','icon':'🌿','settings':settings('light.garden','blue')}]}


@immediate_tests
class AreaRunnersTest(TestCase):
    def setUp(self):
        self.saved=configuration()
        self.writes=[]
        self.calls=[]
        self.now=datetime(2026,10,19,19)
        outer=self

        class Store:
            def __init__(self,hass,version,key):self.key=key
            async def async_load(self):return copy.deepcopy(outer.saved) if self.key=='lightshow_studio' else None
            async def async_save(self,data):outer.writes.append(copy.deepcopy(data));outer.saved=copy.deepcopy(data)

        self.states={eid:NS(state='off',attributes={'supported_color_modes':['rgb'],'effect_list':[]}) for eid in ['light.wall','light.garden']}

        async def call(domain,action,data,**kwargs):
            self.calls.append((action,copy.deepcopy(data)))
            self.states[data['entity_id']].state='off' if action=='turn_off' else 'on'

        self.hass=NS(states=NS(get=self.states.get),services=NS(async_call=call))
        path=Path(__file__).resolve().parents[1]/'custom_components/lightshow_studio/__init__.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in {'Studio','StudioHub','mode_rgb'}]
        rgb=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RGB' for t in n.targets))
        ns={'__package__':'lightshow_studio','HomeAssistant':object,'Any':object,'Store':Store,'DOMAIN':'lightshow_studio',
            'defaults':defaults,'check_settings':check_settings,'migrate_v1':migrate_v1,
            'asyncio':asyncio,'dt_util':NS(now=lambda:self.now),'callback':lambda f:f,
            '_LOGGER':logging.getLogger(__name__),'DYMERAS':set(),'EFFECTS':{'candle'},'json':json,
            'scheduled_target':__import__('lightshow_studio.planning',fromlist=['scheduled_target']).scheduled_target,
            'shuffle_candidates':shuffle_candidates,'random':NS(choice=lambda choices:choices[0]),
            'timedelta':timedelta}
        exec(compile(ast.Module(body=[rgb,*nodes],type_ignores=[]),str(path),'exec'),ns)
        actual=ns['Studio']
        def runner(hass):
            obj=actual(hass);obj.suggestions=lambda:{};return obj
        ns['Studio']=runner
        self.hub=ns['StudioHub'](self.hass)
        finish(self.hub.load())

    async def test_two_shows_run_with_different_colors_and_isolated_stop(self):
        await self.hub.start('halloween','castle','wall')
        await self.hub.start('halloween','castle','garden')
        self.assertTrue(self.hub.areas['wall'].running)
        self.assertTrue(self.hub.areas['garden'].running)
        self.assertEqual(self.calls[0][1]['rgb_color'],[255,0,0])
        self.assertEqual(self.calls[1][1]['rgb_color'],[0,80,255])
        garden_runner=self.hub.areas['garden']
        garden_snapshot=copy.deepcopy(garden_runner.snapshots)
        await self.hub.stop(area_id='wall')
        self.assertEqual(self.states['light.wall'].state,'off')
        self.assertEqual(self.states['light.garden'].state,'on')
        self.assertTrue(garden_runner.running)
        self.assertEqual(garden_runner.snapshots,garden_snapshot)
        await self.hub.stop()
        self.assertTrue(all(s.state=='off' for s in self.states.values()))

    async def test_editing_idle_area_keeps_other_active_runner_and_snapshots(self):
        await self.hub.start('halloween','castle','garden')
        runner=self.hub.areas['garden'];snapshots=copy.deepcopy(runner.snapshots)
        changed=copy.deepcopy(self.hub.areas['wall'].settings)
        changed['packs'][0]['scenes'][0]['name']='Neue Wandshow'
        await self.hub.save(changed,'wall')
        self.assertIs(self.hub.areas['garden'],runner)
        self.assertTrue(runner.running)
        self.assertEqual(runner.snapshots,snapshots)
        self.assertEqual(self.states['light.garden'].state,'on')

    async def test_duplicate_lamp_and_invalid_area_rejected_without_write(self):
        changed=copy.deepcopy(self.hub.areas['wall'].settings)
        changed['fixtures']=[fixture('light.garden')]
        with self.assertRaises(ValueError):await self.hub.save(changed,'wall')
        with self.assertRaises(ValueError):await self.hub.start('halloween','castle','missing')
        self.assertEqual(self.writes,[])

    async def test_save_or_remove_running_area_rejected(self):
        await self.hub.start('halloween','castle','wall')
        with self.assertRaises(ValueError):await self.hub.save(self.hub.areas['wall'].settings,'wall')
        with self.assertRaises(ValueError):await self.hub.edit_areas('remove','wall')
        self.assertEqual(self.writes,[])

    async def test_area_creation_rename_remove_and_last_area_guard(self):
        key=await self.hub.edit_areas('add',name='Pool',icon='🏊')
        self.assertEqual(self.hub.areas[key].settings['fixtures'],[])
        self.assertFalse(self.hub.areas[key].settings['options']['shuffle'])
        await self.hub.edit_areas('rename',key,'Badewanne','🛁')
        self.assertEqual(self.hub.metadata[key]['name'],'Badewanne')
        await self.hub.edit_areas('remove',key)
        await self.hub.edit_areas('remove','wall')
        with self.assertRaises(ValueError):await self.hub.edit_areas('remove','garden')

    async def test_legacy_single_area_migrates_without_writing_on_load(self):
        old=settings('light.wall','red');old['packs'][0]['scenes'][0]['name']='Meine eigene Szene'
        self.saved=copy.deepcopy(old)
        await self.hub.load()
        self.assertEqual(list(self.hub.areas),['main'])
        self.assertEqual(self.hub.areas['main'].settings,old)
        self.assertEqual(self.writes,[])
        await self.hub.edit_areas('rename','main','Außenwand','🏠')
        self.assertEqual(self.saved['schema'],3)
        self.assertEqual(self.saved['areas'][0]['settings'],old)

    async def test_dashboard_settings_and_schedules_are_independent(self):
        await self.hub.operate({'options':{'shuffle':True}},'wall')
        self.assertTrue(self.hub.areas['wall'].settings['options']['shuffle'])
        self.assertFalse(self.hub.areas['garden'].settings['options']['shuffle'])
        for key in self.hub.areas:
            sch=self.hub.areas[key].settings['packs'][0]['schedule']
            sch.update(enabled=True,month=10,day=19,start='18:00',end='22:00')
        await self.hub.tick()
        self.assertTrue(all(area.running for area in self.hub.areas.values()))
        await self.hub.stop(area_id='wall')
        await self.hub.tick()
        self.assertFalse(self.hub.areas['wall'].running)
        self.assertTrue(self.hub.areas['garden'].running)

    async def test_export_restore_and_failed_storage_are_atomic(self):
        original=copy.deepcopy(self.hub.configuration())
        await self.hub.edit_areas('add',name='Pool')
        await self.hub.edit_areas('restore',configuration=original)
        self.assertEqual(self.hub.configuration(),original)
        async def fail(data):raise OSError('disk full')
        self.hub.store.async_save=fail
        with self.assertRaises(OSError):await self.hub.edit_areas('rename','wall','Changed','💡')
        self.assertEqual(self.hub.configuration(),original)

    async def test_summary_lists_both_states_and_scene_names(self):
        await self.hub.start('halloween','castle','wall')
        data=self.hub.data('garden')
        self.assertEqual(data['area_id'],'garden')
        self.assertEqual([a['running'] for a in data['areas']],[True,False])
        self.assertEqual(data['areas'][0]['scene'],'Gruselschloss')
        self.assertEqual(data['areas'][0]['lights'],1)

    async def test_program_positions_and_deadlines_survive_other_area_edit(self):
        for key,area in self.hub.areas.items():
            program=area.settings['packs'][0]['programs'][0]['id']
            await self.hub.start_program('halloween',program,key)
        garden=self.hub.areas['garden'];until=garden.program_until
        await self.hub.edit_areas('rename','wall','Außenwand neu','🏠')
        self.assertIs(self.hub.areas['garden'],garden)
        self.assertEqual(garden.program_until,until)
        self.now+=timedelta(seconds=61)
        await self.hub.tick()
        self.assertEqual([a.program_index for a in self.hub.areas.values()],[1,1])
        await self.hub.stop(area_id='wall')
        self.assertTrue(garden.active_program)
        self.assertEqual(garden.program_index,1)

    async def test_scheduler_failure_in_one_area_does_not_block_others(self):
        async def fail():raise RuntimeError('simulated failure')
        self.hub.areas['wall'].tick=fail
        row=self.hub.areas['garden'].settings['packs'][0]['schedule']
        row.update(enabled=True,month=10,day=19,start='18:00',end='22:00')
        with self.assertLogs(__name__,level='ERROR'):await self.hub.tick()
        self.assertTrue(self.hub.areas['garden'].running)

    async def test_full_restore_requires_all_areas_idle(self):
        original=copy.deepcopy(self.hub.configuration())
        await self.hub.start('halloween','castle','garden')
        with self.assertRaises(ValueError):
            await self.hub.edit_areas('restore',configuration=original)
        self.assertTrue(self.hub.areas['garden'].running)
        self.assertEqual(self.writes,[])

    async def test_shuffle_switches_to_selected_other_pack_without_touching_garden(self):
        wall=self.hub.areas['wall']
        wall.settings['shuffle_scenes']=[{'pack_id':'christmas','scene_id':'advent'}]
        wall.settings['options'].update(shuffle=True,shuffle_interval=60)
        await self.hub.start('halloween','castle','wall')
        await self.hub.start('halloween','castle','garden')
        self.now+=timedelta(seconds=61)
        await self.hub.tick()
        self.assertEqual((wall.active_pack,wall.active_scene),('christmas','advent'))
        self.assertEqual(self.hub.areas['garden'].active_pack,'halloween')
        self.assertEqual(wall.messages,[])
        self.assertEqual(self.states['light.garden'].state,'on')

    async def test_empty_shuffle_selection_holds_scene_and_programs_keep_order(self):
        wall=self.hub.areas['wall']
        wall.settings['shuffle_scenes']=[]
        wall.settings['options'].update(shuffle=True,shuffle_interval=60)
        await self.hub.start('halloween','castle','wall')
        self.now+=timedelta(seconds=61)
        await self.hub.tick()
        self.assertEqual(wall.active_scene,'castle')
        self.assertEqual(wall.last_shuffle,self.now)
        wall.settings['shuffle_scenes']=[{'pack_id':'christmas','scene_id':'advent'}]
        await self.hub.start_program('halloween','tour','wall')
        self.now+=timedelta(seconds=61)
        await self.hub.tick()
        self.assertEqual((wall.active_pack,wall.active_scene),('halloween','haunted'))


class AreaValidationTest(TestCase):
    def test_limits_ids_names_icons_and_ownership(self):
        for field,value in [('id','bad/id'),('name',''),('icon','')]:
            data=configuration();data['areas'][0][field]=value
            with self.assertRaises(ValueError):area_configuration(data)
        with self.assertRaises(ValueError):area_configuration({'schema':3,'areas':[]})
        data=configuration();data['areas']=[copy.deepcopy(data['areas'][0]) for _ in range(31)]
        with self.assertRaises(ValueError):area_configuration(data)
        data=configuration();data['areas'][1]['id']='wall'
        with self.assertRaises(ValueError):area_configuration(data)
