"""Python counterpart of C++ OpponentModel.cpp / OpponentModel.h."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Dict, Optional, Tuple


class EnemyOpening(str, Enum):
    Unknown = "Unknown"


class OpponentModel:
    _instance: ClassVar[Optional["OpponentModel"]] = None

    def __init__(self) -> None:
        self.initial_enemy_race_ = "Unknown"
        self.enemy_race_ = "Unknown"
        self.enemy_opening_ = EnemyOpening.Unknown
        self.emp_seen_ = False
        self.air_to_ground_present_ = False
        self.cloaked_present_ = False
        self.dark_templar_frame_ = -1
        self.dark_templar_position_ = None
        self.mutalisk_frame_ = -1
        self.mutalisk_position_ = None
        self.lurker_frame_ = -1
        self.blocked_expansion_seen_ = False
        self.non_basic_combat_unit_seen_ = False
        self.enemy_base_sufficiently_scouted_ = False
        self.enemy_natural_sufficiently_scouted_ = False

    @classmethod
    def Instance(cls) -> "OpponentModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(self) -> None:
        self.__init__()

    def update(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        enemy_units = self._parse_units(snapshot.get("enemy_units"))
        self.enemy_race_ = str(snapshot.get("enemy_race") or self.enemy_race_)
        opening = str(snapshot.get("enemy_opening") or "").strip()
        if opening:
            self.enemy_opening_ = EnemyOpening.Unknown if opening == "Unknown" else opening
        self.air_to_ground_present_ = bool(snapshot.get("enemy_air_to_ground_present", self.air_to_ground_present_))
        self.cloaked_present_ = bool(snapshot.get("enemy_cloaked_present", self.cloaked_present_))
        self.emp_seen_ = bool(snapshot.get("emp_seen", self.emp_seen_))
        self.non_basic_combat_unit_seen_ = bool(snapshot.get("non_basic_combat_unit_seen", self.non_basic_combat_unit_seen_))
        self.blocked_expansion_seen_ = self.blocked_expansion_seen_ or any(
            str(unit.get("type") or "") in {"Protoss_Photon_Cannon", "Terran_Bunker", "Zerg_Sunken_Colony"} for unit in enemy_units
        )
        self.non_basic_combat_unit_seen_ = self.non_basic_combat_unit_seen_ or any(
            str(unit.get("type") or "") in {"Protoss_Dark_Templar", "Terran_Ghost", "Zerg_Lurker"} for unit in enemy_units
        )
        self.enemy_base_sufficiently_scouted_ = bool(snapshot.get("enemy_base_scouted", self.enemy_base_sufficiently_scouted_))
        self.enemy_natural_sufficiently_scouted_ = bool(snapshot.get("enemy_natural_scouted", self.enemy_natural_sufficiently_scouted_))
        self.dark_templar_frame_ = int(snapshot.get("dark_templar_frame", self.dark_templar_frame_))
        self.mutalisk_frame_ = int(snapshot.get("mutalisk_frame", self.mutalisk_frame_))
        self.lurker_frame_ = int(snapshot.get("lurker_frame", self.lurker_frame_))
        self.dark_templar_position_ = snapshot.get("dark_templar_position", self.dark_templar_position_)
        self.mutalisk_position_ = snapshot.get("mutalisk_position", self.mutalisk_position_)

    def _parse_units(self, units: Any) -> list[Dict[str, Any]]:
        if not isinstance(units, list):
            return []
        return [unit for unit in units if isinstance(unit, dict)]

    def enemy_opening(self) -> Any:
        return self.enemy_opening_

    def enemy_opening_info(self, enemy_opening: Optional[Any] = None) -> str:
        target = enemy_opening or self.enemy_opening_
        return str(target)

    def emp_seen(self) -> bool:
        return self.emp_seen_

    def initial_enemy_race(self) -> str:
        return self.initial_enemy_race_

    def enemy_race_known(self) -> bool:
        return self.enemy_race_ in {"Zerg", "Terran", "Protoss"}

    def enemy_race(self) -> str:
        return self.enemy_race_

    def enemy_earliest_expansion_frame(self) -> int:
        return -1

    def enemy_latest_expansion_frame(self) -> int:
        return -1

    def air_to_ground_present(self) -> bool:
        return self.air_to_ground_present_

    def cloaked_present(self) -> bool:
        return self.cloaked_present_

    def cloaked_or_mine_present(self) -> bool:
        return self.cloaked_present_

    def dark_templar_frame(self) -> int:
        return self.dark_templar_frame_

    def dark_templar_position(self) -> Any:
        return self.dark_templar_position_

    def mutalisk_frame(self) -> int:
        return self.mutalisk_frame_

    def mutalisk_position(self) -> Any:
        return self.mutalisk_position_

    def lurker_frame(self) -> int:
        return self.lurker_frame_

    def blocked_expansion_seen(self) -> bool:
        return self.blocked_expansion_seen_

    def non_basic_combat_unit_seen(self) -> bool:
        return self.non_basic_combat_unit_seen_

    def enemy_base_sufficiently_scouted(self) -> bool:
        return self.enemy_base_sufficiently_scouted_

    def enemy_natural_sufficiently_scouted(self) -> bool:
        return self.enemy_natural_sufficiently_scouted_
