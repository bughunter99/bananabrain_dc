import json
import queue
import socket
import threading
from collections import deque
from copy import deepcopy
from datetime import datetime
from itertools import count
from typing import Any, Deque, Dict, List, Optional, Tuple


UDP_HOST = "127.0.0.1"
UDP_EVENT_PORT = 37000
UDP_ACTION_PORT = 37001
MAX_RECENT_EVENTS = 300

REPRESENTATIVE_STRATEGIES = {
    "Protoss": [
        {"label": "PvZ 10/12 Gate", "opening": "PvZ_10/12gate", "summary": "무난한 기본 오프닝"},
        {"label": "PvZ Bisu", "opening": "PvZ_bisu", "summary": "운영형 커세어/하이템플러 계열"},
        {"label": "PvT 12 Nexus", "opening": "PvT_12nexus", "summary": "빠른 확장 중심"},
        {"label": "PvP 3 Gate Robo", "opening": "PvP_3gaterobo", "summary": "로보틱스 압박"},
        {"label": "PvU Forge", "opening": "PvU_forge", "summary": "범용 포지 기반 수비"},
    ],
    "Terran": [
        {"label": "TvZ 1 Rax FE", "opening": "TvZ_1raxfe", "summary": "정석 빠른 확장"},
        {"label": "TvZ 2 Rax", "opening": "TvZ_2rax", "summary": "초반 압박"},
        {"label": "TvT 1 Fact FE", "opening": "TvT_1factfe", "summary": "안정적인 메카 전개"},
        {"label": "TvP Siege Expand", "opening": "TvP_siegeexpand", "summary": "탱크 중심 운영"},
        {"label": "TvU 1 Fact", "opening": "TvU_1fact", "summary": "범용 팩토리 시작"},
    ],
    "Zerg": [
        {"label": "ZvZ 9 Pool Spire", "opening": "ZvZ_9poolspire", "summary": "뮤탈 전환형"},
        {"label": "ZvT 3 Hatch Muta", "opening": "ZvT_3hatchmuta", "summary": "클래식 뮤탈 운영"},
        {"label": "ZvT 9 Pool Lurker", "opening": "ZvT_9poollurker", "summary": "러커 타이밍"},
        {"label": "ZvP 9734", "opening": "ZvP_9734", "summary": "대표 히드라 타이밍"},
        {"label": "ZvU 9 Pool Speed", "opening": "ZvU_9poolspeed", "summary": "범용 스피드링"},
    ],
}


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
            "enemy_count": None,
            "is_replay": None,
            "is_1v1": None,
            "is_ffa": None,
            "opening": None,
            "mode": None,
            "frame": -1,
            "minerals": None,
            "gas": None,
            "supply_used": None,
            "supply_total": None,
            "manual_mode": None,
            "last_error": None,
        }
        self._subscribers = {}  # type: Dict[int, queue.Queue]
        self._subscriber_ids = count(1)
        self._event_ids = count(1)

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._state["status"] = f"listening {UDP_HOST}:{UDP_EVENT_PORT}"
            self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True, name="UdpBridgeService")
            self._listener_thread.start()

    def _listen_loop(self):
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind((UDP_HOST, UDP_EVENT_PORT))
        recv_sock.settimeout(0.25)
        self._recv_sock = recv_sock

        self.emit_local_event(
            "bridge_status",
            {
                "message": f"UDP bridge listening on {UDP_HOST}:{UDP_EVENT_PORT}",
                "action_port": UDP_ACTION_PORT,
            },
        )

        try:
            while self._running:
                try:
                    data, _ = recv_sock.recvfrom(65507)
                except socket.timeout:
                    continue
                except OSError as exc:
                    self._state["last_error"] = str(exc)
                    self.emit_local_event("bridge_error", {"message": str(exc)})
                    continue

                try:
                    decoded = json.loads(data.decode("utf-8"))
                except Exception as exc:
                    self.emit_local_event("bridge_parse_error", {"message": str(exc)})
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
            recv_sock.close()

    def _record_event(self, event):
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

    def _apply_event_to_state(self, event):
        payload = event.get("payload", {})
        event_name = event.get("event")

        if event_name == "onStart":
            self._state["status"] = "game connected"
            self._state["self_race"] = payload.get("self_race")
            self._state["enemy_count"] = payload.get("enemy_count")
            self._state["is_replay"] = payload.get("is_replay")
        elif event_name == "onStart_initialized":
            self._state["is_1v1"] = payload.get("is_1v1")
            self._state["is_ffa"] = payload.get("is_ffa")
            self._state["opening"] = payload.get("opening")
        elif event_name == "onFrame":
            self._state["minerals"] = payload.get("minerals")
            self._state["gas"] = payload.get("gas")
            self._state["supply_used"] = payload.get("supply_used")
            self._state["supply_total"] = payload.get("supply_total")
            self._state["mode"] = payload.get("mode")
        elif event_name == "onEnd":
            self._state["status"] = "game ended"
            self._state["winner"] = payload.get("winner")
            self._state["manual_mode"] = None
        elif event_name == "manual_mode_changed":
            self._state["manual_mode"] = payload.get("manual_mode") == "true"

    def emit_local_event(self, event_name, payload):
        event = {
            "id": next(self._event_ids),
            "time": iso_now(),
            "event": event_name,
            "frame": self._state.get("frame", -1),
            "payload": payload,
            "source": "web",
        }
        self._record_event(event)

    def send_action(self, action):
        self.start()
        payload = json.dumps(action, ensure_ascii=False).encode("utf-8")
        with self._lock:
            send_sock = self._send_sock
        if send_sock is None:
            raise RuntimeError("Action socket is not initialized")
        send_sock.sendto(payload, (UDP_HOST, UDP_ACTION_PORT))
        self.emit_local_event("ui_action_sent", {"action": action})

    def subscribe(self):
        self.start()
        subscriber_id = next(self._subscriber_ids)
        q = queue.Queue()
        with self._lock:
            self._subscribers[subscriber_id] = q
        return subscriber_id, q

    def unsubscribe(self, subscriber_id):
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def snapshot(self):
        self.start()
        with self._lock:
            state = deepcopy(self._state)
            events = list(self._recent_events)
        race = state.get("self_race")
        state["available_strategies"] = REPRESENTATIVE_STRATEGIES
        state["current_strategies"] = REPRESENTATIVE_STRATEGIES.get(race, [])
        return {"state": state, "events": events}


_service = None  # type: Optional[UdpBridgeService]
_service_lock = threading.Lock()


def get_bridge_service():
    global _service
    with _service_lock:
        if _service is None:
            _service = UdpBridgeService()
        _service.start()
        return _service