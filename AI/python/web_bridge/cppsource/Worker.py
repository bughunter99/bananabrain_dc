"""Python counterpart of C++ Worker.cpp / Worker.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple


class WorkerAllocation:
    def __init__(self, minerals=None, refineries=None, worker_map=None) -> None:
        self.minerals_ = minerals or []
        self.refineries_ = refineries or []
        self.worker_map_ = worker_map or {}

    def pick_mineral_for_worker(self, worker: "Worker") -> Any:
        return self.minerals_[0] if self.minerals_ else None

    def minerals_with_worker_count(self, worker_count: int, worker_unit: Any) -> List[Any]:
        return list(self.minerals_)

    def pick_refinery_for_worker(self, worker: "Worker") -> Any:
        return self.refineries_[0] if self.refineries_ else None

    def unsaturated_refineries(self, worker_unit: Any) -> List[Any]:
        return list(self.refineries_)

    def closest_unit(self, units: List[Any], target_unit: Any) -> Any:
        return units[0] if units else None

    def max_workers(self) -> int:
        return len(self.minerals_) * 2

    def average_workers_per_mineral(self) -> float:
        return 0.0

    def count_refinery_workers(self) -> int:
        return 0


@dataclass(order=True)
class WorkerPositionAndVelocity:
    position: Tuple[int, int] = (0, 0)
    velocity_x: int = 0
    velocity_y: int = 0


class WorkerOrder:
    def __init__(self, worker: "Worker") -> None:
        self.worker_ = worker
        self.unit_ = worker.unit()
        self.done_ = False

    def apply_orders(self) -> None:
        return None

    def is_done(self) -> bool:
        return bool(self.done_)

    def is_idle(self) -> bool:
        return False

    def is_pullable(self) -> bool:
        return False

    def is_defending(self) -> bool:
        return False

    def is_scouting(self) -> bool:
        return False

    def is_combat(self) -> bool:
        return False

    def scout_base(self) -> Any:
        return None

    def gather_target(self) -> Any:
        return None

    def building_type(self) -> Any:
        return None

    def building_position(self) -> Tuple[int, int]:
        return (0, 0)

    def building(self) -> Any:
        return None

    def repair_target(self) -> Any:
        return None

    def draw(self) -> None:
        return None


class ScoutWorkerOrder(WorkerOrder):
    def __init__(self, worker: "Worker", scout_base: Any = None) -> None:
        super().__init__(worker)
        self.scout_base_ = scout_base

    def is_scouting(self) -> bool:
        return True

    def scout_base(self) -> Any:
        return self.scout_base_


class WaitAtProxyLocationOrder(WorkerOrder):
    def __init__(self, worker: "Worker", position: Tuple[int, int]) -> None:
        super().__init__(worker)
        self.position_ = position

    def is_idle(self) -> bool:
        return True

    def building_position(self) -> Tuple[int, int]:
        return self.position_


class BlockPositionOrder(WorkerOrder):
    def __init__(self, worker: "Worker", position: Tuple[int, int]) -> None:
        super().__init__(worker)
        self.position_ = position

    def is_defending(self) -> bool:
        return True

    def building_position(self) -> Tuple[int, int]:
        return self.position_


class BuildWorkerOrder(WorkerOrder):
    kBuildTimeoutFrames = 240
    kResourceTimeoutFrames = 240

    def __init__(self, worker: "Worker", building_type: Any, building_position: Tuple[int, int]) -> None:
        super().__init__(worker)
        self.building_type_ = building_type
        self.building_position_ = building_position

    def building_type(self) -> Any:
        return self.building_type_

    def building_position(self) -> Tuple[int, int]:
        return self.building_position_


class CombatWorkerOrder(WorkerOrder):
    def is_combat(self) -> bool:
        return True


class WorkerManager:
    """Singleton for worker management."""
    
    _instance: ClassVar[Optional['WorkerManager']] = None
    
    def __init__(self) -> None:
        self.force_refinery_workers_ = False
    
    @classmethod
    def Instance(cls) -> 'WorkerManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize worker manager."""
        self.force_refinery_workers_ = False
    
    def set_force_refinery_workers(self, force: bool) -> None:
        """Force workers to gas refineries."""
        self.force_refinery_workers_ = force
    
    def is_force_refinery_workers(self) -> bool:
        """Check if forcing workers to gas."""
        return self.force_refinery_workers_


class ContinueBuildWorkerOrder(WorkerOrder):
    def __init__(self, worker: "Worker", building: Any) -> None:
        super().__init__(worker)
        self.building_ = building

    def building_type(self) -> Any:
        return getattr(self.building_, "type", None)

    def building_position(self) -> Tuple[int, int]:
        return getattr(self.building_, "position", (0, 0))

    def building(self) -> Any:
        return self.building_


class DefendBaseOrder(WorkerOrder):
    def __init__(self, worker: "Worker", base: Any, fight_to_the_death: bool) -> None:
        super().__init__(worker)
        self.base_ = base
        self.fight_to_the_death_ = fight_to_the_death

    def is_defending(self) -> bool:
        return True


class DefendBuildingOrder(WorkerOrder):
    def __init__(self, worker: "Worker", building_unit: Any) -> None:
        super().__init__(worker)
        self.building_unit_ = building_unit

    def is_defending(self) -> bool:
        return True


class DefendCannonRushOrder(WorkerOrder):
    def is_defending(self) -> bool:
        return True

    @staticmethod
    def should_apply_cannon_rush_defense(information_unit: Any, allow_pylons_and_probes: bool = False) -> bool:
        return False


class FleeWorkerOrder(WorkerOrder):
    def is_defending(self) -> bool:
        return True

    def is_idle(self) -> bool:
        return False


class GatherWorkerOrder(WorkerOrder):
    def __init__(self, worker: "Worker", gather_target: Any) -> None:
        super().__init__(worker)
        self.gather_target_ = gather_target

    def gather_target(self) -> Any:
        return self.gather_target_


class IdleWorkerOrder(WorkerOrder):
    def is_idle(self) -> bool:
        return True

    def is_pullable(self) -> bool:
        return True


class RepairWorkerOrder(WorkerOrder):
    def __init__(self, worker: "Worker", repair_target: Any) -> None:
        super().__init__(worker)
        self.repair_target_ = repair_target

    def repair_target(self) -> Any:
        return self.repair_target_


class Worker:
    def __init__(self, unit: Any) -> None:
        self.unit_ = unit
        self.order_: Optional[WorkerOrder] = None

    def unit(self) -> Any:
        return self.unit_

    def order(self) -> Optional[WorkerOrder]:
        return self.order_

    def apply_orders(self) -> None:
        if self.order_ is not None:
            self.order_.apply_orders()

    def draw(self) -> None:
        return None

    def idle(self) -> None:
        self.order_ = IdleWorkerOrder(self)

    def flee(self) -> None:
        self.order_ = FleeWorkerOrder(self)

    def gather(self, gather_target: Any) -> None:
        self.order_ = GatherWorkerOrder(self, gather_target)

    def build(self, building_type: Any, building_position: Tuple[int, int]) -> None:
        self.order_ = BuildWorkerOrder(self, building_type, building_position)

    def continue_build(self, building: Any) -> None:
        self.order_ = ContinueBuildWorkerOrder(self, building)

    def defend_base(self, base: Any, fight_to_the_death: bool) -> None:
        self.order_ = DefendBaseOrder(self, base, fight_to_the_death)

    def defend_building(self, building_unit: Any) -> None:
        self.order_ = DefendBuildingOrder(self, building_unit)

    def defend_cannon_rush(self) -> None:
        self.order_ = DefendCannonRushOrder(self)

    def scout_for_proxies(self) -> None:
        self.order_ = ScoutWorkerOrder(self)

    def scout(self) -> None:
        self.order_ = ScoutWorkerOrder(self)

    def wait_at_proxy_location(self, position: Tuple[int, int]) -> None:
        self.order_ = WaitAtProxyLocationOrder(self, position)

    def block_position(self, position: Tuple[int, int]) -> None:
        self.order_ = BlockPositionOrder(self, position)

    def repair(self, repair_target: Any) -> None:
        self.order_ = RepairWorkerOrder(self, repair_target)

    def combat(self) -> None:
        self.order_ = CombatWorkerOrder(self)
