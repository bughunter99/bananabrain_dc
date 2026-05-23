"""
Script runner for strategy Python scripts.
Each script lives in bridgeui/scripts/<id>.py and must define:
    def run(ctx): ...
The ctx object provides helpers to send commands to the C++ bot.
"""
import importlib.util
import os
import threading
import time
from datetime import datetime


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

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

    def set_opening(self, opening):
        """Tell the C++ bot to switch to the given opening."""
        self._service.send_action({"type": "set_opening", "opening": opening})
        self.log("set_opening: {}".format(opening))

    def control(self, action_type, **kwargs):
        """Send a control action (gather_minerals, set_auto_play, set_manual, scout, block_entrance …)."""
        action = {"type": action_type}
        action.update(kwargs)
        self._service.send_action(action)
        self.log("control: {}".format(action_type))

    def send_text(self, text):
        """Send in-game chat."""
        self._service.send_action({"type": "send_text", "text": str(text)})

    def wait(self, seconds):
        """Sleep for the given number of seconds (blocks the script thread)."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._stopped:
                raise InterruptedError("script stopped")
            time.sleep(0.1)

    def log(self, message):
        """Broadcast a log event visible in the dashboard event log."""
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
            ctx.log("스크립트 시작")
            mod.run(ctx)
            ctx.log("스크립트 완료")
        except InterruptedError:
            ctx.log("스크립트 중단됨")
        except Exception as exc:
            ctx.log("스크립트 오류: {}".format(exc))

    t = threading.Thread(target=_run, daemon=True, name="script_{}".format(script_id))
    t._ctx = ctx
    with _running_lock:
        _running[script_id] = t
    t.start()
    return t
