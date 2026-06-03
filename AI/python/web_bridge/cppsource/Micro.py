"""Python counterpart of C++ Micro.cpp / Micro.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple


@dataclass
class TentativeEffect:
    """Predicted effect at a position."""
    frame: int = -1
    position: Tuple[int, int] = (0, 0)
    target: Any = None


@dataclass
class TransportCommand:
    """Transport unit command."""
    unit_id: Any = None
    target_position: Tuple[int, int] = (0, 0)
    load: bool = False


@dataclass
class TransportState:
    """State of transport unit."""
    in_transport: bool = False
    passengers: List[Any] = field(default_factory=list)


@dataclass
class OverlordCommand:
    """Overlord movement command."""
    unit_id: Any = None
    target_position: Tuple[int, int] = (0, 0)
    hold_position: bool = False


@dataclass
class OverlordState:
    """State of overlord scout."""
    scouting: bool = False
    target_position: Optional[Tuple[int, int]] = None
    last_scouted_position: Optional[Tuple[int, int]] = None


@dataclass
class AirToAirTarget:
    """Air-to-air engagement target."""
    unit_id: Any = None
    priority: int = 0


@dataclass
class MutaliskDive:
    """Mutalisk dive attack."""
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None
    retreat_frame: int = -1
    attacking: bool = False


@dataclass
class ObserverTarget:
    """Observer movement target."""
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None
    scanning: bool = False


@dataclass
class SiegeTankState:
    """Siege tank control state."""
    unit_id: Any = None
    sieged: bool = False
    target_position: Optional[Tuple[int, int]] = None
    siege_site: Optional[Tuple[int, int]] = None


@dataclass
class VultureState:
    """Vulture control state."""
    unit_id: Any = None
    mine_count: int = 0
    target_position: Optional[Tuple[int, int]] = None
    laying_mines: bool = False


@dataclass
class DragoonState:
    """Dragoon control state."""
    unit_id: Any = None
    target_position: Optional[Tuple[int, int]] = None
    retreating: bool = False
    kiting: bool = False


@dataclass
class UnstickState:
    """Unit stuck detection state."""
    unit_id: Any = None
    stuck_since_frame: int = -1
    last_position: Optional[Tuple[int, int]] = None


@dataclass
class CombatState:
    """Overall combat state summary."""
    frame: int = -1
    own_army_count: int = 0
    enemy_army_count: int = 0
    attack_mode: bool = False
    defend_mode: bool = False
    retreat_mode: bool = False
    
    def army_advantage(self) -> int:
        """Get our army advantage (positive = we're ahead)."""
        return self.own_army_count - self.enemy_army_count


@dataclass
class CombatUnitTarget:
    """Unit combat targeting information."""
    unit_id: Any = None
    target_id: Any = None
    score: float = 0.0
    priority: int = 0


class MicroManager:
    """Singleton for managing unit micromanagement."""
    
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
        self.controlled_units_: Dict[Any, Any] = {}
        self.potential_field_: Dict[Tuple[int, int], float] = {}
    
    @classmethod
    def Instance(cls) -> "MicroManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize micro manager."""
        self.tentative_effects_ = []
        self.transport_state_ = {}
        self.overlord_state_ = {}
        self.air_to_air_targets_ = []
        self.mutalisk_dives_ = {}
        self.observer_targets_ = {}
        self.siege_tank_state_ = {}
        self.vulture_state_ = {}
        self.dragoon_state_ = {}
        self.unstick_state_ = {}
        self.combat_targets_ = {}
        self.controlled_units_ = {}
        self.potential_field_ = {}
    
    def update(self, snapshot: Optional[Dict[str, Any]] = None, frame: int = 0) -> None:
        """Update micro management from game state."""
        snapshot = snapshot or {}
        own_units = self._parse_units(snapshot.get("own_units", []))
        enemy_units = self._parse_units(snapshot.get("enemy_units", []))
        own_army = self._count_combat_units(own_units)
        enemy_army = self._count_combat_units(enemy_units)
        
        # Determine combat mode
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
        """Get current combat state."""
        return self.combat_state_
    
    def add_unit(self, unit_id: Any, unit_type: str) -> None:
        """Add unit to micro management."""
        self.controlled_units_[unit_id] = unit_type
    
    def remove_unit(self, unit_id: Any) -> None:
        """Remove unit from micro management."""
        self.controlled_units_.pop(unit_id, None)
        self.combat_targets_.pop(unit_id, None)
        self.transport_state_.pop(unit_id, None)
        self.overlord_state_.pop(unit_id, None)
        self.siege_tank_state_.pop(unit_id, None)
        self.vulture_state_.pop(unit_id, None)
        self.dragoon_state_.pop(unit_id, None)
        self.unstick_state_.pop(unit_id, None)
    
    def frame(self) -> None:
        """Execute micromanagement logic each frame."""
        self._control_all_units()
        self._compute_potential_field()
    
    def _control_all_units(self) -> None:
        """Control all managed units."""
        for unit_id, unit_type in self.controlled_units_.items():
            self._control_unit(unit_id, unit_type)
    
    def _control_unit(self, unit_id: Any, unit_type: str) -> None:
        """Control individual unit based on type."""
        if "SiegeTank" in unit_type:
            self._control_siege_tank(unit_id)
        elif "Vulture" in unit_type:
            self._control_vulture(unit_id)
        elif "Dragoon" in unit_type:
            self._control_dragoon(unit_id)
        elif "Mutalisk" in unit_type:
            self._control_mutalisk(unit_id)
    
    def _control_siege_tank(self, unit_id: Any) -> None:
        """Control siege tank unit."""
        if unit_id not in self.siege_tank_state_:
            self.siege_tank_state_[unit_id] = SiegeTankState(unit_id=unit_id)
    
    def _control_vulture(self, unit_id: Any) -> None:
        """Control vulture unit."""
        if unit_id not in self.vulture_state_:
            self.vulture_state_[unit_id] = VultureState(unit_id=unit_id)
    
    def _control_dragoon(self, unit_id: Any) -> None:
        """Control dragoon unit."""
        if unit_id not in self.dragoon_state_:
            self.dragoon_state_[unit_id] = DragoonState(unit_id=unit_id)
    
    def _control_mutalisk(self, unit_id: Any) -> None:
        """Control mutalisk unit."""
        if unit_id not in self.mutalisk_dives_:
            self.mutalisk_dives_[unit_id] = MutaliskDive(unit_id=unit_id)
    
    def _compute_potential_field(self) -> None:
        """Compute movement potential fields for units."""
        self.potential_field_ = {}
        # Simplified: would compute gradients from threats/objectives
    
    def _parse_units(self, units: Any) -> List[Any]:
        """Parse unit list from snapshot."""
        if not units:
            return []
        return units if isinstance(units, list) else []
    
    def _count_combat_units(self, units: List[Any]) -> int:
        """Count combat units in list."""
        # Simplified: count all units as combat units
        return len(units)
    
    def _refresh_target_cache(self, own_units: List[Any], enemy_units: List[Any]) -> None:
        """Refresh targeting cache."""
        self.combat_targets_ = {}
        for own_unit in own_units:
            # Find best target for this unit
            best_target = None
            best_score = -float('inf')
            for enemy_unit in enemy_units:
                score = self._compute_target_score(own_unit, enemy_unit)
                if score > best_score:
                    best_score = score
                    best_target = enemy_unit
            
            if best_target is not None:
                self.combat_targets_[own_unit] = CombatUnitTarget(
                    unit_id=own_unit,
                    target_id=best_target,
                    score=best_score
                )
    
    def _compute_target_score(self, own_unit: Any, enemy_unit: Any) -> float:
        """Compute targeting score for enemy unit."""
        # Simplified: base score on distance
        return 1.0
    
    def draw(self) -> None:
        """Draw micro debug information."""
        pass
