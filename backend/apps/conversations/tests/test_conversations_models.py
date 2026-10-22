"""
Tests for Conversation and ConversationMember models.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.accounts.models import User
from apps.conversations.models import Conversation, ConversationMember, ConversationType, MemberRole


@pytest.mark.django_db
class TestConversationModels:
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

    def test_generate_direct_key_is_deterministic(self):
        key1 = Conversation.generate_direct_key(self.user1.id, self.user2.id)
        key2 = Conversation.generate_direct_key(self.user2.id, self.user1.id)
        assert key1 == key2
        sorted_uuids = sorted([str(self.user1.id), str(self.user2.id)])
        assert key1 == f"{sorted_uuids[0]}:{sorted_uuids[1]}"

    def test_direct_conversation_creation(self):
        key = Conversation.generate_direct_key(self.user1.id, self.user2.id)
        conv = Conversation.objects.create(
            type=ConversationType.DIRECT,
            direct_key=key,
            created_by=self.user1,
        )
        assert isinstance(conv.id, uuid.UUID)
        assert conv.type == ConversationType.DIRECT
        assert conv.direct_key == key

    def test_direct_conversation_unique_constraint(self):
        key = Conversation.generate_direct_key(self.user1.id, self.user2.id)
        Conversation.objects.create(
            type=ConversationType.DIRECT,
            direct_key=key,
            created_by=self.user1,
        )
        with pytest.raises(IntegrityError):
            Conversation.objects.create(
                type=ConversationType.DIRECT,
                direct_key=key,
                created_by=self.user2,
            )

    def test_direct_conversation_clean_validation(self):
        # Direct conv without direct_key raises error
        conv = Conversation(type=ConversationType.DIRECT, direct_key=None)
        with pytest.raises(ValidationError):
            conv.clean()

        # Direct conv with group_name raises error
        conv = Conversation(
            type=ConversationType.DIRECT,
            direct_key="key",
            group_name="Some Group",
        )
        with pytest.raises(ValidationError):
            conv.clean()

    def test_conversation_member_unique_constraint(self):
        key = Conversation.generate_direct_key(self.user1.id, self.user2.id)
        conv = Conversation.objects.create(type=ConversationType.DIRECT, direct_key=key)
        ConversationMember.objects.create(
            conversation=conv, user=self.user1, role=MemberRole.MEMBER
        )

        with pytest.raises(IntegrityError):
            ConversationMember.objects.create(
                conversation=conv, user=self.user1, role=MemberRole.ADMIN
            )
