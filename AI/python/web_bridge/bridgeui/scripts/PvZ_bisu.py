"""PvZ Bisu (간소화 비슈 오프닝 뒠 — forge 빠른 확장 기반)

핵심 흐름:
  supply 8  → Pylon ×1, scout
  supply 9  → Forge ×1
  supply 11 → Photon Cannon ×2 (수비)
  supply 13 → Nexus 앞마당 확장
  supply 14 → Gateway ×1, Assimilator ×1
  supply 15 → Pylon ×2
  supply 16 → Cybernetics Core ×1
  supply 28 → Assimilator ×2 → Stargate ×1
  Corsair ×2 → Citadel → Templar Archives → DT ×2
  DT ×2 + Gateway ×4 → C++ Main 위임
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvZ_bisu"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvZ Bisu 오프닝 시작 (supply milestone)")
    h.start_trace("PvZ_Bisu", interval=1.5)
    scout_sent = False
    natural_sent = False

    while not ctx._stopped:
        s = h.supply_count()
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            cannons=h.count_including_unfinished("Protoss Photon Cannon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            corsair=h.count_including_unfinished("Protoss Corsair"),
            dt=h.count_including_unfinished("Protoss Dark Templar"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Bisu 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)
        h.manage_supply(threshold=4)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        if s >= 9:
            h.try_build_at_most("Protoss Forge", 150, 1)

        if s >= 11 and h.has_including_unfinished("Protoss Forge"):
            h.try_build_at_most("Protoss Photon Cannon", 150, 2)

        # 앞마당 Nexus 확장 (Cannon 1개 + Forge 완성 후)
        if (h.has("Protoss Forge") and
                h.count_of("Protoss Photon Cannon") >= 1 and
                not natural_sent and h.minerals() >= 400):
            if h.expand(cost=400):
                natural_sent = True

        if s >= 14:
            h.try_build_at_most("Protoss Gateway", 150, 1)
            h.try_build_at_most("Protoss Assimilator", 100, 1)

        if s >= 15:
            h.try_build_at_most("Protoss Pylon", 100, 2)

        if s >= 16 and h.has_including_unfinished("Protoss Assimilator"):
            h.try_build_at_most("Protoss Cybernetics Core", 200, 1)

        if s >= 28:
            h.try_build_at_most("Protoss Assimilator", 100, 2)

        if h.count_including_unfinished("Protoss Assimilator") >= 2:
            h.try_build_at_most("Protoss Stargate", 150, 1, gas_cost=150)

        if h.has_including_unfinished("Protoss Stargate"):
            h.try_train_at_most("Protoss Stargate", "Protoss Corsair", 150, 6, gas_cost=100)

        # Corsair 2 → Gateway 2
        if h.count_of("Protoss Corsair") >= 2:
            h.try_build_at_most("Protoss Gateway", 150, 2)

        # DT 루트
        if h.has("Protoss Cybernetics Core"):
            h.try_build_at_most("Protoss Citadel of Adun", 150, 1, gas_cost=100)
        if h.has("Protoss Citadel of Adun"):
            h.try_build_at_most("Protoss Templar Archives", 150, 1, gas_cost=200)
        if h.has("Protoss Templar Archives"):
            h.try_train_at_most("Protoss Gateway", "Protoss Dark Templar", 125, 2, gas_cost=100)

        # DT 2 + Gateway 4 → C++ Main
        if (h.count_of("Protoss Dark Templar", completed_only=True) >= 2 and
                h.count_including_unfinished("Protoss Gateway") >= 4):
            ctx.log("Bisu 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        ctx.gather_idle_workers()
        ctx.wait(0.25)
