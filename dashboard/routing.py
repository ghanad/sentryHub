from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/dashboard/realtime/$", consumers.AlertsConsumer.as_asgi(), name="ws-realtime-dashboard"),
]