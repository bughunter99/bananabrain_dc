"""PvU Dark Templar: Gate->Cyber->Citadel->Templar Archives->DTs"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
