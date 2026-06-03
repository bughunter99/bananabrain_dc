"""Python counterpart of C++ BuildingPlacement.cpp / BuildingPlacement.h."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from cppsource.BaseState import BaseState


class BuildingPlacementManager:
    """Building placement, walling, proxy, and defense position planner."""

    _instance: ClassVar[Optional["BuildingPlacementManager"]] = None

    def __init__(self) -> None:
        self._last_plan: Dict[str, Any] = {}

    @classmethod
    def Instance(cls) -> "BuildingPlacementManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(self) -> None:
        self._last_plan = self.default_plan()

    def default_plan(
        self,
        state: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        decision: Any = None,
    ) -> Dict[str, Any]:
        state = state or {}
        payload = payload or {}
        base_state = BaseState.Instance()
        self_race = str(getattr(decision, "self_race", state.get("self_race") or payload.get("race") or "Unknown"))
        enemy_race = str(getattr(decision, "enemy_race", state.get("enemy_race") or payload.get("enemy_race") or "Unknown"))
        is_1v1 = bool(getattr(decision, "is_1v1", int(state.get("enemy_count") or payload.get("enemy_count") or 1) == 1))

        wall_policy = "none"
        proxy_policy = "none"
        if self_race == "Protoss":
            wall_policy = "forge_fast_expand" if is_1v1 else "tight_main_wall"
        elif self_race == "Terran":
            wall_policy = "bunker_ramp" if is_1v1 else "depot_barracks_wall"
        elif self_race == "Zerg":
            wall_policy = "choke_spine" if enemy_race == "Protoss" else "none"

        if self_race == "Protoss" and not is_1v1:
            proxy_policy = "pylon_probe"

        defensive_anchor = "main_ramp"
        if base_state.is_backdoor_natural():
            defensive_anchor = "natural_backdoor"
        elif base_state.is_island_map():
            defensive_anchor = "island_main"

        plan = {
            "plan": "default",
            "self_race": self_race,
            "enemy_race": enemy_race,
            "expand_priority": "natural" if base_state.natural_base() else "macro",
            "wall_policy": wall_policy,
            "proxy_policy": proxy_policy,
            "defensive_anchor": defensive_anchor,
            "natural_base": base_state.natural_base(),
            "start_base": base_state.start_base(),
        }
        self._last_plan = dict(plan)
        return plan

    def plan(self) -> Dict[str, Any]:
        return dict(self._last_plan)

    def set_plan(self, plan: Dict[str, Any]) -> None:
        self._last_plan = dict(plan or {})
