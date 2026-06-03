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
        if self._opening == kZvZ_9PoolSpire:
            self.opening_ZvZ_9poolspire()
        else:
            self.update_stage()
    
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
        """Check if enemy has overwhelming offense."""
        return False
    
    def opening_lost_too_many_workers(self) -> bool:
        """Check if lost too many workers during opening."""
        return False
    
    def attack_check_condition(self) -> None:
        """Check if should continue/end attack."""
        pass
    
    def expect_lurkers(self) -> bool:
        """Predict Lurker usage by Zerg opponent."""
        return "lurker" in self._opening.lower()
    
    def expect_dark_templars(self) -> bool:
        """Predict DT usage (always False for Zerg)."""
        return False
