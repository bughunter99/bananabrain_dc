"""ZvU 9 Pool Speed: 9Pool->Zergling Speed->Zerglings"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("ZvU 9 Pool Speed 시작")
    while not ctx._stopped:
        h.manage_workers(desired=9)
        h.try_build("Zerg Spawning Pool", 200, max_count=1)
        if h.has("Zerg Spawning Pool"):
            h.try_train_larva("Zerg Zergling", 50)
        h.manage_supply(threshold=2)
        h.attack_with(["Zerg Zergling"], min_army=12)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
