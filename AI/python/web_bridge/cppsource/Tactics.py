"""Tactical combat management.

C++ equivalent: Tactics.cpp/Tactics.h

Manages:
- Enemy cluster tracking
- Engagement distance calculations
- Front line determination
- Combat supply calculations
"""


from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class EnemyCluster:
    """Represents a cluster of enemy units for tactical analysis."""
    
    # Engagement distances (in pixels)
    ENGAGEMENT_DISTANCE: int = 32
    FRONT_DISTANCE: int = 256
    MAX_FRONT_STRIDE: int = 512
    
    units: List[Any] = field(default_factory=list, init=False)
    engagement_distances: Dict[Any, int] = field(default_factory=dict, init=False)
    front_units: Set[Any] = field(default_factory=set, init=False)
    
    defense_supply: float = 0.0
    front_supply: float = 0.0
    push_through: bool = False
    
    def expect_win(self, unit: Any) -> bool:
        """Check if friendly unit would win engagement."""
        return False
    
    def is_engaged(self, unit: Any) -> bool:
        """Check if unit is currently engaged with enemy."""
        return unit in self.engagement_distances
    
    def is_nearly_engaged(self, unit: Any) -> bool:
        """Check if unit is nearly engaged (within close distance)."""
        return False
    
    def in_front(self, unit: Any) -> bool:
        """Check if unit is in front line."""
        return unit in self.front_units
    
    def stim_allowed(self, unit: Any) -> bool:
        """Check if stimmed unit is allowed."""
        return False
    
    def in_front_with_supply_at_least(self, unit: Any, supply: int) -> bool:
        """Check if front units have at least specified supply."""
        return False
    
    def calculate_engagement_distances(self) -> None:
        """Calculate distances to all enemy units."""
        pass
    
    def determine_front(self) -> None:
        """Determine front line units."""
        pass
    
    def calculate_defense_supply(self) -> None:
        """Calculate defensive unit supply values."""
        pass


@dataclass
class TacticsManager:
    """Singleton for managing tactical decisions."""
    
    _instance: Optional['TacticsManager'] = None
    
    enemy_clusters: List[EnemyCluster] = field(default_factory=list, init=False)
    current_cluster: Optional[EnemyCluster] = None
    
    @classmethod
    def Instance(cls) -> 'TacticsManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def update(self, enemy_units: List[Any]) -> None:
        """Update tactical analysis from enemy units."""
        if enemy_units:
            self.current_cluster = EnemyCluster()
            self.current_cluster.units = enemy_units
            self.current_cluster.calculate_engagement_distances()
            self.current_cluster.determine_front()
            self.current_cluster.calculate_defense_supply()
    
    def draw(self) -> None:
        """Draw tactical debug information."""
        pass


from typing import Any


from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple


kEngagementDistance = 192


@dataclass
class EnemyCluster:
    unit_ids: List[Any] = field(default_factory=list)
    friendly_units_ascending_distance_: List[Tuple[Any, int]] = field(default_factory=list)
    center: Tuple[int, int] = (0, 0)
    radius: int = 0
    threat: int = 0
    last_seen_frame: int = -1

    def contains(self, unit_id: Any) -> bool:
        return unit_id in self.unit_ids

    def size(self) -> int:
        return len(self.unit_ids)

    def add_friendly_unit(self, unit: Any, distance: int) -> None:
        self.friendly_units_ascending_distance_.append((unit, int(distance)))
        self.friendly_units_ascending_distance_.sort(key=lambda entry: entry[1])

    def is_nearly_engaged(self) -> bool:
        return bool(
            self.friendly_units_ascending_distance_
            and self.friendly_units_ascending_distance_[0][1] <= kEngagementDistance
        )

    def closest_friendly_unit(self) -> Optional[Any]:
        if not self.friendly_units_ascending_distance_:
            return None
        return self.friendly_units_ascending_distance_[0][0]


class TacticsManager:
    _instance: ClassVar[Optional["TacticsManager"]] = None

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {
            "enemy_pressure": "low",
            "should_attack": False,
            "should_defend": False,
            "army_strength": 0,
            "enemy_army_strength": 0,
            "last_update_frame": -1,
        }
        self._enemy_clusters: List[EnemyCluster] = []

    @classmethod
    def Instance(cls) -> "TacticsManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None, frame: int = 0) -> None:
        snapshot = snapshot or {}
        own_units = self._parse_units(snapshot.get("own_units"))
        enemy_units = self._parse_units(snapshot.get("enemy_units"))
        own_army = self._count_combat_units(own_units)
        enemy_army = self._count_combat_units(enemy_units)
        supply_used = int(snapshot.get("supply_used") or 0)
        supply_total = int(snapshot.get("supply_total") or 0)

        pressure = "low"
        should_defend = False
        should_attack = False
        if enemy_army > own_army + 2:
            pressure = "high"
            should_defend = True
        elif enemy_army > own_army:
            pressure = "medium"
            should_defend = True
        elif own_army >= enemy_army + 3 and supply_total > 0 and supply_used >= max(supply_total - 4, 0):
            pressure = "opportunity"
            should_attack = True

        self._state.update(
            {
                "enemy_pressure": pressure,
                "should_attack": should_attack,
                "should_defend": should_defend,
                "army_strength": own_army,
                "enemy_army_strength": enemy_army,
                "last_update_frame": int(frame),
            }
        )
        self._enemy_clusters = self._build_enemy_clusters(own_units, enemy_units, int(frame))

    def state(self) -> Dict[str, Any]:
        return dict(self._state)

    def enemy_pressure(self) -> str:
        return str(self._state.get("enemy_pressure") or "low")

    def should_attack(self) -> bool:
        return bool(self._state.get("should_attack"))

    def should_defend(self) -> bool:
        return bool(self._state.get("should_defend"))

    def enemy_clusters(self) -> List[EnemyCluster]:
        return list(self._enemy_clusters)

    def strongest_enemy_cluster(self) -> Optional[EnemyCluster]:
        if not self._enemy_clusters:
            return None
        return max(self._enemy_clusters, key=lambda cluster: (cluster.threat, cluster.size()))

    def _parse_units(self, units: Any) -> list[Dict[str, Any]]:
        if not isinstance(units, list):
            return []
        return [unit for unit in units if isinstance(unit, dict)]

    def _count_combat_units(self, units: list[Dict[str, Any]]) -> int:
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

    def _build_enemy_clusters(self, own_units: list[Dict[str, Any]], enemy_units: list[Dict[str, Any]], frame: int) -> List[EnemyCluster]:
        if not enemy_units:
            return []

        clusters: Dict[str, EnemyCluster] = {}
        for unit in enemy_units:
            unit_id = unit.get("id")
            unit_type = str(unit.get("type") or "unknown")
            cluster = clusters.setdefault(
                unit_type,
                EnemyCluster(center=self._unit_position(unit), radius=96, threat=0, last_seen_frame=frame),
            )
            if unit_id is not None:
                cluster.unit_ids.append(unit_id)
            cluster.threat += self._unit_threat(unit_type)
            cluster.last_seen_frame = frame

        for cluster in clusters.values():
            for friendly_unit in own_units:
                cluster.add_friendly_unit(friendly_unit, self._distance(cluster.center, self._unit_position(friendly_unit)))

        return list(clusters.values())

    @staticmethod
    def _unit_position(unit: Dict[str, Any]) -> Tuple[int, int]:
        x = int(unit.get("x") or 0)
        y = int(unit.get("y") or 0)
        return x, y

    @staticmethod
    def _unit_threat(unit_type: str) -> int:
        threat_map = {
            "Protoss_Reaver": 6,
            "Protoss_Dragoon": 3,
            "Protoss_Zealot": 2,
            "Terran_Siege_Tank_Tank_Mode": 5,
            "Terran_Siege_Tank_Siege_Mode": 6,
            "Terran_Marine": 2,
            "Terran_Firebat": 2,
            "Zerg_Lurker": 5,
            "Zerg_Hydralisk": 3,
            "Zerg_Mutalisk": 4,
            "Zerg_Zergling": 1,
        }
        return threat_map.get(unit_type, 1)

    @staticmethod
    def _distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))
