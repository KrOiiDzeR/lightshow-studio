"""A relay selected as a lamp must only receive standard switch actions."""
from datetime import timedelta
from types import SimpleNamespace as NS
from unittest import TestCase
from inline_async import immediate_tests
import test_areas
from test_settings import fixture, defaults, check_settings


@immediate_tests
class SwitchLightTest(TestCase):
    def setUp(self):
        test_areas.AreaRunnersTest.setUp(self)
        self.runner=self.hub.areas['wall']
        self.fixture=fixture('switch.demo_lamp',transport='homeassistant')
        self.runner.settings['fixtures']=[self.fixture]
        self.states['switch.demo_lamp']=NS(state='on',attributes={'friendly_name':'Relay lamp'})
        self.commands=[]
        async def call(domain,action,data,**kwargs):
            self.commands.append((domain,action,dict(data)))
            self.states[data['entity_id']].state='on' if action=='turn_on' else 'off'
        self.hass.services.async_call=call

    async def test_relay_receives_no_color_brightness_effect_or_transition(self):
        self.runner.settings['options']['transition']=10
        for mode in ['red','warm','candle','colorloop','off']:
            await self.runner._apply(self.fixture,{'mode':mode,'brightness':60,'speed':80,'color':'#112233'})
            self.assertEqual(self.commands[-1],('switch','turn_off' if mode=='off' else 'turn_on',{'entity_id':'switch.demo_lamp'}))
        await self.runner._apply(self.fixture,{'mode':'red','brightness':0,'speed':80,'color':'#112233'})
        self.assertEqual(self.commands[-1][1],'turn_off')

    async def test_show_stop_restores_an_originally_on_and_off_relay(self):
        for initial in ['on','off']:
            self.states['switch.demo_lamp'].state=initial
            await self.runner.start('halloween','castle')
            self.assertEqual(self.states['switch.demo_lamp'].state,'on')
            await self.runner.stop()
            self.assertEqual(self.states['switch.demo_lamp'].state,initial)

    async def test_explicit_blink_uses_slow_switch_states_and_stops_cleanly(self):
        cue={'mode':'blink','brightness':70,'speed':100,'color':'#112233'}
        await self.runner._apply(self.fixture,cue)
        self.now+=timedelta(seconds=4)
        await self.runner.effect_tick()
        self.assertEqual(self.commands[-1][1],'turn_on')
        self.now+=timedelta(seconds=5)
        await self.runner.effect_tick()
        self.assertEqual(self.commands[-1][1],'turn_off')
        await self.runner._restore('switch.demo_lamp',{'state':'on'})
        self.assertFalse(self.runner.ha_effects)
        self.assertEqual(self.commands[-1][1],'turn_on')

    def test_only_light_and_switch_entities_are_allowed_and_defaults_play(self):
        data=defaults();data['fixtures']=[self.fixture]
        self.assertEqual(check_settings(data)['fixtures'][0]['role'],'upper')
        data['fixtures'][0]['entity_id']='cover.demo'
        with self.assertRaises(ValueError):check_settings(data)
