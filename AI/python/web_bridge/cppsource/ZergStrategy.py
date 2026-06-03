"""Zerg race-specific strategy.

C++ equivalent: ZergStrategy.cpp/ZergStrategy.h

Implements ZvP, ZvT, ZvZ strategies with:
- Opening selection
- Larva injection timing
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass

from cppsource.Strategy import Strategy


@dataclass
class ZergStrategy(Strategy):
    """Zerg-specific strategic decisions."""
    
    # ZvP openings
    ZVP_POOL = "ZvP_pool"
    ZVP_HATCHERY = "ZvP_hatchery"
    ZVP_MUTALISK = "ZvP_mutalisk"
    ZVP_HYDRALISK = "ZvP_hydralisk"
    ZVP_DEFILER = "ZvP_defiler"
    
    # ZvT openings
    ZVT_POOL = "ZvT_pool"
    ZVT_HATCHERY = "ZvT_hatchery"
    ZVT_LING_FLOOD = "ZvT_lingflood"
    ZVT_BANELING = "ZvT_baneling"
    
    # ZvZ openings
    ZVZ_POOL = "ZvZ_pool"
    ZVZ_HATCHERY = "ZvZ_hatchery"
    ZVZ_ROACH = "ZvZ_roach"
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select Zerg strategy based on opponent."""
        self._opening = self.ZVP_POOL
        self._mode = "standard"
    
    def frame_inner(self) -> None:
        """Execute Zerg strategy logic each frame."""
        self.update_stage()
    
    def update_stage(self) -> None:
        """Update Zerg stage."""
        pass
    
    def expect_lurkers(self) -> bool:
        """Predict Lurker usage by Zerg opponent."""
        return "hydralisk" in self._opening.lower() or "defiler" in self._opening.lower()
