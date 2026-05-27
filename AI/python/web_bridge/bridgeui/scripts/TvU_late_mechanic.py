"""TvU Late Mechanic — Battlecruiser + Tank (supply milestone)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1
  supply 11 → Refinery ×1
  supply 13 → Refinery ×2
  supply 14 → Factory ×1
  supply 17 → Machine Shop, Factory ×2, Armory
  supply 21 → Starport ×1 → Science Facility → Physics Lab
  Battlecruiser → 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_late_mechanic"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Late Mechanic 시작 (supply milestone)")
    h.start_trace("TvU_LateMechanic", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            factories=h.count_including_unfinished("Terran Factory"),
            starport=h.count_including_unfinished("Terran Starport"),
            physics_lab=h.count_including_unfinished("Terran Physics Lab"),
            bc=h.count_including_unfinished("Terran Battlecruiser"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Late Mechanic 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 11:
            h.try_build_at_most("Terran Refinery", 100, 1)

        if s >= 13:
            h.try_build_at_most("Terran Refinery", 100, 2)

        if s >= 14 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        if s >= 17 and h.has("Terran Factory"):
            h.try_build_at_most("Terran Machine Shop", 50, 1, gas_cost=25)
            h.try_build_at_most("Terran Factory", 200, 2, gas_cost=100)
            h.try_build_at_most("Terran Armory", 100, 1, gas_cost=50)

        if s >= 21:
            h.try_build_at_most("Terran Starport", 150, 1, gas_cost=100)

        if h.has("Terran Armory") and h.has("Terran Starport"):
            h.try_build_at_most("Terran Science Facility", 100, 1, gas_cost=150)

        if h.has("Terran Science Facility"):
            h.try_build_at_most("Terran Physics Lab", 50, 1, gas_cost=50)

        # 유닛 생산
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=4)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        if h.has("Terran Physics Lab"):
            h.try_train("Terran Starport", "Terran Battlecruiser", 400, gas_cost=300)

        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Battlecruiser"], min_army=2)

        if h.count_of("Terran Battlecruiser") >= 1 and h.count_of("Terran Siege Tank Tank Mode") >= 2:
            ctx.log("TvU Late Mechanic 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
