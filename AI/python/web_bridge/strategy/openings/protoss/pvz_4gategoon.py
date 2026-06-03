from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvZ_4gategoon"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_standard",
        "expand_priority": "none",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Pylon"},
        {"type": "build_structure", "building_type": "Gateway"},
        {"type": "build_structure", "building_type": "Assimilator"},
        {"type": "build_structure", "building_type": "Cybernetics_Core"},
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
        result["mode"] = "Defend fast pool"
        return result

    # 4게이트 드래군: 게이트 4개 + 드래군 러시
    # CCore 완성 → Singularity Charge → Gateway 2,3,4 → 드래군 공격
    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 2nd
        requests.append({"type": "research_upgrade", "upgrade_type": "Singularity_Charge"})
    if supply >= 26:
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 3rd
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 4th
        result["mode"] = "Main"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
