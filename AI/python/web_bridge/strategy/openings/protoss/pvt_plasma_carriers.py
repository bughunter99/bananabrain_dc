from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvT_plasma_carriers"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_air",
        "expand_priority": "natural",
        "wall_policy": "none",
        "proxy_policy": "none",
        "map_specific": "plasma",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'build_structure', 'building_type': 'Cybernetics_Core'},
        {'type': 'build_structure', 'building_type': 'Stargate'},
        {'type': 'build_structure', 'building_type': 'Fleet_Beacon'},
        {'type': 'train_unit', 'unit_type': 'Carrier'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if supply >= 40:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
