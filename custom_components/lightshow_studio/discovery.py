"""Zigbee2MQTT metadata parsing, independent of Home Assistant."""
from __future__ import annotations

import json


def base_topic(value: str) -> str:
    """Validate a literal MQTT prefix, preserving its case."""
    if not isinstance(value, str):
        raise ValueError('MQTT-Basistopic muss Text sein')
    value = value.rstrip('/')
    if not value or any(c in value for c in ('+', '#', '\x00')):
        raise ValueError('MQTT-Basistopic darf nicht leer sein oder Platzhalter enthalten')
    return value


def device_list(payload: str | bytes, topic: str) -> tuple[str, list[dict]]:
    """Read one bridge's retained inventory without trusting arbitrary payloads."""
    suffix = '/bridge/devices'
    if not topic.endswith(suffix):
        raise ValueError('Unbekanntes Gerätelisten-Topic')
    prefix = base_topic(topic[:-len(suffix)])
    loaded = json.loads(payload)
    if not isinstance(loaded, list):
        raise ValueError('Geräteliste muss ein JSON-Array sein')
    result = []
    for item in loaded:
        if not isinstance(item, dict) or item.get('type') == 'Coordinator':
            continue
        if item.get('supported') is False or item.get('disabled') is True:
            continue
        name = item.get('friendly_name')
        if not isinstance(name, str) or not name or any(c in name for c in ('+', '#', '\x00')):
            continue
        definition = item.get('definition')
        definition = definition if isinstance(definition, dict) else {}
        result.append({
            'friendly_name': name,
            'ieee_address': str(item.get('ieee_address') or ''),
            'model': str(definition.get('model') or ''),
            'description': str(definition.get('description') or ''),
            'base_topic': prefix,
        })
    return prefix, result


def command_topic(devices: list[dict], name: str) -> str:
    """Resolve a device unambiguously; never guess between two bridges."""
    matches = [d for d in devices if d['friendly_name'] == name]
    if not matches:
        raise ValueError('Zigbee2MQTT-Gerät nicht in der Geräteliste gefunden')
    if len(matches) != 1:
        raise ValueError('Gerätename ist auf mehreren Bridges vorhanden; mqtt_base_topic festlegen')
    return f"{base_topic(matches[0]['base_topic'])}/{name}/set"
