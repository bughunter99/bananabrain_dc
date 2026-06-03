from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvZ_sparks"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_bio",
        "expand_priority": "none",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Supply_Depot"},
        {"type": "build_structure", "building_type": "Barracks"},
        {"type": "build_structure", "building_type": "Barracks"},
        {"type": "build_structure", "building_type": "Refinery"},
        {"type": "build_structure", "building_type": "Academy"},
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

    # Sparks: 2랙 바이오 → Stim + Engineer Bay → 공격
    # 9: Depot, 11: Rax1, 13: Rax2, 15: Depot2, 20: Refinery, 24: Academy
    if supply >= 24:
        requests.append({"type": "research_tech", "tech_type": "Stim_Packs"})
        requests.append({"type": "build_structure", "building_type": "Barracks"})  # 3rd
        requests.append({"type": "build_structure", "building_type": "Engineering_Bay"})
    if supply >= 27:
        requests.append({"type": "research_upgrade", "upgrade_type": "Terran_Infantry_Weapons"})
    if supply >= 30:
        result["mode"] = "Main Bio"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
