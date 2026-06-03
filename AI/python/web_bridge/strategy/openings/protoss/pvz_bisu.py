from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvZ_bisu"

PROFILE: Dict[str, Any] = {
    "mode": "Main",
    "placement": {
        "plan": "protoss_macro",
        "expand_priority": "natural_fast",
        "wall_policy": "forge_expand_wall",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Pylon"},
        {"type": "build_structure", "building_type": "Gateway"},
        {"type": "build_structure", "building_type": "Forge"},
        {"type": "build_structure", "building_type": "Assimilator"},
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
        result["mode"] = "Defend fast pool (FFE)"
        placement["defensive_anchor"] = "main_ramp"
        requests.append({"type": "build_structure", "building_type": "Photon_Cannon"})
    else:
        result["mode"] = "Main"

    if supply >= 31:
        requests.append({"type": "build_structure", "building_type": "Stargate"})
        requests.append({"type": "build_structure", "building_type": "Assimilator"})
    if supply >= 36:
        requests.append({"type": "build_structure", "building_type": "Citadel_of_Adun"})
    if supply >= 42:
        requests.append({"type": "build_structure", "building_type": "Templar_Archives"})

    result["placement"] = placement
    result["build_requests"] = requests
    return result
