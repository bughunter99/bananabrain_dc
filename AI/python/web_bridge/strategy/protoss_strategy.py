from __future__ import annotations

from .base import BaseStrategy
from .opening_profile import OpeningProfileMixin


class ProtossStrategy(OpeningProfileMixin, BaseStrategy):
    name = "ProtossStrategy"
    race_key = "protoss"

    PVZ = [
        "PvZ_sairdt",
        "PvZ_10/12gate",
        "PvZ_1basespeedzeal",
        "PvZ_2basespeedzeal",
        "PvZ_bisu",
        "PvZ_neobisu",
        "PvZ_4gate2archon",
        "PvZ_5gategoon",
        "PvZ_sairgoon",
        "PvZ_sairreaver",
        "PvZ_stove",
        "PvZ_4gategoon",
        "PvZ_9/9gate",
        "PvZ_9/9proxygate",
    ]
    PVT = [
        "PvT_10/12gate",
        "PvT_2gatedt",
        "PvT_1gatedtexpo",
        "PvT_2gaterngexpo",
        "PvT_1gatereaver",
        "PvT_10/15gate",
        "PvT_bulldog",
        "PvT_12nexus",
        "PvT_28nexus",
        "PvT_32nexus",
        "PvT_dtdrop",
        "PvT_stove",
        "PvT_4gategoon",
        "PvT_9/9gate",
        "PvT_9/9proxygate",
    ]
    PVP = [
        "PvP_nzcore",
        "PvP_zcore",
        "PvP_zzcore",
        "PvP_zcorez",
        "PvP_10/12gate",
        "PvP_10/12gatedt",
        "PvP_2gatedtexpo",
        "PvP_2gatereaver",
        "PvP_3gaterobo",
        "PvP_3gatespeedzeal",
        "PvP_4gategoon",
        "PvP_12nexus",
        "PvP_9/9gate",
        "PvP_9/9proxygate",
    ]
    PVU = [
        "PvU_10/12gate",
        "PvU_9/9gate",
        "PvU_9/9proxygate",
        "PvU_4gategoon",
        "PvU_forge",
        "PvU_plasma_carriers",
        "PvU_plasma_9/9proxygate",
    ]

    opening_profiles = {
        "PvT_12nexus": {
            "mode": "Reactive fast expand",
            "placement": {"expand_priority": "natural_fast", "wall_policy": "none"},
            "build_requests": [
                {"type": "build_structure", "building_type": "Pylon"},
                {"type": "build_structure", "building_type": "Gateway"},
                {"type": "build_structure", "building_type": "Nexus"},
            ],
        },
        "PvT_9/9proxygate": {
            "mode": "Defend proxy gate",
            "placement": {"proxy_policy": "9_9_proxy", "defensive_anchor": "enemy_natural"},
            "build_requests": [
                {"type": "build_structure", "building_type": "Pylon"},
                {"type": "build_structure", "building_type": "Gateway"},
            ],
        },
        "PvZ_bisu": {
            "mode": "Defend fast pool",
            "placement": {"wall_policy": "forge_expand_wall", "defensive_anchor": "natural"},
            "build_requests": [
                {"type": "build_structure", "building_type": "Forge"},
                {"type": "build_structure", "building_type": "Photon_Cannon"},
            ],
        },
        "PvP_3gaterobo": {
            "mode": "Main",
            "build_requests": [
                {"type": "build_structure", "building_type": "Gateway"},
                {"type": "build_structure", "building_type": "Robotics_Facility"},
            ],
        },
    }

    def pick_strategy(self, is_1v1: bool) -> None:
        if not is_1v1:
            self._opening = "PvU_10/12gate"
            return

        enemy_opening = self._enemy_opening()
        if self.enemy_race == "Zerg":
            if "pool" in enemy_opening:
                self._opening = "PvZ_bisu"
            elif "muta" in enemy_opening:
                self._opening = "PvZ_sairgoon"
            else:
                self._opening = self._stable_pick(self.PVZ, "pvz")
        elif self.enemy_race == "Terran":
            if "proxy" in enemy_opening or "rush" in enemy_opening:
                self._opening = "PvT_9/9proxygate"
            elif "bio" in enemy_opening or "marine" in enemy_opening:
                self._opening = "PvT_10/12gate"
            else:
                self._opening = self._stable_pick(self.PVT, "pvt")
        elif self.enemy_race == "Protoss":
            if "fast" in enemy_opening:
                self._opening = "PvP_3gaterobo"
            else:
                self._opening = self._stable_pick(self.PVP, "pvp")
        else:
            self._opening = self._stable_pick(self.PVU, "pvu")

    def frame_inner(self) -> None:
        frame = int(self.state.get("frame") or self.payload.get("frame") or 0)
        supply_used = int(self.state.get("supply_used") or self.payload.get("supply_used") or 0)
        enemy_opening = self._enemy_opening()

        profile_mode = self._profile_mode()
        if profile_mode:
            self._mode = profile_mode
        elif frame < 24 * 3:
            self._mode = "Opening"
        elif self._opening_lost_too_many_workers() or self._is_gas_stolen():
            self._mode = "Main"
        elif ("4_5pool" in enemy_opening or "9pool" in enemy_opening) and ("forge" in self._opening.lower() or "bisu" in self._opening.lower() or "2base" in self._opening.lower()):
            self._mode = "Defend fast pool (FFE)"
        elif "pool" in enemy_opening or self._is_defending_rush():
            self._mode = "Defend fast pool"
        elif "proxy" in enemy_opening:
            self._mode = "Defend proxy gate"
        elif "cannon" in enemy_opening:
            self._mode = "Defend cannon rush"
        elif "4gate" in enemy_opening or "4 gate" in enemy_opening:
            self._mode = "Defend four gate goon"
        elif "3hatch" in enemy_opening and "ling" in enemy_opening:
            self._mode = "Defend three hatch ling (FFE)"
        elif self._is_enemy_offense_larger_than_defense() or self._is_contained():
            self._mode = "Reactive fast expand"
        elif supply_used < 40:
            self._mode = "Reactive fast expand"
        else:
            self._mode = "Main"

        map_width = int(self.state.get("map_width_tiles") or 128)
        map_height = int(self.state.get("map_height_tiles") or 128)
        max_dim = max(map_width, map_height)
        if max_dim <= 384:
            self._late_game_strategy = "carriers"
        elif max_dim >= 512:
            self._late_game_strategy = "arbiters"
        else:
            self._late_game_strategy = "arbiters" if (max_dim % 2 == 0) else "carriers"

    def decide_building_placement(self) -> None:
        enemy_opening = self._enemy_opening()
        if "cannon" in enemy_opening:
            wall_policy = "block_choke"
            defensive_anchor = "natural"
        elif "pool" in enemy_opening or "rush" in enemy_opening:
            wall_policy = "tight_wall"
            defensive_anchor = "main_ramp"
        else:
            wall_policy = "forge_expand_wall" if "forge" in self._opening.lower() else "none"
            defensive_anchor = "natural"

        proxy_policy = "9_9_proxy" if "9/9proxygate" in self._opening.lower() else "none"
        expand_priority = "natural_fast" if "nexus" in self._opening.lower() else "natural"

        self._placement_plan = {
            "plan": "protoss_macro",
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
            if opening == "pvz_sairdt":
                if supply >= 8:
                    self._append_unique_build(requests, "Pylon")
                if supply >= 10:
                    self._append_unique_build(requests, "Gateway")
                if supply >= 12:
                    self._append_unique_build(requests, "Assimilator")
                if supply >= 20:
                    self._append_unique_build(requests, "Cybernetics_Core")
            elif opening == "pvz_1basespeedzeal":
                if supply >= 8:
                    self._append_unique_build(requests, "Pylon")
                if supply >= 10:
                    self._append_unique_build(requests, "Gateway")
                if supply >= 12:
                    self._append_unique_build(requests, "Assimilator")
                if supply >= 20:
                    self._append_unique_build(requests, "Cybernetics_Core")
                if supply >= 27:
                    self._append_unique_build(requests, "Citadel_of_Adun")
                if supply >= 37:
                    self._append_unique_build(requests, "Templar_Archives")
            elif opening == "pvt_12nexus":
                if supply >= 8:
                    self._append_unique_build(requests, "Pylon")
                if supply >= 10:
                    self._append_unique_build(requests, "Gateway")
                if supply >= 12:
                    self._append_unique_build(requests, "Nexus")
                if supply >= 16:
                    self._append_unique_build(requests, "Assimilator")
            if "opening" in mode:
                self._append_unique_build(requests, "Pylon")
                self._append_unique_build(requests, "Gateway")
            if "nexus" in opening or "fast expand" in mode:
                self._append_unique_build(requests, "Nexus")
            if "cannon" in mode:
                self._append_unique_build(requests, "Photon_Cannon")
            if "main" in mode:
                self._append_unique_build(requests, "Assimilator")
        self._build_requests = requests
