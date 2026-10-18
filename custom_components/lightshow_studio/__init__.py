"""Lightshow Studio: reusable event packs + one-time HA/Zigbee2MQTT light inventory.

Local-only. No credentials are stored. All light actions are explicitly requested,
except optional annual schedules enabled by the user. Admin-only websocket API.
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
from homeassistant.components import mqtt, websocket_api
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

DOMAIN = "lightshow_studio"
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
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
        self.running = False
        self.active_pack = ""
        self.active_scene = ""
        self.active_program = ""
        self.program_index = 0
        self.program_until = dt_util.now()
        self.run_source = "manual"
        self.snapshots: dict[str, dict] = {}
        self.native: dict[str, tuple[str, str]] = {}
        self.preview_tasks: dict[str, asyncio.Task] = {}
        self.messages: list[str] = []
        self.migrated = False
        self.manual_stop_date: str | None = None
        self.last_shuffle = dt_util.now()
        self.last_wind = dt_util.now()
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
            loaded = json.loads(message.payload)
            if not isinstance(loaded, list):
                return
            self.devices = [{
                "friendly_name": d["friendly_name"],
                "ieee_address": d.get("ieee_address", ""),
                "model": (d.get("definition") or {}).get("model", ""),
                "description": (d.get("definition") or {}).get("description", ""),
            } for d in loaded if isinstance(d, dict) and d.get("type") != "Coordinator"
               and d.get("supported", True) and isinstance(d.get("friendly_name"), str)]
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
        return {"settings": self.settings, "devices": self.devices, "suggestions": self.suggestions(),
                "migrated": self.migrated,
                "status": {"running": self.running, "pack_id": self.active_pack, "scene_id": self.active_scene, "program_id": self.active_program,
                           "source": self.run_source, "previewing": list(self.preview_tasks), "warnings": self.messages[-15:]}}

    def _fixture(self, eid: str) -> dict | None:
        return next((f for f in self.settings["fixtures"] if f["entity_id"] == eid), None)

    def _dymera(self, f: dict) -> tuple[str, str] | None:
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
        if not any(d["friendly_name"] == name for d in self.devices):
            raise ValueError("Zigbee2MQTT-Gerät nicht in der Geräteliste gefunden")
        await mqtt.async_publish(self.hass, f"zigbee2mqtt/{name}/set", json.dumps(payload), qos=0, retain=False)

    def _snapshot(self, eid: str) -> dict | None:
        st = self.hass.states.get(eid)
        if st is None or st.state in ("unavailable", "unknown"):
            return None
        props = st.attributes
        return {"state": st.state, "brightness": props.get("brightness"),
                "rgb_color": props.get("rgb_color"), "hs_color": props.get("hs_color"),
                "color_temp_kelvin": props.get("color_temp_kelvin"), "effect": props.get("effect")}

    async def _apply(self, f: dict, cue: dict) -> str | None:
        eid = f["entity_id"]
        st = self.hass.states.get(eid)
        if st is None or st.state == "unavailable":
            return f"{eid}: Entität ist nicht verfügbar"
        mode = cue["mode"]
        bright = max(1, round(cue["brightness"] * 2.54))
        native = self._dymera(f)
        if native:
            name, ep = native
            if mode == "off":
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
        if mode == "off":
            await self.hass.services.async_call("light", "turn_off", {"entity_id": eid}, blocking=True)
            return None
        kwargs = {"entity_id": eid, "brightness": bright}
        available = st.attributes.get("effect_list") or []
        color_modes = st.attributes.get("supported_color_modes") or []
        color_ok = any(x in color_modes for x in ("hs", "rgb", "xy", "rgbw", "rgbww"))
        note = None
        if mode in EFFECTS:
            if mode in available:
                kwargs["effect"] = mode
            else:
                note = f"{eid}: Effekt {mode} nicht unterstützt; stattdessen warmes Licht"
                if color_ok:
                    kwargs["rgb_color"] = RGB["warm"]
        elif color_ok:
            kwargs["rgb_color"] = mode_rgb(cue)
        else:
            note = f"{eid}: keine Farbsteuerung unterstützt; nur Helligkeit gesetzt"
        await self.hass.services.async_call("light", "turn_on", kwargs, blocking=True)
        return note

    async def _restore(self, eid: str, snapshot: dict, native: tuple[str, str] | None = None):
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
        if snapshot.get("color_temp_kelvin") is not None:
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

    async def _stop_locked(self):
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

            async def finish():
                try:
                    await asyncio.sleep(10)
                finally:
                    try:
                        await self._restore(eid, snapshot, target)
                    except Exception as err:
                        _LOGGER.warning("Preview restore for %s failed: %s", eid, err)
                    self.preview_tasks.pop(eid, None)

            self.preview_tasks[eid] = self.hass.async_create_task(finish(), f"lightshow_preview_{eid}")

    async def _cancel_previews(self):
        tasks = list(self.preview_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def tick(self):
        now = dt_util.now()
        day = now.date()
        current_time = now.strftime("%H:%M")
        today = (day.month, day.day)
        if self.running and self.run_source == "schedule":
            pack = next((p for p in self.settings["packs"] if p["id"] == self.active_pack), None)
            if pack:
                sch = pack["schedule"]
                if not (sch["enabled"] and (sch["month"], sch["day"]) == today and sch["start"] <= current_time < sch["end"]):
                    await self.stop(manual=False)
        if not self.running and self.manual_stop_date != day.isoformat():
            for pack in self.settings["packs"]:
                sch = pack["schedule"]
                if sch["enabled"] and (sch["month"], sch["day"]) == today and sch["start"] <= current_time < sch["end"]:
                    if sch.get("program_id"):
                        await self.start_program(pack["id"], sch["program_id"], source="schedule")
                    else:
                        await self.start(pack["id"], sch["scene_id"], source="schedule")
                    break
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
            pack = next(p for p in self.settings["packs"] if p["id"] == self.active_pack)
            other_ids = [sc["id"] for sc in pack["scenes"] if sc["id"] != self.active_scene]
            if other_ids:
                async with self._lock:
                    await self._change_locked(pack["id"], random.choice(other_ids))
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    studio = Studio(hass)
    await studio.load()
    hass.data[DOMAIN] = studio
    js_path = Path(__file__).parent / "static" / "lightshow-studio.js"
    await hass.http.async_register_static_paths([StaticPathConfig(f"/{DOMAIN}/lightshow-studio.js", str(js_path), False)])
    try:
        unsubscribe = await mqtt.async_subscribe(hass, "zigbee2mqtt/bridge/devices", studio.got_devices)
    except Exception as err:
        _LOGGER.warning("Zigbee2MQTT discovery not yet available: %s", err)
        unsubscribe = lambda: None

    async def periodic(_time: datetime):
        try:
            await studio.tick()
        except Exception:
            _LOGGER.exception("Lightshow scheduler error")

    cancel = async_track_time_interval(hass, periodic, timedelta(seconds=5))

    @callback
    def shutdown(_event):
        unsubscribe()
        cancel()
        for task in list(studio.preview_tasks.values()):
            task.cancel()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown)

    async def service_start(call: ServiceCall):
        await studio.start(call.data["pack_id"], call.data["scene_id"])

    async def service_stop(_call: ServiceCall):
        await studio.stop()

    hass.services.async_register(DOMAIN, "start", service_start, schema=vol.Schema({vol.Required("pack_id"): str, vol.Required("scene_id"): str}))
    async def service_program(call: ServiceCall):
        await studio.start_program(call.data["pack_id"], call.data["program_id"])

    hass.services.async_register(DOMAIN, "stop", service_stop)
    hass.services.async_register(DOMAIN, "start_program", service_program, schema=vol.Schema({vol.Required("pack_id"): str, vol.Required("program_id"): str}))
    for handler in (ws_get, ws_save, ws_start, ws_program, ws_stop, ws_preview):
        websocket_api.async_register_command(hass, handler)
    return True


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get"})
@callback
def ws_get(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    conn.send_result(msg["id"], hass.data[DOMAIN].data())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/save", vol.Required("settings"): dict})
@websocket_api.async_response
async def ws_save(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].save(msg["settings"])
        conn.send_result(msg["id"], hass.data[DOMAIN].data())
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_settings", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/start", vol.Required("pack_id"): str, vol.Required("scene_id"): str})
@websocket_api.async_response
async def ws_start(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].start(msg["pack_id"], msg["scene_id"])
        conn.send_result(msg["id"], hass.data[DOMAIN].data())
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_scene", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/start_program", vol.Required("pack_id"): str, vol.Required("program_id"): str})
@websocket_api.async_response
async def ws_program(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].start_program(msg["pack_id"], msg["program_id"])
        conn.send_result(msg["id"], hass.data[DOMAIN].data())
    except ValueError as err:
        conn.send_error(msg["id"], "invalid_program", str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/stop"})
@websocket_api.async_response
async def ws_stop(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    await hass.data[DOMAIN].stop()
    conn.send_result(msg["id"], hass.data[DOMAIN].data())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/preview", vol.Required("pack_id"): str,
                                 vol.Required("scene_id"): str, vol.Required("entity_id"): cv.entity_id})
@websocket_api.async_response
async def ws_preview(hass: HomeAssistant, conn: websocket_api.ActiveConnection, msg: dict):
    try:
        await hass.data[DOMAIN].preview(msg["pack_id"], msg["scene_id"], msg["entity_id"])
        conn.send_result(msg["id"], hass.data[DOMAIN].data())
    except ValueError as err:
        conn.send_error(msg["id"], "preview_error", str(err))
