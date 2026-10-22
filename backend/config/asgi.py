"""
ASGI config for VaaniLink project.
Exposes ASGI callable as a module-level variable named `application`.
Configures ProtocolTypeRouter for HTTP and WebSocket traffic.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

import apps.realtime.routing  # noqa: E402
from apps.realtime.middleware import JwtAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddlewareStack(URLRouter(apps.realtime.routing.websocket_urlpatterns)),
    }
)
