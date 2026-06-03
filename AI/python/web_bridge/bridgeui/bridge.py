from __future__ import annotations

import json
import queue
import socket
import threading
import time
from collections import deque
from copy import deepcopy
from datetime import datetime
from itertools import count
from typing import Any, Deque, Dict, List, Optional, Tuple


UDP_HOST = "127.0.0.1"
UDP_EVENT_PORT = 37000
UDP_ACTION_PORT = 37001
MAX_RECENT_EVENTS = 300


def iso_now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


class UdpBridgeService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._listener_thread = None  # type: Optional[threading.Thread]
        self._recv_sock = None  # type: Optional[socket.socket]
        self._send_sock = None  # type: Optional[socket.socket]
        self._recent_events = deque(maxlen=MAX_RECENT_EVENTS)  # type: Deque[Dict[str, Any]]
        self._state = {  # type: Dict[str, Any]
            "status": "idle",
            "connected": False,
            "last_event_at": None,
            "self_race": None,
            "enemy_race": None,
            "enemy_count": None,
            "is_replay": None,
            "is_1v1": None,
            "is_ffa": None,
            "frame": -1,
            "minerals": None,
            "gas": None,
            "supply_used": None,
            "supply_total": None,
            "start_tile_x": -1,
            "start_tile_y": -1,
            "map_width_tiles": 128,
            "map_height_tiles": 128,
            "enemy_start_locations": [],
            "mineral_fields": [],
            "geysers": [],
            "own_units": [],
            "enemy_units": [],
            "enemy_opening": None,
            "lost_worker_count": 0,
            "sent_initial_scout": False,
            "last_action": None,
            "last_strategy_command": None,
            "last_placement_policy": None,
            "last_error": None,
            "policy_running": False,
            "strategy_opening": None,
            "strategy_mode": None,
            "strategy_late_game": None,
            "strategy_decision": None,
        }
        self._subscribers = {}  # type: Dict[int, queue.Queue]
        self._subscriber_ids = count(1)
        self._event_ids = count(1)

    def start_listener(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._state["status"] = f"listening {UDP_HOST}:{UDP_EVENT_PORT}"
            self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True, name="UdpBridgeService")
            self._listener_thread.start()

    def stop_listener(self) -> None:
        with self._lock:
            self._running = False
            recv_sock = self._recv_sock
            send_sock = self._send_sock
            self._recv_sock = None
            self._send_sock = None

        for sock in (recv_sock, send_sock):
            if sock is None:
                continue
            try:
                sock.close()
            except OSError:
                pass

    def _listen_loop(self) -> None:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind((UDP_HOST, UDP_EVENT_PORT))
        recv_sock.settimeout(0.25)
        self._recv_sock = recv_sock

        self.emit_local_event(
            "bridge_status",
            {"message": f"UDP bridge listening on {UDP_HOST}:{UDP_EVENT_PORT}", "action_port": UDP_ACTION_PORT},
        )

        try:
            while True:
                with self._lock:
                    if not self._running:
                        break

                try:
                    data, _ = recv_sock.recvfrom(65507)
                except socket.timeout:
                    continue
                except OSError as exc:
                    self._state["last_error"] = str(exc)
                    self.emit_local_event("bridge_error", {"message": str(exc)})
                    continue

                try:
                    decoded = json.loads(data.decode("utf-8", errors="replace"))
                except Exception as exc:
                    self.emit_local_event("bridge_parse_error", {"message": str(exc)})
                    continue

                if not isinstance(decoded, dict):
                    continue

                event = {
                    "id": next(self._event_ids),
                    "time": iso_now(),
                    "event": decoded.get("event", "unknown"),
                    "frame": int(decoded.get("frame", -1)),
                    "payload": decoded.get("payload", {}),
                    "source": "game",
                }
                self._record_event(event)
        finally:
            try:
                recv_sock.close()
            except OSError:
                pass

    def _record_event(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._recent_events.append(event)
            self._state["connected"] = True
            self._state["last_event_at"] = event["time"]
            self._state["frame"] = event.get("frame", -1)
            self._apply_event_to_state(event)
            subscribers = list(self._subscribers.values())

        envelope = {"kind": "event", "event": event}
        for subscriber in subscribers:
            subscriber.put(envelope)

    def _apply_event_to_state(self, event: Dict[str, Any]) -> None:
        payload = event.get("payload", {})
        event_name = event.get("event")

        if event_name == "onStart":
            self._state["status"] = "game connected"
            self._state["self_race"] = payload.get("race") or payload.get("self_race")
            self._state["enemy_race"] = payload.get("enemy_race")
            self._state["enemy_count"] = payload.get("enemy_count")
            self._state["is_replay"] = payload.get("is_replay")
            self._state["start_tile_x"] = payload.get("start_tile_x", -1)
            self._state["start_tile_y"] = payload.get("start_tile_y", -1)
            self._state["map_width_tiles"] = payload.get("map_width_tiles", 128)
            self._state["map_height_tiles"] = payload.get("map_height_tiles", 128)
            self._state["enemy_start_locations"] = payload.get("enemy_start_locations", [])
            self._state["mineral_fields"] = payload.get("mineral_fields", [])
            self._state["geysers"] = payload.get("geysers", [])
            self._state["own_units"] = payload.get("units", [])
            if "own_units" in payload:
                self._state["own_units"] = payload["own_units"]
            self._state["enemy_units"] = payload.get("enemy_units", [])
            if "enemy_units" in payload:
                self._state["enemy_units"] = payload["enemy_units"]
        elif event_name == "onFrame":
            if payload.get("race"):
                self._state["self_race"] = payload.get("race")
            if payload.get("enemy_race"):
                self._state["enemy_race"] = payload.get("enemy_race")
            if payload.get("enemy_count") is not None:
                self._state["enemy_count"] = payload.get("enemy_count")
            self._state["minerals"] = payload.get("minerals")
            self._state["gas"] = payload.get("gas")
            self._state["supply_used"] = payload.get("supply_used")
            self._state["supply_total"] = payload.get("supply_total")
            self._state["strategy_mode"] = payload.get("mode", self._state.get("strategy_mode"))
            if "start_tile_x" in payload:
                self._state["start_tile_x"] = payload["start_tile_x"]
            if "start_tile_y" in payload:
                self._state["start_tile_y"] = payload["start_tile_y"]
            if "own_units" in payload:
                self._state["own_units"] = payload["own_units"]
            if "enemy_units" in payload:
                self._state["enemy_units"] = payload["enemy_units"]
            inferred_enemy_opening = self._infer_enemy_opening_from_units()
            if inferred_enemy_opening:
                self._state["enemy_opening"] = inferred_enemy_opening
        elif event_name == "onEnd":
            self._state["status"] = "game ended"
            self._state["winner"] = payload.get("winner")
            self._state["own_units"] = []
            self._state["enemy_units"] = []
            self._state["policy_running"] = False
        elif event_name == "onUnitDestroy":
            destroyed_type = str(payload.get("type") or "")
            destroyed_id = payload.get("id")
            self._state["own_units"] = [unit for unit in self._state.get("own_units", []) if str(unit.get("id")) != str(destroyed_id)]
            self._state["enemy_units"] = [unit for unit in self._state.get("enemy_units", []) if str(unit.get("id")) != str(destroyed_id)]
            if destroyed_type in {"Protoss_Probe", "Terran_SCV", "Zerg_Drone"}:
                own_unit_ids = {str(unit.get("id")) for unit in self._state.get("own_units", [])}
                enemy_unit_ids = {str(unit.get("id")) for unit in self._state.get("enemy_units", [])}
                if str(destroyed_id) not in enemy_unit_ids and str(destroyed_id) in own_unit_ids:
                    self._state["lost_worker_count"] = int(self._state.get("lost_worker_count") or 0) + 1
        elif event_name == "strategy_decision":
            self._state["policy_running"] = True
            self._state["strategy_opening"] = payload.get("opening")
            self._state["strategy_mode"] = payload.get("mode")
            self._state["strategy_late_game"] = payload.get("late_game_strategy")
            self._state["worker_cap"] = payload.get("worker_cap")
            self._state["strategy_decision"] = payload
        elif event_name == "strategy_started":
            self._state["policy_running"] = True
        elif event_name == "strategy_stopped":
            self._state["policy_running"] = False
        elif event_name == "strategy_scout":
            if payload.get("sent_initial_scout"):
                self._state["sent_initial_scout"] = True
        elif event_name == "ui_action_sent":
            action = payload.get("action") if isinstance(payload, dict) else None
            if isinstance(action, dict):
                self._state["last_action"] = action
                action_type = str(action.get("type") or "")
                if action_type == "strategy_command":
                    self._state["last_strategy_command"] = action
                elif action_type == "placement_policy":
                    self._state["last_placement_policy"] = action
        elif event_name == "ui_actions_sent":
            actions = payload.get("actions") if isinstance(payload, dict) else None
            if isinstance(actions, list) and actions:
                last_action = next((item for item in reversed(actions) if isinstance(item, dict)), None)
                if isinstance(last_action, dict):
                    self._state["last_action"] = last_action
                    action_type = str(last_action.get("type") or "")
                    if action_type == "strategy_command":
                        self._state["last_strategy_command"] = last_action
                    elif action_type == "placement_policy":
                        self._state["last_placement_policy"] = last_action

    def send_actions(self, actions: List[Dict[str, Any]]) -> None:
        payload = json.dumps(actions if len(actions) != 1 else actions[0], ensure_ascii=True)
        self.send_raw(payload)
        if len(actions) == 1:
            self.emit_local_event("ui_action_sent", {"action": actions[0]})
        else:
            self.emit_local_event("ui_actions_sent", {"actions": actions, "count": len(actions)})

    def send_raw(self, raw_json: str) -> None:
        self.start_listener()
        with self._lock:
            send_sock = self._send_sock
        if send_sock is None:
            raise RuntimeError("Action socket is not initialized")
        send_sock.sendto(raw_json.encode("utf-8"), (UDP_HOST, UDP_ACTION_PORT))

    def send_action(self, action: Dict[str, Any]) -> None:
        self.send_actions([action])

    def _parse_unit_entries(self, value: Any) -> List[Dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        text = str(value).strip()
        if not text:
            return []
        entries: List[Dict[str, Any]] = []
        for entry in text.split(";"):
            parts = entry.strip().split(",")
            if len(parts) < 2:
                continue
            try:
                entries.append({"id": int(parts[0]), "type": parts[1]})
            except ValueError:
                continue
        return entries

    def _infer_enemy_opening_from_units(self) -> str:
        units = self._parse_unit_entries(self._state.get("enemy_units"))
        if not units:
            return str(self._state.get("enemy_opening") or "")

        counts: Dict[str, int] = {}
        for unit in units:
            unit_type = str(unit.get("type") or "")
            if not unit_type:
                continue
            counts[unit_type] = counts.get(unit_type, 0) + 1

        if counts.get("Protoss_Photon_Cannon", 0) > 0 or counts.get("Protoss_Forge", 0) > 0:
            return "cannon"
        if counts.get("Protoss_Gateway", 0) >= 2 and counts.get("Protoss_Cybernetics_Core", 0) > 0:
            return "4gate"
        if counts.get("Protoss_Dark_Templar", 0) > 0 or counts.get("Protoss_Templar_Archives", 0) > 0:
            return "dt"

        if counts.get("Terran_Marine", 0) >= 3 or counts.get("Terran_Barracks", 0) >= 2:
            return "bio"
        if counts.get("Terran_Factory", 0) > 0 or counts.get("Terran_Siege_Tank_Tank_Mode", 0) > 0:
            return "mech"

        if counts.get("Zerg_Mutalisk", 0) > 0 or counts.get("Zerg_Spire", 0) > 0:
            return "muta"
        if counts.get("Zerg_Lurker", 0) > 0 or counts.get("Zerg_Hydralisk_Den", 0) > 0:
            return "lurker"
        if counts.get("Zerg_Zergling", 0) > 0 or counts.get("Zerg_Spawning_Pool", 0) > 0:
            return "pool"

        return str(self._state.get("enemy_opening") or "")

    def subscribe(self):
        self.start_listener()
        subscriber_id = next(self._subscriber_ids)
        q = queue.Queue()
        with self._lock:
            self._subscribers[subscriber_id] = q
        return subscriber_id, q

    def unsubscribe(self, subscriber_id: int) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def emit_local_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        event = {
            "id": next(self._event_ids),
            "time": iso_now(),
            "event": event_name,
            "frame": self._state.get("frame", -1),
            "payload": payload,
            "source": "web",
        }
        with self._lock:
            self._recent_events.append(event)
            self._apply_event_to_state(event)
            subscribers = list(self._subscribers.values())
        envelope = {"kind": "event", "event": event}
        for subscriber in subscribers:
            subscriber.put(envelope)

    def snapshot(self) -> Dict[str, Any]:
        self.start_listener()
        with self._lock:
            state = deepcopy(self._state)
            events = list(self._recent_events)
        return {"state": state, "events": events}


bridge_service = UdpBridgeService()
