"""PvP 3 Gate Robo (C++ opening_PvP_3GateRobo 기반)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 10 → Gateway ×1
  supply 12 → Assimilator ×1
  supply 14 → Cybernetics Core ×1, Zealot ×1
  supply 16 → Pylon ×2
  supply 18 → Dragoon ×1  (사이버네틱스 필요)
  supply 21 → Pylon ×3
  supply 22 → Dragoon ×2
  supply 26 → Robotics Facility ×1  (Dragoon 2 이상)
  supply 29 → Gateway ×3, Pylon ×4, Dragoon ×3
  supply 33 → Observatory ×1  (Dragoon 3 이상)
  Observer 완성 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvP_3gaterobo"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvP 3게이트 로보 오프닝 시작 (supply milestone)")
    h.start_trace("PvP_3GateRobo", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            dragoons=h.count_including_unfinished("Protoss Dragoon"),
            robo=h.count_including_unfinished("Protoss Robotics Facility"),
            obs=h.count_of("Protoss Observer", completed_only=True),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "3Gate Robo 위기 감지 → C++ Main으로 즉시 전환")
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
            h.try_train_at_most("Protoss Gateway", "Protoss Dragoon", 125, 1, gas_cost=50)

        if s >= 21:
            h.try_build_at_most("Protoss Pylon", 100, 3)

        if s >= 22 and h.has("Protoss Cybernetics Core"):
            h.try_train_at_most("Protoss Gateway", "Protoss Dragoon", 125, 2, gas_cost=50)

        if s >= 26 and h.count_of("Protoss Dragoon") >= 2:
            h.try_build_at_most("Protoss Robotics Facility", 200, 1, gas_cost=200)

        if s >= 29 and h.has_including_unfinished("Protoss Robotics Facility"):
            h.try_build_at_most("Protoss Gateway", 150, 3)
            h.try_build_at_most("Protoss Pylon", 100, 4)
            if h.has("Protoss Cybernetics Core"):
                h.try_train_at_most("Protoss Gateway", "Protoss Dragoon", 125, 3, gas_cost=50)

        if s >= 33 and h.count_of("Protoss Dragoon") >= 3:
            h.try_build_at_most("Protoss Observatory", 50, 1, gas_cost=100)

        # Observer 생산
        if h.has("Protoss Robotics Facility"):
            h.try_train_at_most("Protoss Robotics Facility", "Protoss Observer", 25, 1, gas_cost=75)

        # Observer 완성 → C++ Main
        if h.count_of("Protoss Observer", completed_only=True) >= 1:
            ctx.log("3게이트 로보 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
