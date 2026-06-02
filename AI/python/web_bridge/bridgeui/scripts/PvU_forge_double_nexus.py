"""PvU Forge Double Nexus: Natural Pylon -> Forge -> Nexus -> Cannon -> Gate -> Zealots"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import time
from _helpers import StrategyHelper

CPP_OPENING = "PvU_forge"

def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Forge Double Nexus 시작")
    h.start_trace("PvU_ForgeDoubleNexus", interval=1.5)
    natural_tile = None
    natural_retry_at = 0.0
    natural_lookup_fails = 0
    natural_place_fails = 0
    while not ctx._stopped:
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            forge=h.count_including_unfinished("Protoss Forge"),
            cannons=h.count_including_unfinished("Protoss Photon Cannon"),
            nexus=h.count_including_unfinished("Protoss Nexus"),
            gates=h.count_including_unfinished("Protoss Gateway"),
        )

        if h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3):
            h.mark_once("fallback_main", "Forge Double Nexus 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        h.manage_workers(desired=20)

        pylon_count = h.count_including_unfinished("Protoss Pylon")
        pylon_completed = h.count_of("Protoss Pylon", completed_only=True)
        if pylon_count == 0:
            if (not natural_tile) and (time.monotonic() >= natural_retry_at):
                natural_tile = ctx.get_natural_expansion_sync()
                if not natural_tile:
                    natural_lookup_fails += 1
                    natural_retry_at = time.monotonic() + 0.5
                    if natural_lookup_fails in (1, 3):
                        ctx.log("앞마당 위치 탐색 실패: 파일런 위치 재시도")
                else:
                    natural_place_fails = 0
            if natural_tile:
                if h.try_build_near("Protoss Pylon", 100, near_tile=natural_tile, max_count=1, cooldown=8.0):
                    h.mark_once("natural_pylon", "앞마당 첫 파일런 건설 시작")
                    natural_place_fails = 0
                elif h.minerals() >= 100:
                    natural_place_fails += 1
                    if natural_place_fails in (3, 6):
                        ctx.log("앞마당 파일런 배치 실패 누적: 재탐색 시도")
                    if natural_place_fails >= 6:
                        natural_tile = None
                        natural_retry_at = time.monotonic() + 0.5
            if pylon_count == 0 and h.minerals() >= 100 and (natural_lookup_fails >= 3 or natural_place_fails >= 6):
                if h.try_build("Protoss Pylon", 100, max_count=1, cooldown=8.0):
                    h.mark_once("fallback_pylon", "파일런 폴백: 본진 위치로 오프닝 진행")
            elif natural_lookup_fails >= 3:
                if h.try_build("Protoss Pylon", 100, max_count=1, cooldown=8.0):
                    h.mark_once("fallback_pylon", "앞마당 위치 탐색 실패 누적: 본진 파일런으로 진행")
        else:
            h.manage_supply(threshold=2)

        if pylon_completed > 0:
            h.try_build("Protoss Forge", 150, max_count=1)
        else:
            h.mark_once("wait_pylon_complete", "Forge 대기: 파일런 완성 전")

        if h.has_including_unfinished("Protoss Forge"):
            # Forge 착공되는 즉시 Nexus/Gateway 시작 (Forge 완성을 기다리지 않음)
            if h.count_including_unfinished("Protoss Nexus") < 2 and h.minerals() >= 400:
                h.expand(cost=400)
            h.try_build("Protoss Gateway", 150, max_count=3)
            # Cannon은 Forge 완성 후에만 건설 가능
            if h.has("Protoss Forge") and h.count_including_unfinished("Protoss Nexus") >= 2:
                h.try_build("Protoss Photon Cannon", 150, max_count=1)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=8)
        if (h.count_including_unfinished("Protoss Nexus") >= 2 and
                h.count_including_unfinished("Protoss Gateway") >= 2 and
                h.count_of("Protoss Zealot") >= 8):
            ctx.log("PvU Forge Double Nexus 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return
        ctx.gather_idle_workers()
        ctx.wait(0.25)
