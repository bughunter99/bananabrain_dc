# -*- coding: utf-8 -*-
"""
전략 스크립트 전체를 실제 게임 로직이 있는 버전으로 재작성.
한 번만 실행하는 유틸리티 스크립트.
"""
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "web_bridge", "bridgeui", "scripts")

HEADER = '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper
'''

SCRIPTS = {}

# ═══════════════════════════════════════════════════════════════════════════
# PROTOSS
# ═══════════════════════════════════════════════════════════════════════════

SCRIPTS["PvZ_10-12gate.py"] = '''"""PvZ 10/12 Gate: Pylon->Gateway x2->Zealot rush"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvZ 10/12 Gate 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=14)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvZ_bisu.py"] = '''"""PvZ Bisu: Gate->Assimilator->Cyber->Stargate->Corsairs+Zealots"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvZ Bisu 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=16)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_build("Protoss Stargate", 150, max_count=1, gas_cost=150)
        if h.has("Protoss Stargate"):
            h.try_train("Protoss Stargate", "Protoss Corsair", 150, gas_cost=100)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Corsair", "Protoss Zealot"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvT_12nexus.py"] = '''"""PvT 12 Nexus: Gate->expand->Cyber->Dragoons"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvT 12 Nexus 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=1)
        if h.minerals() >= 600 and not h.has("Protoss Nexus", completed_only=False):
            h.expand(cost=400)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_train("Protoss Gateway", "Protoss Dragoon", 125, gas_cost=50)
        h.attack_with(["Protoss Dragoon"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvP_3gaterobo.py"] = '''"""PvP 3-Gate Robo: Pylon->Gate x3->Robo->Dragoons+Shuttle"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvP 3게이트 로보 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=16)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        h.try_build("Protoss Gateway", 150, max_count=3)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_build("Protoss Robotics Facility", 200, max_count=1, gas_cost=200)
        if h.has("Protoss Cybernetics Core"):
            h.try_train("Protoss Gateway", "Protoss Dragoon", 125, gas_cost=50)
        if h.has("Protoss Robotics Facility"):
            h.try_train("Protoss Robotics Facility", "Protoss Shuttle", 200, gas_cost=200)
        h.attack_with(["Protoss Dragoon", "Protoss Shuttle"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_forge.py"] = '''"""PvU Forge: Forge->Photon Cannon x2->Gate->Zealots"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Forge 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=16)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Forge", 150, max_count=1)
        if h.has("Protoss Forge"):
            h.try_build("Protoss Photon Cannon", 150, max_count=2)
            h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_forge_double_nexus.py"] = '''"""PvU Forge Double Nexus: Forge->Cannon->expand->Gate->Zealots"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Forge Double Nexus 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Forge", 150, max_count=1)
        if h.has("Protoss Forge"):
            h.try_build("Protoss Photon Cannon", 150, max_count=1)
            if h.minerals() >= 400:
                h.expand(cost=400)
            h.try_build("Protoss Gateway", 150, max_count=3)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_zealot_rush.py"] = '''"""PvU Zealot Rush: Pylon->Gate x2->Zealots (no gas)"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Zealot Rush 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=10)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_dark_templar.py"] = '''"""PvU Dark Templar: Gate->Cyber->Citadel->Templar Archives->DTs"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Dark Templar 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=14)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_build("Protoss Citadel of Adun", 150, max_count=1, gas_cost=100)
        if h.has("Protoss Citadel of Adun"):
            h.try_build("Protoss Templar Archives", 150, max_count=1, gas_cost=200)
        if h.has("Protoss Templar Archives"):
            h.try_train("Protoss Gateway", "Protoss Dark Templar", 125, gas_cost=100)
        h.attack_with(["Protoss Dark Templar"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_reaver_drop.py"] = '''"""PvU Reaver Drop: Gate->Cyber->Robo->Shuttle->Reaver"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Reaver Drop 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=16)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_build("Protoss Robotics Facility", 200, max_count=1, gas_cost=200)
        if h.has("Protoss Robotics Facility"):
            h.try_build("Protoss Robotics Support Bay", 150, max_count=1, gas_cost=100)
            h.try_train("Protoss Robotics Facility", "Protoss Shuttle", 200, gas_cost=200)
        if h.has("Protoss Robotics Support Bay"):
            h.try_train("Protoss Robotics Facility", "Protoss Reaver", 200, gas_cost=100)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Reaver", "Protoss Shuttle"], min_army=2)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_one_punch.py"] = '''"""PvU One Punch: Gate x4->Cyber->Templar Archives->Zealots+HT"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU One Punch 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=18)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=4)
        h.try_build("Protoss Assimilator", 100, max_count=1)
        if h.has("Protoss Assimilator"):
            h.try_build("Protoss Cybernetics Core", 200, max_count=1)
        if h.has("Protoss Cybernetics Core"):
            h.try_build("Protoss Citadel of Adun", 150, max_count=1, gas_cost=100)
        if h.has("Protoss Citadel of Adun"):
            h.try_build("Protoss Templar Archives", 150, max_count=1, gas_cost=200)
        if h.has("Protoss Templar Archives"):
            h.try_train("Protoss Gateway", "Protoss High Templar", 50, gas_cost=150, max_count=4)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot", "Protoss High Templar"], min_army=10)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["PvU_natural_expand.py"] = '''"""PvU Natural Expand: expand->Gate->Pylon->Zealots"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Natural Expand 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        if h.minerals() >= 400 and not h.has("Protoss Nexus", completed_only=False):
            h.expand(cost=400)
        h.try_build("Protoss Gateway", 150, max_count=3)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

# ═══════════════════════════════════════════════════════════════════════════
# TERRAN
# ═══════════════════════════════════════════════════════════════════════════

SCRIPTS["TvZ_1raxfe.py"] = '''"""TvZ 1 Rax FE: Barracks->SupplyDepot->CC expand->Factory->Marines+Tanks"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvZ 1Rax FE 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=18)
        h.try_build("Terran Barracks", 150, max_count=2)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        if h.minerals() >= 500 and not h.has("Terran Command Center", completed_only=False):
            h.expand(cost=400)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Siege Tank Siege Mode"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvZ_2rax.py"] = '''"""TvZ 2 Rax: Barracks x2->Marines rush"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvZ 2 Rax 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=14)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=2)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        h.attack_with(["Terran Marine"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvT_1factfe.py"] = '''"""TvT 1 Factory FE: Barracks->Factory->CC expand->Siege Tank"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvT 1 Factory FE 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=1)
        h.try_build("Terran Refinery", 100, max_count=1)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.minerals() >= 500 and not h.has("Terran Command Center", completed_only=False):
            h.expand(cost=400)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=4)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Siege Tank Siege Mode"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvP_siegeexpand.py"] = '''"""TvP Siege Expand: Barracks->Factory->EngineeringBay->Siege Tanks"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvP Siege Expand 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=18)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=1)
        h.try_build("Terran Refinery", 100, max_count=1)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
            h.try_build("Terran Engineering Bay", 125, max_count=1)
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=6)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Siege Tank Siege Mode"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_1fact.py"] = '''"""TvU 1 Factory: Barracks->SupplyDepot->Factory->Marines+Tanks"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU 1 Factory 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=16)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=2)
        h.try_build("Terran Refinery", 100, max_count=1)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_bunkering.py"] = '''"""TvU Bunkering: Barracks->Bunker x2->Marines"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Bunkering 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=14)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=2)
        if h.has("Terran Barracks"):
            h.try_build("Terran Bunker", 100, max_count=2)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        h.attack_with(["Terran Marine"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_fd.py"] = '''"""TvU FD: Barracks->Medic/Marine->Factory->Starport->Dropship+Vultures"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU FD 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=18)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=2)
        h.try_build("Terran Refinery", 100, max_count=1)
        if h.has("Terran Barracks"):
            h.try_build("Terran Academy", 150, max_count=1)
            h.try_build("Terran Factory", 200, max_count=1, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Starport", 150, max_count=1, gas_cost=100)
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=8)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25, max_count=4)
        h.try_train("Terran Factory", "Terran Vulture", 75)
        if h.has("Terran Starport"):
            h.try_train("Terran Starport", "Terran Dropship", 100, gas_cost=100)
        h.attack_with(["Terran Marine", "Terran Medic", "Terran Vulture"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_mechanic.py"] = '''"""TvU Mechanic: Factory x2->Armory->Tanks+Vultures+Goliaths"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Mechanic 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=18)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=1)
        h.try_build("Terran Refinery", 100, max_count=2)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
            h.try_build("Terran Armory", 100, max_count=1, gas_cost=50)
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=4)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        if h.has("Terran Armory"):
            h.try_train("Terran Factory", "Terran Goliath", 100, gas_cost=50)
        h.try_train("Terran Factory", "Terran Vulture", 75)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Goliath", "Terran Vulture"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_sk.py"] = '''"""TvU SK Terran: Barracks x3->Academy->Marines+Medics+SciVessel"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU SK Terran 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=3)
        h.try_build("Terran Refinery", 100, max_count=1)
        if h.has("Terran Barracks"):
            h.try_build("Terran Academy", 150, max_count=1)
            h.try_build("Terran Factory", 200, max_count=1, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Starport", 150, max_count=1, gas_cost=100)
        if h.has("Terran Starport"):
            h.try_build("Terran Control Tower", 50, max_count=1, gas_cost=50)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        if h.has("Terran Academy"):
            h.try_train("Terran Barracks", "Terran Medic", 50, gas_cost=25)
        if h.has("Terran Control Tower"):
            h.try_train("Terran Starport", "Terran Science Vessel", 100, gas_cost=225, max_count=2)
        h.attack_with(["Terran Marine", "Terran Medic", "Terran Science Vessel"], min_army=10)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_late_mechanic.py"] = '''"""TvU Late Mechanic: Factory->Armory->SciFacility->Battlecruiser"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Late Mechanic 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        h.try_build("Terran Barracks", 150, max_count=1)
        h.try_build("Terran Refinery", 100, max_count=2)
        if h.has("Terran Barracks"):
            h.try_build("Terran Factory", 200, max_count=2, gas_cost=100)
        if h.has("Terran Factory"):
            h.try_build("Terran Machine Shop", 50, max_count=2, gas_cost=25)
            h.try_build("Terran Armory", 100, max_count=1, gas_cost=50)
            h.try_build("Terran Starport", 150, max_count=1, gas_cost=100)
        if h.has("Terran Armory") and h.has("Terran Starport"):
            h.try_build("Terran Science Facility", 100, max_count=1, gas_cost=150)
        if h.has("Terran Science Facility"):
            h.try_build("Terran Physics Lab", 50, max_count=1, gas_cost=50)
        h.try_train("Terran Barracks", "Terran Marine", 50, max_count=4)
        h.try_train("Terran Factory", "Terran Siege Tank Tank Mode", 150, gas_cost=100)
        if h.has("Terran Physics Lab"):
            h.try_train("Terran Starport", "Terran Battlecruiser", 400, gas_cost=300)
        h.attack_with(["Terran Marine", "Terran Siege Tank Tank Mode",
                       "Terran Battlecruiser"], min_army=2)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["TvU_natural_expand.py"] = '''"""TvU Natural Expand: CC expand->Barracks->Marines"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("TvU Natural Expand 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=20)
        h.try_build("Terran Supply Depot", 100, max_count=99, cooldown=12.0)
        if h.minerals() >= 500 and not h.has("Terran Command Center", completed_only=False):
            h.expand(cost=400)
        h.try_build("Terran Barracks", 150, max_count=3)
        h.try_train("Terran Barracks", "Terran Marine", 50)
        h.attack_with(["Terran Marine"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

# ═══════════════════════════════════════════════════════════════════════════
# ZERG
# ═══════════════════════════════════════════════════════════════════════════

SCRIPTS["ZvZ_9poolspire.py"] = '''"""ZvZ 9 Pool Spire: 9Pool->Extractor->Lair->Spire->Mutas"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvZ 9 Pool Spire 시작")
    while not ctx._stopped:
        h.manage_workers(desired=12)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            h.try_train_larva("Zerg Zergling", 50)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Spire", 200, max_count=1, gas_cost=200)
        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Mutalisk"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvT_3hatchmuta.py"] = '''"""ZvT 3 Hatch Muta: Hatch x3->Pool->Extractor->Lair->Spire->Mutas"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvT 3 Hatch Muta 시작")
    while not ctx._stopped:
        h.manage_workers(desired=18)
        # 해처리 2개 더 건설 (앞마당 포함)
        if h.count_of("Zerg Hatchery", completed_only=False) < 2:
            h.try_build("Zerg Hatchery", 300, max_count=2)
        if h.minerals() >= 300 and h.count_of("Zerg Hatchery", completed_only=False) < 3:
            h.expand(cost=300)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Spire", 200, max_count=1, gas_cost=200)
        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Mutalisk"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvT_9poollurker.py"] = '''"""ZvT 9 Pool Lurker: 9Pool->Lair->HydraliskDen->Lurkers"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvT 9 Pool Lurker 시작")
    while not ctx._stopped:
        h.manage_workers(desired=14)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            h.try_train_larva("Zerg Zergling", 50, max_count=6)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Hydralisk Den", 100, max_count=1, gas_cost=50)
        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25)
            # 히드라 → 러커 변이
            h.try_morph("Zerg Hydralisk", "Zerg Lurker", 50, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Lurker", "Zerg Zergling"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvP_9734.py"] = '''"""ZvP 9734: Pool->HydraliskDen->Hydralisks+Zerglings"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvP 9734 시작")
    while not ctx._stopped:
        h.manage_workers(desired=16)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            h.try_train_larva("Zerg Zergling", 50)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Hydralisk Den", 100, max_count=1, gas_cost=50)
        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Hydralisk", "Zerg Zergling"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_9poolspeed.py"] = '''"""ZvU 9 Pool Speed: 9Pool->Zergling Speed->Zerglings"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU 9 Pool Speed 시작")
    while not ctx._stopped:
        h.manage_workers(desired=9)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Zergling"], min_army=12)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_3hatch.py"] = '''"""ZvU 3 Hatch: Hatch x3->Pool->Zerglings+Drones"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU 3 Hatch 시작")
    while not ctx._stopped:
        h.manage_workers(desired=20)
        if h.count_of("Zerg Hatchery", completed_only=False) < 2:
            h.try_build("Zerg Hatchery", 300, max_count=2)
        if h.minerals() >= 300 and h.count_of("Zerg Hatchery", completed_only=False) < 3:
            h.expand(cost=300)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Zergling"], min_army=12)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_ling_lurker.py"] = '''"""ZvU Ling Lurker: Pool->Lair->HydraliskDen->Lurkers+Zerglings"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Ling Lurker 시작")
    while not ctx._stopped:
        h.manage_workers(desired=16)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            h.try_train_larva("Zerg Zergling", 50, max_count=8)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Hydralisk Den", 100, max_count=1, gas_cost=50)
        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25, max_count=8)
            h.try_morph("Zerg Hydralisk", "Zerg Lurker", 50, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Lurker", "Zerg Zergling"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_muta_micro.py"] = '''"""ZvU Muta Micro: Pool->Extractor->Lair->Spire->Mutas"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Muta Micro 시작")
    while not ctx._stopped:
        h.manage_workers(desired=14)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Spire", 200, max_count=1, gas_cost=200)
        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Mutalisk"], min_army=8)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_defiler.py"] = '''"""ZvU Defiler: Pool->Lair->Hive->DefilerMound->Defilers+Ultralisk"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Defiler 시작")
    while not ctx._stopped:
        h.manage_workers(desired=20)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=2)
            h.try_train_larva("Zerg Zergling", 50, max_count=8)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_morph("Zerg Lair", "Zerg Hive", 200, gas_cost=150)
        if h.has("Zerg Hive"):
            h.try_build("Zerg Defiler Mound", 100, max_count=1, gas_cost=100)
            h.try_build("Zerg Ultralisk Cavern", 150, max_count=1, gas_cost=200)
        if h.has("Zerg Defiler Mound"):
            h.try_train_larva("Zerg Defiler", 50, gas_cost=150, max_count=4)
        if h.has("Zerg Ultralisk Cavern"):
            h.try_train_larva("Zerg Ultralisk", 200, gas_cost=200)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Ultralisk", "Zerg Zergling", "Zerg Defiler"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_queen_lurker.py"] = '''"""ZvU Queen Lurker: Pool->Lair->QueensNest->HydraliskDen->Queens+Lurkers"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Queen Lurker 시작")
    while not ctx._stopped:
        h.manage_workers(desired=16)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            h.try_train_larva("Zerg Zergling", 50, max_count=6)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Queens Nest", 150, max_count=1, gas_cost=100)
            h.try_build("Zerg Hydralisk Den", 100, max_count=1, gas_cost=50)
        if h.has("Zerg Queens Nest"):
            h.try_train_larva("Zerg Queen", 100, gas_cost=100, max_count=4)
        if h.has("Zerg Hydralisk Den"):
            h.try_train_larva("Zerg Hydralisk", 75, gas_cost=25)
            h.try_morph("Zerg Hydralisk", "Zerg Lurker", 50, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Lurker", "Zerg Queen", "Zerg Zergling"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

SCRIPTS["ZvU_natural_expand.py"] = '''"""ZvU Natural Expand: Hatch expand->Pool->Zerglings"""
''' + HEADER + '''
def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Natural Expand 시작")
    while not ctx._stopped:
        h.manage_workers(desired=18)
        if h.minerals() >= 300 and h.count_of("Zerg Hatchery", completed_only=False) < 2:
            h.expand(cost=300)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Zergling"], min_army=12)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
'''

# ─── 파일 쓰기 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    written = []
    for filename, content in SCRIPTS.items():
        path = os.path.join(SCRIPTS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(filename)
    print(f"완료: {len(written)}개 스크립트 재작성")
    for fn in written:
        print(f"  ✓ {fn}")
