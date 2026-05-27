"""TvU Natural Expand (supply milestone 기반)

빌드 오더:
  supply 8  → Supply Depot ×1
  supply 9  → Barracks ×1
  supply 14 → 앞마당 CC 확장
  supply 15 → Refinery ×1, Barracks ×2
  supply 17 → Factory ×1
  Marine 다수 + Tank → 코어 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvU_1FactFE"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Natural Expand 시작 (supply milestone)")
    h.start_trace("TvU_NaturalExpand", interval=1.5)
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            cc=h.count_including_unfinished("Terran Command Center"),
            factory=h.count_including_unfinished("Terran Factory"),
            marines=h.count_including_unfinished("Terran Marine"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Natural Expand 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=22)
        h.manage_supply(threshold=2)

        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)

        if s >= 14 and not natural_sent and h.minerals() >= 400:
            if h.expand(cost=400):
                natural_sent = True

        if s >= 15:
            h.try_build_at_most("Terran Refinery", 100, 1)
            h.try_build_at_most("Terran Barracks", 150, 2)

        if s >= 17 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        # 유닛 생산
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Factory"):
            h.try_build_at_most("Terran Machine Shop", 50, 1, gas_cost=25)
            h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)

        if h.count_of("Terran Marine") >= 6:
            h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode"], min_army=6)

        if (h.count_including_unfinished("Terran Command Center") >= 2 and
                h.count_including_unfinished("Terran Factory") >= 1 and
                h.count_of("Terran Marine") >= 6):
            ctx.log("TvU Natural Expand 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
