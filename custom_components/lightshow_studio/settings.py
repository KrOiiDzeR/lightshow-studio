"""Validation, defaults and one-way import of v1; intentionally HA-independent."""
from __future__ import annotations
import copy
from datetime import date
import re
from .catalog import BUILTIN_PACKS, cue

ROLES = ("upper", "lower", "entrance", "other")
ENDPOINTS = ("auto", "top", "bottom")
EFFECTS = {"candle", "fireplace", "sparkle", "breathe", "blink", "colorloop", "sunset", "sunrise", "opal", "glisten", "underwater", "cosmos", "sunbeam", "enchant"}
COLORS = {"red", "purple", "green", "warm", "blue", "gold", "ice", "white", "custom_color"}
MODES = EFFECTS | COLORS | {"off"}
ENTITY_RE = re.compile(r"^light\.[a-z0-9_]+$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
HEX_RE = re.compile(r"^#[a-fA-F0-9]{6}$")

def role_for(entity_id: str) -> str:
    return "upper" if entity_id.endswith("_top") else "lower" if entity_id.endswith("_bottom") else "entrance" if entity_id.endswith(("_entrance", "_door", "_haustur")) else "other"


def fixture(entity_id: str, *, role: str | None = None, friendly_name: str = "", endpoint: str | None = None, transport: str = "auto") -> dict:
    return {"entity_id": entity_id, "role": role or role_for(entity_id), "friendly_name": friendly_name,
            "endpoint": endpoint or ("top" if entity_id.endswith("_top") else "bottom" if entity_id.endswith("_bottom") else "auto"), "enabled": True, "transport": transport}


def defaults() -> dict:
    return {"schema": 2,
            "fixtures": [],
            "packs": copy.deepcopy(BUILTIN_PACKS),
            "options": {"shuffle": False, "shuffle_interval": 180, "wind": False}}


def check_cue(obj: dict) -> None:
    if not isinstance(obj, dict) or obj.get("mode") not in MODES:
        raise ValueError("Unbekannter Lichteffekt")
    for prop in ("brightness", "speed"):
        v = obj.get(prop)
        if type(v) is not int or not 0 <= v <= 100:
            raise ValueError(f"{prop}: Wert von 0 bis 100 erforderlich")
    if not isinstance(obj.get("color"), str) or not HEX_RE.fullmatch(obj["color"]):
        raise ValueError("Farbwert muss #RRGGBB sein")


def validate_pack(p: dict) -> dict:
    if not isinstance(p, dict):
        raise ValueError("Ungültiges Show-Paket")
    if not isinstance(p.get("id"), str) or not KEY_RE.fullmatch(p["id"]):
        raise ValueError("Paket-ID: nur Kleinbuchstaben, Ziffern und _")
    for k, mx in (("name", 70), ("icon", 12), ("description", 250)):
        if not isinstance(p.get(k), str) or len(p[k]) > mx or (k == "name" and not p[k].strip()):
            raise ValueError(f"Paketfeld {k} ungültig")
    scenes = p.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 35:
        raise ValueError("Ein Paket braucht 1 bis 35 Szenen")
    ids: set[str] = set()
    for sc in scenes:
        if not isinstance(sc, dict) or not isinstance(sc.get("id"), str) or not KEY_RE.fullmatch(sc["id"]) or sc["id"] in ids:
            raise ValueError("Ungültige oder doppelte Szenen-ID")
        ids.add(sc["id"])
        for k, mx in (("name", 70), ("icon", 12), ("description", 250)):
            if not isinstance(sc.get(k), str) or len(sc[k]) > mx or (k == "name" and not sc[k].strip()):
                raise ValueError(f"Szenenfeld {k} ungültig")
        tracks = sc.get("tracks")
        if not isinstance(tracks, dict) or set(tracks) != set(ROLES):
            raise ValueError("Szene muss die Gruppen oben, unten, Haustür, andere enthalten")
        for track in tracks.values():
            check_cue(track)
        overrides = sc.get("overrides")
        if not isinstance(overrides, list) or len(overrides) > 150:
            raise ValueError("Ungültige Einzelzuweisungen")
        seen: set[str] = set()
        for ov in overrides:
            if not isinstance(ov, dict) or not isinstance(ov.get("entity_id"), str) or not ENTITY_RE.fullmatch(ov["entity_id"]):
                raise ValueError("Überschreibung enthält ungültige Leuchte")
            if ov["entity_id"] in seen:
                raise ValueError("Doppelte Einzelzuweisung")
            seen.add(ov["entity_id"])
            check_cue(ov)
    programs = p.get("programs", [])
    if not isinstance(programs, list) or len(programs) > 20:
        raise ValueError("Maximal 20 Show-Abläufe")
    program_ids: set[str] = set()
    for prog in programs:
        if not isinstance(prog, dict) or not isinstance(prog.get("id"), str) or not KEY_RE.fullmatch(prog["id"]) or prog["id"] in program_ids:
            raise ValueError("Ungültige oder doppelte Ablauf-ID")
        program_ids.add(prog["id"])
        if not isinstance(prog.get("name"), str) or not 1 <= len(prog["name"].strip()) <= 70 or not isinstance(prog.get("icon"), str) or len(prog["icon"]) > 12:
            raise ValueError("Ungültiger Ablaufname oder Symbol")
        steps = prog.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= 50:
            raise ValueError("Ein Ablauf braucht 1 bis 50 Schritte")
        for step in steps:
            if not isinstance(step, dict) or step.get("scene_id") not in ids or type(step.get("duration")) is not int or not 10 <= step["duration"] <= 3600:
                raise ValueError("Ablauf: Szene oder Dauer ungültig (10-3600 Sekunden)")
    sch = p.get("schedule")
    if not isinstance(sch, dict) or type(sch.get("enabled")) is not bool:
        raise ValueError("Ungültige Zeitplan-Einstellung")
    month, day = sch.get("month"), sch.get("day")
    if type(month) is not int or type(day) is not int:
        raise ValueError("Ungültiges Datum")
    try:
        date(2024, month, day)  # leap year allows 29 February recurring dates
    except ValueError as err:
        raise ValueError("Ungültiges Datum") from err
    start, end = sch.get("start"), sch.get("end")
    if not isinstance(start, str) or not TIME_RE.fullmatch(start) or not isinstance(end, str) or not TIME_RE.fullmatch(end) or start >= end:
        raise ValueError("Zeitfenster muss am gleichen Tag liegen")
    if sch.get("scene_id") not in ids:
        raise ValueError("Zeitplan verweist auf unbekannte Szene")
    if sch.get("program_id", "") not in ("", *program_ids):
        raise ValueError("Zeitplan verweist auf unbekannten Show-Ablauf")
    return copy.deepcopy(p)


def check_settings(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != 2:
        raise ValueError("Unbekannte Konfigurationsversion")
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) > 150:
        raise ValueError("Maximal 150 Lampen")
    seen: set[str] = set()
    for f in fixtures:
        if not isinstance(f, dict) or not isinstance(f.get("entity_id"), str) or not ENTITY_RE.fullmatch(f["entity_id"]) or f["entity_id"] in seen:
            raise ValueError("Ungültige oder doppelte light.* Entität")
        seen.add(f["entity_id"])
        if f.get("role") not in ROLES or f.get("endpoint") not in ENDPOINTS or type(f.get("enabled")) is not bool:
            raise ValueError("Leuchtengruppe/Endpunkt ungültig")
        if not isinstance(f.get("friendly_name"), str) or len(f["friendly_name"]) > 150:
            raise ValueError("Ungültiger Zigbee2MQTT-Gerätename")
        if f.get("transport", "auto") not in ("auto", "homeassistant", "zigbee2mqtt"):
            raise ValueError("Unbekannte Lampenanbindung")
    packs = data.get("packs")
    if not isinstance(packs, list) or not 1 <= len(packs) <= 30:
        raise ValueError("1 bis 30 Pakete erlaubt")
    ids: set[str] = set()
    active_schedules = []
    for p in packs:
        validate_pack(p)
        if p["id"] in ids:
            raise ValueError("Doppelte Paket-ID")
        ids.add(p["id"])
        sch = p["schedule"]
        if sch["enabled"]:
            active_schedules.append((p["name"], sch))
        for sc in p["scenes"]:
            if any(ov["entity_id"] not in seen for ov in sc["overrides"]):
                raise ValueError("Einzelzuweisung verweist auf nicht eingerichtete Lampe")
    for i, (name, s) in enumerate(active_schedules):
        for other_name, other in active_schedules[i+1:]:
            if (s["month"], s["day"]) == (other["month"], other["day"]) and s["start"] < other["end"] and other["start"] < s["end"]:
                raise ValueError(f"Zeitpläne überschneiden sich: {name} / {other_name}")
    opts = data.get("options")
    if not isinstance(opts, dict) or type(opts.get("shuffle")) is not bool or type(opts.get("wind")) is not bool:
        raise ValueError("Optionen ungültig")
    interval = opts.get("shuffle_interval")
    if type(interval) is not int or not 60 <= interval <= 3600:
        raise ValueError("Szenenwechsel: 60 bis 3600 Sekunden")
    if type(opts.get("shuffle_no_repeat", True)) is not bool:
        raise ValueError("Shuffle-Rundenoption ungültig")
    if type(opts.get("transition", 0)) is not int or not 0 <= opts.get("transition", 0) <= 30:
        raise ValueError("Übergang: 0 bis 30 Sekunden")
    from .planning import validate_weekly
    validate_weekly(data.get("weekly", []), packs)
    from .shuffle import validate_shuffle
    validate_shuffle(data)
    if "favorites" in data:
        validate_shuffle({**data, "shuffle_scenes": data["favorites"]})
    return copy.deepcopy(data)


def migrate_v1(old: dict) -> dict:
    """Convert old halloween_control_center storage to one reusable show pack."""
    fresh = defaults()
    fixtures = {f["entity_id"]: f for f in fresh["fixtures"]}
    scenes: list[dict] = []
    for sc in old.get("scenes", []):
        if not isinstance(sc, dict):
            continue
        tracks = {role: cue("off") for role in ROLES}
        overrides = []
        for r in sc.get("lights", []):
            eid = r.get("entity_id", "")
            if not ENTITY_RE.fullmatch(eid) or r.get("mode") not in MODES:
                continue
            if eid not in fixtures:
                fixtures[eid] = fixture(eid)
            f = fixtures[eid]
            if r.get("friendly_name"):
                f["friendly_name"] = r["friendly_name"]
            if r.get("endpoint") in ENDPOINTS:
                f["endpoint"] = r["endpoint"]
            overrides.append({"entity_id": eid, **cue(r["mode"], r.get("brightness", 65), r.get("speed", 55))})
        scenes.append({"id": sc.get("id", ""), "name": sc.get("name", ""), "icon": sc.get("emoji", "🎃"),
                       "description": "Aus Halloween Control Center v1 übernommen", "tracks": tracks, "overrides": overrides})
    if scenes:
        fresh["packs"][0]["scenes"] = scenes
        fresh["packs"][0]["programs"] = []  # Originale Halloween-Szenen erhalten
        sched = old.get("schedule", {})
        fresh["packs"][0]["schedule"].update({"enabled": bool(sched.get("enabled", False)),
            "start": sched.get("start", "18:00"), "end": sched.get("end", "23:00"),
            "scene_id": sched.get("scene_id", scenes[0]["id"])})
    fresh["fixtures"] = list(fixtures.values())
    fresh["options"] = {"shuffle": bool(old.get("shuffle_enabled", False)),
                        "shuffle_interval": old.get("shuffle_interval", 180), "wind": bool(old.get("wind_enabled", False))}
    return check_settings(fresh)
