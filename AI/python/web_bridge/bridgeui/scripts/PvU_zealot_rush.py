"""PvU Zealot Rush: Pylon->Gate x2->Zealots (no gas)"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _helpers import StrategyHelper

def run(ctx):
    h = StrategyHelper(ctx)
    if not h.setup():
        return
    ctx.log("PvU Zealot Rush 시작")
    while not ctx._stopped:
        h.manage_supply(threshold=2)
        h.manage_workers(desired=10)
        h.try_build("Protoss Pylon", 100, max_count=99, cooldown=12.0)
        h.try_build("Protoss Gateway", 150, max_count=2)
        h.try_train("Protoss Gateway", "Protoss Zealot", 100)
        h.attack_with(["Protoss Zealot"], min_army=6)
        ctx.gather_idle_workers()
        ctx.wait(0.25)
