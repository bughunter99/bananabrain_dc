from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "PvZ_sairdt"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_standard",
        "expand_priority": "natural",
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

    # DefendFastPool: fast pool / 9pool 감지 시 방어 모드
    if "4_5pool" in enemy_opening or "9pool" in enemy_opening:
        result["mode"] = "Defend fast pool"
        placement["defensive_anchor"] = "main_ramp"
        return result

    # 빌드 순서 (supply 기반)
    # supply 8+: Pylon → scout
    # supply 10+: Gateway, Zealot 생산
    # supply 12+: Assimilator, Cybernetics Core
    # Cybernetics Core 완성 후 Main으로 전환
    result["mode"] = "Opening"

    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Stargate"})
        requests.append({"type": "build_structure", "building_type": "Citadel_of_Adun"})
        result["mode"] = "Main"

    result["placement"] = placement
    result["build_requests"] = requests
    return result
