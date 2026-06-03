"""Python counterpart of C++ UnitUtils.cpp / UnitUtils.h."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


class UnitUtils:
    @staticmethod
    def unit_id(unit: Any) -> Optional[Any]:
        if isinstance(unit, dict):
            return unit.get("id")
        return getattr(unit, "id", None)

    @staticmethod
    def unit_type(unit: Any) -> str:
        if isinstance(unit, dict):
            return str(unit.get("type") or "")
        return str(getattr(unit, "type", ""))

    @staticmethod
    def is_worker(unit: Any) -> bool:
        return UnitUtils.unit_type(unit) in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}

    @staticmethod
    def count_units(units: Iterable[Any], unit_type: str) -> int:
        return sum(1 for unit in units if UnitUtils.unit_type(unit) == unit_type)
