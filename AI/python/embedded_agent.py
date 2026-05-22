import json


def _to_int(payload: dict, key: str, default: int = -1) -> int:
    try:
        return int(payload.get(key, default))
    except Exception:
        return default


def handle_event(event_name: str, frame: int, payload_json: str):
    """
    Called from C++ DLL (in-process embedded Python 3.12).

    Return format:
    1) single action dict
       {"type": "send_text", "text": "hello"}

    2) list of action dicts
       [
         {"type": "unit_move", "unit_id": 11, "x": 3200, "y": 2400},
         {"type": "send_text", "text": "moved"}
       ]

    Supported action types in this sample bridge:
    - none
    - send_text
    - leave_game
    - unit_stop
    - unit_move
    - unit_attack_unit
    - unit_attack_move
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
    except Exception:
        payload = {}

    # Example 1: game start message
    if event_name == "onStart":
        return {"type": "send_text", "text": "Python 3.12 embedded bridge ready"}

    # Example 2: when our unit is created, move it once if position info exists
    if event_name == "onUnitCreate":
        unit_id = _to_int(payload, "unit_id")
        pos = payload.get("position", "")
        if unit_id >= 0 and "," in pos:
            try:
                x_str, y_str = pos.split(",", 1)
                x = int(x_str)
                y = int(y_str)
                # Move a little near spawn for easy visual verification
                return {"type": "unit_move", "unit_id": unit_id, "x": x + 64, "y": y + 64}
            except Exception:
                pass
        return {"type": "none"}

    # Example 3: simple periodic chat heartbeat
    if event_name == "onFrame" and frame > 0 and frame % (24 * 30) == 0:
        return {"type": "send_text", "text": f"python tick frame={frame}"}

    # Example 4: show multiple actions (optional)
    if event_name == "onNukeDetect":
        return [
            {"type": "send_text", "text": "Nuke detected by Python"},
        ]

    return {"type": "none"}
