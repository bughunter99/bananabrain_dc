"""TvZ 1 Rax FE (C++ opening_TvZ_1raxfe 기반)

빌드 오더 (C++ 원본과 동일한 바이오 오프닝):
  supply 9  → Supply Depot ×1
  supply 11 → Barracks ×1, 스카웃
  Barracks 완성 → Marine 생산 (수비)
  supply 15 → 앞마당 CC 확장
  CC×2 계획/완성 → C++ MainBio 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "TvZ_1RaxFE"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvZ 1Rax FE 시작 (바이오 오프닝)")
    h.start_trace("TvZ_1RaxFE", interval=1.5)
    scout_sent = False
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            depots=h.count_including_unfinished("Terran Supply Depot"),
            rax=h.count_including_unfinished("Terran Barracks"),
            marines=h.count_including_unfinished("Terran Marine"),
            cc=h.count_including_unfinished("Terran Command Center"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "1Rax FE 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=18)
        h.manage_supply(threshold=2)

        if s >= 9:
            h.try_build_at_most("Terran Supply Depot", 100, 1)

        if s >= 11:
            h.try_build_at_most("Terran Barracks", 150, 1)
            if h.has_including_unfinished("Terran Barracks") and not scout_sent:
                h.send_scout()
                scout_sent = True

        # Barracks 완성 → Marine 생산
        if h.has("Terran Barracks"):
            h.try_train("Terran Barracks", "Terran Marine", 50)

        # supply 15: 앞마당 CC
        if s >= 15 and not natural_sent and h.minerals() >= 400:
            if h.expand(cost=400):
                natural_sent = True

        # CC×2 계획됨 → C++ MainBio
        if h.count_including_unfinished("Terran Command Center") >= 2:
            ctx.log("TvZ 1Rax FE 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
