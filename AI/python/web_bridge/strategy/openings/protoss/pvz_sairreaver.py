from __future__ import annotations
from typing import Any, Dict


OPENING_NAME = "PvZ_sairreaver"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "protoss_forge_expand",
        "wall_policy": "forge_expand_wall",
        "proxy_policy": "none",
        "defensive_anchor": "natural",
    },
    "build_requests": [
        {'type': 'build_structure', 'building_type': 'Pylon'},
        {'type': 'build_structure', 'building_type': 'Gateway'},
        {'type': 'build_structure', 'building_type': 'Forge'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'build_structure', 'building_type': 'Photon_Cannon'},
        {'type': 'build_structure', 'building_type': 'Nexus'},
        {'type': 'build_structure', 'building_type': 'Cybernetics_Core'},
        {'type': 'build_structure', 'building_type': 'Assimilator'},
        {'type': 'build_structure', 'building_type': 'Stargate'},
        {'type': 'train_unit', 'unit_type': 'Corsair'},
        {'type': 'build_structure', 'building_type': 'Robotics_Facility'},
        {'type': 'build_structure', 'building_type': 'Robotics_Support_Bay'},
        {'type': 'train_unit', 'unit_type': 'Shuttle'},
        {'type': 'train_unit', 'unit_type': 'Reaver'},
        {'type': 'upgrade', 'upgrade_type': 'Air_Weapons'},
        {'type': 'upgrade', 'upgrade_type': 'Gravitic_Drive'},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    placement = dict(result["placement"])
    requests = [dict(r) for r in result["build_requests"]]
    enemy = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = (int(state.get("supply_used") or payload.get("supply_used") or 0) + 1) // 2
    if ("4_5pool" in enemy or "9pool" in enemy or "9pool_speed" in enemy):
        result["mode"] = "Defend fast pool"; return result
    if supply >= 35:
        result["mode"] = "Main"
    result["placement"] = placement
    result["build_requests"] = requests
    return result
