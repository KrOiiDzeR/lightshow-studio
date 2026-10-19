"""Lightshow Studio: reusable event packs + one-time HA/Zigbee2MQTT light inventory.

Local-only. No credentials are stored. All light actions are explicitly requested,
except optional annual/weekly schedules enabled by the user. Admin-only websocket API.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import random
import re
from typing import Any

import voluptuous as vol
from homeassistant.components import frontend, mqtt, panel_custom, websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .settings import (
    COLORS, EFFECTS, check_settings, defaults, migrate_v1, validate_pack,
)
from .discovery import base_topic, command_topic, device_list

from .const import CONFIG_PATH, CONTROL_PATH, DOMAIN, MODULE_URL, VERSION
from .planning import scheduled_target
from .shuffle import shuffle_candidates
from .ha_effects import frame as ha_effect_frame
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Any(None, vol.Schema({vol.Optional("mqtt_base_topic"): base_topic})),
}, extra=vol.ALLOW_EXTRA)
_LOGGER = logging.getLogger(__name__)
IEEE_RE = re.compile(r"0x[0-9a-fA-F]{16}")
DYMERAS = {"046677585235"}
RGB = {"red": [255, 0, 0], "purple": [152, 40, 225], "green": [0, 220, 65],
       "warm": [255, 145, 60], "blue": [0, 80, 255], "gold": [255, 180, 35],
       "ice": [110, 205, 255], "white": [255, 255, 255]}


def mode_rgb(cue: dict) -> list[int]:
    if cue["mode"] != "custom_color":
        return RGB[cue["mode"]]
    value = cue["color"]
    return [int(value[i:i+2], 16) for i in (1, 3, 5)]


class Studio:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.store = Store(hass, 2, DOMAIN)
        self.settings = defaults()
        self.devices: list[dict] = []
        self._devices_by_base: dict[str, list[dict]] = {}
        self.running = False
        self.active_pack = ""
        self.active_scene = ""
        self.active_program = ""
        self.program_index = 0
        self.program_until = dt_util.now()
        self.run_source = "manual"
        self.schedule_key = None
        self.connection = {"mqtt_mode": "disabled", "mqtt_base_topic": ""}
        self.snapshots: dict[str, dict] = {}
        self.native: dict[str, tuple[str, str]] = {}
        self.preview_tasks: dict[str, asyncio.Task] = {}
        self.preview_states: dict[str, tuple] = {}
        self.messages: list[str] = []
        self.ha_effects: dict[str, dict] = {}
        self.migrated = False
        self.manual_stop_date: str | None = None
        self.last_shuffle = dt_util.now()
        self.last_wind = dt_util.now()
        self.shuffle_seen = set()
        self.stop_at = None
        self._lock = asyncio.Lock()

    async def load(self):
        data = await self.store.async_load()
        if data is not None:
            self.settings = check_settings(data)
            return
        legacy = await Store(self.hass, 1, "halloween_control_center").async_load()
        if legacy:
            try:
                self.settings = migrate_v1(legacy)
                await self.store.async_save(self.settings)
                self.migrated = True
                _LOGGER.info("Halloween Control Center v1 settings imported into Lightshow Studio")
            except (ValueError, TypeError, KeyError) as err:
                _LOGGER.warning("Legacy migration skipped: %s", err)

    async def save(self, data: dict):
        checked = check_settings(data)
        async with self._lock:
            if self.running or self.preview_tasks:
                raise ValueError("Bitte zuerst Show bzw. Vorschau beenden")
            self.settings = checked
            await self.store.async_save(checked)

    @callback
    def got_devices(self, message: Any):
        try:
            prefix, devices = device_list(message.payload, message.topic)
            self._devices_by_base[prefix] = devices
            self.devices = [device for inventory in self._devices_by_base.values() for device in inventory]
        except (TypeError, ValueError, KeyError) as err:
            _LOGGER.warning("Could not read Zigbee2MQTT device list: %s", err)

    def suggestions(self) -> dict[str, str]:
        ent_reg, dev_reg = er.async_get(self.hass), dr.async_get(self.hass)
        by_ieee = {d["ieee_address"].lower(): d["friendly_name"] for d in self.devices if d["ieee_address"]}
        result = {}
        for st in self.hass.states.async_all("light"):
            ent = ent_reg.async_get(st.entity_id)
            dev = dev_reg.async_get(ent.device_id) if ent and ent.device_id else None
            if not dev:
                continue
            for _, identifier in dev.identifiers | dev.connections:
                match = IEEE_RE.search(str(identifier))
                if match and match.group().lower() in by_ieee:
                    result[st.entity_id] = by_ieee[match.group().lower()]
                    break
        return result

    def data(self) -> dict:
        return {"settings": self.settings, "connection": self.connection, "devices": self.devices, "suggestions": self.suggestions(),
                "migrated": self.migrated,
                "status": {"running": self.running, "stop_at": self.stop_at, "pack_id": self.active_pack, "scene_id": self.active_scene, "program_id": self.active_program,
                           "source": self.run_source, "previewing": list(self.preview_tasks), "warnings": self.messages[-15:]}}

    def _fixture(self, eid: str) -> dict | None:
        return next((f for f in self.settings["fixtures"] if f["entity_id"] == eid), None)

    def _dymera(self, f: dict) -> tuple[str, str] | None:
        # An explicit HA choice must never be overridden by discovery.
        if f.get("transport", "auto") == "homeassistant":
            return None
        name = f["friendly_name"] or self.suggestions().get(f["entity_id"], "")
        device = next((d for d in self.devices if d["friendly_name"] == name), None)
        if not device or device["model"] not in DYMERAS:
            return None
        ep = f["endpoint"]
        if ep == "auto":
            eid = f["entity_id"]
            ep = "top" if eid.endswith("_top") else "bottom" if eid.endswith("_bottom") else "auto"
        return (name, ep) if ep in {"top", "bottom"} else None

    async def _publish(self, name: str, payload: dict):
        topic = command_topic(self.devices, name)
        await mqtt.async_publish(self.hass, topic, json.dumps(payload), qos=0, retain=False)

    def _snapshot(self, eid: str) -> dict | None:
        st = self.hass.states.get(eid)
        if st is None or st.state in ("unavailable", "unknown"):
            return None
        props = st.attributes
        return {"state": st.state, "brightness": props.get("brightness"), "color_mode": props.get("color_mode"),
                "rgb_color": props.get("rgb_color"), "hs_color": props.get("hs_color"),
                "rgbw_color": props.get("rgbw_color"), "rgbww_color": props.get("rgbww_color"), "xy_color": props.get("xy_color"),
                "color_temp_kelvin": props.get("color_temp_kelvin"), "effect": props.get("effect")}

    async def _apply(self, f: dict, cue: dict, *, effect_frame: bool = False) -> str | None:
        eid = f["entity_id"]
        if not effect_frame:
            self.ha_effects.pop(eid, None)
        st = self.hass.states.get(eid)
        if st is None or st.state in ("unavailable", "unknown"):
            return f"{eid}: Entität ist nicht verfügbar"
        mode = cue["mode"]
        bright = max(1, round(cue["brightness"] * 2.54))
        native = self._dymera(f)
        if native:
            name, ep = native
            if mode == "off" or cue["brightness"] == 0:
                await self._publish(name, {f"effect_{ep}": "stop_effect"})
                await self._publish(name, {f"state_{ep}": "OFF"})
            elif mode in EFFECTS:
                await self._publish(name, {f"state_{ep}": "ON", f"brightness_{ep}": bright})
                await self._publish(name, {f"effect_{ep}": mode, f"effect_speed_{ep}": round(cue["speed"] / 100, 2)})
            else:
                await self._publish(name, {f"effect_{ep}": "stop_effect"})
                r, g, b = mode_rgb(cue)
                await self._publish(name, {f"state_{ep}": "ON", f"brightness_{ep}": bright,
                                           f"color_{ep}": {"r": r, "g": g, "b": b}})
            return None
        if mode == "off" or cue["brightness"] == 0:
            off = {"entity_id": eid}
            if not effect_frame and self.settings["options"].get("transition", 0) and (st.attributes.get("supported_features", 0) & 32):
                off["transition"] = self.settings["options"]["transition"]
            await self.hass.services.async_call("light", "turn_off", off, blocking=True)
            return None
        kwargs = {"entity_id": eid}
        if not effect_frame and mode not in EFFECTS and self.settings["options"].get("transition", 0) and (st.attributes.get("supported_features", 0) & 32):
            kwargs["transition"] = self.settings["options"]["transition"]
        available = st.attributes.get("effect_list") or []
        color_modes = st.attributes.get("supported_color_modes") or []
        if any(x != "onoff" for x in color_modes):
            kwargs["brightness"] = bright
        color_ok = any(x in color_modes for x in ("hs", "rgb", "xy", "rgbw", "rgbww"))
        note = None
        if mode in EFFECTS:
            if mode in available:
                kwargs["effect"] = mode
            else:
                # Run a software show through HA's public light actions. On/off
                # lights only participate in explicit blinking, otherwise stay on.
                dimmable = any(x != "onoff" for x in color_modes)
                if dimmable or mode == "blink":
                    warning = await self._apply(f, ha_effect_frame(cue, 0, sum(map(ord, eid))), effect_frame=True)
                    self.ha_effects[eid] = {"fixture": dict(f), "cue": dict(cue),
                        "started": dt_util.now().timestamp(), "last": dt_util.now().timestamp()}
                    return warning
                note = f"{eid}: nur Ein/Aus verfügbar; für {mode} eingeschaltet"
        elif color_ok:
            kwargs["rgb_color"] = mode_rgb(cue)
        elif "color_temp" in color_modes and (effect_frame or mode in ("warm", "white", "ice")):
            low = st.attributes.get("min_color_temp_kelvin", 2000)
            high = st.attributes.get("max_color_temp_kelvin", 6500)
            kwargs["color_temp_kelvin"] = max(low, min(high, cue.get("kelvin", {"warm": 2700, "white": 4000, "ice": 6500}.get(mode, 2700))))
        else:
            note = f"{eid}: keine Farbsteuerung unterstützt; {'nur Helligkeit gesetzt' if 'brightness' in kwargs else 'nur eingeschaltet'}"
        await self.hass.services.async_call("light", "turn_on", kwargs, blocking=True)
        return note

    async def _restore(self, eid: str, snapshot: dict, native: tuple[str, str] | None = None):
        self.ha_effects.pop(eid, None)
        target = native or self.native.get(eid)
        if target:
            try:
                await self._publish(target[0], {f"effect_{target[1]}": "stop_effect"})
            except Exception as err:
                _LOGGER.warning("Could not stop native effect before restoration of %s: %s", eid, err)
        if snapshot["state"] == "off":
            await self.hass.services.async_call("light", "turn_off", {"entity_id": eid}, blocking=True)
            return
        data = {"entity_id": eid}
        if snapshot.get("brightness") is not None:
            data["brightness"] = snapshot["brightness"]
        color_key = {"rgbw": "rgbw_color", "rgbww": "rgbww_color", "rgb": "rgb_color", "hs": "hs_color", "xy": "xy_color"}.get(snapshot.get("color_mode"))
        if color_key and snapshot.get(color_key) is not None:
            data[color_key] = list(snapshot[color_key])
        elif snapshot.get("color_temp_kelvin") is not None:
            data["color_temp_kelvin"] = snapshot["color_temp_kelvin"]
        elif snapshot.get("hs_color") is not None:
            data["hs_color"] = list(snapshot["hs_color"])
        elif snapshot.get("rgb_color") is not None:
            data["rgb_color"] = list(snapshot["rgb_color"])
        st = self.hass.states.get(eid)
        if snapshot.get("effect") and st and snapshot["effect"] in (st.attributes.get("effect_list") or []):
            data["effect"] = snapshot["effect"]
        await self.hass.services.async_call("light", "turn_on", data, blocking=True)

    def _pack_scene(self, pack_id: str, scene_id: str) -> tuple[dict, dict]:
        pack = next((p for p in self.settings["packs"] if p["id"] == pack_id), None)
        scene = next((s for s in pack["scenes"] if s["id"] == scene_id), None) if pack else None
        if pack is None or scene is None:
            raise ValueError("Show-Paket oder Szene nicht gefunden")
        return pack, scene

    def assignments(self, scene: dict) -> list[tuple[dict, dict]]:
        overrides = {o["entity_id"]: o for o in scene["overrides"]}
        return [(f, overrides.get(f["entity_id"], scene["tracks"][f["role"]]))
                for f in self.settings["fixtures"] if f["enabled"]]

    async def _change_locked(self, pack_id: str, scene_id: str):
        _, scene = self._pack_scene(pack_id, scene_id)
        assigns = self.assignments(scene)
        warnings: list[str] = []
        ids = {f["entity_id"] for f, _ in assigns}
        # Restore lights removed from running show before applying the next one.
        for eid in list(self.snapshots):
            if eid not in ids:
                try:
                    await self._restore(eid, self.snapshots[eid])
                    del self.snapshots[eid]
                    self.native.pop(eid, None)
                except Exception as err:
                    warnings.append(f"{eid}: Rücksetzen fehlgeschlagen: {err}")
        for f, cue in assigns:
            eid = f["entity_id"]
            if eid not in self.snapshots:
                snapshot = self._snapshot(eid)
                if snapshot:
                    self.snapshots[eid] = snapshot
            if eid not in self.snapshots:
                warnings.append(f"{eid}: nicht verfügbar, übersprungen")
                continue
            try:
                if target := self._dymera(f):
                    self.native[eid] = target
                warning = await self._apply(f, cue)
                if warning:
                    warnings.append(warning)
            except Exception as err:
                _LOGGER.exception("Lightshow failed for %s", eid)
                warnings.append(f"{eid}: {err}")
        self.active_pack = pack_id
        self.active_scene = scene_id
        self.messages = warnings
        self.last_shuffle = dt_util.now()

    async def start_program(self, pack_id: str, program_id: str, source: str = "manual"):
        async with self._lock:
            pack = next((p for p in self.settings["packs"] if p["id"] == pack_id), None)
            program = next((pr for pr in pack.get("programs", []) if pr["id"] == program_id), None) if pack else None
            if not program:
                raise ValueError("Show-Ablauf nicht gefunden")
            await self._cancel_previews()
            if not self.running:
                self.snapshots, self.native = {}, {}
            self.active_program = program_id
            self.program_index = 0
            self.program_until = dt_util.now() + timedelta(seconds=program["steps"][0]["duration"])
            await self._change_locked(pack_id, program["steps"][0]["scene_id"])
            self.running = True
            self.run_source = source
            self.shuffle_seen = {(pack_id, self.active_scene)}

    async def start(self, pack_id: str, scene_id: str, source: str = "manual"):
        async with self._lock:
            self._pack_scene(pack_id, scene_id)
            await self._cancel_previews()
            if not self.running:
                self.snapshots, self.native = {}, {}
            await self._change_locked(pack_id, scene_id)
            self.active_program = ""
            self.running = True
            self.run_source = source
            self.shuffle_seen = {(pack_id, scene_id)}

    async def _stop_locked(self):
        self.stop_at = None
        self.shuffle_seen = set()
        self.ha_effects.clear()
        if not self.running:
            return
        self.running = False
        self.active_pack = self.active_scene = self.active_program = ""
        warnings = []
        for eid, state in list(self.snapshots.items()):
            try:
                await self._restore(eid, state)
            except Exception as err:
                warnings.append(f"{eid}: Zurücksetzen fehlgeschlagen: {err}")
        self.snapshots, self.native = {}, {}
        self.messages = warnings

    async def stop(self, manual: bool = True):
        async with self._lock:
            if manual:
                self.manual_stop_date = dt_util.now().date().isoformat()
            await self._cancel_previews()
            await self._stop_locked()

    async def preview(self, pack_id: str, scene_id: str, eid: str):
        async with self._lock:
            if self.running:
                raise ValueError("Vorschau nur möglich, wenn keine Show läuft")
            _, sc = self._pack_scene(pack_id, scene_id)
            f = self._fixture(eid)
            if not f or not f["enabled"]:
                raise ValueError("Leuchte ist nicht in deiner zentralen Lampenliste aktiviert")
            if eid in self.preview_tasks:
                raise ValueError("Diese Leuchte wird bereits getestet")
            snapshot = self._snapshot(eid)
            if snapshot is None:
                raise ValueError("Leuchte aktuell nicht verfügbar")
            cue = next((x for x in sc["overrides"] if x["entity_id"] == eid), sc["tracks"][f["role"]])
            target = self._dymera(f)
            warn = await self._apply(f, cue)
            self.messages = [warn] if warn else []
            self.preview_states[eid] = (snapshot, target)

            async def finish():
                try:
                    await asyncio.sleep(10)
                    async with self._lock:
                        await self._restore(eid, snapshot, target)
                except asyncio.CancelledError:
                    # stop/start cancels previews while already holding _lock.
                    # Restore here without trying to acquire it a second time.
                    await self._restore(eid, snapshot, target)
                except Exception as err:
                    _LOGGER.warning("Preview restore for %s failed: %s", eid, err)
                finally:
                    self.preview_tasks.pop(eid, None)
                    self.preview_states.pop(eid, None)

            self.preview_tasks[eid] = self.hass.async_create_task(finish(), f"lightshow_preview_{eid}")

    async def _cancel_previews(self):
        tasks = list(self.preview_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        # A task cancelled before its first CPU turn never enters its finally.
        for eid, (snapshot, target) in list(self.preview_states.items()):
            try:
                await self._restore(eid, snapshot, target)
            finally:
                self.preview_states.pop(eid, None)
                self.preview_tasks.pop(eid, None)

    async def effect_tick(self):
        """Serialize frames with scene changes, previews and snapshot restoration."""
        async with self._lock:
            now = dt_util.now().timestamp()
            for eid, active in list(self.ha_effects.items()):
                if now - active["last"] < 2:
                    continue
                active["last"] = now
                try:
                    cue = ha_effect_frame(active["cue"], now - active["started"], sum(map(ord, eid)))
                    if cue == active.get("sent"):
                        continue
                    warning = await self._apply(active["fixture"], cue, effect_frame=True)
                    active["sent"] = cue
                    if warning and warning not in self.messages:
                        self.messages = (self.messages + [warning])[-15:]
                except Exception as err:
                    self.ha_effects.pop(eid, None)
                    self.messages = (self.messages + [f"{eid}: HA-Effekt beendet: {err}"])[-15:]

    async def tick(self):
        now = dt_util.now()
        if self.running and self.stop_at is not None and now.timestamp() >= self.stop_at:
            await self.stop(manual=True)
            return
        day = now.date()
        target = scheduled_target(self.settings, now)
        if self.running and self.run_source == "schedule" and (not target or target[0] != self.schedule_key):
            await self.stop(manual=False)
        if not self.running and target and self.manual_stop_date != day.isoformat():
            key, pack_id, scene_id, program_id = target
            if program_id:
                await self.start_program(pack_id, program_id, source="schedule")
            else:
                await self.start(pack_id, scene_id, source="schedule")
            self.schedule_key = key
        if self.running and self.active_program and now >= self.program_until:
            async with self._lock:
                pack = next(p for p in self.settings["packs"] if p["id"] == self.active_pack)
                program = next(pr for pr in pack["programs"] if pr["id"] == self.active_program)
                self.program_index = (self.program_index + 1) % len(program["steps"])
                step = program["steps"][self.program_index]
                self.program_until = now + timedelta(seconds=step["duration"])
                await self._change_locked(pack["id"], step["scene_id"])
        opts = self.settings["options"]
        if self.running and not self.active_program and opts["shuffle"] and (now - self.last_shuffle).total_seconds() >= opts["shuffle_interval"]:
            choices = shuffle_candidates(self.settings, self.active_pack, self.active_scene)
            if choices:
                async with self._lock:
                    if opts.get("shuffle_no_repeat", True):
                        self.shuffle_seen.add((self.active_pack, self.active_scene))
                        remaining = [pair for pair in choices if pair not in self.shuffle_seen]
                        if not remaining:
                            self.shuffle_seen = set()
                            remaining = choices
                        selected = random.choice(remaining)
                        self.shuffle_seen.add(selected)
                    else:
                        selected = random.choice(choices)
                    await self._change_locked(*selected)
            else:
                self.last_shuffle = now
        if self.running and opts["wind"] and (now - self.last_wind).total_seconds() >= 30:
            self.last_wind = now
            _, scene = self._pack_scene(self.active_pack, self.active_scene)
            possibilities = [(f, cue) for f, cue in self.assignments(scene)
                             if cue["mode"] in ("candle", "fireplace") and self._dymera(f)]
            if possibilities:
                f, cue = random.choice(possibilities)
                try:
                    async with self._lock:
                        name, ep = self._dymera(f)
                        speed = max(0.0, min(1.0, (cue["speed"] + random.randint(-20, 20))/100))
                        await self._publish(name, {f"effect_speed_{ep}": round(speed, 2)})
                except Exception as err:
                    _LOGGER.warning("Wind update failed: %s", err)


class StudioHub:
    """One shared MQTT connection and store, independent runners for every area."""

    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 2, DOMAIN)
        self.areas = {}
        self.metadata = {}
        self.connection = {"mqtt_mode": "disabled", "mqtt_base_topic": ""}
        self._devices_by_base = {}
        self.devices = []
        self._lock = asyncio.Lock()
        self.migrated = False

    @property
    def running(self):
        return any(area.running for area in self.areas.values())

    @property
    def preview_tasks(self):
        return {f"{key}:{eid}": task for key, area in self.areas.items() for eid, task in area.preview_tasks.items()}

    def configuration(self):
        return {"schema": 3, "areas": [{**self.metadata[key], "settings": area.settings} for key, area in self.areas.items()]}

    def _replace(self, configuration):
        """Retain existing runners so other areas keep their snapshots and timers."""
        retained = {}
        metadata = {}
        for item in configuration["areas"]:
            key = item["id"]
            area = self.areas.get(key) or Studio(self.hass)
            area.settings = item["settings"]
            area.devices = self.devices
            retained[key] = area
            metadata[key] = {field: item[field] for field in ("id", "name", "icon")}
        self.areas, self.metadata = retained, metadata

    async def load(self):
        from .areas import area_configuration
        data = await self.store.async_load()
        if data is None:
            legacy = await Store(self.hass, 1, "halloween_control_center").async_load()
            if legacy:
                try:
                    data = migrate_v1(legacy)
                    self.migrated = True
                except (ValueError, TypeError, KeyError) as err:
                    _LOGGER.warning("Legacy migration skipped: %s", err)
        self._replace(area_configuration(data))

    def _area(self, area_id=None):
        key = area_id or next(iter(self.areas))
        if key not in self.areas:
            raise ValueError("Bereich nicht gefunden")
        return self.areas[key]

    @callback
    def got_devices(self, message):
        try:
            prefix, devices = device_list(message.payload, message.topic)
            self._devices_by_base[prefix] = devices
            self.devices = [device for inventory in self._devices_by_base.values() for device in inventory]
            for area in self.areas.values():
                area.devices = self.devices
        except (TypeError, ValueError, KeyError) as err:
            _LOGGER.warning("Could not read Zigbee2MQTT device list: %s", err)

    def data(self, area_id=None):
        area = self._area(area_id)
        key = next(key for key, candidate in self.areas.items() if candidate is area)
        result = area.data()
        summaries = []
        for item_id, runner in self.areas.items():
            pack = next((p for p in runner.settings["packs"] if p["id"] == runner.active_pack), {})
            scene = next((s for s in pack.get("scenes", []) if s["id"] == runner.active_scene), {})
            program = next((p for p in pack.get("programs", []) if p["id"] == runner.active_program), {})
            summaries.append({**self.metadata[item_id], "running": runner.running,
                              "previewing": bool(runner.preview_tasks), "warnings": runner.messages[-15:],
                              "pack": pack.get("name", ""), "scene": scene.get("name", ""),
                              "program": program.get("name", ""), "source": runner.run_source, "stop_at": runner.stop_at,
                              "lights": sum(f["enabled"] for f in runner.settings["fixtures"])})
        result.update(area_id=key, areas=summaries, configuration=self.configuration(),
                      connection=self.connection, migrated=self.migrated)
        return result

    async def _persist(self, candidate):
        from .areas import area_configuration
        checked = area_configuration(candidate)
        await self.store.async_save(checked)
        self._replace(checked)

    async def save(self, settings, area_id=None):
        import copy
        async with self._lock:
            area = self._area(area_id)
            if area.running or area.preview_tasks:
                raise ValueError("Bitte zuerst die Show bzw. Vorschau in diesem Bereich beenden")
            candidate = copy.deepcopy(self.configuration())
            key = next(key for key, runner in self.areas.items() if runner is area)
            next(row for row in candidate["areas"] if row["id"] == key)["settings"] = settings
            await self._persist(candidate)

    async def operate(self, changes, area_id=None):
        import copy
        from .planning import operation_settings
        async with self._lock:
            area = self._area(area_id)
            key = next(key for key, runner in self.areas.items() if runner is area)
            candidate = copy.deepcopy(self.configuration())
            next(row for row in candidate["areas"] if row["id"] == key)["settings"] = operation_settings(area.settings, changes)
            await self._persist(candidate)

    async def edit_areas(self, action, area_id=None, name="", icon="💡", configuration=None):
        import copy
        async with self._lock:
            candidate = copy.deepcopy(self.configuration())
            if action in ("add", "copy"):
                import uuid
                key = "area_" + uuid.uuid4().hex[:12]
                settings = defaults()
                if action == "copy":
                    source = self._area(area_id)
                    settings = copy.deepcopy(source.settings)
                    settings["fixtures"] = []
                    for pack in settings["packs"]:
                        pack["schedule"]["enabled"] = False
                        for scene in pack["scenes"]:
                            scene["overrides"] = []
                    for row in settings.get("weekly", []):
                        row["enabled"] = False
                candidate["areas"].append({"id": key, "name": name, "icon": icon, "settings": settings})
            elif action == "restore":
                if self.running or self.preview_tasks:
                    raise ValueError("Vor vollständiger Wiederherstellung alle Bereiche stoppen")
                candidate = configuration
                key = None
            else:
                self._area(area_id)
                key = area_id or next(iter(self.areas))
                if action == "rename":
                    row = next(row for row in candidate["areas"] if row["id"] == key)
                    row.update(name=name, icon=icon)
                elif action == "remove":
                    if self._area(key).running or self._area(key).preview_tasks:
                        raise ValueError("Bereich zuerst stoppen")
                    candidate["areas"] = [row for row in candidate["areas"] if row["id"] != key]
                    key = None
                else:
                    raise ValueError("Unbekannte Bereichsaktion")
            await self._persist(candidate)
            return key or next(iter(self.areas))

    async def start(self, pack_id, scene_id, area_id=None):
        async with self._lock:
            await self._area(area_id).start(pack_id, scene_id)

    async def control(self, action, area_id=None, area_ids=None, pack_id="", scene_id="", minutes=0):
        """Small runtime commands; validate all group targets before changing lights."""
        import copy
        async with self._lock:
            area = self._area(area_id)
            if action == "timer":
                if type(minutes) is not int or not 0 <= minutes <= 720:
                    raise ValueError("Timer: 0 bis 720 Minuten")
                if minutes and not area.running:
                    raise ValueError("Bitte zuerst die Show starten")
                area.stop_at = dt_util.now().timestamp() + minutes * 60 if minutes else None
                return {}
            if action == "favorite":
                area._pack_scene(pack_id, scene_id)
                candidate = copy.deepcopy(self.configuration())
                key = next(key for key, runner in self.areas.items() if runner is area)
                settings = next(row["settings"] for row in candidate["areas"] if row["id"] == key)
                pair = {"pack_id": pack_id, "scene_id": scene_id}
                favorites = settings.setdefault("favorites", [])
                if pair in favorites:
                    favorites.remove(pair)
                else:
                    favorites.append(pair)
                await self._persist(candidate)
                return {}
            if action not in ("start_selected", "stop_selected"):
                raise ValueError("Unbekannte Bedienaktion")
            if not isinstance(area_ids, list) or not 1 <= len(area_ids) <= 30 or any(not isinstance(key, str) for key in area_ids) or len(set(area_ids)) != len(area_ids):
                raise ValueError("Bitte 1 bis 30 unterschiedliche Bereiche auswählen")
            targets = [(key, self._area(key)) for key in area_ids]
            if action == "start_selected":
                for key, runner in targets:
                    try:
                        runner._pack_scene(pack_id, scene_id)
                    except ValueError as err:
                        raise ValueError(f"{self.metadata[key]['name']}: ausgewählte Szene fehlt") from err
                    if not any(f["enabled"] for f in runner.settings["fixtures"]):
                        raise ValueError(f"{self.metadata[key]['name']}: keine aktive Lampe")
            results = {}
            for key, runner in targets:
                try:
                    if action == "start_selected":
                        await runner.start(pack_id, scene_id)
                    else:
                        await runner.stop()
                    results[key] = {"ok": True, "warnings": runner.messages[-15:]}
                except Exception as err:
                    results[key] = {"ok": False, "error": str(err)}
            return results

    async def start_program(self, pack_id, program_id, area_id=None):
        async with self._lock:
            await self._area(area_id).start_program(pack_id, program_id)

    async def preview(self, pack_id, scene_id, entity_id, area_id=None):
        async with self._lock:
            await self._area(area_id).preview(pack_id, scene_id, entity_id)

    async def stop(self, manual=True, area_id=None):
        async with self._lock:
            for area in ([self._area(area_id)] if area_id else list(self.areas.values())):
                await area.stop(manual=manual)

    async def tick(self):
        async with self._lock:
            for key, area in self.areas.items():
                try:
                    await area.tick()
                except Exception:
                    _LOGGER.exception("Lightshow scheduler error in area %s", key)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    js_path = Path(__file__).parent / "static" / "lightshow-studio.js"
    await hass.http.async_register_static_paths([StaticPathConfig(f"/{DOMAIN}/lightshow-studio.js", str(js_path), False)])
    if DOMAIN in config:
        hass.async_create_task(hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=config[DOMAIN] or {}))

    async def service_start(call: ServiceCall):
        await hass.data[DOMAIN].start(call.data["pack_id"], call.data["scene_id"], **({"area_id": call.data["area_id"]} if "area_id" in call.data else {}))

    async def service_stop(_call: ServiceCall):
        await hass.data[DOMAIN].stop(**({"area_id": _call.data["area_id"]} if "area_id" in _call.data else {}))

    hass.services.async_register(DOMAIN, "start", service_start, schema=vol.Schema({vol.Required("pack_id"): str, vol.Required("scene_id"): str, vol.Optional("area_id"): str}))
    async def service_program(call: ServiceCall):
        await hass.data[DOMAIN].start_program(call.data["pack_id"], call.data["program_id"], **({"area_id": call.data["area_id"]} if "area_id" in call.data else {}))

    hass.services.async_register(DOMAIN, "stop", service_stop, schema=vol.Schema({vol.Optional("area_id"): str}))
    hass.services.async_register(DOMAIN, "start_program", service_program, schema=vol.Schema({vol.Required("pack_id"): str, vol.Required("program_id"): str, vol.Optional("area_id"): str}))
    for handler in (ws_get, ws_save, ws_operate, ws_areas, ws_connection, ws_start, ws_program, ws_stop, ws_preview, ws_control):
        websocket_api.async_register_command(hass, handler)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start one UI-managed Studio; preserve the existing v2 storage key."""
    studio = StudioHub(hass)
    await studio.load()
    studio.connection = {**entry.data, **entry.options}
    mode = studio.connection.get("mqtt_mode", "auto")
    unsubscribe = lambda: None
    if mode != "disabled":
        prefix = studio.connection.get("mqtt_base_topic", "")
        topic = f"{prefix}/bridge/devices" if mode == "manual" else "+/bridge/devices"
        try:
            unsubscribe = await mqtt.async_subscribe(hass, topic, studio.got_devices)
        except Exception as err:
            raise ConfigEntryNotReady("MQTT connection is not ready") from err
    hass.data[DOMAIN] = studio

    async def periodic(_time: datetime):
        try:
            await studio.tick()
        except Exception:
            _LOGGER.exception("Lightshow scheduler error")

    cancel = async_track_time_interval(hass, periodic, timedelta(seconds=5))

    async def effect_periodic(_time: datetime):
        async with studio._lock:
            for area in studio.areas.values():
                await area.effect_tick()

    cancel_effects = async_track_time_interval(hass, effect_periodic, timedelta(seconds=2))

    closed = False

    @callback
    def shutdown(_event=None):
        nonlocal closed
        if closed:
            return
        closed = True
        unsubscribe()
        cancel()
        cancel_effects()
        for area in studio.areas.values():
            area.ha_effects.clear()
        for task in list(studio.preview_tasks.values()):
            task.cancel()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown))
    entry.async_on_unload(shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    frontend.add_extra_js_url(hass, MODULE_URL)
    await panel_custom.async_register_panel(
        hass, frontend_url_path=CONFIG_PATH, webcomponent_name="lightshow-studio-panel",
        module_url=MODULE_URL, require_admin=True, config_panel_domain=DOMAIN,
        config={"mode": "configuration"})
    await panel_custom.async_register_panel(
        hass, frontend_url_path=CONTROL_PATH, webcomponent_name="lightshow-studio-panel",
        module_url=MODULE_URL, sidebar_title="Lightshow Studio", sidebar_icon="mdi:party-popper",
        require_admin=True, config={"mode": "operation"})
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, DOMAIN)},
        name="Lightshow Studio", manufacturer="Lightshow Studio", model="Show Controller",
        sw_version=VERSION, configuration_url=f"homeassistant://{CONFIG_PATH}")
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Restore lights before unloading; the store remains untouched."""
    studio = hass.data.get(DOMAIN)
    if studio:
        await studio.stop(manual=False)
    for path in (CONFIG_PATH, CONTROL_PATH):
        frontend.async_remove_panel(hass, path)
    frontend.remove_extra_js_url(hass, MODULE_URL)
    hass.data.pop(DOMAIN, None)
    return True


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get", vol.Optional("area_id"): str})
@callback
def ws_get(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_area", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/save", vol.Required("settings"): dict, vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_save(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].save(msg["settings"], msg.get("area_id"))
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_settings", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/operate", vol.Required("changes"): dict, vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_operate(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    """Merge only runtime controls, never accept a stale complete configuration."""
    try:
        studio = hass.data[DOMAIN]
        await studio.operate(msg["changes"], msg.get("area_id"))
        conn.send_result(msg["id"], studio.data(msg.get("area_id")))
    except (ValueError, KeyError, TypeError) as err:
        conn.send_error(msg["id"], "invalid_operation", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/areas", vol.Required("action"): str,
    vol.Optional("area_id"): str, vol.Optional("name", default=""): str,
    vol.Optional("icon", default="💡"): str, vol.Optional("configuration"): dict})
@websocket_api.async_response
async def ws_areas(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        studio = hass.data[DOMAIN]
        selected = await studio.edit_areas(msg["action"], msg.get("area_id"), msg.get("name", ""),
                                           msg.get("icon", "💡"), msg.get("configuration"))
        conn.send_result(msg["id"], studio.data(selected))
    except (ValueError, KeyError, TypeError) as err:
        conn.send_error(msg["id"], "invalid_area", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/control", vol.Required("action"): str,
    vol.Optional("area_id"): str, vol.Optional("area_ids"): [str], vol.Optional("pack_id"): str,
    vol.Optional("scene_id"): str, vol.Optional("minutes"): int})
@websocket_api.async_response
async def ws_control(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        studio = hass.data[DOMAIN]
        results = await studio.control(msg["action"], msg.get("area_id"), msg.get("area_ids"),
                                       msg.get("pack_id", ""), msg.get("scene_id", ""), msg.get("minutes", 0))
        conn.send_result(msg["id"], {**studio.data(msg.get("area_id")), "control_results": results})
    except (ValueError, KeyError, TypeError) as err:
        conn.send_error(msg["id"], "invalid_control", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/connection", vol.Required("connection"): dict})
@websocket_api.async_response
async def ws_connection(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    from .config_flow import validate_connection
    try:
        studio = hass.data[DOMAIN]
        if studio.running or studio.preview_tasks:
            raise ValueError("Bitte zuerst Show bzw. Vorschau beenden")
        values = validate_connection(hass, msg["connection"])
        entry = next(iter(hass.config_entries.async_entries(DOMAIN)))
        hass.config_entries.async_update_entry(entry, options=values)
        conn.send_result(msg["id"], {"saved": True, "connection": values})
    except ValueError as err:
        labels = {"mqtt_not_configured": "Bitte zuerst die MQTT-Integration in Home Assistant einrichten",
                  "invalid_topic": "Gültiges MQTT-Basisthema ohne + oder # eingeben"}
        conn.send_error(msg["id"], "connection_error", labels.get(str(err), str(err)))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/start", vol.Required("pack_id"): str, vol.Required("scene_id"): str, vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_start(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].start(msg["pack_id"], msg["scene_id"], msg.get("area_id"))
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_scene", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/start_program", vol.Required("pack_id"): str, vol.Required("program_id"): str, vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_program(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].start_program(msg["pack_id"], msg["program_id"], msg.get("area_id"))
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_program", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/stop", vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_stop(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].stop(area_id=msg.get("area_id"))
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_area", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/preview", vol.Required("pack_id"): str,
                                 vol.Required("scene_id"): str, vol.Required("entity_id"): cv.entity_id, vol.Optional("area_id"): str})
@websocket_api.async_response
async def ws_preview(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].preview(msg["pack_id"], msg["scene_id"], msg["entity_id"], msg.get("area_id"))
        conn.send_result(msg["id"], hass.data[DOMAIN].data(msg.get("area_id")))
    except ValueError as err:
        conn.send_error(msg["id"], "preview_error", str(err))
