from __future__ import annotations

CANONICAL_STRATEGY_UNITS = [
    "ProtossStrategy",
    "TerranStrategy",
    "ZergStrategy",
]

STRATEGY_UNIT_ALIASES = {
    "auto": "auto",
    "protoss": "ProtossStrategy",
    "terran": "TerranStrategy",
    "zerg": "ZergStrategy",
    "protossstrategy": "ProtossStrategy",
    "terranstrategy": "TerranStrategy",
    "zergstrategy": "ZergStrategy",
    "protossstrategy.cpp": "ProtossStrategy",
    "terranstrategy.cpp": "TerranStrategy",
    "zergstrategy.cpp": "ZergStrategy",
}


def normalize_strategy_unit_name(raw_name: str) -> str:
    key = str(raw_name or "auto").strip().lower()
    return STRATEGY_UNIT_ALIASES.get(key, key)
