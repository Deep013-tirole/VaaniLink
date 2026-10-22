"""
Tests for JwtAuthMiddleware in Django Channels.
"""

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.realtime.middleware import JwtAuthMiddleware


@pytest.mark.django_db
@pytest.mark.asyncio
class TestJwtAuthMiddleware:
    async def test_authenticate_via_query_string(self):
        user = await sync_to_async(User.objects.create_user)(
            username="ws_jwt_user",
            email="ws_jwt@example.com",
            display_name="WS User",
            password="Password123!",
        )

        token = str(AccessToken.for_user(user))

        scope = {
            "type": "websocket",
            "query_string": f"token={token}".encode(),
            "headers": [],
        }

        async def dummy_app(inner_scope, receive, send):
            return inner_scope["user"]

        middleware = JwtAuthMiddleware(dummy_app)
        authenticated_user = await middleware(scope, None, None)

        assert authenticated_user.is_authenticated
        assert authenticated_user.id == user.id

    async def test_authenticate_via_sec_websocket_protocol(self):
        user = await sync_to_async(User.objects.create_user)(
            username="ws_subprotocol_user",
            email="ws_sub@example.com",
            display_name="WS Sub User",
            password="Password123!",
        )

        token = str(AccessToken.for_user(user))

        scope = {
            "type": "websocket",
            "query_string": b"",
            "headers": [
                (b"sec-websocket-protocol", f"Bearer {token}".encode()),
            ],
        }

        async def dummy_app(inner_scope, receive, send):
            return inner_scope["user"]

        middleware = JwtAuthMiddleware(dummy_app)
        authenticated_user = await middleware(scope, None, None)

        assert authenticated_user.is_authenticated
        assert authenticated_user.id == user.id

    async def test_anonymous_when_no_token(self):
        scope = {
            "type": "websocket",
            "query_string": b"",
            "headers": [],
        }

        async def dummy_app(inner_scope, receive, send):
            return inner_scope["user"]

        middleware = JwtAuthMiddleware(dummy_app)
        authenticated_user = await middleware(scope, None, None)

        assert isinstance(authenticated_user, AnonymousUser)
        assert not authenticated_user.is_authenticated

    async def test_anonymous_when_invalid_token(self):
        scope = {
            "type": "websocket",
            "query_string": b"token=invalid_garbage_token_value",
            "headers": [],
        }

        async def dummy_app(inner_scope, receive, send):
            return inner_scope["user"]

        middleware = JwtAuthMiddleware(dummy_app)
        authenticated_user = await middleware(scope, None, None)

        assert isinstance(authenticated_user, AnonymousUser)
        assert not authenticated_user.is_authenticated
