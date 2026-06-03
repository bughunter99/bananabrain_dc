from __future__ import annotations

from typing import Type

from .base import BaseStrategy, StrategyContext
from .protoss_strategy import ProtossStrategy
from .terran_strategy import TerranStrategy
from .zerg_strategy import ZergStrategy
from .strategy_units import CANONICAL_STRATEGY_UNITS, normalize_strategy_unit_name


class StrategySelector:
    def __init__(self) -> None:
        self._strategy_types = {
            "Protoss": ProtossStrategy,
            "Terran": TerranStrategy,
            "Zerg": ZergStrategy,
            "ProtossStrategy": ProtossStrategy,
            "TerranStrategy": TerranStrategy,
            "ZergStrategy": ZergStrategy,
        }

    def available_units(self):
        return list(CANONICAL_STRATEGY_UNITS)

    def select(self, context: StrategyContext) -> BaseStrategy:
        strategy_name = normalize_strategy_unit_name(context.strategy_name)
        if strategy_name == "ProtossStrategy":
            strategy_type = ProtossStrategy
        elif strategy_name == "TerranStrategy":
            strategy_type = TerranStrategy
        elif strategy_name == "ZergStrategy":
            strategy_type = ZergStrategy
        else:
            self_race = str(context.state.get("self_race") or context.payload.get("race") or context.payload.get("self_race") or "Unknown")
            strategy_type = self._strategy_types.get(self_race, ProtossStrategy)
        return strategy_type(context)
