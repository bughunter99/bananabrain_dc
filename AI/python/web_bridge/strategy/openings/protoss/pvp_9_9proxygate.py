from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvP_9_9proxygate"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_proxy",
        "wall_policy": "none",
        "proxy_policy": "9_9_proxy",
        "defensive_anchor": "enemy_natural",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'train_unit', 'unit_type': 'Zealot'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if "4_5pool" in enemy:
        result["mode"] = "Defend fast pool"; return result
    if supply >= 11:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
