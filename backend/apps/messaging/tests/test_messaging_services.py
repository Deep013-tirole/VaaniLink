"""
Tests for MessageService.
"""

import uuid

import pytest

from apps.accounts.models import User
from apps.common.exceptions import PermissionDeniedError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.services import ConversationService
from apps.messaging.models import Message
from apps.messaging.services import MessageService


@pytest.mark.django_db
class TestMessageService:
    def setup_method(self):
        self.user1 = User.objects.create_user(
            username="user_one",
            email="one@example.com",
            password="Password123!",
            display_name="User One",
        )
        self.user2 = User.objects.create_user(
            username="user_two",
            email="two@example.com",
            password="Password123!",
            display_name="User Two",
        )
        self.user3 = User.objects.create_user(
            username="user_three",
            email="three@example.com",
            password="Password123!",
            display_name="User Three",
        )
        self.conv, _ = ConversationService.get_or_create_direct_conversation(self.user1, self.user2)

    def test_send_message_creates_receipts_and_sequence(self):
        client_msg_id = uuid.uuid4()
        msg = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=client_msg_id,
            text="Hello from user 1! 😊",
        )
        assert msg.sequence_number == 1
        assert msg.original_text == "Hello from user 1! 😊"
        assert msg.receipts.count() == 1
        assert msg.receipts.first().user == self.user2

        # Second message increments sequence number
        msg2 = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user2,
            client_message_id=uuid.uuid4(),
            text="Reply from user 2! 👍",
        )
        assert msg2.sequence_number == 2
        assert msg2.receipts.count() == 1
        assert msg2.receipts.first().user == self.user1

    def test_send_message_idempotent_retry(self):
        client_msg_id = uuid.uuid4()
        msg1 = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=client_msg_id,
            text="Original send attempt",
        )
        # Identical client_message_id retried by client
        msg2 = MessageService.send_message(
            conversation_id=self.conv.id,
            sender=self.user1,
            client_message_id=client_msg_id,
            text="Original send attempt (retry)",
        )
        assert msg1.id == msg2.id
        assert Message.objects.filter(conversation=self.conv).count() == 1

    def test_send_message_non_member_forbidden(self):
        with pytest.raises(PermissionDeniedError) as exc:
            MessageService.send_message(
                conversation_id=self.conv.id,
                sender=self.user3,
                client_message_id=uuid.uuid4(),
                text="Unauthorized message",
            )
        assert exc.value.code == "NOT_A_CONVERSATION_MEMBER"

    def test_send_empty_message_rejected(self):
        with pytest.raises(AppValidationError) as exc:
            MessageService.send_message(
                conversation_id=self.conv.id,
                sender=self.user1,
                client_message_id=uuid.uuid4(),
                text="   ",
            )
        assert exc.value.code == "MESSAGE_TEXT_EMPTY"
