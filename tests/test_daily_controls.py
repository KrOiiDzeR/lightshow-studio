"""Use production runners for favorites, batches, timers, copy and shuffle rounds."""
from datetime import timedelta
from unittest import TestCase
import copy
import test_areas
from inline_async import immediate_tests
from test_settings import check_settings
from lightshow_studio.planning import operation_settings


@immediate_tests
class DailyControlsTest(TestCase):
    def setUp(self):
        test_areas.AreaRunnersTest.setUp(self)

    async def test_favorites_are_persisted_and_scoped_while_show_runs(self):
        await self.hub.start('halloween', 'castle', 'wall')
        runner = self.hub.areas['wall']
        snapshots = copy.deepcopy(runner.snapshots)
        await self.hub.control('favorite', 'wall', pack_id='halloween', scene_id='castle')
        self.assertEqual(self.saved['areas'][0]['settings']['favorites'], [{'pack_id':'halloween','scene_id':'castle'}])
        self.assertNotIn('favorites', self.hub.areas['garden'].settings)
        self.assertIs(self.hub.areas['wall'], runner)
        self.assertEqual(runner.snapshots, snapshots)
        await self.hub.control('favorite', 'wall', pack_id='halloween', scene_id='castle')
        self.assertEqual(runner.settings['favorites'], [])

    async def test_group_preflight_does_not_start_any_area_if_scene_missing(self):
        del self.hub.areas['garden'].settings['packs'][0]['scenes'][0]
        with self.assertRaises(ValueError):
            await self.hub.control('start_selected', area_ids=['wall','garden'], pack_id='halloween', scene_id='castle')
        self.assertEqual(self.calls, [])
        for keys in [[], ['wall','wall'], ['wall','absent']]:
            with self.assertRaises(ValueError):
                await self.hub.control('stop_selected', area_ids=keys)

    async def test_group_start_uses_own_tracks_and_stop_only_selected(self):
        result = await self.hub.control('start_selected', area_ids=['wall','garden'], pack_id='halloween', scene_id='castle')
        self.assertTrue(all(row['ok'] for row in result.values()))
        self.assertEqual([row[1]['rgb_color'] for row in self.calls], [[255,0,0],[0,80,255]])
        await self.hub.control('stop_selected', area_ids=['wall'])
        self.assertFalse(self.hub.areas['wall'].running)
        self.assertTrue(self.hub.areas['garden'].running)

    async def test_group_reports_partial_execution_failure_and_continues(self):
        async def fail(*args):
            raise RuntimeError('Demo error')
        self.hub.areas['wall'].start = fail
        result = await self.hub.control('start_selected', area_ids=['wall','garden'], pack_id='halloween', scene_id='castle')
        self.assertFalse(result['wall']['ok'])
        self.assertTrue(result['garden']['ok'])
        self.assertTrue(self.hub.areas['garden'].running)

    async def test_timer_expires_only_its_area_restores_and_prevents_schedule_restart(self):
        await self.hub.control('start_selected', area_ids=['wall','garden'], pack_id='halloween', scene_id='castle')
        await self.hub.control('timer', 'wall', minutes=30)
        end = self.hub.areas['wall'].stop_at
        # Scene changes preserve an already active timer.
        await self.hub.start('halloween', 'castle', 'wall')
        self.assertEqual(self.hub.areas['wall'].stop_at, end)
        self.now += timedelta(minutes=29)
        await self.hub.tick()
        self.assertTrue(self.hub.areas['wall'].running)
        self.now += timedelta(minutes=1)
        await self.hub.tick()
        self.assertFalse(self.hub.areas['wall'].running)
        self.assertEqual(self.states['light.wall'].state, 'off')
        self.assertTrue(self.hub.areas['garden'].running)
        self.assertIsNone(self.hub.areas['wall'].stop_at)
        self.assertEqual(self.hub.areas['wall'].manual_stop_date, self.now.date().isoformat())

    async def test_timer_validation_cancel_and_manual_stop(self):
        with self.assertRaises(ValueError):
            await self.hub.control('timer', 'wall', minutes=30)
        await self.hub.start('halloween','castle','wall')
        for minutes in [-1,721,True,1.5]:
            with self.assertRaises(ValueError):
                await self.hub.control('timer','wall',minutes=minutes)
        await self.hub.control('timer','wall',minutes=30)
        await self.hub.control('timer','wall',minutes=0)
        self.assertIsNone(self.hub.areas['wall'].stop_at)
        await self.hub.control('timer','wall',minutes=15)
        await self.hub.stop(area_id='wall')
        self.assertIsNone(self.hub.areas['wall'].stop_at)

    async def test_copy_is_deep_and_clears_lights_overrides_and_armed_schedules(self):
        source = self.hub.areas['wall'].settings
        source['packs'][0]['schedule']['enabled'] = True
        source['packs'][0]['scenes'][0]['overrides'] = [{'entity_id':'light.wall', **source['packs'][0]['scenes'][0]['tracks']['other']}]
        source['weekly'] = [{'id':'demo','enabled':True,'days':[0],'start':'18:00','end':'20:00','pack_id':'halloween','scene_id':'castle','program_id':''}]
        key = await self.hub.edit_areas('copy','wall',name='Kopie')
        clone = self.hub.areas[key].settings
        self.assertEqual(clone['fixtures'], [])
        self.assertFalse(clone['packs'][0]['schedule']['enabled'])
        self.assertEqual(clone['packs'][0]['scenes'][0]['overrides'], [])
        self.assertFalse(clone['weekly'][0]['enabled'])
        clone['packs'][0]['name'] = 'Changed'
        self.assertNotEqual(source['packs'][0]['name'], 'Changed')
        self.assertTrue(source['packs'][0]['schedule']['enabled'])

    async def test_shuffle_plays_entire_pool_before_repeating(self):
        runner = self.hub.areas['wall']
        scenes = runner.settings['packs'][0]['scenes'][:3]
        pool = [{'pack_id':'halloween','scene_id':sc['id']} for sc in scenes]
        runner.settings['shuffle_scenes'] = pool
        runner.settings['options'].update(shuffle=True, shuffle_no_repeat=True, shuffle_interval=60)
        await self.hub.start('halloween',scenes[0]['id'],'wall')
        played = [runner.active_scene]
        for _ in range(8):
            self.now += timedelta(seconds=60)
            await self.hub.tick()
            played.append(runner.active_scene)
        for start in [0,3,6]:
            self.assertEqual(len(set(played[start:start+3])),3)
        self.assertTrue(all(a!=b for a,b in zip(played,played[1:])))

    def test_options_and_unknown_favorites_are_validated(self):
        current = self.hub.areas['wall'].settings
        valid = operation_settings(current, {'options':{'transition':3,'shuffle_no_repeat':True}})
        self.assertEqual(valid['options']['transition'],3)
        for invalid in [{'transition':-1},{'transition':31},{'shuffle_no_repeat':'yes'}]:
            with self.assertRaises(ValueError):
                operation_settings(current,{'options':invalid})
        with self.assertRaises(ValueError):
            check_settings({**current,'favorites':[{'pack_id':'missing','scene_id':'missing'}]})
