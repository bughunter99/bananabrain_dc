"""TvU 1 Factory (supply milestone 기반)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1
  supply 11 → Refinery ×1
  supply 14 → Factory ×1
  supply 17 → Machine Shop ×1, Barracks ×2
  supply 21 → Factory ×2
  Marines + Tanks → 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_1Fact"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU 1 Factory 시작 (supply milestone)")
    h.start_trace("TvU_1Fact", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            factory=h.count_including_unfinished("Terran Factory"),
            machine_shop=h.count_including_unfinished("Terran Machine Shop"),
            tanks=h.count_including_unfinished("Terran Siege Tank Tank Mode"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "1Fact 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=16)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 11:
            h.try_build_at_most("Terran Refinery", 100, 1)

        if s >= 14 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        if s >= 17 and h.has("Terran Factory"):
            h.try_build_at_most("Terran Machine Shop", 50, 1, gas_cost=25)
            h.try_build_at_most("Terran Barracks", 150, 2)

        if s >= 21:
            h.try_build_at_most("Terran Factory", 200, 2, gas_cost=100)

        # 유닛 생산
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Factory"):
            h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
            h.try_train("Terran Factory", "Terran Vulture", 75)

        # Factory + Machine Shop 완성 → C++ Main 위임
        if (h.has("Terran Factory") and h.has("Terran Machine Shop")):
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
