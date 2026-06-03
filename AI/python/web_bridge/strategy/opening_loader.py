from __future__ import annotations

import importlib
from pathlib import Path
import re
from functools import lru_cache
from typing import Any, Dict


def _slugify_opening(opening_name: str) -> str:
    normalized = opening_name.strip().lower()
    normalized = normalized.replace("/", "_").replace(".", "_").replace("-", "_")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unknown_opening"


@lru_cache(maxsize=512)
def _import_opening_module(race_key: str, opening_name: str):
    if not race_key or not opening_name:
        return None
    module_name = f"strategy.openings.{race_key}.{_slugify_opening(opening_name)}"
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def load_opening_profile(race_key: str, opening_name: str, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    module = _import_opening_module(race_key, opening_name)
    if module is None:
        return {}

    provider = getattr(module, "get_profile", None)
    if callable(provider):
        try:
            data = provider(state or {}, payload or {})
            if isinstance(data, dict):
                return data
        except Exception:
            return {}

    profile = getattr(module, "PROFILE", None)
    if isinstance(profile, dict):
        return dict(profile)

    return {}


def reload_opening_modules() -> None:
    _import_opening_module.cache_clear()
    opening_catalog.cache_clear()


def _display_opening_name(file_stem: str) -> str:
    name = file_stem.upper()
    parts = name.split("_")
    if len(parts) >= 3 and parts[0] in {"PVT", "PVZ", "PVP", "PVU", "TVT", "TVP", "TVZ", "TVU", "ZVZ", "ZVT", "ZVP", "ZVU"}:
        return f"{parts[0][:2]}{parts[0][2]}_" + "_".join(parts[1:])
    return file_stem


@lru_cache(maxsize=1)
def opening_catalog() -> Dict[str, Any]:
    base = Path(__file__).resolve().parent / "openings"
    race_map = {
        "protoss": "Protoss",
        "terran": "Terran",
        "zerg": "Zerg",
    }
    template_marker = "Edit this opening profile to customize behavior for this specific opening."

    catalog: Dict[str, Any] = {
        "races": {},
        "summary": {"total": 0, "implemented": 0, "template": 0},
    }

    for race_key, race_name in race_map.items():
        race_dir = base / race_key
        items = []
        if race_dir.exists():
            for path in sorted(race_dir.glob("*.py")):
                if path.name == "__init__.py":
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                is_template = template_marker in text
                item = {
                    "opening": _display_opening_name(path.stem),
                    "race": race_name,
                    "module": f"strategy.openings.{race_key}.{path.stem}",
                    "relative_file": f"strategy/openings/{race_key}/{path.name}",
                    "file": str(path),
                    "implemented": not is_template,
                }
                items.append(item)
                catalog["summary"]["total"] += 1
                if is_template:
                    catalog["summary"]["template"] += 1
                else:
                    catalog["summary"]["implemented"] += 1
        catalog["races"][race_name] = items

    return catalog
