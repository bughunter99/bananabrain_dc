from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvP_2hatchmuta"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "zerg_standard",
        "expand_priority": "natural",
        "defensive_anchor": "natural_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Spawning_Pool"},
        {"type": "build_structure", "building_type": "Hatchery"},
        {"type": "build_structure", "building_type": "Extractor"},
        {"type": "build_structure", "building_type": "Lair"},
        {"type": "build_structure", "building_type": "Spire"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    requests = [dict(req) for req in result["build_requests"]]

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # 2해처리 뮤탈 vs 프로토스: 빠른 뮤탈 러시
    if supply >= 18:
        requests.append({"type": "train_unit", "unit_type": "Mutalisk"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Metabolic_Boost"})
    if supply >= 24:
        result["mode"] = "Main ZvP"
    else:
        result["mode"] = "Opening (Muta)"

    result["build_requests"] = requests
    return result
