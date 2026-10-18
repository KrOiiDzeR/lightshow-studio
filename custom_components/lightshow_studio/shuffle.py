"""Per-area shuffle selection, with backward-compatible current-pack behavior."""
from __future__ import annotations


def validate_shuffle(settings: dict) -> None:
    if "shuffle_scenes" not in settings:
        return
    rows = settings["shuffle_scenes"]
    if not isinstance(rows, list) or len(rows) > 1050:
        raise ValueError("Ungültige Shuffle-Szenenauswahl")
    available = {(p["id"], s["id"]) for p in settings["packs"] for s in p["scenes"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"pack_id", "scene_id"} or not isinstance(row["pack_id"], str) or not isinstance(row["scene_id"], str):
            raise ValueError("Shuffle-Auswahl braucht Paket- und Szenen-ID")
        key = (row["pack_id"], row["scene_id"])
        if key not in available or key in seen:
            raise ValueError("Shuffle-Auswahl enthält unbekannte oder doppelte Szene")
        seen.add(key)


def shuffle_candidates(settings: dict, pack_id: str, scene_id: str) -> list[tuple[str, str]]:
    """Never repeat the current pair immediately; an empty explicit pool stays empty."""
    if "shuffle_scenes" in settings:
        pool = [(row["pack_id"], row["scene_id"]) for row in settings["shuffle_scenes"]]
    else:
        pack = next((p for p in settings["packs"] if p["id"] == pack_id), None)
        pool = [(pack_id, s["id"]) for s in pack["scenes"]] if pack else []
    return [pair for pair in pool if pair != (pack_id, scene_id)]
