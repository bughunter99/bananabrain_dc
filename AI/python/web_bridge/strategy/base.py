from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

if TYPE_CHECKING:
    from strategy.result_store import ResultStore


@dataclass
class StrategyContext:
    service: Any
    state: Dict[str, Any]
    payload: Dict[str, Any]
    event: Dict[str, Any]
    strategy_name: str = "auto"
    result_store: Optional["ResultStore"] = None


@dataclass(frozen=True)
class StrategyDecision:
    self_race: str
    enemy_race: str
    is_1v1: bool
    opening: str
    mode: str
    late_game_strategy: str = "none"
    placement_plan: Dict[str, Any] = field(default_factory=dict)
    build_requests: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    source: str = ""


class BaseStrategy:
    name = "base"

    def __init__(self, context: StrategyContext) -> None:
        self.context = context
        self._opening = "auto_play"
        self._mode = "Opening"
        self._late_game_strategy = "none"
        self._placement_plan: Dict[str, Any] = {}
        self._build_requests: List[Dict[str, Any]] = []
        self._notes: List[str] = []

    @property
    def state(self) -> Dict[str, Any]:
        return self.context.state

    @property
    def payload(self) -> Dict[str, Any]:
        return self.context.payload

    @property
    def event(self) -> Dict[str, Any]:
        return self.context.event

    @property
    def self_race(self) -> str:
        return str(self.payload.get("race") or self.payload.get("self_race") or self.state.get("self_race") or "Unknown")

    @property
    def enemy_race(self) -> str:
        return str(self.payload.get("enemy_race") or self.state.get("enemy_race") or "Unknown")

    @property
    def is_1v1(self) -> bool:
        return bool(self.payload.get("enemy_count", self.state.get("enemy_count") or 1) == 1)

    @property
    def opening(self) -> str:
        return self._opening

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def late_game_strategy(self) -> str:
        return self._late_game_strategy

    def decision(self) -> StrategyDecision:
        self.decide_building_placement()
        self.decide_build_requests()
        return StrategyDecision(
            self_race=self.self_race,
            enemy_race=self.enemy_race,
            is_1v1=self.is_1v1,
            opening=self.opening,
            mode=self.mode,
            late_game_strategy=self.late_game_strategy,
            placement_plan=dict(self._placement_plan),
            build_requests=list(self._build_requests),
            notes=list(self._notes),
            source=self.name,
        )

    def pick_strategy(self, is_1v1: bool) -> None:
        raise NotImplementedError

    def frame_inner(self) -> None:
        return

    def decide_building_placement(self) -> None:
        self._placement_plan = {
            "plan": "default",
            "expand_priority": "natural",
            "wall_policy": "none",
            "proxy_policy": "none",
            "defensive_anchor": "main_ramp",
        }

    def decide_build_requests(self) -> None:
        self._build_requests = []

    def _opening_supply_count(self) -> int:
        supply_used = int(self.state.get("supply_used") or self.payload.get("supply_used") or 0)
        return (supply_used + 1) // 2

    def _opening_worker_count(self) -> int:
        own_units = self.state.get("own_units") or []
        if isinstance(own_units, str):
            parsed_units = []
            for entry in own_units.split(";"):
                parts = entry.strip().split(",")
                if len(parts) < 2:
                    continue
                parsed_units.append({"type": parts[1]})
            own_units = parsed_units
        race = self.self_race
        result = 0
        for unit in own_units:
            unit_type = str(unit.get("type") or "")
            if race == "Protoss" and unit_type == "Protoss_Probe":
                result += 1
            elif race == "Terran" and unit_type == "Terran_SCV":
                result += 1
            elif race == "Zerg" and unit_type == "Zerg_Drone":
                result += 1
        return result

    def _opening_lost_too_many_workers(self) -> bool:
        lost_worker_count = int(self.state.get("lost_worker_count") or self.payload.get("lost_worker_count") or 0)
        if self.state.get("sent_initial_scout") or self.payload.get("sent_initial_scout"):
            lost_worker_count -= 1
        return lost_worker_count > 0

    def _is_defending_rush(self) -> bool:
        enemy_supply = int(self.state.get("enemy_army_supply") or self.payload.get("enemy_army_supply") or 0)
        army_supply = int(self.state.get("army_supply") or self.payload.get("army_supply") or 0)
        return army_supply < 40 and army_supply <= enemy_supply

    def _is_contained(self) -> bool:
        offense = int(self.state.get("enemy_offense_supply") or self.payload.get("enemy_offense_supply") or 0)
        army = int(self.state.get("army_supply") or self.payload.get("army_supply") or 0)
        return offense > army

    def _is_enemy_offense_larger_than_defense(self) -> bool:
        offense = int(self.state.get("enemy_offense_supply") or self.payload.get("enemy_offense_supply") or 0)
        defense = int(self.state.get("defense_supply") or self.payload.get("defense_supply") or 0)
        return offense > defense

    def _expect_lurkers(self) -> bool:
        hint = str(self.state.get("enemy_opening") or self.payload.get("enemy_opening") or "").lower()
        return "lurker" in hint or "hydra" in hint

    def _expect_dark_templars(self) -> bool:
        hint = str(self.state.get("enemy_opening") or self.payload.get("enemy_opening") or "").lower()
        return "dt" in hint or "dark" in hint

    def _is_gas_stolen(self) -> bool:
        return bool(self.payload.get("gas_stolen") or self.state.get("gas_stolen"))

    def _stable_pick(self, candidates: Sequence[str], salt: str = "") -> str:
        items = [candidate for candidate in candidates if candidate]
        if not items:
            return "auto_play"

        # ResultStore가 있으면 가중치 랜덤 선택 시도
        rs = getattr(self.context, "result_store", None)
        if rs is not None:
            chosen = rs.weighted_pick(items)
            if chosen is not None:
                return chosen

        # 기록 없으면 해시 기반 결정론적 선택
        key = "|".join([
            self.self_race,
            self.enemy_race,
            str(self.is_1v1),
            str(self.state.get("map_width_tiles", 0)),
            str(self.state.get("map_height_tiles", 0)),
            salt,
        ])
        digest = hashlib.sha1(key.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(items)
        return items[index]
