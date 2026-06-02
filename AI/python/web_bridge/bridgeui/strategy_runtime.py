import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from . import script_runner


EventHandler = Callable[[Dict[str, Any]], None]


class EventDispatcher:
    def __init__(self) -> None:
        self._handlers = defaultdict(list)  # type: Dict[str, List[EventHandler]]

    def on(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def dispatch(self, event: Dict[str, Any]) -> None:
        name = event.get("event", "")
        for handler in self._handlers.get(name, []):
            handler(event)
        for handler in self._handlers.get("*", []):
            handler(event)


class PythonStrategyRuntime:
    """Event-driven runtime that parses game events, updates state, and selects Python strategy scripts."""

    def __init__(self, bridge_service) -> None:
        self._service = bridge_service
        self._lock = threading.Lock()
        self._running = False
        self._thread = None  # type: Optional[threading.Thread]
        self._sub_id = None  # type: Optional[int]
        self._event_queue = None
        self._handler_ids = []  # type: List[int]
        self._target_script_id = "auto_play"
        self._policy_mode = False
        self._last_switch_at = 0.0
        self._switch_cooldown = 0.8
        self._last_policy_decision = None
        self._race_opening_defaults = {
            "Protoss": "PvU_natural_expand",
            "Terran": "TvU_natural_expand",
            "Zerg": "ZvU_natural_expand",
        }
        self._matchup_opening_defaults = {
            ("Protoss", "Protoss"): "PvP_3gaterobo",
            ("Protoss", "Terran"): "PvT_12nexus",
            ("Protoss", "Zerg"): "PvZ_10-12gate",
            ("Protoss", "Unknown"): "PvU_natural_expand",
            ("Terran", "Protoss"): "TvP_siegeexpand",
            ("Terran", "Terran"): "TvT_1factfe",
            ("Terran", "Zerg"): "TvZ_1raxfe",
            ("Terran", "Unknown"): "TvU_natural_expand",
            ("Zerg", "Protoss"): "ZvP_9734",
            ("Zerg", "Terran"): "ZvT_3hatchmuta",
            ("Zerg", "Zerg"): "ZvZ_9poolspire",
            ("Zerg", "Unknown"): "ZvU_natural_expand",
        }
        self._state = {
            "frame": -1,
            "self_race": None,
            "enemy_race": None,
            "enemy_count": None,
            "is_1v1": None,
            "is_ffa": None,
            "minerals": 0,
            "gas": 0,
            "supply_used": 0,
            "supply_total": 0,
            "own_units": [],
            "enemy_units": [],
            "current_script_id": None,
            "runtime_enabled": False,
            "target_script_id": "auto_play",
            "policy_mode": False,
            "last_event": None,
            "last_error": None,
        }
        self._dispatcher = EventDispatcher()
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._dispatcher.on("onStart", self._on_start)
        self._dispatcher.on("onStart_initialized", self._on_start_initialized)
        self._dispatcher.on("onFrame", self._on_frame)
        self._dispatcher.on("onEnd", self._on_end)
        self._dispatcher.on("script_status", self._on_script_status)
        self._dispatcher.on("onUnitCreate", self._on_unit_event)
        self._dispatcher.on("onUnitDestroy", self._on_unit_event)
        self._dispatcher.on("onUnitComplete", self._on_unit_event)
        self._dispatcher.on("battle_judgement", self._on_battle_judgement)

    def start(self, target_script_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if target_script_id:
                self._target_script_id = target_script_id
                self._policy_mode = False
            elif not self._target_script_id:
                self._target_script_id = "auto_play"
                self._policy_mode = True
            elif not target_script_id:
                self._policy_mode = True
            if self._running:
                self._state["target_script_id"] = self._target_script_id
                self._state["policy_mode"] = self._policy_mode
                return {"ok": True, "running": True, "target_script_id": self._target_script_id}

            self._running = True
            self._state["runtime_enabled"] = True
            self._state["target_script_id"] = self._target_script_id
            self._state["policy_mode"] = self._policy_mode
            self._register_event_callbacks()

        self._service.emit_local_event("runtime_status", {
            "status": "started",
            "target_script_id": self._target_script_id,
            "policy_mode": self._policy_mode,
        })
        return {"ok": True, "running": True, "target_script_id": self._target_script_id}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self._running = False
            self._state["runtime_enabled"] = False
            sub_id = self._sub_id
            self._sub_id = None
            handler_ids = list(self._handler_ids)
            self._handler_ids = []

        if sub_id is not None:
            self._service.unsubscribe(sub_id)
        for handler_id in handler_ids:
            try:
                self._service.remove_event_handler(handler_id)
            except Exception:
                pass

        self._service.emit_local_event("runtime_status", {"status": "stopped"})
        return {"ok": True, "running": False}

    def set_target_strategy(self, script_id: str) -> Dict[str, Any]:
        script_id = (script_id or "").strip()
        if not script_id:
            return {"ok": False, "error": "script_id is required"}

        with self._lock:
            self._target_script_id = script_id
            self._policy_mode = False
            self._state["target_script_id"] = script_id
            self._state["policy_mode"] = False

        self._service.emit_local_event("runtime_strategy_selected", {
            "script_id": script_id,
        })
        return {"ok": True, "script_id": script_id}

    def set_policy_mode(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            self._policy_mode = bool(enabled)
            self._state["policy_mode"] = bool(enabled)
        self._service.emit_local_event("runtime_policy_mode", {"enabled": bool(enabled)})
        return {"ok": True, "policy_mode": bool(enabled)}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "running": self._running,
                "state": dict(self._state),
            }

    def _run_loop(self) -> None:
        try:
            while True:
                with self._lock:
                    if not self._running:
                        break
                    event_queue = self._event_queue
                if event_queue is None:
                    time.sleep(0.05)
                    continue

                try:
                    message = event_queue.get(timeout=0.2)
                except Exception:
                    continue

                event = message.get("event", {})
                if not event:
                    continue

                try:
                    self._dispatcher.dispatch(event)
                except Exception as exc:
                    with self._lock:
                        self._state["last_error"] = str(exc)
                    self._service.emit_local_event("runtime_error", {
                        "message": str(exc),
                        "event": event.get("event"),
                    })
        finally:
            with self._lock:
                self._running = False
                self._state["runtime_enabled"] = False

    def _register_event_callbacks(self) -> None:
        """Prefer callback-style event handling; fall back to queue loop if unavailable."""
        self._handler_ids = []
        if hasattr(self._service, "add_event_handler"):
            hid = self._service.add_event_handler("*", self._on_event_callback)
            self._handler_ids.append(hid)
            return

        # Fallback path (legacy bridge service): consume via subscriber queue.
        self._sub_id, self._event_queue = self._service.subscribe()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PythonStrategyRuntime")
        self._thread.start()

    def _on_event_callback(self, event: Dict[str, Any]) -> None:
        with self._lock:
            if not self._running:
                return
        try:
            self._dispatcher.dispatch(event)
        except Exception as exc:
            with self._lock:
                self._state["last_error"] = str(exc)
            self._service.emit_local_event("runtime_error", {
                "message": str(exc),
                "event": event.get("event"),
            })

    def _on_start(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        with self._lock:
            self._state["self_race"] = payload.get("self_race")
            self._state["enemy_race"] = self._normalize_race_name(payload.get("enemy_race") or payload.get("initial_enemy_race"))
            self._state["enemy_count"] = payload.get("enemy_count")
            self._state["frame"] = event.get("frame", -1)
            self._state["own_units"] = payload.get("units", [])
            self._state["last_event"] = "onStart"

    def _on_start_initialized(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        with self._lock:
            self._state["is_1v1"] = payload.get("is_1v1")
            self._state["is_ffa"] = payload.get("is_ffa")
            self._state["last_event"] = "onStart_initialized"

    def _on_frame(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        with self._lock:
            self._state["frame"] = event.get("frame", -1)
            self._state["minerals"] = payload.get("minerals", 0)
            self._state["gas"] = payload.get("gas", 0)
            self._state["supply_used"] = payload.get("supply_used", 0)
            self._state["supply_total"] = payload.get("supply_total", 0)
            self._state["own_units"] = payload.get("own_units", self._state.get("own_units", []))
            self._state["enemy_units"] = payload.get("enemy_units", self._state.get("enemy_units", []))
            if payload.get("enemy_race"):
                self._state["enemy_race"] = self._normalize_race_name(payload.get("enemy_race"))
            if not self._state.get("enemy_race"):
                inferred_enemy_race = self._infer_enemy_race_from_units(self._state.get("enemy_units") or [])
                if inferred_enemy_race:
                    self._state["enemy_race"] = inferred_enemy_race
            self._state["last_event"] = "onFrame"
            target_script_id = self._select_target_script_locked()
            current_script_id = self._state.get("current_script_id")

        if not target_script_id:
            return
        if current_script_id == target_script_id:
            return
        if (time.monotonic() - self._last_switch_at) < self._switch_cooldown:
            return

        if script_runner.read_script(target_script_id) is None:
            self._service.emit_local_event("runtime_error", {
                "message": f"strategy script not found: {target_script_id}",
                "script_id": target_script_id,
            })
            return

        try:
            script_runner.run_script(target_script_id, self._service)
            self._last_switch_at = time.monotonic()
            self._service.emit_local_event("runtime_strategy_applied", {
                "script_id": target_script_id,
                "frame": event.get("frame", -1),
            })
        except Exception as exc:
            with self._lock:
                self._state["last_error"] = str(exc)
            self._service.emit_local_event("runtime_error", {
                "message": str(exc),
                "script_id": target_script_id,
            })

    def _on_end(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._state["frame"] = event.get("frame", -1)
            self._state["last_event"] = "onEnd"
            self._state["current_script_id"] = None
            self._state["own_units"] = []
            self._state["enemy_units"] = []

    def _on_script_status(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        status = payload.get("status")
        script_id = payload.get("script_id")
        with self._lock:
            if status == "started":
                self._state["current_script_id"] = script_id
            elif status == "stopped" and self._state.get("current_script_id") == script_id:
                self._state["current_script_id"] = None
            self._state["last_event"] = "script_status"

    def _on_unit_event(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._state["last_event"] = event.get("event")

    def _on_battle_judgement(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        tags = payload.get("tags", "")
        with self._lock:
            self._state["last_event"] = "battle_judgement"
            # 러시 경보 시 opening 강제 유지
            if self._policy_mode and isinstance(tags, str) and ("rush_alert" in tags or "enemy_pressure" in tags):
                race = self._state.get("self_race")
                enemy_race = self._state.get("enemy_race") or "Unknown"
                opening = self._resolve_opening_script(race, enemy_race)
                if opening and script_runner.read_script(opening) is not None:
                    self._target_script_id = opening
                    self._state["target_script_id"] = opening

    def _select_target_script_locked(self) -> str:
        """Decide target strategy script from current runtime state. Lock must be held."""
        if not self._policy_mode:
            return self._target_script_id

        race = self._state.get("self_race")
        enemy_race = self._state.get("enemy_race") or "Unknown"
        supply = int(self._state.get("supply_used") or 0)
        own_units = self._state.get("own_units") or []

        depot_types = {
            "Protoss": "Protoss_Nexus",
            "Terran": "Terran_Command_Center",
            "Zerg": "Zerg_Hatchery",
        }
        depot = depot_types.get(race)
        base_count = 0
        if depot:
            for unit in own_units:
                if unit.get("type") == depot and unit.get("completed", True):
                    base_count += 1

        opening = self._resolve_opening_script(race, enemy_race)
        decided = "auto_play"
        if opening and script_runner.read_script(opening) is not None:
            # 초반에는 기본 opening을 유지하고, 일정 시점 이후 auto_play 전환
            if supply < 24 and base_count < 2:
                decided = opening

        if decided != self._last_policy_decision:
            self._last_policy_decision = decided
            self._service.emit_local_event("runtime_policy_decision", {
                "script_id": decided,
                "race": race,
                "enemy_race": enemy_race,
                "supply_used": supply,
                "bases": base_count,
            })

        self._target_script_id = decided
        self._state["target_script_id"] = decided
        return decided

    def _resolve_opening_script(self, race: Optional[str], enemy_race: Optional[str]) -> Optional[str]:
        race_n = self._normalize_race_name(race)
        enemy_n = self._normalize_race_name(enemy_race)
        if not race_n:
            return None

        preferred = self._matchup_opening_defaults.get((race_n, enemy_n))
        if preferred and script_runner.read_script(preferred) is not None:
            return preferred

        fallback = self._race_opening_defaults.get(race_n)
        if fallback and script_runner.read_script(fallback) is not None:
            return fallback

        return "auto_play"

    def _infer_enemy_race_from_units(self, enemy_units: List[Dict[str, Any]]) -> Optional[str]:
        for unit in enemy_units:
            race = self._normalize_race_name(unit.get("race"))
            if race and race != "Unknown":
                return race

            utype = str(unit.get("type") or "")
            if not utype:
                continue
            token = utype.replace("_", " ").strip().split(" ", 1)[0]
            race = self._normalize_race_name(token)
            if race and race != "Unknown":
                return race
        return None

    def _normalize_race_name(self, race: Optional[Any]) -> Optional[str]:
        if race is None:
            return None
        r = str(race).strip().lower()
        if not r:
            return None
        if "protoss" in r:
            return "Protoss"
        if "terran" in r:
            return "Terran"
        if "zerg" in r:
            return "Zerg"
        if "unknown" in r or r == "u":
            return "Unknown"
        return None


_runtime = None
_runtime_lock = threading.Lock()


def get_strategy_runtime(bridge_service):
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = PythonStrategyRuntime(bridge_service)
        return _runtime
