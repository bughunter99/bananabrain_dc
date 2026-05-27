"""TvU Bunkering (supply milestone 기반)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1 (depot 있을 때)
  supply 11 → Bunker ×1  (Barracks 있을 때)
  supply 13 → Refinery ×1, Bunker ×2
  supply 15 → Academy ×1, Barracks ×2
  Marine + Medic 반부 생산 → 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_bunkering"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Bunkering 시작 (supply milestone)")
    h.start_trace("TvU_Bunkering", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            bunkers=h.count_including_unfinished("Terran Bunker"),
            marines=h.count_including_unfinished("Terran Marine"),
            academy=h.count_including_unfinished("Terran Academy"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Bunkering 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=14)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 11 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Bunker", 100, 1)

        if s >= 13:
            h.try_build_at_most("Terran Refinery", 100, 1)
            h.try_build_at_most("Terran Bunker", 100, 2)

        if s >= 15:
            h.try_build_at_most("Terran Academy", 150, 1)
            h.try_build_at_most("Terran Barracks", 150, 2)

        if h.has("Terran Barracks"):
            h.try_train("Terran Barracks", "Terran Marine", 50)

        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25)

        if h.count_of("Terran Marine") >= 8:
            h.attack_with(["Terran Marine", "Terran Medic"], min_army=8)
            ctx.log("TvU Bunkering 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
