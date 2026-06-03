from __future__ import annotations

import json
import queue
from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .bridge import bridge_service
from strategy.opening_loader import reload_opening_modules
from strategy_runtime import get_strategy_runtime


def _json_body(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    snapshot = bridge_service.snapshot()
    return render(request, "dashboard.html", {"initial_data": json.dumps(snapshot, ensure_ascii=False)})


@require_GET
def event_stream(_request: HttpRequest) -> StreamingHttpResponse:
    subscriber_id, event_queue = bridge_service.subscribe()
    snapshot = bridge_service.snapshot()

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
            bridge_service.unsubscribe(subscriber_id)

    response = StreamingHttpResponse(generate(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@require_GET
def state_api(_request: HttpRequest) -> JsonResponse:
    runtime = get_strategy_runtime(bridge_service)
    snapshot = bridge_service.snapshot()
    snapshot["runtime"] = runtime.status()
    return JsonResponse(snapshot)


@require_GET
def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True, "service": "ai_dc2-web-bridge", "bridge": bridge_service.snapshot()["state"].get("status")})


@csrf_exempt
@require_POST
def runtime_start(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    strategy = str(body.get("strategy_unit") or body.get("strategy") or "auto")
    runtime = get_strategy_runtime(bridge_service)
    result = runtime.start(strategy)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def runtime_stop(_request: HttpRequest) -> JsonResponse:
    runtime = get_strategy_runtime(bridge_service)
    result = runtime.stop()
    return JsonResponse(result)


@require_GET
def runtime_status(_request: HttpRequest) -> JsonResponse:
    runtime = get_strategy_runtime(bridge_service)
    return JsonResponse(runtime.status())


@require_GET
def runtime_catalog(_request: HttpRequest) -> JsonResponse:
    runtime = get_strategy_runtime(bridge_service)
    return JsonResponse({"ok": True, "catalog": runtime.catalog()})


@require_GET
def runtime_results(_request: HttpRequest) -> JsonResponse:
    """오프닝별 승패 통계 API."""
    runtime = get_strategy_runtime(bridge_service)
    stats = runtime._result_store.get_stats()
    summary = []
    for opening, entry in sorted(stats.items()):
        wins = entry.get("wins", 0)
        losses = entry.get("losses", 0)
        total = wins + losses
        summary.append({
            "opening": opening,
            "wins": wins,
            "losses": losses,
            "total": total,
            "win_rate": round(wins / total * 100, 1) if total > 0 else None,
        })
    return JsonResponse({"ok": True, "results": summary, "raw": stats})


@csrf_exempt
@require_POST
def runtime_select(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    runtime = get_strategy_runtime(bridge_service)

    result: Dict[str, Any] = {"ok": True}

    if "strategy_file" in body:
        file_result = runtime.select_strategy_file(str(body.get("strategy_file") or "").strip())
        if not file_result.get("ok"):
            return JsonResponse(file_result, status=400)
        result["strategy_file"] = file_result

    if "strategy_unit" in body or "strategy" in body:
        strategy_name = str(body.get("strategy_unit") or body.get("strategy") or "auto")
        result["strategy"] = runtime.set_strategy_override(strategy_name)

    if "mode" in body:
        result["mode"] = runtime.set_mode_override(str(body.get("mode") or ""))

    if "opening" in body:
        opening = str(body.get("opening") or "").strip()
        if not opening:
            return JsonResponse({"ok": False, "error": "opening is required when setting opening override"}, status=400)
        race = str(body.get("race") or body.get("self_race") or "").strip()
        if not race:
            state = bridge_service.snapshot().get("state") or {}
            race = str(state.get("self_race") or "Unknown")
        result["opening"] = runtime.set_opening_override(race, opening)

    result["status"] = runtime.status()
    return JsonResponse(result)


@csrf_exempt
@require_POST
def runtime_clear(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    runtime = get_strategy_runtime(bridge_service)
    kind = str(body.get("kind") or "all").strip().lower()
    race = str(body.get("race") or body.get("self_race") or "").strip()
    result = runtime.clear_overrides(kind=kind, race=race)
    result["status"] = runtime.status()
    return JsonResponse(result)


@csrf_exempt
@require_POST
def runtime_reload_openings(_request: HttpRequest) -> JsonResponse:
    reload_opening_modules()
    return JsonResponse({"ok": True, "reloaded": True})


@csrf_exempt
@require_POST
def action_send(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    if isinstance(body, list):
        actions = [item for item in body if isinstance(item, dict)]
    elif isinstance(body, dict):
        actions = [body]
    else:
        return JsonResponse({"ok": False, "error": "payload must be an object or array"}, status=400)

    if not actions:
        return JsonResponse({"ok": False, "error": "no actions provided"}, status=400)

    bridge_service.send_actions(actions)
    return JsonResponse({"ok": True, "count": len(actions), "actions": actions})


@csrf_exempt
@require_POST
def send_text_action(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    text = str(body.get("text", "")).strip()
    if not text:
        return JsonResponse({"ok": False, "error": "text is required"}, status=400)
    action = {"type": "send_text", "text": text}
    bridge_service.send_action(action)
    return JsonResponse({"ok": True, "action": action})


@csrf_exempt
@require_POST
def unit_action(request: HttpRequest) -> JsonResponse:
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

    bridge_service.send_action(action)
    return JsonResponse({"ok": True, "action": action})


@csrf_exempt
@require_POST
def control_action(request: HttpRequest) -> JsonResponse:
    body = _json_body(request)
    action_type = str(body.get("type", "")).strip()
    if action_type not in {"leave_game", "send_text"}:
        return JsonResponse({"ok": False, "error": f"unsupported control type: {action_type}"}, status=400)
    action = {"type": action_type}
    if action_type == "send_text":
        text = str(body.get("text", "")).strip()
        if not text:
            return JsonResponse({"ok": False, "error": "text is required"}, status=400)
        action["text"] = text
    bridge_service.send_action(action)
    return JsonResponse({"ok": True, "action": action})
