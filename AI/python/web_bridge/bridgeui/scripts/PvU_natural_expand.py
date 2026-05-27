"""PvU Natural Expand: expand->Gate->Pylon->Zealots"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
