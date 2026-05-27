"""PvU Dark Templar (supply milestone 기반)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 10 → Gateway ×1
  supply 12 → Assimilator ×1
  supply 14 → Cybernetics Core ×1, Zealot ×1
  supply 16 → Pylon ×2
  Cybernetics Core 완성 → Citadel of Adun
  Citadel 완성 → Templar Archives
  Templar Archives 완성 → DT 생산
  DT 2마리 → 코어로 진출
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_dt"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Dark Templar 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_DarkTemplar", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gate=h.count_including_unfinished("Protoss Gateway"),
            cyber=h.count_including_unfinished("Protoss Cybernetics Core"),
            citadel=h.count_including_unfinished("Protoss Citadel of Adun"),
            dt=h.count_including_unfinished("Protoss Dark Templar"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Dark Templar 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=14)

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

        if h.has("Protoss Cybernetics Core"):
            h.try_build_at_most("Protoss Citadel of Adun", 150, 1, gas_cost=100)

        if h.has("Protoss Citadel of Adun"):
            h.try_build_at_most("Protoss Templar Archives", 150, 1, gas_cost=200)

        if h.has("Protoss Templar Archives"):
            h.try_train("Protoss Gateway", "Protoss Dark Templar", 125, gas_cost=100)

        # DT 2마리 이상 → 코어로 공격
        if h.count_of("Protoss Dark Templar") >= 2:
            h.attack_with(["Protoss Dark Templar", "Protoss Zealot"], min_army=2)
            ctx.log("PvU Dark Templar 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
