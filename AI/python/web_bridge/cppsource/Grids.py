"""Grid systems for spatial indexing.

C++ equivalent: Grids.cpp/Grids.h

Implements three grid types:
- TileGrid: 256x256 tile-based grid
- WalkGrid: 4*256x4*256 walk-based grid
- SparsePositionGrid: Sparse position-centered grid
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

T = TypeVar('T')

MAP_WIDTH = 256
MAP_HEIGHT = 256


@dataclass
class TileGrid(Generic[T]):
    """Grid indexed by tile positions (256x256)."""
    
    data_: list = field(default_factory=lambda: [None] * (256 * 256), init=False)
    
    def clear(self, default_value: Optional[T] = None) -> None:
        """Clear all grid values."""
        self.data_ = [default_value] * (256 * 256)
    
    def get(self, x: int, y: int) -> Optional[T]:
        """Get value at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            return self.data_[y * 256 + x]
        return None
    
    def set(self, x: int, y: int, value: T) -> None:
        """Set value at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            self.data_[y * 256 + x] = value
    
    def __getitem__(self, key: tuple) -> Optional[T]:
        """Support grid[x, y] syntax."""
        if isinstance(key, tuple):
            return self.get(key[0], key[1])
        return None
    
    def __setitem__(self, key: tuple, value: T) -> None:
        """Support grid[x, y] = value syntax."""
        if isinstance(key, tuple):
            self.set(key[0], key[1], value)


@dataclass
class WalkGrid(Generic[T]):
    """Grid indexed by walk positions (4*256 x 4*256)."""
    
    data_: list = field(default_factory=lambda: [None] * (4 * 256 * 4 * 256), init=False)
    
    def clear(self, default_value: Optional[T] = None) -> None:
        """Clear all grid values."""
        self.data_ = [default_value] * (4 * 256 * 4 * 256)
    
    def get(self, x: int, y: int) -> Optional[T]:
        """Get value at walk position."""
        if 0 <= x < 4 * 256 and 0 <= y < 4 * 256:
            return self.data_[y * 4 * 256 + x]
        return None
    
    def set(self, x: int, y: int, value: T) -> None:
        """Set value at walk position."""
        if 0 <= x < 4 * 256 and 0 <= y < 4 * 256:
            self.data_[y * 4 * 256 + x] = value


@dataclass
class WalkabilityGrid:
    """Grid tracking walkable positions."""
    
    data_: list = field(default_factory=lambda: [True] * (4 * 256 * 4 * 256), init=False)
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable."""
        if 0 <= x < 4 * 256 and 0 <= y < 4 * 256:
            return self.data_[y * 4 * 256 + x]
        return False
    
    def set_walkable(self, x: int, y: int, walkable: bool) -> None:
        """Set walkability of position."""
        if 0 <= x < 4 * 256 and 0 <= y < 4 * 256:
            self.data_[y * 4 * 256 + x] = walkable


@dataclass
class ThreatGrid:
    """Grid tracking threat levels from enemies."""
    
    data_: list = field(default_factory=lambda: [0.0] * (256 * 256), init=False)
    
    def get_threat(self, x: int, y: int) -> float:
        """Get threat level at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            return self.data_[y * 256 + x]
        return 0.0
    
    def set_threat(self, x: int, y: int, threat: float) -> None:
        """Set threat level at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            self.data_[y * 256 + x] = threat
    
    def update(self) -> None:
        """Update threat grid from enemy positions."""
        pass


@dataclass
class UnitGrid:
    """Grid tracking unit positions for spatial lookup."""
    
    data_: list = field(default_factory=lambda: [[] for _ in range(256 * 256)], init=False)
    
    def clear(self) -> None:
        """Clear all unit positions."""
        self.data_ = [[] for _ in range(256 * 256)]
    
    def add_unit(self, x: int, y: int, unit: Any) -> None:
        """Add unit at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            self.data_[y * 256 + x].append(unit)
    
    def get_units(self, x: int, y: int) -> list:
        """Get units at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            return self.data_[y * 256 + x]
        return []


@dataclass
class RoomGrid:
    """Grid tracking room/area connectivity."""
    
    data_: list = field(default_factory=lambda: [None] * (256 * 256), init=False)
    
    def get_room(self, x: int, y: int) -> Optional[Any]:
        """Get room/area at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            return self.data_[y * 256 + x]
        return None
    
    def set_room(self, x: int, y: int, room: Any) -> None:
        """Set room/area at tile position."""
        if 0 <= x < 256 and 0 <= y < 256:
            self.data_[y * 256 + x] = room
    
    def invalidate(self) -> None:
        """Invalidate room grid (requires recalculation)."""
        pass


# Global grid singletons
walkability_grid: Optional[WalkabilityGrid] = None
threat_grid: Optional[ThreatGrid] = None
unit_grid: Optional[UnitGrid] = None
room_grid: Optional[RoomGrid] = None

def init_grids() -> None:
    """Initialize all grid singletons."""
    global walkability_grid, threat_grid, unit_grid, room_grid
    walkability_grid = WalkabilityGrid()
    threat_grid = ThreatGrid()
    unit_grid = UnitGrid()
    room_grid = RoomGrid()


class TileGrid:
    def __init__(self) -> None:
        self._data: Dict[Tuple[int, int], Any] = {}

    def clear(self) -> None:
        self._data.clear()

    def get(self, tile_position: Tuple[int, int], default: Any = None) -> Any:
        return self._data.get(tuple(tile_position), default)

    def set(self, tile_position: Tuple[int, int], value: Any) -> None:
        self._data[tuple(tile_position)] = value


class WalkGrid(TileGrid):
    def is_walkable(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.get(tile_position, False))


class SparsePositionGrid:
    def __init__(self, center: Tuple[int, int]) -> None:
        self._center = tuple(center)
        self._data: Dict[Tuple[int, int], Any] = {}

    def clear(self) -> None:
        self._data.clear()

    def center(self) -> Tuple[int, int]:
        return self._center

    def get(self, position: Tuple[int, int], default: Any = None) -> Any:
        return self._data.get(tuple(position), default)

    def set(self, position: Tuple[int, int], value: Any) -> None:
        self._data[tuple(position)] = value


class WalkabilityGrid:
    _instance: ClassVar[Optional["WalkabilityGrid"]] = None

    def __init__(self) -> None:
        self.terrain_walkable_ = TileGrid()
        self.walkable_ = TileGrid()

    @classmethod
    def Instance(cls) -> "WalkabilityGrid":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(self) -> None:
        self.terrain_walkable_.clear()
        self.walkable_.clear()

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        for entry in snapshot.get("walkable_tiles", []):
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                self.walkable_.set((int(entry[0]), int(entry[1])), True)

    def is_terrain_walkable(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.terrain_walkable_.get(tile_position, False))

    def is_walkable(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.walkable_.get(tile_position, False))

    def walkable_tile_near(self, position: Tuple[int, int], range_: int) -> Tuple[int, int]:
        return tuple(position)


class ConnectivityGrid:
    _instance: ClassVar[Optional["ConnectivityGrid"]] = None

    def __init__(self) -> None:
        self.valid_ = False
        self.component_ = TileGrid()

    @classmethod
    def Instance(cls) -> "ConnectivityGrid":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.valid_ = True
        snapshot = snapshot or {}
        for entry in snapshot.get("connectivity", []):
            if isinstance(entry, dict) and "tile" in entry:
                tile = entry["tile"]
                if isinstance(tile, (list, tuple)) and len(tile) == 2:
                    self.component_.set((int(tile[0]), int(tile[1])), int(entry.get("component", 0)))

    def invalidate(self) -> None:
        self.valid_ = False

    def component_for_position(self, tile_position: Tuple[int, int]) -> int:
        return int(self.component_.get(tile_position, 0) or 0)

    def component_and_tile_for_position(self, position: Tuple[int, int]) -> Tuple[int, Tuple[int, int]]:
        return self.component_for_position(position), tuple(position)

    def check_reachability(self, combat_unit: Any, enemy_unit: Any) -> bool:
        return True

    def check_reachability_melee(self, component: int, enemy_unit: Any) -> bool:
        return True

    def check_reachability_ranged(self, component: int, range_: int, enemy_unit: Any) -> bool:
        return True

    def building_has_component(self, unit_type: Any, tile_position: Tuple[int, int], component: int) -> bool:
        return self.component_for_position(tile_position) == component

    def building_components(self, unit_type: Any, tile_position: Tuple[int, int]) -> set[int]:
        return {self.component_for_position(tile_position)}

    def is_wall_building(self, unit: Any) -> bool:
        return False

    def wall_building_perimeter(self, unit: Any, component: int) -> int:
        return 0


class ThreatGrid:
    class ThreatComponentGrid:
        def __init__(self) -> None:
            self.component_grid_ = TileGrid()

        def component(self, tile_position: Tuple[int, int]) -> int:
            return int(self.component_grid_.get(tile_position, 0) or 0)

        def component_from_position(self, position: Tuple[int, int]) -> int:
            return self.component(position)

    _instance: ClassVar[Optional["ThreatGrid"]] = None

    def __init__(self) -> None:
        self.ground_threat_ = TileGrid()
        self.air_threat_ = TileGrid()
        self.ground_threat_excluding_workers_ = TileGrid()
        self.ground_component_ = ThreatGrid.ThreatComponentGrid()
        self.air_component_ = ThreatGrid.ThreatComponentGrid()
        self.cloaked_air_threat_component_ = ThreatGrid.ThreatComponentGrid()
        self.air_cross_component_ = ThreatGrid.ThreatComponentGrid()
        self.ground_splash_distance_ = TileGrid()

    @classmethod
    def Instance(cls) -> "ThreatGrid":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        self.ground_threat_.clear()
        self.air_threat_.clear()
        for entry in snapshot.get("enemy_threat", []):
            if isinstance(entry, dict) and "tile" in entry:
                tile = entry["tile"]
                if isinstance(tile, (list, tuple)) and len(tile) == 2:
                    self.ground_threat_.set((int(tile[0]), int(tile[1])), bool(entry.get("ground", False)))
                    self.air_threat_.set((int(tile[0]), int(tile[1])), bool(entry.get("air", False)))

    def ground_threat(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.ground_threat_.get(tile_position, False))

    def air_threat(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.air_threat_.get(tile_position, False))

    def threat(self, tile_position: Tuple[int, int], air: bool) -> bool:
        return self.air_threat(tile_position) if air else self.ground_threat(tile_position)

    def ground_threat_excluding_workers(self, tile_position: Tuple[int, int]) -> bool:
        return bool(self.ground_threat_excluding_workers_.get(tile_position, False))

    def component_grid(self, type_: Any) -> "ThreatGrid.ThreatComponentGrid":
        return self.ground_component_

    def ground_splash_distance(self, tile_position: Tuple[int, int]) -> int:
        return int(self.ground_splash_distance_.get(tile_position, 0) or 0)

    def draw(self, air: bool) -> None:
        return None


class UnitGrid:
    _instance: ClassVar[Optional["UnitGrid"]] = None

    def __init__(self) -> None:
        self.units_ = []

    @classmethod
    def Instance(cls) -> "UnitGrid":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.units_ = list((snapshot or {}).get("units", []))


class RoomGrid:
    _instance: ClassVar[Optional["RoomGrid"]] = None

    def __init__(self) -> None:
        self.rooms_ = []

    @classmethod
    def Instance(cls) -> "RoomGrid":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.rooms_ = list((snapshot or {}).get("rooms", []))
