import json
import queue

try:
    import psutil as _psutil
except ImportError:
    _psutil = None
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .bridge import get_bridge_service, REPRESENTATIVE_STRATEGIES
from . import script_runner
from . import launcher as _launcher


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


_ALLOWED_CONTROL_TYPES = {"gather_minerals", "set_auto_play", "set_manual", "scout", "block_entrance"}


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


@require_GET
def sysinfo_api(request):
    if _psutil is None:
        return JsonResponse({"cpu": None, "mem": None, "disk_used": None, "disk_total": None, "disk_pct": None})
    disk = _psutil.disk_usage("/")
    return JsonResponse({
        "cpu": _psutil.cpu_percent(interval=None),
        "mem": _psutil.virtual_memory().percent,
        "disk_used": round(disk.used / (1024 ** 3), 1),
        "disk_total": round(disk.total / (1024 ** 3), 1),
        "disk_pct": disk.percent,
    })


# ---------------------------------------------------------------------------
# Script editor views
# ---------------------------------------------------------------------------

def _opening_to_script_id(opening):
    """Map an opening string to the script file id (no slashes/dots)."""
    return opening.replace("/", "-").replace(".", "_")


def _build_script_catalog():
    """Return list of dicts with race/label/opening/script_id/exists."""
    catalog = []
    for race, strategies in REPRESENTATIVE_STRATEGIES.items():
        for s in strategies:
            sid = _opening_to_script_id(s["opening"])
            catalog.append({
                "race": race,
                "label": s["label"],
                "opening": s["opening"],
                "summary": s.get("summary", ""),
                "script_id": sid,
                "exists": script_runner.read_script(sid) is not None,
            })
    return catalog


@require_GET
def scripts_page(request):
    catalog = _build_script_catalog()
    return render(request, "scripts.html", {"catalog_json": json.dumps(catalog, ensure_ascii=False)})


@csrf_exempt
def script_detail(request, script_id):
    """GET: return script source; POST: save script source."""
    # Validate script_id: only alphanum, dash, underscore, dot
    import re
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', script_id):
        return JsonResponse({"ok": False, "error": "invalid script id"}, status=400)

    if request.method == "GET":
        content = script_runner.read_script(script_id)
        if content is None:
            return JsonResponse({"ok": False, "error": "not found"}, status=404)
        return JsonResponse({"ok": True, "script_id": script_id, "content": content})

    if request.method == "POST":
        body = _json_body(request)
        content = body.get("content", "")
        script_runner.write_script(script_id, content)
        return JsonResponse({"ok": True, "script_id": script_id})

    return JsonResponse({"ok": False, "error": "method not allowed"}, status=405)


@csrf_exempt
@require_POST
def script_run(request, script_id):
    """Execute the strategy script in a background thread."""
    import re
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', script_id):
        return JsonResponse({"ok": False, "error": "invalid script id"}, status=400)

    service = get_bridge_service()
    try:
        script_runner.run_script(script_id, service)
    except FileNotFoundError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
    return JsonResponse({"ok": True, "script_id": script_id})


# ---------------------------------------------------------------------------
# Launcher views
# ---------------------------------------------------------------------------

@require_GET
def launcher_status(request):
    return JsonResponse(_launcher.status())


@csrf_exempt
@require_POST
def launcher_start(request):
    body = _json_body(request)
    debug = bool(body.get("debug", False))
    result = _launcher.launch_and_inject(debug=debug)
    status_code = 200 if result.get("ok") else 409
    return JsonResponse(result, status=status_code)


@csrf_exempt
@require_POST
def launcher_stop(request):
    result = _launcher.kill_starcraft()
    status_code = 200 if result.get("ok") else 409
    return JsonResponse(result, status=status_code)


@csrf_exempt
@require_POST
def launcher_inject(request):
    """이미 실행 중인 StarCraft 에 DLL 만 인젝션 (카오스 런처 연동용)."""
    body = _json_body(request)
    debug = bool(body.get("debug", False))
    result = _launcher.inject_into_running(debug=debug)
    status_code = 200 if result.get("ok") else 409
    return JsonResponse(result, status=status_code)