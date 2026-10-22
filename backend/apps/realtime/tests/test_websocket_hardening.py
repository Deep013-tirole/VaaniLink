"""
Hardened WebSocket edge cases and security tests (Phase 10 Hardening).
Verifies:
- Rejection of frames missing event
- Non-member attempt to join a conversation room
- Unauthorized edit / delete over WebSocket
- Authorized edit / delete over WebSocket with real-time broadcast
"""

import uuid

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.messaging.services import MessageService
from config.asgi import application


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocketHardening:
    async def test_missing_event_in_frame_returns_error(self):
        """Frames without 'event' return INVALID_FRAME error response."""
        user = await sync_to_async(User.objects.create_user)(
            username="ws_hardened_1",
            email="h1@example.com",
            display_name="H1",
            password="Password123!",
        )
        token = str(AccessToken.for_user(user))
        comm = WebsocketCommunicator(application, f"/ws/chat/?token={token}")
        connected, _ = await comm.connect()
        assert connected

        await comm.send_json_to({"request_id": "req-1", "data": {}})
        resp = await comm.receive_json_from()
        assert resp["event"] == "error"
        assert resp["data"]["code"] == "INVALID_FRAME"

        await comm.disconnect()

    async def test_non_member_cannot_join_conversation_room(self):
        """User cannot join a conversation room they do not belong to."""
        alice = await sync_to_async(User.objects.create_user)(
            username="alice_ws",
            email="alice_ws@example.com",
            display_name="Alice",
            password="Password123!",
        )
        bob = await sync_to_async(User.objects.create_user)(
            username="bob_ws",
            email="bob_ws@example.com",
            display_name="Bob",
            password="Password123!",
        )
        eve = await sync_to_async(User.objects.create_user)(
            username="eve_ws",
            email="eve_ws@example.com",
            display_name="Eve",
            password="Password123!",
        )
        conv, _ = await sync_to_async(ConversationService.get_or_create_direct_conversation)(
            alice, bob
        )

        token_eve = str(AccessToken.for_user(eve))
        comm = WebsocketCommunicator(application, f"/ws/chat/?token={token_eve}")
        connected, _ = await comm.connect()
        assert connected

        # Eve attempts to join Alice & Bob's conversation
        await comm.send_json_to(
            {
                "event": "conversation.join",
                "request_id": "req-join",
                "data": {"conversation_id": str(conv.id)},
            }
        )
        resp = await comm.receive_json_from()
        assert resp["event"] == "error"
        assert resp["data"]["code"] == "NOT_A_CONVERSATION_MEMBER"

        await comm.disconnect()

    async def test_websocket_edit_and_delete_permissions(self):
        """Sender can edit and delete own message; other users receive error."""
        alice = await sync_to_async(User.objects.create_user)(
            username="alice_ed",
            email="alice_ed@example.com",
            display_name="Alice",
            password="Password123!",
        )
        bob = await sync_to_async(User.objects.create_user)(
            username="bob_ed",
            email="bob_ed@example.com",
            display_name="Bob",
            password="Password123!",
        )
        conv, _ = await sync_to_async(ConversationService.get_or_create_direct_conversation)(
            alice, bob
        )

        msg = await sync_to_async(MessageService.send_message)(
            conversation_id=conv.id,
            sender=alice,
            client_message_id=uuid.uuid4(),
            text="Alice's test message",
        )

        token_alice = str(AccessToken.for_user(alice))
        token_bob = str(AccessToken.for_user(bob))

        comm_alice = WebsocketCommunicator(application, f"/ws/chat/?token={token_alice}")
        comm_bob = WebsocketCommunicator(application, f"/ws/chat/?token={token_bob}")

        await comm_alice.connect()
        await comm_bob.connect()

        # Flush initial presence notifications
        while not await comm_bob.receive_nothing():
            await comm_bob.receive_json_from()
        while not await comm_alice.receive_nothing():
            await comm_alice.receive_json_from()

        # 1. Bob attempts to edit Alice's message -> forbidden
        await comm_bob.send_json_to(
            {
                "event": "message.edit",
                "request_id": "req-edit-fail",
                "data": {"message_id": str(msg.id), "text": "Hacked text"},
            }
        )
        resp = await comm_bob.receive_json_from()
        assert resp["event"] == "error"
        assert resp["data"]["code"] == "MESSAGE_EDIT_FORBIDDEN"

        # 2. Alice edits her own message -> success and broadcasts to room
        await comm_alice.send_json_to(
            {
                "event": "message.edit",
                "request_id": "req-edit-ok",
                "data": {"message_id": str(msg.id), "text": "Alice's edited text ✨"},
            }
        )
        ack = await comm_alice.receive_json_from()
        assert ack["event"] == "message.edited_ack"
        assert ack["data"]["version"] == 2

        # Alice also receives room broadcast of message.edited
        alice_bcast = await comm_alice.receive_json_from()
        assert alice_bcast["event"] == "message.edited"

        # Bob receives message.edited broadcast
        bcast = await comm_bob.receive_json_from()
        assert bcast["event"] == "message.edited"
        assert bcast["data"]["id"] == str(msg.id)
        assert bcast["data"]["original_text"] == "Alice's edited text ✨"
        assert bcast["data"]["version"] == 2

        # 3. Alice deletes her message -> success and broadcasts
        await comm_alice.send_json_to(
            {
                "event": "message.delete",
                "request_id": "req-del-ok",
                "data": {"message_id": str(msg.id)},
            }
        )
        del_ack = await comm_alice.receive_json_from()
        assert del_ack["event"] == "message.deleted_ack"

        # Bob receives events from conversation room (including message.deleted)
        bob_events = []
        while not await comm_bob.receive_nothing():
            b_evt = await comm_bob.receive_json_from()
            bob_events.append(b_evt)

        del_event = next((e for e in bob_events if e["event"] == "message.deleted"), None)
        assert del_event is not None
        assert del_event["data"]["message_id"] == str(msg.id)

        await comm_alice.disconnect()
        await comm_bob.disconnect()
