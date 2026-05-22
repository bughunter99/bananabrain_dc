"""
udp_agent.py  –  BananaBrain external agent over UDP
=====================================================
Receives game events from BananaBrain.dll (port 37000),
sends action responses back (port 37001).

Run before or after launching StarCraft – the bridge silently drops
packets if the agent is not running, and the agent just retries until
the game starts sending.

Protocol
--------
Event  (C++ → agent) : {"event":"onFrame","frame":1234,"payload":{...}}
Action (agent → C++) : {"type":"unit_move","unit_id":11,"x":3200,"y":2400}
                     | [{"type":"..."}, ...]   (list of actions)
                     | {"type":"none"}          (no-op)
"""

import json
import socket
import datetime

EVENT_LISTEN_PORT = 37000   # bind here to receive events from C++
ACTION_SEND_PORT  = 37001   # send actions to C++ on this port

HOST = "127.0.0.1"


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now_str()}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------

def none_action():
    return {"type": "none"}

def send_text(text: str):
    return {"type": "send_text", "text": text}

def unit_move(unit_id: int, x: int, y: int):
    return {"type": "unit_move", "unit_id": unit_id, "x": x, "y": y}

def unit_attack_move(unit_id: int, x: int, y: int):
    return {"type": "unit_attack_move", "unit_id": unit_id, "x": x, "y": y}

def unit_attack_unit(unit_id: int, target_unit_id: int):
    return {"type": "unit_attack_unit", "unit_id": unit_id, "target_unit_id": target_unit_id}

def unit_stop(unit_id: int):
    return {"type": "unit_stop", "unit_id": unit_id}


# ---------------------------------------------------------------------------
# Event handler  –  implement your agent logic here
# ---------------------------------------------------------------------------

def handle_event(event_name: str, frame: int, payload: dict) -> object:
    """
    Return a single action dict, a list of action dicts, or None / "none".

    Supported action types (same as embedded_agent.py):
        none, send_text, leave_game,
        unit_stop, unit_move, unit_attack_unit, unit_attack_move
    """
    if event_name == "onStart":
        log(f"Game started – bridge ready (frame {frame})")
        return send_text("UDP agent connected")

    if event_name == "onStart_initialized":
        log(f"Init complete: map={payload.get('map_name','?')} "
            f"race={payload.get('race','?')} vs {payload.get('enemy_race','?')}")
        return none_action()

    if event_name == "onEnd":
        won = payload.get("is_winner", "false").lower() == "true"
        log(f"Game ended – {'WON' if won else 'LOST'}")
        return none_action()

    if event_name == "shutdown":
        log("Received shutdown – stopping agent")
        return none_action()

    if event_name == "onFrame":
        # Called every 240 frames (~10 s at fastest speed).
        # Add periodic logic here.
        return none_action()

    if event_name == "onUnitCreate":
        unit_id = int(payload.get("unit_id", -1))
        log(f"Unit created: id={unit_id} type={payload.get('unit_type','?')}")
        return none_action()

    if event_name == "onUnitDestroy":
        return none_action()

    if event_name == "onUnitComplete":
        return none_action()

    return none_action()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind((HOST, EVENT_LISTEN_PORT))
    recv_sock.settimeout(1.0)   # 1-second timeout so KeyboardInterrupt works

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    log(f"UDP agent listening on {HOST}:{EVENT_LISTEN_PORT} "
        f"(sending actions to :{ACTION_SEND_PORT})")

    try:
        while True:
            try:
                data, _ = recv_sock.recvfrom(65507)
            except socket.timeout:
                continue

            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception as exc:
                log(f"parse error: {exc}")
                continue

            event_name = msg.get("event", "unknown")
            frame      = int(msg.get("frame", -1))
            payload    = msg.get("payload", {})

            try:
                result = handle_event(event_name, frame, payload)
            except Exception as exc:
                log(f"handle_event raised: {exc}")
                result = none_action()

            if result is None:
                result = none_action()

            action_bytes = json.dumps(result).encode("utf-8")
            send_sock.sendto(action_bytes, (HOST, ACTION_SEND_PORT))

            if event_name == "shutdown":
                break

    except KeyboardInterrupt:
        log("Interrupted – stopping agent")
    finally:
        recv_sock.close()
        send_sock.close()


if __name__ == "__main__":
    main()
