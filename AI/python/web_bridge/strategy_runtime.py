from __future__ import annotations

"""Single-file BananaBrain-style strategy policy.

This is the customization point for user-editable strategy decisions. The goal
is to keep the strategic logic in one Python file so it can be tuned without
recompiling the DLL.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from strategy import CANONICAL_STRATEGY_UNITS, StrategyContext, StrategySelector, normalize_strategy_unit_name
from strategy.opening_loader import opening_catalog
from strategy.result_store import ResultStore


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


class BananaBrainPolicyRuntime:
    def __init__(self, bridge_service) -> None:
        self._service = bridge_service
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._subscriber_id: Optional[int] = None
        self._queue = None
        self._last_decision: Optional[StrategyChoice] = None
        self._last_publish_at = 0.0
        self._publish_interval_sec = 4.0
        self._strategy_name = "auto"
        self._mode_override: Optional[str] = None
        self._selector = StrategySelector()

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
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="BananaBrainPolicyRuntime")
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
        from strategy.opening_loader import reload_opening_modules
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
                elif event_name == "onEnd":
                    self._handle_end(event)
        finally:
            with self._lock:
                self._running = False

    def _handle_start(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}

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

        decision = self._choose_strategy(payload, event)
        with self._lock:
            self._last_decision = decision
            self._last_publish_at = time.monotonic()
            self._current_opening = decision.opening
        self._service.emit_local_event("strategy_decision", self._decision_payload(decision))
        self._send_economy_actions(int(event.get("frame") or 0), payload)

    def _handle_frame(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        frame = int(event.get("frame") or 0)
        if frame <= 0 or (frame % 24) != 0:
            return

        # --- Overlord scouting (Zerg only) ---
        self._update_overlord_scouting(payload, frame)

        decision = self._choose_strategy(payload, event)
        now = time.monotonic()
        with self._lock:
            same_choice = self._last_decision == decision
            too_soon = (now - self._last_publish_at) < self._publish_interval_sec
            if same_choice and too_soon:
                self._send_economy_actions(frame, payload)
                return
            self._last_decision = decision
            self._last_publish_at = now
            self._last_applied_frame = frame

        self._service.emit_local_event("strategy_decision", self._decision_payload(decision))
        self._send_economy_actions(frame, payload)
        self._service.send_action(
            {
                "type": "strategy_command",
                **self._decision_payload(decision),
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
        for req in decision.build_requests:
            self._service.send_action(req)

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

    def _handle_end(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload") or {}
        is_winner_raw = payload.get("is_winner", "")
        won = str(is_winner_raw).lower() in {"true", "1", "yes"}
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

    def _choose_strategy(self, payload: Dict[str, Any], event: Dict[str, Any]) -> StrategyChoice:
        state = self._service.snapshot()["state"]
        context = StrategyContext(
            service=self._service,
            state=state,
            payload=payload,
            event=event,
            strategy_name=self._strategy_name,
            result_store=self._result_store,
        )
        selected = self._selector.select(context)
        selected.pick_strategy(selected.is_1v1)
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
        is_1v1 = selected_decision.is_1v1
        opening = selected_decision.opening
        mode = selected_decision.mode
        late_game = selected_decision.late_game_strategy
        placement_plan = dict(selected_decision.placement_plan or {})
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
            _runtime = BananaBrainPolicyRuntime(bridge_service)
        return _runtime