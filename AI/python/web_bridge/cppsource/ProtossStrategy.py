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
        # Handle opening phase
        if self.mode_ == ProtossMode.OPENING:
            if self._opening == kPvZ_SairDt:
                self.opening_PvZ_SairDt()
            else:
                self.update_stage()
        
        # Handle main strategies
        elif self.mode_ == ProtossMode.MAIN:
            self.main_strategy()
        elif self.mode_ == ProtossMode.DEFEND_FAST_POOL:
            self.defend_fast_pool()
        else:
            self.update_stage()
    
    def main_strategy(self) -> None:
        """Handle MAIN strategy - sustained tech and expansion."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.Tactics import TacticsManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        tactics = TacticsManager.Instance()
        
        # Gateways for unit production
        gateway_count = building_manager.building_count_including_planned("Protoss_Gateway")
        if gateway_count < 4 and tactics.enemy_pressure() == "low":
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 4)
        
        # Unit composition
        zealot_count = training_manager.unit_count("Protoss_Zealot")
        dragoon_count = training_manager.unit_count("Protoss_Dragoon")
        
        # Zealots with upgrades
        if zealot_count < 6:
            training_manager.larva_train_distribution().set("Protoss_Zealot", 0.5)
        
        # Dragoons for ranged support
        if dragoon_count < 8:
            training_manager.larva_train_distribution().set("Protoss_Dragoon", 1.0)
        
        # Tech buildings
        if building_manager.building_exists("Protoss_Templar_Archives"):
            # Continue DT production
            dt_count = training_manager.unit_count("Protoss_Dark_Templar")
            if dt_count < 4:
                training_manager.larva_train_distribution().set("Protoss_Dark_Templar", 0.3)
        
        # Expansion
        if tactics.enemy_pressure() == "low":
            building_manager.set_requested_building_count_at_least("Protoss_Nexus", 2)
        
        # Armor and weapon upgrades
        building_manager.request_upgrade("Protoss_Armor")
        building_manager.request_upgrade("Protoss_Weapons")
    
    def defend_fast_pool(self) -> None:
        """Handle DEFEND_FAST_POOL - defend against early Zerg pool."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Forge for cannon defense ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Protoss_Forge", 1)
        
        # === Cannons at chokepoint ===
        if building_manager.building_exists("Protoss_Forge"):
            building_manager.set_requested_building_count_at_least("Protoss_Photon_Cannon", 2)
        
        # === Zealots for defense ===
        zealot_count = training_manager.unit_count("Protoss_Zealot")
        if zealot_count < 6:
            training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        # === Transition when safe ===
        if (zealot_count >= 6 and
            building_manager.building_count_including_planned("Protoss_Photon_Cannon") >= 2):
            self.mode_ = ProtossMode.MAIN
    
    def opening_PvZ_SairDt(self) -> None:
        """Handle PvZ SairDT opening.
        
        Sair (air) DT strategy - use early DTs + air units to pressure Zerg.
        """
        from cppsource.OpponentModel import OpponentModel
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        opponent_model = OpponentModel.Instance()
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        # Check for fast pool defense
        if opponent_model.enemy_opening() == "Z_4_5Pool":
            self.mode_ = ProtossMode.DEFEND_FAST_POOL
            return
        
        # Get current supply
        supply = self.opening_supply_count()
        
        # === SUPPLY 9: Gateway ===
        if supply >= 9:
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 1)
        
        # === SUPPLY 12-14: Cyber Core ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Protoss_Cybernetics_Core", 1)
        
        # === SUPPLY 13: Assimilator ===
        if supply >= 13:
            building_manager.set_requested_building_count_at_least("Protoss_Assimilator", 1)
        
        # === Gateway Zealots ===
        if (building_manager.building_exists("Protoss_Gateway") and
            training_manager.unit_count("Protoss_Zealot") < 2):
            training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        # === Stargate (for early corsairs/carriers) ===
        if (building_manager.building_count_including_planned("Protoss_Assimilator") >= 1 and
            self.done_or_in_progress("Protoss_Leg_Enhancements")):
            building_manager.set_requested_building_count_at_least("Protoss_Stargate", 1)
        
        # === Leg Enhancements for Zealots ===
        if training_manager.unit_count("Protoss_Zealot") >= 2:
            building_manager.request_upgrade("Protoss_Leg_Enhancements")
        
        # === Dark Templar Tech ===
        if (building_manager.building_count_including_planned("Protoss_Cybernetics_Core") >= 1 and
            building_manager.building_count_including_planned("Protoss_Assimilator") >= 1):
            building_manager.set_requested_building_count_at_least("Protoss_Templar_Archives", 1)
        
        # === Dark Templars ===
        if building_manager.building_exists("Protoss_Templar_Archives"):
            # Limit DTs while keeping them trained
            if training_manager.unit_count("Protoss_Dark_Templar") < 3:
                training_manager.larva_train_distribution().set("Protoss_Dark_Templar", 0.5)
        
        # === Dragoons ===
        if (self.done_or_in_progress("Protoss_Leg_Enhancements") and
            training_manager.unit_count("Protoss_Dragoon") < 4):
            training_manager.larva_train_distribution().set("Protoss_Dragoon", 1.0)
        
        # === Expansion ===
        if (building_manager.building_exists("Protoss_Templar_Archives") and
            training_manager.unit_count("Protoss_Zealot") >= 4):
            building_manager.set_requested_building_count_at_least("Protoss_Nexus", 2)
        
        # === Transition to Main ===
        if (training_manager.unit_count("Protoss_Dark_Templar") >= 2 and
            training_manager.unit_count("Protoss_Dragoon") >= 4):
            self.mode_ = ProtossMode.MAIN
            return
    
    def update_stage(self) -> None:
        """Update Protoss stage."""
        pass
    
    def is_defending_rush(self) -> bool:
        """Check defending against early aggression."""
        return False
    
    def expect_dark_templars(self) -> bool:
        """Predict DT usage by Protoss opponent."""
        return "dt" in self._opening.lower()
    
    def opening_PvT_FFE(self) -> None:
        """Handle PvT FFE (Fast Forge Expand) opening.
        
        Forge first expand - defensive expansion with cannons.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 12: Forge ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Protoss_Forge", 1)
        
        # === SUPPLY 16: Nexus Expansion ===
        if supply >= 16:
            building_manager.set_requested_building_count_at_least("Protoss_Nexus", 2)
        
        # === Photon Cannons ===
        if building_manager.building_exists("Protoss_Forge"):
            building_manager.set_requested_building_count_at_least("Protoss_Photon_Cannon", 3)
        
        # === Zealots for defense ===
        zealot_count = training_manager.unit_count("Protoss_Zealot")
        if zealot_count < 4:
            training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        # === Tech to gateway ===
        if building_manager.building_exists("Protoss_Gateway"):
            building_manager.set_requested_building_count_at_least("Protoss_Cybernetics_Core", 1)
        
        # === Dragoons ===
        if (building_manager.building_exists("Protoss_Cybernetics_Core") and
            training_manager.unit_count("Protoss_Dragoon") < 3):
            training_manager.larva_train_distribution().set("Protoss_Dragoon", 1.0)
        
        # === Transition ===
        if (training_manager.unit_count("Protoss_Zealot") >= 4 and
            building_manager.building_exists("Protoss_Nexus", count=2)):
            self.mode_ = ProtossMode.MAIN
    
    def opening_PvP_1012Gate(self) -> None:
        """Handle PvP 10/12 Gateway opening.
        
        Early gateway attack vs Protoss.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 10-12: Gateways ===
        if supply >= 10:
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 2)
        
        # === Zealots ===
        if building_manager.building_exists("Protoss_Gateway"):
            if training_manager.unit_count("Protoss_Zealot") < 6:
                training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        # === Cyber Core ===
        if (building_manager.building_exists("Protoss_Gateway", count=2) and
            training_manager.unit_count("Protoss_Zealot") >= 3):
            building_manager.set_requested_building_count_at_least("Protoss_Cybernetics_Core", 1)
        
        # === Dragoons ===
        if building_manager.building_exists("Protoss_Cybernetics_Core"):
            if training_manager.unit_count("Protoss_Dragoon") < 4:
                training_manager.larva_train_distribution().set("Protoss_Dragoon", 0.5)
        
        # === Attack ===
        if training_manager.unit_count("Protoss_Zealot") >= 4:
            self.attacking_ = True
        
        # === Transition ===
        if training_manager.unit_count("Protoss_Zealot") >= 6:
            self.mode_ = ProtossMode.MAIN
    
    def opening_PvZ_10_12Gate(self) -> None:
        """Handle PvZ 10/12 Gate - gateway focus."""
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Gateways ===
        if supply >= 10:
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 2)
        
        # === Zealots ===
        if building_manager.building_exists("Protoss_Gateway"):
            if training_manager.unit_count("Protoss_Zealot") < 8:
                training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        # === Leg Enhancements ===
        if training_manager.unit_count("Protoss_Zealot") >= 3:
            building_manager.request_upgrade("Protoss_Leg_Enhancements")
        
        # === Cyber for dragoons ===
        if (training_manager.unit_count("Protoss_Zealot") >= 5 and
            self.done_or_in_progress("Protoss_Leg_Enhancements")):
            building_manager.set_requested_building_count_at_least("Protoss_Cybernetics_Core", 1)
            if training_manager.unit_count("Protoss_Dragoon") < 3:
                training_manager.larva_train_distribution().set("Protoss_Dragoon", 0.5)
        
        # === Attack ===
        if training_manager.unit_count("Protoss_Zealot") >= 6:
            self.attacking_ = True
        
        # === Transition ===
        if training_manager.unit_count("Protoss_Zealot") >= 8:
            self.mode_ = ProtossMode.MAIN
    
    def opening_PvT_1012Gate(self) -> None:
        """Handle PvT 10/12 Gate - gateway attack."""
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Early Gateways ===
        if supply >= 10:
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 2)
        
        # === Zealots with Leg Enhancements ===
        if building_manager.building_exists("Protoss_Gateway"):
            if training_manager.unit_count("Protoss_Zealot") < 6:
                training_manager.larva_train_distribution().set("Protoss_Zealot", 1.0)
        
        if training_manager.unit_count("Protoss_Zealot") >= 2:
            building_manager.request_upgrade("Protoss_Leg_Enhancements")
        
        # === Attack quickly ===
        if training_manager.unit_count("Protoss_Zealot") >= 4:
            self.attacking_ = True
        
        # === Continue building ===
        if (training_manager.unit_count("Protoss_Zealot") >= 4 and
            supply >= 12):
            building_manager.set_requested_building_count_at_least("Protoss_Gateway", 3)
        
        # === Transition ===
        if training_manager.unit_count("Protoss_Zealot") >= 8:
            self.mode_ = ProtossMode.MAIN
