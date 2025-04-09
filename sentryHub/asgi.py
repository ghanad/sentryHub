"""
ASGI config for sentryHub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import alerts.urls
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentryHub.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(alerts.urls.websocket_urlpatterns))),
})

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(alerts.urls.websocket_urlpatterns))),
})
