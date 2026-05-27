"""ZvU Ling Lurker (supply milestone 기반)

빌드 오더:
  supply 9  → Spawning Pool
  Pool + Extractor → Lair → Hydralisk Den → Lurker 변이
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvU_ling_lurker"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Ling Lurker 시작 (supply milestone)")
    h.start_trace("ZvU_LingLurker", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            lair=h.count_including_unfinished("Zerg Lair"),
            den=h.count_including_unfinished("Zerg Hydralisk Den"),
            lurker=h.count_including_unfinished("Zerg Lurker"),
            lings=h.count_including_unfinished("Zerg Zergling"),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "LingLurker 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=16)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        if h.has("Zerg Spawning Pool"):
            h.try_build_at_most("Zerg Extractor", 50, 1)
            h.try_train_larva("Zerg Zergling", 50, max_count=8)

        if h.has("Zerg Spawning Pool") and h.has("Zerg Extractor"):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        if h.has("Zerg Lair"):
            h.try_build_at_most("Zerg Hydralisk Den", 100, 1, gas_cost=50)

        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25, max_count=8)
            h.try_morph("Zerg Hydralisk", "Zerg Lurker", 50, gas_cost=100)

        h.attack_with(["Zerg Lurker", "Zerg Zergling"], min_army=4)
        if h.count_of("Zerg Lurker") >= 2 and h.count_of("Zerg Zergling") >= 6:
            ctx.log("ZvU Ling Lurker 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
