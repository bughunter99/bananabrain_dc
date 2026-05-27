"""PvU Reaver Drop: Gate->Cyber->Robo->Shuttle->Reaver"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
