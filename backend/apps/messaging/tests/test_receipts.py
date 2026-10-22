"""
Tests for MessageReceipt and message acknowledgement lifecycle:
PENDING -> SENT -> DELIVERED -> SEEN
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.messaging.models import MessageReceipt
from apps.messaging.services import MessageService


@pytest.mark.django_db
class TestMessageReceipts:
    def test_delivery_and_seen_lifecycle(self):
        u1 = User.objects.create_user(
            username="receipt_sender",
            email="rs@example.com",
            display_name="Sender",
            password="Password123!",
        )
        u2 = User.objects.create_user(
            username="receipt_receiver",
            email="rr@example.com",
            display_name="Receiver",
            password="Password123!",
        )

        conv, _ = ConversationService.get_or_create_direct_conversation(u1, u2)

        # Send a message
        msg = MessageService.send_message(
            conversation_id=conv.id,
            sender=u1,
            client_message_id=uuid.uuid4(),
            text="Testing receipt progression",
        )

        # 1. State immediately after sending: SENT
        receipt = MessageReceipt.objects.get(message=msg, user=u2)
        assert receipt.delivered_at is None
        assert receipt.seen_at is None
        assert msg.get_status_for_user(u1.id) == "SENT"

        # 2. Mark DELIVERED
        delivered_results = MessageService.mark_messages_delivered(u2, [msg.id])
        assert len(delivered_results) == 1
        receipt.refresh_from_db()
        assert receipt.delivered_at is not None
        assert receipt.seen_at is None
        assert msg.get_status_for_user(u1.id) == "DELIVERED"

        # 3. Mark SEEN
        seen_results = MessageService.mark_messages_seen(
            user=u2,
            conversation_id=conv.id,
            up_to_message_id=msg.id,
        )
        assert len(seen_results) == 1
        receipt.refresh_from_db()
        assert receipt.seen_at is not None
        assert msg.get_status_for_user(u1.id) == "SEEN"

    def test_delivery_api_endpoint(self):
        u1 = User.objects.create_user(
            username="deliv_api_u1",
            email="dau1@example.com",
            display_name="DA U1",
            password="Password123!",
        )
        u2 = User.objects.create_user(
            username="deliv_api_u2",
            email="dau2@example.com",
            display_name="DA U2",
            password="Password123!",
        )
        conv, _ = ConversationService.get_or_create_direct_conversation(u1, u2)
        msg = MessageService.send_message(
            conversation_id=conv.id,
            sender=u1,
            client_message_id=uuid.uuid4(),
            text="Delivery endpoint test",
        )

        client = APIClient()
        client.force_authenticate(user=u2)

        res = client.post(
            "/api/v1/messages/delivered/",
            {"message_ids": [str(msg.id)]},
            format="json",
        )
        assert res.status_code == 200
        assert len(res.data["delivered"]) == 1

        receipt = MessageReceipt.objects.get(message=msg, user=u2)
        assert receipt.delivered_at is not None

    def test_seen_api_endpoint(self):
        u1 = User.objects.create_user(
            username="seen_api_u1",
            email="sau1@example.com",
            display_name="SA U1",
            password="Password123!",
        )
        u2 = User.objects.create_user(
            username="seen_api_u2",
            email="sau2@example.com",
            display_name="SA U2",
            password="Password123!",
        )
        conv, _ = ConversationService.get_or_create_direct_conversation(u1, u2)
        msg = MessageService.send_message(
            conversation_id=conv.id,
            sender=u1,
            client_message_id=uuid.uuid4(),
            text="Seen endpoint test",
        )

        client = APIClient()
        client.force_authenticate(user=u2)

        res = client.post(
            f"/api/v1/conversations/{conv.id}/seen/",
            {"up_to_message_id": str(msg.id)},
            format="json",
        )
        assert res.status_code == 200
        assert len(res.data["seen"]) == 1

        receipt = MessageReceipt.objects.get(message=msg, user=u2)
        assert receipt.seen_at is not None
        assert receipt.delivered_at is not None
