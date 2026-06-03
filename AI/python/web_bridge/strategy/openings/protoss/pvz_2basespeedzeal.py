from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvZ_2basespeedzeal"

PROFILE: Dict[str, Any] = {
    "mode": "Opening (FFE)",
    "placement": {
        "plan": "protoss_ffe",
        "expand_priority": "natural_fast",
        "wall_policy": "forge_expand_wall",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Pylon"},
        {"type": "build_structure", "building_type": "Forge"},
        {"type": "build_structure", "building_type": "Nexus"},
        {"type": "build_structure", "building_type": "Gateway"},
        {"type": "build_structure", "building_type": "Assimilator"},
        {"type": "build_structure", "building_type": "Cybernetics_Core"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(req) for req in result["build_requests"]]

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # FFE 완성 후 속도질럿 진행
    # supply 24+: Pylon3, auto supply
    # supply 27+: Citadel, Gateway3, Leg Enhancements
    # 공격: 질럿 8 + Leg 업 완성 + Templar_Archives
    if supply >= 24:
        requests.append({"type": "build_structure", "building_type": "Pylon"})
    if supply >= 27:
        requests.append({"type": "build_structure", "building_type": "Citadel_of_Adun"})
        requests.append({"type": "build_structure", "building_type": "Gateway"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Leg_Enhancements"})
        requests.append({"type": "build_structure", "building_type": "Assimilator"})

    if supply >= 35:
        requests.append({"type": "build_structure", "building_type": "Templar_Archives"})
        requests.append({"type": "build_structure", "building_type": "Robotics_Facility"})
        result["mode"] = "Main"
    else:
        result["mode"] = "Opening (FFE)"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
