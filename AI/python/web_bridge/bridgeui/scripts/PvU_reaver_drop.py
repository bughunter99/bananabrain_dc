"""PvU Reaver Drop (supply milestone 기반)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 10 → Gateway ×1
  supply 12 → Assimilator ×1
  supply 14 → Cybernetics Core ×1, Zealot ×1
  supply 16 → Pylon ×2
  supply 18 → Robotics Facility  (Cyber 사용 가능 후)
  supply 22 → Robotics Support Bay + Shuttle
  Reaver 생산 → 드락 주뒅
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_reaverDrop"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Reaver Drop 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_ReaverDrop", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gate=h.count_including_unfinished("Protoss Gateway"),
            robo=h.count_including_unfinished("Protoss Robotics Facility"),
            shuttle=h.count_including_unfinished("Protoss Shuttle"),
            reaver=h.count_including_unfinished("Protoss Reaver"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Reaver Drop 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=16)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 10:
            h.try_build_at_most("Protoss Gateway", 150, 1)

        if s >= 12:
            h.try_build_at_most("Protoss Assimilator", 100, 1)

        if s >= 14:
            h.try_build_at_most("Protoss Cybernetics Core", 200, 1)
            h.try_train_at_most("Protoss Gateway", "Protoss Zealot", 100, 1)

        if s >= 16:
            h.try_build_at_most("Protoss Pylon", 100, 2)

        if s >= 18 and h.has("Protoss Cybernetics Core"):
            h.try_build_at_most("Protoss Robotics Facility", 200, 1, gas_cost=200)

        if s >= 22 and h.has("Protoss Robotics Facility"):
            h.try_build_at_most("Protoss Robotics Support Bay", 150, 1, gas_cost=100)
            h.try_train_at_most("Protoss Robotics Facility", "Protoss Shuttle", 200, 1, gas_cost=200)

        if h.has("Protoss Robotics Support Bay"):
            h.try_train_at_most("Protoss Robotics Facility", "Protoss Reaver", 200, 2, gas_cost=100)

        # Zealot 지속 생산
        if h.has("Protoss Gateway"):
            h.try_train("Protoss Gateway", "Protoss Zealot", 100)

        # Reaver + Shuttle 드락 공격
        if h.count_of("Protoss Reaver") >= 1 and h.count_of("Protoss Shuttle") >= 1:
            h.attack_with(["Protoss Reaver", "Protoss Shuttle", "Protoss Zealot"], min_army=2)
            ctx.log("PvU Reaver Drop 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
