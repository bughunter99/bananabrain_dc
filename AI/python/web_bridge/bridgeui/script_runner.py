"""
Script runner for strategy Python scripts.
Each script lives in bridgeui/scripts/<id>.py and must define:
    def run(ctx): ...
The ctx object provides helpers to send commands to the C++ bot.
"""
import importlib.util
import os
import queue
import sys
import threading
import time
from datetime import datetime


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

# Ensure scripts directory is importable (for _helpers.py etc.)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# id -> running Thread
_running = {}
_running_lock = threading.Lock()


def _iso_now():
    return datetime.now().strftime("%H:%M:%S")


class ScriptContext:
    """Helper object passed into each strategy script's run() function."""

    def __init__(self, bridge_service, script_id):
        self._service = bridge_service
        self._script_id = script_id
        self._stopped = False
        # Subscribe to game events for sync-wait helpers
        self._event_sub_id, self._event_queue = bridge_service.subscribe()

    def _cleanup(self):
        """Unsubscribe from game events. Call when script finishes."""
        if self._event_sub_id is not None:
            self._service.unsubscribe(self._event_sub_id)
            self._event_sub_id = None
            self._event_queue = None

    # ------------------------------------------------------------------
    # Game state
    # ------------------------------------------------------------------

    def get_state(self):
        """Return the current game state snapshot dict."""
        return self._service.snapshot()["state"]

    def own_units(self):
        """List of own units from latest frame state."""
        return self.get_state().get("own_units", [])

    def workers(self):
        return [u for u in self.own_units() if u.get("is_worker")]

    def idle_workers(self):
        return [u for u in self.workers()
                if u.get("idle") and not u.get("constructing")]

    def units_of_type(self, unit_type):
        return [u for u in self.own_units() if u.get("type") == unit_type]

    def buildings_of_type(self, unit_type, completed_only=True):
        units = [u for u in self.own_units() if u.get("type") == unit_type]
        if completed_only:
            units = [u for u in units if u.get("completed", True)]
        return units

    def has_building(self, unit_type):
        return len(self.buildings_of_type(unit_type)) > 0

    def minerals(self):
        return self.get_state().get("minerals") or 0

    def gas(self):
        return self.get_state().get("gas") or 0

    def supply_used(self):
        return self.get_state().get("supply_used") or 0

    def supply_total(self):
        return self.get_state().get("supply_total") or 0

    def supply_free(self):
        return self.supply_total() - self.supply_used()

    # ------------------------------------------------------------------
    # Sync event waiting
    # ------------------------------------------------------------------

    def _wait_event(self, event_name, timeout=4.0):
        """Wait for a specific game event. Returns payload dict or None."""
        if self._event_queue is None:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._stopped:
                raise InterruptedError("script stopped")
            try:
                envelope = self._event_queue.get(timeout=0.1)
                event = envelope.get("event", {})
                if event.get("event") == event_name:
                    return event.get("payload", {})
            except queue.Empty:
                pass
        return None

    # ------------------------------------------------------------------
    # Build location / natural expansion (sync request-response)
    # ------------------------------------------------------------------

    def find_build_location_sync(self, worker_id, building_type):
        """Ask DLL for a build location. Returns (tile_x, tile_y) or None."""
        state = self.get_state()
        action = {
            "type": "find_build_location",
            "unit_id": worker_id,
            "building_type": building_type,
            "near_tile_x": state.get("start_tile_x", 64),
            "near_tile_y": state.get("start_tile_y", 40),
        }
        # Subscribe a fresh queue to avoid stale events
        sub_id, eq = self._service.subscribe()
        try:
            self._service.send_action(action)
            deadline = time.time() + 4.0
            while time.time() < deadline:
                if self._stopped:
                    raise InterruptedError("script stopped")
                try:
                    envelope = eq.get(timeout=0.1)
                    event = envelope.get("event", {})
                    if event.get("event") == "build_location_result":
                        p = event.get("payload", {})
                        if p.get("building_type") == building_type and p.get("ok"):
                            return (p.get("tile_x"), p.get("tile_y"))
                        return None
                except queue.Empty:
                    pass
            return None
        finally:
            self._service.unsubscribe(sub_id)

    def get_natural_expansion_sync(self):
        """Ask DLL for the nearest expansion tile. Returns (tile_x, tile_y) or None."""
        sub_id, eq = self._service.subscribe()
        try:
            self._service.send_action({"type": "get_natural_expansion"})
            deadline = time.time() + 4.0
            while time.time() < deadline:
                if self._stopped:
                    raise InterruptedError("script stopped")
                try:
                    envelope = eq.get(timeout=0.1)
                    event = envelope.get("event", {})
                    if event.get("event") == "natural_expansion_result":
                        p = event.get("payload", {})
                        if p.get("ok"):
                            return (p.get("tile_x"), p.get("tile_y"))
                        return None
                except queue.Empty:
                    pass
            return None
        finally:
            self._service.unsubscribe(sub_id)

    # ------------------------------------------------------------------
    # Action shortcuts
    # ------------------------------------------------------------------

    def build(self, worker_id, building_type, tile_x, tile_y):
        """Send worker to build a building at the given tile."""
        self._service.send_action({
            "type": "build",
            "unit_id": worker_id,
            "building_type": building_type,
            "tile_x": tile_x,
            "tile_y": tile_y,
        })

    def train(self, building_id, unit_type):
        """Train a unit from a building."""
        self._service.send_action({
            "type": "train_unit",
            "unit_id": building_id,
            "unit_type": unit_type,
        })

    def morph(self, unit_id, unit_type):
        """Morph a unit (Zerg: Hydra→Lurker, Hatchery→Lair, etc.)."""
        self._service.send_action({
            "type": "morph_unit",
            "unit_id": unit_id,
            "unit_type": unit_type,
        })

    def attack_move(self, unit_id, x, y):
        self._service.send_action({"type": "unit_attack_move", "unit_id": unit_id, "x": x, "y": y})

    def move(self, unit_id, x, y):
        self._service.send_action({"type": "unit_move", "unit_id": unit_id, "x": x, "y": y})

    def gather(self, unit_id, target_id):
        self._service.send_action({"type": "gather_unit", "unit_id": unit_id, "target_id": target_id})

    def gather_idle_workers(self):
        """Send all idle workers to gather minerals."""
        self._service.send_action({"type": "gather_minerals"})

    def set_rally(self, building_id, x, y):
        self._service.send_action({"type": "set_rally_point", "unit_id": building_id, "x": x, "y": y})

    # ------------------------------------------------------------------
    # Legacy API (kept for backward compatibility)
    # ------------------------------------------------------------------

    def set_opening(self, opening):
        """Tell the C++ bot to switch to the given opening (legacy)."""
        self._service.send_action({"type": "set_opening", "opening": opening})
        self.log("set_opening: {}".format(opening))

    def control(self, action_type, **kwargs):
        """Send a raw control action."""
        action = {"type": action_type}
        action.update(kwargs)
        self._service.send_action(action)
        self.log("control: {}".format(action_type))

    def send_text(self, text):
        self._service.send_action({"type": "send_text", "text": str(text)})

    def wait(self, seconds):
        """Sleep for the given number of seconds (interruptible)."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._stopped:
                raise InterruptedError("script stopped")
            time.sleep(0.05)

    def log(self, message):
        try:
            self._service.emit_local_event(
                "script_log",
                {"script_id": self._script_id, "message": str(message)},
            )
        except Exception:
            pass

    def stop(self):
        self._stopped = True


# ---------------------------------------------------------------------------

def _sanitize_id(opening):
    """Convert an opening string to a safe filename id (no slashes/dots)."""
    return opening.replace("/", "-").replace(".", "_")


def script_path(script_id):
    return os.path.join(SCRIPTS_DIR, script_id + ".py")


def list_scripts():
    """Return list of script ids (filenames without .py) in the scripts dir."""
    if not os.path.isdir(SCRIPTS_DIR):
        return []
    return sorted(
        f[:-3] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py") and not f.startswith("_")
    )


def read_script(script_id):
    path = script_path(script_id)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_script(script_id, content):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    path = script_path(script_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_script(script_id, bridge_service):
    """Load and execute a strategy script in a background thread."""
    path = script_path(script_id)
    if not os.path.isfile(path):
        raise FileNotFoundError("script not found: {}".format(script_id))

    # Stop any previously running script for this id
    with _running_lock:
        prev = _running.get(script_id)
        if prev and prev.is_alive():
            # signal stop via context stored as thread attribute
            ctx = getattr(prev, "_ctx", None)
            if ctx:
                ctx.stop()

    spec = importlib.util.spec_from_file_location("strategy_script_" + script_id, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ctx = ScriptContext(bridge_service, script_id)

    def _run():
        try:
            # Python이 게임을 완전히 제어 (manual_mode=true + python_mode=true)
            bridge_service.send_action({"type": "set_python_mode"})
            ctx.log("스크립트 시작 (Python 제어 모드)")
            mod.run(ctx)
            ctx.log("스크립트 완료")
        except InterruptedError:
            ctx.log("스크립트 중단됨")
        except Exception as exc:
            import traceback
            ctx.log("스크립트 오류: {}  /  {}".format(exc, traceback.format_exc().replace('\n', ' | ')))
        finally:
            try:
                bridge_service.send_action({"type": "clear_python_mode"})
            except Exception:
                pass
            ctx._cleanup()

    t = threading.Thread(target=_run, daemon=True, name="script_{}".format(script_id))
    t._ctx = ctx
    with _running_lock:
        _running[script_id] = t
    t.start()
    return t
