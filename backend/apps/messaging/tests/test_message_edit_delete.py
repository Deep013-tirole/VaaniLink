"""
Unit and API integration tests for Message Edit, Delete, and Reply features.
Conforms strictly to Section 2, Section 12, and Section 13.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.exceptions import PermissionDeniedError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.services import ConversationService
from apps.messaging.api.serializers import MessageSerializer
from apps.messaging.services import MessageService


@pytest.mark.django_db
class TestMessageEditDeleteServices:
    def setup_method(self):
        self.user1 = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
            display_name="Alice",
        )
        self.user2 = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="Password123!",
            display_name="Bob",
        )
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.user1, self.user2)

    def test_sender_can_edit_own_message(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Initial text",
        )
        assert msg.version == 1
        assert msg.edited_at is None
        assert msg.original_text == "Initial text"

        edited = MessageService.edit_message(
            message_id=msg.id,
            sender=self.user1,
            new_text="Updated text with emoji 🎉",
        )
        assert edited.id == msg.id
        assert edited.version == 2
        assert edited.edited_at is not None
        assert edited.original_text == "Updated text with emoji 🎉"

    def test_non_sender_cannot_edit_message(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Alice's message",
        )
        with pytest.raises(PermissionDeniedError) as exc_info:
            MessageService.edit_message(
                message_id=msg.id,
                sender=self.user2,
                new_text="Bob trying to tamper",
            )
        assert exc_info.value.code == "MESSAGE_EDIT_FORBIDDEN"

    def test_cannot_edit_deleted_message(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Will be deleted",
        )
        MessageService.delete_message(message_id=msg.id, sender=self.user1)

        with pytest.raises(AppValidationError) as exc_info:
            MessageService.edit_message(
                message_id=msg.id,
                sender=self.user1,
                new_text="Try editing after delete",
            )
        assert exc_info.value.code == "CANNOT_EDIT_DELETED_MESSAGE"

    def test_edit_validates_empty_and_max_length(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Normal text",
        )
        with pytest.raises(AppValidationError) as exc_info:
            MessageService.edit_message(message_id=msg.id, sender=self.user1, new_text="   ")
        assert exc_info.value.code == "MESSAGE_TEXT_EMPTY"

        with pytest.raises(AppValidationError) as exc_info2:
            MessageService.edit_message(message_id=msg.id, sender=self.user1, new_text="A" * 5001)
        assert exc_info2.value.code == "MESSAGE_TOO_LONG"

    def test_sender_can_soft_delete_for_everyone(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Sensitive information to erase",
        )
        assert not msg.is_deleted
        assert msg.deleted_at is None

        deleted = MessageService.delete_message(message_id=msg.id, sender=self.user1)
        assert deleted.is_deleted
        assert deleted.deleted_at is not None

        # Check serialization tombstone
        serialized = MessageSerializer(deleted).data
        assert serialized["text"] == "This message was deleted."
        assert serialized["deleted_at"] is not None

    def test_non_sender_cannot_delete_message(self):
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Alice's note",
        )
        with pytest.raises(PermissionDeniedError) as exc_info:
            MessageService.delete_message(message_id=msg.id, sender=self.user2)
        assert exc_info.value.code == "MESSAGE_DELETE_FORBIDDEN"

    def test_reply_serialization(self):
        msg1 = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Question: How is the weather today?",
        )

        msg2 = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user2,
            client_message_id=uuid.uuid4(),
            text="Answer: It is very sunny! ☀️",
            reply_to_id=msg1.id,
        )

        assert msg2.reply_to_message_id == msg1.id
        serialized = MessageSerializer(msg2).data
        assert serialized["reply_to"] is not None
        assert serialized["reply_to"]["id"] == str(msg1.id)
        assert serialized["reply_to"]["sender_name"] == "Alice"
        assert "Question: How is the weather today?" in serialized["reply_to"]["text"]


@pytest.mark.django_db
class TestMessageEditDeleteAPI:
    def setup_method(self):
        self.user1 = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
            display_name="Alice",
        )
        self.user2 = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="Password123!",
            display_name="Bob",
        )
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.user1, self.user2)
        self.client = APIClient()

    def test_api_patch_edit_message(self):
        self.client.force_authenticate(user=self.user1)
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Hello before edit",
        )

        url = f"/api/v1/messages/{msg.id}/"
        response = self.client.patch(url, {"text": "Hello after edit ✨"}, format="json")
        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "Hello after edit ✨"
        assert data["version"] == 2
        assert data["edited_at"] is not None

    def test_api_delete_message(self):
        self.client.force_authenticate(user=self.user1)
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            text="Hello will delete",
        )

        url = f"/api/v1/messages/{msg.id}/"
        response = self.client.delete(url)
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == str(msg.id)
        assert data["deleted_at"] is not None

        # Fetch message again, verify text tombstone
        fetch_res = self.client.get(f"/api/v1/conversations/{self.conv.id}/messages/")
        assert fetch_res.status_code == 200
        msgs = fetch_res.json()
        assert len(msgs) == 1
        assert msgs[0]["text"] == "This message was deleted."
