"""Python counterpart of C++ Strategy.cpp / Strategy.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CANONICAL_STRATEGY_UNITS = ["ProtossStrategy", "TerranStrategy", "ZergStrategy"]


def normalize_strategy_unit_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "auto":
        return "auto"
    return text


@dataclass
class StrategyDecision:
    self_race: str = "Unknown"
    enemy_race: str = "Unknown"
    opening: str = "auto"
    mode: str = "Opening"
    late_game_strategy: str = "none"
    placement_plan: Dict[str, Any] = field(default_factory=dict)
    source: str = "Strategy"
    strategy_unit: str = "Strategy"
    build_requests: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StrategyContext:
    service: Any
    state: Dict[str, Any]
    payload: Dict[str, Any]
    event: Dict[str, Any]
    strategy_name: str = "auto"
    result_store: Any = None


class Strategy:
    def __init__(self, context: Optional[StrategyContext] = None) -> None:
        self._context = context
        self._opening = "auto"
        self._mode = "Opening"
        self._late_game_strategy = "none"
        self._decision = StrategyDecision(source=self.__class__.__name__)
        self.self_race = "Unknown"
        self.enemy_race = "Unknown"

    def pick_strategy(self, is_1v1: bool) -> None:
        if self._context is not None:
            self.self_race = str(self._context.state.get("self_race") or self._context.payload.get("race") or "Unknown")
            self.enemy_race = str(self._context.state.get("enemy_race") or self._context.payload.get("enemy_race") or "Unknown")
            self._mode = str(self._context.state.get("strategy_mode") or self._context.payload.get("mode") or self._mode)
            self._opening = str(self._context.state.get("strategy_opening") or self._opening)
        self._decision.self_race = self.self_race
        self._decision.enemy_race = self.enemy_race
        self._decision.opening = self._opening
        self._decision.mode = self._mode
        self._decision.late_game_strategy = self._late_game_strategy

    def mode(self) -> str:
        return self._mode

    def opening(self) -> str:
        return self._opening

    def late_game_strategy(self) -> str:
        return self._late_game_strategy

    def frame_inner(self) -> None:
        self._decision.self_race = self.self_race
        self._decision.enemy_race = self.enemy_race
        self._decision.opening = self._opening
        self._decision.mode = self._mode
        self._decision.late_game_strategy = self._late_game_strategy
        if not self._decision.placement_plan:
            self._decision.placement_plan = self._default_placement_plan()
        self._decision.source = self.__class__.__name__
        self._decision.strategy_unit = self.__class__.__name__

    def set_placement_plan(self, plan: Dict[str, Any]) -> None:
        self._decision.placement_plan = dict(plan or {})

    def add_build_request(self, request: Dict[str, Any]) -> None:
        if request:
            self._decision.build_requests.append(dict(request))

    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "default",
            "expand_priority": "natural",
            "wall_policy": "none",
            "proxy_policy": "none",
            "defensive_anchor": "main_ramp",
        }

    def decision(self) -> StrategyDecision:
        return self._decision


class ProtossStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "protoss_default",
            "expand_priority": "natural",
            "wall_policy": "forge_fast_expand",
            "proxy_policy": "pylon_probe",
            "defensive_anchor": "main_ramp",
        }


class TerranStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "terran_default",
            "expand_priority": "natural",
            "wall_policy": "bunker_ramp",
            "proxy_policy": "none",
            "defensive_anchor": "main_ramp",
        }


class ZergStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "zerg_default",
            "expand_priority": "natural",
            "wall_policy": "choke_spine",
            "proxy_policy": "none",
            "defensive_anchor": "main_hatch",
        }


class StrategySelector:
    def select(self, context: StrategyContext) -> Strategy:
        strategy_name = normalize_strategy_unit_name(context.strategy_name)
        if strategy_name == "TerranStrategy":
            return TerranStrategy(context)
        if strategy_name == "ZergStrategy":
            return ZergStrategy(context)
        return ProtossStrategy(context)
