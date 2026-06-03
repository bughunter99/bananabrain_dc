"""Tactical combat management.

C++ equivalent: Tactics.cpp/Tactics.h

Manages:
- Enemy cluster tracking
- Engagement distance calculations
- Front line determination
- Combat supply calculations
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple
import math


# Engagement distances (in pixels)
ENGAGEMENT_DISTANCE = 192
FRONT_DISTANCE = 256
MAX_FRONT_STRIDE = 512


@dataclass
class EnemyCluster:
    """Represents a cluster of enemy units for tactical analysis."""
    
    unit_ids: List[Any] = field(default_factory=list)
    friendly_units_ascending_distance_: List[Tuple[Any, int]] = field(default_factory=list)
    center: Tuple[int, int] = (0, 0)
    radius: int = 0
    threat: int = 0
    last_seen_frame: int = -1
    
    defense_supply: float = 0.0
    front_supply: float = 0.0
    push_through: bool = False
    engagement_distances: Dict[Any, int] = field(default_factory=dict, init=False)
    front_units: Set[Any] = field(default_factory=set, init=False)
    
    def contains(self, unit_id: Any) -> bool:
        """Check if unit is in cluster."""
        return unit_id in self.unit_ids
    
    def size(self) -> int:
        """Get cluster size."""
        return len(self.unit_ids)
    
    def add_friendly_unit(self, unit: Any, distance: int) -> None:
        """Track friendly unit distance to cluster."""
        self.friendly_units_ascending_distance_.append((unit, int(distance)))
        self.friendly_units_ascending_distance_.sort(key=lambda entry: entry[1])
    
    def is_nearly_engaged(self) -> bool:
        """Check if any friendly unit is nearly engaged."""
        return bool(
            self.friendly_units_ascending_distance_
            and self.friendly_units_ascending_distance_[0][1] <= ENGAGEMENT_DISTANCE
        )
    
    def closest_friendly_unit(self) -> Optional[Any]:
        """Get closest friendly unit to cluster."""
        if not self.friendly_units_ascending_distance_:
            return None
        return self.friendly_units_ascending_distance_[0][0]
    
    def expect_win(self, unit: Any) -> bool:
        """Check if friendly unit would win engagement."""
        if self.threat == 0:
            return True
        return False
    
    def is_engaged(self, unit: Any) -> bool:
        """Check if unit is currently engaged with enemy."""
        return unit in self.engagement_distances
    
    def is_nearly_engaged_unit(self, unit: Any) -> bool:
        """Check if unit is nearly engaged."""
        if unit not in self.engagement_distances:
            return False
        return self.engagement_distances[unit] <= ENGAGEMENT_DISTANCE * 2
    
    def in_front(self, unit: Any) -> bool:
        """Check if unit is in front line."""
        return unit in self.front_units
    
    def stim_allowed(self, unit: Any) -> bool:
        """Check if stimmed unit is allowed (has healing support)."""
        return self.is_engaged(unit) and self.defense_supply > 0
    
    def in_front_with_supply_at_least(self, unit: Any, supply_threshold: float) -> bool:
        """Check if front units have at least specified supply."""
        if unit not in self.front_units:
            return False
        return self.front_supply >= supply_threshold
    
    def calculate_engagement_distances(self) -> None:
        """Calculate distances to all enemy units."""
        self.engagement_distances = {}
        # Calculate center and radius
        if self.unit_ids:
            # Simplified: assume unit positions available in context
            self.threat = len(self.unit_ids)
    
    def determine_front(self) -> None:
        """Determine front line units."""
        self.front_units = set(self.unit_ids[:max(1, len(self.unit_ids) // 3)])
    
    def calculate_defense_supply(self) -> None:
        """Calculate defensive unit supply values."""
        self.defense_supply = float(len(self.unit_ids))
        self.front_supply = float(len(self.front_units))


@dataclass
class TacticsManager:
    """Singleton for managing tactical decisions."""
    
    _instance: ClassVar[Optional['TacticsManager']] = None
    
    enemy_clusters: List[EnemyCluster] = field(default_factory=list, init=False)
    current_cluster: Optional[EnemyCluster] = None
    main_cluster: Optional[EnemyCluster] = None
    
    enemy_pressure_: str = "low"  # "low", "medium", "high", "critical"
    should_attack_: bool = False
    should_defend_: bool = False
    army_strength_: int = 0
    
    @classmethod
    def Instance(cls) -> 'TacticsManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize tactics manager."""
        self.enemy_clusters = []
        self.current_cluster = None
        self.main_cluster = None
        self.enemy_pressure_ = "low"
        self.should_attack_ = False
        self.should_defend_ = False
    
    def update(self, enemy_units: Optional[List[Any]] = None, own_units: Optional[List[Any]] = None) -> None:
        """Update tactical analysis from enemy units."""
        self.enemy_clusters = []
        
        if enemy_units:
            # Create main cluster
            cluster = EnemyCluster()
            cluster.unit_ids = enemy_units
            cluster.calculate_engagement_distances()
            cluster.determine_front()
            cluster.calculate_defense_supply()
            
            self.main_cluster = cluster
            self.current_cluster = cluster
            self.enemy_clusters.append(cluster)
            
            # Evaluate pressure
            threat_count = len(enemy_units)
            own_count = len(own_units) if own_units else 0
            
            if threat_count == 0:
                self.enemy_pressure_ = "low"
                self.should_defend_ = False
            elif threat_count >= own_count + 5:
                self.enemy_pressure_ = "critical"
                self.should_defend_ = True
                self.should_attack_ = False
            elif threat_count >= own_count + 2:
                self.enemy_pressure_ = "high"
                self.should_defend_ = True
                self.should_attack_ = False
            elif threat_count > own_count:
                self.enemy_pressure_ = "medium"
                self.should_defend_ = True
            else:
                self.enemy_pressure_ = "low"
                self.should_attack_ = True
                self.should_defend_ = False
            
            self.army_strength_ = threat_count
    
    def is_under_attack(self) -> bool:
        """Check if under enemy attack."""
        return self.enemy_pressure_ in ["medium", "high", "critical"]
    
    def should_attack(self) -> bool:
        """Check if should perform aggressive action."""
        return self.should_attack_
    
    def should_defend(self) -> bool:
        """Check if should perform defensive action."""
        return self.should_defend_
    
    def enemy_pressure(self) -> str:
        """Get current enemy pressure level."""
        return self.enemy_pressure_
    
    def main_enemy_cluster(self) -> Optional[EnemyCluster]:
        """Get main enemy cluster."""
        return self.main_cluster
    
    def draw(self) -> None:
        """Draw tactical debug information."""
        pass
