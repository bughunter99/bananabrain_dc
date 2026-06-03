from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvZ_fantasy"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_mech",
        "expand_priority": "natural",
        "wall_policy": "tvz_wall",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Supply_Depot"},
        {"type": "build_structure", "building_type": "Barracks"},
        {"type": "build_structure", "building_type": "Refinery"},
        {"type": "build_structure", "building_type": "Factory"},
        {"type": "build_structure", "building_type": "Machine_Shop"},
        {"type": "build_structure", "building_type": "Starport"},
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
        return result

    # Fantasy: 1팩 메카닉 → Spider Mines → Expand → Dropship + Vulture
    # 9: Depot, 11: Barracks, 12: Refinery, Factory → MachineShop → Starport
    if supply >= 14:
        requests.append({"type": "research_tech", "tech_type": "Spider_Mines"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Ion_Thrusters"})
    if supply >= 18:
        requests.append({"type": "build_structure", "building_type": "Command_Center"})  # natural expand
        requests.append({"type": "build_structure", "building_type": "Control_Tower"})
    if supply >= 24:
        requests.append({"type": "build_structure", "building_type": "Armory"})
        requests.append({"type": "build_structure", "building_type": "Factory"})
        result["mode"] = "Main Mech"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
