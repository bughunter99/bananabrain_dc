"""Terran race-specific strategy.

C++ equivalent: TerranStrategy.cpp/TerranStrategy.h

Implements TvZ, TvT, TvP strategies with:
- Opening selection  
- Wall/bunker placement
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Optional

from cppsource.Strategy import Strategy


class TerranMode(Enum):
    """Terran strategy modes."""
    OPENING = "Opening"
    MAIN_MECH = "Main Mech"
    MAIN_BIO = "Main Bio"
    MAIN_BIO_MECH = "Main BioMech"
    DEFEND_FAST_POOL = "Defend Fast Pool"


# Terran opening constants
kTvZ_Fantasy = "TvZ_fantasy"
kTvZ_Sparks = "TvZ_sparks"
kTvZ_Ayumi = "TvZ_ayumi"
kTvZ_1RaxFE = "TvZ_1raxfe"
kTvZ_2Rax = "TvZ_2rax"
kTvZ_14CC = "TvZ_14cc"
kTvZ_3FactGoliath = "TvZ_3factgoliath"
kTvZ_5FactGoliath = "TvZ_5factgoliath"
kTvZ_2PortWraithBio = "TvZ_2portWraithbio"
kTvZ_2PortWraithMech = "TvZ_2portWraithmech"
kTvZ_8RaxMech = "TvZ_8raxmech"
kTvZ_BBS = "TvZ_bbs"
kTvZ_ProxyBBS = "TvZ_proxybbs"

kTvT_2FactVults = "TvT_2factvults"
kTvT_3FactVults = "TvT_3factvults"
kTvT_1FactFE = "TvT_1factfe"
kTvT_1RaxFE = "TvT_1raxfe"
kTvT_14CC = "TvT_14cc"
kTvT_1RaxFEBioMech = "TvT_1raxfebiomech"
kTvT_2RaxBioMech = "TvT_2raxbiomech"
kTvT_1PortWraith = "TvT_1portwraith"
kTvT_2PortWraith = "TvT_2portwraith"
kTvT_Proxy5Rax = "TvT_proxy5rax"
kTvT_8RaxMech = "TvT_8raxmech"
kTvT_BBS = "TvT_bbs"
kTvT_ProxyBBS = "TvT_proxybbs"

kTvP_2FactVults = "TvP_2factvults"
kTvP_GundamRush = "TvP_gundam_rush"
kTvP_JoyORush = "TvP_joyorush"
kTvP_ShallowTwo = "TvP_shallowTwo"
kTvP_DeepSix = "TvP_deepsix"
kTvP_SiegeExpand = "TvP_siegeexpand"
kTvP_1FactFE = "TvP_1factfe"
kTvP_1RaxFE = "TvP_1raxfe"
kTvP_14CC = "TvP_14cc"
kTvP_StrongFD = "TvP_strongfd"
kTvP_101010FD = "TvP_101010fd"
kTvP_BBS = "TvP_bbs"
kTvP_ProxyBBS = "TvP_proxybbs"

kTvU_1Fact = "TvU_1fact"
kTvU_1FactMech = "TvU_1factmech"
kTvU_2Rax = "TvU_2rax"
kTvU_BBS = "TvU_bbs"
kTvU_ProxyBBS = "TvU_proxybbs"


@dataclass
class TerranStrategy(Strategy):
    """Terran-specific strategic decisions."""
    
    mode_: TerranMode = TerranMode.OPENING
    opening_wall_positioned_: bool = False
    opening_wall_positioned_successfully_: bool = False
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select Terran strategy based on opponent and 1v1 status."""
        if not is_1v1:
            self._opening = kTvU_1Fact
            return
        
        from cppsource.OpponentModel import OpponentModel
        from cppsource.Results import ResultStore
        from cppsource.Configuration import Configuration
        
        opponent_model = OpponentModel.Instance()
        result_store = ResultStore.Instance()
        configuration = Configuration.Instance()
        
        enemy_race = opponent_model.enemy_race()
        
        if enemy_race == "Zerg":
            config_opening = configuration.TvZ_opening() if hasattr(configuration, 'TvZ_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kTvZ_Fantasy, kTvZ_Sparks, kTvZ_Ayumi, kTvZ_1RaxFE,
                          kTvZ_2Rax, kTvZ_14CC, kTvZ_3FactGoliath, kTvZ_5FactGoliath,
                          kTvZ_2PortWraithBio, kTvZ_2PortWraithMech, kTvZ_8RaxMech,
                          kTvZ_BBS, kTvZ_ProxyBBS]
                self._opening = result_store.pick_strategy(options)
                
        elif enemy_race == "Terran":
            config_opening = configuration.TvT_opening() if hasattr(configuration, 'TvT_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kTvT_2FactVults, kTvT_3FactVults, kTvT_1FactFE, kTvT_1RaxFE,
                          kTvT_14CC, kTvT_1RaxFEBioMech, kTvT_2RaxBioMech, kTvT_1PortWraith,
                          kTvT_2PortWraith, kTvT_Proxy5Rax, kTvT_8RaxMech,
                          kTvT_BBS, kTvT_ProxyBBS]
                self._opening = result_store.pick_strategy(options)
                
        elif enemy_race == "Protoss":
            config_opening = configuration.TvP_opening() if hasattr(configuration, 'TvP_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kTvP_2FactVults, kTvP_GundamRush, kTvP_JoyORush, kTvP_ShallowTwo,
                          kTvP_DeepSix, kTvP_SiegeExpand, kTvP_1FactFE, kTvP_1RaxFE,
                          kTvP_14CC, kTvP_StrongFD, kTvP_101010FD,
                          kTvP_BBS, kTvP_ProxyBBS]
                self._opening = result_store.pick_strategy(options)
        else:
            config_opening = configuration.TvU_opening() if hasattr(configuration, 'TvU_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kTvU_1Fact, kTvU_1FactMech, kTvU_2Rax, kTvU_BBS, kTvU_ProxyBBS]
                self._opening = result_store.pick_strategy(options)
    
    def mode(self) -> str:
        """Get current mode as string."""
        return str(self.mode_.value)
    
    def frame_inner(self) -> None:
        """Execute Terran strategy logic each frame."""
        if self._opening == kTvZ_Fantasy:
            self.opening_TvZ_fantasy()
        else:
            self.update_stage()
    
    def update_stage(self) -> None:
        """Update Terran stage."""
        pass
    
    def opening_TvZ_fantasy(self) -> None:
        """Handle TvZ Fantasy opening."""
        from cppsource.OpponentModel import OpponentModel
        
        opponent_model = OpponentModel.Instance()
        
        # Check for fast pool defense
        if opponent_model.enemy_opening() == "Z_4_5Pool":
            self.mode_ = TerranMode.DEFEND_FAST_POOL
            return
        
        # Continue opening execution
        pass
    
    def is_defending_rush(self) -> bool:
        """Check defending against early aggression."""
        return self.mode_ == TerranMode.DEFEND_FAST_POOL
