"""Opponent analysis and prediction.

C++ equivalent: OpponentModel.cpp/OpponentModel.h

Analyzes opponent:
- Opening strategy prediction
- Unit types (air, cloaked, etc)
- Expansion timing
- Special unit frames (DT, lurker, EMP)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional
from enum import Enum


class EnemyOpening(Enum):
    """Predicted enemy opening types."""
    UNKNOWN = "unknown"
    
    # Zerg openings
    Z_4_5_POOL = "z_4pool"
    Z_9_POOL = "z_9pool"
    Z_POOL_SPEED = "z_poolspeed"
    Z_12_POOL = "z_12pool"
    Z_10_HATCH = "z_10hatch"
    
    # Terran openings
    T_BBS = "t_bbs"
    T_2RAX = "t_2rax"
    T_PROXY_RAX = "t_proxyrax"
    T_FACTORY = "t_factory"
    T_FAST_EXPAND = "t_fe"
    
    # Protoss openings
    P_1GATE_CORE = "p_1gatecore"
    P_4GATE_GOON = "p_4gategoon"
    P_2GATE = "p_2gate"
    P_PROXY_GATE = "p_proxygate"
    P_FAST_EXPAND = "p_fe"
    P_CANNON_RUSH = "p_cannonrush"


@dataclass
class OpponentModel:
    """Singleton for modeling opponent behavior and predictions."""
    
    _instance: ClassVar[Optional['OpponentModel']] = None
    
    enemy_opening_: EnemyOpening = EnemyOpening.UNKNOWN
    enemy_race_: str = "Unknown"
    initial_enemy_race_: str = "Unknown"
    race_known_: bool = False
    
    emp_seen_: bool = False
    air_to_ground_present_: bool = False
    cloaked_present_: bool = False
    
    dark_templar_frame_: int = -1
    mutalisk_frame_: int = -1
    lurker_frame_: int = -1
    
    expansion_frames_: List[int] = field(default_factory=list, init=False)
    
    @classmethod
    def Instance(cls) -> 'OpponentModel':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize opponent model."""
        self.enemy_opening_ = EnemyOpening.UNKNOWN
        self.race_known_ = False
        self.emp_seen_ = False
    
    def update(self) -> None:
        """Update opponent analysis from current game state."""
        self._detect_opening()
        self._detect_special_units()
        self._detect_expansions()
    
    def _detect_opening(self) -> None:
        """Detect opponent opening strategy."""
        # Analyze build order and unit production
        pass
    
    def _detect_special_units(self) -> None:
        """Detect special enemy units (DT, cloaked, air, etc)."""
        pass
    
    def _detect_expansions(self) -> None:
        """Track enemy expansion timings."""
        pass
    
    def enemy_opening(self) -> EnemyOpening:
        """Get predicted enemy opening."""
        return self.enemy_opening_
    
    def enemy_opening_info(self) -> str:
        """Get string description of enemy opening."""
        return self.enemy_opening_.value if self.enemy_opening_ else "Unknown"
    
    def enemy_race(self) -> str:
        """Get current enemy race."""
        return self.enemy_race_
    
    def initial_enemy_race(self) -> str:
        """Get initial enemy race."""
        return self.initial_enemy_race_
    
    def emp_seen(self) -> bool:
        """Check if enemy has used EMP."""
        return self.emp_seen_
    
    def air_to_ground_present(self) -> bool:
        """Check if enemy has air-to-ground units."""
        return self.air_to_ground_present_
    
    def cloaked_present(self) -> bool:
        """Check if enemy has cloaked units."""
        return self.cloaked_present_
    
    def dark_templar_frame(self) -> int:
        """Get frame when first DT was detected."""
        return self.dark_templar_frame_
    
    def mutalisk_frame(self) -> int:
        """Get frame when first mutalisk was detected."""
        return self.mutalisk_frame_
    
    def lurker_frame(self) -> int:
        """Get frame when first lurker was detected."""
        return self.lurker_frame_
    
    def enemy_earliest_expansion_frame(self) -> int:
        """Get earliest expansion timing."""
        return min(self.expansion_frames_) if self.expansion_frames_ else -1
    
    def enemy_latest_expansion_frame(self) -> int:
        """Get latest expansion timing."""
        return max(self.expansion_frames_) if self.expansion_frames_ else -1
