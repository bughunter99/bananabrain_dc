"""ZvT 3 Hatch Muta (supply milestone 기반)

빌드 오더:
  supply 9  → 앞마당 Hatch 확장
  supply 12 → Pool, Extractor
  supply 14 → 3번 Hatch
  Pool + Extractor 오피 → Lair → Spire → Muta
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvT_3hatchMuta"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvT 3 Hatch Muta 시작 (supply milestone)")
    h.start_trace("ZvT_3HatchMuta", interval=1.5)
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            hatch=h.count_including_unfinished("Zerg Hatchery"),
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            lair=h.count_including_unfinished("Zerg Lair"),
            spire=h.count_including_unfinished("Zerg Spire"),
            muta=h.count_including_unfinished("Zerg Mutalisk"),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "3Hatch Muta 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=18)
        h.manage_supply(threshold=2)

        # supply 9: 앞마당 Hatch
        if s >= 9 and not natural_sent and h.minerals() >= 300:
            if h.expand(cost=300):
                natural_sent = True

        # supply 12: Pool + Extractor
        if s >= 12:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)
            if h.has_including_unfinished("Zerg Spawning Pool"):
                h.try_build_at_most("Zerg Extractor", 50, 1)

        # supply 14: 3번째 Hatch
        if s >= 14 and h.count_including_unfinished("Zerg Hatchery") < 3 and h.minerals() >= 300:
            h.expand(cost=300)

        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50, max_count=4)  # 수비용

        if h.has("Zerg Spawning Pool") and h.has("Zerg Extractor"):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        if h.has("Zerg Lair"):
            h.try_build_at_most("Zerg Spire", 200, 1, gas_cost=200)

        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)

        # Muta 6마리 이상 → C++ Main 위임
        if h.count_of("Zerg Mutalisk") >= 6:
            ctx.log("3 Hatch Muta 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
