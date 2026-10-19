"""Runtime controls and local-time weekly scheduling, independent of HA."""
from __future__ import annotations

import copy
from datetime import datetime


def validate_weekly(rows: list, packs: list) -> None:
    from .settings import KEY_RE, TIME_RE
    if not isinstance(rows, list) or len(rows) > 50:
        raise ValueError("Maximal 50 Wochenzeiten")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not KEY_RE.fullmatch(row["id"]) or row["id"] in seen:
            raise ValueError("Ungültige oder doppelte Wochenzeit-ID")
        seen.add(row["id"])
        if type(row.get("enabled")) is not bool:
            raise ValueError("Wochenzeit: Aktivierung ungültig")
        days = row.get("days")
        if not isinstance(days, list) or not days or any(type(day) is not int or day not in range(7) for day in days) or len(set(days)) != len(days):
            raise ValueError("Wochenzeit: Wochentage auswählen")
        start, end = row.get("start"), row.get("end")
        if not isinstance(start, str) or not TIME_RE.fullmatch(start) or not isinstance(end, str) or not TIME_RE.fullmatch(end) or start >= end:
            raise ValueError("Wochenzeit muss am gleichen Tag enden")
        pack = next((p for p in packs if p["id"] == row.get("pack_id")), None)
        if pack is None or row.get("scene_id") not in {s["id"] for s in pack["scenes"]} or row.get("program_id", "") not in {"", *(p["id"] for p in pack.get("programs", []))}:
            raise ValueError("Wochenzeit verweist auf unbekannte Show")
    active = [row for row in rows if row["enabled"]]
    for i, row in enumerate(active):
        for other in active[i+1:]:
            if set(row["days"]) & set(other["days"]) and row["start"] < other["end"] and other["start"] < row["end"]:
                raise ValueError("Aktive Wochenzeiten überschneiden sich")


def scheduled_target(settings: dict, now: datetime) -> tuple | None:
    """Annual events take precedence over weekly entries. Windows exclude the end."""
    clock = now.strftime("%H:%M")
    for pack in settings["packs"]:
        row = pack["schedule"]
        if row["enabled"] and (row["month"], row["day"]) == (now.month, now.day) and row["start"] <= clock < row["end"]:
            return ("annual:"+pack["id"], pack["id"], row["scene_id"], row.get("program_id", ""))
    for row in settings.get("weekly", []):
        if row["enabled"] and now.weekday() in row["days"] and row["start"] <= clock < row["end"]:
            return ("weekly:"+row["id"], row["pack_id"], row["scene_id"], row.get("program_id", ""))
    return None


def operation_settings(current: dict, changes: dict) -> dict:
    """Allowlist dashboard edits, merged into the latest configuration."""
    from .settings import check_settings
    if not isinstance(changes, dict) or set(changes) - {"options", "schedules", "weekly"}:
        raise ValueError("Dashboard darf nur Bedienung und Zeitpläne ändern")
    data = copy.deepcopy(current)
    if "options" in changes:
        options = changes["options"]
        if not isinstance(options, dict) or set(options) - {"shuffle", "shuffle_interval", "wind", "shuffle_no_repeat", "transition"}:
            raise ValueError("Unbekannte Bedienoption")
        data["options"].update(options)
    if "schedules" in changes:
        if not isinstance(changes["schedules"], dict):
            raise ValueError("Ungültige Zeitpläne")
        for key, schedule in changes["schedules"].items():
            pack = next((p for p in data["packs"] if p["id"] == key), None)
            if pack is None:
                raise ValueError("Unbekanntes Paket")
            pack["schedule"] = copy.deepcopy(schedule)
    if "weekly" in changes:
        data["weekly"] = copy.deepcopy(changes["weekly"])
    return check_settings(data)
