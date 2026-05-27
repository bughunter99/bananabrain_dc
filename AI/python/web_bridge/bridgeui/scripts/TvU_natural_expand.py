"""TvU Natural Expand: CC expand->Barracks->Marines"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
