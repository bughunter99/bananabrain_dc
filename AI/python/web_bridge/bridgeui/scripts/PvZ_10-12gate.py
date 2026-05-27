"""PvX 10/12 Gate (C++ opening_PvX_1012Gate 기반)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 10 → Gateway ×1  (pylon 있을 때)
  supply 12 → Gateway ×2
  supply 13 → Zealot ×1
  supply 15 → Pylon ×2
  supply 17 → Zealot ×3
  supply 21 → Pylon ×3
  완료 조건: Gateway×2 + Pylon×3 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvZ_1012Gate"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("10/12 Gate 오프닝 시작 (supply milestone)")
    h.start_trace("PvX_1012Gate", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()  # C++ opening_supply_count()와 동일
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            zealots=h.count_including_unfinished("Protoss Zealot"),
        )

        # C++ opening_PvX_1012Gate의 초기 방어/실패 분기 근사치
        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "10/12 Gate 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        # 일꾼은 최대 14마리까지 지속 생산
        h.manage_workers(desired=14)

        # supply 8: pylon 1 건설 + 스카웃
        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        # supply 10: gateway 1 (pylon 완성/건설 중 필요)
        if s >= 10 and h.has_including_unfinished("Protoss Pylon"):
            h.try_build_at_most("Protoss Gateway", 150, 1)

        # supply 12: gateway 2
        if s >= 12:
            h.try_build_at_most("Protoss Gateway", 150, 2)

        # supply 13: zealot 1
        if s >= 13:
            h.try_train_at_most("Protoss Gateway", "Protoss Zealot", 100, 1)

        # supply 15: pylon 2
        if s >= 15:
            h.try_build_at_most("Protoss Pylon", 100, 2)

        # supply 17: zealot 3
        if s >= 17:
            h.try_train_at_most("Protoss Gateway", "Protoss Zealot", 100, 3)

        # supply 21: pylon 3
        if s >= 21:
            h.try_build_at_most("Protoss Pylon", 100, 3)

        # 오프닝 완료 조건: gateway 2 + pylon 3 → C++ Main
        if (h.count_including_unfinished("Protoss Gateway") >= 2 and
                h.count_including_unfinished("Protoss Pylon") >= 3):
            ctx.log("10/12 Gate 오프닝 완료 → C++ 자율 플레이로 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
