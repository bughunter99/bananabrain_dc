from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvT_10_15gate"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_expand",
        "expand_priority": "natural",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "main_ramp",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'build_structure', 'building_type': 'Cybernetics_Core'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'upgrade', 'upgrade_type': 'Singularity_Charge'},
        {'type': 'train_unit', 'unit_type': 'Dragoon'},
        {'type': 'build_structure', 'building_type': 'Nexus'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if ("proxy_rax" in enemy or "bbs" in enemy or "2rax" in enemy):
        result["mode"] = "Main"; return result
    if supply >= 29:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
