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
]