from django.urls import path

# Project-level websocket URL patterns aggregate app patterns.
# Each app can expose `websocket_urlpatterns`. We import and merge them here.
websocket_urlpatterns = []

try:
    from dashboard.routing import websocket_urlpatterns as dashboard_ws
    websocket_urlpatterns += dashboard_ws
except Exception:
    # If dashboard routing is not yet available at import time, we keep it empty.
    pass