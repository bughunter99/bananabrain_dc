from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("events/stream/", views.event_stream, name="event-stream"),
    path("api/state/", views.state_api, name="state-api"),
    path("api/health/", views.health, name="health"),
    path("api/runtime/start/", views.runtime_start, name="runtime-start"),
    path("api/runtime/start", views.runtime_start, name="runtime-start-no-slash"),
    path("api/runtime/stop/", views.runtime_stop, name="runtime-stop"),
    path("api/runtime/stop", views.runtime_stop, name="runtime-stop-no-slash"),
    path("api/runtime/status/", views.runtime_status, name="runtime-status"),
    path("api/runtime/status", views.runtime_status, name="runtime-status-no-slash"),
    path("api/runtime/catalog/", views.runtime_catalog, name="runtime-catalog"),
    path("api/runtime/catalog", views.runtime_catalog, name="runtime-catalog-no-slash"),
    path("api/runtime/select/", views.runtime_select, name="runtime-select"),
    path("api/runtime/select", views.runtime_select, name="runtime-select-no-slash"),
    path("api/runtime/clear/", views.runtime_clear, name="runtime-clear"),
    path("api/runtime/clear", views.runtime_clear, name="runtime-clear-no-slash"),
    path("api/runtime/reload-openings/", views.runtime_reload_openings, name="runtime-reload-openings"),
    path("api/runtime/reload-openings", views.runtime_reload_openings, name="runtime-reload-openings-no-slash"),
    path("api/runtime/results/", views.runtime_results, name="runtime-results"),
    path("api/runtime/results", views.runtime_results, name="runtime-results-no-slash"),
    path("api/actions/send/", views.action_send, name="action-send"),
    path("api/actions/send", views.action_send, name="action-send-no-slash"),
    path("api/action/text/", views.send_text_action, name="send-text-action"),
    path("api/action/unit/", views.unit_action, name="unit-action"),
    path("api/action/control/", views.control_action, name="control-action"),
]
