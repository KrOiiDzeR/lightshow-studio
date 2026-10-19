"""Real async tasks: preview cancellation must not leave an HA effect behind."""
import asyncio
from datetime import timedelta
from types import SimpleNamespace as NS
from unittest import IsolatedAsyncioTestCase
import test_areas
from lightshow_studio.settings import EFFECTS


class EffectPreviewTest(IsolatedAsyncioTestCase):
    def setUp(self):
        test_areas.AreaRunnersTest.setUp(self)
        self.runner = self.hub.areas['wall']
        self.runner._apply.__globals__['EFFECTS'] = EFFECTS
        self.gate = asyncio.Event()
        self.runner._apply.__globals__['asyncio'] = NS(
            Lock=asyncio.Lock, Task=asyncio.Task, CancelledError=asyncio.CancelledError,
            sleep=lambda _: self.gate.wait(), gather=asyncio.gather)
        self.hass.async_create_task = lambda coro, name: asyncio.create_task(coro, name=name)
        self.runner.settings['packs'][0]['scenes'][0]['tracks']['other']['mode'] = 'candle'

    async def test_preview_expiry_stops_animation_and_restores(self):
        await self.runner.preview('halloween', 'castle', 'light.wall')
        task = self.runner.preview_tasks['light.wall']
        self.assertTrue(self.runner.ha_effects)
        self.now += timedelta(seconds=3)
        await self.runner.effect_tick()
        self.gate.set()
        await asyncio.wait_for(task, 1)
        self.assertEqual(self.states['light.wall'].state, 'off')
        self.assertFalse(self.runner.ha_effects)
        self.assertFalse(self.runner.preview_states)

    async def test_immediate_stop_restores_even_if_preview_task_never_started(self):
        await self.runner.preview('halloween', 'castle', 'light.wall')
        await self.runner.stop()
        self.assertEqual(self.states['light.wall'].state, 'off')
        self.assertFalse(self.runner.ha_effects)
        self.assertFalse(self.runner.preview_tasks)
        self.assertFalse(self.runner.preview_states)

    async def test_start_cancels_preview_without_deadlock(self):
        await self.runner.preview('halloween', 'castle', 'light.wall')
        await asyncio.sleep(0)
        await asyncio.wait_for(self.runner.start('halloween', 'castle'), 1)
        self.assertTrue(self.runner.running)
        self.assertTrue(self.runner.ha_effects)
        self.assertFalse(self.runner.preview_tasks)
        await self.runner.stop()
        self.assertEqual(self.states['light.wall'].state, 'off')
