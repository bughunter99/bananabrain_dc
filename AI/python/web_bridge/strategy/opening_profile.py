from __future__ import annotations

from typing import Any, Dict, List

from .opening_loader import load_opening_profile


class OpeningProfileMixin:
    """Shared helpers for opening-driven mode, placement and build decisions."""

    opening_profiles: Dict[str, Dict[str, Any]] = {}
    race_key: str = ""

    def _profile(self) -> Dict[str, Any]:
        base_profile = self.opening_profiles.get(self._opening, {})
        dynamic_profile = load_opening_profile(self.race_key, self._opening, self.state, self.payload)
        if not dynamic_profile:
            return dict(base_profile)

        merged: Dict[str, Any] = dict(base_profile)
        for key, value in dynamic_profile.items():
            merged[key] = value
        return merged

    def _profile_build_requests(self) -> List[Dict[str, Any]]:
        profile = self._profile()
        requests = profile.get("build_requests")
        if isinstance(requests, list):
            return [dict(req) for req in requests if isinstance(req, dict)]
        return []

    def _profile_mode(self) -> str:
        profile = self._profile()
        value = profile.get("mode")
        return str(value) if value else ""

    def _profile_placement(self) -> Dict[str, Any]:
        profile = self._profile()
        placement = profile.get("placement")
        if isinstance(placement, dict):
            return dict(placement)
        return {}

    def _parse_unit_entries(self, value: Any) -> List[Dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        text = str(value).strip()
        if not text:
            return []
        entries: List[Dict[str, Any]] = []
        for entry in text.split(";"):
            parts = entry.strip().split(",")
            if len(parts) < 2:
                continue
            try:
                entries.append({"id": int(parts[0]), "type": parts[1]})
            except ValueError:
                continue
        return entries

    def _infer_enemy_opening(self) -> str:
        units = self._parse_unit_entries(self.state.get("enemy_units") or self.payload.get("enemy_units"))
        if not units:
            return ""

        counts: Dict[str, int] = {}
        for unit in units:
            unit_type = str(unit.get("type") or "")
            if not unit_type:
                continue
            counts[unit_type] = counts.get(unit_type, 0) + 1

        if counts.get("Protoss_Photon_Cannon", 0) > 0 or counts.get("Protoss_Forge", 0) > 0:
            return "cannon"
        if counts.get("Protoss_Gateway", 0) >= 2 and counts.get("Protoss_Cybernetics_Core", 0) > 0:
            return "4gate"
        if counts.get("Protoss_Dark_Templar", 0) > 0 or counts.get("Protoss_Templar_Archives", 0) > 0:
            return "dt"

        if counts.get("Terran_Marine", 0) >= 3 or counts.get("Terran_Barracks", 0) >= 2:
            return "bio"
        if counts.get("Terran_Factory", 0) > 0 or counts.get("Terran_Siege_Tank_Tank_Mode", 0) > 0:
            return "mech"

        if counts.get("Zerg_Mutalisk", 0) > 0 or counts.get("Zerg_Spire", 0) > 0:
            return "muta"
        if counts.get("Zerg_Lurker", 0) > 0 or counts.get("Zerg_Hydralisk_Den", 0) > 0:
            return "lurker"
        if counts.get("Zerg_Zergling", 0) > 0 or counts.get("Zerg_Spawning_Pool", 0) > 0:
            return "pool"

        return ""

    def _enemy_opening(self) -> str:
        explicit = str(self.state.get("enemy_opening") or self.payload.get("enemy_opening") or "").lower()
        if explicit:
            return explicit
        return self._infer_enemy_opening().lower()

    def _append_unique_build(self, requests: List[Dict[str, Any]], building_type: str) -> None:
        for req in requests:
            if req.get("type") == "build_structure" and req.get("building_type") == building_type:
                return
        requests.append({"type": "build_structure", "building_type": building_type})
