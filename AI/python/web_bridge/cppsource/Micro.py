"""Python counterpart of C++ Micro.cpp / Micro.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple


@dataclass
class TentativeEffect:
    frame: int = -1
    position: Tuple[int, int] = (0, 0)
    target: Any = None


@dataclass
class TransportCommand:
    unit_id: Any = None
    target_position: Tuple[int, int] = (0, 0)
    load: bool = False


@dataclass
class TransportState:
    in_transport: bool = False
    passengers: List[Any] = field(default_factory=list)


@dataclass
class OverlordCommand:
    unit_id: Any = None
    target_position: Tuple[int, int] = (0, 0)
    hold_position: bool = False


@dataclass
class OverlordState:
    scouting: bool = False
    target_position: Optional[Tuple[int, int]] = None


@dataclass
class AirToAirTarget:
    unit_id: Any = None
    priority: int = 0


@dataclass
class MutaliskDive:
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None
    retreat_frame: int = -1


@dataclass
class ObserverTarget:
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None


@dataclass
class SiegeTankState:
    unit_id: Any = None
    sieged: bool = False
    target_position: Optional[Tuple[int, int]] = None


@dataclass
class VultureState:
    unit_id: Any = None
    mine_count: int = 0
    target_position: Optional[Tuple[int, int]] = None


@dataclass
class DragoonState:
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None
    retreating: bool = False


@dataclass
class UnstickState:
    unit_id: Any = None
    stuck_since_frame: int = -1


@dataclass
class CombatState:
    frame: int = -1
    own_army_count: int = 0
    enemy_army_count: int = 0
    attack_mode: bool = False
    defend_mode: bool = False
    retreat_mode: bool = False


@dataclass
class CombatUnitTarget:
    unit_id: Any = None
    target_id: Any = None
    score: float = 0.0


class MicroManager:
    _instance: ClassVar[Optional["MicroManager"]] = None

    def __init__(self) -> None:
        self.tentative_effects_: List[TentativeEffect] = []
        self.transport_state_: Dict[Any, TransportState] = {}
        self.overlord_state_: Dict[Any, OverlordState] = {}
        self.air_to_air_targets_: List[AirToAirTarget] = []
        self.mutalisk_dives_: Dict[Any, MutaliskDive] = {}
        self.observer_targets_: Dict[Any, ObserverTarget] = {}
        self.siege_tank_state_: Dict[Any, SiegeTankState] = {}
        self.vulture_state_: Dict[Any, VultureState] = {}
        self.dragoon_state_: Dict[Any, DragoonState] = {}
        self.unstick_state_: Dict[Any, UnstickState] = {}
        self.combat_state_ = CombatState()
        self.combat_targets_: Dict[Any, CombatUnitTarget] = {}

    @classmethod
    def Instance(cls) -> "MicroManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None, frame: int = 0) -> None:
        snapshot = snapshot or {}
        own_units = self._parse_units(snapshot.get("own_units"))
        enemy_units = self._parse_units(snapshot.get("enemy_units"))
        own_army = self._count_combat_units(own_units)
        enemy_army = self._count_combat_units(enemy_units)
        attack_mode = own_army >= enemy_army + 3
        defend_mode = enemy_army > own_army
        retreat_mode = enemy_army >= own_army + 5

        self.combat_state_ = CombatState(
            frame=int(frame),
            own_army_count=own_army,
            enemy_army_count=enemy_army,
            attack_mode=attack_mode,
            defend_mode=defend_mode,
            retreat_mode=retreat_mode,
        )
        self._refresh_target_cache(own_units, enemy_units)

    def combat_state(self) -> CombatState:
        return self.combat_state_

    def should_attack(self) -> bool:
        return self.combat_state_.attack_mode

    def should_defend(self) -> bool:
        return self.combat_state_.defend_mode

    def should_retreat(self) -> bool:
        return self.combat_state_.retreat_mode

    def command_transport(self, unit_id: Any, target_position: Tuple[int, int], load: bool = False) -> None:
        self.transport_state_[unit_id] = TransportState(in_transport=bool(load))

    def command_overlord(self, unit_id: Any, target_position: Tuple[int, int], hold_position: bool = False) -> None:
        self.overlord_state_[unit_id] = OverlordState(scouting=True, target_position=tuple(target_position))

    def command_dragoon(self, unit_id: Any, target_position: Tuple[int, int], retreating: bool = False) -> None:
        self.dragoon_state_[unit_id] = DragoonState(unit_id=unit_id, target_position=tuple(target_position), retreating=bool(retreating))

    def command_vulture(self, unit_id: Any, target_position: Tuple[int, int], mine_count: int = 0) -> None:
        self.vulture_state_[unit_id] = VultureState(unit_id=unit_id, target_position=tuple(target_position), mine_count=int(mine_count))

    def command_siege_tank(self, unit_id: Any, target_position: Tuple[int, int], sieged: bool = False) -> None:
        self.siege_tank_state_[unit_id] = SiegeTankState(unit_id=unit_id, target_position=tuple(target_position), sieged=bool(sieged))

    def add_tentative_effect(self, position: Tuple[int, int], frame: int, target: Any = None) -> None:
        self.tentative_effects_.append(TentativeEffect(frame=int(frame), position=tuple(position), target=target))

    def _parse_units(self, units: Any) -> List[Dict[str, Any]]:
        if not isinstance(units, list):
            return []
        return [unit for unit in units if isinstance(unit, dict)]

    def _count_combat_units(self, units: List[Dict[str, Any]]) -> int:
        combat_types = {
            "Protoss_Zealot",
            "Protoss_Dragoon",
            "Protoss_Reaver",
            "Protoss_Archon",
            "Terran_Marine",
            "Terran_Firebat",
            "Terran_Ghost",
            "Terran_Siege_Tank_Tank_Mode",
            "Terran_Siege_Tank_Siege_Mode",
            "Zerg_Zergling",
            "Zerg_Hydralisk",
            "Zerg_Mutalisk",
            "Zerg_Ultralisk",
            "Zerg_Lurker",
        }
        return sum(1 for unit in units if str(unit.get("type") or "") in combat_types)

    def _refresh_target_cache(self, own_units: List[Dict[str, Any]], enemy_units: List[Dict[str, Any]]) -> None:
        self.combat_targets_.clear()
        enemy_by_type = {str(unit.get("type") or ""): unit for unit in enemy_units}
        for unit in own_units:
            unit_id = unit.get("id")
            if unit_id is None:
                continue
            self.combat_targets_[unit_id] = CombatUnitTarget(
                unit_id=unit_id,
                target_id=next(iter(enemy_by_type.values()), {}).get("id") if enemy_by_type else None,
                score=float(len(enemy_units)),
            )
