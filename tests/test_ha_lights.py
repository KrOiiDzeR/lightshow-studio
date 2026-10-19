"""Exercise production runners with HA lights and explicit transport choices."""
from unittest import TestCase
from inline_async import immediate_tests
import test_areas
from test_settings import fixture, defaults, check_settings
from datetime import timedelta
from lightshow_studio.settings import EFFECTS


@immediate_tests
class HALightsTest(TestCase):
    def setUp(self):
        test_areas.AreaRunnersTest.setUp(self)
        self.runner = self.hub.areas['wall']
        self.runner._apply.__globals__['EFFECTS'] = EFFECTS
        self.runner._dymera.__globals__['DYMERAS'] = {'046677585235'}
        self.fixture = fixture('light.wall', transport='homeassistant')
        self.cue = {'mode': 'red', 'brightness': 60, 'speed': 50, 'color': '#124578'}
        self.state = self.states['light.wall']

    async def test_rgb_rgbw_rgbww_hs_and_xy_use_ha_without_mqtt(self):
        for mode in ['rgb', 'rgbw', 'rgbww', 'hs', 'xy']:
            with self.subTest(mode=mode):
                self.state.attributes = {'supported_color_modes': [mode]}
                await self.runner._apply(self.fixture, self.cue)
                self.assertEqual(self.calls[-1], ('turn_on', {'entity_id': 'light.wall', 'brightness': 152, 'rgb_color': [255, 0, 0]}))

    async def test_explicit_ha_never_uses_discovered_native_device(self):
        self.runner.devices = [{'friendly_name': 'known', 'model': '046677585235'}]
        self.runner.suggestions = lambda: {'light.wall': 'known'}
        self.fixture.update(friendly_name='known', endpoint='top')
        legacy = dict(self.fixture)
        legacy.pop('transport')
        self.assertEqual(self.runner._dymera(legacy), ('known', 'top'))
        self.assertEqual(self.runner._dymera(dict(legacy, transport='zigbee2mqtt')), ('known', 'top'))
        self.assertIsNone(self.runner._dymera(self.fixture))
        await self.runner._apply(self.fixture, self.cue)
        self.assertEqual(self.calls[-1][0], 'turn_on')

    async def test_onoff_light_is_not_sent_unsupported_brightness_or_color(self):
        self.state.attributes = {'supported_color_modes': ['onoff']}
        warning = await self.runner._apply(self.fixture, self.cue)
        self.assertEqual(self.calls[-1], ('turn_on', {'entity_id': 'light.wall'}))
        self.assertIn('nur eingeschaltet', warning)

    async def test_transitions_only_for_supported_static_ha_commands(self):
        self.runner.settings['options']['transition'] = 3
        self.state.attributes = {'supported_color_modes':['rgbw'],'supported_features':32,'effect_list':['candle']}
        await self.runner._apply(self.fixture,self.cue)
        self.assertEqual(self.calls[-1][1]['transition'],3)
        self.cue['mode']='candle'
        await self.runner._apply(self.fixture,self.cue)
        self.assertNotIn('transition',self.calls[-1][1])
        self.cue['mode']='red'
        self.state.attributes['supported_features']=0
        await self.runner._apply(self.fixture,self.cue)
        self.assertNotIn('transition',self.calls[-1][1])

    async def test_dimmer_retains_brightness_without_color(self):
        self.state.attributes = {'supported_color_modes': ['brightness']}
        await self.runner._apply(self.fixture, self.cue)
        self.assertEqual(self.calls[-1][1], {'entity_id': 'light.wall', 'brightness': 152})

    async def test_white_temperature_is_clamped_to_device_range(self):
        self.state.attributes = {'supported_color_modes': ['color_temp'], 'min_color_temp_kelvin': 3000, 'max_color_temp_kelvin': 5000}
        for mode, expected in [('warm', 3000), ('white', 4000), ('ice', 5000), ('candle', 3000)]:
            self.cue['mode'] = mode
            await self.runner._apply(self.fixture, self.cue)
            self.assertEqual(self.calls[-1][1]['color_temp_kelvin'], expected)

    async def test_supported_effect_is_used_and_missing_effect_runs_ha_frames(self):
        self.cue['mode'] = 'candle'
        self.state.attributes = {'supported_color_modes': ['rgbw'], 'effect_list': ['candle']}
        self.assertIsNone(await self.runner._apply(self.fixture, self.cue))
        self.assertEqual(self.calls[-1][1]['effect'], 'candle')
        self.state.attributes['effect_list'] = []
        self.assertIsNone(await self.runner._apply(self.fixture, self.cue))
        self.assertIn('rgb_color', self.calls[-1][1])
        self.assertNotIn('effect', self.calls[-1][1])
        self.assertIn('light.wall', self.runner.ha_effects)

    async def test_all_software_effects_advance_with_valid_standard_actions(self):
        for mode in sorted(EFFECTS):
            for color_mode in ['rgbw', 'rgbww', 'color_temp', 'brightness', 'onoff']:
                with self.subTest(mode=mode, color_mode=color_mode):
                    self.state.attributes = {'supported_color_modes': [color_mode]}
                    self.cue['mode'] = mode
                    await self.runner._apply(self.fixture, self.cue)
                    first = self.calls[-1]
                    self.now += timedelta(seconds=5)
                    await self.runner.effect_tick()
                    action, payload = self.calls[-1]
                    self.assertNotIn('effect', payload)
                    self.assertIn(action, ['turn_on', 'turn_off'])
                    if color_mode == 'onoff':
                        self.assertEqual(set(payload), {'entity_id'})
                    if color_mode in ['rgbw', 'rgbww'] and mode not in ['blink']:
                        self.assertIn('rgb_color', payload)
                        self.assertNotEqual(first, self.calls[-1])
                    if color_mode == 'color_temp' and action == 'turn_on' and mode != 'blink':
                        self.assertIn('color_temp_kelvin', payload)

    async def test_frame_rate_and_static_change_stop_effect(self):
        self.cue['mode'] = 'colorloop'
        await self.runner._apply(self.fixture, self.cue)
        count = len(self.calls)
        self.now += timedelta(seconds=1)
        await self.runner.effect_tick()
        self.assertEqual(len(self.calls), count)
        self.now += timedelta(seconds=2)
        await self.runner.effect_tick()
        self.assertGreater(len(self.calls), count)
        self.cue['mode'] = 'red'
        await self.runner._apply(self.fixture, self.cue)
        self.assertFalse(self.runner.ha_effects)

    async def test_stop_clears_effect_before_snapshot_restore(self):
        settings = self.runner.settings
        settings['fixtures'][0]['transport'] = 'homeassistant'
        settings['packs'][0]['scenes'][0]['tracks']['other']['mode'] = 'candle'
        await self.runner.start('halloween', 'castle')
        self.assertTrue(self.runner.ha_effects)
        await self.runner.stop()
        count = len(self.calls)
        self.now += timedelta(seconds=5)
        await self.runner.effect_tick()
        self.assertFalse(self.runner.ha_effects)
        self.assertEqual(len(self.calls), count)
        self.assertEqual(self.state.state, 'off')

    async def test_effect_failure_does_not_leave_an_orphan_runner(self):
        self.cue['mode'] = 'candle'
        async def fail(*args, **kwargs):
            raise RuntimeError('light service failed')
        self.hass.services.async_call = fail
        with self.assertRaises(RuntimeError):
            await self.runner._apply(self.fixture, self.cue)
        self.assertFalse(self.runner.ha_effects)

    async def test_rgbww_snapshot_and_parallel_area_survive_effect_stop(self):
        self.state.state = 'on'
        self.state.attributes = {'supported_color_modes': ['rgbww'], 'color_mode': 'rgbww',
                                 'rgbww_color': [10, 20, 30, 140, 190], 'brightness': 84}
        self.runner.settings['packs'][0]['scenes'][0]['tracks']['other']['mode'] = 'colorloop'
        await self.runner.start('halloween', 'castle')
        garden = self.hub.areas['garden']
        garden.settings['packs'][0]['scenes'][0]['tracks']['other']['mode'] = 'candle'
        await garden.start('halloween', 'castle')
        await self.runner.stop()
        self.assertEqual(self.calls[-1], ('turn_on', {'entity_id':'light.wall', 'brightness':84,
                          'rgbww_color':[10,20,30,140,190]}))
        self.assertTrue(garden.running)
        self.assertTrue(garden.ha_effects)

    def test_new_catalogue_lights_have_a_show_but_saved_off_is_preserved(self):
        self.assertNotEqual(defaults()['packs'][0]['scenes'][0]['tracks']['other']['mode'], 'off')
        data = defaults()
        data['packs'][0]['scenes'][0]['tracks']['other']['mode'] = 'off'
        self.assertEqual(check_settings(data)['packs'][0]['scenes'][0]['tracks']['other']['mode'], 'off')

    async def test_zero_brightness_turns_off_and_unknown_never_sends(self):
        self.cue['brightness'] = 0
        await self.runner._apply(self.fixture, self.cue)
        self.assertEqual(self.calls[-1], ('turn_off', {'entity_id': 'light.wall'}))
        before = len(self.calls)
        for state in ['unknown', 'unavailable']:
            self.state.state = state
            self.assertIn('nicht verfügbar', await self.runner._apply(self.fixture, self.cue))
        self.assertEqual(len(self.calls), before)

    async def test_restore_preserves_white_channels_and_active_color_mode(self):
        for mode, value in [('rgbw', [40, 60, 80, 170]), ('rgbww', [40, 60, 80, 120, 190]), ('xy', [.2, .3])]:
            with self.subTest(mode=mode):
                key = mode + '_color'
                self.state.state = 'on'
                self.state.attributes = {'brightness': 88, 'color_mode': mode, key: value,
                                         'color_temp_kelvin': 3000, 'hs_color': [40, 30]}
                snapshot = self.runner._snapshot('light.wall')
                await self.runner._restore('light.wall', snapshot)
                self.assertEqual(self.calls[-1][1], {'entity_id': 'light.wall', 'brightness': 88, key: value})

    def test_transport_validation_and_legacy_data(self):
        data = defaults()
        data['fixtures'] = [self.fixture]
        for transport in ['homeassistant', 'zigbee2mqtt', 'auto']:
            self.fixture['transport'] = transport
            self.assertEqual(check_settings(data)['fixtures'][0]['transport'], transport)
        self.fixture.pop('transport')
        self.assertNotIn('transport', check_settings(data)['fixtures'][0])
        self.fixture['transport'] = 'invalid'
        with self.assertRaises(ValueError):
            check_settings(data)
