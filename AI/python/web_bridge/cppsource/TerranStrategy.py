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
        # Handle opening phase
        if self.mode_ == TerranMode.OPENING:
            if self._opening == kTvZ_Fantasy:
                self.opening_TvZ_fantasy()
            else:
                self.update_stage()
        
        # Handle main strategies
        elif self.mode_ == TerranMode.MAIN_BIO:
            self.main_BIO()
        elif self.mode_ == TerranMode.MAIN_MECH:
            self.main_MECH()
        elif self.mode_ == TerranMode.DEFEND_FAST_POOL:
            self.defend_fast_pool()
        else:
            self.update_stage()
    
    def main_BIO(self) -> None:
        """Handle MAIN_BIO strategy - Marine + Medic army."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.Tactics import TacticsManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        tactics = TacticsManager.Instance()
        
        # Continue marine production
        marine_count = training_manager.unit_count("Terran_Marine")
        if marine_count < 20:
            training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # Add more medics
        medic_count = training_manager.unit_count("Terran_Medic")
        if medic_count < marine_count // 4:
            training_manager.larva_train_distribution().set("Terran_Medic", 0.5)
        
        # Infantry upgrades
        building_manager.request_upgrade("Terran_Infantry_Weapons")
        building_manager.request_upgrade("Terran_Infantry_Armor")
        
        # Add barracks
        barracks_count = building_manager.building_count_including_planned("Terran_Barracks")
        if barracks_count < 4 and marine_count >= 10:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", barracks_count + 1)
        
        # Expand
        if marine_count >= 12 and tactics.enemy_pressure() == "low":
            building_manager.set_requested_building_count_at_least("Terran_Command_Center", 2)
        
        # Continue attacking
        if tactics.should_attack():
            self.attacking_ = True
    
    def main_MECH(self) -> None:
        """Handle MAIN_MECH strategy - Tanks + Goliaths."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        
        # Siege tanks
        tank_count = training_manager.unit_count("Terran_Siege_Tank_Tank_Mode")
        if tank_count < 10:
            training_manager.larva_train_distribution().set("Terran_Siege_Tank_Tank_Mode", 0.7)
        
        # Goliaths for air defense
        goliath_count = training_manager.unit_count("Terran_Goliath")
        if goliath_count < tank_count // 2:
            training_manager.larva_train_distribution().set("Terran_Goliath", 0.3)
        
        # Siege mode upgrade
        if tank_count >= 3:
            building_manager.request_upgrade("Terran_Siege_Tech")
        
        # Factory and starport
        factory_count = building_manager.building_count_including_planned("Terran_Factory")
        if factory_count < 3:
            building_manager.set_requested_building_count_at_least("Terran_Factory", factory_count + 1)
        
        # Armor upgrades
        building_manager.request_upgrade("Terran_Vehicle_Armor")
        building_manager.request_upgrade("Terran_Vehicle_Weapons")
    
    def defend_fast_pool(self) -> None:
        """Handle DEFEND_FAST_POOL - defend against early Zerg pool."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Early bunkers at ramp ===
        if supply >= 16:
            building_manager.set_requested_building_count_at_least("Terran_Bunker", 2)
        
        # === Marines for bunker and main army ===
        marine_count = training_manager.unit_count("Terran_Marine")
        if marine_count < 10:
            training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # === Get extra supply depots ===
        if supply >= 22:
            building_manager.set_requested_building_count_at_least("Terran_Supply_Depot", 2)
        
        # === Transition when safe ===
        if (marine_count >= 10 and 
            building_manager.building_count_including_planned("Terran_Bunker") >= 2):
            self.mode_ = TerranMode.MAIN_BIO
    
    def update_stage(self) -> None:
        """Update Terran stage."""
        pass
    
    def opening_TvZ_fantasy(self) -> None:
        """Handle TvZ Fantasy opening.
        
        Fantasy build - early aggression with Marines and Medics.
        Two barracks to pressure early Zerg.
        """
        from cppsource.OpponentModel import OpponentModel
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        opponent_model = OpponentModel.Instance()
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        # Check for fast pool defense
        if opponent_model.enemy_opening() == "Z_4_5Pool":
            self.mode_ = TerranMode.DEFEND_FAST_POOL
            return
        
        # Get current supply
        supply = self.opening_supply_count()
        
        # === SUPPLY 12: First Barracks ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === SUPPLY 15: Second Barracks ===
        if supply >= 15:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 2)
        
        # === SUPPLY 14: Supply Depot ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Supply_Depot", 1)
        
        # === Marines from first Barracks ===
        if (building_manager.building_exists("Terran_Barracks") and
            training_manager.unit_count("Terran_Marine") < 4):
            training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # === Marines from second Barracks ===
        if (building_manager.building_count_including_planned("Terran_Barracks") >= 2 and
            training_manager.unit_count("Terran_Marine") < 8):
            training_manager.larva_train_distribution().set("Terran_Marine", 2.0)
        
        # === Academy for Medic support ===
        if training_manager.unit_count("Terran_Marine") >= 6:
            building_manager.set_requested_building_count_at_least("Terran_Academy", 1)
        
        # === Medics for healing ===
        if building_manager.building_exists("Terran_Academy"):
            if training_manager.unit_count("Terran_Medic") < 2:
                training_manager.larva_train_distribution().set("Terran_Medic", 0.3)
        
        # === Infantry Weapons upgrade ===
        if training_manager.unit_count("Terran_Marine") >= 4:
            building_manager.request_upgrade("Terran_Infantry_Weapons")
        
        # === Continue attacking with marines ===
        if training_manager.unit_count("Terran_Marine") >= 4:
            self.attacking_ = True
        
        # === Supply management ===
        if supply >= 22:
            building_manager.set_requested_building_count_at_least("Terran_Supply_Depot", 2)
        
        # === Transition to Main BIO ===
        if (training_manager.unit_count("Terran_Marine") >= 10 and
            self.done_or_in_progress("Terran_Infantry_Weapons")):
            self.mode_ = TerranMode.MAIN_BIO
            return
    
    def is_defending_rush(self) -> bool:
        """Check defending against early aggression."""
        return self.mode_ == TerranMode.DEFEND_FAST_POOL
    
    def opening_TvP_1RaxFE(self) -> None:
        """Handle TvP 1 Rax FE (Fast Expand) opening.
        
        1 Barracks Fast Expand vs Protoss.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 12: Barracks ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === SUPPLY 16: Command Center Expand ===
        if supply >= 16:
            building_manager.set_requested_building_count_at_least("Terran_Command_Center", 2)
        
        # === Marines for defense ===
        if building_manager.building_exists("Terran_Barracks"):
            if training_manager.unit_count("Terran_Marine") < 4:
                training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # === Supply Depot ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Supply_Depot", 1)
        
        # === Transition to Main ===
        if (building_manager.building_exists("Terran_Command_Center", count=2) and
            training_manager.unit_count("Terran_Marine") >= 6):
            self.mode_ = TerranMode.MAIN_BIO
    
    def opening_TvT_2FactVults(self) -> None:
        """Handle TvT 2 Factory Vultures opening.
        
        Vulture harassment with 2 factories vs Terran.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 12-14: First Barracks ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === SUPPLY 14-16: Factory ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Factory", 1)
        
        # === SUPPLY 16: Second Factory ===
        if supply >= 18:
            building_manager.set_requested_building_count_at_least("Terran_Factory", 2)
        
        # === Marines early ===
        if building_manager.building_exists("Terran_Barracks"):
            if training_manager.unit_count("Terran_Marine") < 2:
                training_manager.larva_train_distribution().set("Terran_Marine", 0.5)
        
        # === Vultures from Factory ===
        if (building_manager.building_exists("Terran_Factory") and
            training_manager.unit_count("Terran_Vulture") < 6):
            training_manager.larva_train_distribution().set("Terran_Vulture", 1.0)
        
        # === Attack with vultures ===
        if training_manager.unit_count("Terran_Vulture") >= 4:
            self.attacking_ = True
        
        # === Transition ===
        if training_manager.unit_count("Terran_Vulture") >= 8:
            self.mode_ = TerranMode.MAIN_MECH
    
    def opening_TvZ_14CC(self) -> None:
        """Handle TvZ 14 CC - early expansion."""
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Barracks ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === Early CC expand ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Command_Center", 2)
        
        # === Marines ===
        if building_manager.building_exists("Terran_Barracks"):
            if training_manager.unit_count("Terran_Marine") < 6:
                training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # === Supply ===
        if supply >= 22:
            building_manager.set_requested_building_count_at_least("Terran_Supply_Depot", 2)
        
        # === Transition ===
        if (building_manager.building_exists("Terran_Command_Center", count=2) and
            training_manager.unit_count("Terran_Marine") >= 8):
            self.mode_ = TerranMode.MAIN_BIO
    
    def opening_TvP_14CC(self) -> None:
        """Handle TvP 14 CC - macro expand vs Protoss."""
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Barracks ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === Natural expansion ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Command_Center", 2)
        
        # === Marines for defense ===
        if building_manager.building_exists("Terran_Barracks"):
            if training_manager.unit_count("Terran_Marine") < 4:
                training_manager.larva_train_distribution().set("Terran_Marine", 1.0)
        
        # === Continue building ===
        if (building_manager.building_exists("Terran_Command_Center", count=2) and
            supply >= 20):
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 2)
        
        # === Transition ===
        if (building_manager.building_exists("Terran_Barracks", count=2) and
            training_manager.unit_count("Terran_Marine") >= 8):
            self.mode_ = TerranMode.MAIN_BIO
    
    def opening_TvT_1FactFE(self) -> None:
        """Handle TvT 1 Fact FE - Factory with expansion."""
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === Early Factory ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Terran_Factory", 1)
        
        # === Barracks ===
        if supply >= 14:
            building_manager.set_requested_building_count_at_least("Terran_Barracks", 1)
        
        # === Expansion ===
        if (building_manager.building_exists("Terran_Factory") and
            training_manager.unit_count("Terran_Marine") >= 2):
            building_manager.set_requested_building_count_at_least("Terran_Command_Center", 2)
        
        # === Marines from barracks ===
        if building_manager.building_exists("Terran_Barracks"):
            if training_manager.unit_count("Terran_Marine") < 4:
                training_manager.larva_train_distribution().set("Terran_Marine", 0.5)
        
        # === Vultures from factory ===
        if building_manager.building_exists("Terran_Factory"):
            if training_manager.unit_count("Terran_Vulture") < 4:
                training_manager.larva_train_distribution().set("Terran_Vulture", 0.5)
        
        # === Transition ===
        if (building_manager.building_exists("Terran_Command_Center", count=2) and
            training_manager.unit_count("Terran_Vulture") >= 4):
            self.mode_ = TerranMode.MAIN_MECH
