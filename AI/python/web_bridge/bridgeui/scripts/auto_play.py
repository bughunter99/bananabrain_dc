"""자율 플레이 (Auto Play)

종족을 자동 감지하여 게임 전체를 Python으로만 자율 운영합니다.
  Terran  : Marine + Medic + Vulture + Goliath  (Bio/Mech 혼합)
  Protoss : Zealot + Dragoon + Reaver
  Zerg    : Zergling + Mutalisk + Hydralisk

C++ 자율 루프에 절대 위임하지 않습니다.
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import time
from _helpers import StrategyHelper


# ─────────────────────────────────────────────────────────────────────────────
# 테란 자율 플레이
#   초반 : Marine 다수 생산 → 8명 이상 첫 공격
#   중반 : Academy(Medic) + Factory(Vulture) 추가
#   후반 : Armory(Goliath) + Barracks 증설
# ─────────────────────────────────────────────────────────────────────────────
def _play_terran(ctx, h):
    ARMY = [
        "Terran Marine", "Terran Medic",
        "Terran Vulture", "Terran Goliath",
    ]
    natural_sent = False
    last_scout_at = 0.0

    while not ctx._stopped:
        s = h.supply_count()
        m = h.minerals()

        # 일꾼 목표: 초반 14 → 중반 22 → 후반 28
        wt = 14 if s < 20 else 22 if s < 36 else 28
        h.manage_workers(desired=wt, maximum=32)
        h.manage_supply(threshold=2)

        # ── 초반 인프라 ──────────────────────────────────────
        if s >= 8:
            h.try_build_at_most("Terran Supply Depot", 100, 1)
        if s >= 9 and h.has_including_unfinished("Terran Supply Depot"):
            h.try_build_at_most("Terran Barracks", 150, 1)
        if s >= 11:
            h.try_build_at_most("Terran Refinery", 100, 1)

        # ── 앞마당 ───────────────────────────────────────────
        if s >= 16 and not natural_sent and m >= 400:
            if h.expand(cost=400):
                natural_sent = True

        # ── 군사 시설 ────────────────────────────────────────
        if s >= 13 and h.has("Terran Barracks"):
            h.try_build_at_most("Terran Factory", 200, 1, gas_cost=100)
        if s >= 15:
            h.try_build_at_most("Terran Barracks", 150, 2)
        if s >= 18:
            h.try_build_at_most("Terran Academy", 150, 1)
            h.try_build_at_most("Terran Refinery", 100, 2)
        if s >= 22:
            h.try_build_at_most("Terran Barracks", 150, 3)
            h.try_build_at_most("Terran Factory", 200, 2, gas_cost=100)
        if s >= 26:
            h.try_build_at_most("Terran Armory", 100, 1, gas_cost=50)
            h.try_build_at_most("Terran Barracks", 150, 4)
        if s >= 32:
            h.try_build_at_most("Terran Factory", 200, 3, gas_cost=100)
            h.try_build_at_most("Terran Barracks", 150, 5)

        # ── 유닛 생산 ────────────────────────────────────────
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25)
        h.try_train("Terran Factory", "Terran Vulture", 75)
        if h.has("Terran Armory"):
            h.try_train("Terran Factory", "Terran Goliath", 100, gas_cost=50)

        # ── 공격 ─────────────────────────────────────────────
        total = sum(h.count_of(u) for u in ARMY)
        if total >= 10:
            h.attack_with(ARMY, min_army=10)
        h.reinforce_attack(ARMY)

        if not ctx.get_state().get("enemy_units") and (time.monotonic() - last_scout_at) >= 20.0:
            h.send_scout()
            last_scout_at = time.monotonic()

        ctx.gather_idle_workers(interval=8.0)
        ctx.wait(0.25)


# ─────────────────────────────────────────────────────────────────────────────
# 프로토스 자율 플레이
#   초반 : Zealot → Cybernetics Core → Dragoon
#   중반 : 앞마당 + Gateway 3개
#   후반 : Robotics Facility → Reaver
# ─────────────────────────────────────────────────────────────────────────────
def _play_protoss(ctx, h):
    ARMY = [
        "Protoss Zealot", "Protoss Dragoon", "Protoss Reaver",
    ]
    scout_sent   = False
    natural_sent = False
    last_scout_at = 0.0

    while not ctx._stopped:
        s = h.supply_count()
        m = h.minerals()

        # 일꾼 목표
        wt = 14 if s < 20 else 22 if s < 36 else 28
        h.manage_workers(desired=wt, maximum=32)
        h.manage_supply(threshold=4)

        # ── 초반 ─────────────────────────────────────────────
        if s >= 8:
            h.try_build_at_most("Protoss Pylon", 100, 1)
            if h.has_including_unfinished("Protoss Pylon") and not scout_sent:
                h.send_scout()
                scout_sent = True
        if s >= 10:
            h.try_build_at_most("Protoss Gateway", 150, 1)
        if s >= 12:
            h.try_build_at_most("Protoss Assimilator", 100, 1)
        if s >= 14 and h.has_including_unfinished("Protoss Gateway"):
            h.try_build_at_most("Protoss Cybernetics Core", 200, 1)

        # ── 앞마당 ───────────────────────────────────────────
        if s >= 18 and not natural_sent and m >= 400:
            if h.expand(cost=400):
                natural_sent = True

        # ── 군사 확장 ────────────────────────────────────────
        if s >= 18 and h.has("Protoss Cybernetics Core"):
            h.try_build_at_most("Protoss Gateway", 150, 3)
        if s >= 24:
            h.try_build_at_most("Protoss Assimilator", 100, 2)
        if s >= 26:
            h.try_build_at_most("Protoss Gateway", 150, 5)
            h.try_build_at_most("Protoss Robotics Facility", 200, 1, gas_cost=200)
        if h.has("Protoss Robotics Facility"):
            h.try_build_at_most("Protoss Robotics Support Bay", 150, 1, gas_cost=100)

        # ── 유닛 생산 ────────────────────────────────────────
        if h.has("Protoss Cybernetics Core"):
            h.try_train("Protoss Gateway", "Protoss Dragoon", 125, gas_cost=50)
        else:
            h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        if h.has("Protoss Robotics Support Bay"):
            h.try_train("Protoss Robotics Facility", "Protoss Reaver", 200, gas_cost=100)

        # ── 공격 ─────────────────────────────────────────────
        total = h.count_of("Protoss Zealot") + h.count_of("Protoss Dragoon")
        if total >= 8:
            h.attack_with(ARMY, min_army=8)
        h.reinforce_attack(ARMY)

        if not ctx.get_state().get("enemy_units") and (time.monotonic() - last_scout_at) >= 20.0:
            h.send_scout()
            last_scout_at = time.monotonic()

        ctx.gather_idle_workers(interval=8.0)
        ctx.wait(0.25)


# ─────────────────────────────────────────────────────────────────────────────
# 저그 자율 플레이
#   초반 : 앞마당 Hatch + Spawning Pool → Zergling 러쉬
#   중반 : Lair → Spire → Mutalisk
#   후반 : Hydralisk Den → Hydralisk 혼합
# ─────────────────────────────────────────────────────────────────────────────
def _play_zerg(ctx, h):
    ARMY_LING  = ["Zerg Zergling"]
    ARMY_MUTA  = ["Zerg Mutalisk", "Zerg Zergling"]
    ARMY_HYDRA = ["Zerg Hydralisk", "Zerg Mutalisk", "Zerg Zergling"]

    natural_sent = False
    third_sent   = False
    lair_done    = False
    last_scout_at = 0.0

    while not ctx._stopped:
        s = h.supply_count()
        m = h.minerals()

        # 일꾼 목표
        wt = 12 if s < 16 else 20 if s < 30 else 28
        h.manage_workers(desired=wt, maximum=36)
        h.manage_supply(threshold=2)

        # ── 앞마당 ───────────────────────────────────────────
        if s >= 9 and not natural_sent and m >= 300:
            if h.expand(cost=300):
                natural_sent = True

        # ── 기초 건물 ────────────────────────────────────────
        if s >= 12:
            h.try_build_at_most("Zerg Spawning Pool", 200, 1)
        if h.has_including_unfinished("Zerg Spawning Pool"):
            h.try_build_at_most("Zerg Extractor", 50, 1)

        # ── 3번 기지 ─────────────────────────────────────────
        if s >= 15 and natural_sent and not third_sent and m >= 300:
            if h.count_including_unfinished("Zerg Hatchery") < 3:
                if h.expand(cost=300):
                    third_sent = True

        # ── Lair 변이 ────────────────────────────────────────
        if (h.has("Zerg Spawning Pool")
                and h.has("Zerg Extractor")
                and not lair_done
                and not h.has_including_unfinished("Zerg Lair")):
            if h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100):
                lair_done = True

        # ── Lair 이후 테크 ────────────────────────────────────
        if h.has("Zerg Lair"):
            h.try_build_at_most("Zerg Spire", 200, 1, gas_cost=200)
            h.try_build_at_most("Zerg Hydralisk Den", 100, 1, gas_cost=50)

        # ── 유닛 생산 ────────────────────────────────────────
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)
        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)
        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25)

        # ── 공격 ─────────────────────────────────────────────
        mutas  = h.count_of("Zerg Mutalisk")
        hydras = h.count_of("Zerg Hydralisk")
        lings  = h.count_of("Zerg Zergling")

        if hydras >= 6:
            h.attack_with(ARMY_HYDRA, min_army=6)
            h.reinforce_attack(ARMY_HYDRA)
        elif mutas >= 6:
            h.attack_with(ARMY_MUTA, min_army=6)
            h.reinforce_attack(ARMY_MUTA)
        elif lings >= 12:
            h.attack_with(ARMY_LING, min_army=12)
            h.reinforce_attack(ARMY_LING)

        if not ctx.get_state().get("enemy_units") and (time.monotonic() - last_scout_at) >= 20.0:
            h.send_scout()
            last_scout_at = time.monotonic()

        ctx.gather_idle_workers(interval=8.0)
        ctx.wait(0.25)


# ─────────────────────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────────────────────
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log(f"[자율 플레이] 시작 — 종족: {h.race}")

    if h.race == "Terran":
        _play_terran(ctx, h)
    elif h.race == "Protoss":
        _play_protoss(ctx, h)
    elif h.race == "Zerg":
        _play_zerg(ctx, h)
    else:
        ctx.log(f"[자율 플레이] 알 수 없는 종족 '{h.race}' — 종료")
