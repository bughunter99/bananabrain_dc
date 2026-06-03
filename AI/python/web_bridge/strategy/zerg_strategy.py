from __future__ import annotations

from .base import BaseStrategy
from .opening_profile import OpeningProfileMixin


class ZergStrategy(OpeningProfileMixin, BaseStrategy):
    name = "ZergStrategy"
    race_key = "zerg"

    ZVZ = [
        "ZvZ_4pool",
        "ZvZ_5pool",
        "ZvZ_2hatchling",
        "ZvZ_3hatchling",
        "ZvZ_9hatchling",
        "ZvZ_9poolspire",
        "ZvZ_9gas9pool",
        "ZvZ_9gas10pool",
        "ZvZ_11gas10pool",
        "ZvZ_overgas",
        "ZvZ_overpool9gas",
        "ZvZ_10hatch",
        "ZvZ_12pool",
        "ZvZ_12poolmain",
        "ZvZ_hydra",
    ]
    ZVT = [
        "ZvT_4pool",
        "ZvT_5pool",
        "ZvT_7pool",
        "ZvT_2hatchling",
        "ZvT_3hatchling",
        "ZvT_9hatchling",
        "ZvT_2hatchmuta_12hatch",
        "ZvT_2hatchmuta_12pool",
        "ZvT_2_5hatchmuta",
        "ZvT_3hatchmuta",
        "ZvT_crazyzerg",
        "ZvT_13poolmuta",
        "ZvT_mutahydra",
        "ZvT_9poollurker",
        "ZvT_3hatchlurker",
    ]
    ZVP = [
        "ZvP_5pool",
        "ZvP_2hatchling",
        "ZvP_3hatchling",
        "ZvP_9hatchling",
        "ZvP_10hatchling",
        "ZvP_2hatchmuta",
        "ZvP_3hatchmuta",
        "ZvP_2hatchhydra",
        "ZvP_9734",
        "ZvP_10poollurker",
        "ZvP_3hatchlurker",
        "ZvP_neosauron",
        "ZvP_4hatchbeforegas",
        "ZvP_5hatchbeforegas",
        "ZvP_6hatch",
    ]
    ZVU = ["ZvU_4pool", "ZvU_5pool", "ZvU_2hatchling", "ZvU_3hatchling", "ZvU_9hatchling", "ZvU_9poolspeed", "ZvU_11pool"]

    opening_profiles = {
        "ZvT_3hatchmuta": {
            "mode": "Main Muta/Hydra/Lurker/Ling",
            "build_requests": [
                {"type": "build_structure", "building_type": "Hatchery"},
                {"type": "build_structure", "building_type": "Spire"},
            ],
        },
        "ZvT_9poollurker": {
            "mode": "Main Hydra/Lurker/Ling",
            "build_requests": [
                {"type": "build_structure", "building_type": "Hydralisk_Den"},
                {"type": "build_structure", "building_type": "Lair"},
            ],
        },
        "ZvP_9734": {
            "mode": "Defend one base protoss",
            "placement": {"defensive_anchor": "natural_sunken"},
            "build_requests": [
                {"type": "build_structure", "building_type": "Spawning_Pool"},
                {"type": "build_structure", "building_type": "Hydralisk_Den"},
            ],
        },
    }

    def pick_strategy(self, is_1v1: bool) -> None:
        if not is_1v1:
            self._opening = "ZvU_9poolspeed"
            return

        enemy_opening = self._enemy_opening()
        if self.enemy_race == "Zerg":
            self._opening = self._stable_pick(self.ZVZ, "zvz")
        elif self.enemy_race == "Terran":
            if "bio" in enemy_opening or "marine" in enemy_opening:
                self._opening = "ZvT_3hatchmuta"
            elif "mech" in enemy_opening:
                self._opening = "ZvT_9poollurker"
            else:
                self._opening = self._stable_pick(self.ZVT, "zvt")
        elif self.enemy_race == "Protoss":
            if "dt" in enemy_opening or "dark" in enemy_opening:
                self._opening = "ZvP_9734"
            elif "cannon" in enemy_opening:
                self._opening = "ZvP_2hatchhydra"
            else:
                self._opening = self._stable_pick(self.ZVP, "zvp")
        else:
            self._opening = self._stable_pick(self.ZVU, "zvu")

    def frame_inner(self) -> None:
        frame = int(self.state.get("frame") or self.payload.get("frame") or 0)
        enemy_opening = self._enemy_opening()

        profile_mode = self._profile_mode()
        if profile_mode:
            self._mode = profile_mode
        elif frame < 24 * 3:
            self._mode = "Opening"
        elif "4_5pool" in enemy_opening or "9pool" in enemy_opening:
            self._mode = "Defend fast pool"
        elif "proxy" in enemy_opening and self.enemy_race == "Terran":
            self._mode = "Defend proxy rax"
        elif "pool" in enemy_opening or self._is_defending_rush():
            self._mode = "Defend Fast Pool"
        elif self.enemy_race == "Protoss":
            self._mode = "Defend one base protoss" if "dt" in enemy_opening or "proxy" in enemy_opening else "Main Hydra/Lurker/Ling"
        elif self.enemy_race == "Terran":
            self._mode = "Main Ultra/Ling" if "ultra" in self._opening.lower() else "Main Muta/Hydra/Lurker/Ling"
        elif self.enemy_race == "Zerg":
            self._mode = "Main ZvZ" if self._opening != "ZvZ_9poolspire" else "Main ZvZ late game"
        else:
            self._mode = "Main Muta/Hydra/Lurker/Ling"

        self._late_game_strategy = "zerg_late"

    def decide_building_placement(self) -> None:
        enemy_opening = self._enemy_opening()
        if "pool" in enemy_opening or "proxy" in enemy_opening:
            defensive_anchor = "main_sunken"
            wall_policy = "none"
            expand_priority = "main_hold"
        elif self.enemy_race == "Terran":
            defensive_anchor = "natural_sunken"
            wall_policy = "none"
            expand_priority = "natural"
        else:
            defensive_anchor = "natural_sunken"
            wall_policy = "none"
            expand_priority = "third_hatch"

        self._placement_plan = {
            "plan": "zerg_macro",
            "expand_priority": expand_priority,
            "wall_policy": wall_policy,
            "proxy_policy": "none",
            "defensive_anchor": defensive_anchor,
        }
        self._placement_plan.update(self._profile_placement())

    def decide_build_requests(self) -> None:
        requests = self._profile_build_requests()
        supply = self._opening_supply_count()
        opening = self._opening.lower()
        if not requests:
            mode = self._mode.lower()
            if opening == "zvz_9poolspire":
                if supply >= 9:
                    self._append_unique_build(requests, "Spawning_Pool")
                    self._append_unique_build(requests, "Extractor")
                if supply >= 11:
                    self._append_unique_build(requests, "Lair")
                if supply >= 16:
                    self._append_unique_build(requests, "Spire")
            elif opening == "zvz_9gas9pool":
                if supply >= 9:
                    self._append_unique_build(requests, "Extractor")
                    self._append_unique_build(requests, "Spawning_Pool")
                if supply >= 11:
                    self._append_unique_build(requests, "Lair")
                if supply >= 16:
                    self._append_unique_build(requests, "Spire")
            elif opening == "zvt_3hatchmuta":
                if supply >= 12:
                    self._append_unique_build(requests, "Hatchery")
                if supply >= 16:
                    self._append_unique_build(requests, "Lair")
                if supply >= 20:
                    self._append_unique_build(requests, "Spire")
            if "opening" in mode:
                self._append_unique_build(requests, "Spawning_Pool")
                self._append_unique_build(requests, "Extractor")
            if "hatch" in opening:
                self._append_unique_build(requests, "Hatchery")
            if "defend" in mode and "pool" in mode:
                self._append_unique_build(requests, "Creep_Colony")
            if "main" in mode:
                self._append_unique_build(requests, "Hydralisk_Den")
        self._build_requests = requests
