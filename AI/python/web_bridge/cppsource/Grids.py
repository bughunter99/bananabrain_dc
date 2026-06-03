"""Python counterpart of C++ Grids.cpp / Grids.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple


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
