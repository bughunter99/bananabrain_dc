"""Terran race-specific strategy.

C++ equivalent: TerranStrategy.cpp/TerranStrategy.h

Implements TvZ, TvT, TvP strategies with:
- Opening selection  
- Wall/bunker placement
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass

from cppsource.Strategy import Strategy


@dataclass
class TerranStrategy(Strategy):
    """Terran-specific strategic decisions."""
    
    # TvZ openings
    TVZ_2RAXFE = "TvZ_2raxfe"
    TVZ_1RAXFE = "TvZ_1raxfe"
    TVZ_3RAX = "TvZ_3rax"
    TVZ_WALL = "TvZ_wall"
    TVZ_EXPAND = "TvZ_expand"
    
    # TvT openings
    TVT_STANDARD = "TvT_standard"
    TVT_EXPAND = "TvT_expand"
    TVT_SCVS = "TvT_scvs"
    
    # TvP openings
    TVP_2RAXFE = "TvP_2raxfe"
    TVP_EXPAND = "TvP_expand"
    TVP_BBS = "TvP_bbs"
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select Terran strategy based on opponent."""
        self._opening = self.TVZ_2RAXFE
        self._mode = "standard"
    
    def frame_inner(self) -> None:
        """Execute Terran strategy logic each frame."""
        self.update_stage()
    
    def frame(self) -> None:
        """Execute frame logic."""
        super().frame()
