"""
Tests for Messaging API endpoints.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService


@pytest.mark.django_db
class TestMessagingAPI:
    def setup_method(self):
        self.client = APIClient()
        self.me = User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        self.john = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="Password123!",
            display_name="John Smith",
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="Password123!",
            display_name="Outsider",
        )
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.me, self.john)

        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        self.token = login_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_send_message_success(self):
        client_msg_id = str(uuid.uuid4())
        payload = {
            "client_message_id": client_msg_id,
            "text": "Kal meeting attend kar lena please 😊",
        }
        response = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/", payload, format="json"
        )

        assert response.status_code == 201
        assert response.data["original_text"] == "Kal meeting attend kar lena please 😊"
        assert response.data["client_message_id"] == client_msg_id
        assert response.data["sequence_number"] == 1
        assert response.data["sender"]["username"] == "deepak"

    def test_send_message_idempotency(self):
        client_msg_id = str(uuid.uuid4())
        payload = {
            "client_message_id": client_msg_id,
            "text": "First attempt",
        }
        res1 = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/", payload, format="json"
        )
        res2 = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/", payload, format="json"
        )

        assert res1.status_code == 201
        assert res2.status_code == 201
        assert res1.data["id"] == res2.data["id"]
        assert res2.data["sequence_number"] == 1

    def test_list_messages_chronological_order(self):
        for i in range(1, 4):
            self.client.post(
                f"/api/v1/conversations/{self.conv.id}/messages/",
                {"client_message_id": str(uuid.uuid4()), "text": f"Message {i}"},
                format="json",
            )

        response = self.client.get(f"/api/v1/conversations/{self.conv.id}/messages/")
        assert response.status_code == 200
        assert len(response.data) == 3
        seqs = [m["sequence_number"] for m in response.data]
        assert seqs == [1, 2, 3]

    def test_non_member_cannot_view_or_send_messages(self):
        login_res = self.client.post(
            "/api/v1/auth/login/",
            {"username": "outsider", "password": "Password123!"},
            format="json",
        )
        outsider_token = login_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {outsider_token}")

        # Try GET
        get_res = self.client.get(f"/api/v1/conversations/{self.conv.id}/messages/")
        assert get_res.status_code == 403

        # Try POST
        post_res = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/",
            {"client_message_id": str(uuid.uuid4()), "text": "Intrusion"},
            format="json",
        )
        assert post_res.status_code == 403
