"""Python counterpart of C++ Utils.h."""

from __future__ import annotations

from typing import Any, Iterable, Tuple


class Utils:
    @staticmethod
    def clamp(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, int(value)))

    @staticmethod
    def manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))

    @staticmethod
    def first(iterable: Iterable[Any], default: Any = None) -> Any:
        for item in iterable:
            return item
        return default
