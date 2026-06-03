from __future__ import annotations

"""Single-file BananaBrain-style strategy policy.

This is the customization point for user-editable strategy decisions. The goal
is to keep the strategic logic in one Python file so it can be tuned without
recompiling the DLL.
"""

import threading
import time
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from cppsource.BaseState import BaseState
from cppsource.Configuration import Configuration
from cppsource.Strategy import CANONICAL_STRATEGY_UNITS, StrategyContext, StrategySelector, normalize_strategy_unit_name
from cppsource.OpeningLoader import opening_catalog, reload_opening_modules
from cppsource.Information import InformationManager
from cppsource.BuildingPlacement import BuildingPlacementManager
from cppsource.Tactics import TacticsManager
from cppsource.OpponentModel import OpponentModel
from cppsource.PathFinder import PathFinder
from cppsource.Results import ResultStore
from cppsource.Grids import RoomGrid, WalkabilityGrid
from cppsource.Macro import BuildingManager, SpendingManager


class BWEMMapAdapter:
    def __init__(self) -> None:
        self._snapshot: Dict[str, Any] = {}
        self._initialized = False
        self._found_start_locations = False
        self._automatic_path_analysis = False

    def Initialize(self, broodwar_ptr: Optional[Any] = None) -> None:
        if isinstance(broodwar_ptr, dict):
            self._snapshot = dict(broodwar_ptr)
        elif hasattr(broodwar_ptr, "get"):
            try:
                self._snapshot = dict(broodwar_ptr)  # type: ignore[arg-type]
            except Exception:
                self._snapshot = {}
        else:
            self._snapshot = {}

        self._initialized = True
        BaseState.Instance().init_bases(self._snapshot)

    def FindBasesForStartingLocations(self) -> None:
        if not self._initialized:
            self.Initialize({})
        BaseState.Instance().update_base_information(self._snapshot)
        self._found_start_locations = True

    def EnableAutomaticPathAnalysis(self) -> None:
        if not self._initialized:
            self.Initialize({})
        PathFinder.Instance().init(self._snapshot)
        self._automatic_path_analysis = True

    def snapshot(self) -> Dict[str, Any]:
        return dict(self._snapshot)

    def initialized(self) -> bool:
        return self._initialized


bwem_map = BWEMMapAdapter()
configuration = Configuration.Instance()
base_state = BaseState.Instance()
path_finder = PathFinder.Instance()
opponent_model = OpponentModel.Instance()
building_placement_manager = BuildingPlacementManager.Instance()
tactics_manager = TacticsManager.Instance()
result_store = ResultStore()
walkability_grid = WalkabilityGrid.Instance()
room_grid = RoomGrid.Instance()
building_manager = BuildingManager.Instance()
spending_manager = SpendingManager.Instance()


class WorkerManagerAdapter:
    def __init__(self) -> None:
        self._optimal_mining_data: Dict[int, Dict[str, Any]] = {}

    def init_optimal_mining_data(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        snapshot = snapshot or {}
        own_units = [unit for unit in (snapshot.get("own_units") or []) if isinstance(unit, dict)]
        minerals = [field for field in (snapshot.get("mineral_fields") or []) if isinstance(field, dict)]
        mineral_positions = [(int(field.get("x") or 0), int(field.get("y") or 0)) for field in minerals]
        self._optimal_mining_data.clear()

        if not mineral_positions:
            return

        for unit in own_units:
            unit_type = str(unit.get("type") or "")
            if unit_type not in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}:
                continue
            unit_id = int(unit.get("id") or 0)
            if unit_id <= 0:
                continue
            worker_x = int(unit.get("x") or 0)
            worker_y = int(unit.get("y") or 0)
            nearest = min(mineral_positions, key=lambda pos: abs(pos[0] - worker_x) + abs(pos[1] - worker_y))
            self._optimal_mining_data[unit_id] = {"target_x": nearest[0], "target_y": nearest[1]}


worker_manager = WorkerManagerAdapter()


@dataclass(frozen=True)
class StrategyChoice:
    self_race: str
    enemy_race: str
    is_1v1: bool
    opening: str
    mode: str
    late_game_strategy: str = "none"
    placement_plan: Dict[str, Any] = field(default_factory=dict)
    strategy_unit: str = ""
    build_requests: list[Dict[str, Any]] = field(default_factory=list)
    worker_cap: int = -1
    opening_source: str = "auto"
    mode_source: str = "auto"
    strategy_source: str = "auto"


class BananaBrain:
    def __init__(self, bridge_service) -> None:
        self._service = bridge_service
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._subscriber_id: Optional[int] = None
        self._queue = None
        self._last_decision: Optional[StrategyChoice] = None
        self._last_publish_at = 0.0
        self._publish_interval_sec = 0.5
        self._strategy_name = "auto"
        self._mode_override: Optional[str] = None
        self._selector = StrategySelector()
        self.max_duration_ = 0
        self.frame_zero_duration_ = 0
        self.initialized_ = False
        self.is_1v1_ = False
        self.is_ffa_ = False
        self.strategy_: Optional[Any] = None
        self._current_frame_event: Optional[Dict[str, Any]] = None

        # A single editable strategy catalog for users.
        self._openings: Dict[str, Dict[Tuple[str, bool], str]] = {
            "Protoss": {
                ("Zerg", True): "PvZ_10/12gate",
                ("Zerg", False): "PvZ_bisu",
                ("Terran", True): "PvT_12nexus",
                ("Terran", False): "PvT_1012Gate",
                ("Protoss", True): "PvP_3gaterobo",
                ("Protoss", False): "PvP_4gategoon",
                ("Unknown", True): "PvU_forge",
                ("Unknown", False): "PvU_1012Gate",
            },
            "Terran": {
                ("Zerg", True): "TvZ_1raxfe",
                ("Zerg", False): "TvZ_2rax",
                ("Terran", True): "TvT_1factfe",
                ("Terran", False): "TvT_2factvults",
                ("Protoss", True): "TvP_siegeexpand",
                ("Protoss", False): "TvP_2raxbiomech",
                ("Unknown", True): "TvU_1fact",
                ("Unknown", False): "TvU_2rax",
            },
            "Zerg": {
                ("Zerg", True): "ZvZ_9poolspire",
                ("Zerg", False): "ZvZ_10hatch",
                ("Terran", True): "ZvT_3hatchmuta",
                ("Terran", False): "ZvT_9PoolLurker",
                ("Protoss", True): "ZvP_9734",
                ("Protoss", False): "ZvP_2HatchHydra",
                ("Unknown", True): "ZvU_9poolspeed",
                ("Unknown", False): "ZvU_11Pool",
            },
        }

        self._opening_overrides: Dict[str, str] = {}
        self._last_applied_frame: int = -1
        self._current_opening: Optional[str] = None
        self._result_store = ResultStore()
        self._economy_bootstrapped = False
        self._worker_targets: Dict[int, tuple[int, int]] = {}
        self._worker_order_at: Dict[tuple[str, int], int] = {}
        self._last_frame_context: Dict[str, Any] = {}

        # Overlord scouting state
        self._all_start_tiles: list = []        # [(tx, ty), ...] all start locations
        self._self_start_tile: Optional[tuple] = None
        self._scout_targets: list = []          # [(tx, ty)] unexplored starts (excluding own)
        self._scout_assigned: Dict[int, tuple] = {}  # overlord_id -> (tx, ty) assigned target

    def start(self, strategy_name: str = "auto") -> Dict[str, Any]:
        requested_strategy = normalize_strategy_unit_name(strategy_name)
        with self._lock:
            if self._running:
                self._strategy_name = requested_strategy
                return {
                    "ok": True,
                    "running": True,
                    "last_decision": self._decision_dict_locked(),
                    "selected_strategy": self._strategy_name,
                    "selected_strategy_unit": self._strategy_name,
                }
            self._strategy_name = requested_strategy
            self._subscriber_id, self._queue = self._service.subscribe()
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="BananaBrain")
            self._thread.start()

        self._service.emit_local_event(
            "strategy_started",
            {"runtime": "banana_brain_policy", "strategy": self._strategy_name},
        )
        return {
            "ok": True,
            "running": True,
            "last_decision": self._decision_dict_locked(),
            "selected_strategy": self._strategy_name,
            "selected_strategy_unit": self._strategy_name,
        }

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self._running = False
            subscriber_id = self._subscriber_id
            self._subscriber_id = None
            self._queue = None
        if subscriber_id is not None:
            self._service.unsubscribe(subscriber_id)
        self._service.emit_local_event("strategy_stopped", {"runtime": "banana_brain_policy"})
        return {"ok": True, "running": False}

    def _emit_callback(self, callback_name: str, payload: Dict[str, Any]) -> None:
        self._service.emit_local_event(
            "callback_invoked",
            {
                "callback": callback_name,
                "payload": payload,
            },
        )

    def onStart(self) -> None:
        snapshot = self._service.snapshot().get("state") or {}
        ok = True

        if bool(snapshot.get("is_replay")):
            self.initialized_ = True
            return

        self.is_1v1_ = int(snapshot.get("enemy_count") or 0) == 1 and int(snapshot.get("ally_count") or 0) == 0
        if not self.is_1v1_:
            game_type = str(snapshot.get("game_type") or snapshot.get("gameType") or "").lower()
            self.is_ffa_ = game_type in {"free_for_all", "team_free_for_all", "ffa", "tffa"}

        if ok:
            configuration.init()
            configuration.update_from_snapshot(snapshot)

            random.seed(int(time.time()))

            bwem_map.Initialize(snapshot)
            bwem_map.FindBasesForStartingLocations()
            bwem_map.EnableAutomaticPathAnalysis()
            base_state.init_bases(snapshot)
            path_finder.init(snapshot)
            opponent_model.init()
            building_placement_manager.init()
            spending_manager.init_resource_counters()
            worker_manager.init_optimal_mining_data(snapshot)
            tactics_manager.update(snapshot, int(snapshot.get("frame") or 0))
            walkability_grid.init()
            room_grid.update(snapshot)
            walkability_grid.update(snapshot)

            if self.is_1v1_:
                result_store.reset()

            self.initialized_ = True

    def onEnd(self, isWinner: bool) -> None:
        if not self.initialized_:
            return
        
        won = bool(isWinner)
        
        if self.is_1v1_:
            if self.strategy_:
                self.strategy_.apply_result(won)
            self._result_store.store()
        
        # WorkerManager에서 최적 채굴 데이터 저장
        try:
            WorkerManager.Instance().store_optimal_mining_data()
        except Exception:
            pass
        
        self._emit_callback("onEnd", {"is_winner": won})

    def onFrame(self) -> None:
        """Called every game frame. Core game loop."""
        if not self.initialized_:
            return
        
        # Check if game is paused or self is invalid
        state = self._service.snapshot().get("state") or {}
        if bool(state.get("is_paused")) or state.get("self_race") is None:
            return
        
        frame_count = int(state.get("frame") or 0)
        
        # Send greeting at frame 240 if playing against human
        try:
            if (configuration.human_opponent() and frame_count == 240):
                self.onSendText("glhf")
        except Exception:
            pass
        
        # Performance measurement
        start_time = time.monotonic()
        
        # Core game loop: before -> strategy -> after -> surrender check
        self.before()
        self._strategy_frame_inner(state)
        self.after()
        self.surrender_if_hope_lost()
        
        # Draw performance information if enabled
        try:
            if configuration.draw_enabled():
                self.draw()
                duration_ms = int((time.monotonic() - start_time) * 1000)
                
                if frame_count == 0:
                    self.frame_zero_duration_ = duration_ms
                else:
                    self.max_duration_ = max(duration_ms, self.max_duration_)
                
                # Emit performance metrics
                self._service.emit_local_event(
                    "performance_metrics",
                    {
                        "frame": frame_count,
                        "duration_ms": duration_ms,
                        "max_duration_ms": self.max_duration_,
                        "frame_zero_duration_ms": self.frame_zero_duration_,
                    },
                )
        except Exception:
            pass
        
        self._emit_callback("onFrame", {"frame": frame_count})

    def onSendText(self, text: str) -> None:
        """Send text message through game chat."""
        message = str(text or "").strip()
        self._emit_callback("onSendText", {"text": message})
        if message and self.initialized_:
            self._service.emit_local_event(
                "chat_sent",
                {"text": message, "timestamp": time.time()}
            )
            self._service.send_action(
                {
                    "type": "send_text",
                    "text": message,
                    "source": "banana_brain_policy",
                }
            )

    def onReceiveText(self, player: str, text: str) -> None:
        """Receive text message from player."""
        player_name = str(player or "Unknown")
        message = str(text or "")
        
        if self.initialized_:
            self._service.emit_local_event(
                "chat_received",
                {
                    "player": player_name,
                    "text": message,
                    "timestamp": time.time()
                },
            )
        
        self._emit_callback(
            "onReceiveText",
            {
                "player": player_name,
                "text": message,
            },
        )

    def onPlayerLeft(self, player: str) -> None:
        """Handle player disconnection or leaving."""
        player_name = str(player or "Unknown")
        
        if self.initialized_:
            self._service.emit_local_event(
                "player_event",
                {
                    "event": "left",
                    "player": player_name,
                    "timestamp": time.time()
                },
            )
        
        self._emit_callback("onPlayerLeft", {"player": player_name})

    def onNukeDetect(self, target: Any) -> None:
        """Detect incoming nuclear strike (Terran)."""
        if not self.initialized_:
            return
        
        target_data = dict(target) if isinstance(target, dict) else {"raw": str(target)}
        
        self._service.emit_local_event(
            "threat_detected",
            {
                "type": "nuke",
                "target": target_data,
                "timestamp": time.time()
            },
        )
        
        # Send nuke alert to DLL for emergency response
        self._service.send_action(
            {
                "type": "nuke_detected",
                "target": target_data,
                "source": "banana_brain_policy",
            }
        )
        
        self._emit_callback("onNukeDetect", {"target": target_data})

    def onUnitDiscover(self, unit: Any) -> None:
        """Discover new enemy unit."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        # Invalidate connectivity grid if building
        try:
            unit_type = str(unit_data.get("type") or "")
            if any(x in unit_type for x in ["Nexus", "Hatchery", "Command", "Pylon", "Gateway", "Barracks", "Factory"]):
                room_grid.invalidate()
        except Exception:
            pass
        
        # Update opponent model with discovered unit
        try:
            OpponentModel.Instance().on_unit_discovered(unit_data)
        except Exception:
            pass
        
        # Update information manager
        try:
            InformationManager.Instance().on_unit_discover(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "discover",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitDiscover", {"unit": unit_data})

    def onUnitEvade(self, unit: Any) -> None:
        """Unit evades from attacked position."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        # Update information manager
        try:
            InformationManager.Instance().on_unit_evade(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "evade",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitEvade", {"unit": unit_data})

    def onUnitShow(self, unit: Any) -> None:
        """Unit becomes visible (e.g., cloaked unit revealed)."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        try:
            InformationManager.Instance().on_unit_show(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "show",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitShow", {"unit": unit_data})

    def onUnitHide(self, unit: Any) -> None:
        """Unit becomes invisible (e.g., cloaked)."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        try:
            InformationManager.Instance().on_unit_hide(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "hide",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitHide", {"unit": unit_data})

    def onUnitCreate(self, unit: Any) -> None:
        """New unit created (own or enemy)."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        # Invalidate connectivity grid if building
        try:
            unit_type = str(unit_data.get("type") or "")
            if any(x in unit_type for x in ["Nexus", "Hatchery", "Command", "Pylon", "Gateway", "Barracks", "Factory"]):
                room_grid.invalidate()
        except Exception:
            pass
        
        try:
            InformationManager.Instance().on_unit_create(unit_data)
        except Exception:
            pass
        
        # Update training manager
        try:
            from strategy_runtime import training_manager
            training_manager.on_unit_create(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "create",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitCreate", {"unit": unit_data})

    def onUnitDestroy(self, unit: Any) -> None:
        """Unit destroyed."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        try:
            InformationManager.Instance().on_unit_destroy(unit_data)
        except Exception:
            pass
        
        # Update all managers
        try:
            from strategy_runtime import building_manager, training_manager
            building_manager.on_unit_lost(unit_data)
            training_manager.on_unit_lost(unit_data)
        except Exception:
            pass
        
        try:
            WorkerManager.Instance().on_unit_lost(unit_data)
        except Exception:
            pass
        
        # Invalidate connectivity grid if building
        try:
            unit_type = str(unit_data.get("type") or "")
            if any(x in unit_type for x in ["Nexus", "Hatchery", "Command", "Pylon", "Gateway", "Barracks", "Factory"]):
                room_grid.invalidate()
        except Exception:
            pass
        
        # Update building placement manager
        try:
            BuildingPlacementManager.Instance().on_unit_destroy(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "destroy",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitDestroy", {"unit": unit_data})

    def onUnitMorph(self, unit: Any) -> None:
        """Unit morphs to another type (e.g., Zerg Hatchery -> Lair)."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        try:
            WorkerManager.Instance().on_unit_morph(unit_data)
        except Exception:
            pass
        
        try:
            from strategy_runtime import training_manager
            training_manager.on_unit_morph(unit_data)
        except Exception:
            pass
        
        try:
            InformationManager.Instance().on_unit_morph(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "morph",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitMorph", {"unit": unit_data})

    def onUnitRenegade(self, unit: Any) -> None:
        """Unit changes allegiance (mind control effect)."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        # Worker lost to mind control
        try:
            WorkerManager.Instance().on_unit_lost(unit_data)
        except Exception:
            pass
        
        try:
            InformationManager.Instance().on_unit_renegade(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "renegade",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitRenegade", {"unit": unit_data})

    def onSaveGame(self, gameName: str) -> None:
        """Game is being saved."""
        game_name = str(gameName or "")
        
        if self.initialized_:
            # Store current game state snapshot
            state = self._service.snapshot().get("state") or {}
            self._service.emit_local_event(
                "game_saved",
                {
                    "game_name": game_name,
                    "frame": int(state.get("frame") or 0),
                    "timestamp": time.time()
                },
            )
        
        self._emit_callback("onSaveGame", {"game_name": game_name})

    def onUnitComplete(self, unit: Any) -> None:
        """Unit completes construction/training."""
        if not self.initialized_:
            return
        
        unit_data = dict(unit) if isinstance(unit, dict) else {"raw": str(unit)}
        
        try:
            from strategy_runtime import training_manager
            training_manager.on_unit_complete(unit_data)
        except Exception:
            pass
        
        try:
            InformationManager.Instance().on_unit_complete(unit_data)
        except Exception:
            pass
        
        try:
            SpendingManager.Instance().on_unit_complete(unit_data)
        except Exception:
            pass
        
        try:
            BuildingPlacementManager.Instance().on_unit_complete(unit_data)
        except Exception:
            pass
        
        self._service.emit_local_event(
            "unit_event",
            {
                "event": "complete",
                "unit": unit_data,
                "timestamp": time.time()
            },
        )
        
        self._emit_callback("onUnitComplete", {"unit": unit_data})

    def before(self) -> None:
        """Update game state before strategy execution (C++ BananaBrain::before parity)."""
        state = self._service.snapshot().get("state") or {}
        payload = self._current_frame_event.get("payload") if self._current_frame_event else {}
        frame = int(state.get("frame") or 0)
        
        if frame <= 0:
            return
        
        try:
            # Update unit and building information
            InformationManager.Instance().update_units_and_buildings(state, frame)
            
            # Update grids
            try:
                walkability_grid.update(state)
            except Exception:
                pass
            
            try:
                room_grid.update(state)  # connectivity_grid equivalent
            except Exception:
                pass
            
            # Update base state
            try:
                base_state.update_base_information(state)
            except Exception:
                pass
            
            # Path finder operations
            try:
                PathFinder.Instance().close_small_chokepoints_if_needed()
            except Exception:
                pass
            
            # Unit grid update
            try:
                from strategy_runtime import unit_grid
                unit_grid.update(state)
            except Exception:
                pass
            
            # Training manager initialization
            try:
                from strategy_runtime import training_manager
                training_manager.init_unit_count_map()
            except Exception:
                pass
            
            # Building manager initialization
            try:
                from strategy_runtime import building_manager
                building_manager.init_building_count_map()
                building_manager.init_base_defense_map()
                building_manager.init_upgrade_and_research()
                building_manager.update_supply_requests()
            except Exception:
                pass
            
            # Update information and tactical data
            InformationManager.Instance().update_information(state)
            TacticsManager.Instance().update(state, frame)
            OpponentModel.Instance().update(state)
            
            # Threat grid update
            try:
                from strategy_runtime import threat_grid
                threat_grid.update(state)
            except Exception:
                pass
            
            # Micro manager preparation
            try:
                from strategy_runtime import micro_manager
                micro_manager.prepare_combat()
            except Exception:
                pass
            
            # Worker manager before
            WorkerManager.Instance().before()
            
            # Emit frame context for UI
            frame_context = self._build_frame_context(frame, payload)
            with self._lock:
                self._last_frame_context = frame_context
            self._service.emit_local_event("frame_before", frame_context)
            
            # Overlord scouting
            self._update_overlord_scouting(payload, frame)
            
        except Exception as e:
            self._service.emit_local_event("frame_error", {
                "phase": "before",
                "error": str(e),
                "frame": frame,
            })

    def _strategy_frame_inner(self, state: Dict[str, Any]) -> None:
        """Execute strategy frame logic - called from _handle_frame."""
        if self.strategy_:
            try:
                self.strategy_.frame()
            except Exception as e:
                self._service.emit_local_event(
                    "strategy_error",
                    {"error": str(e), "frame": int(state.get("frame") or 0)},
                )

    def after(self) -> None:
        """Apply actions after strategy execution (C++ BananaBrain::after parity)."""
        state = self._service.snapshot().get("state") or {}
        frame = int(state.get("frame") or 0)
        
        if frame <= 0:
            return
        
        try:
            # Initialize spendable resources
            SpendingManager.Instance().init_spendable()
            WorkerManager.Instance().after()
            
            # Training manager operations
            try:
                from strategy_runtime import training_manager
                training_manager.update_overlord_training()
                if training_manager.worker_production() and not training_manager.worker_cut():
                    training_manager.apply_worker_train_orders()
            except Exception:
                pass
            
            # Building manager pre-upgrade setup
            try:
                from strategy_runtime import building_manager
                building_manager.update_requested_building_count_for_pre_upgrade()
                building_manager.apply_building_requests(priority=True)
                building_manager.apply_upgrades(priority=True)
            except Exception:
                pass
            
            # Training with priority
            try:
                from strategy_runtime import training_manager
                if training_manager.prioritize_training():
                    training_manager.apply_train_orders()
            except Exception:
                pass
            
            # Building manager non-priority operations
            try:
                from strategy_runtime import building_manager
                building_manager.apply_building_requests(priority=False)
                building_manager.apply_upgrades(priority=False)
                building_manager.apply_research()
            except Exception:
                pass
            
            # Training without priority
            try:
                from strategy_runtime import training_manager
                if not training_manager.prioritize_training():
                    training_manager.apply_train_orders()
            except Exception:
                pass
            
            # Worker production cut handling
            try:
                from strategy_runtime import training_manager
                if training_manager.worker_production() and training_manager.worker_cut():
                    training_manager.apply_worker_train_orders()
            except Exception:
                pass
            
            # Building finalization and repair
            try:
                from strategy_runtime import building_manager
                building_manager.repair_damaged_buildings()
                building_manager.continue_unfinished_buildings_without_worker()
            except Exception:
                pass
            
            # Worker and combat management
            WorkerManager.Instance().apply_worker_orders()
            
            try:
                from strategy_runtime import micro_manager
                micro_manager.apply_combat_orders()
            except Exception:
                pass
            
            # Final building cleanup
            try:
                from strategy_runtime import building_manager
                building_manager.cancel_doomed_buildings()
            except Exception:
                pass
            
            # Emit frame after event
            self._service.emit_local_event("frame_after", {"frame": frame})
            
        except Exception as e:
            self._service.emit_local_event("frame_error", {
                "phase": "after",
                "error": str(e),
                "frame": frame,
            })

    def surrender_if_hope_lost(self) -> None:
        """Check if we should surrender (C++ BananaBrain::surrender_if_hope_lost parity)."""
        state = self._service.snapshot().get("state") or {}
        frame = int(state.get("frame") or 0)
        
        # Check every 2 seconds (48 frames at 24 fps)
        if frame <= 0 or (frame % (2 * 24)) != 0:
            return
        
        try:
            own_units = self._parse_unit_entries(state.get("own_units"))
            enemy_units = self._parse_unit_entries(state.get("enemy_units"))
            
            # Resource depot types
            resource_depot_types = {"Protoss_Nexus", "Terran_Command_Center", "Zerg_Hatchery", "Zerg_Lair", "Zerg_Hive"}
            
            # Combat unit types (can fight)
            combat_unit_types = {
                "Protoss_Zealot", "Protoss_Dragoon", "Protoss_Reaver", "Protoss_Dark_Templar", "Protoss_Carrier",
                "Terran_Marine", "Terran_Firebat", "Terran_Vulture", "Terran_Siege_Tank_Tank_Mode", "Terran_Siege_Tank_Siege_Mode",
                "Zerg_Zergling", "Zerg_Hydralisk", "Zerg_Mutalisk", "Zerg_Lurker", 
                "Zerg_Egg", "Zerg_Lurker_Egg", "Zerg_Cocoon"  # Unfinished combat units
            }
            
            # Check if we have any hope:
            for unit in own_units:
                unit_type = str(unit.get("type") or "")
                
                # 1. Resource depot with resources to train workers
                if unit_type in resource_depot_types:
                    try:
                        minerals = int(state.get("minerals") or 0)
                        if minerals >= 50:  # Worker cost
                            return  # We can train workers, so don't surrender
                    except Exception:
                        pass
                
                # 2. Building with units in training queue
                if any(x in unit_type for x in ["Nexus", "Hatchery", "Lair", "Hive", "Command", "Barracks", "Factory", "Starport"]):
                    if unit.get("constructing"):
                        return  # Building is training units, so don't surrender
                
                # 3. Any combat unit
                if unit_type in combat_unit_types:
                    return  # We have combat units, so don't surrender
            
            # Check if enemy has visible attackers
            enemy_attacker_types = {
                "Protoss_Zealot", "Protoss_Dragoon", "Protoss_Reaver", "Protoss_Carrier",
                "Terran_Marine", "Terran_Firebat", "Terran_Vulture", "Terran_Siege_Tank_Tank_Mode", "Terran_Siege_Tank_Siege_Mode",
                "Zerg_Zergling", "Zerg_Hydralisk", "Zerg_Mutalisk", "Zerg_Lurker"
            }
            
            visible_attacker_found = any(
                str(unit.get("type") or "") in enemy_attacker_types
                for unit in enemy_units
            )
            
            # Only surrender if no visible attackers
            if not visible_attacker_found:
                return
            
            # If we reach here: we have no hope AND enemy has visible attackers -> surrender
            self._service.emit_local_event(
                "strategy_surrender",
                {"frame": frame, "reason": "hope_lost"},
            )
            
            # Send GG message if human opponent
            try:
                if configuration.human_opponent():
                    self.onSendText("gg")
            except Exception:
                pass
            
            # Leave game
            self._service.send_action({
                "type": "leave_game",
                "frame": frame,
                "source": "banana_brain_policy",
            })
        except Exception as e:
            self._service.emit_local_event("frame_error", {
                "phase": "surrender_check",
                "error": str(e),
                "frame": frame,
            })

    def draw(self) -> None:
        """Draw debug information (C++ BananaBrain::draw parity)."""
        try:
            self.draw_info()
            
            # Draw base state information
            try:
                base_state.draw()
            except Exception:
                pass
            
            # Draw information manager data
            try:
                InformationManager.Instance().draw()
            except Exception:
                pass
            
            # Draw tactics manager data
            try:
                TacticsManager.Instance().draw()
            except Exception:
                pass
            
            # Draw micro manager data
            try:
                from strategy_runtime import micro_manager
                micro_manager.draw()
            except Exception:
                pass
            
            # Draw building placement manager data
            try:
                BuildingPlacementManager.Instance().draw()
            except Exception:
                pass
            
            # Draw worker manager data
            try:
                WorkerManager.Instance().draw_for_workers()
            except Exception:
                pass
            
            # Commented out in original:
            # room_grid.draw()
            # threat_grid.draw(true)
            
        except Exception as e:
            self._service.emit_local_event("draw_error", {"error": str(e)})

    def draw_info(self) -> None:
        """Draw debug info text (C++ BananaBrain::draw_info parity)."""
        try:
            state = self._service.snapshot().get("state") or {}
            frame = int(state.get("frame") or 0)
            
            # Collect all info for UI display
            info_lines = []
            y_pos = 26
            
            # Line 1: Time and frame count
            frame_str = self._frame_to_string(frame)
            info_lines.append({"y": y_pos, "text": f"Time {frame_str} (frame {frame})"})
            y_pos += 10
            
            # Line 2: Race and map info
            self_race = str(state.get("self_race") or "Unknown")
            enemy_race = str(state.get("enemy_race") or "Unknown")
            map_name = str(state.get("map_name") or "Unknown")
            is_island = self._is_island_map()
            island_suffix = " (island map)" if is_island else ""
            info_lines.append({"y": y_pos, "text": f"Playing: {self_race} vs {enemy_race} on {map_name}{island_suffix}"})
            y_pos += 10
            
            # Line 3: Income
            try:
                income = SpendingManager.Instance().income_per_minute()
                minerals_income = income.get("minerals", 0)
                gas_income = income.get("gas", 0)
                ratio = minerals_income / gas_income if gas_income > 0 else 0.0
                info_lines.append({"y": y_pos, "text": f"Income: {minerals_income}/{gas_income} ratio={ratio:.1f}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Income: N/A"})
            y_pos += 10
            
            # Line 4: Training costs
            try:
                training_cost = SpendingManager.Instance().training_cost_per_minute()
                tm = training_cost.get("minerals", 0)
                tg = training_cost.get("gas", 0)
                ts = training_cost.get("supply", 0)
                ratio = tm / tg if tg > 0 else 0.0
                info_lines.append({"y": y_pos, "text": f"Training: {tm:.1f}/{tg:.1f}/{ts:.1f} ratio={ratio:.1f}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Training: N/A"})
            y_pos += 10
            
            # Line 5: Worker training costs
            try:
                worker_cost = SpendingManager.Instance().worker_training_cost_per_minute()
                wm = worker_cost.get("minerals", 0)
                wg = worker_cost.get("gas", 0)
                ws = worker_cost.get("supply", 0)
                info_lines.append({"y": y_pos, "text": f"Worker training: {wm:.1f}/{wg:.1f}/{ws:.1f}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Worker training: N/A"})
            y_pos += 10
            
            # Line 6: Remainder resources
            try:
                remainder = SpendingManager.Instance().remainder()
                rm = remainder.get("minerals", 0)
                rg = remainder.get("gas", 0)
                info_lines.append({"y": y_pos, "text": f"Remainder: {rm}/{rg}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Remainder: N/A"})
            y_pos += 10
            
            # Line 7: Spendable resources
            try:
                spendable = SpendingManager.Instance().spendable()
                sm = spendable.get("minerals", 0)
                sg = spendable.get("gas", 0)
                info_lines.append({"y": y_pos, "text": f"Spendable: {sm}/{sg}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Spendable: N/A"})
            y_pos += 10
            
            # Line 8: Worker/Army supply
            try:
                tm = TacticsManager.Instance()
                worker_supply = tm.worker_supply() * 0.5
                army_supply = tm.army_supply() * 0.5
                enemy_worker_supply = tm.enemy_worker_supply() * 0.5
                enemy_army_supply = tm.enemy_army_supply() * 0.5
                info_lines.append({"y": y_pos, "text": f"Worker/Army supply: {worker_supply:.1f}/{army_supply:.1f} opponent: {enemy_worker_supply:.1f}/{enemy_army_supply:.1f}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Worker/Army supply: N/A"})
            y_pos += 10
            
            # Line 9: Enemy defense and offense supply
            try:
                tm = TacticsManager.Instance()
                enemy_defense = tm.enemy_defense_supply() * 0.5
                enemy_offense = tm.enemy_offense_supply() * 0.5
                info_lines.append({"y": y_pos, "text": f"Enemy defense and offense supply: {enemy_defense:.1f}/{enemy_offense:.1f}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Enemy defense and offense supply: N/A"})
            y_pos += 10
            
            # Line 10: Average workers per mineral
            try:
                avg_workers = WorkerManager.Instance().average_workers_per_mineral()
                mining_bases = base_state.mining_base_count()
                info_lines.append({"y": y_pos, "text": f"Average #workers/mineral: {avg_workers:.1f}, #mining bases: {mining_bases}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Average #workers/mineral: N/A"})
            y_pos += 10
            
            # Line 11: Race-specific unit distribution
            try:
                from strategy_runtime import training_manager
                if self_race == "Protoss":
                    dist = training_manager.gateway_train_distribution()
                    z = dist.get("Protoss_Zealot", 0)
                    d = dist.get("Protoss_Dragoon", 0)
                    ht = dist.get("Protoss_High_Templar", 0)
                    dt = dist.get("Protoss_Dark_Templar", 0)
                    info_lines.append({"y": y_pos, "text": f"Gateway distribution: Z {z:.2f}, D {d:.2f}, Ht {ht:.2f}, Dt {dt:.2f}"})
                elif self_race == "Terran":
                    dist = training_manager.factory_train_distribution()
                    v = dist.get("Terran_Vulture", 0)
                    s = dist.get("Terran_Siege_Tank_Tank_Mode", 0)
                    g = dist.get("Terran_Goliath", 0)
                    info_lines.append({"y": y_pos, "text": f"Factory distribution: V {v:.2f}, S {s:.2f}, G {g:.2f}"})
                elif self_race == "Zerg":
                    dist = training_manager.larva_train_distribution()
                    d = dist.get("Zerg_Drone", 0)
                    o = dist.get("Zerg_Overlord", 0)
                    z = dist.get("Zerg_Zergling", 0)
                    h = dist.get("Zerg_Hydralisk", 0)
                    m = dist.get("Zerg_Mutalisk", 0)
                    s = dist.get("Zerg_Scourge", 0)
                    df = dist.get("Zerg_Defiler", 0)
                    u = dist.get("Zerg_Ultralisk", 0)
                    info_lines.append({"y": y_pos, "text": f"Larva distribution: D {d:.2f}, O {o:.2f}, Z {z:.2f}, H {h:.2f}, M {m:.2f} S {s:.2f} Df {df:.2f} U {u:.2f}"})
            except Exception:
                pass
            y_pos += 10
            
            # Line 12: Mode
            try:
                mode = self.strategy_.mode() if self.strategy_ else "N/A"
                info_lines.append({"y": y_pos, "text": f"Mode: {mode}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Mode: N/A"})
            y_pos += 10
            
            # Line 13: Opening
            try:
                opening = self.strategy_.opening() if self.strategy_ else "N/A"
                info_lines.append({"y": y_pos, "text": f"Opening: {opening}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Opening: N/A"})
            y_pos += 10
            
            # Line 14: Late game strategy
            try:
                late_game = self.strategy_.late_game_strategy() if self.strategy_ else "N/A"
                info_lines.append({"y": y_pos, "text": f"Late game strategy: {late_game}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Late game strategy: N/A"})
            y_pos += 10
            
            # Line 15: Enemy opening
            try:
                enemy_opening = OpponentModel.Instance().enemy_opening_info()
                info_lines.append({"y": y_pos, "text": f"Enemy opening: {enemy_opening}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Enemy opening: N/A"})
            y_pos += 10
            
            # Line 16: Lost workers/units
            try:
                from strategy_runtime import training_manager
                lost_workers = WorkerManager.Instance().lost_worker_count()
                lost_units = training_manager.lost_unit_count()
                info_lines.append({"y": y_pos, "text": f"Lost workers/units: {lost_workers}/{lost_units}"})
            except Exception:
                info_lines.append({"y": y_pos, "text": "Lost workers/units: N/A"})
            
            # Emit all info lines as event
            self._service.emit_local_event("draw_info", {
                "frame": frame,
                "lines": info_lines,
            })
            
        except Exception as e:
            self._service.emit_local_event("draw_error", {"phase": "draw_info", "error": str(e)})

    def _frame_to_string(self, frame: int) -> str:
        """Convert frame count to time string (MM:SS)."""
        try:
            seconds = frame // 24  # 24 fps
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        except Exception:
            return "00:00"
    
    def _is_island_map(self) -> bool:
        """Check if current map is island map."""
        try:
            return base_state.is_island_map()
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "running": self._running,
                "last_decision": self._decision_dict_locked(),
                "catalog": self.catalog(),
                "selected_strategy": self._strategy_name,
                "selected_strategy_unit": self._strategy_name,
                "selected_opening_overrides": dict(self._opening_overrides),
                "selected_mode_override": self._mode_override,
                "effective_strategy_unit": self._last_decision.strategy_unit if self._last_decision else None,
                "effective_opening": self._last_decision.opening if self._last_decision else None,
                "effective_mode": self._last_decision.mode if self._last_decision else None,
                "last_applied_frame": self._last_applied_frame,
            }

    def catalog(self) -> Dict[str, Any]:
        serializable_openings: Dict[str, Dict[str, str]] = {}
        for race, opening_map in self._openings.items():
            serializable_openings[race] = {
                f"{enemy_race}|{'1v1' if is_1v1 else 'team'}": opening
                for (enemy_race, is_1v1), opening in opening_map.items()
            }
        return {
            "openings": serializable_openings,
            "overrides": dict(self._opening_overrides),
            "mode_override": self._mode_override,
            "strategy_modules": ["ProtossStrategy", "TerranStrategy", "ZergStrategy"],
            "strategy_units": list(CANONICAL_STRATEGY_UNITS),
            "opening_catalog": opening_catalog(),
            "notes": [
                "Edit this file to customize strategy selection.",
                "BananaBrain C++ logic is mirrored here at the policy layer.",
            ],
        }

    def set_opening_override(self, race: str, opening: str) -> Dict[str, Any]:
        with self._lock:
            self._opening_overrides[str(race)] = str(opening)
            return {
                "ok": True,
                "race": str(race),
                "opening": str(opening),
                "overrides": dict(self._opening_overrides),
            }

    def set_mode_override(self, mode: str) -> Dict[str, Any]:
        mode_text = str(mode or "").strip()
        with self._lock:
            self._mode_override = mode_text or None
            return {
                "ok": True,
                "mode_override": self._mode_override,
            }

    def set_strategy_override(self, strategy_name: str) -> Dict[str, Any]:
        requested_strategy = normalize_strategy_unit_name(strategy_name)
        with self._lock:
            self._strategy_name = requested_strategy
            return {
                "ok": True,
                "selected_strategy": self._strategy_name,
                "selected_strategy_unit": self._strategy_name,
            }

    def select_strategy_file(self, selector: str) -> Dict[str, Any]:
        selector_text = str(selector or "").strip()
        if not selector_text:
            return {"ok": False, "error": "strategy_file is required"}

        # Opening files are edited live from the web UI, so force a fresh scan
        # before resolving the selection target.
        reload_opening_modules()

        unit_alias = {
            "strategy/protoss_strategy.py": "ProtossStrategy",
            "strategy/terran_strategy.py": "TerranStrategy",
            "strategy/zerg_strategy.py": "ZergStrategy",
        }
        if selector_text in unit_alias:
            with self._lock:
                self._strategy_name = unit_alias[selector_text]
            return {
                "ok": True,
                "selected_strategy_unit": self._strategy_name,
                "selected_opening_overrides": dict(self._opening_overrides),
                "selected_from": {
                    "strategy_file": selector_text,
                },
            }

        catalog = opening_catalog()
        target = None
        for race_items in (catalog.get("races") or {}).values():
            for item in race_items:
                if not isinstance(item, dict):
                    continue
                if selector_text in {
                    str(item.get("module") or ""),
                    str(item.get("relative_file") or ""),
                    str(item.get("file") or ""),
                    str(item.get("opening") or ""),
                }:
                    target = item
                    break
            if target:
                break

        if target is None:
            return {"ok": False, "error": f"strategy file not found: {selector_text}"}

        race = str(target.get("race") or "Unknown")
        opening = str(target.get("opening") or "")
        race_to_unit = {
            "Protoss": "ProtossStrategy",
            "Terran": "TerranStrategy",
            "Zerg": "ZergStrategy",
        }
        strategy_unit = race_to_unit.get(race, "auto")

        with self._lock:
            self._strategy_name = strategy_unit
            if opening:
                self._opening_overrides[race] = opening

        return {
            "ok": True,
            "selected_strategy_unit": self._strategy_name,
            "selected_opening_overrides": dict(self._opening_overrides),
            "selected_from": {
                "race": race,
                "opening": opening,
                "module": target.get("module"),
                "relative_file": target.get("relative_file"),
            },
        }

    def clear_overrides(self, kind: str = "all", race: str = "") -> Dict[str, Any]:
        with self._lock:
            if kind in {"all", "strategy"}:
                self._strategy_name = "auto"
            if kind in {"all", "mode"}:
                self._mode_override = None
            if kind in {"all", "opening"}:
                if race:
                    self._opening_overrides.pop(race, None)
                else:
                    self._opening_overrides.clear()
            return {
                "ok": True,
                "selected_strategy_unit": self._strategy_name,
                "selected_mode_override": self._mode_override,
                "selected_opening_overrides": dict(self._opening_overrides),
            }

    def _run_loop(self) -> None:
        try:
            while True:
                with self._lock:
                    if not self._running:
                        break
                    event_queue = self._queue
                if event_queue is None:
                    time.sleep(0.05)
                    continue

                try:
                    message = event_queue.get(timeout=0.25)
                except Exception:
                    continue

                event = message.get("event") or {}
                if not event:
                    continue

                event_name = event.get("event")
                if event_name == "onStart":
                    self._handle_start(event)
                elif event_name == "onFrame":
                    self._handle_frame(event)
                elif event_name == "onSendText":
                    self._handle_send_text(event)
                elif event_name == "onReceiveText":
                    self._handle_receive_text(event)
                elif event_name == "onPlayerLeft":
                    self._handle_player_left(event)
                elif event_name == "onNukeDetect":
                    self._handle_nuke_detect(event)
                elif event_name == "onUnitDiscover":
                    self._handle_unit_discover(event)
                elif event_name == "onUnitEvade":
                    self._handle_unit_evade(event)
                elif event_name == "onUnitShow":
                    self._handle_unit_show(event)
                elif event_name == "onUnitHide":
                    self._handle_unit_hide(event)
                elif event_name == "onUnitCreate":
                    self._handle_unit_create(event)
                elif event_name == "onUnitDestroy":
                    self._handle_unit_destroy(event)
                elif event_name == "onUnitMorph":
                    self._handle_unit_morph(event)
                elif event_name == "onUnitRenegade":
                    self._handle_unit_renegade(event)
                elif event_name == "onSaveGame":
                    self._handle_save_game(event)
                elif event_name == "onUnitComplete":
                    self._handle_unit_complete(event)
                elif event_name == "onEnd":
                    self._handle_end(event)
        finally:
            with self._lock:
                self._running = False

    def _handle_start(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onStart()

        # Parse start locations from C++ payload
        self._all_start_tiles = []
        for entry in (payload.get("start_locations") or "").split(";"):
            parts = entry.strip().split(",")
            if len(parts) == 2:
                try:
                    self._all_start_tiles.append((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass

        self._self_start_tile = None
        self_start_raw = (payload.get("self_start") or "").strip()
        if self_start_raw:
            parts = self_start_raw.split(",")
            if len(parts) == 2:
                try:
                    self._self_start_tile = (int(parts[0]), int(parts[1]))
                except ValueError:
                    pass

        # Scout targets = all starts except own
        self._scout_targets = [
            t for t in self._all_start_tiles if t != self._self_start_tile
        ]
        self._scout_assigned = {}
        self._sent_initial_scout = False
        self._economy_bootstrapped = False
        self._worker_targets = {}
        self._worker_order_at = {}
        self._last_frame_context = {}

        decision = self._choose_strategy(payload, event)
        with self._lock:
            self._last_decision = decision
            self._last_publish_at = time.monotonic()
            self._current_opening = decision.opening
        self._service.emit_local_event("strategy_decision", self._decision_payload(decision))
        self._bootstrap_economy(frame=int(event.get("frame") or 0), payload=payload)
        self._send_economy_actions(int(event.get("frame") or 0), payload)

    def _handle_frame(self, event: Dict[str, Any]) -> None:
        self._current_frame_event = event
        self.onFrame()  # This now handles before, strategy, after, surrender_if_hope_lost internally
        # Also publish strategy decision
        payload = event.get("payload") or {}
        self._strategy_frame(event)

    def _before_frame(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        frame = int(event.get("frame") or 0)
        if frame <= 0:
            return

        state = self._service.snapshot().get("state") or {}
        InformationManager.Instance().update_units_and_buildings(state, frame)
        InformationManager.Instance().update_information(state)
        TacticsManager.Instance().update(state, frame)
        OpponentModel.Instance().update(state)
        PathFinder.Instance().update(state)

        frame_context = self._build_frame_context(frame, payload)
        with self._lock:
            self._last_frame_context = frame_context

        self._service.emit_local_event("frame_before", frame_context)

        # --- Overlord scouting (Zerg only) ---
        self._update_overlord_scouting(payload, frame)

    def _strategy_frame(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        frame = int(event.get("frame") or 0)
        if frame <= 0:
            return

        decision = self._choose_strategy(payload, event)
        now = time.monotonic()
        should_publish = True
        with self._lock:
            same_choice = self._last_decision == decision
            too_soon = (now - self._last_publish_at) < self._publish_interval_sec
            should_publish = not (same_choice and too_soon)
            if should_publish:
                self._last_decision = decision
                self._last_publish_at = now
                self._last_applied_frame = frame

        if not should_publish:
            return

        decision_payload = self._decision_payload(decision)
        self._service.emit_local_event("strategy_decision", decision_payload)
        self._service.send_action(
            {
                "type": "strategy_command",
                **decision_payload,
                "frame": frame,
                "source": "banana_brain_policy",
            }
        )
        placement = decision.placement_plan or {}
        if placement:
            self._service.send_action(
                {
                    "type": "placement_policy",
                    "plan": str(placement.get("plan", "default")),
                    "expand_priority": str(placement.get("expand_priority", "natural")),
                    "wall_policy": str(placement.get("wall_policy", "none")),
                    "proxy_policy": str(placement.get("proxy_policy", "none")),
                    "defensive_anchor": str(placement.get("defensive_anchor", "main_ramp")),
                    "frame": frame,
                    "source": "banana_brain_policy",
                }
            )

        current_state = self._service.snapshot().get("state") or {}
        for req in decision.build_requests:
            request_state = self._classify_build_request(req, current_state)
            if request_state == "satisfied":
                continue
            if request_state == "blocked":
                break
            self._service.send_action(req)
            break

    def _after_frame(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        frame = int(event.get("frame") or 0)
        if frame <= 0:
            return
        self._send_economy_actions(frame, payload)

    def _maybe_surrender(self, event: Dict[str, Any]) -> None:
        frame = int(event.get("frame") or 0)
        if frame <= 0 or (frame % (2 * 24)) != 0:
            return

        state = self._service.snapshot().get("state") or {}
        own_units = self._parse_unit_entries(state.get("own_units"))
        enemy_units = self._parse_unit_entries(state.get("enemy_units"))

        has_depot = any(
            str(unit.get("type") or "") in {"Protoss_Nexus", "Terran_Command_Center", "Zerg_Hatchery", "Zerg_Lair", "Zerg_Hive"}
            for unit in own_units
        )
        if has_depot:
            return

        visible_attacker_found = any(
            str(unit.get("type") or "") in {
                "Protoss_Zealot",
                "Protoss_Dragoon",
                "Protoss_Reaver",
                "Terran_Marine",
                "Terran_Firebat",
                "Terran_Siege_Tank_Tank_Mode",
                "Terran_Siege_Tank_Siege_Mode",
                "Zerg_Zergling",
                "Zerg_Hydralisk",
                "Zerg_Mutalisk",
                "Zerg_Lurker",
            }
            for unit in enemy_units
        )
        if not visible_attacker_found:
            return

        self._service.emit_local_event(
            "strategy_surrender",
            {
                "frame": frame,
                "reason": "hope_lost",
            },
        )
        self._service.send_action(
            {
                "type": "leave_game",
                "frame": frame,
                "source": "banana_brain_policy",
            }
        )

    def _bootstrap_economy(self, frame: int, payload: Optional[Dict[str, Any]] = None) -> None:
        if self._economy_bootstrapped:
            return
        snapshot = self._service.snapshot().get("state") or {}
        source = payload or {}
        units = self._parse_unit_entries(snapshot.get("own_units") or source.get("own_units") or source.get("units"))
        minerals = self._parse_mineral_entries(snapshot.get("mineral_fields") or source.get("mineral_fields"))
        if not units or not minerals:
            return

        mineral_positions = [(m["x"], m["y"]) for m in minerals]
        for unit in units:
            unit_type = str(unit.get("type") or "")
            if unit_type not in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}:
                continue
            unit_id = int(unit.get("id") or 0)
            if unit_id <= 0:
                continue
            worker_x = int(unit.get("x") or 0)
            worker_y = int(unit.get("y") or 0)
            nearest = min(mineral_positions, key=lambda pos: abs(pos[0] - worker_x) + abs(pos[1] - worker_y))
            self._worker_targets[unit_id] = nearest
            self._service.emit_local_event("economy_action", {
                "type": "worker_gather",
                "unit_id": unit_id,
                "target_x": nearest[0],
                "target_y": nearest[1],
                "frame": frame,
                "bootstrap": True,
            })
            self._service.send_action({
                "type": "worker_gather",
                "unit_id": unit_id,
                "target_x": nearest[0],
                "target_y": nearest[1],
                "frame": frame,
                "source": "banana_brain_bootstrap",
            })

        self._economy_bootstrapped = True

    def _update_overlord_scouting(self, payload: Dict[str, Any], frame: int) -> None:
        """BananaBrain InitialScout 로직: 미탐색 스타트 위치로 오버로드 이동."""
        # Parse current overlord states: "id,x,y,is_idle;..."
        overlord_raw = (payload.get("overlord_units") or "").strip()
        if not overlord_raw:
            return

        overlords = {}
        for entry in overlord_raw.split(";"):
            parts = entry.split(",")
            if len(parts) == 4:
                try:
                    uid = int(parts[0])
                    ox = int(parts[1])
                    oy = int(parts[2])
                    is_idle = parts[3] == "1"
                    overlords[uid] = {"x": ox, "y": oy, "idle": is_idle}
                except ValueError:
                    pass

        if not overlords:
            return

        # Parse explored start tiles: "tx,ty;..."
        explored_raw = (payload.get("explored_start_tiles") or "").strip()
        explored = set()
        for entry in explored_raw.split(";"):
            parts = entry.split(",")
            if len(parts) == 2:
                try:
                    explored.add((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass

        # Remove explored targets from scout list and clear assignments to them
        self._scout_targets = [t for t in self._scout_targets if t not in explored]
        self._scout_assigned = {
            uid: tgt for uid, tgt in self._scout_assigned.items()
            if tgt not in explored and uid in overlords
        }

        if not self._scout_targets:
            return  # All bases found or no scouts needed

        # Tile → pixel center conversion (each tile = 32 pixels)
        def tile_to_pixel(tx, ty):
            return tx * 32 + 16, ty * 32 + 16

        # Assign idle, unassigned overlords to nearest unscounted target
        assigned_targets = set(self._scout_assigned.values())
        for uid, info in overlords.items():
            if not info["idle"]:
                continue
            if uid in self._scout_assigned:
                continue  # Already moving somewhere
            # Find nearest unassigned target
            unassigned = [t for t in self._scout_targets if t not in assigned_targets]
            if not unassigned:
                break
            nearest = min(
                unassigned,
                key=lambda t: abs(tile_to_pixel(*t)[0] - info["x"]) + abs(tile_to_pixel(*t)[1] - info["y"])
            )
            px, py = tile_to_pixel(*nearest)
            self._scout_assigned[uid] = nearest
            assigned_targets.add(nearest)
            if not self._sent_initial_scout:
                self._sent_initial_scout = True
                self._service.emit_local_event(
                    "strategy_scout",
                    {
                        "sent_initial_scout": True,
                        "unit_id": uid,
                        "frame": frame,
                    },
                )
            self._service.send_action({
                "type": "unit_move",
                "unit_id": uid,
                "x": px,
                "y": py,
                "frame": frame,
                "source": "overlord_scout",
            })

    def _classify_build_request(self, req: Dict[str, Any], state: Dict[str, Any]) -> str:
        req_type = str(req.get("type") or "").strip()
        building_type = str(req.get("building_type") or "").strip()
        unit_type = str(req.get("unit_type") or "").strip()
        own_units = self._parse_unit_entries(state.get("own_units"))

        def bwapi_type_name(name: str) -> str:
            if not name:
                return ""
            if name.startswith("Protoss_") or name.startswith("Terran_") or name.startswith("Zerg_"):
                return name
            return f"{str(state.get('self_race') or 'Protoss')}_{name}"

        def count_unit(type_name: str, completed_only: bool = False) -> int:
            total = 0
            for unit in own_units:
                if str(unit.get("type") or "") != type_name:
                    continue
                if completed_only and not bool(unit.get("completed")):
                    continue
                total += 1
            return total

        def has_structure(type_name: str, completed_only: bool = False) -> bool:
            return count_unit(type_name, completed_only=completed_only) > 0

        if req_type == "build_structure":
            unit_name = bwapi_type_name(building_type)
            if building_type in {"Pylon", "Nexus", "Gateway", "Assimilator", "Forge", "Photon_Cannon", "Cybernetics_Core"}:
                if has_structure(unit_name):
                    return "satisfied"

            if building_type == "Gateway":
                if has_structure(bwapi_type_name("Gateway")):
                    return "satisfied"
                if not has_structure(bwapi_type_name("Pylon"), completed_only=True):
                    return "blocked"
                return "issue"

            if building_type == "Assimilator":
                if has_structure(bwapi_type_name("Assimilator")):
                    return "satisfied"
                if not has_structure(bwapi_type_name("Nexus"), completed_only=True):
                    return "blocked"
                return "issue"

            if building_type == "Cybernetics_Core":
                if has_structure(bwapi_type_name("Cybernetics_Core")):
                    return "satisfied"
                if not has_structure(bwapi_type_name("Gateway"), completed_only=True):
                    return "blocked"
                return "issue"

            if building_type == "Photon_Cannon":
                if has_structure(bwapi_type_name("Photon_Cannon")):
                    return "satisfied"
                if not has_structure(bwapi_type_name("Forge"), completed_only=True):
                    return "blocked"
                return "issue"

            return "issue"

        if req_type == "train_unit":
            if unit_type == "Zealot":
                if count_unit(bwapi_type_name("Zealot")) > 0:
                    return "satisfied"
                if not has_structure(bwapi_type_name("Gateway"), completed_only=True):
                    return "blocked"
                return "issue"

        return "issue"

    def _handle_end(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        is_winner_raw = payload.get("is_winner", "")
        won = str(is_winner_raw).lower() in {"true", "1", "yes"}
        self.onEnd(won)
        with self._lock:
            opening = self._current_opening
            self._current_opening = None
        if opening:
            self._result_store.record(opening, won)
            self._service.emit_local_event(
                "strategy_result_recorded",
                {"opening": opening, "won": won, "stats": self._result_store.get_stats().get(opening, {})},
            )
        self._service.emit_local_event("strategy_stopped", {"runtime": "banana_brain_policy", "reason": "game ended"})

    def _handle_receive_text(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        player = str(payload.get("player") or "Unknown")
        text = str(payload.get("text") or "")
        self.onReceiveText(player, text)

    def _handle_send_text(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onSendText(str(payload.get("text") or ""))

    def _handle_player_left(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onPlayerLeft(str(payload.get("player") or "Unknown"))

    def _handle_nuke_detect(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onNukeDetect(dict(payload))

    def _handle_unit_discover(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitDiscover(dict(payload))

    def _handle_unit_evade(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitEvade(dict(payload))

    def _handle_unit_show(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitShow(dict(payload))

    def _handle_unit_hide(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitHide(dict(payload))

    def _handle_unit_create(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitCreate(dict(payload))

    def _handle_unit_destroy(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitDestroy(dict(payload))

    def _handle_unit_morph(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitMorph(dict(payload))

    def _handle_unit_renegade(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitRenegade(dict(payload))

    def _handle_save_game(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        game_name = str(payload.get("game_name") or payload.get("gameName") or "")
        self.onSaveGame(game_name)

    def _handle_unit_complete(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        self.onUnitComplete(dict(payload))

    def _choose_strategy(self, payload: Dict[str, Any], event: Dict[str, Any]) -> StrategyChoice:
        state = self._service.snapshot()["state"]
        raw_enemy_count = payload.get("enemy_count", state.get("enemy_count") or 1)
        try:
            enemy_count = int(raw_enemy_count)
        except (TypeError, ValueError):
            enemy_count = 1
        context = StrategyContext(
            service=self._service,
            state=state,
            payload=payload,
            event=event,
            strategy_name=self._strategy_name,
            result_store=self._result_store,
        )
        selected = self._selector.select(context)
        selected.pick_strategy(enemy_count == 1)
        self.strategy_ = selected
        forced_opening = self._resolve_opening_override(selected.self_race)
        if forced_opening:
            selected._opening = forced_opening
        selected.frame_inner()
        mode_override = self._resolve_mode_override()
        if mode_override:
            selected._mode = mode_override
        selected_decision = selected.decision()

        self_race = selected_decision.self_race
        enemy_race = selected_decision.enemy_race
        is_1v1 = enemy_count == 1
        opening = selected_decision.opening
        mode = selected_decision.mode
        late_game = selected_decision.late_game_strategy
        placement_plan = dict(selected_decision.placement_plan or {})
        if not placement_plan:
            placement_plan = BuildingPlacementManager.Instance().default_plan(state, payload, selected_decision)
        else:
            BuildingPlacementManager.Instance().set_plan(placement_plan)
        strategy_unit = str(selected_decision.source or selected.__class__.__name__)
        build_requests = list(selected_decision.build_requests or [])
        strategy_source = "override" if self._strategy_name != "auto" else "auto"
        opening_source = "override" if forced_opening else "auto"
        mode_source = "override" if mode_override else "auto"

        return StrategyChoice(
            self_race=self_race,
            enemy_race=enemy_race,
            is_1v1=is_1v1,
            opening=opening,
            mode=mode,
            late_game_strategy=late_game,
            placement_plan=placement_plan,
            strategy_unit=strategy_unit,
            build_requests=build_requests,
            opening_source=opening_source,
            mode_source=mode_source,
            strategy_source=strategy_source,
        )

    def _resolve_opening_override(self, self_race: str) -> Optional[str]:
        with self._lock:
            return self._opening_overrides.get(self_race)

    def _resolve_mode_override(self) -> Optional[str]:
        with self._lock:
            return self._mode_override

    def _parse_semicolon_entries(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value or "").strip()
        if not text:
            return []
        return [part.strip() for part in text.split(";") if part.strip()]

    def _worker_cap_from_state(self, state: Dict[str, Any], payload: Dict[str, Any]) -> int:
        entries = self._parse_semicolon_entries(state.get("mineral_fields") or payload.get("mineral_fields"))
        self_start = str(state.get("self_start") or payload.get("self_start") or "").strip()
        origin_x = origin_y = None
        if self_start:
            parts = self_start.split(",")
            if len(parts) == 2:
                try:
                    origin_x = int(parts[0]) * 32 + 16
                    origin_y = int(parts[1]) * 32 + 16
                except ValueError:
                    origin_x = origin_y = None

        mineral_count = 0
        for entry in entries:
            parts = entry.split(",")
            if len(parts) != 3:
                continue
            try:
                mx = int(parts[1])
                my = int(parts[2])
            except ValueError:
                continue
            if origin_x is None or origin_y is None:
                mineral_count += 1
                continue
            if abs(mx - origin_x) + abs(my - origin_y) <= 640:
                mineral_count += 1
        if mineral_count <= 0:
            mineral_count = 8
        return mineral_count * 2

    def _count_entries(self, entries: list[Dict[str, Any]], type_names: set[str], completed_only: bool = False) -> int:
        total = 0
        for entry in entries:
            if str(entry.get("type") or "") not in type_names:
                continue
            if completed_only and not bool(entry.get("completed")):
                continue
            total += 1
        return total

    def _build_frame_context(self, frame: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self._service.snapshot().get("state") or {}
        own_units = self._parse_unit_entries(snapshot.get("own_units") or payload.get("own_units") or payload.get("units"))
        enemy_units = self._parse_unit_entries(snapshot.get("enemy_units") or payload.get("enemy_units"))
        minerals = self._parse_mineral_entries(snapshot.get("mineral_fields") or payload.get("mineral_fields"))
        geysers = self._parse_semicolon_entries(snapshot.get("geysers") or payload.get("geysers"))

        worker_types = {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}
        depot_types = {"Protoss_Nexus", "Terran_Command_Center", "Zerg_Hatchery", "Zerg_Lair", "Zerg_Hive"}
        building_types = {
            "Protoss_Pylon", "Protoss_Gateway", "Protoss_Forge", "Protoss_Assimilator",
            "Protoss_Cybernetics_Core", "Protoss_Photon_Cannon", "Protoss_Nexus",
            "Terran_Barracks", "Terran_Factory", "Terran_Starport", "Terran_Command_Center",
            "Zerg_Spawning_Pool", "Zerg_Hydralisk_Den", "Zerg_Lair", "Zerg_Hive", "Zerg_Hatchery",
        }
        combat_types = {
            "Protoss_Zealot", "Protoss_Dragoon", "Protoss_Reaver", "Protoss_Dark_Templar",
            "Terran_Marine", "Terran_Firebat", "Terran_Vulture", "Terran_Siege_Tank_Tank_Mode", "Terran_Siege_Tank_Siege_Mode",
            "Zerg_Zergling", "Zerg_Hydralisk", "Zerg_Mutalisk", "Zerg_Lurker",
        }

        worker_count = self._count_entries(own_units, worker_types)
        building_count = self._count_entries(own_units, building_types)
        depot_count = self._count_entries(own_units, depot_types)
        combat_count = self._count_entries(own_units, combat_types)
        enemy_combat_count = self._count_entries(enemy_units, combat_types)
        completed_buildings = self._count_entries(own_units, building_types, completed_only=True)

        supply_used = int(snapshot.get("supply_used") or payload.get("supply_used") or 0)
        supply_total = int(snapshot.get("supply_total") or payload.get("supply_total") or 0)
        minerals_count = int(snapshot.get("minerals") or payload.get("minerals") or 0)
        gas_count = int(snapshot.get("gas") or payload.get("gas") or 0)

        if supply_used < 20:
            stage = "opening"
        elif supply_used < 60:
            stage = "midgame"
        else:
            stage = "late"

        if enemy_combat_count > combat_count + 3:
            pressure = "high"
        elif enemy_combat_count > 0:
            pressure = "medium"
        else:
            pressure = "low"

        return {
            "frame": frame,
            "self_race": snapshot.get("self_race") or payload.get("race") or payload.get("self_race"),
            "enemy_race": snapshot.get("enemy_race") or payload.get("enemy_race"),
            "minerals": minerals_count,
            "gas": gas_count,
            "supply_used": supply_used,
            "supply_total": supply_total,
            "stage": stage,
            "pressure": pressure,
            "own_unit_count": len(own_units),
            "enemy_unit_count": len(enemy_units),
            "worker_count": worker_count,
            "building_count": building_count,
            "depot_count": depot_count,
            "combat_count": combat_count,
            "enemy_combat_count": enemy_combat_count,
            "completed_buildings": completed_buildings,
            "mineral_field_count": len(minerals),
            "geyser_count": len(geysers),
            "start_tile_x": snapshot.get("start_tile_x", payload.get("start_tile_x", -1)),
            "start_tile_y": snapshot.get("start_tile_y", payload.get("start_tile_y", -1)),
            "policy_running": bool(snapshot.get("policy_running")),
            "strategy_opening": snapshot.get("strategy_opening"),
            "strategy_mode": snapshot.get("strategy_mode"),
            "strategy_late_game": snapshot.get("strategy_late_game"),
            "selected_strategy_unit": self._strategy_name,
        }

    def _can_issue_worker_order(self, order_type: str, unit_id: int, frame: int, cooldown_frames: int = 24) -> bool:
        key = (str(order_type), int(unit_id))
        last_frame = int(self._worker_order_at.get(key) or -10**9)
        if frame - last_frame < cooldown_frames:
            return False
        self._worker_order_at[key] = frame
        return True

    def _parse_unit_entries(self, value: Any) -> list[Dict[str, Any]]:
        if not value:
            return []
        entries: list[Dict[str, Any]] = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    entries.append(item)
            return entries
        text = str(value).strip()
        if not text:
            return []
        for entry in text.split(";"):
            parts = entry.strip().split(",")
            if len(parts) < 9:
                continue
            try:
                entries.append({
                    "id": int(parts[0]),
                    "type": parts[1],
                    "x": int(parts[2]),
                    "y": int(parts[3]),
                    "idle": parts[4] == "1",
                    "carrying_minerals": parts[5] == "1",
                    "carrying_gas": parts[6] == "1",
                    "completed": parts[7] == "1",
                    "constructing": parts[8] == "1",
                })
            except ValueError:
                continue
        return entries

    def _parse_mineral_entries(self, value: Any) -> list[Dict[str, Any]]:
        if not value:
            return []
        entries: list[Dict[str, Any]] = []
        text = str(value).strip()
        if not text:
            return []
        for entry in text.split(";"):
            parts = entry.strip().split(",")
            if len(parts) < 3:
                continue
            try:
                entries.append({"id": int(parts[0]), "x": int(parts[1]), "y": int(parts[2])})
            except ValueError:
                continue
        return entries

    def _send_economy_actions(self, frame: int, payload: Optional[Dict[str, Any]] = None) -> None:
        snapshot = self._service.snapshot().get("state") or {}
        source = payload or {}
        units = self._parse_unit_entries(snapshot.get("own_units") or source.get("own_units") or source.get("units"))
        minerals = self._parse_mineral_entries(snapshot.get("mineral_fields") or source.get("mineral_fields"))
        if not units or not minerals:
            return

        worker_count = 0
        for unit in units:
            unit_type = str(unit.get("type") or "")
            if unit_type in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}:
                worker_count += 1

        worker_cap = self._worker_cap_from_state(snapshot, snapshot)
        if worker_count < worker_cap:
            depot = next(
                (
                    unit for unit in units
                    if str(unit.get("type") or "") in {"Protoss_Nexus", "Terran_Command_Center", "Zerg_Hatchery", "Zerg_Lair", "Zerg_Hive"}
                    and int(unit.get("id") or 0) > 0
                ),
                None,
            )
            if depot is None:
                return
            worker_type = {
                "Protoss": "Protoss_Probe",
                "Terran": "Terran_SCV",
                "Zerg": "Zerg_Drone",
            }.get(str(snapshot.get("self_race") or ""), "Protoss_Probe")
            self._service.emit_local_event("economy_action", {
                "type": "worker_train",
                "unit_id": int(depot.get("id") or 0),
                "worker_type": worker_type,
                "enabled": 1,
                "worker_cap": worker_cap,
                "frame": frame,
            })
            if self._can_issue_worker_order("worker_train", int(depot.get("id") or 0), frame, cooldown_frames=48):
                self._service.send_action({
                    "type": "worker_train",
                    "unit_id": int(depot.get("id") or 0),
                    "worker_type": worker_type,
                    "enabled": 1,
                    "worker_cap": worker_cap,
                    "frame": frame,
                    "source": "banana_brain_policy",
                })
        else:
            self._service.emit_local_event("economy_action", {
                "type": "worker_train",
                "enabled": 0,
                "worker_cap": worker_cap,
                "frame": frame,
            })
            if self._can_issue_worker_order("worker_train_off", 0, frame, cooldown_frames=48):
                self._service.send_action({
                    "type": "worker_train",
                    "enabled": 0,
                    "worker_cap": worker_cap,
                    "frame": frame,
                    "source": "banana_brain_policy",
                })

        mineral_positions = [(m["x"], m["y"]) for m in minerals]
        for unit in units:
            unit_type = str(unit.get("type") or "")
            if unit_type not in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}:
                continue
            unit_id = int(unit.get("id") or 0)
            if unit_id <= 0:
                continue
            if unit.get("carrying_minerals") or unit.get("carrying_gas"):
                self._service.emit_local_event("economy_action", {
                    "type": "worker_return",
                    "unit_id": unit_id,
                    "frame": frame,
                })
                if not self._can_issue_worker_order("worker_return", unit_id, frame, cooldown_frames=36):
                    continue
                self._service.send_action({
                    "type": "worker_return",
                    "unit_id": unit_id,
                    "frame": frame,
                    "source": "banana_brain_policy",
                })
                continue
            if not unit.get("idle"):
                continue
            worker_x = int(unit.get("x") or 0)
            worker_y = int(unit.get("y") or 0)
            nearest = min(mineral_positions, key=lambda pos: abs(pos[0] - worker_x) + abs(pos[1] - worker_y))
            self._service.emit_local_event("economy_action", {
                "type": "worker_gather",
                "unit_id": unit_id,
                "target_x": nearest[0],
                "target_y": nearest[1],
                "frame": frame,
            })
            if not self._can_issue_worker_order("worker_gather", unit_id, frame, cooldown_frames=36):
                continue
            self._service.send_action({
                "type": "worker_gather",
                "unit_id": unit_id,
                "target_x": nearest[0],
                "target_y": nearest[1],
                "frame": frame,
                "source": "banana_brain_policy",
            })

    def _choose_strategy_legacy(self, payload: Dict[str, Any], event: Dict[str, Any]) -> StrategyChoice:
        state = self._service.snapshot()["state"]
        self_race = str(payload.get("race") or payload.get("self_race") or state.get("self_race") or "Unknown")
        enemy_race = str(payload.get("enemy_race") or state.get("enemy_race") or "Unknown")
        is_1v1 = bool(payload.get("enemy_count", 1) == 1)

        opening = self._select_opening(self_race, enemy_race, is_1v1, payload)
        mode = self._select_mode(event, payload, self_race, enemy_race)
        late_game = self._select_late_game(self_race, payload)
        return StrategyChoice(
            self_race=self_race,
            enemy_race=enemy_race,
            is_1v1=is_1v1,
            opening=opening,
            mode=mode,
            late_game_strategy=late_game,
            placement_plan={},
            strategy_unit="LegacyStrategy",
            build_requests=[],
        )

    def _select_opening(self, self_race: str, enemy_race: str, is_1v1: bool, payload: Dict[str, Any]) -> str:
        override = self._opening_overrides.get(self_race)
        if override:
            return override

        matchup_hint = str(payload.get("opening_hint") or payload.get("enemy_opening") or "").strip()
        if self_race == "Protoss" and matchup_hint:
            hint = matchup_hint.lower()
            if "pool" in hint or "zerg" in hint:
                return "PvZ_bisu"
            if "terran" in hint or "marine" in hint:
                return "PvT_sairgoon"

        opening_map = self._openings.get(self_race, {})
        if (enemy_race, is_1v1) in opening_map:
            return opening_map[(enemy_race, is_1v1)]
        if (enemy_race, True) in opening_map:
            return opening_map[(enemy_race, True)]
        if ("Unknown", is_1v1) in opening_map:
            return opening_map[("Unknown", is_1v1)]
        if ("Unknown", True) in opening_map:
            return opening_map[("Unknown", True)]
        return "auto_play"

    def _select_mode(self, event: Dict[str, Any], payload: Dict[str, Any], self_race: str, enemy_race: str) -> str:
        frame = int(event.get("frame") or 0)
        supply_used = int(payload.get("supply_used") or 0)
        enemy_count = int(payload.get("enemy_count") or 1)
        if frame < 24 * 3:
            return "Opening"
        if supply_used < 40:
            return "Midgame"
        if enemy_count > 1:
            return "MultiEnemy"
        if self_race == "Protoss" and enemy_race == "Zerg" and supply_used < 80:
            return "Pressure"
        return "Main"

    def _select_late_game(self, self_race: str, payload: Dict[str, Any]) -> str:
        map_width = int(payload.get("map_width_tiles") or 128)
        map_height = int(payload.get("map_height_tiles") or 128)
        max_dim = max(map_width, map_height)
        if self_race == "Protoss":
            return "carriers" if max_dim < 160 else "arbiters"
        if self_race == "Terran":
            return "mechanic" if max_dim >= 128 else "bio_mech"
        if self_race == "Zerg":
            return "zerg_late"
        return "none"

    def _decision_payload(self, decision: StrategyChoice) -> Dict[str, Any]:
        return {
            "self_race": decision.self_race,
            "enemy_race": decision.enemy_race,
            "is_1v1": decision.is_1v1,
            "opening": decision.opening,
            "mode": decision.mode,
            "late_game_strategy": decision.late_game_strategy,
            "placement_plan": decision.placement_plan or {},
            "strategy_unit": decision.strategy_unit,
            "build_requests": decision.build_requests,
            "worker_cap": self._worker_cap_from_state(self._service.snapshot().get("state") or {}, self._service.snapshot().get("state") or {}),
            "strategy_source": decision.strategy_source,
            "opening_source": decision.opening_source,
            "mode_source": decision.mode_source,
        }

    def _decision_dict_locked(self) -> Optional[Dict[str, Any]]:
        if self._last_decision is None:
            return None
        return self._decision_payload(self._last_decision)


_runtime = None
_runtime_lock = threading.Lock()


def get_strategy_runtime(bridge_service):
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = BananaBrain(bridge_service)
        return _runtime


BananaBrainPolicyRuntime = BananaBrain