"""Python counterpart of C++ Results.cpp / Results.h."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from typing import Any, Dict, Iterable, List, Optional, TextIO


@dataclass
class Result:
    opening: str = "unknown"
    wins: int = 0
    losses: int = 0
    games: int = 0
    raw: str = ""


class ResultStore:
    def __init__(self) -> None:
        self._stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    def read_file(self, f: TextIO, results: List[Result]) -> None:
        if f is None:
            return

        for raw_line in f:
            line = str(raw_line).strip()
            if not line or line.startswith("#"):
                continue

            parsed = self._parse_result_line(line)
            if parsed is None:
                continue

            result = Result(
                opening=str(parsed.get("opening") or parsed.get("name") or "unknown"),
                wins=int(parsed.get("wins", 0)),
                losses=int(parsed.get("losses", 0)),
                games=int(parsed.get("games", 0)),
                raw=line,
            )
            if result.games <= 0:
                result.games = result.wins + result.losses
            results.append(result)
            if result.games > 0:
                for _ in range(result.wins):
                    self.record(result.opening, True)
                for _ in range(result.losses):
                    self.record(result.opening, False)

    def record(self, opening: str, won: bool) -> None:
        entry = self._stats[str(opening)]
        if won:
            entry["wins"] += 1
        else:
            entry["losses"] += 1

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        return {opening: dict(values) for opening, values in self._stats.items()}

    def reset(self) -> None:
        self._stats.clear()

    def record_snapshot(self, snapshot: Dict[str, Any]) -> None:
        opening = str(snapshot.get("opening") or snapshot.get("strategy_opening") or "unknown")
        won = bool(snapshot.get("won", False))
        self.record(opening, won)

    def merge(self, stats: Dict[str, Dict[str, int]]) -> None:
        for opening, values in (stats or {}).items():
            entry = self._stats[str(opening)]
            entry["wins"] += int(values.get("wins", 0))
            entry["losses"] += int(values.get("losses", 0))

    def best_opening(self) -> Optional[str]:
        best_name: Optional[str] = None
        best_score = -1.0
        for opening, values in self._stats.items():
            games = values["wins"] + values["losses"]
            score = values["wins"] / games if games else 0.0
            if score > best_score:
                best_score = score
                best_name = opening
        return best_name

    def _parse_result_line(self, line: str) -> Optional[Dict[str, Any]]:
        if not line:
            return None

        if line.startswith("{") or line.startswith("["):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data:
                first = data[0]
                return first if isinstance(first, dict) else None

        separators = [",", ";", "\t", "|"]
        for separator in separators:
            if separator in line:
                parts = [part.strip() for part in line.split(separator)]
                if not parts:
                    continue
                parsed: Dict[str, Any] = {"opening": parts[0]}
                if len(parts) > 1:
                    parsed["wins"] = self._safe_int(parts[1])
                if len(parts) > 2:
                    parsed["losses"] = self._safe_int(parts[2])
                if len(parts) > 3:
                    parsed["games"] = self._safe_int(parts[3])
                return parsed

        return {"opening": line}

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
