from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvP_2gatedtexpo"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_expand",
        "expand_priority": "natural",
        "wall_policy": "none",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'train_unit', 'unit_type': 'Zealot'},
        {'type': 'build_structure', 'building_type': 'Cybernetics_Core'},
        {'type': 'build_structure', 'building_type': 'Citadel_of_Adun'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Templar_Archives'},
        {'type': 'train_unit', 'unit_type': 'Dark_Templar'},
        {'type': 'build_structure', 'building_type': 'Forge'},
        {'type': 'build_structure', 'building_type': 'Nexus'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if ("forge_fast" in enemy or "fast_expand" in enemy):
        result["mode"] = "Reactive fast expand"; return result
    if "proxy_gate" in enemy:
        result["mode"] = "Defend proxy gate"; return result
    if "cannon_rush" in enemy:
        result["mode"] = "Defend cannon rush"; return result
    if supply >= 29:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
