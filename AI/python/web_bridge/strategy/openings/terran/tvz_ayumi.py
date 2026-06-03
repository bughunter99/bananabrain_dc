from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "TvZ_ayumi"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "terran_bio",
        "expand_priority": "natural_fast",
        "wall_policy": "none",
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

    if "4_5pool" in enemy_opening:
        result["mode"] = "Defend Fast Pool"
        return result

    # Ayumi: 1랙 빠른 확장 → 4랙 바이오 마린+메딕 대규모 공격
    # 10: Rax1, 14: Depot2, 20: expand(CC), 29: Rax2~4, 35: Refinery, 38: Academy, 52: Stim
    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Command_Center"})
    if supply >= 29:
        requests.append({"type": "build_structure", "building_type": "Barracks"})
        requests.append({"type": "build_structure", "building_type": "Barracks"})
        requests.append({"type": "build_structure", "building_type": "Barracks"})
    if supply >= 35:
        requests.append({"type": "build_structure", "building_type": "Refinery"})
    if supply >= 38:
        requests.append({"type": "build_structure", "building_type": "Academy"})
    if supply >= 52:
        requests.append({"type": "research_tech", "tech_type": "Stim_Packs"})
        result["mode"] = "Main Bio"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
