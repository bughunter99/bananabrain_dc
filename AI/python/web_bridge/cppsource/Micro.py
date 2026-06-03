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


# ========== PHASE 7: ADVANCED MICRO SYSTEMS ==========

class UnitBehavior:
    """Individual unit behavior state machine."""
    
    def __init__(self, unit_id: Any) -> None:
        self.unit_id = unit_id
        self.state = "idle"  # idle, moving, attacking, retreating, regrouping
        self.target_position: Optional[Tuple[int, int]] = None
        self.target_unit: Optional[Any] = None
        self.last_action_frame = 0
        self.health_percent = 100.0
    
    def update_state(self, current_frame: int, enemy_nearby: bool, health_pct: float) -> None:
        """Update behavior state based on conditions."""
        self.health_percent = health_pct
        
        if health_pct < 30 and self.state != "retreating":
            self.state = "retreating"
        elif health_pct > 50 and self.state == "retreating":
            self.state = "attacking"
        elif not enemy_nearby and self.state == "attacking":
            self.state = "moving"
    
    def should_attack(self) -> bool:
        """Check if should engage target."""
        return self.state in ["attacking", "idle"] and self.health_percent > 40
    
    def should_retreat(self) -> bool:
        """Check if should retreat."""
        return self.state == "retreating" or self.health_percent < 25
    
    def should_regroup(self) -> bool:
        """Check if should regroup with allies."""
        return self.state == "regrouping"


class EngagementLogic:
    """Combat engagement and target selection."""
    
    def __init__(self) -> None:
        self.threat_map: Dict[Any, float] = {}
        self.engagement_priority: Dict[Any, int] = {}
        self.auto_attack_enabled = True
    
    def evaluate_threat(self, enemy_unit: Any, distance: float, damage_per_hit: float) -> float:
        """Evaluate threat level of enemy unit."""
        if distance > 100:  # Out of range
            return 0.0
        
        threat_score = damage_per_hit / max(1, distance)
        return threat_score
    
    def select_primary_target(self, enemy_units: List[Any], own_unit: Any) -> Optional[Any]:
        """Select primary target based on priority."""
        best_target = None
        best_priority = -1
        
        for enemy in enemy_units:
            priority = self.engagement_priority.get(enemy, 5)
            if priority > best_priority:
                best_priority = priority
                best_target = enemy
        
        return best_target
    
    def prioritize_high_threat_units(self, enemy_units: List[Any]) -> None:
        """Set high priority for dangerous enemy units."""
        threat_units = ["Terran_Siege_Tank", "Protoss_Dark_Templar", "Zerg_Lurker",
                        "Protoss_Reaver", "Terran_Battlecruiser"]
        
        for enemy in enemy_units:
            unit_type = str(enemy).split("_")[0] if hasattr(enemy, "__str__") else ""
            if unit_type in threat_units:
                self.engagement_priority[enemy] = 1  # Highest priority
            else:
                self.engagement_priority[enemy] = 5  # Normal priority


class FormationManager:
    """Unit formation maintenance and positioning."""
    
    def __init__(self) -> None:
        self.formation_type = "loose"  # loose, tight, spread, defensive
        self.formation_center: Tuple[int, int] = (0, 0)
        self.unit_positions: Dict[Any, Tuple[int, int]] = {}
        self.desired_spacing = 5  # Tiles between units
    
    def set_formation(self, formation_type: str) -> None:
        """Set desired formation type."""
        self.formation_type = formation_type
    
    def compute_formation_position(self, unit_id: Any, unit_index: int, total_units: int) -> Tuple[int, int]:
        """Compute desired position for unit in formation."""
        if self.formation_type == "loose":
            # Spread units in loose circle
            angle = (unit_index / max(1, total_units)) * 6.28
            radius = self.desired_spacing * 3
            x = int(self.formation_center[0] + radius * 3.14 * angle / 6.28)  # cos approximation
            y = int(self.formation_center[1] + radius * angle / 6.28)  # sin approximation
            return (x, y)
        
        elif self.formation_type == "tight":
            # Clustered formation
            x = self.formation_center[0] + (unit_index % 3) * self.desired_spacing
            y = self.formation_center[1] + (unit_index // 3) * self.desired_spacing
            return (x, y)
        
        else:
            return self.formation_center
    
    def update_formation_center(self, new_center: Tuple[int, int]) -> None:
        """Move formation center."""
        self.formation_center = new_center


class RetreatSystem:
    """Health-based retreat and regrouping."""
    
    def __init__(self) -> None:
        self.retreat_threshold = 30  # Health percent
        self.retreat_destination: Tuple[int, int] = (0, 0)
        self.regrouping_units: List[Any] = []
        self.safe_location_cache: Dict[str, Tuple[int, int]] = {}
    
    def should_unit_retreat(self, unit_health_percent: float, enemy_count: int) -> bool:
        """Determine if unit should retreat."""
        if unit_health_percent < self.retreat_threshold:
            return True
        
        # Retreat if overwhelmed
        if enemy_count > 3 and unit_health_percent < 60:
            return True
        
        return False
    
    def find_safe_retreat_location(self, current_pos: Tuple[int, int], map_name: str = "") -> Tuple[int, int]:
        """Find safe position to retreat to."""
        # Cache common safe locations (main base, expansions)
        if map_name in self.safe_location_cache:
            return self.safe_location_cache[map_name]
        
        # Default: retreat 10 tiles back towards origin
        safe_x = max(0, current_pos[0] - 10)
        safe_y = max(0, current_pos[1] - 10)
        
        return (safe_x, safe_y)
    
    def add_regrouping_unit(self, unit_id: Any) -> None:
        """Mark unit for regrouping."""
        if unit_id not in self.regrouping_units:
            self.regrouping_units.append(unit_id)
    
    def clear_regrouping(self) -> None:
        """Clear regrouping list."""
        self.regrouping_units.clear()


class TargetPrioritization:
    """Advanced target prioritization AI."""
    
    def __init__(self) -> None:
        self.priority_rules: List[str] = []
        self.focus_fire_targets: Dict[str, List[Any]] = {}
        self.priority_weights = {
            "threat_level": 0.4,
            "distance": 0.3,
            "unit_type": 0.2,
            "armor": 0.1
        }
    
    def compute_priority_score(self, own_unit: Any, enemy_unit: Any, 
                             threat: float, distance: float) -> float:
        """Compute comprehensive priority score."""
        score = 0.0
        
        # Threat component (higher threat = higher priority)
        threat_score = min(threat, 100.0) / 100.0
        score += threat_score * self.priority_weights["threat_level"]
        
        # Distance component (closer = higher priority)
        distance_score = max(0, 1.0 - distance / 300.0)
        score += distance_score * self.priority_weights["distance"]
        
        # Focus fire bonus
        if enemy_unit in self.focus_fire_targets.get("active", []):
            score += 0.3
        
        return score
    
    def add_focus_fire_target(self, target_unit: Any) -> None:
        """Add unit to focus fire list."""
        if "active" not in self.focus_fire_targets:
            self.focus_fire_targets["active"] = []
        self.focus_fire_targets["active"].append(target_unit)
    
    def clear_focus_fire(self) -> None:
        """Clear focus fire targeting."""
        self.focus_fire_targets["active"] = []


class MicroCoordinator:
    """Coordinate multiple micro systems."""
    
    def __init__(self) -> None:
        self.behaviors: Dict[Any, UnitBehavior] = {}
        self.engagement = EngagementLogic()
        self.formation = FormationManager()
        self.retreat = RetreatSystem()
        self.targeting = TargetPrioritization()
    
    def execute_micro_frame(self, own_units: List[Any], enemy_units: List[Any], 
                           current_frame: int) -> Dict[Any, Dict[str, Any]]:
        """Execute one frame of micro control."""
        commands = {}
        
        # Update threat map
        for enemy in enemy_units:
            threat = self.engagement.evaluate_threat(enemy, distance=50, damage_per_hit=10)
            self.engagement.threat_map[enemy] = threat
        
        # Process each own unit
        for unit in own_units:
            if unit not in self.behaviors:
                self.behaviors[unit] = UnitBehavior(unit)
            
            behavior = self.behaviors[unit]
            behavior.update_state(current_frame, len(enemy_units) > 0, health_pct=75.0)
            
            # Generate commands
            if behavior.should_retreat():
                safe_loc = self.retreat.find_safe_retreat_location((50, 50))
                commands[unit] = {"action": "move", "target": safe_loc}
            elif behavior.should_attack():
                target = self.engagement.select_primary_target(enemy_units, unit)
                if target:
                    commands[unit] = {"action": "attack", "target": target}
            else:
                # Move to formation position
                formation_pos = self.formation.compute_formation_position(unit, len(commands), len(own_units))
                commands[unit] = {"action": "move", "target": formation_pos}
        
        return commands
