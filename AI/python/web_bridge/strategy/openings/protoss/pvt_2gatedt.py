from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvT_2gatedt"

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

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # 2게이트 DT: CCore → CitadelOfAdun → TemplarArchives → DT 2기 → 공격
    if supply >= 18:
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 2nd
        requests.append({"type": "build_structure", "building_type": "Citadel_of_Adun"})
    if supply >= 24:
        requests.append({"type": "build_structure", "building_type": "Templar_Archives"})
        result["mode"] = "Main"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
