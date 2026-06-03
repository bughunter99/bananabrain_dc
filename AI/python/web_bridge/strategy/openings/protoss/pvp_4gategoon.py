from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvP_4gategoon"

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

    # 4게이트 드래군 vs 프로토스: 상대 DT 감지 시 오브저버 트리로
    if "dt" in enemy_opening or "dark_templar" in enemy_opening:
        requests.append({"type": "build_structure", "building_type": "Robotics_Facility"})
        result["mode"] = "Defend DT"
        return result

    if supply >= 20:
        requests.append({"type": "research_upgrade", "upgrade_type": "Singularity_Charge"})
        requests.append({"type": "build_structure", "building_type": "Gateway"})
    if supply >= 26:
        requests.append({"type": "build_structure", "building_type": "Gateway"})
        requests.append({"type": "build_structure", "building_type": "Gateway"})
        result["mode"] = "Main"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
