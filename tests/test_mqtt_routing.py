"""Exercise production MQTT callbacks and native commands with a fake broker."""
import ast
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from test_discovery import discovery, sample

path = Path(__file__).resolve().parents[1] / 'custom_components/lightshow_studio/__init__.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
studio = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Studio')
names = {'got_devices', '_dymera', '_publish', '_apply'}
selected = [n for n in studio.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
test_class = ast.ClassDef(name='StudioUnderTest', bases=[], keywords=[], body=selected, decorator_list=[])


def finish(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError('Fake broker must complete immediately')


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.sent = []

        async def publish(hass, topic, payload, **kwargs):
            self.sent.append((topic, json.loads(payload), kwargs))

        namespace = {'Any': object, 'callback': lambda f: f, 'json': json,
                     'device_list': discovery.device_list, 'command_topic': discovery.command_topic,
                     '_LOGGER': logging.getLogger(__name__), 'DYMERAS': {'046677585235'},
                     'EFFECTS': {'candle'}, 'mqtt': SimpleNamespace(async_publish=publish)}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[test_class], type_ignores=[])), str(path), 'exec'), namespace)
        self.studio = namespace['StudioUnderTest']()
        self.studio.devices = []
        self.studio._devices_by_base = {}
        self.studio.suggestions = lambda: {}
        self.studio.hass = SimpleNamespace(states=SimpleNamespace(get=lambda eid: SimpleNamespace(state='off')))

    def receive(self, prefix, devices):
        self.studio.got_devices(SimpleNamespace(topic=prefix+'/bridge/devices', payload=json.dumps(devices)))

    def test_native_effect_and_speed_use_received_case_sensitive_prefix(self):
        self.receive('Zigbee2mqtt', [sample()])
        fixture = {'entity_id': 'light.demo_top', 'friendly_name': 'demo-wall', 'endpoint': 'top'}
        finish(self.studio._apply(fixture, {'mode': 'candle', 'brightness': 60, 'speed': 25}))
        self.assertEqual(len(self.sent), 2)
        self.assertTrue(all(topic == 'Zigbee2mqtt/demo-wall/set' for topic, _, _ in self.sent))
        self.assertEqual(self.sent[1][1], {'effect_top': 'candle', 'effect_speed_top': .25})
        self.assertTrue(all(options == {'qos': 0, 'retain': False} for _, _, options in self.sent))

    def test_bridge_inventory_replacement_keeps_other_bridges(self):
        self.receive('a', [sample('first')])
        self.receive('b', [sample('second')])
        self.receive('a', [])
        self.assertEqual([d['friendly_name'] for d in self.studio.devices], ['second'])

    def test_invalid_message_keeps_working_inventory(self):
        self.receive('a', [sample()])
        with self.assertLogs(__name__, level='WARNING'):
            self.studio.got_devices(SimpleNamespace(topic='a/bridge/devices', payload='not-json'))
        self.assertEqual(len(self.studio.devices), 1)

    def test_duplicate_names_never_send_a_command(self):
        self.receive('a', [sample()])
        self.receive('b', [sample()])
        with self.assertRaises(ValueError):
            finish(self.studio._publish('demo-wall', {'effect_top': 'candle'}))
        self.assertEqual(self.sent, [])
