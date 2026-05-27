"""TvZ 2 Rax (C++ opening_TvZ_2rax 기반)

빌드 오더:
  supply 9  → Supply Depot ×1, 스카웃
  supply 11 → Barracks ×1
  supply 13 → Barracks ×2
  supply 14 → Supply Depot ×2
  supply 15 → Refinery ×1
  supply 18 → Academy ×1
  Marine + Medic 생산 → Academy 완성 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvZ_2Rax"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvZ 2 Rax 시작 (supply milestone)")
    h.start_trace("TvZ_2Rax", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            marines=h.count_including_unfinished("Terran Marine"),
            medics=h.count_including_unfinished("Terran Medic"),
            academy=h.count_including_unfinished("Terran Academy"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "2Rax 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=14)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Terran Supply Depot", 100, 1)
            if h.has_including_unfinished("Terran Supply Depot") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 11:
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 13:
            h.try_build_at_most("Terran Barracks", 150, 2)

        if s >= 14:
            h.try_build_at_most("Terran Supply Depot", 100, 2)

        if s >= 15:
            h.try_build_at_most("Terran Refinery", 100, 1)

        if s >= 18:
            if h.has_including_unfinished("Terran Barracks"):
                h.try_build_at_most("Terran Academy", 150, 1)

        # 유닛 생산
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25)

        # Academy 완성 → C++ Main
        if h.has("Terran Academy"):
            ctx.log("TvZ 2 Rax 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
