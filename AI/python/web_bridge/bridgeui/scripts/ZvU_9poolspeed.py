"""ZvU 9 Pool Speed (supply milestone 기반)

빌드 오더:
  supply 4~8 → Drone 지속 훈련
  supply 9  → Spawning Pool ×1
  Pool 완성 → Zergling 8마리 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "ZvU_9poolspeed"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU 9 Pool Speed 시작 (supply milestone)")
    h.start_trace("ZvU_9PoolSpeed", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pool=h.count_including_unfinished("Zerg Spawning Pool"),
            lings=h.count_including_unfinished("Zerg Zergling"),
            workers=len(h.workers()),
        )

        if h.enemy_offense_larger_than_defense(cushion=2) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "9PoolSpeed 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        # 9마리까지만 drone 훈련
        h.manage_workers(desired=9)
        h.manage_supply(threshold=2)

        # supply 9 → Spawning Pool
        if s >= 9:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)

        # Pool 완성 후 Zergling 군단 훈련
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)

        if h.count_of("Zerg Zergling") >= 8:
            h.attack_with(["Zerg Zergling"], min_army=8)
            ctx.log("ZvU 9 Pool Speed 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
