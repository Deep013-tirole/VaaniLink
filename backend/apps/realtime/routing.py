"""
WebSocket routing definitions.
Mounted at /ws/chat/
"""

from django.urls import re_path

from apps.realtime.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"^ws/chat/$", ChatConsumer.as_asgi()),
]
