"""
zmq_agent.py  –  BananaBrain ZMQ bridge agent
===============================================

역할
----
  C++ ai_dc.dll(UDP) <──── zmq_agent.py ────> 외부 ZMQ 클라이언트
  
프로토콜
--------
  [C++ → Agent]  UDP recv  127.0.0.1:37000   JSON 이벤트
  [Agent → C++]  UDP send  127.0.0.1:37001   JSON 액션

  [Agent → 외부] ZMQ PUB   tcp://*:5555      게임 이벤트 발행
  [외부 → Agent] ZMQ PULL  tcp://*:5556      액션 수신

ZMQ PUB 메시지 형식
-------------------
  topic  : 이벤트 이름 (bytes)  예) b"onFrame", b"onStart"
  body   : JSON bytes          예) b'{"frame":1234,"payload":{...}}'

  수신 예 (Python):
    sub.setsockopt(zmq.SUBSCRIBE, b"")  # 전체 구독
    topic, body = sub.recv_multipart()
    data = json.loads(body)

ZMQ PULL 메시지 형식 (액션 전송)
----------------------------------
  단일 액션:
    push.send_json({"type":"unit_move","unit_id":11,"x":3200,"y":2400})
  복수 액션:
    push.send_json([{"type":"unit_move",...}, {"type":"send_text","text":"hi"}])
  지원 타입: none, send_text, leave_game,
             unit_stop, unit_move, unit_attack_unit, unit_attack_move

실행
----
  pip install pyzmq
  python zmq_agent.py
"""

import json
import socket
import datetime
import threading
import queue
import sys

try:
    import zmq
except ImportError:
    print("[ERROR] pyzmq 미설치. 다음 명령 실행: pip install pyzmq", flush=True)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
UDP_HOST           = "127.0.0.1"
UDP_EVENT_PORT     = 37000   # C++ → Agent : 이벤트 수신 (UDP bind)
UDP_ACTION_PORT    = 37001   # Agent → C++ : 액션 전송 (UDP send)

ZMQ_PUB_PORT       = 5555    # Agent → 외부 : 이벤트 발행 (ZMQ PUB)
ZMQ_PULL_PORT      = 5556    # 외부 → Agent : 액션 수신  (ZMQ PULL)

UDP_RECV_TIMEOUT   = 0.02    # 20 ms polling interval


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def log(msg: str) -> None:
    print(f"[{now_str()}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# ZMQ 발행 스레드
# ---------------------------------------------------------------------------
class ZmqPublisher(threading.Thread):
    """UDP로 수신한 게임 이벤트를 ZMQ PUB으로 발행."""

    def __init__(self, ctx: zmq.Context, pub_port: int):
        super().__init__(daemon=True, name="ZmqPublisher")
        self._pub = ctx.socket(zmq.PUB)
        self._pub.bind(f"tcp://*:{pub_port}")
        self._q: queue.Queue = queue.Queue()
        log(f"ZMQ PUB 바인딩: tcp://*:{pub_port}")

    def enqueue(self, event_name: str, frame: int, payload: dict) -> None:
        self._q.put((event_name, frame, payload))

    def run(self) -> None:
        while True:
            try:
                event_name, frame, payload = self._q.get(timeout=1.0)
            except queue.Empty:
                continue
            body = json.dumps({"frame": frame, "payload": payload},
                              ensure_ascii=False).encode("utf-8")
            topic = event_name.encode("utf-8")
            try:
                self._pub.send_multipart([topic, body])
            except zmq.ZMQError as exc:
                log(f"[PUB] 전송 오류: {exc}")


# ---------------------------------------------------------------------------
# ZMQ 수신 스레드 (액션)
# ---------------------------------------------------------------------------
class ZmqActionReceiver(threading.Thread):
    """ZMQ PULL로 액션을 수신해 큐에 적재."""

    def __init__(self, ctx: zmq.Context, pull_port: int):
        super().__init__(daemon=True, name="ZmqActionReceiver")
        self._pull = ctx.socket(zmq.PULL)
        self._pull.bind(f"tcp://*:{pull_port}")
        self._pull.setsockopt(zmq.RCVTIMEO, 200)   # 200 ms timeout
        self._q: queue.Queue = queue.Queue()
        log(f"ZMQ PULL 바인딩: tcp://*:{pull_port}")

    def get_action(self):
        """액션이 없으면 None 반환."""
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def run(self) -> None:
        while True:
            try:
                raw = self._pull.recv()
            except zmq.Again:
                continue
            except zmq.ZMQError as exc:
                log(f"[PULL] 수신 오류: {exc}")
                continue
            try:
                action = json.loads(raw.decode("utf-8"))
                self._q.put(action)
                name = action[0]["type"] if isinstance(action, list) else action.get("type", "?")
                log(f"[PULL] 액션 수신: {name}")
            except Exception as exc:
                log(f"[PULL] 파싱 오류: {exc}")


# ---------------------------------------------------------------------------
# 기본 이벤트 핸들러 (자체 응답 로직)
# ZMQ 액션이 없을 때 fallback으로 사용.
# ---------------------------------------------------------------------------
def default_handle(event_name: str, frame: int, payload: dict) -> object:
    """ZMQ 외부 액션이 없을 때 자체 처리 (필요시 여기 로직 추가)."""
    if event_name == "onStart":
        log(f"[EVT] 게임 시작 – race={payload.get('race','?')} vs {payload.get('enemy_race','?')}")
        return {"type": "send_text", "text": "ZMQ bridge ready"}

    if event_name == "onStart_initialized":
        log(f"[EVT] 초기화 완료 – map={payload.get('map_name','?')}")
        return {"type": "none"}

    if event_name == "onEnd":
        won = str(payload.get("is_winner", "false")).lower() == "true"
        log(f"[EVT] 게임 종료 – {'승리' if won else '패배'}")
        return {"type": "none"}

    if event_name == "onFrame" and frame % 240 == 0:
        log(f"[EVT] frame={frame}")

    return {"type": "none"}


# ---------------------------------------------------------------------------
# 메인 루프
# ---------------------------------------------------------------------------
def main() -> None:
    log("=" * 60)
    log("BananaBrain ZMQ Bridge Agent 시작")
    log(f"  UDP 이벤트 수신  : {UDP_HOST}:{UDP_EVENT_PORT}  ← C++ ai_dc.dll")
    log(f"  UDP 액션 전송    : {UDP_HOST}:{UDP_ACTION_PORT}  → C++ ai_dc.dll")
    log(f"  ZMQ PUB (이벤트) : tcp://*:{ZMQ_PUB_PORT}       → 외부 구독자")
    log(f"  ZMQ PULL (액션)  : tcp://*:{ZMQ_PULL_PORT}       ← 외부 컨트롤러")
    log("=" * 60)

    ctx = zmq.Context()
    publisher = ZmqPublisher(ctx, ZMQ_PUB_PORT)
    receiver  = ZmqActionReceiver(ctx, ZMQ_PULL_PORT)
    publisher.start()
    receiver.start()

    # UDP 소켓
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind((UDP_HOST, UDP_EVENT_PORT))
    recv_sock.settimeout(UDP_RECV_TIMEOUT)

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    log(f"UDP 수신 대기 중 … ({UDP_HOST}:{UDP_EVENT_PORT})")

    try:
        while True:
            # --- UDP 이벤트 수신 ---
            try:
                data, _ = recv_sock.recvfrom(65507)
            except socket.timeout:
                continue

            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception as exc:
                log(f"[UDP] 파싱 오류: {exc}")
                continue

            event_name = msg.get("event", "unknown")
            frame      = int(msg.get("frame", -1))
            payload    = msg.get("payload", {})

            # --- ZMQ PUB 발행 ---
            publisher.enqueue(event_name, frame, payload)

            # --- 액션 결정: ZMQ PULL 우선, 없으면 기본 핸들러 ---
            action = receiver.get_action()
            if action is None:
                action = default_handle(event_name, frame, payload)

            if action is None:
                action = {"type": "none"}

            # --- UDP 액션 전송 → C++ ---
            try:
                action_bytes = json.dumps(action, ensure_ascii=False).encode("utf-8")
                send_sock.sendto(action_bytes, (UDP_HOST, UDP_ACTION_PORT))
            except Exception as exc:
                log(f"[UDP] 전송 오류: {exc}")

    except KeyboardInterrupt:
        log("종료 (Ctrl+C)")
    finally:
        recv_sock.close()
        send_sock.close()
        ctx.destroy(linger=0)


if __name__ == "__main__":
    main()
