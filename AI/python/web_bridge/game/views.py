import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import bridge_service


# ── 대시보드 ───────────────────────────────────────────────────────────────────
def dashboard(request):
    """메인 웹 대시보드 페이지."""
    return render(request, 'game/dashboard.html')


# ── REST API ──────────────────────────────────────────────────────────────────

def api_status(request):
    """게임 현재 상태를 JSON으로 반환."""
    state = bridge_service.get_game_state()
    return JsonResponse({
        'connected':   state['connected'],
        'frame':       state['last_frame'],
        'opening':     state['opening'],
        'mode':        state['mode'],
        'late_game':   state['late_game'],
        'race':        state['race'],
        'enemy_race':  state['enemy_race'],
        'strategies':  state['strategies'],
        'rx_log':      state['rx_log'][:100],   # DLL → Django 수신 이벤트
        'tx_log':      state['tx_log'][:100],   # Django → DLL 송신 액션
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_strategy_set(request):
    """전략 변경 명령을 C++ 봇에 전송.

    Request body (JSON):
        {"strategy_unit": "PvT_FFE"}   — 특정 전략 선택
        {"strategy": "auto"}            — 자동 전략 복귀
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': '잘못된 JSON'}, status=400)

    strategy_unit = body.get('strategy_unit', '').strip()
    strategy_auto = body.get('strategy', '').strip().lower() == 'auto'

    if not strategy_unit and not strategy_auto:
        return JsonResponse({'ok': False, 'error': 'strategy_unit 또는 strategy:auto 필요'}, status=400)

    payload = {'type': 'strategy_command'}
    if strategy_auto:
        payload['strategy_unit'] = 'auto'
        label = 'auto'
    else:
        payload['strategy_unit'] = strategy_unit
        label = strategy_unit

    ok = bridge_service.send_action(payload)
    if ok:
        return JsonResponse({'ok': True, 'message': f'전략 전송: {label}', 'strategy': label})
    else:
        return JsonResponse({'ok': False, 'error': 'UDP 전송 실패'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_send_text(request):
    """게임 채팅창에 텍스트 전송.

    Request body (JSON): {"text": "glhf"}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': '잘못된 JSON'}, status=400)

    text = body.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False, 'error': 'text 필드 필요'}, status=400)

    ok = bridge_service.send_action({'type': 'send_text', 'text': text})
    return JsonResponse({'ok': ok})


@csrf_exempt
@require_http_methods(['POST'])
def api_leave_game(request):
    """게임 퇴장 명령 전송."""
    ok = bridge_service.send_action({'type': 'leave_game'})
    return JsonResponse({'ok': ok})
