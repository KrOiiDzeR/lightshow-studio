"""Area configuration, validation and migration, without Home Assistant imports."""
from __future__ import annotations

import copy
from .settings import KEY_RE, check_settings, defaults


def area_configuration(data: dict | None) -> dict:
    """Keep existing v2 content as the first independently controlled area."""
    if data is None:
        data = defaults()
    if not isinstance(data, dict):
        raise ValueError("Ungültige Bereichskonfiguration")
    if data.get("schema") == 2:
        data = {"schema": 3, "areas": [{"id": "main", "name": "Mein Bereich", "icon": "💡", "settings": data}]}
    if data.get("schema") != 3 or not isinstance(data.get("areas"), list) or not 1 <= len(data["areas"]) <= 30:
        raise ValueError("1 bis 30 Bereiche erlaubt")
    ids, owners = set(), {}
    checked = []
    for area in data["areas"]:
        if not isinstance(area, dict) or not isinstance(area.get("id"), str) or not KEY_RE.fullmatch(area["id"]) or area["id"] in ids:
            raise ValueError("Ungültige oder doppelte Bereichs-ID")
        ids.add(area["id"])
        if not isinstance(area.get("name"), str) or not 1 <= len(area["name"].strip()) <= 70:
            raise ValueError("Bereich braucht einen Namen mit maximal 70 Zeichen")
        if not isinstance(area.get("icon"), str) or not 1 <= len(area["icon"]) <= 12:
            raise ValueError("Bereichssymbol ungültig")
        settings = check_settings(area.get("settings"))
        for fixture in settings["fixtures"]:
            entity = fixture["entity_id"]
            if entity in owners:
                raise ValueError(f"{entity} ist bereits dem Bereich {owners[entity]} zugeordnet. Eine Lampe darf nur einen Bereich steuern.")
            owners[entity] = area["name"].strip()
        checked.append({"id": area["id"], "name": area["name"].strip(), "icon": area["icon"], "settings": settings})
    return {"schema": 3, "areas": copy.deepcopy(checked)}
