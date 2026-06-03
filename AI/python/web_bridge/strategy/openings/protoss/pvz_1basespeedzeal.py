from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvZ_1basespeedzeal"

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

    # supply 기반 빌드 진행
    # 10: Gateway  12: Assimilator  13+: Zealot x1  16: Pylon2  20: CCore
    # 27: Citadel → Leg Enhancements  29: Gateway2  31: Pylon4 + LegUpgrade
    # 37: Pylon5 + Templar_Archives  attack at 8 zealots
    if supply >= 27:
        requests.append({"type": "build_structure", "building_type": "Citadel_of_Adun"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Leg_Enhancements"})
    if supply >= 29:
        requests.append({"type": "build_structure", "building_type": "Gateway"})  # 2nd gate
    if supply >= 37:
        requests.append({"type": "build_structure", "building_type": "Templar_Archives"})
        result["mode"] = "Main"
    elif supply >= 27:
        result["mode"] = "Opening"
    else:
        result["mode"] = "Opening"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
