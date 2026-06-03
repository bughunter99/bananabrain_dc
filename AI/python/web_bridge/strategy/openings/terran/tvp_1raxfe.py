from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvP_1raxfe"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_standard",
        "expand_priority": "natural_fast",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Supply_Depot"},
        {"type": "build_structure", "building_type": "Barracks"},
        {"type": "build_structure", "building_type": "Command_Center"},
        {"type": "build_structure", "building_type": "Refinery"},
        {"type": "build_structure", "building_type": "Factory"},
        {"type": "build_structure", "building_type": "Machine_Shop"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(req) for req in result["build_requests"]]

    enemy_opening = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # 빠른 확장 감지: 프로토스 2게이트 이상이면 수비 전환
    if "proxy" in enemy_opening or "4gate" in enemy_opening:
        result["mode"] = "Defend proxy"
        requests.append({"type": "build_structure", "building_type": "Bunker"})
        return result

    # 1Rax FE vs Protoss: Depot→Rax→CC expand→Refinery→Factory→MachineShop
    if supply >= 18:
        requests.append({"type": "research_tech", "tech_type": "Spider_Mines"})
    if supply >= 22:
        requests.append({"type": "build_structure", "building_type": "Starport"})
        requests.append({"type": "build_structure", "building_type": "Control_Tower"})
    if supply >= 28:
        requests.append({"type": "build_structure", "building_type": "Armory"})
        requests.append({"type": "build_structure", "building_type": "Factory"})
        result["mode"] = "Main Mech"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
