# examples/integrations/django_approvals/config/asgi.py
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
http = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import (  # noqa: E402
    AllowedHostsOriginValidator,
)

from approvals.ws import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": http,
        # X0.7: cookie-authenticated sockets check Origin, and the
        # consumer closes 1008 without an authenticated user.
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
