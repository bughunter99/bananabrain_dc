from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvT_3hatchlurker"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "zerg_standard",
        "expand_priority": "natural_fast",
        "defensive_anchor": "natural_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Spawning_Pool"},
        {"type": "build_structure", "building_type": "Hatchery"},
        {"type": "build_structure", "building_type": "Hatchery"},
        {"type": "build_structure", "building_type": "Extractor"},
        {"type": "build_structure", "building_type": "Lair"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    requests = [dict(req) for req in result["build_requests"]]

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # 3해처리 럴커 vs 테란
    if supply >= 20:
        requests.append({"type": "build_structure", "building_type": "Hydralisk_Den"})
    if supply >= 24:
        requests.append({"type": "research_tech", "tech_type": "Lurker_Aspect"})
        requests.append({"type": "research_upgrade", "upgrade_type": "Muscular_Augments"})
    if supply >= 30:
        result["mode"] = "Main HydraLurker"
    else:
        result["mode"] = "Opening (Lurker)"

    result["build_requests"] = requests
    return result
