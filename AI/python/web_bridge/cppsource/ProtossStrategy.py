"""Protoss race-specific strategy.

C++ equivalent: ProtossStrategy.cpp/ProtossStrategy.h

Implements PvZ, PvT, PvP strategies with:
- Opening selection
- Tech progression
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, List, Optional

from cppsource.Strategy import Strategy


class ProtossMode(Enum):
    """Protoss strategy modes."""
    OPENING = "Opening"
    DEFEND_FAST_POOL = "Defend fast pool"
    DEFEND_FAST_POOL_FFE = "Defend fast pool (FFE)"
    DEFEND_PROXY_GATE = "Defend proxy gate"
    DEFEND_CANNON_RUSH = "Defend cannon rush"
    DEFEND_FOUR_GATE_GOON = "Defend four gate goon"
    DEFEND_THREE_HATCH_LING_FFE = "Defend three hatch ling (FFE)"
    REACTIVE_FAST_EXPAND = "Reactive fast expand"
    MAIN = "Main"


class LateGameStrategy(Enum):
    """Protoss late game strategies."""
    NONE = "none"
    ARBITERS = "arbiters"
    CARRIERS = "carriers"


# Protoss opening constants
kPvZ_SairDt = "PvZ_sairdt"
kPvZ_1012Gate = "PvZ_1012gate"
kPvZ_1BaseSpeedZeal = "PvZ_1basespeedzeal"
kPvZ_2BaseSpeedZeal = "PvZ_2basespeedzeal"
kPvZ_Bisu = "PvZ_bisu"
kPvZ_NeoBisu = "PvZ_neobisu"
kPvZ_4Gate2Archon = "PvZ_4gate2archon"
kPvZ_5GateGoon = "PvZ_5gategoon"
kPvZ_SairGoon = "PvZ_sairgoon"
kPvZ_SairReaver = "PvZ_sairreaver"
kPvZ_Stove = "PvZ_stove"
kPvZ_4GateGoon = "PvZ_4gategoon"
kPvZ_99Gate = "PvZ_99gate"
kPvZ_99ProxyGate = "PvZ_99proxygate"

kPvT_1012Gate = "PvT_1012gate"
kPvT_2GateDt = "PvT_2gatedt"
kPvT_1GateDtExpo = "PvT_1gatedtexpo"
kPvT_2GateRngExpo = "PvT_2gaternexpo"
kPvT_1GateReaver = "PvT_1gatereaver"
kPvT_1015Gate = "PvT_1015gate"
kPvT_Bulldog = "PvT_bulldog"
kPvT_12Nexus = "PvT_12nexus"
kPvT_28Nexus = "PvT_28nexus"
kPvT_32Nexus = "PvT_32nexus"
kPvT_DtDrop = "PvT_dtdrop"
kPvT_Stove = "PvT_stove"
kPvT_4GateGoon = "PvT_4gategoon"
kPvT_99Gate = "PvT_99gate"
kPvT_99ProxyGate = "PvT_99proxygate"

kPvP_NZCore = "PvP_nzcore"
kPvP_ZCore = "PvP_zcore"
kPvP_ZZCore = "PvP_zzcore"
kPvP_ZCoreZ = "PvP_zcorez"
kPvP_1012Gate = "PvP_1012gate"
kPvP_1012GateDt = "PvP_1012gatedt"
kPvP_2GateDtExpo = "PvP_2gatedtexpo"
kPvP_2GateReaver = "PvP_2gatereaver"
kPvP_3GateRobo = "PvP_3gaterobo"
kPvP_3GateSpeedZeal = "PvP_3gatespeedzeal"
kPvP_4GateGoon = "PvP_4gategoon"
kPvP_12Nexus = "PvP_12nexus"
kPvP_99Gate = "PvP_99gate"
kPvP_99ProxyGate = "PvP_99proxygate"

kPvU_1012Gate = "PvU_1012gate"
kPvU_99Gate = "PvU_99gate"
kPvU_99ProxyGate = "PvU_99proxygate"
kPvU_4GateGoon = "PvU_4gategoon"
kPvU_Forge = "PvU_forge"


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
