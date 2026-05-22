import json
import queue

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .bridge import get_bridge_service


def _json_body(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


@require_GET
def dashboard(request):
    service = get_bridge_service()
    snapshot = service.snapshot()
    return render(request, "dashboard.html", {"initial_data": json.dumps(snapshot, ensure_ascii=False)})


@require_GET
def state_api(request):
    service = get_bridge_service()
    return JsonResponse(service.snapshot())


@require_GET
def event_stream(request):
    service = get_bridge_service()
    subscriber_id, event_queue = service.subscribe()
    snapshot = service.snapshot()

    def generate():
        try:
            yield f"data: {json.dumps({'kind': 'snapshot', **snapshot}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    message = event_queue.get(timeout=15)
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            service.unsubscribe(subscriber_id)

    response = StreamingHttpResponse(generate(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
@require_POST
def send_text_action(request):
    service = get_bridge_service()
    body = _json_body(request)
    text = str(body.get("text", "")).strip()
    if not text:
        return JsonResponse({"ok": False, "error": "text is required"}, status=400)
    action = {"type": "send_text", "text": text}
    service.send_action(action)
    return JsonResponse({"ok": True, "action": action})


@csrf_exempt
@require_POST
def unit_action(request):
    service = get_bridge_service()
    body = _json_body(request)
    action_type = str(body.get("type", "")).strip()
    if action_type not in {"unit_move", "unit_stop", "unit_attack_move", "unit_attack_unit"}:
        return JsonResponse({"ok": False, "error": "unsupported unit action"}, status=400)

    try:
        action = {"type": action_type, "unit_id": int(body.get("unit_id"))}
        if action_type in {"unit_move", "unit_attack_move"}:
            action["x"] = int(body.get("x"))
            action["y"] = int(body.get("y"))
        if action_type == "unit_attack_unit":
            action["target_unit_id"] = int(body.get("target_unit_id"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "invalid numeric fields"}, status=400)

    service.send_action(action)
    return JsonResponse({"ok": True, "action": action})


@csrf_exempt
@require_POST
def strategy_action(request):
    service = get_bridge_service()
    body = _json_body(request)
    opening = str(body.get("opening", "")).strip()
    if not opening:
        return JsonResponse({"ok": False, "error": "opening is required"}, status=400)
    action = {"type": "set_opening", "opening": opening}
    service.send_action(action)
    return JsonResponse({"ok": True, "action": action})


_ALLOWED_CONTROL_TYPES = {"gather_minerals", "set_auto_play", "set_manual"}


@csrf_exempt
@require_POST
def control_action(request):
    service = get_bridge_service()
    body = _json_body(request)
    action_type = str(body.get("type", "")).strip()
    if action_type not in _ALLOWED_CONTROL_TYPES:
        return JsonResponse({"ok": False, "error": f"unsupported control type: {action_type}"}, status=400)
    action = {"type": action_type}
    service.send_action(action)
    return JsonResponse({"ok": True, "action": action})