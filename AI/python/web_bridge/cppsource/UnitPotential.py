"""Python counterpart of C++ UnitPotential.cpp / UnitPotential.h."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class UnitPotential:
    unit_id: object = None
    position: Tuple[int, int] = (0, 0)
    value: float = 0.0

    def update(self, position: Tuple[int, int], value: float) -> None:
        self.position = (int(position[0]), int(position[1]))
        self.value = float(value)
