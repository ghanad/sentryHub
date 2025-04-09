from django.urls import re_path
from channels.routing import URLRouter
from . import consumers

websocket_urlpatterns = URLRouter([
    re_path(r"ws/alerts/", consumers.AlertConsumer.as_asgi()),
])