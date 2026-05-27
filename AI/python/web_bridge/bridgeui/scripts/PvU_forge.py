"""PvU Forge (C++ opening_PvU_Forge 기반)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 9  → Forge ×1
  supply 11 → Photon Cannon ×2  (Forge 건설 중 이후)
  supply 13 → Photon Cannon ×3
  supply 14 → Gateway ×1
  supply 15 → Pylon ×2
  supply 16 → Assimilator ×1 → Cybernetics Core ×1
  Zealot ×1 + Cybernetics Core 건설 중 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_forge"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Forge 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_Forge", interval=1.5)
    scout_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            forge=h.count_including_unfinished("Protoss Forge"),
            cannons=h.count_including_unfinished("Protoss Photon Cannon"),
            gate=h.count_including_unfinished("Protoss Gateway"),
            cyber=h.count_including_unfinished("Protoss Cybernetics Core"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Forge 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=14)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 9:
            h.try_build_at_most("Protoss Forge", 150, 1)

        if s >= 11 and h.has_including_unfinished("Protoss Forge"):
            h.try_build_at_most("Protoss Photon Cannon", 150, 2)

        if s >= 13:
            h.try_build_at_most("Protoss Photon Cannon", 150, 3)

        if s >= 14:
            h.try_build_at_most("Protoss Gateway", 150, 1)

        if s >= 15:
            h.try_build_at_most("Protoss Pylon", 100, 2)

        if s >= 16:
            h.try_build_at_most("Protoss Assimilator", 100, 1)
            if h.has_including_unfinished("Protoss Assimilator"):
                h.try_build_at_most("Protoss Cybernetics Core", 200, 1)

        # Gateway + Cybernetics Core 착수 후 Zealot 생산
        if h.has("Protoss Gateway") and h.has_including_unfinished("Protoss Cybernetics Core"):
            h.try_train_at_most("Protoss Gateway", "Protoss Zealot", 100, 1)

        # 완료 조건: Zealot 건재 + Cybernetics Core 착수 → C++ Main
        if (h.count_of("Protoss Zealot") >= 1 and
                h.has_including_unfinished("Protoss Cybernetics Core")):
            ctx.log("Forge 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
