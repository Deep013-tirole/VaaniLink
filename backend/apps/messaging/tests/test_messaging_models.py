"""
Tests for Message and MessageReceipt models.
"""

import uuid

import pytest
from django.db.utils import IntegrityError

from apps.accounts.models import User
from apps.conversations.models import Conversation, ConversationType
from apps.messaging.models import Message, MessageReceipt


@pytest.mark.django_db
class TestMessageModels:
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
        key = Conversation.generate_direct_key(self.user1.id, self.user2.id)
        self.conv = Conversation.objects.create(type=ConversationType.DIRECT, direct_key=key)

    def test_create_message_preserves_original_text(self):
        client_msg_id = uuid.uuid4()
        msg = Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            client_message_id=client_msg_id,
            sequence_number=1,
            original_text="me kal nahi aaunga 😊",
        )
        assert msg.original_text == "me kal nahi aaunga 😊"
        assert msg.version == 1
        assert not msg.is_deleted
        assert msg.sequence_number == 1

    def test_idempotency_constraint_unique_sender_client_message_id(self):
        client_msg_id = uuid.uuid4()
        Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            client_message_id=client_msg_id,
            sequence_number=1,
            original_text="First send",
        )
        # Attempt to insert same client_message_id for same sender
        with pytest.raises(IntegrityError):
            Message.objects.create(
                conversation=self.conv,
                sender=self.user1,
                client_message_id=client_msg_id,
                sequence_number=2,
                original_text="Retry send",
            )

    def test_sequence_number_unique_per_conversation(self):
        Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Msg 1",
        )
        with pytest.raises(IntegrityError):
            Message.objects.create(
                conversation=self.conv,
                sender=self.user2,
                client_message_id=uuid.uuid4(),
                sequence_number=1,
                original_text="Msg with duplicate sequence",
            )

    def test_message_receipt_unique_constraint(self):
        msg = Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Msg with receipt",
        )
        MessageReceipt.objects.create(message=msg, user=self.user2)

        with pytest.raises(IntegrityError):
            MessageReceipt.objects.create(message=msg, user=self.user2)
