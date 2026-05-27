"""
공통 StarCraft 전략 헬퍼 모듈.
각 스크립트에서 `from _helpers import StrategyHelper` 로 임포트.
"""
import time

# ── 종족별 상수 ─────────────────────────────────────────────────────────────
WORKER = {
    "Protoss": "Protoss Probe",
    "Terran": "Terran SCV",
    "Zerg": "Zerg Drone",
}
BASE = {
    "Protoss": "Protoss Nexus",
    "Terran": "Terran Command Center",
    "Zerg": "Zerg Hatchery",
}
SUPPLY = {
    "Protoss": "Protoss Pylon",
    "Terran": "Terran Supply Depot",
    "Zerg": "Zerg Overlord",
}


class StrategyHelper:
    """ScriptContext 를 감싸는 편의 클래스."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.race = None
        self._natural_tile = None
        self._pending_builds = {}   # btype -> timestamp (중복 건설 방지)
        self._attacking = False

    def setup(self, timeout=30.0):
        """게임이 시작될 때까지 대기 후 종족 정보 설정. False 반환 시 게임 미접속."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.ctx._stopped:
                return False
            state = self.ctx.get_state()
            if state.get("frame", -1) >= 0 and state.get("self_race"):
                self.race = state["self_race"]
                self.ctx.log(f"[helper] 종족={self.race}, 게임 시작")
                return True
            time.sleep(0.5)
        self.ctx.log("[helper] 게임 접속 대기 시간 초과")
        return False

    # ── 자원 ────────────────────────────────────────────────────────────────

    def minerals(self):
        return self.ctx.get_state().get("minerals") or 0

    def gas(self):
        return self.ctx.get_state().get("gas") or 0

    def supply_free(self):
        s = self.ctx.get_state()
        return (s.get("supply_total") or 0) - (s.get("supply_used") or 0)

    # ── 유닛 조회 ────────────────────────────────────────────────────────────

    def workers(self):
        return [u for u in self.ctx.own_units() if u.get("is_worker")]

    def idle_workers(self):
        return [u for u in self.workers()
                if u.get("idle") and not u.get("constructing")]

    def _free_worker(self):
        cands = [w for w in self.idle_workers() if not w.get("constructing")]
        if cands:
            return cands[0]
        # idle 없으면 일반 일꾼
        ws = self.workers()
        return ws[0] if ws else None

    def buildings_of(self, btype, completed_only=True):
        units = [u for u in self.ctx.own_units() if u.get("type") == btype]
        if completed_only:
            units = [u for u in units if u.get("completed", True)]
        return units

    def count_of(self, utype, completed_only=False):
        return sum(
            1 for u in self.ctx.own_units()
            if u.get("type") == utype and (not completed_only or u.get("completed", True))
        )

    def units_of(self, utype):
        return [u for u in self.ctx.own_units() if u.get("type") == utype]

    def has(self, btype, completed_only=True):
        return self.count_of(btype, completed_only) > 0

    def army_units(self, *unit_types):
        result = []
        for ut in unit_types:
            result.extend(self.units_of(ut))
        return result

    # ── 건설 ────────────────────────────────────────────────────────────────

    def try_build(self, btype, cost, max_count=1, gas_cost=0, cooldown=18.0):
        """건물 건설 시도. True 반환 = 명령 전송됨."""
        if self.count_of(btype, completed_only=False) >= max_count:
            return False
        # 최근에 같은 건물 명령을 보냈으면 스킵 (중복 방지)
        now = time.time()
        if now - self._pending_builds.get(btype, 0) < cooldown:
            return False
        if self.minerals() < cost:
            return False
        if gas_cost > 0 and self.gas() < gas_cost:
            return False
        worker = self._free_worker()
        if not worker:
            return False
        loc = self.ctx.find_build_location_sync(worker["id"], btype)
        if loc:
            self.ctx.build(worker["id"], btype, loc[0], loc[1])
            self._pending_builds[btype] = now
            self.ctx.log(f"건설: {btype} ({loc[0]},{loc[1]})")
            return True
        return False

    def try_train(self, from_btype, utype, cost, gas_cost=0, max_count=9999):
        """건물에서 유닛 훈련 시도."""
        if self.count_of(utype) >= max_count:
            return False
        if self.minerals() < cost:
            return False
        if gas_cost > 0 and self.gas() < gas_cost:
            return False
        for b in self.buildings_of(from_btype):
            if not b.get("training"):
                self.ctx.train(b["id"], utype)
                return True
        return False

    def try_train_larva(self, utype, cost, gas_cost=0, max_count=9999):
        """저그 전용: 라바에서 유닛 훈련."""
        if self.count_of(utype) >= max_count:
            return False
        if self.minerals() < cost:
            return False
        if gas_cost > 0 and self.gas() < gas_cost:
            return False
        larvas = self.units_of("Zerg Larva")
        if larvas:
            self.ctx.train(larvas[0]["id"], utype)
            return True
        return False

    def try_morph(self, from_utype, to_utype, cost, gas_cost=0):
        """저그 변이 (Hydra→Lurker, Hatchery→Lair 등)."""
        if self.minerals() < cost:
            return False
        if gas_cost > 0 and self.gas() < gas_cost:
            return False
        for u in self.units_of(from_utype):
            if not u.get("training") and not u.get("constructing"):
                self.ctx.morph(u["id"], to_utype)
                return True
        return False

    # ── 경제 관리 ────────────────────────────────────────────────────────────

    def manage_supply(self, threshold=4):
        """공급이 부족하면 파일런/서플라이/오버로드 생산."""
        if not self.race or self.supply_free() > threshold:
            return False
        if self.race == "Zerg":
            return self.try_train_larva("Zerg Overlord", 100)
        # 이미 건설 중인 공급 건물이 있으면 대기
        under = [u for u in self.ctx.own_units()
                 if u.get("type") == SUPPLY[self.race] and not u.get("completed")]
        if under:
            return False
        return self.try_build(SUPPLY[self.race], 100, max_count=99, cooldown=12.0)

    def manage_workers(self, desired=14, maximum=24):
        """일꾼 수가 desired 미만이면 훈련."""
        if not self.race or len(self.workers()) >= minimum(desired, maximum):
            return False
        cost = 50
        if self.race == "Zerg":
            return self.try_train_larva(WORKER["Zerg"], cost, max_count=maximum)
        return self.try_train(BASE[self.race], WORKER[self.race], cost, max_count=desired)

    # ── 확장 ────────────────────────────────────────────────────────────────

    def expand(self, cost=400, gas_cost=0):
        """앞마당 넥서스/커맨드센터/해처리 건설."""
        if not self.race:
            return False
        if self.minerals() < cost:
            return False
        if not self._natural_tile:
            self._natural_tile = self.ctx.get_natural_expansion_sync()
        if not self._natural_tile:
            return False
        worker = self._free_worker()
        if not worker:
            return False
        tx, ty = self._natural_tile
        self.ctx.build(worker["id"], BASE[self.race], tx, ty)
        self.ctx.log(f"확장: {BASE[self.race]} → ({tx},{ty})")
        self._natural_tile = None  # 다음 확장을 위해 초기화
        return True

    # ── 전투 ────────────────────────────────────────────────────────────────

    def attack_with(self, unit_types, min_army=4):
        """지정 유닛 종류로 공격. min_army 이상일 때만 출격."""
        army = self.army_units(*unit_types)
        if len(army) < min_army:
            return False

        state = self.ctx.get_state()
        stx = (state.get("start_tile_x") or 64) * 32
        sty = (state.get("start_tile_y") or 40) * 32

        # 알려진 적 유닛이 있으면 그쪽으로, 아니면 맵 반대편으로
        enemies = state.get("enemy_units", [])
        if enemies:
            target_x, target_y = enemies[0]["x"], enemies[0]["y"]
        else:
            # 맵 크기 4096×4096 기준 반대편 추정
            target_x = max(32, 4096 - stx)
            target_y = max(32, 4096 - sty)

        for u in army:
            self.ctx.attack_move(u["id"], target_x, target_y)

        self.ctx.log(f"공격 출격: {len(army)}유닛 → ({target_x},{target_y})")
        self._attacking = True
        return True

    def reinforce_attack(self, unit_types):
        """이미 공격 중이면 신규 유닛도 같은 방향으로 이동."""
        if not self._attacking:
            return
        state = self.ctx.get_state()
        enemies = state.get("enemy_units", [])
        if not enemies:
            return
        tx, ty = enemies[0]["x"], enemies[0]["y"]
        for ut in unit_types:
            for u in self.units_of(ut):
                if u.get("idle"):
                    self.ctx.attack_move(u["id"], tx, ty)


def minimum(a, b):
    return a if a < b else b
