"""PvU 앞마당 확장 뒠 (supply milestone)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 12 → 앞마당 Nexus
  supply 13 → Gateway ×1, Assimilator ×1
  supply 15 → Cybernetics Core ×1
  supply 18 → Pylon ×2, Gateway ×2
  Cybernetics Core 이후 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_naturalExpand"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Natural Expand 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_NaturalExpand", interval=1.5)
    scout_sent = False
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            cyber=h.count_including_unfinished("Protoss Cybernetics Core"),
            nexus=h.count_including_unfinished("Protoss Nexus"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Natural Expand 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=22)
        h.manage_supply(threshold=4)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 12 and not natural_sent and h.minerals() >= 400:
            if h.expand(cost=400):
                natural_sent = True

        if s >= 13:
            h.try_build_at_most("Protoss Gateway", 150, 1)
            h.try_build_at_most("Protoss Assimilator", 100, 1)

        if s >= 15 and h.has_including_unfinished("Protoss Assimilator"):
            h.try_build_at_most("Protoss Cybernetics Core", 200, 1)

        if s >= 18:
            h.try_build_at_most("Protoss Pylon", 100, 2)
            h.try_build_at_most("Protoss Gateway", 150, 2)

        # Cybernetics Core 완성 → C++ Main
        if h.has("Protoss Cybernetics Core"):
            ctx.log("Natural Expand 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
