"""PvU 앞마당 확장 뒠 (supply milestone)

빌드 오더:
  supply 8  → Pylon ×1, scout
  supply 12 → 앞마당 Nexus (착공 확인될 때까지 반복 시도)
  Nexus 착공 후 → Gateway ×1, Assimilator ×1
  supply 15 → Cybernetics Core ×1
  supply 18 → Pylon ×2, Gateway ×2
  Cybernetics Core 완성 → 자율 플레이 전환
"""
import sys, os, time; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

CPP_OPENING = "PvU_naturalExpand"


def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Natural Expand 오프닝 시작 (supply milestone)")
    h.start_trace("PvU_NaturalExpand", interval=1.5)
    scout_sent = False
    expand_sent_at = 0.0
    force_gather_at = 0.0

    while not ctx._stopped:
        s = h.supply_count()
        nexus_count = h.count_including_unfinished("Protoss Nexus")
        h.trace(
            "Opening",
            pylons=h.count_including_unfinished("Protoss Pylon"),
            gates=h.count_including_unfinished("Protoss Gateway"),
            cyber=h.count_including_unfinished("Protoss Cybernetics Core"),
            nexus=nexus_count,
        )

        # 앞마당 넥서스가 아직 시작되지 않은 초반에는 위기 판정 오탐이 잦아
        # 조기 이탈(autoplay 전환)을 막는다.
        if nexus_count >= 2 and (h.enemy_offense_larger_than_defense(cushion=1) or h.opening_lost_too_many_workers(margin=3)):
            h.mark_once("fallback_main", "Natural Expand 위기 감지 → C++ Main으로 즉시 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        # 시작 직후 일부 환경에서 idle 판정 누락으로 일꾼 채집이 멈추는 경우가 있어
        # 오프닝 초반에는 주기적으로 채집 명령을 강제로 펄스한다.
        now = time.time()
        if now >= force_gather_at and nexus_count < 2:
            ctx.control("gather_minerals")
            force_gather_at = now + 1.5

        h.manage_workers(desired=22)
        h.manage_supply(threshold=4)

        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True

        # 앞마당 넥서스: natural_sent 플래그 대신 실제 넥서스 수로 판단해 착공 확인될 때까지 재시도
        if s >= 12 and nexus_count < 2:
            if h.minerals() >= 400:
                if h.expand(cost=400):
                    expand_sent_at = time.time()
                else:
                    h.mark_once("expand_retry", "앞마당 착공 재시도 중...")
            else:
                h.mark_once("expand_minerals", "앞마당 대기: 미네랄 부족")

        # 파일런 파워 범위 이슈: 게이트/사이버는 파일런 근처 우선 배치
        # 앞마당 넥서스 착공 확인 후에만 게이트/어시 건설 (그 전엔 일꾼 묶이면 안 됨)
        pylon_tile = None
        pylons_done = h.buildings_of("Protoss Pylon", completed_only=True)
        if pylons_done:
            tx = pylons_done[0].get("tile_x")
            ty = pylons_done[0].get("tile_y")
            if tx is not None and ty is not None:
                pylon_tile = (tx, ty)

        if s >= 13 and nexus_count >= 2:
            if pylon_tile and h.count_including_unfinished("Protoss Gateway") < 1:
                if not h.try_build_near("Protoss Gateway", 150, near_tile=pylon_tile, max_count=1, cooldown=6.0):
                    h.try_build_at_most("Protoss Gateway", 150, 1)
            else:
                h.try_build_at_most("Protoss Gateway", 150, 1)
            h.try_build_at_most("Protoss Assimilator", 100, 1)

        if s >= 15 and h.has_including_unfinished("Protoss Assimilator"):
            if pylon_tile and h.count_including_unfinished("Protoss Cybernetics Core") < 1:
                if not h.try_build_near("Protoss Cybernetics Core", 200, near_tile=pylon_tile, max_count=1, cooldown=6.0):
                    h.try_build_at_most("Protoss Cybernetics Core", 200, 1)
            else:
                h.try_build_at_most("Protoss Cybernetics Core", 200, 1)

        if s >= 18:
            h.try_build_at_most("Protoss Pylon", 100, 2)
            if pylon_tile and h.count_including_unfinished("Protoss Gateway") < 2:
                if not h.try_build_near("Protoss Gateway", 150, near_tile=pylon_tile, max_count=2, cooldown=6.0):
                    h.try_build_at_most("Protoss Gateway", 150, 2)
            else:
                h.try_build_at_most("Protoss Gateway", 150, 2)

        h.try_train("Protoss Gateway", "Protoss Zealot", 100)

        # Cybernetics Core 완성 → C++ Main
        if h.has("Protoss Cybernetics Core"):
            ctx.log("Natural Expand 오프닝 완료 → C++ 자율 플레이 전환")
            h.delegate_to_cpp(CPP_OPENING)
            return

        # 확장 착공 커맨드 직후에는 일꾼 강제 채광 복귀를 잠시 막아 착공을 보장한다.
        if nexus_count >= 2 or (time.time() - expand_sent_at > 15.0):
            ctx.gather_idle_workers()
        ctx.wait(0.25)
