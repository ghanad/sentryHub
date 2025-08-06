"""
ASGI config for sentryHub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Channels setup
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')

django_asgi_app = get_asgi_application()

# Import project websocket routing
try:
    from .routing import websocket_urlpatterns as project_ws_patterns
except Exception:
    project_ws_patterns = []

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(project_ws_patterns)
    ),
})
