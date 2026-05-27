"""TvU Fast Drop (supply milestone 기반)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1
  supply 11 → Refinery ×1
  supply 13 → Academy ×1, Barracks ×2
  supply 15 → Factory ×1
  supply 17 → Starport ×1
  Dropship + Medic + Marine → 드락 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_fd"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Fast Drop 시작 (supply milestone)")
    h.start_trace("TvU_FD", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            factory=h.count_including_unfinished("Terran Factory"),
            starport=h.count_including_unfinished("Terran Starport"),
            dropship=h.count_including_unfinished("Terran Dropship"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Fast Drop 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=18)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 11:
            h.try_build_at_most("Terran Refinery", 100, 1)

        if s >= 13:
            h.try_build_at_most("Terran Academy", 150, 1)
            h.try_build_at_most("Terran Barracks", 150, 2)

        if s >= 15 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        if s >= 17 and h.has("Terran Factory"):
            h.try_build_at_most("Terran Starport", 150, 1, gas_cost=100)

        # 유닛 생산
        if h.has("Terran Barracks"):
            h.try_train("Terran Barracks", "Terran Marine", 50, max_count=8)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25, max_count=4)
        if h.has("Terran Starport"):
            h.try_train("Terran Starport", "Terran Dropship", 100, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_train("Terran Factory", "Terran Vulture", 75)

        if h.count_of("Terran Dropship") >= 1 and h.count_of("Terran Marine") >= 4:
            h.attack_with(["Terran Marine", "Terran Medic", "Terran Dropship",
                           "Terran Vulture"], min_army=6)
            ctx.log("TvU Fast Drop 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
