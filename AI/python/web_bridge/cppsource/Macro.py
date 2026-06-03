"""Python counterpart of C++ Macro.cpp / Macro.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional

from cppsource.BaseState import BaseState


@dataclass
class CostPerMinute:
    minerals: float = 0.0
    gas: float = 0.0
    supply: float = 0.0


@dataclass
class MineralGas:
    minerals: int = 0
    gas: int = 0

    def can_pay(self, other: "MineralGas") -> bool:
        return self.minerals >= other.minerals and self.gas >= other.gas


class ResourceCounter:
    def __init__(self, size: int) -> None:
        self.values_: List[int] = [0] * size
        self.index_ = 0
        self.per_minute_ = 0.0

    def init(self, value: int) -> None:
        self.values_ = [int(value)] * len(self.values_)

    def process_value(self, value: int) -> None:
        if not self.values_:
            return
        self.values_[self.index_] = int(value)
        self.index_ = (self.index_ + 1) % len(self.values_)
        self.per_minute_ = float(sum(self.values_))

    def per_minute(self) -> float:
        return self.per_minute_


class TrainDistribution:
    kLarvaSpawnFrames = 342

    def __init__(self, builder_type: Any) -> None:
        self.builder_type_ = builder_type
        self.weights_: Dict[Any, float] = {}

    def clear(self) -> None:
        self.weights_.clear()

    def get(self, unit_type: Any) -> float:
        return float(self.weights_.get(unit_type, 0.0))

    def set(self, unit_type: Any, value: float) -> None:
        self.weights_[unit_type] = float(value)

    def is_empty(self) -> bool:
        return not self.is_nonempty()

    def is_nonempty(self) -> bool:
        return bool(self.weights_)

    def sum(self) -> float:
        return float(sum(self.weights_.values()))

    def sample(self) -> Any:
        return next(iter(self.weights_), None)

    def weighted_cost(self) -> MineralGas:
        return MineralGas()

    def cost_per_minute(self, producers: int = 1) -> CostPerMinute:
        return CostPerMinute()

    @staticmethod
    def cost_per_minute_for_unit(unit_type: Any) -> CostPerMinute:
        return CostPerMinute()

    def additional_producers(self) -> int:
        return 0

    def apply_train_orders(self) -> None:
        return None

    def builder_type(self) -> Any:
        return self.builder_type_


@dataclass
class BuildingCount:
    actual: int = 0
    planned: int = 0
    warping: int = 0
    additional: int = 0
    additional_important: int = 0

    def requested(self, important: bool = False) -> int:
        return self.actual + self.planned + (self.additional_important if important else self.additional)


@dataclass
class BaseDefense:
    @dataclass
    class Single:
        exists: bool = False
        planned: bool = False
        add: bool = False

    @dataclass
    class Multi:
        actual: int = 0
        planned: int = 0
        additional: int = 0

    pylon: "BaseDefense.Single" = field(default_factory=Single)
    cannons: "BaseDefense.Multi" = field(default_factory=Multi)
    turrets: "BaseDefense.Multi" = field(default_factory=Multi)
    creep_colony: "BaseDefense.Single" = field(default_factory=Single)
    sunken_colony: "BaseDefense.Single" = field(default_factory=Single)
    spore_colony: "BaseDefense.Single" = field(default_factory=Single)


class BuildingManager:
    _instance: ClassVar[Optional["BuildingManager"]] = None

    def __init__(self) -> None:
        self.building_count_: Dict[Any, BuildingCount] = {}
        self.base_defense_: Dict[Any, BaseDefense] = {}
        self.upgrade_request_: Dict[Any, bool] = {}
        self.research_request_: set[Any] = set()
        self.base_request_: Dict[Any, Dict[str, Any]] = {}
        self.automatic_supply_ = False
        self.pylon_retry_frame_ = 0
        self.non_pylon_building_retry_frame_ = 0
        self.base_defense_retry_frame_: Dict[Any, int] = {}
        self.estimated_travel_frame_cache_: Dict[Any, Any] = {}
        self.lost_building_count_ = 0

    @classmethod
    def Instance(cls) -> "BuildingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update_supply_requests(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        supply_used = int(snapshot.get("supply_used") or 0)
        supply_total = int(snapshot.get("supply_total") or 0)
        self.automatic_supply_ = supply_total > 0 and supply_used >= max(supply_total - 2, 0)

    def init_building_count_map(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.building_count_.clear()
        snapshot = snapshot or {}
        for unit in snapshot.get("own_units", []) or []:
            unit_type = unit.get("type")
            if unit_type is None:
                continue
            entry = self.building_count_.setdefault(unit_type, BuildingCount())
            entry.actual += 1
        for request in snapshot.get("planned_buildings", []) or []:
            unit_type = request.get("type")
            if unit_type is None:
                continue
            entry = self.building_count_.setdefault(unit_type, BuildingCount())
            entry.planned += 1

    def init_base_defense_map(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.base_defense_.clear()
        for base in BaseState.Instance().bases():
            tile = self._tile_from_base(base)
            if tile is None:
                continue
            self.base_defense_.setdefault(tile, BaseDefense())

    def init_upgrade_and_research(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.upgrade_request_.clear()
        self.research_request_.clear()

    def update_requested_building_count_for_pre_upgrade(self) -> None:
        return None

    def apply_building_requests(self, important: bool) -> None:
        return None

    def repair_damaged_buildings(self) -> None:
        return None

    def continue_unfinished_buildings_without_worker(self) -> None:
        return None

    def apply_upgrades(self, important: bool) -> None:
        return None

    def apply_research(self) -> None:
        return None

    def cancel_building(self, building: Any) -> None:
        return None

    def cancel_buildings_of_type(self, building_type: Any) -> None:
        return None

    def cancel_extra_buildings_of_type(self, building_type: Any, keep_including_warping: int, keep_including_planned: int) -> None:
        return None

    def cancel_expansion_hatcheries(self) -> None:
        return None

    def cancel_doomed_buildings(self) -> None:
        return None

    def building_exists(self, unit_type: Any) -> bool:
        return self.building_count(unit_type) > 0

    def building_count(self, unit_type: Any) -> int:
        return int(self.building_count_.get(unit_type, BuildingCount()).actual)

    def building_count_including_planned(self, unit_type: Any) -> int:
        count = self.building_count_.get(unit_type, BuildingCount())
        return count.actual + count.planned

    def building_count_including_warping(self, unit_type: Any) -> int:
        count = self.building_count_.get(unit_type, BuildingCount())
        return count.actual + count.warping

    def building_count_including_requested(self, unit_type: Any, important: bool = False) -> int:
        return self.building_count_.get(unit_type, BuildingCount()).requested(important)

    def set_requested_building_count_at_least(self, unit_type: Any, count: int, important: bool = False) -> None:
        entry = self.building_count_.setdefault(unit_type, BuildingCount())
        if important:
            entry.additional_important = max(entry.additional_important, int(count) - entry.actual - entry.planned)
        else:
            entry.additional = max(entry.additional, int(count) - entry.actual - entry.planned)

    def automatic_supply(self) -> bool:
        return self.automatic_supply_

    def set_automatic_supply(self, automatic_supply: bool) -> None:
        self.automatic_supply_ = bool(automatic_supply)

    def request_upgrade(self, upgrade_type: Any, important: bool = False) -> None:
        self.upgrade_request_[upgrade_type] = self.upgrade_request_.get(upgrade_type, False) or important

    def request_research(self, tech_type: Any) -> None:
        self.research_request_.add(tech_type)

    def request_base(self, base: Any, important: bool = False) -> None:
        self.base_request_[base] = {"important": important}

    def request_next_base(self, important: bool = False) -> bool:
        next_bases = BaseState.Instance().next_available_bases()
        if not next_bases:
            return False
        base = next_bases[0]
        self.request_base(base, important=important)
        return True

    def request_bases(self, count: int) -> bool:
        if count <= 0:
            return False
        requested = False
        for base in BaseState.Instance().next_available_bases()[: int(count)]:
            self.request_base(base, important=False)
            requested = True
        return requested

    def base_defense_pylon_exists(self, base: Any) -> bool:
        return self.base_defense_.get(base, BaseDefense()).pylon.exists

    def base_defense_cannons_including_planned(self, base: Any) -> int:
        entry = self.base_defense_.get(base, BaseDefense())
        return entry.cannons.actual + entry.cannons.planned

    def base_defense_creep_colony_planned_or_exists(self, base: Any) -> bool:
        entry = self.base_defense_.get(base, BaseDefense())
        return entry.creep_colony.planned or entry.creep_colony.exists

    def base_defense_creep_colony_exists(self, base: Any) -> bool:
        return self.base_defense_.get(base, BaseDefense()).creep_colony.exists

    def base_defense_sunken_colony_planned_or_exists(self, base: Any) -> bool:
        entry = self.base_defense_.get(base, BaseDefense())
        return entry.sunken_colony.planned or entry.sunken_colony.exists

    def base_defense_sunken_colony_exists(self, base: Any) -> bool:
        return self.base_defense_.get(base, BaseDefense()).sunken_colony.exists

    @staticmethod
    def _tile_from_base(base: Any) -> Optional[tuple[int, int]]:
        tile = None
        if isinstance(base, dict):
            tile = base.get("tile") or base.get("location") or base.get("tile_position")
        if isinstance(tile, (list, tuple)) and len(tile) == 2:
            try:
                return int(tile[0]), int(tile[1])
            except (TypeError, ValueError):
                return None
        if isinstance(tile, str):
            parts = [part.strip() for part in tile.split(",")]
            if len(parts) == 2:
                try:
                    return int(parts[0]), int(parts[1])
                except ValueError:
                    return None
        return None

    def base_defense_spore_colony_planned_or_exists(self, base: Any) -> bool:
        entry = self.base_defense_.get(base, BaseDefense())
        return entry.spore_colony.planned or entry.spore_colony.exists

    def base_defense_spore_colony_exists(self, base: Any) -> bool:
        return self.base_defense_.get(base, BaseDefense()).spore_colony.exists

    def request_base_defense_pylon(self, base: Any) -> None:
        return None

    def set_requested_base_defense_cannon_count_at_least(self, base: Any, count: int) -> None:
        return None

    def set_requested_base_defense_turret_count_at_least(self, base: Any, count: int) -> None:
        return None

    def request_base_defense_creep_colony(self, base: Any) -> None:
        return None

    def request_base_defense_sunken_colony(self, base: Any) -> None:
        return None

    def request_base_defense_spore_colony(self, base: Any) -> None:
        return None

    def lost_building_count(self) -> int:
        return self.lost_building_count_

    def can_not_place_refinery(self) -> bool:
        return False

    def required_buildings_exist_for_building(self, unit_type: Any) -> bool:
        return True

    def pylon_placement_failed(self) -> bool:
        return False

    def non_pylon_building_placement_failed(self) -> bool:
        return False

    def building_placement_failed(self) -> bool:
        return self.pylon_placement_failed() or self.non_pylon_building_placement_failed()

    def onUnitLost(self, unit: Any) -> None:
        self.lost_building_count_ += 1


class SpendingManager:
    _instance: ClassVar[Optional["SpendingManager"]] = None

    def __init__(self) -> None:
        self.mineral_counter_ = ResourceCounter(480)
        self.gas_counter_ = ResourceCounter(480)

    @classmethod
    def Instance(cls) -> "SpendingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_resource_counters(self) -> None:
        self.mineral_counter_.init(0)
        self.gas_counter_.init(0)

    def income_per_minute(self) -> MineralGas:
        return MineralGas()
