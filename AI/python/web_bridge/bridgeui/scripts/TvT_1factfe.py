"""TvT 1 Factory FE (C++ opening_TvT_1factfe 기반)

빌드 오더:
  supply 9  → Supply Depot ×1
  supply 12 → Barracks ×1, Refinery ×1
  Marine < 2: Marine 생산
  supply 16 → Supply Depot ×2, Factory ×1
  supply 20 → 앞마당 CC 확장, Vulture 생산
  supply 24 → Machine Shop ×1
  supply 26 → Factory ×2
  Factory×2 계획됨 → C++ MainMech 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvT_1FactFE"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvT 1 Factory FE 시작 (supply milestone)")
    h.start_trace("TvT_1FactFE", interval=1.5)
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            factory=h.count_including_unfinished("Terran Factory"),
            vulture=h.count_including_unfinished("Terran Vulture"),
            cc=h.count_including_unfinished("Terran Command Center"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "1Fact FE 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=22)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 12:
            h.try_build_at_most("Terran Barracks", 150, 1)
            if h.has_including_unfinished("Terran Barracks"):
                h.try_build_at_most("Terran Refinery", 100, 1)

        # Marine 2기까지 생산
        if h.has("Terran Barracks") and h.count_of("Terran Marine") < 2:
            h.try_train("Terran Barracks", "Terran Marine", 50)

        if s >= 16:
            h.try_build_at_most("Terran Supply Depot", 100, 2)
            if h.count_including_unfinished("Terran Supply Depot") >= 2:
                h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        if s >= 20 and not natural_sent and h.minerals() >= 400:
            if h.expand(cost=400):
                natural_sent = True

        # 앞마당 완성 후 Vulture 생산
        if h.count_including_unfinished("Terran Command Center") >= 2:
            h.try_train("Terran Factory", "Terran Vulture", 75, gas_cost=0)

        if s >= 24 and h.has("Terran Factory"):
            h.try_build_at_most("Terran Machine Shop", 50, 1, gas_cost=25)

        if s >= 26:
            h.try_build_at_most("Terran Factory", 200, 2, gas_cost=100)

        # Factory×2 계획됨 → C++ MainMech
        if h.count_including_unfinished("Terran Factory") >= 2:
            ctx.log("TvT 1 Factory FE 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
