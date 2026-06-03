from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvT_3hatchmuta"

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
        {"type": "build_structure", "building_type": "Spire"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    requests = [dict(req) for req in result["build_requests"]]

    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    # 3해처리 뮤탈: 해처리3개 + Extractor + Lair + Spire → 뮤탈 공격
    if supply >= 20:
        requests.append({"type": "research_upgrade", "upgrade_type": "Metabolic_Boost"})
    if supply >= 22:
        requests.append({"type": "train_unit", "unit_type": "Mutalisk"})
    if supply >= 30:
        result["mode"] = "Main HydraLurker"
    elif supply >= 20:
        result["mode"] = "Opening (Muta)"
    else:
        result["mode"] = "Opening"

    result["build_requests"] = requests
    return result
