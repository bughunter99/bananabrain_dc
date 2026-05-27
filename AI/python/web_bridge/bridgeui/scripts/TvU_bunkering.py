"""TvU Bunkering: Barracks->Bunker x2->Marines"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
