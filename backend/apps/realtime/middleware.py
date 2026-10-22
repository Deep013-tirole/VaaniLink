"""
JWT Authentication Middleware for Django Channels WebSockets.
Extracts JWT Access Tokens from query parameters, Sec-WebSocket-Protocol, or Authorization header.
"""

import urllib.parse
import uuid

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User


@database_sync_to_async
def get_user_by_id(user_id: uuid.UUID | str) -> User | None:
    try:
        return User.objects.filter(id=user_id, is_active=True).first()
    except Exception:
        return None


class JwtAuthMiddleware(BaseMiddleware):
    """
    Custom ASGI middleware to authenticate WebSocket connections using SimpleJWT tokens.
    """

    async def __call__(self, scope, receive, send):
        # Default to AnonymousUser
        scope["user"] = AnonymousUser()

        token = None

        # 1. Check Query String: ?token=<access_token>
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            params = urllib.parse.parse_qs(query_string)
            token = params.get("token", [None])[0]

        # 2. Check WebSocket Subprotocol Header: Sec-WebSocket-Protocol: Bearer <token> or <token>
        if not token:
            headers = dict(scope.get("headers", []))
            subprotocols = headers.get(b"sec-websocket-protocol", b"").decode("utf-8")
            if subprotocols:
                parts = [p.strip() for p in subprotocols.split(",")]
                for part in parts:
                    if part.startswith("Bearer "):
                        token = part.split(" ", 1)[1].strip()
                        break
                    elif "." in part and len(part) > 30:
                        token = part
                        break

            # 3. Check Authorization Header: Authorization: Bearer <token>
            if not token:
                auth_header = headers.get(b"authorization", b"").decode("utf-8")
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ", 1)[1].strip()

        # If a token was provided, validate and load the active user
        if token:
            try:
                token_obj = AccessToken(token)
                user_id = token_obj.get("user_id")
                if user_id:
                    user = await get_user_by_id(user_id)
                    if user and user.is_active:
                        scope["user"] = user
            except Exception:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """Convenience wrapper for JwtAuthMiddleware."""
    return JwtAuthMiddleware(inner)
