"""Python counterpart of C++ Configuration.cpp / Configuration.h."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional


@dataclass
class Configuration:
    _instance: ClassVar[Optional["Configuration"]] = None

    human_opponent_: bool = False
    draw_enabled_: bool = False
    ucb1_: bool = False
    tournament_: bool = False

    PvZ_opening_: str = ""
    PvT_opening_: str = ""
    PvP_opening_: str = ""
    PvU_opening_: str = ""
    TvZ_opening_: str = ""
    TvT_opening_: str = ""
    TvP_opening_: str = ""
    TvU_opening_: str = ""
    ZvZ_opening_: str = ""
    ZvT_opening_: str = ""
    ZvP_opening_: str = ""
    ZvU_opening_: str = ""

    @classmethod
    def Instance(cls) -> "Configuration":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(self, base_path: str = "bwapi-data") -> None:
        read_dir = Path(base_path) / "read"
        ai_dir = Path(base_path) / "AI"
        if (read_dir / "schnail.env").exists():
            self.human_opponent_ = True
        self.read_configuration_file(ai_dir / "Configuration.txt")
        self.read_configuration_file(read_dir / "Configuration.txt")

    def read_configuration_file(self, path: str | Path) -> None:
        config_path = Path(path)
        if not config_path.exists():
            return
        for line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            self.apply_key_value(key.strip(), value.strip())

    def apply_key_value(self, key: str, value: str) -> None:
        normalized = value.strip().lower()
        if key == "draw":
            self.draw_enabled_ = normalized == "true"
        elif key == "ucb1":
            self.ucb1_ = normalized == "true"
        elif key == "tournament":
            self.tournament_ = normalized == "true"
        elif key == "PvZ_opening":
            self.PvZ_opening_ = value
        elif key == "PvT_opening":
            self.PvT_opening_ = value
        elif key == "PvP_opening":
            self.PvP_opening_ = value
        elif key == "PvU_opening":
            self.PvU_opening_ = value
        elif key == "TvZ_opening":
            self.TvZ_opening_ = value
        elif key == "TvT_opening":
            self.TvT_opening_ = value
        elif key == "TvP_opening":
            self.TvP_opening_ = value
        elif key == "TvU_opening":
            self.TvU_opening_ = value
        elif key == "ZvZ_opening":
            self.ZvZ_opening_ = value
        elif key == "ZvT_opening":
            self.ZvT_opening_ = value
        elif key == "ZvP_opening":
            self.ZvP_opening_ = value
        elif key == "ZvU_opening":
            self.ZvU_opening_ = value

    def update_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.human_opponent_ = bool(snapshot.get("human_opponent", self.human_opponent_))
        self.draw_enabled_ = bool(snapshot.get("draw_enabled", self.draw_enabled_))
        self.ucb1_ = bool(snapshot.get("ucb1", self.ucb1_))
        self.tournament_ = bool(snapshot.get("tournament", self.tournament_))

    def set_opening(self, matchup: str, opening: str) -> None:
        key = f"{matchup}_opening_"
        if hasattr(self, key):
            setattr(self, key, str(opening))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "human_opponent": self.human_opponent_,
            "draw_enabled": self.draw_enabled_,
            "ucb1": self.ucb1_,
            "tournament": self.tournament_,
            "openings": {
                "PvZ": self.PvZ_opening_,
                "PvT": self.PvT_opening_,
                "PvP": self.PvP_opening_,
                "PvU": self.PvU_opening_,
                "TvZ": self.TvZ_opening_,
                "TvT": self.TvT_opening_,
                "TvP": self.TvP_opening_,
                "TvU": self.TvU_opening_,
                "ZvZ": self.ZvZ_opening_,
                "ZvT": self.ZvT_opening_,
                "ZvP": self.ZvP_opening_,
                "ZvU": self.ZvU_opening_,
            },
        }

    def human_opponent(self) -> bool:
        return self.human_opponent_

    def draw_enabled(self) -> bool:
        return self.draw_enabled_

    def ucb1(self) -> bool:
        return self.ucb1_

    def tournament(self) -> bool:
        return self.tournament_

    def PvZ_opening(self) -> str:
        return self.PvZ_opening_

    def PvT_opening(self) -> str:
        return self.PvT_opening_

    def PvP_opening(self) -> str:
        return self.PvP_opening_

    def PvU_opening(self) -> str:
        return self.PvU_opening_

    def TvZ_opening(self) -> str:
        return self.TvZ_opening_

    def TvT_opening(self) -> str:
        return self.TvT_opening_

    def TvP_opening(self) -> str:
        return self.TvP_opening_

    def TvU_opening(self) -> str:
        return self.TvU_opening_

    def ZvZ_opening(self) -> str:
        return self.ZvZ_opening_

    def ZvT_opening(self) -> str:
        return self.ZvT_opening_

    def ZvP_opening(self) -> str:
        return self.ZvP_opening_

    def ZvU_opening(self) -> str:
        return self.ZvU_opening_

