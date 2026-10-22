"""
Tests for Conversation API endpoints.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService


@pytest.mark.django_db
class TestConversationAPI:
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
        self.meet = User.objects.create_user(
            username="meet",
            email="meet@example.com",
            password="Password123!",
            display_name="Meet Patel",
        )

        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        self.token = login_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_direct_conversation_by_user_id(self):
        payload = {"user_id": str(self.john.id)}
        response = self.client.post("/api/v1/conversations/direct/", payload, format="json")

        assert response.status_code == 201
        assert response.data["type"] == "DIRECT"
        assert response.data["direct_user"]["username"] == "john"

        # Calling again returns 200 with same ID
        response2 = self.client.post("/api/v1/conversations/direct/", payload, format="json")
        assert response2.status_code == 200
        assert response2.data["id"] == response.data["id"]

    def test_create_direct_conversation_by_username(self):
        payload = {"username": "meet"}
        response = self.client.post("/api/v1/conversations/direct/", payload, format="json")

        assert response.status_code == 201
        assert response.data["direct_user"]["username"] == "meet"

    def test_create_direct_with_self_forbidden(self):
        payload = {"username": "deepak"}
        response = self.client.post("/api/v1/conversations/direct/", payload, format="json")

        assert response.status_code == 409
        assert response.data["error"]["code"] == "SELF_CONVERSATION_NOT_ALLOWED"

    def test_list_conversations(self):
        # Create conversations with John and Meet
        ConversationService.get_or_create_direct_conversation(self.me, self.john)
        ConversationService.get_or_create_direct_conversation(self.me, self.meet)

        response = self.client.get("/api/v1/conversations/")
        assert response.status_code == 200
        assert len(response.data) == 2
        usernames = [c["direct_user"]["username"] for c in response.data]
        assert "john" in usernames
        assert "meet" in usernames

    def test_conversation_detail(self):
        conv, _ = ConversationService.get_or_create_direct_conversation(self.me, self.john)

        response = self.client.get(f"/api/v1/conversations/{conv.id}/")
        assert response.status_code == 200
        assert response.data["id"] == str(conv.id)
        assert len(response.data["members"]) == 2
