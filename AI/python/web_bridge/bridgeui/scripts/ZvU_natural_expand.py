"""ZvU Natural Expand (supply milestone 기반)

빌드 오더:
  supply 4~9  → Drone 훈련
  supply 9   → 앞마당 Hatch 확장
  supply 12  → Spawning Pool
  Pool 완성 → Zergling 생산
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvU_natural_expand"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Natural Expand 시작 (supply milestone)")
    h.start_trace("ZvU_NaturalExpand", interval=1.5)
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            hatch=h.count_including_unfinished("Zerg Hatchery"),
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            lings=h.count_including_unfinished("Zerg Zergling"),
            workers=len(h.workers()),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Natural Expand 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=18)
        h.manage_supply(threshold=2)

        # supply 9: 앞마당 확장
        if s >= 9 and not natural_sent and h.minerals() >= 300:
            if h.expand(cost=300):
                natural_sent = True

        # supply 12: Spawning Pool
        if s >= 12:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)

        if h.count_of("Zerg Zergling") >= 12:
            h.attack_with(["Zerg Zergling"], min_army=12)
            ctx.log("ZvU Natural Expand 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
