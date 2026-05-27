"""TvU Mechanic: Factory x2->Armory->Tanks+Vultures+Goliaths"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
