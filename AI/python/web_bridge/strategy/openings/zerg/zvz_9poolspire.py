from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvZ_9poolspire"

PROFILE: Dict[str, Any] = {
    "mode": "Main ZvZ",
    "placement": {
        "plan": "zerg_macro",
        "expand_priority": "natural",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "natural_sunken",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Spawning_Pool"},
        {"type": "build_structure", "building_type": "Extractor"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(req) for req in result["build_requests"]]

    enemy_opening = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    if "4_5pool" in enemy_opening:
        result["mode"] = "Defend Fast Pool"
        placement["expand_priority"] = "main_hold"
        placement["defensive_anchor"] = "main_sunken"
        requests.append({"type": "build_structure", "building_type": "Creep_Colony"})
    else:
        result["mode"] = "Main ZvZ"

    if supply >= 11:
        requests.append({"type": "build_structure", "building_type": "Lair"})
    if supply >= 14:
        requests.append({"type": "build_structure", "building_type": "Hatchery"})
    if supply >= 16:
        requests.append({"type": "build_structure", "building_type": "Spire"})

    result["placement"] = placement
    result["build_requests"] = requests
    return result
