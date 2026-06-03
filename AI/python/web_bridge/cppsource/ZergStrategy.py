"""Zerg race-specific strategy.

C++ equivalent: ZergStrategy.cpp/ZergStrategy.h

Implements ZvP, ZvT, ZvZ strategies with:
- Opening selection
- Larva injection timing
- Unit composition
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Dict, List, Optional

from cppsource.Strategy import Strategy


class ZergMode(Enum):
    """Zerg strategy modes."""
    OPENING = "Opening"
    DEFEND_ONE_BASE_PROTOSS = "Defend one base protoss"
    DEFEND_PROXY_RAX = "Defend proxy rax"
    DEFEND_FAST_POOL = "Defend fast pool"
    MAIN_MUTA_HYDRA_LURKER_LING = "Main Muta/Hydra/Lurker/Ling"
    MAIN_HYDRA_LURKER_LING = "Main Hydra/Lurker/Ling"
    MAIN_ULTRA_LING = "Main Ultra/Ling"
    MAIN_ZVZ = "Main ZvZ"
    MAIN_ZVZ_LATE_GAME = "Main ZvZ late game"


# Zerg opening constants
kZvZ_4Pool = "ZvZ_4pool"
kZvZ_5Pool = "ZvZ_5pool"
kZvZ_2HatchLing = "ZvZ_2hatchling"
kZvZ_3HatchLing = "ZvZ_3hatchling"
kZvZ_9HatchLing = "ZvZ_9hatchling"
kZvZ_9PoolSpire = "ZvZ_9poolspire"
kZvZ_9Gas9Pool = "ZvZ_9gas9pool"
kZvZ_9Gas10Pool = "ZvZ_9gas10pool"
kZvZ_11Gas10Pool = "ZvZ_11gas10pool"
kZvZ_OverGas = "ZvZ_overgas"
kZvZ_OverPool9Gas = "ZvZ_overpool9gas"
kZvZ_10Hatch = "ZvZ_10hatch"
kZvZ_12Pool = "ZvZ_12pool"
kZvZ_12PoolMain = "ZvZ_12pool_main"
kZvZ_Hydra = "ZvZ_hydra"

kZvT_4Pool = "ZvT_4pool"
kZvT_5Pool = "ZvT_5pool"
kZvT_7Pool = "ZvT_7pool"
kZvT_2HatchLing = "ZvT_2hatchling"
kZvT_3HatchLing = "ZvT_3hatchling"
kZvT_9HatchLing = "ZvT_9hatchling"
kZvT_2HatchMuta_12Hatch = "ZvT_2hatchmuta_12hatch"
kZvT_2HatchMuta_12Pool = "ZvT_2hatchmuta_12pool"
kZvT_2_5HatchMuta = "ZvT_2.5hatchmuta"
kZvT_3HatchMuta = "ZvT_3hatchmuta"
kZvT_CrazyZerg = "ZvT_crazyzerg"
kZvT_13PoolMuta = "ZvT_13poolmuta"
kZvT_MutaHydra = "ZvT_mutahydra"
kZvT_9PoolLurker = "ZvT_9poollurker"
kZvT_3HatchLurker = "ZvT_3hatchlurker"

kZvP_5Pool = "ZvP_5pool"
kZvP_2HatchLing = "ZvP_2hatchling"
kZvP_3HatchLing = "ZvP_3hatchling"
kZvP_9HatchLing = "ZvP_9hatchling"
kZvP_10HatchLing = "ZvP_10hatchling"
kZvP_2HatchMuta = "ZvP_2hatchmuta"
kZvP_3HatchMuta = "ZvP_3hatchmuta"
kZvP_2HatchHydra = "ZvP_2hatchhydra"
kZvP_9734 = "ZvP_9734"
kZvP_10PoolLurker = "ZvP_10poollurker"
kZvP_3HatchLurker = "ZvP_3hatchlurker"
kZvP_NeoSauron = "ZvP_neosauron"
kZvP_4HatchBeforeGas = "ZvP_4hatchbeforegas"
kZvP_5HatchBeforeGas = "ZvP_5hatchbeforegas"
kZvP_6Hatch = "ZvP_6hatch"

kZvU_4Pool = "ZvU_4pool"
kZvU_5Pool = "ZvU_5pool"
kZvU_2HatchLing = "ZvU_2hatchling"
kZvU_3HatchLing = "ZvU_3hatchling"
kZvU_9HatchLing = "ZvU_9hatchling"
kZvU_9PoolSpeed = "ZvU_9poolspeed"
kZvU_11Pool = "ZvU_11pool"


@dataclass
class ZergStrategy(Strategy):
    """Zerg-specific strategic decisions."""
    
    mode_: ZergMode = ZergMode.OPENING
    attacking_: bool = False
    opening_attack_started_: bool = False
    fast_pool_sunken_count_: int = 0
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select Zerg strategy based on opponent and 1v1 status."""
        if not is_1v1:
            self._opening = kZvU_9PoolSpeed
            return
        
        from cppsource.OpponentModel import OpponentModel
        from cppsource.Results import ResultStore
        from cppsource.Configuration import Configuration
        
        opponent_model = OpponentModel.Instance()
        result_store = ResultStore.Instance()
        configuration = Configuration.Instance()
        
        enemy_race = opponent_model.enemy_race()
        
        if enemy_race == "Zerg":
            config_opening = configuration.ZvZ_opening() if hasattr(configuration, 'ZvZ_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                # Pick from result store UCB1/Greedy
                options = [kZvZ_4Pool, kZvZ_5Pool, kZvZ_2HatchLing, kZvZ_3HatchLing, kZvZ_9HatchLing,
                          kZvZ_9PoolSpire, kZvZ_9Gas9Pool, kZvZ_9Gas10Pool, kZvZ_11Gas10Pool,
                          kZvZ_OverGas, kZvZ_OverPool9Gas, kZvZ_10Hatch, kZvZ_12Pool, kZvZ_12PoolMain, kZvZ_Hydra]
                self._opening = result_store.pick_strategy(options)
                
        elif enemy_race == "Terran":
            config_opening = configuration.ZvT_opening() if hasattr(configuration, 'ZvT_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kZvT_4Pool, kZvT_5Pool, kZvT_7Pool, kZvT_2HatchLing, kZvT_3HatchLing,
                          kZvT_9HatchLing, kZvT_2HatchMuta_12Hatch, kZvT_2HatchMuta_12Pool,
                          kZvT_2_5HatchMuta, kZvT_3HatchMuta, kZvT_CrazyZerg, kZvT_13PoolMuta,
                          kZvT_MutaHydra, kZvT_9PoolLurker, kZvT_3HatchLurker]
                self._opening = result_store.pick_strategy(options)
                
        elif enemy_race == "Protoss":
            config_opening = configuration.ZvP_opening() if hasattr(configuration, 'ZvP_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kZvP_5Pool, kZvP_2HatchLing, kZvP_3HatchLing, kZvP_9HatchLing,
                          kZvP_10HatchLing, kZvP_2HatchMuta, kZvP_3HatchMuta, kZvP_2HatchHydra,
                          kZvP_9734, kZvP_10PoolLurker, kZvP_3HatchLurker, kZvP_NeoSauron,
                          kZvP_4HatchBeforeGas, kZvP_5HatchBeforeGas, kZvP_6Hatch]
                self._opening = result_store.pick_strategy(options)
        else:
            config_opening = configuration.ZvU_opening() if hasattr(configuration, 'ZvU_opening') else ""
            if config_opening:
                self._opening = config_opening
            else:
                options = [kZvU_4Pool, kZvU_5Pool, kZvU_2HatchLing, kZvU_3HatchLing,
                          kZvU_9HatchLing, kZvU_9PoolSpeed, kZvU_11Pool]
                self._opening = result_store.pick_strategy(options)
    
    def mode(self) -> str:
        """Get current mode as string."""
        return str(self.mode_.value)
    
    def frame_inner(self) -> None:
        """Execute Zerg strategy logic each frame."""
        # Handle by opening during opening phase
        if self.mode_ == ZergMode.OPENING:
            if self._opening == kZvZ_9PoolSpire:
                self.opening_ZvZ_9poolspire()
            else:
                self.update_stage()
        
        # Handle main strategies
        elif self.mode_ == ZergMode.MAIN_ZVZ:
            self.main_ZvZ()
        elif self.mode_ == ZergMode.DEFEND_FAST_POOL:
            self.defend_fast_pool()
        elif self.mode_ == ZergMode.MAIN_MUTA_HYDRA_LURKER_LING:
            self.main_muta_hydra()
        else:
            self.update_stage()
    
    def main_ZvZ(self) -> None:
        """Handle MAIN_ZVZ strategy - sustained mutalisk harassment."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.Tactics import TacticsManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        tactics = TacticsManager.Instance()
        
        # Continue mutalisk production
        mutalisk_count = training_manager.unit_count("Zerg_Mutalisk")
        if mutalisk_count < 12:
            training_manager.larva_train_distribution().set("Zerg_Mutalisk", 1.0)
        
        # Expand to 3 bases if ahead
        if mutalisk_count >= 6 and tactics.enemy_pressure() == "low":
            building_manager.set_requested_building_count_at_least("Zerg_Hatchery", 3)
        
        # Add hydras for anti-air
        if mutalisk_count >= 8:
            if training_manager.unit_count("Zerg_Hydralisk") < 6:
                training_manager.larva_train_distribution().set("Zerg_Hydralisk", 0.5)
        
        # Continue attacking
        if tactics.should_attack():
            self.attacking_ = True
        
        # Late game transition
        if mutalisk_count >= 15 and training_manager.unit_count("Zerg_Hydralisk") >= 8:
            self.mode_ = ZergMode.MAIN_ZVZ_LATE_GAME
    
    def defend_fast_pool(self) -> None:
        """Handle DEFEND_FAST_POOL strategy - defend against early pool pressure."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.OpponentModel import OpponentModel
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        opponent_model = OpponentModel.Instance()
        
        supply = self.opening_supply_count()
        
        # === Emergency Sunken Colonies ===
        if supply <= 16:
            # Build sunkens at choke points
            sunken_count = self.fast_pool_sunken_count_
            if sunken_count < 3:
                building_manager.set_requested_building_count_at_least("Zerg_Sunken_Colony", min(3, sunken_count + 1))
        
        # === Defense Zerglings ===
        zergling_count = training_manager.unit_count("Zerg_Zergling")
        if zergling_count < 8:
            training_manager.larva_train_distribution().set("Zerg_Zergling", 1.0)
        
        # === Get to Lair for Overlord armor ===
        if supply >= 20:
            building_manager.set_requested_building_count_at_least("Zerg_Lair", 1)
        
        # === Overlord armor upgrade ===
        if building_manager.building_exists("Zerg_Lair"):
            building_manager.request_upgrade("Overlord_Armor")
        
        # === Counter based on enemy ===
        enemy_opening = opponent_model.enemy_opening()
        
        # If early zerglings coming, focus defense
        if "4_5pool" in enemy_opening.lower():
            self.fast_pool_sunken_count_ = 3
            # Keep producing zerglings
            training_manager.larva_train_distribution().clear()
            training_manager.larva_train_distribution().set("Zerg_Zergling", 1.0)
        
        # === Transition to main when safe ===
        if (zergling_count >= 8 and 
            building_manager.building_count_including_planned("Zerg_Sunken_Colony") >= 2):
            self.mode_ = ZergMode.MAIN_ZVZ
    
    def main_muta_hydra(self) -> None:
        """Handle MAIN_MUTA_HYDRA_LURKER_LING - mixed composition strategy."""
        from cppsource.TrainingManager import TrainingManager
        from cppsource.BuildingPlacement import BuildingPlacementManager
        
        training_manager = TrainingManager.Instance()
        building_manager = BuildingPlacementManager.Instance()
        
        # Balance mixed composition
        mutalisk_count = training_manager.unit_count("Zerg_Mutalisk")
        hydralisk_count = training_manager.unit_count("Zerg_Hydralisk")
        
        # Target ratio: 2 mutalisks per 1 hydralisk
        if mutalisk_count < hydralisk_count * 2 + 2:
            training_manager.larva_train_distribution().set("Zerg_Mutalisk", 0.7)
        else:
            training_manager.larva_train_distribution().set("Zerg_Hydralisk", 0.5)
        
        # Add zerglings as needed
        zergling_count = training_manager.unit_count("Zerg_Zergling")
        if zergling_count < 6:
            training_manager.larva_train_distribution().set("Zerg_Zergling", 0.3)
        
        # Lurker support
        if building_manager.building_exists("Zerg_Lair"):
            lurker_count = training_manager.unit_count("Zerg_Lurker")
            if lurker_count < 3:
                training_manager.larva_train_distribution().set("Zerg_Lurker", 0.2)
    
    def update_stage(self) -> None:
        """Update Zerg stage."""
        pass
    
    def opening_ZvZ_9poolspire(self) -> None:
        """Handle ZvZ 9 pool spire opening.
        
        C++ equivalent: void ZergStrategy::opening_ZvZ_9poolspire()
        
        Complete opening sequence:
        1. Check opponent for fast pool defense
        2. Request pool, extractor, lair, spire in sequence
        3. Train overlords, zerglings, mutalisks
        4. Upgrade speed, transition to main
        """
        from cppsource.OpponentModel import OpponentModel
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        from cppsource.Worker import WorkerManager
        
        opponent_model = OpponentModel.Instance()
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        worker_manager = WorkerManager.Instance()
        
        # Check for fast pool defense
        if opponent_model.enemy_opening() == "Z_4_5Pool":
            self.fast_pool_sunken_count_ = 0
            self.mode_ = ZergMode.DEFEND_FAST_POOL
            return
        
        # Transition to main if needed
        if (self.is_enemy_offense_larger_than_defense() or
            self.opening_lost_too_many_workers() or
            building_manager.building_placement_failed()):
            self.mode_ = ZergMode.MAIN_ZVZ
            return
        
        # Check if Spire should save larvae
        save_larvae = self.morphing_building_hp_at_least("Zerg_Spire", 350)
        
        # Get current supply
        supply = self.opening_supply_count()
        
        # === SUPPLY 9: Request Pool ===
        if supply >= 9:
            building_manager.set_requested_building_count_at_least("Zerg_Spawning_Pool", 1)
        
        # === SUPPLY 9: Request Extractor (need Pool) ===
        if (supply >= 9 and 
            building_manager.building_count_including_planned("Zerg_Spawning_Pool") >= 1):
            building_manager.set_requested_building_count_at_least("Zerg_Extractor", 1)
        
        # === SUPPLY 8: Train Overlord #2 (need Extractor) ===
        if (supply >= 8 and
            building_manager.building_count_including_planned("Zerg_Extractor") >= 1 and
            training_manager.unit_count("Zerg_Overlord") < 2):
            training_manager.larva_train_distribution().set("Zerg_Overlord", 1.0)
        
        # === Train Zerglings (need Pool, Pool must exist) ===
        if (building_manager.building_exists("Zerg_Spawning_Pool") and
            not save_larvae and
            training_manager.unit_count("Zerg_Zergling") < 6):
            training_manager.larva_train_distribution().set("Zerg_Zergling", 1.0)
        
        # === Force refinery workers (need Extractor) ===
        if (building_manager.building_exists("Zerg_Extractor") and
            training_manager.unit_count("Zerg_Drone") >= 8):
            worker_manager.set_force_refinery_workers(True)
        
        # === Request Metabolic Boost (need 6 Zerglings) ===
        if (building_manager.building_exists("Zerg_Spawning_Pool") and
            training_manager.unit_count("Zerg_Zergling") >= 6):
            building_manager.request_upgrade("Metabolic_Boost")
        
        # === After Metabolic Boost ===
        if self.done_or_in_progress("Metabolic_Boost"):
            # Continue Zerglings or start Lair
            if (not save_larvae and
                training_manager.unit_count("Zerg_Zergling") < 8):
                training_manager.larva_train_distribution().set("Zerg_Zergling", 1.0)
            else:
                building_manager.set_requested_building_count_at_least("Zerg_Lair", 1)
        
        # === Train more Zerglings (need Lair) ===
        if (building_manager.building_count_including_planned("Zerg_Lair") >= 1 and
            not save_larvae and
            training_manager.unit_count("Zerg_Zergling") < 14):
            training_manager.larva_train_distribution().set("Zerg_Zergling", 1.0)
        
        # === Request Spire (need Lair + Metabolic Boost) ===
        if (self.done_or_in_progress("Metabolic_Boost") and
            building_manager.building_exists("Zerg_Lair")):
            building_manager.set_requested_building_count_at_least("Zerg_Spire", 1)
        
        # === SUPPLY 16: Train Overlord #3 ===
        if supply >= 16 and training_manager.unit_count("Zerg_Overlord") < 3:
            training_manager.larva_train_distribution().set("Zerg_Overlord", 1.0)
        
        # === Train Mutalisks (need Spire + 3 Overlords) ===
        if (building_manager.building_exists("Zerg_Spire") and
            training_manager.unit_count("Zerg_Overlord") >= 3 and
            training_manager.unit_count("Zerg_Mutalisk") < 3):
            training_manager.larva_train_distribution().clear()
            training_manager.larva_train_distribution().set("Zerg_Mutalisk", 1.0)
        
        # === Transition to Main (3 Mutalisks + attack started) ===
        if (self.opening_attack_started_ and
            training_manager.unit_count("Zerg_Mutalisk") >= 3):
            self.mode_ = ZergMode.MAIN_ZVZ
            return
        
        # === Start attack with 2 Zerglings ===
        if (training_manager.unit_count("Zerg_Zergling") >= 2 and
            not self.opening_attack_started_):
            self.attacking_ = True
            self.opening_attack_started_ = True
        
        # === Continue attack check ===
        if self.opening_attack_started_:
            self.attack_check_condition()
        
        # === Train replacement Drones ===
        if (not save_larvae and
            training_manager.unit_count("Zerg_Drone") < 9 and
            training_manager.larva_train_distribution().is_empty()):
            training_manager.larva_train_distribution().set("Zerg_Drone", 1.0)
    
    def is_enemy_offense_larger_than_defense(self) -> bool:
        """Check if enemy has overwhelming offense vs own defense."""
        from cppsource.Information import InformationManager
        from cppsource.Tactics import TacticsManager
        
        info = InformationManager.Instance()
        tactics = TacticsManager.Instance()
        
        # Check if main enemy cluster exists and is threatening
        enemy_pressure = tactics.enemy_pressure()
        if enemy_pressure == "critical":
            return True
        if enemy_pressure == "high":
            # Check actual army counts
            enemy_units = info.enemy_units()
            own_units = info.my_units()
            
            enemy_count = len(enemy_units) if enemy_units else 0
            own_count = len(own_units) if own_units else 0
            
            # If enemy has 2x more units, we're overwhelmed
            return enemy_count > own_count * 2
        
        return False
    
    def opening_lost_too_many_workers(self) -> bool:
        """Check if lost too many workers during opening."""
        from cppsource.Information import InformationManager
        
        info = InformationManager.Instance()
        
        # Get current drone count
        current_drones = info.count_unit("Zerg_Drone")
        
        # Expected drones for opening stage
        # 9PoolSpire typically has 9 drones by mid-game
        # If we have less than 4, something went wrong
        expected_drones = 9
        acceptable_loss = 5
        
        return current_drones < (expected_drones - acceptable_loss)
    
    def attack_check_condition(self) -> None:
        """Check if should continue/end attack during opening."""
        from cppsource.Information import InformationManager
        from cppsource.Tactics import TacticsManager
        
        info = InformationManager.Instance()
        tactics = TacticsManager.Instance()
        
        # Get zergling count
        zergling_count = info.count_unit("Zerg_Zergling")
        
        # End attack if lost all zerglings
        if zergling_count == 0:
            self.attacking_ = False
            return
        
        # End attack if enemy is too strong
        if tactics.enemy_pressure() == "critical":
            self.attacking_ = False
            return
        
        # Continue attack if we have advantage or can harass
        self.attacking_ = True
    
    def opening_supply_count(self) -> int:
        """Get current supply used in opening phase.
        
        Supply = number of units consuming supply (Drones, Overlords, combat units)
        """
        from cppsource.Information import InformationManager
        
        info = InformationManager.Instance()
        
        supply = 0
        
        # Each unit type consumes supply
        supply += info.count_unit("Zerg_Drone") * 1         # 1 supply each
        supply += info.count_unit("Zerg_Overlord") * 8      # Overlords provide +8 supply
        supply += info.count_unit("Zerg_Zergling") * 1      # 1 supply each
        supply += info.count_unit("Zerg_Mutalisk") * 3      # 3 supply each
        supply += info.count_unit("Zerg_Hydralisk") * 2     # 2 supply each
        supply += info.count_unit("Zerg_Lurker") * 2        # 2 supply each
        
        # Return only supply used (not provided by Overlords)
        # Rough calculation: total - overlord supply provided
        overlord_count = info.count_unit("Zerg_Overlord")
        overlord_supply_provided = overlord_count * 8
        
        # Supply used is roughly: drones + combat units
        supply_used = (info.count_unit("Zerg_Drone") +
                      info.count_unit("Zerg_Zergling") +
                      info.count_unit("Zerg_Mutalisk") * 3 +
                      info.count_unit("Zerg_Hydralisk") * 2 +
                      info.count_unit("Zerg_Lurker") * 2)
        
        return supply_used
    
    def expect_lurkers(self) -> bool:
        """Predict Lurker usage by Zerg opponent."""
        return "lurker" in self._opening.lower()
    
    def expect_dark_templars(self) -> bool:
        """Predict DT usage (always False for Zerg)."""
        return False
    
    def opening_ZvT_2hatchmuta(self) -> None:
        """Handle ZvT 2 Hatch Mutalisk opening.
        
        Early mutalisk pressure vs Terran with 2 hatcheries.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 12: Request Extractor ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Zerg_Extractor", 1)
        
        # === SUPPLY 13: Request Second Hatchery ===
        if supply >= 13:
            building_manager.set_requested_building_count_at_least("Zerg_Hatchery", 2)
        
        # === Request Lair (need second Hatchery) ===
        if building_manager.building_exists("Zerg_Hatchery", count=2):
            building_manager.set_requested_building_count_at_least("Zerg_Lair", 1)
        
        # === Request Spire (need Lair) ===
        if building_manager.building_exists("Zerg_Lair"):
            building_manager.set_requested_building_count_at_least("Zerg_Spire", 1)
        
        # === Train Mutalisks ===
        if building_manager.building_exists("Zerg_Spire"):
            if training_manager.unit_count("Zerg_Mutalisk") < 6:
                training_manager.larva_train_distribution().set("Zerg_Mutalisk", 1.0)
        
        # === Transition ===
        if training_manager.unit_count("Zerg_Mutalisk") >= 6:
            self.mode_ = ZergMode.MAIN_MUTA_HYDRA_LURKER_LING
    
    def opening_ZvP_2hatchmuta(self) -> None:
        """Handle ZvP 2 Hatch Mutalisk opening.
        
        Fast expand with mutas vs Protoss.
        """
        from cppsource.BuildingPlacement import BuildingPlacementManager
        from cppsource.TrainingManager import TrainingManager
        
        building_manager = BuildingPlacementManager.Instance()
        training_manager = TrainingManager.Instance()
        
        supply = self.opening_supply_count()
        
        # === SUPPLY 12-13: Second Hatchery + Extractor ===
        if supply >= 12:
            building_manager.set_requested_building_count_at_least("Zerg_Hatchery", 2)
            building_manager.set_requested_building_count_at_least("Zerg_Extractor", 1)
        
        # === Request Lair ===
        if (building_manager.building_exists("Zerg_Hatchery", count=2) and
            building_manager.building_exists("Zerg_Extractor")):
            building_manager.set_requested_building_count_at_least("Zerg_Lair", 1)
        
        # === Request Spire ===
        if building_manager.building_exists("Zerg_Lair"):
            building_manager.set_requested_building_count_at_least("Zerg_Spire", 1)
        
        # === Overlord Speed ===
        if building_manager.building_exists("Zerg_Lair"):
            building_manager.request_upgrade("Overlord_Speed")
        
        # === Scout with Overlord ===
        overlord_speed = self.done_or_in_progress("Overlord_Speed")
        if overlord_speed:
            # Once speed is done, send overlord scout
            pass
        
        # === Train Mutalisks ===
        if building_manager.building_exists("Zerg_Spire"):
            if training_manager.unit_count("Zerg_Mutalisk") < 8:
                training_manager.larva_train_distribution().set("Zerg_Mutalisk", 1.0)
        
        # === Transition ===
        if training_manager.unit_count("Zerg_Mutalisk") >= 8:
            self.mode_ = ZergMode.MAIN_MUTA_HYDRA_LURKER_LING
