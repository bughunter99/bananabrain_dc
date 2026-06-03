"""ResultStore — 오프닝별 승패 기록 및 가중치 선택."""
from __future__ import annotations

import json
import os
import random
import threading
from typing import Dict, List, Optional, Sequence


class ResultStore:
    """JSON 파일로 오프닝별 승패를 저장하고 가중치 랜덤 선택을 제공한다."""

    DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "opening_results.json")

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = os.path.abspath(path or self.DEFAULT_PATH)
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, int]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, opening: str, won: bool) -> None:
        """경기 결과를 기록한다."""
        if not opening or opening == "auto_play":
            return
        with self._lock:
            entry = self._data.setdefault(opening, {"wins": 0, "losses": 0})
            if won:
                entry["wins"] += 1
            else:
                entry["losses"] += 1
            self._save_locked()

    def weighted_pick(self, candidates: Sequence[str]) -> Optional[str]:
        """승률 기반 가중 랜덤 선택.

        한 번도 기록이 없으면 None 반환 → 호출자가 기본 선택 로직으로 폴백.
        모든 후보에 기록이 없으면 None 반환.
        """
        items = [c for c in candidates if c]
        if not items:
            return None

        with self._lock:
            data = dict(self._data)

        weights: List[float] = []
        any_data = False
        for item in items:
            entry = data.get(item)
            if entry:
                any_data = True
                w = entry["wins"] + 1  # Laplace smoothing
                l = entry["losses"] + 1
                # Wilson 하한 근사 (간략 버전): wins / total 에 보정
                total = w + l
                weights.append(w / total)
            else:
                weights.append(0.5)  # 기록 없는 오프닝은 중립 가중치

        if not any_data:
            return None

        chosen = random.choices(items, weights=weights, k=1)[0]
        return chosen

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {k: dict(v) for k, v in self._data.items()}

    def win_rate(self, opening: str) -> Optional[float]:
        with self._lock:
            entry = self._data.get(opening)
        if not entry:
            return None
        total = entry["wins"] + entry["losses"]
        if total == 0:
            return None
        return entry["wins"] / total

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data = loaded
        except Exception:
            self._data = {}

    def _save_locked(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path)
        except Exception:
            pass
