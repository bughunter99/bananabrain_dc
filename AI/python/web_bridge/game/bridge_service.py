"""
UDP bridge service: C++ MsgBusBridge와 통신하는 서비스.

프로토콜:
  - C++ → Django  : UDP port 37000  (이벤트 수신)
  - Django → C++  : UDP port 37001  (액션 전송)

메시지 형식 (C++ 발신):
  {"event":"status","frame":1234,"payload":{"opening":"PvT_FFE","mode":"Opening",...}}

액션 형식 (Django 발신):
  {"type":"strategy_command","strategy_unit":"PvT_FFE"}
"""

import json
import socket
import threading
import time
from collections import deque
from typing import Any

# ── 포트 설정 (MsgBusBridge.h와 일치) ─────────────────────────────────────────
EVENT_LISTEN_PORT = 37000   # C++가 이벤트를 보내는 포트 (Django가 수신)
ACTION_SEND_PORT  = 37001   # Django가 액션을 보내는 포트 (C++가 수신)
TARGET_HOST       = '127.0.0.1'

# ── 게임 상태 공유 메모리 ──────────────────────────────────────────────────────
_state_lock = threading.Lock()
_game_state: dict[str, Any] = {
    'connected': False,
    'last_frame': -1,
    'last_seen': 0.0,
    'opening': '',
    'mode': '',
    'late_game': '',
    'race': '',
    'enemy_race': '',
    'strategies': [],   # available strategies list
    'rx_log': deque(maxlen=200),   # DLL → Django 수신 이벤트
    'tx_log': deque(maxlen=200),   # Django → DLL 송신 액션
}

# ── UDP 송신 소켓 ──────────────────────────────────────────────────────────────
_send_sock: socket.socket | None = None
_send_lock = threading.Lock()


def _init_send_sock():
    global _send_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _send_sock = s


def send_action(payload: dict) -> bool:
    """C++ 봇에 액션 JSON을 UDP로 전송한다."""
    global _send_sock
    if _send_sock is None:
        _init_send_sock()
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    try:
        with _send_lock:
            _send_sock.sendto(data, (TARGET_HOST, ACTION_SEND_PORT))
        # 송신 로그 기록
        entry = {
            'ts': time.strftime('%H:%M:%S'),
            'type': payload.get('type', ''),
            'payload': {k: v for k, v in payload.items() if k != 'type'},
        }
        with _state_lock:
            _game_state['tx_log'].appendleft(entry)
        return True
    except OSError:
        return False


# ── 이벤트 수신 루프 ───────────────────────────────────────────────────────────
def _handle_event(raw: str):
    """C++에서 수신한 이벤트 JSON을 파싱해 game_state를 갱신."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    event   = msg.get('event', '')
    frame   = msg.get('frame', -1)
    payload = msg.get('payload', {})

    with _state_lock:
        _game_state['connected'] = True
        _game_state['last_seen'] = time.time()
        _game_state['last_frame'] = frame

        log_entry = {'ts': time.strftime('%H:%M:%S'), 'frame': frame, 'event': event, 'payload': payload}
        _game_state['rx_log'].appendleft(log_entry)

        if event == 'status':
            _game_state['opening']   = payload.get('opening', _game_state['opening'])
            _game_state['mode']      = payload.get('mode',    _game_state['mode'])
            _game_state['late_game'] = payload.get('late_game', _game_state['late_game'])

        elif event == 'strategy_list':
            raw_csv = payload.get('strategies', '')
            _game_state['strategies']  = [s.strip() for s in raw_csv.split(',') if s.strip()]
            _game_state['opening']     = payload.get('selected', '')
            _game_state['race']        = payload.get('race', '')
            _game_state['enemy_race']  = payload.get('enemy_race', '')

        elif event in ('onEnd', 'shutdown'):
            _game_state['connected'] = False

        # player_left는 이미 rx_log에 기록됨 (위에서 appendleft)


def _listen_loop():
    """백그라운드 스레드: UDP 이벤트를 영속 수신."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((TARGET_HOST, EVENT_LISTEN_PORT))
    except OSError as e:
        with _state_lock:
            _game_state['rx_log'].appendleft(
                {'ts': time.strftime('%H:%M:%S'), 'frame': -1, 'event': 'bridge_error',
                 'payload': {'msg': f'포트 {EVENT_LISTEN_PORT} 바인드 실패: {e}'}}
            )
        return

    sock.settimeout(1.0)
    while True:
        try:
            data, _ = sock.recvfrom(65507)
            _handle_event(data.decode('utf-8', errors='replace'))
        except socket.timeout:
            # 연결 끊김 감지: 마지막 패킷으로부터 10초 이상 경과
            with _state_lock:
                if _game_state['connected'] and time.time() - _game_state['last_seen'] > 10:
                    _game_state['connected'] = False
        except OSError:
            break


# ── 공개 API ────────────────────────────────────────────────────────────────────────────────────
DEFAULT_LOG_SIZE = 100

def get_game_state() -> dict:
    """현재 게임 상태의 스냅샷(복사본)을 반환."""
    with _state_lock:
        state = dict(_game_state)
        state['rx_log'] = list(_game_state['rx_log'])
        state['tx_log'] = list(_game_state['tx_log'])
    return state


def start():
    """Django apps.py ready()에서 한 번 호출한다."""
    _init_send_sock()
    t = threading.Thread(target=_listen_loop, daemon=True, name='udp-event-listener')
    t.start()
