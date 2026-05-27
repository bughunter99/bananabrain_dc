"""PvU One Punch — Gate x4 + High Templar + Zealot (supply milestone)

빌드 오더:
  supply 8  → Pylon ×1
  supply 10 → Gateway ×1
  supply 12 → Assimilator ×1
  supply 14 → Cybernetics Core ×1, Zealot ×1
  supply 16 → Pylon ×2, Gateway ×2
  supply 22 → Citadel of Adun
  supply 24 → Pylon ×3, Gateway ×4
  Citadel 완성 → Templar Archives
  High Templar 4마리 + Zealot 8마리 → 공격
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_one_punch"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU One Punch 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_OnePunch", interval=1.5)

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            citadel=h.count_including_unfinished("Protoss Citadel of Adun"),
            archives=h.count_including_unfinished("Protoss Templar Archives"),
            ht=h.count_including_unfinished("Protoss High Templar"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "One Punch 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=18)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)

        if s >= 10 and h.has_including_unfinished("Protoss Pylon"):
            h.try_build_at_most("Protoss Gateway", 150, 1)

        if s >= 12:
            h.try_build_at_most("Protoss Assimilator", 100, 1)

        if s >= 14:
            h.try_build_at_most("Protoss Cybernetics Core", 200, 1)
            h.try_train_at_most("Protoss Gateway", "Protoss Zealot", 100, 2)

        if s >= 16:
            h.try_build_at_most("Protoss Pylon", 100, 2)
            h.try_build_at_most("Protoss Gateway", 150, 2)

        if s >= 22 and h.has("Protoss Cybernetics Core"):
            h.try_build_at_most("Protoss Citadel of Adun", 150, 1, gas_cost=100)

        if s >= 24:
            h.try_build_at_most("Protoss Pylon", 100, 3)
            h.try_build_at_most("Protoss Gateway", 150, 4)

        if h.has("Protoss Citadel of Adun"):
            h.try_build_at_most("Protoss Templar Archives", 150, 1, gas_cost=200)

        # High Templar
        if h.has("Protoss Templar Archives"):
            h.try_train("Protoss Gateway", "Protoss High Templar", 50, gas_cost=150)
        else:
            h.try_train("Protoss Gateway", "Protoss Zealot", 100)

        # 대군 형성 후 코어 공격
        if h.count_of("Protoss High Templar") >= 4 and h.count_of("Protoss Zealot") >= 8:
            h.attack_with(["Protoss Zealot", "Protoss High Templar"], min_army=10)
            ctx.log("PvU One Punch 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
