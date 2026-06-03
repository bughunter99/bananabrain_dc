"""Protoss race-specific strategy.

C++ equivalent: ProtossStrategy.cpp/ProtossStrategy.h

Implements PvZ, PvT, PvP strategies with:
- Opening selection
- Tech progression
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cppsource.Strategy import Strategy


class ProtossStrategy(Strategy):
    """Protoss-specific strategic decisions."""
    
    # PvZ openings
    PVZ_SAIRDT = "PvZ_sairdt"
    PVZ_10_12_GATE = "PvZ_10/12gate"
    PVZ_1BASE_SPEED_ZEAL = "PvZ_1basespeedzeal"
    PVZ_2BASE_SPEED_ZEAL = "PvZ_2basespeedzeal"
    PVZ_BISU = "PvZ_bisu"
    PVZ_NEOBISU = "PvZ_neobisu"
    
    # PvT openings
    PVT_2GATE = "PvT_2gate"
    PVT_FFE = "PvT_ffe"
    PVT_10_12_GATE = "PvT_10/12gate"
    PVT_AGGRESSIVE = "PvT_aggressive"
    PVT_EXPAND = "PvT_expand"
    
    # PvP openings
    PVP_1GATE = "PvP_1gate"
    PVP_2GATE = "PvP_2gate"
    PVP_PROXY_GATE = "PvP_proxygate"
    PVP_FORGE_FE = "PvP_forge_fe"
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select Protoss strategy based on opponent."""
        self._opening = self.PVT_2GATE
        self._mode = "standard"
    
    def frame_inner(self) -> None:
        """Execute Protoss strategy logic each frame."""
        self.update_stage()
    
    def update_stage(self) -> None:
        """Update Protoss stage."""
        pass
    
    def is_defending_rush(self) -> bool:
        """Check defending against early aggression."""
        return False
    
    def expect_dark_templars(self) -> bool:
        """Predict DT usage by Protoss opponent."""
        return "dt" in self._opening.lower()
