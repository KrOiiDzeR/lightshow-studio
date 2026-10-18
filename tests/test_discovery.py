import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/lightshow_studio/discovery.py'
spec = importlib.util.spec_from_file_location('studio_discovery', path)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def sample(name='demo-wall'):
    return {'type': 'Router', 'supported': True, 'friendly_name': name,
            'ieee_address': 'demo-ieee', 'definition': {'model': '046677585235'}}


class DiscoveryTest(unittest.TestCase):
    def test_case_sensitive_prefix_roundtrip(self):
        for prefix in ['zigbee2mqtt', 'Zigbee2mqtt', 'home/garden/z2m']:
            with self.subTest(prefix=prefix):
                actual, devices = discovery.device_list(json.dumps([sample()]), prefix+'/bridge/devices')
                self.assertEqual(actual, prefix)
                self.assertEqual(discovery.command_topic(devices, 'demo-wall'), prefix+'/demo-wall/set')

    def test_skip_coordinator_disabled_unsupported_and_bad_entries(self):
        items = [sample(), dict(sample(), type='Coordinator'), dict(sample(), disabled=True),
                 dict(sample(), supported=False), None, {}, sample('bad/#')]
        _, devices = discovery.device_list(json.dumps(items), 'Zigbee2mqtt/bridge/devices')
        self.assertEqual(len(devices), 1)

    def test_null_definition_is_safe(self):
        _, devices = discovery.device_list(json.dumps([dict(sample(), definition=None)]), 'z2m/bridge/devices')
        self.assertEqual(devices[0]['model'], '')

    def test_malformed_inventory_rejected(self):
        for payload, topic in [('oops', 'z2m/bridge/devices'), ('{}', 'z2m/bridge/devices'), ('[]', 'z2m/bridge/event')]:
            with self.assertRaises(ValueError):
                discovery.device_list(payload, topic)

    def test_ambiguous_or_missing_device_does_not_publish(self):
        _, devices = discovery.device_list(json.dumps([sample()]), 'a/bridge/devices')
        _, other = discovery.device_list(json.dumps([sample()]), 'b/bridge/devices')
        with self.assertRaises(ValueError):
            discovery.command_topic(devices+other, 'demo-wall')
        with self.assertRaises(ValueError):
            discovery.command_topic(devices, 'unknown')

    def test_literal_base_topic_validation(self):
        self.assertEqual(discovery.base_topic('House/Zigbee/'), 'House/Zigbee')
        for value in ['', '#', '+', 'home/+/zigbee', None]:
            with self.assertRaises(ValueError):
                discovery.base_topic(value)
