"""ZvT 9 Pool Lurker (C++ opening_ZvT_9poollurker 기반)

빌드 오더:
  supply 9  → Spawning Pool, Extractor
  Extractor → Zergling ×6
  Pool+Extractor+Zergling≥6 → Lair
  supply 14 + Lair 건설중 → Hydralisk Den
  Hydralisk Den 완성 → Hydra 생산 → Lurker 변이
  Lurker ×4 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvT 9 Pool Lurker 시작 (supply milestone)")
    h.start_trace("ZvT_9PoolLurker", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            gas=h.count_including_unfinished("Zerg Extractor"),
            lair=h.count_including_unfinished("Zerg Lair"),
            den=h.count_including_unfinished("Zerg Hydralisk Den"),
            lurker=h.count_including_unfinished("Zerg Lurker"),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "9Pool Lurker 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp()
            return

        h.manage_workers(desired=14)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        if h.has("Zerg Spawning Pool"):
            h.try_build_at_most("Zerg Extractor", 50, 1)

        if h.has("Zerg Extractor"):
            # Zergling 6기 먼저 생산 (Lair 전 수비)
            h.try_train_larva("Zerg Zergling", 50, max_count=6)

        # Pool+Extractor 완성 AND Zergling 6기 이상 → Lair
        if (h.has("Zerg Spawning Pool") and
                h.has("Zerg Extractor") and
                h.count_including_unfinished("Zerg Zergling") >= 6):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        # supply 14 + Lair 건설중 → Hydralisk Den
        if s >= 14 and h.has_including_unfinished("Zerg Lair"):
            h.try_build_at_most("Zerg Hydralisk Den", 100, 1, gas_cost=50)

        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25)

        # Lurker 변이 (Hydralisk → Lurker)
        if h.has("Zerg Hydralisk Den"):
            h.try_morph("Zerg Hydralisk", "Zerg Lurker", 50, gas_cost=100)

        # Lurker ×4 완성 → C++ Main
        if h.count_of("Zerg Lurker") >= 4:
            ctx.log("ZvT 9 Pool Lurker 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp()
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
