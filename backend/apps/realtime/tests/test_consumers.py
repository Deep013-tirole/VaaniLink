"""
Integration tests for ChatConsumer WebSocket events.
"""

import uuid

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from config.asgi import application


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumer:
    async def test_connect_unauthenticated_rejected(self):
        """Unauthenticated connections are rejected with code 4001."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 4001

    async def test_connect_authenticated_success(self):
        """Authenticated connection succeeds and registers presence."""
        user = await sync_to_async(User.objects.create_user)(
            username="ws_test_user",
            email="ws_test@example.com",
            display_name="WS User",
            password="Password123!",
        )
        token = str(AccessToken.for_user(user))

        communicator = WebsocketCommunicator(application, f"/ws/chat/?token={token}")
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_websocket_message_send_lifecycle(self):
        """Test sending a message over WebSocket, receiving message.sent, and verifying broadcast."""
        u1 = await sync_to_async(User.objects.create_user)(
            username="ws_sender",
            email="sender@example.com",
            display_name="Sender",
            password="Password123!",
        )
        u2 = await sync_to_async(User.objects.create_user)(
            username="ws_recipient",
            email="recipient@example.com",
            display_name="Recipient",
            password="Password123!",
        )

        conv, _ = await sync_to_async(ConversationService.get_or_create_direct_conversation)(u1, u2)

        token1 = str(AccessToken.for_user(u1))
        token2 = str(AccessToken.for_user(u2))

        # Connect both users
        comm1 = WebsocketCommunicator(application, f"/ws/chat/?token={token1}")
        comm2 = WebsocketCommunicator(application, f"/ws/chat/?token={token2}")

        connected1, _ = await comm1.connect()
        connected2, _ = await comm2.connect()
        assert connected1 and connected2

        # When User 2 connects, User 1 receives presence.changed for User 2
        presence_evt = await comm1.receive_json_from()
        assert presence_evt["event"] == "presence.changed"
        assert presence_evt["data"]["user_id"] == str(u2.id)
        assert presence_evt["data"]["is_online"] is True

        # User 1 sends message
        client_msg_id = str(uuid.uuid4())
        await comm1.send_json_to(
            {
                "event": "message.send",
                "request_id": "req-1",
                "data": {
                    "conversation_id": str(conv.id),
                    "client_message_id": client_msg_id,
                    "text": "Hello over WebSockets!",
                },
            }
        )

        # Sender should receive message.sent confirmation
        resp1 = await comm1.receive_json_from()
        assert resp1["event"] == "message.sent"
        assert resp1["request_id"] == "req-1"
        assert resp1["data"]["client_message_id"] == client_msg_id
        assert resp1["data"]["sequence_number"] == 1

        # Sender should also receive message.created broadcast from conversation room
        created_event_sender = await comm1.receive_json_from()
        assert created_event_sender["event"] == "message.created"
        assert created_event_sender["data"]["original_text"] == "Hello over WebSockets!"

        # Recipient should receive message.created broadcast
        resp2 = await comm2.receive_json_from()
        assert resp2["event"] == "message.created"
        assert resp2["data"]["original_text"] == "Hello over WebSockets!"

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_websocket_typing_indicator(self):
        """Test typing indicator dispatch to peer."""
        u1 = await sync_to_async(User.objects.create_user)(
            username="ws_type1",
            email="type1@example.com",
            display_name="Typer 1",
            password="Password123!",
        )
        u2 = await sync_to_async(User.objects.create_user)(
            username="ws_type2",
            email="type2@example.com",
            display_name="Typer 2",
            password="Password123!",
        )

        conv, _ = await sync_to_async(ConversationService.get_or_create_direct_conversation)(u1, u2)

        token1 = str(AccessToken.for_user(u1))
        token2 = str(AccessToken.for_user(u2))

        comm1 = WebsocketCommunicator(application, f"/ws/chat/?token={token1}")
        comm2 = WebsocketCommunicator(application, f"/ws/chat/?token={token2}")

        await comm1.connect()
        await comm2.connect()

        # Drain presence event for comm1
        _ = await comm1.receive_json_from()

        # User 1 starts typing
        await comm1.send_json_to(
            {
                "event": "typing.start",
                "data": {"conversation_id": str(conv.id)},
            }
        )

        # User 2 receives typing.started
        typing_event = await comm2.receive_json_from()
        assert typing_event["event"] == "typing.started"
        assert typing_event["data"]["conversation_id"] == str(conv.id)
        assert typing_event["data"]["user_id"] == str(u1.id)

        # User 1 stops typing
        await comm1.send_json_to(
            {
                "event": "typing.stop",
                "data": {"conversation_id": str(conv.id)},
            }
        )

        # User 2 receives typing.stopped
        stopped_event = await comm2.receive_json_from()
        assert stopped_event["event"] == "typing.stopped"
        assert stopped_event["data"]["user_id"] == str(u1.id)

        await comm1.disconnect()
        await comm2.disconnect()
