from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvZ_9gas10pool"

PROFILE: Dict[str, Any] = {
    "mode": "Opening",
    "placement": {
        "plan": "zerg_standard",
        "expand_priority": "natural",
        "defensive_anchor": "natural_ramp",
    },
    "build_requests": [
        {"type": "build_structure", "building_type": "Extractor"},
        {"type": "build_structure", "building_type": "Spawning_Pool"},
    ],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(PROFILE)
    requests = [dict(req) for req in result["build_requests"]]

    enemy_opening = str(state.get("enemy_opening") or payload.get("enemy_opening") or "").lower()
    supply = int(state.get("supply_used") or payload.get("supply_used") or 0)
    supply = (supply + 1) // 2

    if "4_5pool" in enemy_opening:
        result["mode"] = "Defend Fast Pool"
        return result

    # 9가스 10풀: Extractor(9)→Pool(10)→Lair(12)→Hatchery2→Spire
    if supply >= 12:
        requests.append({"type": "build_structure", "building_type": "Lair"})
        requests.append({"type": "build_structure", "building_type": "Hatchery"})
    if supply >= 14:
        requests.append({"type": "build_structure", "building_type": "Spire"})
    if supply >= 17:
        requests.append({"type": "train_unit", "unit_type": "Mutalisk"})
    if supply >= 24:
        result["mode"] = "Main ZvZ"
    else:
        result["mode"] = "Opening"

    result["build_requests"] = requests
    return result
