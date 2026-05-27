"""ZvT 3 Hatch Muta: Hatch x3->Pool->Extractor->Lair->Spire->Mutas"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvT 3 Hatch Muta 시작")
    while not ctx._stopped:
        h.manage_workers(desired=18)
        # 해처리 2개 더 건설 (앞마당 포함)
        if h.count_of("Zerg Hatchery", completed_only=False) < 2:
            h.try_build("Zerg Hatchery", 300, max_count=2)
        if h.minerals() >= 300 and h.count_of("Zerg Hatchery", completed_only=False) < 3:
            h.expand(cost=300)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_build("Zerg Extractor", 50, max_count=1)
            if h.has("Zerg Extractor"):
                h.try_morph("Zerg Hatchery", "Zerg Lair", 150, gas_cost=100)
        if h.has("Zerg Lair"):
            h.try_build("Zerg Spire", 200, max_count=1, gas_cost=200)
        if h.has("Zerg Spire"):
            h.try_train_larva("Zerg Mutalisk", 100, gas_cost=100)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Mutalisk"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
