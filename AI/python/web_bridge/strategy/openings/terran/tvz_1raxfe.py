from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvZ_1raxfe"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_macro",
        "expand_priority": "natural_fast",
        "wall_policy": "tvz_wall",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Supply_Depot"},
        {"type": "build_structure", "building_type": "Barracks"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(req) for req in result["build_requests"]]

    enemy_opening = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    if "4_5pool" in enemy_opening or "9pool" in enemy_opening:
        result["mode"] = "Defend Fast Pool"
        requests.append({"type": "build_structure", "building_type": "Bunker"})
        placement["expand_priority"] = "main_hold"
    else:
        result["mode"] = "Opening"

    if supply >= 15:
        requests.append({"type": "build_structure", "building_type": "Command_Center"})
    if supply >= 18:
        requests.append({"type": "build_structure", "building_type": "Bunker"})
    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Refinery"})
    if supply >= 24:
        requests.append({"type": "build_structure", "building_type": "Academy"})

    result["placement"] = placement
    result["build_requests"] = requests
    return result
