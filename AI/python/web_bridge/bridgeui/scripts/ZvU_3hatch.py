"""ZvU 3 Hatch (supply milestone 기반)

빌드 오더:
  supply 4~9  → Drone 훈련
  supply 9   → 앞마당 확장 (Hatch ×2)
  supply 12  → Spawning Pool, Extractor
  supply 14  → 3번 Hatch / 3rd base
  Pool 완성 → Lair → Muta or Ling 댓한 참게
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvU_3hatch"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU 3 Hatch 시작 (supply milestone)")
    h.start_trace("ZvU_3Hatch", interval=1.5)
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
            h.mark_once("fallback_main", "3Hatch 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=2)

        # supply 9: 앞마당 확장 (Hatch)
        if s >= 9 and not natural_sent and h.minerals() >= 300:
            if h.expand(cost=300):
                natural_sent = True

        # supply 12: Pool + Extractor
        if s >= 12:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)
            if h.has_including_unfinished("Zerg Spawning Pool"):
                h.try_build_at_most("Zerg Extractor", 50, 1)

        # supply 14: 3번 Hatch (추가 확장)
        if s >= 14 and h.count_including_unfinished("Zerg Hatchery") < 3 and h.minerals() >= 300:
            h.expand(cost=300)

        # Pool 이후 Zergling 생산
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)

        # Extractor 오피 후 Lair
        if h.has("Zerg Spawning Pool") and h.has("Zerg Extractor"):
            h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)

        if h.has("Zerg Lair"):
            h.try_build_at_most("Zerg Spire", 200, 1, gas_cost=200)

        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)

        if h.count_of("Zerg Mutalisk") >= 6:
            h.attack_with(["Zerg Mutalisk", "Zerg Zergling"], min_army=6)
            ctx.log("ZvU 3 Hatch 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return
        elif h.count_of("Zerg Zergling") >= 12:
            h.attack_with(["Zerg Zergling"], min_army=12)
            ctx.log("ZvU 3 Hatch 오프닝 완료(링) → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
