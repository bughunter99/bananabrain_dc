from __future__ import annotations

from .base import BaseStrategy
from .opening_profile import OpeningProfileMixin


class TerranStrategy(OpeningProfileMixin, BaseStrategy):
    name = "TerranStrategy"
    race_key = "terran"

    TVZ = [
        "TvZ_fantasy",
        "TvZ_sparks",
        "TvZ_ayumi",
        "TvZ_1raxfe",
        "TvZ_2rax",
        "TvZ_14cc",
        "TvZ_3factgoliath",
        "TvZ_5factgoliath",
        "TvZ_2portwraithbio",
        "TvZ_2portwraithmech",
        "TvZ_8raxmech",
        "TvZ_bbs",
        "TvZ_proxybbs",
    ]
    TVT = [
        "TvT_2factvults",
        "TvT_3factvults",
        "TvT_1factfe",
        "TvT_1raxfe",
        "TvT_14cc",
        "TvT_1raxfebiomech",
        "TvT_2raxbiomech",
        "TvT_1portwraith",
        "TvT_2portwraith",
        "TvT_proxy5rax",
        "TvT_8raxmech",
        "TvT_bbs",
        "TvT_proxybbs",
    ]
    TVP = [
        "TvP_2factvults",
        "TvP_gundamrush",
        "TvP_joyorush",
        "TvP_shallowtwo",
        "TvP_deepsix",
        "TvP_siegeexpand",
        "TvP_1factfe",
        "TvP_1raxfe",
        "TvP_14cc",
        "TvP_strongfd",
        "TvP_101010fd",
        "TvP_bbs",
        "TvP_proxybbs",
    ]
    TVU = ["TvU_1fact", "TvU_1factmech", "TvU_2rax", "TvU_bbs", "TvU_proxybbs"]

    opening_profiles = {
        "TvZ_1raxfe": {
            "mode": "Opening",
            "placement": {"expand_priority": "natural_fast", "wall_policy": "tvz_wall"},
            "build_requests": [
                {"type": "build_structure", "building_type": "Supply_Depot"},
                {"type": "build_structure", "building_type": "Barracks"},
                {"type": "build_structure", "building_type": "Command_Center"},
            ],
        },
        "TvP_siegeexpand": {
            "mode": "Main BioMech",
            "build_requests": [
                {"type": "build_structure", "building_type": "Factory"},
                {"type": "build_structure", "building_type": "Machine_Shop"},
            ],
        },
        "TvP_101010fd": {
            "mode": "Defend Cannon Rush",
            "build_requests": [
                {"type": "build_structure", "building_type": "Barracks"},
                {"type": "build_structure", "building_type": "Bunker"},
            ],
        },
    }

    def pick_strategy(self, is_1v1: bool) -> None:
        if not is_1v1:
            self._opening = "TvU_1fact"
            return

        enemy_opening = self._enemy_opening()
        if self.enemy_race == "Zerg":
            if "pool" in enemy_opening:
                self._opening = "TvZ_1raxfe"
            elif "lurker" in enemy_opening:
                self._opening = "TvZ_2portwraithmech"
            else:
                self._opening = self._stable_pick(self.TVZ, "tvz")
        elif self.enemy_race == "Terran":
            self._opening = self._stable_pick(self.TVT, "tvt")
        elif self.enemy_race == "Protoss":
            if "rush" in enemy_opening or "proxy" in enemy_opening:
                self._opening = "TvP_101010fd"
            else:
                self._opening = self._stable_pick(self.TVP, "tvp")
        else:
            self._opening = self._stable_pick(self.TVU, "tvu")

    def frame_inner(self) -> None:
        frame = int(self.state.get("frame") or self.payload.get("frame") or 0)
        enemy_opening = self._enemy_opening()
        supply_used = int(self.state.get("supply_used") or self.payload.get("supply_used") or 0)

        profile_mode = self._profile_mode()
        if profile_mode:
            self._mode = profile_mode
        elif frame < 24 * 3:
            self._mode = "Opening"
        elif "4_5pool" in enemy_opening or "9pool" in enemy_opening:
            self._mode = "Defend Fast Pool"
        elif self._opening_lost_too_many_workers() or self._is_gas_stolen():
            self._mode = "Main Bio"
        elif "cannon" in enemy_opening:
            self._mode = "Defend Cannon Rush"
        elif "pool" in enemy_opening or self._is_defending_rush():
            self._mode = "Defend Fast Pool"
        elif self._expect_lurkers() or self._expect_dark_templars():
            self._mode = "Main Bio"
        elif self._is_enemy_offense_larger_than_defense():
            self._mode = "Main Bio"
        elif supply_used < 64:
            self._mode = "Main Bio"
        elif supply_used < 96:
            self._mode = "Main BioMech"
        else:
            self._mode = "Main Mech"

        self._late_game_strategy = "mechanic" if self.state.get("map_width_tiles", 0) >= 128 else "bio_mech"

    def decide_building_placement(self) -> None:
        enemy_opening = self._enemy_opening()
        if "pool" in enemy_opening or "ling" in enemy_opening:
            wall_policy = "tvz_wall"
            defensive_anchor = "main_ramp"
        elif "proxy" in enemy_opening:
            wall_policy = "anti_proxy_wall"
            defensive_anchor = "natural"
        else:
            wall_policy = "tvp_standard" if self.enemy_race == "Protoss" else "none"
            defensive_anchor = "natural"

        expand_priority = "natural_fast" if "14cc" in self._opening.lower() or "1raxfe" in self._opening.lower() else "natural"
        proxy_policy = "proxy_bbs" if "proxy" in self._opening.lower() else "none"

        self._placement_plan = {
            "plan": "terran_macro",
            "expand_priority": expand_priority,
            "wall_policy": wall_policy,
            "proxy_policy": proxy_policy,
            "defensive_anchor": defensive_anchor,
        }
        self._placement_plan.update(self._profile_placement())

    def decide_build_requests(self) -> None:
        requests = self._profile_build_requests()
        supply = self._opening_supply_count()
        opening = self._opening.lower()
        if not requests:
            mode = self._mode.lower()
            if opening == "tvz_1raxfe":
                if supply >= 9:
                    self._append_unique_build(requests, "Supply_Depot")
                if supply >= 11:
                    self._append_unique_build(requests, "Barracks")
                if supply >= 15:
                    self._append_unique_build(requests, "Command_Center")
                if supply >= 18:
                    self._append_unique_build(requests, "Bunker")
            elif opening == "tvz_fantasy":
                if supply >= 9:
                    self._append_unique_build(requests, "Supply_Depot")
                if supply >= 11:
                    self._append_unique_build(requests, "Barracks")
                if supply >= 12:
                    self._append_unique_build(requests, "Refinery")
                if supply >= 20:
                    self._append_unique_build(requests, "Factory")
                if supply >= 24:
                    self._append_unique_build(requests, "Machine_Shop")
            if "opening" in mode:
                self._append_unique_build(requests, "Supply_Depot")
                self._append_unique_build(requests, "Barracks")
            if "14cc" in opening or "1raxfe" in opening:
                self._append_unique_build(requests, "Command_Center")
            if "mech" in mode:
                self._append_unique_build(requests, "Factory")
            if "cannon rush" in mode:
                self._append_unique_build(requests, "Bunker")
        self._build_requests = requests
