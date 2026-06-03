from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvT_12nexus"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_standard",
        "expand_priority": "natural_fast",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Pylon"},
        {"type": "build_structure", "building_type": "Gateway"},
        {"type": "build_structure", "building_type": "Nexus"},
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

    # 빠른 테란 러시 감지 → 1게이트 수비 전환
    if "proxy" in enemy_opening or "bbs" in enemy_opening:
        result["mode"] = "Defend proxy rax"
        requests.append({"type": "build_structure", "building_type": "Gateway"})
        return result

    # 12 넥서스: Pylon→Gate→Nexus(12)→Assimilator→CCore
    if supply >= 22:
        requests.append({"type": "build_structure", "building_type": "Robotics_Facility"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Singularity_Charge"})
    if supply >= 28:
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 2nd
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 3rd
    if supply >= 34:
        requests.append({"type": "build_structure", "building_type": "Robotics_Support_Bay"})
        result["mode"] = "Main"
    else:
        result["mode"] = "Reactive fast expand"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
