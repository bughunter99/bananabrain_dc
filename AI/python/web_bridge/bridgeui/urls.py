from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("events/stream/", views.event_stream, name="event-stream"),
    path("api/state/", views.state_api, name="state-api"),
    path("api/action/text/", views.send_text_action, name="send-text-action"),
    path("api/action/unit/", views.unit_action, name="unit-action"),
    path("api/action/strategy/", views.strategy_action, name="strategy-action"),
    path("api/action/control/", views.control_action, name="control-action"),
    path("api/sysinfo/", views.sysinfo_api, name="sysinfo-api"),
    # Script editor
    path("scripts/", views.scripts_page, name="scripts-page"),
    path("api/scripts/<str:script_id>/", views.script_detail, name="script-detail"),
    path("api/scripts/<str:script_id>/run/", views.script_run, name="script-run"),
]