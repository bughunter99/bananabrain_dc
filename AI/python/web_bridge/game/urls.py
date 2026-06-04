from django.urls import path
from . import views

urlpatterns = [
    path('',                     views.dashboard,         name='dashboard'),
    path('api/status/',          views.api_status,        name='api_status'),
    path('api/strategy/set/',    views.api_strategy_set,  name='api_strategy_set'),
    path('api/send_text/',       views.api_send_text,     name='api_send_text'),
    path('api/leave_game/',      views.api_leave_game,    name='api_leave_game'),
]
