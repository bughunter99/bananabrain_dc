"""
zmq_test_client.py  –  ZMQ 브리지 테스트 클라이언트
======================================================

zmq_agent.py 가 실행 중일 때 이 스크립트를 실행하면:
  - ZMQ SUB로 게임 이벤트를 구독해서 콘솔에 출력
  - 일정 조건에서 ZMQ PUSH로 액션을 전송

실행 순서
---------
  1) python zmq_agent.py      ← 브리지 기동
  2) python zmq_test_client.py ← 이 파일 실행 (게임 실행 전/후 무관)

연결 정보
---------
  SUB  → tcp://127.0.0.1:5555  (이벤트 수신)
  PUSH → tcp://127.0.0.1:5556  (액션 전송)
"""

import json
import sys
import datetime
import threading

try:
    import zmq
except ImportError:
    print("[ERROR] pyzmq 미설치. 다음 명령 실행: pip install pyzmq")
    sys.exit(1)

ZMQ_PUB_ADDR  = "tcp://127.0.0.1:5555"
ZMQ_PULL_ADDR = "tcp://127.0.0.1:5556"

# 구독할 이벤트 토픽 목록 (b"" 이면 전체)
SUBSCRIBE_TOPICS = [
    b"",          # 전체 이벤트 구독 (한 줄 주석 처리 후 개별 지정 가능)
    # b"onStart",
    # b"onEnd",
    # b"onUnitCreate",
    # b"onUnitDestroy",
    # b"onFrame",
]


def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str) -> None:
    print(f"[{now_str()}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 액션 전송 예시 – 별도 스레드에서 입력 대기
# ---------------------------------------------------------------------------
def input_loop(push_sock: zmq.Socket) -> None:
    """콘솔 입력으로 수동 액션 전송."""
    print("\n액션 전송 (Enter 로 실행):")
    print("  t <text>    : send_text")
    print("  m <id> <x> <y> : unit_move")
    print("  q           : 종료\n")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd == "q":
                break
            elif cmd == "t" and len(parts) >= 2:
                action = {"type": "send_text", "text": " ".join(parts[1:])}
            elif cmd == "m" and len(parts) == 4:
                action = {"type": "unit_move",
                          "unit_id": int(parts[1]),
                          "x": int(parts[2]),
                          "y": int(parts[3])}
            else:
                print("  모름:", line)
                continue
            push_sock.send_json(action)
            log(f"[PUSH] 전송: {action}")
        except Exception as exc:
            print(f"  오류: {exc}")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    ctx = zmq.Context()

    sub  = ctx.socket(zmq.SUB)
    push = ctx.socket(zmq.PUSH)

    sub.connect(ZMQ_PUB_ADDR)
    push.connect(ZMQ_PULL_ADDR)

    for topic in SUBSCRIBE_TOPICS:
        sub.setsockopt(zmq.SUBSCRIBE, topic)

    sub.setsockopt(zmq.RCVTIMEO, 300)   # 300 ms polling

    log(f"ZMQ SUB  연결: {ZMQ_PUB_ADDR}")
    log(f"ZMQ PUSH 연결: {ZMQ_PULL_ADDR}")
    log("이벤트 수신 대기 중 … (Ctrl+C 로 종료)")

    # 입력 스레드 시작
    t = threading.Thread(target=input_loop, args=(push,), daemon=True)
    t.start()

    try:
        while True:
            try:
                parts = sub.recv_multipart()
            except zmq.Again:
                continue
            except zmq.ZMQError as exc:
                log(f"[SUB] 오류: {exc}")
                continue

            if len(parts) != 2:
                continue

            topic = parts[0].decode("utf-8", errors="replace")
            try:
                data  = json.loads(parts[1].decode("utf-8"))
            except Exception:
                data  = {"raw": parts[1][:80].decode("utf-8", errors="replace")}

            frame   = data.get("frame", -1)
            payload = data.get("payload", {})

            # onFrame 은 요약만 출력 (240 프레임마다)
            if topic == "onFrame":
                if frame % 240 == 0:
                    log(f"[EVT] onFrame frame={frame}")
            else:
                log(f"[EVT] {topic:20s} frame={frame:6d}  payload={json.dumps(payload, ensure_ascii=False)[:120]}")

    except KeyboardInterrupt:
        log("종료")
    finally:
        sub.close()
        push.close()
        ctx.destroy(linger=0)


if __name__ == "__main__":
    main()
