"""
Tests for ConversationService.
"""

import pytest

from apps.accounts.models import User
from apps.common.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from apps.conversations.models import ConversationType
from apps.conversations.services import ConversationService


@pytest.mark.django_db
class TestConversationService:
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

    def test_get_or_create_direct_conversation(self):
        conv, created = ConversationService.get_or_create_direct_conversation(
            self.user1, self.user2
        )
        assert created
        assert conv.type == ConversationType.DIRECT
        assert conv.members.count() == 2

        # Second call returns existing conversation
        conv2, created2 = ConversationService.get_or_create_direct_conversation(
            self.user2, self.user1
        )
        assert not created2
        assert conv2.id == conv.id

    def test_cannot_create_direct_conversation_with_self(self):
        with pytest.raises(ConflictError) as exc:
            ConversationService.get_or_create_direct_conversation(self.user1, self.user1)
        assert exc.value.code == "SELF_CONVERSATION_NOT_ALLOWED"

    def test_get_conversation_for_user_checks_membership(self):
        conv, _ = ConversationService.get_or_create_direct_conversation(self.user1, self.user2)

        # Member can access
        assert ConversationService.get_conversation_for_user(conv.id, self.user1).id == conv.id

        # Non-member raises PermissionDeniedError
        with pytest.raises(PermissionDeniedError) as exc:
            ConversationService.get_conversation_for_user(conv.id, self.user3)
        assert exc.value.code == "NOT_A_CONVERSATION_MEMBER"

    def test_get_conversation_non_existent(self):
        import uuid

        with pytest.raises(NotFoundError) as exc:
            ConversationService.get_conversation_for_user(uuid.uuid4(), self.user1)
        assert exc.value.code == "CONVERSATION_NOT_FOUND"
