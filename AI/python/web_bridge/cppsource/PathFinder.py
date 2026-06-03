"""Python counterpart of C++ PathFinder.cpp / PathFinder.h."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Tuple


class PathFinder:
    _instance: ClassVar[Optional["PathFinder"]] = None

    def __init__(self) -> None:
        self.small_chokepoints_closed_ = False
        self.ramp_high_ground_: Dict[Any, Tuple[int, int]] = {}

    @classmethod
    def Instance(cls) -> "PathFinder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self.small_chokepoints_closed_ = False
        self.ramp_high_ground_.clear()
        self.update(snapshot)

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        self.ramp_high_ground_.clear()
        for entry in snapshot.get("ramp_high_ground", []):
            if isinstance(entry, dict) and "ramp" in entry and "position" in entry:
                ramp = str(entry["ramp"])
                position = entry["position"]
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    self.ramp_high_ground_[ramp] = (int(position[0]), int(position[1]))

    def close_small_chokepoints_if_needed(self) -> None:
        self.small_chokepoints_closed_ = True

    def first_common_path_position(self, position: Tuple[int, int], destinations: List[Tuple[int, int]]) -> Tuple[int, int]:
        return tuple(destinations[0]) if destinations else tuple(position)

    def ramp_high_ground(self, ramp_name: Any) -> Optional[Tuple[int, int]]:
        return self.ramp_high_ground_.get(str(ramp_name))

    def execute_path(self, unit: Any, position: Tuple[int, int], command) -> bool:
        command()
        return True

