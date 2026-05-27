"""ZvZ 9 Pool Spire (supply milestone 기반)

빌드 오더:
  supply 9  → Spawning Pool
  Pool + Extractor → Lair → Spire → Mutalisk
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvZ_9poolspire"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvZ 9 Pool Spire 시작 (supply milestone)")
    h.start_trace("ZvZ_9PoolSpire", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            gas=h.count_including_unfinished("Zerg Extractor"),
            lair=h.count_including_unfinished("Zerg Lair"),
            spire=h.count_including_unfinished("Zerg Spire"),
            muta=h.count_including_unfinished("Zerg Mutalisk"),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "9Pool Spire 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=12)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        if h.has("Zerg Spawning Pool"):
            h.try_build_at_most("Zerg Extractor", 50, 1)
            h.try_train_larva("Zerg Zergling", 50)  # 세이게를 좌와 대응

        if h.has("Zerg Spawning Pool") and h.has("Zerg Extractor"):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        if h.has("Zerg Lair"):
            h.try_build_at_most("Zerg Spire", 200, 1, gas_cost=200)

        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)

        if h.count_of("Zerg Mutalisk") >= 6:
            h.attack_with(["Zerg Mutalisk"], min_army=6)
            ctx.log("ZvZ 9 Pool Spire 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
