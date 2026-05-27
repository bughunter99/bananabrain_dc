"""TvU SK Terran: Barracks x3->Academy->Marines+Medics+SciVessel"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

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
