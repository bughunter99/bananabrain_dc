"""TvP Siege Expand (C++ opening_TvP_siegeexpand 기반)

빌드 오더 (opening_TvP_siegeexpand_start):
  supply 9  → Supply Depot ×1, 스카웃
  supply 12 → Barracks ×1, Refinery ×1
  supply 15 → Supply Depot ×2
  supply 16 → Factory ×1
  Factory 완성 → Machine Shop ×1, Tank 생산
  supply 21 → 앞마당 CC 확장
  supply 24 → Supply Depot ×3
opening_TvP_siegeexpand:
  supply 28 → Engineering Bay ×1
  Engineering Bay 완성 → C++ MainMech 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvP_SiegeExpand"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvP Siege Expand 시작 (supply milestone)")
    h.start_trace("TvP_SiegeExpand", interval=1.5)
    scout_sent = False
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            factory=h.count_including_unfinished("Terran Factory"),
            tanks=h.count_including_unfinished("Terran Siege Tank Tank Mode"),
            ebay=h.count_including_unfinished("Terran Engineering Bay"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Siege Expand 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Terran Supply Depot", 100, 1)
            if h.has_including_unfinished("Terran Supply Depot") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 12:
            h.try_build_at_most("Terran Barracks", 150, 1)
            if h.has_including_unfinished("Terran Barracks"):
                h.try_build_at_most("Terran Refinery", 100, 1)

        if s >= 15:
            h.try_build_at_most("Terran Supply Depot", 100, 2)

        if s >= 16:
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)

        # Factory 완성 → Machine Shop, Tank 생산
        if h.has("Terran Factory"):
            h.try_build_at_most("Terran Machine Shop", 50, 1, gas_cost=25)
            h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)

        if s >= 21 and not natural_sent and h.minerals() >= 400:
            if h.expand(cost=400):
                natural_sent = True

        if s >= 24:
            h.try_build_at_most("Terran Supply Depot", 100, 3)

        if s >= 28:
            h.try_build_at_most("Terran Engineering Bay", 125, 1)

        # Engineering Bay 완성 → C++ MainMech
        if h.has("Terran Engineering Bay"):
            ctx.log("TvP Siege Expand 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
