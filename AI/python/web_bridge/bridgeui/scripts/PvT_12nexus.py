"""PvT 12 Nexus: Gate->expand->Cyber->Dragoons"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
