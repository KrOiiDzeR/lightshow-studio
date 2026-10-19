"""Extendable built-in show pack catalogue. No Home Assistant imports."""
from __future__ import annotations


def cue(mode: str, brightness: int = 70, speed: int = 55, color: str = "#FF8730") -> dict:
    return {"mode": mode, "brightness": brightness, "speed": speed, "color": color}


def scene(key: str, name: str, icon: str, upper: dict, lower: dict, entrance: dict, other: dict | None = None) -> dict:
    return {"id": key, "name": name, "icon": icon, "description": "", "tracks": {
        "upper": upper, "lower": lower, "entrance": entrance,
        "other": other if other is not None else dict(upper)}, "overrides": []}


def pack(key: str, name: str, icon: str, description: str, month: int, day: int, scenes: list[dict]) -> dict:
    return {"id": key, "name": name, "icon": icon, "description": description,
            "programs": [{"id": "tour", "name": "Komplette Lichtshow", "icon": "🎬", "steps": [
                {"scene_id": s["id"], "duration": 60} for s in scenes]}],
            "schedule": {"enabled": False, "month": month, "day": day,
                         "start": "18:00", "end": "23:00", "scene_id": scenes[0]["id"], "program_id": ""},
            "scenes": scenes}


BUILTIN_PACKS = [
    pack("halloween", "Halloween", "🎃", "Kerzen, Grusel, Gewitter und geheimnisvolle Nächte", 10, 31, [
        scene("castle", "Gruselschloss", "🏰", cue("candle", 76), cue("red", 45), cue("candle", 74)),
        scene("haunted", "Geisterhaus", "👻", cue("sparkle", 62, 42), cue("purple", 50), cue("sparkle", 62)),
        scene("storm", "Gewitternacht", "⚡", cue("blink", 85, 70), cue("off"), cue("blink", 80, 66)),
        scene("fire", "Flammenmeer", "🔥", cue("fireplace", 74), cue("fireplace", 48), cue("candle", 70)),
        scene("bloodmoon", "Blutmond", "🌕", cue("fireplace", 73), cue("red", 58), cue("candle", 68)),
    ]),
    pack("christmas", "Weihnachten", "🎄", "Warmweiße Winterabende, festliche Farben und Kerzenschein", 12, 24, [
        scene("advent", "Adventslichter", "🕯️", cue("candle", 58, 36), cue("gold", 40), cue("candle", 68)),
        scene("winter", "Wintermärchen", "❄️", cue("sparkle", 66, 33), cue("ice", 52), cue("warm", 60)),
        scene("christmas_classic", "Klassische Weihnachten", "🎁", cue("warm", 74), cue("red", 48), cue("green", 60)),
        scene("fireside", "Kaminabend", "🔥", cue("fireplace", 64, 38), cue("warm", 44), cue("candle", 62)),
    ]),
    pack("party", "Party & Geburtstag", "🎉", "Bunte Effekte für Feste und Feiern", 6, 1, [
        scene("disco", "Disco", "🪩", cue("colorloop", 83, 82), cue("colorloop", 75, 62), cue("sparkle", 71)),
        scene("confetti", "Konfetti", "🎊", cue("sparkle", 80, 66), cue("purple", 70), cue("colorloop", 70, 50)),
        scene("birthday", "Geburtstag", "🎂", cue("sunbeam", 77, 48), cue("gold", 68), cue("sparkle", 65)),
    ]),
    pack("ambience", "Ambiente & Jahreszeiten", "🌿", "Gemütliche Lichtstimmungen für jeden Tag", 1, 1, [
        scene("evening", "Gemütlicher Abend", "☕", cue("warm", 55), cue("gold", 35), cue("warm", 48)),
        scene("summer", "Sommernacht", "🌙", cue("breathe", 48, 22), cue("blue", 37), cue("warm", 42)),
        scene("relax", "Entspannung", "🧘", cue("warm", 35), cue("ice", 25), cue("warm", 30)),
    ]),
]
