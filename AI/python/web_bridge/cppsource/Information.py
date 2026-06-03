"""Python counterpart of C++ Information.cpp / Information.h."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Tuple


@dataclass
class InformationUnit:
    unit_id: Any = None
    unit: Any = None
    player: Any = None
    owner: str = "neutral"
    first_frame: int = -1
    start_frame: int = -1
    last_seen_frame: int = -1
    stasis_end_frame: int = -1
    lockdown_end_frame: int = -1
    maelstrom_end_frame: int = -1
    hitpoints: int = 0
    shields: int = 0
    frame: int = 0
    type: str = "None"
    position: Tuple[int, int] = (0, 0)
    flying: bool = False
    burrowed: bool = False
    burrowed_and_should_be_detected_frame: int = 2**31 - 1
    area: Any = None
    base_distance: int = 0
    destroy_neutral: bool = False
    completed: bool = True

    def is_current(self, current_frame: int) -> bool:
        return self.frame == current_frame

    def complete_frame(self) -> int:
        return self.start_frame

    def is_completed(self) -> bool:
        return bool(self.completed)

    def is_stasised(self, current_frame: int) -> bool:
        return self.stasis_end_frame > current_frame

    def is_disabled(self, current_frame: int) -> bool:
        return (
            self.stasis_end_frame > current_frame
            or self.lockdown_end_frame > current_frame
            or self.maelstrom_end_frame > current_frame
        )

    def detection_range(self) -> int:
        """Get detection range if this unit is a detector."""
        # Building detectors: 7 tiles, unit detectors: sight range
        return 224 if not self.is_disabled(0) else -1

    def tile_position(self) -> Tuple[int, int]:
        """Get tile position from center position."""
        x = self.position[0] // 32
        y = self.position[1] // 32
        return (x, y)

    def update(self, unit: Any, frame: int) -> None:
        """Update unit information from game state."""
        self.unit = unit
        self.frame = frame
        self.hitpoints = unit.get('hp', 0) if isinstance(unit, dict) else 0
        self.shields = unit.get('shields', 0) if isinstance(unit, dict) else 0
        self.position = unit.get('pos', (0, 0)) if isinstance(unit, dict) else (0, 0)
        self.type = unit.get('type', 'None') if isinstance(unit, dict) else 'None'
        self.flying = unit.get('flying', False) if isinstance(unit, dict) else False
        self.burrowed = unit.get('burrowed', False) if isinstance(unit, dict) else False
        self.completed = unit.get('completed', True) if isinstance(unit, dict) else True


@dataclass
class InformationManager:
    """Singleton for managing game information and unit tracking."""
    
    _instance: ClassVar[Optional['InformationManager']] = None
    
    all_units_: Dict[int, InformationUnit] = None
    my_units_: List[InformationUnit] = None
    neutral_units_: List[InformationUnit] = None
    enemy_units_: List[InformationUnit] = None
    enemy_building_seen_: bool = False
    enemy_count_: Dict[str, int] = None
    enemy_completed_count_: Dict[str, int] = None
    enemy_seen_: set = None
    enemy_seen_count_: Dict[str, int] = None
    
    def __post_init__(self):
        if self.all_units_ is None:
            self.all_units_ = {}
        if self.my_units_ is None:
            self.my_units_ = []
        if self.neutral_units_ is None:
            self.neutral_units_ = []
        if self.enemy_units_ is None:
            self.enemy_units_ = []
        if self.enemy_count_ is None:
            self.enemy_count_ = {}
        if self.enemy_completed_count_ is None:
            self.enemy_completed_count_ = {}
        if self.enemy_seen_ is None:
            self.enemy_seen_ = set()
        if self.enemy_seen_count_ is None:
            self.enemy_seen_count_ = {}
    
    @classmethod
    def Instance(cls) -> 'InformationManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = InformationManager()
        return cls._instance
    
    def update_units_and_buildings(self, snapshot: Dict[str, Any]) -> None:
        """Update all unit and building information from game snapshot."""
        frame = snapshot.get('frame', 0)
        
        # Clear and rebuild unit lists
        self.my_units_ = []
        self.enemy_units_ = []
        self.neutral_units_ = []
        
        # Process units from snapshot
        for unit_data in snapshot.get('units', []):
            unit_id = unit_data.get('id', 0)
            owner = unit_data.get('owner', 'neutral')
            
            if unit_id not in self.all_units_:
                self.all_units_[unit_id] = InformationUnit()
            
            info_unit = self.all_units_[unit_id]
            info_unit.update(unit_data, frame)
            
            if owner == 'self':
                self.my_units_.append(info_unit)
            elif owner == 'enemy':
                self.enemy_units_.append(info_unit)
            else:
                self.neutral_units_.append(info_unit)
    
    def update_information(self) -> None:
        """Update derived information and statistics."""
        # Update enemy unit counts
        self.enemy_count_ = {}
        self.enemy_completed_count_ = {}
        
        for enemy in self.enemy_units_:
            unit_type = enemy.type
            self.enemy_count_[unit_type] = self.enemy_count_.get(unit_type, 0) + 1
            if enemy.is_completed():
                self.enemy_completed_count_[unit_type] = self.enemy_completed_count_.get(unit_type, 0) + 1
    
    def all_units(self) -> Dict[int, InformationUnit]:
        """Get all units."""
        return self.all_units_
    
    def my_units(self) -> List[InformationUnit]:
        """Get my units."""
        return self.my_units_
    
    def enemy_units(self) -> List[InformationUnit]:
        """Get enemy units."""
        return self.enemy_units_
    
    def enemy_count(self, unit_type: str) -> int:
        """Get count of specific enemy unit type."""
        return self.enemy_count_.get(unit_type, 0)
    
    def enemy_completed_exists(self, unit_type: str) -> bool:
        """Check if completed enemy unit type exists."""
        return self.enemy_completed_count_.get(unit_type, 0) > 0
    
    def on_unit_destroy(self, unit: Any) -> None:
        """Called when a unit is destroyed."""
        pass
    
    def on_unit_discover(self, unit: Any) -> None:
        """Called when a unit is discovered."""
        pass
    
    def on_unit_evade(self, unit: Any) -> None:
        """Called when a unit evades."""
        pass
    
    def draw(self) -> None:
        """Draw debug information."""
        pass

    def expected_hitpoints(self, current_frame: int) -> int:
        return self.hitpoints

    def expected_shields(self, current_frame: int) -> int:
        return self.shields

    def tile_position(self) -> Tuple[int, int]:
        return self.position

    def detection_range(self, current_frame: int) -> int:
        return -1

    def update(self, a_unit: Dict[str, Any], current_frame: int) -> None:
        self.unit = a_unit
        self.unit_id = a_unit.get("id", self.unit_id)
        self.player = a_unit.get("player")
        self.owner = str(a_unit.get("owner") or a_unit.get("team") or a_unit.get("side") or self.owner)
        if self.first_frame == -1:
            self.first_frame = current_frame
        if self.start_frame == -1:
            self.start_frame = current_frame
        self.frame = current_frame
        self.last_seen_frame = current_frame
        self.type = str(a_unit.get("type") or "None")
        self.position = (int(a_unit.get("x") or 0), int(a_unit.get("y") or 0))
        self.flying = bool(a_unit.get("flying"))
        self.burrowed = bool(a_unit.get("burrowed"))
        self.hitpoints = int(a_unit.get("hitpoints") or 0)
        self.shields = int(a_unit.get("shields") or 0)
        self.area = a_unit.get("area")
        self.base_distance = int(a_unit.get("base_distance") or 0)
        self.completed = bool(a_unit.get("completed", a_unit.get("is_completed", True)))
        self.destroy_neutral = bool(a_unit.get("destroy_neutral", self.destroy_neutral))

    def clean_outdated_unit_position(self) -> None:
        return None


class InformationManager:
    _instance: ClassVar[Optional["InformationManager"]] = None

    def __init__(self) -> None:
        self.all_units_: Dict[Any, InformationUnit] = {}
        self.my_units_: List[InformationUnit] = []
        self.neutral_units_: List[InformationUnit] = []
        self.enemy_units_: List[InformationUnit] = []
        self.enemy_count_: Dict[str, int] = {}
        self.enemy_completed_count_: Dict[str, int] = {}
        self.enemy_seen_: set[str] = set()
        self.enemy_seen_count_: Dict[str, int] = {}
        self.upgrades_: Dict[Any, Dict[Any, int]] = {}
        self.bullet_timestamps_: Dict[int, int] = {}
        self.bunker_marines_loaded_: Dict[Any, List[int]] = {}
        self.self_race_: str = "Unknown"
        self.enemy_race_: str = "Unknown"
        self.self_player_: Any = None
        self.enemy_player_: Any = None
        self._seen_unit_ids: set[Any] = set()

    @classmethod
    def Instance(cls) -> "InformationManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update_units_and_buildings(self, snapshot: Optional[Dict[str, Any]] = None, current_frame: int = 0) -> None:
        snapshot = snapshot or {}
        self.my_units_.clear()
        self.neutral_units_.clear()
        self.enemy_units_.clear()
        self._seen_unit_ids.clear()

        self.self_race_ = str(snapshot.get("self_race") or snapshot.get("race") or self.self_race_)
        self.enemy_race_ = str(snapshot.get("enemy_race") or self.enemy_race_)
        self.self_player_ = snapshot.get("self_player", self.self_player_)
        self.enemy_player_ = snapshot.get("enemy_player", self.enemy_player_)

        self._sync_units(snapshot.get("own_units", []), current_frame, self.my_units_, owner_hint="self")
        self._sync_units(snapshot.get("enemy_units", []), current_frame, self.enemy_units_, owner_hint="enemy")
        self._sync_units(snapshot.get("neutral_units", []), current_frame, self.neutral_units_, owner_hint="neutral")

        stale_ids = [unit_id for unit_id in self.all_units_.keys() if unit_id not in self._seen_unit_ids]
        for unit_id in stale_ids:
            self.all_units_.pop(unit_id, None)

        self.update_enemy_count()

    def _sync_units(
        self,
        units: Any,
        current_frame: int,
        target: List[InformationUnit],
        owner_hint: str,
    ) -> None:
        if not isinstance(units, list):
            return

        for unit in units:
            if not isinstance(unit, dict):
                continue
            unit_id = unit.get("id")
            key = unit_id if unit_id is not None else (owner_hint, len(self.all_units_) + len(target))
            info = self.all_units_.get(key)
            if info is None:
                info = InformationUnit()
                self.all_units_[key] = info
            info.update(unit, current_frame)
            self._seen_unit_ids.add(key)
            target.append(info)

    def update_information(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        if "self_race" in snapshot or "enemy_race" in snapshot:
            self.self_race_ = str(snapshot.get("self_race") or snapshot.get("race") or self.self_race_)
            self.enemy_race_ = str(snapshot.get("enemy_race") or self.enemy_race_)
        if "self_player" in snapshot:
            self.self_player_ = snapshot.get("self_player")
        if "enemy_player" in snapshot:
            self.enemy_player_ = snapshot.get("enemy_player")
        self.update_enemy_count()
        self._update_upgrades(snapshot)

    def draw(self) -> None:
        return None

    def onUnitDestroy(self, unit: Any) -> None:
        unit_id = unit if isinstance(unit, int) else getattr(unit, "id", None)
        if unit_id in self.all_units_:
            del self.all_units_[unit_id]
        self.my_units_ = [info for info in self.my_units_ if info.unit_id != unit_id]
        self.enemy_units_ = [info for info in self.enemy_units_ if info.unit_id != unit_id]
        self.neutral_units_ = [info for info in self.neutral_units_ if info.unit_id != unit_id]

    def onUnitDiscover(self, unit: Any) -> None:
        return None

    def onUnitEvade(self, unit: Any) -> None:
        return None

    def all_units(self) -> Dict[Any, InformationUnit]:
        return dict(self.all_units_)

    def my_units(self) -> List[InformationUnit]:
        return list(self.my_units_)

    def neutral_units(self) -> List[InformationUnit]:
        return list(self.neutral_units_)

    def enemy_units(self) -> List[InformationUnit]:
        return list(self.enemy_units_)

    def mark_neutral_for_destruction(self, unit: Any, destroy: bool = True) -> None:
        return None

    def enemy_building_seen(self) -> bool:
        return any(self._is_building_type(unit.type) for unit in self.enemy_units_)

    def enemy_count(self, unit_type: str) -> int:
        return int(self.enemy_count_.get(str(unit_type), 0))

    def enemy_seen(self, unit_type: str) -> bool:
        return str(unit_type) in self.enemy_seen_

    def enemy_seen_count(self, unit_type: str) -> int:
        return int(self.enemy_seen_count_.get(str(unit_type), 0))

    def enemy_exists(self, unit_type: str) -> bool:
        return self.enemy_count(unit_type) > 0

    def enemy_completed_exists(self, unit_type: str) -> bool:
        return int(self.enemy_completed_count_.get(str(unit_type), 0)) > 0

    def upgrade_level(self, player: Any, upgrade_type: Any) -> int:
        return int(self.upgrades_.get(player, {}).get(upgrade_type, 0))

    def enemy_has_upgrade(self, upgrade_type: Any) -> bool:
        if self.enemy_player_ is None:
            return False
        return int(self.upgrades_.get(self.enemy_player_, {}).get(upgrade_type, 0)) > 0

    def no_enemy_has_upgrade(self, upgrade_type: Any) -> bool:
        return not self.enemy_has_upgrade(upgrade_type)

    def bunker_marines_loaded(self, bunker: Any) -> int:
        return max(self.bunker_marines_loaded_.get(bunker, [0])) if bunker in self.bunker_marines_loaded_ else 0

    def unit(self, unit_id: Any) -> Optional[InformationUnit]:
        return self.all_units_.get(unit_id)

    def self_race(self) -> str:
        return self.self_race_

    def enemy_race(self) -> str:
        return self.enemy_race_

    def update_enemy_count(self) -> None:
        self.enemy_count_.clear()
        self.enemy_completed_count_.clear()
        self.enemy_seen_.clear()
        for unit in self.enemy_units_:
            self.enemy_count_[unit.type] = self.enemy_count_.get(unit.type, 0) + 1
            self.enemy_seen_.add(unit.type)
            if unit.is_completed():
                self.enemy_completed_count_[unit.type] = self.enemy_completed_count_.get(unit.type, 0) + 1
            self.enemy_seen_count_[unit.type] = self.enemy_seen_count_.get(unit.type, 0) + 1

    def _update_upgrades(self, snapshot: Dict[str, Any]) -> None:
        upgrades = snapshot.get("upgrades") or {}
        for player, upgrade_map in upgrades.items():
            self.upgrades_[player] = {k: int(v) for k, v in upgrade_map.items()}

    @staticmethod
    def _is_building_type(unit_type: str) -> bool:
        unit_type = str(unit_type or "")
        return unit_type.endswith(
            (
                "Nexus",
                "Command_Center",
                "Hatchery",
                "Lair",
                "Hive",
                "Gateway",
                "Forge",
                "Pylon",
                "Barracks",
                "Factory",
                "Starport",
                "Spawning_Pool",
                "Hydralisk_Den",
                "Sunken_Colony",
                "Spore_Colony",
                "Evolution_Chamber",
                "Extractor",
                "Assimilator",
                "Refinery",
            )
        )
