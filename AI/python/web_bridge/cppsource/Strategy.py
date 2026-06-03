"""Game strategy selection and execution.

C++ equivalent: Strategy.cpp/Strategy.h

Base class for race-specific strategies with:
- Opening selection
- Stage determination (minerals, wall, proxy)
- Rush defense
- Unit attack coordination
"""


from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Set, Tuple
from enum import Enum


class StageType(Enum):
    """Defense stage types."""
    MINERALS = "minerals"
    BLOCK_CHOKEPOINT = "block_chokepoint"
    BLOCK_CHOKEPOINT_DARK_TEMPLAR = "block_chokepoint_dt"
    PROXY = "proxy"
    WALL = "wall"


@dataclass
class Strategy:
    """Base strategy class for all races."""
    
    _mode: str = ""
    _opening: str = ""
    _late_game_strategy: str = ""
    _stage_type: StageType = StageType.MINERALS
    _stage_position: Tuple[int, int] = (0, 0)
    _attacking: bool = False
    _maxed_out: bool = False
    
    def pick_strategy(self, is_1v1: bool) -> None:
        """Select strategy based on game conditions."""
        pass
    
    def mode(self) -> str:
        """Get current strategy mode."""
        return self._mode
    
    def opening(self) -> str:
        """Get opening strategy name."""
        return self._opening
    
    def late_game_strategy(self) -> str:
        """Get late game strategy name."""
        return self._late_game_strategy
    
    def frame(self) -> None:
        """Execute strategy frame logic."""
        self.frame_inner()
    
    def frame_inner(self) -> None:
        """Override in subclasses for strategy logic."""
        pass
    
    def apply_result(self, win: bool) -> None:
        """Record game result for strategy selection."""
        pass
    
    def update_stage(self) -> None:
        """Update stage (minerals, wall, proxy, etc)."""
        pass
    
    def is_defending_rush(self) -> bool:
        """Check if currently defending against rush."""
        return False
    
    def is_contained(self) -> bool:
        """Check if contained/blocked by opponent."""
        return False
    
    def dark_templars_without_mobile_detection(self) -> bool:
        """Check if opponent has DTs without mobile detection."""
        return False
    
    def expect_lurkers(self) -> bool:
        """Predict if opponent will use lurkers."""
        return False
    
    def expect_dark_templars(self) -> bool:
        """Predict if opponent will use dark templars."""
        return False


@dataclass
class ProtossStrategy(Strategy):
    """Protoss-specific strategy."""
    
    # Common PvZ openings
    PVZ_SAIRDТ = "PvZ_sairdt"
    PVZ_10_12_GATE = "PvZ_10/12gate"
    PVZ_1BASE_SPEED_ZEAL = "PvZ_1basespeedzeal"
    PVZ_2BASE_SPEED_ZEAL = "PvZ_2basespeedzeal"
    PVZ_BISU = "PvZ_bisu"
    
    # Common PvT openings
    PVT_2GATE = "PvT_2gate"
    PVT_FFE = "PvT_ffe"
    PVT_1012GATE = "PvT_10/12gate"
    
    # Common PvP openings
    PVP_1GATE = "PvP_1gate"
    PVP_2GATE = "PvP_2gate"
    PVP_PROXY_GATE = "PvP_proxygate"


@dataclass
class TerranStrategy(Strategy):
    """Terran-specific strategy."""
    
    # Common TvZ openings
    TVZ_2RAXFE = "TvZ_2raxfe"
    TVZ_1RAXFE = "TvZ_1raxfe"
    TVZ_3RAX = "TvZ_3rax"
    TVZ_WALL = "TvZ_wall"
    
    # Common TvT openings
    TVT_STANDARD = "TvT_standard"
    TVT_EXPAND = "TvT_expand"
    
    # Common TvP openings
    TVP_2RAXFE = "TvP_2raxfe"
    TVP_EXPAND = "TvP_expand"


@dataclass
class ZergStrategy(Strategy):
    """Zerg-specific strategy."""
    
    # Common ZvP openings
    ZVP_POOL = "ZvP_pool"
    ZVP_HATCHERY = "ZvP_hatchery"
    ZVP_MUTALISK = "ZvP_mutalisk"
    
    # Common ZvT openings
    ZVT_POOL = "ZvT_pool"
    ZVT_HATCHERY = "ZvT_hatchery"
    ZVT_LING_FLOOD = "ZvT_lingflood"
    
    # Common ZvZ openings
    ZVZ_POOL = "ZvZ_pool"
    ZVZ_HATCHERY = "ZvZ_hatchery"


from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CANONICAL_STRATEGY_UNITS = ["ProtossStrategy", "TerranStrategy", "ZergStrategy"]


def normalize_strategy_unit_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "auto":
        return "auto"
    return text


@dataclass
class StrategyDecision:
    self_race: str = "Unknown"
    enemy_race: str = "Unknown"
    opening: str = "auto"
    mode: str = "Opening"
    late_game_strategy: str = "none"
    placement_plan: Dict[str, Any] = field(default_factory=dict)
    source: str = "Strategy"
    strategy_unit: str = "Strategy"
    build_requests: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StrategyContext:
    service: Any
    state: Dict[str, Any]
    payload: Dict[str, Any]
    event: Dict[str, Any]
    strategy_name: str = "auto"
    result_store: Any = None


class Strategy:
    def __init__(self, context: Optional[StrategyContext] = None) -> None:
        self._context = context
        self._opening = "auto"
        self._mode = "Opening"
        self._late_game_strategy = "none"
        self._decision = StrategyDecision(source=self.__class__.__name__)
        self.self_race = "Unknown"
        self.enemy_race = "Unknown"

    def pick_strategy(self, is_1v1: bool) -> None:
        if self._context is not None:
            self.self_race = str(self._context.state.get("self_race") or self._context.payload.get("race") or "Unknown")
            self.enemy_race = str(self._context.state.get("enemy_race") or self._context.payload.get("enemy_race") or "Unknown")
            self._mode = str(self._context.state.get("strategy_mode") or self._context.payload.get("mode") or self._mode)
            self._opening = str(self._context.state.get("strategy_opening") or self._opening)
        self._decision.self_race = self.self_race
        self._decision.enemy_race = self.enemy_race
        self._decision.opening = self._opening
        self._decision.mode = self._mode
        self._decision.late_game_strategy = self._late_game_strategy

    def mode(self) -> str:
        return self._mode

    def opening(self) -> str:
        return self._opening

    def late_game_strategy(self) -> str:
        return self._late_game_strategy

    def frame_inner(self) -> None:
        self._decision.self_race = self.self_race
        self._decision.enemy_race = self.enemy_race
        self._decision.opening = self._opening
        self._decision.mode = self._mode
        self._decision.late_game_strategy = self._late_game_strategy
        if not self._decision.placement_plan:
            self._decision.placement_plan = self._default_placement_plan()
        self._decision.source = self.__class__.__name__
        self._decision.strategy_unit = self.__class__.__name__

    def set_placement_plan(self, plan: Dict[str, Any]) -> None:
        self._decision.placement_plan = dict(plan or {})

    def add_build_request(self, request: Dict[str, Any]) -> None:
        if request:
            self._decision.build_requests.append(dict(request))

    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "default",
            "expand_priority": "natural",
            "wall_policy": "none",
            "proxy_policy": "none",
            "defensive_anchor": "main_ramp",
        }

    def decision(self) -> StrategyDecision:
        return self._decision


class ProtossStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "protoss_default",
            "expand_priority": "natural",
            "wall_policy": "forge_fast_expand",
            "proxy_policy": "pylon_probe",
            "defensive_anchor": "main_ramp",
        }


class TerranStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "terran_default",
            "expand_priority": "natural",
            "wall_policy": "bunker_ramp",
            "proxy_policy": "none",
            "defensive_anchor": "main_ramp",
        }


class ZergStrategy(Strategy):
    def _default_placement_plan(self) -> Dict[str, Any]:
        return {
            "plan": "zerg_default",
            "expand_priority": "natural",
            "wall_policy": "choke_spine",
            "proxy_policy": "none",
            "defensive_anchor": "main_hatch",
        }


class StrategySelector:
    def select(self, context: StrategyContext) -> Strategy:
        strategy_name = normalize_strategy_unit_name(context.strategy_name)
        if strategy_name == "TerranStrategy":
            return TerranStrategy(context)
        if strategy_name == "ZergStrategy":
            return ZergStrategy(context)
        return ProtossStrategy(context)
