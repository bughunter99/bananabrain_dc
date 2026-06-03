from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvT_2factvults"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_mech",
        "expand_priority": "none",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Supply_Depot"},
        {"type": "build_structure", "building_type": "Barracks"},
        {"type": "build_structure", "building_type": "Refinery"},
        {"type": "build_structure", "building_type": "Factory"},
        {"type": "build_structure", "building_type": "Machine_Shop"},
        {"type": "build_structure", "building_type": "Factory"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(req) for req in result["build_requests"]]

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # TvT 2팩 벌쳐: 팩2개 + MachineShop → Vulture + Spider Mines
    if supply >= 16:
        requests.append({"type": "research_tech", "tech_type": "Spider_Mines"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Ion_Thrusters"})
    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Machine_Shop"})  # 2nd factory addon
    if supply >= 24:
        requests.append({"type": "build_structure", "building_type": "Armory"})
        result["mode"] = "Main Mech"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
