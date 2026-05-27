"""ZvU Defiler (supply milestone 기반)

빌드 오더:
  supply 9  → Pool
  Pool + Extractor → Lair → Hive → Defiler Mound + Ultralisk Cavern
  Defiler + Ultralisk 생산
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvU_defiler"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Defiler 시작 (supply milestone)")
    h.start_trace("ZvU_Defiler", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            lair=h.count_including_unfinished("Zerg Lair"),
            hive=h.count_including_unfinished("Zerg Hive"),
            defiler=h.count_including_unfinished("Zerg Defiler"),
            ultra=h.count_including_unfinished("Zerg Ultralisk"),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Defiler 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        if h.has("Zerg Spawning Pool"):
            h.try_build_at_most("Zerg Extractor", 50, 2)
            h.try_train_larva("Zerg Zergling", 50, max_count=8)

        if h.has("Zerg Spawning Pool") and h.has("Zerg Extractor"):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        if h.has("Zerg Lair"):
            h.try_morph("Zerg Lair", "Zerg Hive", 200, gas_cost=150)

        if h.has("Zerg Hive"):
            h.try_build_at_most("Zerg Defiler Mound", 100, 1, gas_cost=100)
            h.try_build_at_most("Zerg Ultralisk Cavern", 150, 1, gas_cost=200)

        if h.has("Zerg Defiler Mound"):
            h.try_train_larva("Zerg Defiler", 50, gas_cost=150, max_count=4)

        if h.has("Zerg Ultralisk Cavern"):
            h.try_train_larva("Zerg Ultralisk", 200, gas_cost=200)

        h.attack_with(["Zerg Ultralisk", "Zerg Zergling", "Zerg Defiler"], min_army=4)

            if h.count_of("Zerg Defiler") >= 2 and h.count_of("Zerg Ultralisk") >= 2:
                ctx.log("ZvU Defiler 오프닝 완료 → C++ 자율 플레이 전환")
                h.delegate_to_cpp(CPP_OPENING)
                return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
