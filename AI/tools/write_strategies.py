"""봇 소스 기반 전략 스크립트 일괄 생성 도구"""
import os

SD = r"D:\util\StarCraft\bwapi-data\AI\python\web_bridge\bridgeui\scripts"

SCRIPTS = {}

# ─── PvU_zealot_rush.py ─────────────────────────────────────────────────────
SCRIPTS["PvU_zealot_rush"] = '''"""
질럿 러쉬 - 2 Gate 10/11 Zealot Rush
출처: McRaveZ PvZ_2G_Main

빌드오더:
  9공 -> 파일런
  10공 -> 게이트웨이 1
  11공 -> 게이트웨이 2
  이후 -> 질럿 풀생산, 파일런 추가
"""
_s = {"pylon": False, "gw1": False, "gw2": False}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("PvU_9/9gate")
    ctx.log("질럿 러쉬: 2 Gate 로드 (이벤트 드리븐)")


def on_start(ctx):
    _s.update({"pylon": False, "gw1": False, "gw2": False})
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("질럿 러쉬 시작")
    ctx.request_build_location("Protoss Pylon", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Gateway", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals

    # 파일런 (9공)
    if not _s["pylon"] and su >= 9 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Pylon", loc["tile_x"], loc["tile_y"])
            _s["pylon"] = True

    # 게이트웨이 1 (파일런 완성 후, 미네랄 150)
    if not _s["gw1"] and _done(ctx, "Protoss Pylon") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway", loc["tile_x"], loc["tile_y"])
            _s["gw1"] = True
            ctx.request_build_location("Protoss Gateway",
                                       ctx.start_tile_x, ctx.start_tile_y)

    # 게이트웨이 2 (11공, 미네랄 150)
    if not _s["gw2"] and _s["gw1"] and su >= 11 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway",
                      loc["tile_x"] + 4, loc["tile_y"])
            _s["gw2"] = True

    # 질럿 풀생산 (가스 없이 미네랄만)
    if m >= 100 and st - su >= 2:
        for gw in ctx.idle_buildings("Protoss Gateway"):
            ctx.train(gw["id"], "Protoss Zealot")

    # 파일런 추가 (공급 4 미만 남으면)
    if st - su <= 4 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Protoss Pylon") * 2
            ctx.build(w[0]["id"], "Protoss Pylon",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── PvU_dark_templar.py ────────────────────────────────────────────────────
SCRIPTS["PvU_dark_templar"] = '''"""
다크 템플러 러쉬
출처: Steamhammer Protoss_DarkTemplarRush.txt + McRaveZ PvT_1GC_DT

빌드오더:
  9공  -> 파일런
  10공 -> 게이트웨이
  12공 -> 어시밀레이터
  14공 -> 사이버네틱스 코어
  16공 -> 시타델 오브 아둔
  18공 -> 템플러 아카이브
  이후 -> 다크 템플러 생산
"""
_s = {
    "pylon": False,
    "gw": False,
    "assim": False,
    "cyb": False,
    "citadel": False,
    "archives": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("PvT_2gatedt")
    ctx.log("다크 템플러: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("다크 템플러 러쉬 시작")
    ctx.request_build_location("Protoss Pylon", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Gateway", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals
    g = ctx.gas

    # 파일런 (9공)
    if not _s["pylon"] and su >= 9 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Pylon", loc["tile_x"], loc["tile_y"])
            _s["pylon"] = True

    # 게이트웨이 (파일런 완성 후)
    if not _s["gw"] and _done(ctx, "Protoss Pylon") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway", loc["tile_x"], loc["tile_y"])
            _s["gw"] = True

    # 어시밀레이터 (게이트웨이 짓는 중, 미네랄 75 이상)
    if not _s["assim"] and _s["gw"] and m >= 75:
        geys = list(ctx.geysers.values())
        w = ctx.idle_workers() or ctx.workers()
        if geys and w:
            g0 = geys[0]
            ctx.build(w[0]["id"], "Protoss Assimilator",
                      g0["x"] // 32, g0["y"] // 32)
            _s["assim"] = True

    # 사이버네틱스 코어 (게이트웨이 완성 후)
    if not _s["cyb"] and _done(ctx, "Protoss Gateway") >= 1 and m >= 200:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Cybernetics_Core",
                      loc["tile_x"] + 3, loc["tile_y"])
            _s["cyb"] = True

    # 시타델 오브 아둔 (코어 완성 후)
    if not _s["citadel"] and _done(ctx, "Protoss Cybernetics_Core") >= 1 and g >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Citadel_of_Adun",
                      loc["tile_x"] + 6, loc["tile_y"])
            _s["citadel"] = True

    # 템플러 아카이브 (시타델 완성 후)
    if not _s["archives"] and _done(ctx, "Protoss Citadel_of_Adun") >= 1:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Templar_Archives",
                      loc["tile_x"] + 9, loc["tile_y"])
            _s["archives"] = True

    # 다크 템플러 생산
    if _done(ctx, "Protoss Templar_Archives") >= 1 and m >= 125 and g >= 100:
        for gw in ctx.idle_buildings("Protoss Gateway"):
            ctx.train(gw["id"], "Protoss Dark_Templar")
    elif _done(ctx, "Protoss Cybernetics_Core") >= 1:
        # 코어 완성~아카이브 전까지 드래군으로 채움
        for gw in ctx.idle_buildings("Protoss Gateway"):
            if m >= 125 and g >= 50:
                ctx.train(gw["id"], "Protoss Dragoon")

    # 파일런 추가
    if st - su <= 4 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Protoss Pylon") * 2
            ctx.build(w[0]["id"], "Protoss Pylon",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── PvT_12nexus.py ─────────────────────────────────────────────────────────
SCRIPTS["PvT_12nexus"] = '''"""
PvT 12 Nexus (1 Gate Core Robo)
출처: McRaveZ PvT_1GC_Robo

빌드오더:
  1 게이트웨이 -> 어시밀레이터 -> 사이버네틱스 코어
  -> 로보틱스 -> 앞마당 넥서스 확장
  -> 리버 + 셔틀 운영, 드래군 병행
"""
_s = {
    "pylon": False,
    "gw": False,
    "assim": False,
    "cyb": False,
    "robo": False,
    "nexus2_log": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("PvT_12nexus")
    ctx.log("PvT 12 Nexus: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("PvT 12 Nexus 시작")
    ctx.request_build_location("Protoss Pylon", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Gateway", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals
    g = ctx.gas

    # 파일런 (9공)
    if not _s["pylon"] and su >= 9 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Pylon", loc["tile_x"], loc["tile_y"])
            _s["pylon"] = True

    # 게이트웨이 (파일런 완성 후)
    if not _s["gw"] and _done(ctx, "Protoss Pylon") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway", loc["tile_x"], loc["tile_y"])
            _s["gw"] = True

    # 어시밀레이터 (게이트웨이 짓는 중)
    if not _s["assim"] and _s["gw"] and m >= 75:
        geys = list(ctx.geysers.values())
        w = ctx.idle_workers() or ctx.workers()
        if geys and w:
            g0 = geys[0]
            ctx.build(w[0]["id"], "Protoss Assimilator",
                      g0["x"] // 32, g0["y"] // 32)
            _s["assim"] = True

    # 사이버네틱스 코어 (게이트웨이 완성 후)
    if not _s["cyb"] and _done(ctx, "Protoss Gateway") >= 1 and m >= 200:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Cybernetics_Core",
                      loc["tile_x"] + 3, loc["tile_y"])
            _s["cyb"] = True

    # 로보틱스 (코어 완성 후)
    if not _s["robo"] and _done(ctx, "Protoss Cybernetics_Core") >= 1 and m >= 200 and g >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Robotics_Facility",
                      loc["tile_x"] + 6, loc["tile_y"])
            _s["robo"] = True

    # 앞마당 넥서스 타이밍 알림 (로보틱스 완성 후 미네랄 400)
    if not _s["nexus2_log"] and _done(ctx, "Protoss Robotics_Facility") >= 1 and m >= 400:
        ctx.log("앞마당 넥서스 타이밍 - 수동 건설 필요")
        _s["nexus2_log"] = True

    # 드래군 생산 (코어 완성 후)
    if _done(ctx, "Protoss Cybernetics_Core") >= 1:
        for gw in ctx.idle_buildings("Protoss Gateway"):
            if m >= 125 and g >= 50 and st - su >= 2:
                ctx.train(gw["id"], "Protoss Dragoon")

    # 프루브 생산
    for nex in ctx.idle_buildings("Protoss Nexus"):
        if m >= 50 and st - su >= 2:
            ctx.train(nex["id"], "Protoss Probe")

    # 파일런 추가
    if st - su <= 4 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Protoss Pylon") * 2
            ctx.build(w[0]["id"], "Protoss Pylon",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── PvU_forge_double_nexus.py ──────────────────────────────────────────────
SCRIPTS["PvU_forge_double_nexus"] = '''"""
포지 더블넥 (Forge Fast Expand / FFE)
출처: McRaveZ PvZ_FFE_Forge

빌드오더:
  14공 파일런 -> 16공 포지 -> 넥서스(앞마당) -> 포토캐논 2기
  -> 게이트웨이 -> 사이버네틱스 코어
  이후: 드래군 + 질럿 방어 후 확장 운영
"""
_s = {
    "pylon": False,
    "forge": False,
    "nexus2_note": False,
    "cannon1": False,
    "cannon2": False,
    "gw": False,
    "cyb": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("PvU_forge")
    ctx.log("포지 더블넥: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("포지 더블넥 시작")
    ctx.request_build_location("Protoss Pylon", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Forge", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Gateway", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals

    # 파일런 (14공)
    if not _s["pylon"] and su >= 14 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Pylon", loc["tile_x"], loc["tile_y"])
            _s["pylon"] = True

    # 포지 (파일런 완성 후)
    if not _s["forge"] and _done(ctx, "Protoss Pylon") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Forge")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Forge", loc["tile_x"], loc["tile_y"])
            _s["forge"] = True

    # 앞마당 넥서스 타이밍 알림 (포지 완성 후 미네랄 400)
    if not _s["nexus2_note"] and _done(ctx, "Protoss Forge") >= 1 and m >= 400:
        ctx.log("앞마당 넥서스 건설 타이밍 (내추럴 위치에 수동 건설)")
        _s["nexus2_note"] = True

    # 포토캐논 1 (포지 완성 후)
    if not _s["cannon1"] and _done(ctx, "Protoss Forge") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Photon_Cannon",
                      loc["tile_x"] + 5, loc["tile_y"])
            _s["cannon1"] = True

    # 포토캐논 2
    if not _s["cannon2"] and _s["cannon1"] and m >= 150:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Photon_Cannon",
                      loc["tile_x"] + 8, loc["tile_y"])
            _s["cannon2"] = True

    # 게이트웨이 (포지 완성 후)
    if not _s["gw"] and _done(ctx, "Protoss Forge") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway", loc["tile_x"], loc["tile_y"])
            _s["gw"] = True

    # 사이버네틱스 코어 (게이트웨이 완성 후)
    if not _s["cyb"] and _done(ctx, "Protoss Gateway") >= 1 and m >= 200:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Cybernetics_Core",
                      loc["tile_x"] + 3, loc["tile_y"])
            _s["cyb"] = True

    # 프루브 생산
    for nex in ctx.idle_buildings("Protoss Nexus"):
        if m >= 50 and st - su >= 2:
            ctx.train(nex["id"], "Protoss Probe")

    # 질럿 생산 (게이트웨이 완성 후)
    if _done(ctx, "Protoss Gateway") >= 1:
        for gw in ctx.idle_buildings("Protoss Gateway"):
            if m >= 100 and st - su >= 2:
                ctx.train(gw["id"], "Protoss Zealot")

    # 파일런 추가
    if st - su <= 6 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Protoss Pylon") * 2
            ctx.build(w[0]["id"], "Protoss Pylon",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── PvZ_bisu.py ─────────────────────────────────────────────────────────────
SCRIPTS["PvZ_bisu"] = '''"""
PvZ 비수 (1 Gate Core -> Corsair + High Templar)
출처: McRaveZ PvZ_1GC + Steamhammer PvZ 분석

빌드오더:
  9공  -> 파일런
  10공 -> 게이트웨이
  12공 -> 어시밀레이터
  14공 -> 사이버네틱스 코어
  18공 -> 스타게이트
  이후 -> 커세어 생산 + 드래군 병행
  후반 -> 시타델 -> 아카이브 -> 하이템플러
"""
_s = {
    "pylon": False,
    "gw": False,
    "assim": False,
    "cyb": False,
    "stargate": False,
    "citadel": False,
    "archives": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("PvZ_bisu")
    ctx.log("PvZ 비수: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("PvZ 비수 시작")
    ctx.request_build_location("Protoss Pylon", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Protoss Gateway", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals
    g = ctx.gas

    # 파일런 (9공)
    if not _s["pylon"] and su >= 9 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Pylon", loc["tile_x"], loc["tile_y"])
            _s["pylon"] = True

    # 게이트웨이 (파일런 완성 후)
    if not _s["gw"] and _done(ctx, "Protoss Pylon") >= 1 and m >= 150:
        loc = ctx.get_build_location("Protoss Gateway")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Gateway", loc["tile_x"], loc["tile_y"])
            _s["gw"] = True

    # 어시밀레이터 (게이트웨이 짓는 중)
    if not _s["assim"] and _s["gw"] and m >= 75:
        geys = list(ctx.geysers.values())
        w = ctx.idle_workers() or ctx.workers()
        if geys and w:
            g0 = geys[0]
            ctx.build(w[0]["id"], "Protoss Assimilator",
                      g0["x"] // 32, g0["y"] // 32)
            _s["assim"] = True

    # 사이버네틱스 코어 (게이트웨이 완성 후)
    if not _s["cyb"] and _done(ctx, "Protoss Gateway") >= 1 and m >= 200:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Cybernetics_Core",
                      loc["tile_x"] + 3, loc["tile_y"])
            _s["cyb"] = True

    # 스타게이트 (코어 완성 후, 가스 150 이상)
    if not _s["stargate"] and _done(ctx, "Protoss Cybernetics_Core") >= 1 and m >= 150 and g >= 150:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Stargate",
                      loc["tile_x"] + 6, loc["tile_y"])
            _s["stargate"] = True

    # 시타델 (드래군 4기 이상 or 스타게이트 완성 후)
    if not _s["citadel"] and _done(ctx, "Protoss Stargate") >= 1 and g >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Citadel_of_Adun",
                      loc["tile_x"] + 9, loc["tile_y"])
            _s["citadel"] = True

    # 아카이브 (시타델 완성 후)
    if not _s["archives"] and _done(ctx, "Protoss Citadel_of_Adun") >= 1:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Protoss Templar_Archives",
                      loc["tile_x"] + 12, loc["tile_y"])
            _s["archives"] = True

    # 커세어 생산 (스타게이트 완성 후)
    if _done(ctx, "Protoss Stargate") >= 1 and m >= 150 and g >= 100 and st - su >= 2:
        for sg in ctx.idle_buildings("Protoss Stargate"):
            ctx.train(sg["id"], "Protoss Corsair")

    # 드래군 생산 (코어 완성 후)
    if _done(ctx, "Protoss Cybernetics_Core") >= 1:
        for gw in ctx.idle_buildings("Protoss Gateway"):
            if m >= 125 and g >= 50 and st - su >= 2:
                ctx.train(gw["id"], "Protoss Dragoon")

    # 프루브 생산
    for nex in ctx.idle_buildings("Protoss Nexus"):
        if m >= 50 and st - su >= 2:
            ctx.train(nex["id"], "Protoss Probe")

    # 파일런 추가
    if st - su <= 4 and m >= 100:
        loc = ctx.get_build_location("Protoss Pylon")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Protoss Pylon") * 2
            ctx.build(w[0]["id"], "Protoss Pylon",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── ZvT_3hatchmuta.py ───────────────────────────────────────────────────────
SCRIPTS["ZvT_3hatchmuta"] = '''"""
ZvT 3 Hatch Muta
출처: Steamhammer Zerg_3HatchMuta.txt + McRaveZ ZvT

빌드오더:
  드론 x4 -> 오버로드 -> 드론 x4 -> 해처리(앞마당) -> 스포닝풀
  -> 해처리2 -> 익스트랙터 -> 레어 -> 스파이어 -> 뮤탈 생산
"""
_s = {
    "pool": False,
    "extractor": False,
    "lair": False,
    "spire": False,
    "hatch2_note": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("ZvT_3hatchmuta")
    ctx.log("3 Hatch Muta: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("3 Hatch Muta 시작")
    ctx.request_build_location("Zerg Hatchery", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Zerg Spawning_Pool", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals
    g = ctx.gas

    # 스포닝 풀 (18공, 미네랄 200)
    if not _s["pool"] and su >= 18 and m >= 200:
        loc = ctx.get_build_location("Zerg Spawning_Pool")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Zerg Spawning_Pool",
                      loc["tile_x"], loc["tile_y"])
            _s["pool"] = True

    # 앞마당 해처리 타이밍 알림
    if not _s["hatch2_note"] and _s["pool"] and m >= 300:
        ctx.log("앞마당 해처리 건설 타이밍 (내추럴 위치에 수동 건설)")
        _s["hatch2_note"] = True

    # 익스트랙터 (스포닝풀 완성 후)
    if not _s["extractor"] and _done(ctx, "Zerg Spawning_Pool") >= 1 and m >= 50:
        geys = list(ctx.geysers.values())
        w = ctx.idle_workers() or ctx.workers()
        if geys and w:
            g0 = geys[0]
            ctx.build(w[0]["id"], "Zerg Extractor",
                      g0["x"] // 32, g0["y"] // 32)
            _s["extractor"] = True

    # 레어 (해처리 2개 이상 + 가스 150)
    if not _s["lair"] and _done(ctx, "Zerg Hatchery") >= 2 and g >= 150:
        for h in ctx.idle_buildings("Zerg Hatchery"):
            ctx.train(h["id"], "Zerg Lair")
            _s["lair"] = True
            break

    # 스파이어 (레어 완성 후, 미네랄 200 + 가스 150)
    if not _s["spire"] and _done(ctx, "Zerg Lair") >= 1 and m >= 200 and g >= 150:
        loc = ctx.get_build_location("Zerg Hatchery")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Zerg Spire",
                      loc["tile_x"] + 5, loc["tile_y"])
            _s["spire"] = True

    # 뮤탈리스크 생산 (스파이어 완성 후)
    if _done(ctx, "Zerg Spire") >= 1 and m >= 100 and g >= 100 and st - su >= 2:
        for h in ctx.idle_buildings("Zerg Hatchery"):
            ctx.train(h["id"], "Zerg Mutalisk")

    # 드론 생산 (뮤탈 전까지)
    if _done(ctx, "Zerg Spire") == 0:
        for h in ctx.idle_buildings("Zerg Hatchery"):
            if m >= 50 and st - su >= 2:
                ctx.train(h["id"], "Zerg Drone")


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''

# ─── TvZ_2rax.py ─────────────────────────────────────────────────────────────
SCRIPTS["TvZ_2rax"] = '''"""
TvZ 2 Rax (11/13 빌드)
출처: McRaveZ TvZ_2Rax_1113

빌드오더:
  11공 -> 배럭 1
  18공 -> 서플라이 디팟
  22공 -> 배럭 2
  이후 -> 마린 풀생산, SCV 병행
"""
_s = {
    "depot1": False,
    "rax1": False,
    "rax2": False,
}


def _done(ctx, t):
    return len([u for u in ctx.buildings(t) if not u.get("constructing")])


def run(ctx):
    """즉시 실행 - StarCraft 화면에 전략 선언."""
    ctx.set_opening("TvZ_2rax")
    ctx.log("TvZ 2 Rax: 이벤트 드리븐 로드")


def on_start(ctx):
    for k in _s:
        _s[k] = False
    ctx.set_manual()
    ctx.gather_all()
    ctx.log("TvZ 2 Rax 시작")
    ctx.request_build_location("Terran Barracks", ctx.start_tile_x, ctx.start_tile_y)
    ctx.request_build_location("Terran Supply_Depot", ctx.start_tile_x, ctx.start_tile_y)


def on_frame(ctx):
    su, st = ctx.supply
    m = ctx.minerals

    # 배럭 1 (11공)
    if not _s["rax1"] and su >= 11 and m >= 150:
        loc = ctx.get_build_location("Terran Barracks")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Terran Barracks", loc["tile_x"], loc["tile_y"])
            _s["rax1"] = True

    # 서플라이 디팟 (공급 6 미만 남으면)
    if not _s["depot1"] and _s["rax1"] and st - su <= 6 and m >= 100:
        loc = ctx.get_build_location("Terran Supply_Depot")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Terran Supply_Depot",
                      loc["tile_x"], loc["tile_y"])
            _s["depot1"] = True

    # 배럭 2 (배럭1 완성 후)
    if not _s["rax2"] and _done(ctx, "Terran Barracks") >= 1 and m >= 150:
        loc = ctx.get_build_location("Terran Barracks")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            ctx.build(w[0]["id"], "Terran Barracks",
                      loc["tile_x"] + 4, loc["tile_y"])
            _s["rax2"] = True

    # 마린 생산
    for rax in ctx.idle_buildings("Terran Barracks"):
        if m >= 50 and st - su >= 2:
            ctx.train(rax["id"], "Terran Marine")

    # SCV 생산
    for cc in ctx.idle_buildings("Terran Command_Center"):
        if m >= 50 and st - su >= 2:
            ctx.train(cc["id"], "Terran SCV")

    # 서플라이 추가 (공급 4 미만 남으면)
    if st - su <= 4 and m >= 100:
        loc = ctx.get_build_location("Terran Supply_Depot")
        w = ctx.idle_workers() or ctx.workers()
        if loc and w:
            off = _done(ctx, "Terran Supply_Depot") * 3
            ctx.build(w[0]["id"], "Terran Supply_Depot",
                      loc["tile_x"] + off, loc["tile_y"])


def on_build_location_result(ctx, building_type, tile_x, tile_y, ok):
    if not ok:
        ctx._build_location_cache.pop(building_type, None)
'''


# ─── 파일 쓰기 ──────────────────────────────────────────────────────────────
for name, content in SCRIPTS.items():
    path = os.path.join(SD, name + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: {name}.py")

print("\n완료: 전략 스크립트 7개 작성")
