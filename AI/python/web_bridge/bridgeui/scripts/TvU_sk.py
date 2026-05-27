"""TvU SK Terran (supply milestone 기반)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1
  supply 13 → Refinery ×1, Barracks ×2
  supply 15 → Academy ×1
  supply 17 → Barracks ×3
  supply 19 → Factory ×1
  supply 21 → Starport ×1
  Science Vessel + Marine + Medic → 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_sk"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU SK Terran 시작 (supply milestone)")
    h.start_trace("TvU_SK", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            academy=h.count_including_unfinished("Terran Academy"),
            starport=h.count_including_unfinished("Terran Starport"),
            vessel=h.count_including_unfinished("Terran Science Vessel"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "SK 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 13:
            h.try_build_at_most("Terran Refinery", 100, 1)
            h.try_build_at_most("Terran Barracks", 150, 2)

        if s >= 15 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Academy", 150, 1)

        if s >= 17:
            h.try_build_at_most("Terran Barracks", 150, 3)

        if s >= 19 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        if s >= 21 and h.has("Terran Factory"):
            h.try_build_at_most("Terran Starport", 150, 1, gas_cost=100)
            h.try_build_at_most("Terran Control Tower", 50, 1, gas_cost=50)

        # 유닛 생산
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25)
        if h.has("Terran Control Tower"):
            h.try_train("Terran Starport", "Terran Science Vessel", 100, gas_cost=225, max_count=2)

        if h.count_of("Terran Marine") >= 8:
            h.attack_with(["Terran Marine", "Terran Medic", "Terran Science Vessel"],
                          min_army=8)

        if (h.count_including_unfinished("Terran Barracks") >= 3 and
                h.count_of("Terran Marine") >= 8 and
                h.count_of("Terran Medic") >= 2 and
                h.count_of("Terran Science Vessel") >= 1):
            ctx.log("TvU SK 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
