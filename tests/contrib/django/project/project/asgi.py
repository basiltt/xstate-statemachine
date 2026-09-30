# tests/contrib/django/project/project/asgi.py
"""ASGI entry of the test project: HTTP + the Channels WebSocket routes."""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_asgi = get_asgi_application()

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter

    from shop.ws import websocket_urlpatterns

    application = ProtocolTypeRouter(
        {
            "http": django_asgi,
            "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        }
    )
except ImportError:  # pragma: no cover - [channels] not installed
    application = django_asgi
