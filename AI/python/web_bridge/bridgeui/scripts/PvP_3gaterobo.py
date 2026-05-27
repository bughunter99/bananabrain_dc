"""PvP 3-Gate Robo: Pylon->Gate x3->Robo->Dragoons+Shuttle"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
