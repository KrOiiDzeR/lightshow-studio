"""UI setup and MQTT options. Show content stays in the existing Studio store."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
from .discovery import base_topic


def connection_schema(values: dict, mqtt_available: bool) -> vol.Schema:
    return vol.Schema({
        vol.Required("mqtt_mode", default=values.get("mqtt_mode", "auto" if mqtt_available else "disabled")):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=["auto", "manual", "disabled"], translation_key="mqtt_mode")),
        vol.Optional("mqtt_base_topic", default=values.get("mqtt_base_topic", "")): str,
    })


def validate_connection(hass, values: dict) -> dict:
    mode = values["mqtt_mode"]
    if mode not in {"auto", "manual", "disabled"}:
        raise ValueError("invalid_topic")
    if mode != "disabled" and not hass.config_entries.async_entries("mqtt"):
        raise ValueError("mqtt_not_configured")
    try:
        prefix = base_topic(values.get("mqtt_base_topic", "")) if mode == "manual" else ""
    except ValueError as err:
        raise ValueError("invalid_topic") from err
    return {"mqtt_mode": mode, "mqtt_base_topic": prefix}


class StudioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One Studio per Home Assistant, configured without YAML."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            try:
                values = validate_connection(self.hass, user_input)
            except ValueError as err:
                errors["base"] = str(err)
            else:
                return self.async_create_entry(title="Lightshow Studio", data=values)
        return self.async_show_form(step_id="user", data_schema=connection_schema(
            user_input or {}, bool(self.hass.config_entries.async_entries("mqtt"))), errors=errors)

    async def async_step_import(self, user_input):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        prefix = (user_input or {}).get("mqtt_base_topic", "")
        return self.async_create_entry(title="Lightshow Studio", data={
            "mqtt_mode": "manual" if prefix else "auto", "mqtt_base_topic": prefix,
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return StudioOptionsFlow()


class StudioOptionsFlow(config_entries.OptionsFlow):
    """Connection options; the registered configuration panel hosts the editors."""

    async def async_step_init(self, user_input=None):
        errors = {}
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            studio = self.hass.data.get(DOMAIN)
            if studio and (studio.running or studio.preview_tasks):
                errors["base"] = "show_running"
            else:
                try:
                    values = validate_connection(self.hass, user_input)
                except ValueError as err:
                    errors["base"] = str(err)
                else:
                    return self.async_create_entry(title="", data=values)
        return self.async_show_form(step_id="init", data_schema=connection_schema(
            user_input or values, bool(self.hass.config_entries.async_entries("mqtt"))), errors=errors)
