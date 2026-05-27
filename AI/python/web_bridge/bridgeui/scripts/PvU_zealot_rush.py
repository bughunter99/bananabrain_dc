"""PvU 질럿 러시 (99 Gate 기반)

빌드 오더:
  supply 8  → Pylon ×1
  supply 9  → Gateway ×1 (pylon 있을 때)
  supply 10 → Zealot 훈련 시작
  supply 14 → Pylon ×2
  supply 16 → Gateway ×2
  supply 18 → Pylon ×3
  supply 22 → Gateway ×3
  Zealot 8마리 이상 → 코어로 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_zealot_rush"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("질럿 러시 시작 (supply milestone)")
    h.start_trace("PvU_ZealotRush", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            zealots=h.count_including_unfinished("Protoss Zealot"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Zealot Rush 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        # 일꾼 최소화, 군사력 집중
        h.manage_workers(desired=10)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)

        if s >= 9 and h.has_including_unfinished("Protoss Pylon"):
            h.try_build_at_most("Protoss Gateway", 150, 1)

        # Zealot 다수 생산 (가스 없이)
        if s >= 10 and h.has("Protoss Gateway"):
            h.try_train("Protoss Gateway", "Protoss Zealot", 100)

        if s >= 14:
            h.try_build_at_most("Protoss Pylon", 100, 2)

        if s >= 16:
            h.try_build_at_most("Protoss Gateway", 150, 2)

        if s >= 18:
            h.try_build_at_most("Protoss Pylon", 100, 3)

        if s >= 22:
            h.try_build_at_most("Protoss Gateway", 150, 3)

        # Zealot 8 이상 → 코어로 공격
        if h.count_of("Protoss Zealot") >= 8:
            h.attack_with(["Protoss Zealot"], min_army=8)
            ctx.log("PvU Zealot Rush 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
