"""TvU FD: Barracks->Medic/Marine->Factory->Starport->Dropship+Vultures"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
