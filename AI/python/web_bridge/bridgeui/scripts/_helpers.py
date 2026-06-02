"""
공통 StarCraft 전략 헬퍼 모듈.
각 스크립트에서 `from _helpers import StrategyHelper` 로 임포트.
"""
import time


def _n(t):
    """타입 이름 정규화: 언더스코어↔공백 무관하게 비교 가능하도록 공백으로 통일."""
    return t.replace("_", " ") if t else ""


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

    # 동일 프로세스 내 중복 스크립트/스레드가 있어도 확장 명령 스팸을 막기 위한 전역 가드
    _global_expand_order_until = 0.0

    def __init__(self, ctx):
        self.ctx = ctx
        self.race = None
        self._natural_tile = None
        self._natural_expand_retry_at = 0.0
        self._pending_builds = {}   # btype -> timestamp (중복 건설 방지)
        self._attacking = False
        self._attack_target = None
        self._attack_target_index = 0
        self._trace_name = None
        self._trace_last = 0.0
        self._trace_interval = 2.0
        self._once_marks = set()
        self._initial_worker_count = None

    def setup(self, timeout=30.0):
        """게임이 시작될 때까지 대기 후 종족 정보 설정. False 반환 시 게임 미접속."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.ctx._stopped:
                return False
            state = self.ctx.get_state()
            if state.get("frame", -1) >= 0 and state.get("self_race"):
                self.race = state["self_race"]
                own = state.get("own_units", [])
                buildings = [u["type"] for u in own if u.get("is_building")]
                self._initial_worker_count = len([u for u in own if u.get("is_worker")])
                self.ctx.log(f"[helper] 종족={self.race} | 유닛:{len(own)} | 건물:{buildings} | 미네랄:{state.get('minerals')}")
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

    def user_locked_unit_ids(self):
        """사용자 명령 우선권이 활성화된 유닛 ID 집합."""
        state = self.ctx.get_state()
        overrides = state.get("user_unit_overrides") or {}
        now = time.time()
        locked = set()
        for key, until in overrides.items():
            try:
                uid = int(key)
                exp = float(until)
            except (TypeError, ValueError):
                continue
            if exp > now:
                locked.add(uid)
        return locked

    def is_user_locked(self, unit_id):
        try:
            uid = int(unit_id)
        except (TypeError, ValueError):
            return False
        return uid in self.user_locked_unit_ids()

    def _free_worker(self):
        cands = [w for w in self.idle_workers()
                 if (not w.get("constructing")) and (not self.is_user_locked(w.get("id")))]
        if cands:
            return cands[0]
        # idle 없으면 일반 일꾼
        ws = [w for w in self.workers() if not self.is_user_locked(w.get("id"))]
        return ws[0] if ws else None

    def buildings_of(self, btype, completed_only=True):
        btype_n = _n(btype)
        units = [u for u in self.ctx.own_units() if _n(u.get("type")) == btype_n]
        if completed_only:
            units = [u for u in units if u.get("completed", True)]
        return units

    def count_of(self, utype, completed_only=False):
        utype_n = _n(utype)
        return sum(
            1 for u in self.ctx.own_units()
            if _n(u.get("type")) == utype_n and (not completed_only or u.get("completed", True))
        )

    def units_of(self, utype):
        utype_n = _n(utype)
        return [u for u in self.ctx.own_units() if _n(u.get("type")) == utype_n]

    def has(self, btype, completed_only=True):
        return self.count_of(btype, completed_only) > 0

    def mark_once(self, key, message):
        """같은 key에 대해 로그를 한 번만 남긴다."""
        if key in self._once_marks:
            return
        self._once_marks.add(key)
        self.ctx.log(message)

    def start_trace(self, name, interval=2.0):
        """C++ parity 점검용 주기 트레이스 시작."""
        self._trace_name = name
        self._trace_interval = interval
        self._trace_last = 0.0

    def trace(self, phase, **extra):
        """핵심 상태를 주기적으로 로깅."""
        if not self._trace_name:
            return
        now = time.monotonic()
        if now - self._trace_last < self._trace_interval:
            return
        self._trace_last = now
        s = self.ctx.get_state()
        msg = (
            f"[trace:{self._trace_name}] phase={phase} "
            f"frame={s.get('frame', -1)} supply={self.supply_count()} "
            f"workers={len(self.workers())} minerals={self.minerals()} gas={self.gas()}"
        )
        if extra:
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            msg += " " + kv
        self.ctx.log(msg)

    def opening_lost_too_many_workers(self, margin=3):
        """C++ opening_lost_too_many_workers()의 단순 근사치."""
        if self._initial_worker_count is None:
            return False
        return len(self.workers()) <= max(0, self._initial_worker_count - margin)

    def enemy_offense_larger_than_defense(self, cushion=1):
        """C++ is_enemy_offense_larger_than_defense()의 단순 근사치."""
        s = self.ctx.get_state()
        enemy_cnt = len(s.get("enemy_units", []))
        own_combat = sum(
            1 for u in self.ctx.own_units()
            if (not u.get("is_worker")) and (not u.get("is_building"))
        )
        return enemy_cnt > (own_combat + cushion)

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

    def try_build_near(self, btype, cost, near_tile, max_count=1, gas_cost=0, cooldown=18.0):
        """지정 타일 근처에 건물 건설 시도. True 반환 = 명령 전송됨."""
        if not near_tile:
            return False
        if self.count_of(btype, completed_only=False) >= max_count:
            return False
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
        tx, ty = near_tile
        loc = self.ctx.find_build_location_sync(worker["id"], btype, near_tile_x=tx, near_tile_y=ty)
        if loc:
            self.ctx.build(worker["id"], btype, loc[0], loc[1])
            self._pending_builds[btype] = now
            self.ctx.log(f"건설: {btype} ({loc[0]},{loc[1]}) [near {tx},{ty}]")
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
                self.ctx.log(f"훈련: {utype}")
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
            self.ctx.log(f"훈련: {utype}")
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
        supply_n = _n(SUPPLY[self.race])
        under = [u for u in self.ctx.own_units()
                 if _n(u.get("type")) == supply_n and not u.get("completed")]
        if under:
            return False
        return self.try_build(SUPPLY[self.race], 100, max_count=99, cooldown=12.0)

    def manage_workers(self, desired=14, maximum=24):
        """일꾼 수가 desired 미만이면 훈련."""
        if not self.race or len(self.workers()) >= min(desired, maximum):
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
        now = time.time()
        if now < StrategyHelper._global_expand_order_until:
            return False
        if now < self._natural_expand_retry_at:
            return False
        # 이미 멀티가 착공/완료 상태면 재명령 방지
        if self.count_including_unfinished(BASE[self.race]) >= 2:
            self._natural_expand_retry_at = now + 10.0
            return False
        if not self._natural_tile:
            self._natural_tile = self.ctx.get_natural_expansion_sync()
        if not self._natural_tile:
            return False
        worker = self._free_worker()
        if not worker:
            return False
        tx, ty = self._natural_tile
        loc = self.ctx.find_build_location_sync(worker["id"], BASE[self.race], near_tile_x=tx, near_tile_y=ty)
        if not loc:
            self._natural_expand_retry_at = now + 0.75
            self.ctx.log(f"확장 위치 탐색 실패: {BASE[self.race]} near ({tx},{ty})")
            return False
        self.ctx.build(worker["id"], BASE[self.race], loc[0], loc[1])
        self.ctx.log(f"확장: {BASE[self.race]} → ({loc[0]},{loc[1]}) [near {tx},{ty}]")
        self._natural_tile = None  # 다음 확장을 위해 초기화
        self._natural_expand_retry_at = now + 20.0  # 일꾼이 이동·착공할 시간 확보 후 재시도
        StrategyHelper._global_expand_order_until = now + 20.0
        return True

    # ── 전투 ────────────────────────────────────────────────────────────────

    def attack_with(self, unit_types, min_army=4):
        """지정 유닛 종류로 공격. min_army 이상일 때만 출격."""
        army = self.army_units(*unit_types)
        if len(army) < min_army:
            return False

        state = self.ctx.get_state()
        # 알려진 적 유닛이 있으면 그쪽으로, 아니면 시작지 후보/맵 주요 지점을 순회 탐색
        enemies = state.get("enemy_units", [])
        if enemies:
            target_x, target_y = enemies[0]["x"], enemies[0]["y"]
        else:
            target_x, target_y = self._next_search_target()

        for u in army:
            if self.is_user_locked(u.get("id")):
                continue
            self.ctx.attack_move(u["id"], target_x, target_y)

        self.ctx.log(f"공격 출격: {len(army)}유닛 → ({target_x},{target_y})")
        self._attacking = True
        self._attack_target = (target_x, target_y)
        return True

    def reinforce_attack(self, unit_types):
        """이미 공격 중이면 신규 유닛도 같은 방향으로 이동."""
        if not self._attacking:
            return
        state = self.ctx.get_state()
        enemies = state.get("enemy_units", [])
        if enemies:
            tx, ty = enemies[0]["x"], enemies[0]["y"]
            self._attack_target = (tx, ty)
        elif self._attack_target:
            tx, ty = self._attack_target
        else:
            tx, ty = self._next_search_target()
            self._attack_target = (tx, ty)
        for ut in unit_types:
            for u in self.units_of(ut):
                if u.get("idle"):
                    if self.is_user_locked(u.get("id")):
                        continue
                    self.ctx.attack_move(u["id"], tx, ty)

    def _next_search_target(self):
        """적이 안 보일 때 탐색용 공격 목표를 순환 선택한다."""
        state = self.ctx.get_state()
        starts = state.get("enemy_start_locations") or []

        if starts:
            idx = self._attack_target_index % len(starts)
            self._attack_target_index += 1
            loc = starts[idx]
            return int(loc.get("tile_x", 64)) * 32, int(loc.get("tile_y", 40)) * 32

        width_px = int(state.get("map_width_tiles", 128)) * 32
        height_px = int(state.get("map_height_tiles", 128)) * 32
        points = [
            (width_px // 2, height_px // 2),
            (64, 64),
            (max(64, width_px - 64), 64),
            (64, max(64, height_px - 64)),
            (max(64, width_px - 64), max(64, height_px - 64)),
        ]
        idx = self._attack_target_index % len(points)
        self._attack_target_index += 1
        return points[idx]


    # ── supply milestone 헬퍼 ────────────────────────────────────────────────

    def supply_count(self):
        """(supplyUsed + 1) // 2 — C++ opening_supply_count()와 동일 (실제 공급 수치)."""
        s = self.ctx.get_state()
        return ((s.get("supply_used") or 0) + 1) // 2

    def count_including_unfinished(self, utype):
        """건설/워핑 중인 건물 포함 전체 유닛/건물 수."""
        utype_n = _n(utype)
        return sum(1 for u in self.ctx.own_units() if _n(u.get("type")) == utype_n)

    def has_including_unfinished(self, btype):
        """건설 중 포함 해당 건물이 1개 이상 존재하는지 여부."""
        return self.count_including_unfinished(btype) > 0

    def try_build_at_most(self, btype, cost, n, gas_cost=0):
        """count_including_unfinished(btype) < n 일 때만 건설 시도 (cooldown 8초)."""
        if self.count_including_unfinished(btype) >= n:
            return False
        return self.try_build(btype, cost, max_count=n, gas_cost=gas_cost, cooldown=8.0)

    def try_train_at_most(self, from_btype, utype, cost, max_train, gas_cost=0):
        """count_including_unfinished(utype) < max_train 일 때만 훈련 시도."""
        if self.count_including_unfinished(utype) >= max_train:
            return False
        return self.try_train(from_btype, utype, cost, gas_cost=gas_cost, max_count=max_train)

    def send_scout(self):
        """일꾼 1명을 스카웃으로 파견."""
        self.ctx.control("scout")
        self.ctx.log("[helper] 스카웃 출발")

    def delegate_to_cpp(self, opening=None):
        """오프닝 스크립트 뒤를 Python 자율 플레이로 이어서 실행합니다.

        기존 전략들은 오프닝만 끝내고 C++ 메인으로 넘기는 구조였는데,
        현재는 Python 자율 루프가 그 뒤를 이어받도록 연결한다.
        """
        self.ctx.log(f"[helper] delegate_to_cpp → Python 자율 플레이로 전환 (요청 오프닝: {opening or '자율'})")
        from auto_play import run as _auto_play_run
        _auto_play_run(self.ctx)


def minimum(a, b):
    return a if a < b else b
