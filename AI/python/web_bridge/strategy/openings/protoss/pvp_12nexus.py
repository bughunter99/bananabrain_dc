from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvP_12nexus"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_expand",
        "expand_priority": "natural_fast",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Nexus'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'train_unit', 'unit_type': 'Zealot'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'build_structure', 'building_type': 'Cybernetics_Core'},
        {'type': 'build_structure', 'building_type': 'Forge'},
        {'type': 'build_structure', 'building_type': 'Photon_Cannon'},
        {'type': 'build_structure', 'building_type': 'Photon_Cannon'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if "proxy_gate" in enemy:
        result["mode"] = "Defend proxy gate"; return result
    if "cannon_rush" in enemy:
        result["mode"] = "Defend cannon rush"; return result
    if supply >= 30:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
