"""
Comprehensive security and authorization tests for VaaniLink (Phase 10 Hardening).
Verifies:
- Unauthenticated rejection across protected REST endpoints
- Token validation and signature tampering rejection
- Cross-tenant conversation data isolation (Section 10, 11, 46)
- Message tampering and horizontal privilege escalation prevention
- Section 43 error envelope consistency on 401/403/404/400
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.messaging.services import MessageService


@pytest.mark.django_db
class TestSecurityHardening:
    def setup_method(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
            display_name="Alice",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="Password123!",
            display_name="Bob",
        )
        self.eve = User.objects.create_user(
            username="eve_attacker",
            email="eve@example.com",
            password="Password123!",
            display_name="Eve Attacker",
        )
        # Direct conversation between Alice and Bob
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.alice, self.bob)
        self.client = APIClient()

    def test_unauthenticated_requests_rejected_with_error_envelope(self):
        """Unauthenticated requests to protected endpoints return 401/403 with Section 43 envelope."""
        protected_urls = [
            ("/api/v1/conversations/", "GET"),
            (f"/api/v1/conversations/{self.conv.id}/messages/", "GET"),
            ("/api/v1/privacy/", "GET"),
            ("/api/v1/blocks/", "GET"),
            ("/api/v1/messages/delivered/", "POST"),
        ]
        for url, method in protected_urls:
            if method == "GET":
                response = self.client.get(url)
            else:
                response = self.client.post(url, {})
            assert response.status_code in (401, 403), f"Failed for {method} {url}"
            data = response.json()
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]

    def test_tampered_jwt_token_rejected(self):
        """Forged or tampered JWT token headers are rejected."""
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.signature"
        )
        response = self.client.get("/api/v1/conversations/")
        assert response.status_code in (401, 403)
        data = response.json()
        assert "error" in data

    def test_non_member_cannot_read_messages(self):
        """Eve (non-member) cannot access messages of Alice and Bob's conversation."""
        self.client.force_authenticate(user=self.eve)
        url = f"/api/v1/conversations/{self.conv.id}/messages/"
        response = self.client.get(url)
        assert response.status_code in (403, 404)
        data = response.json()
        assert data["error"]["code"] in ("NOT_A_CONVERSATION_MEMBER", "CONVERSATION_NOT_FOUND")

    def test_non_member_cannot_send_messages(self):
        """Eve cannot post messages into a conversation she does not belong to."""
        self.client.force_authenticate(user=self.eve)
        url = f"/api/v1/conversations/{self.conv.id}/messages/"
        payload = {
            "client_message_id": str(uuid.uuid4()),
            "text": "Eve trying to inject message",
        }
        response = self.client.post(url, payload, format="json")
        assert response.status_code in (403, 404)
        data = response.json()
        assert data["error"]["code"] in ("NOT_A_CONVERSATION_MEMBER", "CONVERSATION_NOT_FOUND")

    def test_horizontal_privilege_escalation_edit_prevented(self):
        """Bob cannot edit Alice's message."""
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.alice,
            client_message_id=uuid.uuid4(),
            text="Alice's original message",
        )

        self.client.force_authenticate(user=self.bob)
        url = f"/api/v1/messages/{msg.id}/"
        response = self.client.patch(
            url, {"text": "Bob maliciously changing Alice's message"}, format="json"
        )
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "MESSAGE_EDIT_FORBIDDEN"

    def test_horizontal_privilege_escalation_delete_prevented(self):
        """Bob cannot delete Alice's message."""
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.alice,
            client_message_id=uuid.uuid4(),
            text="Alice's important message",
        )

        self.client.force_authenticate(user=self.bob)
        url = f"/api/v1/messages/{msg.id}/"
        response = self.client.delete(url)
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "MESSAGE_DELETE_FORBIDDEN"

    def test_malformed_json_payload_handled_gracefully(self):
        """Sending invalid JSON types or malformed bodies returns 400 with clean fields map."""
        self.client.force_authenticate(user=self.alice)
        url = f"/api/v1/conversations/{self.conv.id}/messages/"
        response = self.client.post(
            url, {"client_message_id": "not-a-uuid", "text": ""}, format="json"
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "fields" in data["error"]
