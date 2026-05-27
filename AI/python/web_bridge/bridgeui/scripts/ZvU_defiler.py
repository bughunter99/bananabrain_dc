"""ZvU Defiler: Pool->Lair->Hive->DefilerMound->Defilers+Ultralisk"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU Defiler 시작")
    while not ctx._stopped:
        h.manage_workers(desired=20)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=2)
            h.try_train_larva("Zerg Zergling", 50, max_count=8)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_morph("Zerg Lair", "Zerg Hive", 200, gas_cost=150)
        if h.has("Zerg Hive"):
            h.try_build("Zerg Defiler Mound", 100, max_count=1, gas_cost=100)
            h.try_build("Zerg Ultralisk Cavern", 150, max_count=1, gas_cost=200)
        if h.has("Zerg Defiler Mound"):
            h.try_train_larva("Zerg Defiler", 50, gas_cost=150, max_count=4)
        if h.has("Zerg Ultralisk Cavern"):
            h.try_train_larva("Zerg Ultralisk", 200, gas_cost=200)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Ultralisk", "Zerg Zergling", "Zerg Defiler"], min_army=4)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
