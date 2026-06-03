"""Python counterpart of C++ WallPlacement.cpp / WallPlacement.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class WallPlacement:
    main_wall: List[Tuple[int, int]] = field(default_factory=list)
    natural_wall: List[Tuple[int, int]] = field(default_factory=list)
    choke_points: List[Tuple[int, int]] = field(default_factory=list)

    def set_main_wall(self, positions: List[Tuple[int, int]]) -> None:
        self.main_wall = [(int(x), int(y)) for x, y in positions]

    def set_natural_wall(self, positions: List[Tuple[int, int]]) -> None:
        self.natural_wall = [(int(x), int(y)) for x, y in positions]

    def update_from_snapshot(self, snapshot: Dict[str, object]) -> None:
        self.choke_points = [tuple(point) for point in snapshot.get("choke_points", []) if isinstance(point, (list, tuple)) and len(point) == 2]
