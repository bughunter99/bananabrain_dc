"""Game result storage and strategy selection.

C++ equivalent: Results.cpp/Results.h

Manages historical game results and selects strategies using:
- Greedy strategy (highest win rate)
- UCB1 algorithm (upper confidence bound)
"""


from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, List, Optional
import random
import datetime
import math


@dataclass
class Result:
    """Single game result record."""
    timestamp: str = ""
    start_positions: int = 0
    start_clock_position: int = 0
    opponent_clock_position: int = 0
    map_name: str = ""
    strategy: str = ""
    late_game_strategy: str = ""
    opponent_strategy: str = ""
    duration: int = 0
    opponent_dark_templar_frame: int = 0
    opponent_mutalisk_frame: int = 0
    opponent_lurker_frame: int = 0
    is_win: bool = False


@dataclass
class ResultStore:
    """Singleton for storing and analyzing game results.
    
    Uses UCB1 or greedy selection to pick best strategies.
    """
    
    _instance: ClassVar[Optional['ResultStore']] = None
    
    prepared_results_: List[Result] = field(default_factory=list, init=False)
    results_: List[Result] = field(default_factory=list, init=False)
    
    DECAY_FACTOR: float = 40.0
    DECAY_FACTOR_TOURNAMENT: float = 3.0
    TARGET_WIN_RATE: float = 0.8
    PRIOR_GAMES: float = 1.5
    
    @classmethod
    def Instance(cls) -> 'ResultStore':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ResultStore()
        return cls._instance
    
    def init(self) -> None:
        """Initialize result store from files."""
        self._read_prepared_results()
        self._read_results()
    
    def _read_prepared_results(self) -> None:
        """Read prepared results from AI directory."""
        try:
            # File path: bwapi-data/AI/Results_{name}.txt
            pass
        except Exception:
            pass
    
    def _read_results(self) -> None:
        """Read game results from read/write directories."""
        try:
            # File paths: bwapi-data/read/Results_{name}.txt
            pass
        except Exception:
            pass
    
    def pick_strategy(self, strategies: List[str]) -> str:
        """Pick best strategy from list.
        
        Uses greedy or UCB1 selection based on configuration.
        
        Args:
            strategies: List of strategy names
            
        Returns:
            Selected strategy name
        """
        if not strategies:
            return ""
        
        if len(strategies) == 1:
            return strategies[0]
        
        # Default: greedy selection (highest win rate)
        return self._pick_strategy_greedy(strategies)
    
    def _pick_strategy_greedy(self, strategies: List[str]) -> str:
        """Pick strategy with highest win rate."""
        best_strategy = strategies[0]
        best_win_rate = 0.0
        
        for strategy in strategies:
            wins = sum(1 for r in self.results_ if r.strategy == strategy and r.is_win)
            total = sum(1 for r in self.results_ if r.strategy == strategy)
            
            if total > 0:
                win_rate = wins / total
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_strategy = strategy
        
        return best_strategy
    
    def _pick_strategy_ucb1(self, strategies: List[str]) -> str:
        """Pick strategy using UCB1 algorithm."""
        import math
        
        best_strategy = strategies[0]
        best_ucb = float('-inf')
        
        for strategy in strategies:
            wins = sum(1 for r in self.results_ if r.strategy == strategy and r.is_win)
            total = max(1, sum(1 for r in self.results_ if r.strategy == strategy))
            
            exploitation = wins / total
            exploration = math.sqrt(math.log(len(self.results_) + 1) / total) if total > 0 else 1.0
            ucb = exploitation + exploration
            
            if ucb > best_ucb:
                best_ucb = ucb
                best_strategy = strategy
        
        return best_strategy
    
    def apply_result(self, strategy: str, late_game_strategy: str, opponent_strategy: str, win: bool) -> None:
        """Record a game result."""
        import datetime
        result = Result(
            timestamp=datetime.datetime.now().isoformat(),
            strategy=strategy,
            late_game_strategy=late_game_strategy,
            opponent_strategy=opponent_strategy,
            is_win=win
        )
        self.results_.append(result)
    
    def store(self) -> None:
        """Write results to file."""
        pass



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
