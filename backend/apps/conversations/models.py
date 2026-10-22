"""
Conversation and ConversationMember models.
Conforms strictly to Section 10, Section 46, Section 47, and Section 51:
- Deterministic direct_key for 1-to-1 chats
- Strict database uniqueness for direct conversations
- Role-based membership
- Optimized indexes for conversation and member lookups
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ConversationType(models.TextChoices):
    DIRECT = "DIRECT", "Direct"
    GROUP = "GROUP", "Group"


class MemberRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"


class Conversation(models.Model):
    """
    Conversation entity supporting 1-to-1 direct chats and multi-user groups.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    type = models.CharField(
        max_length=10,
        choices=ConversationType.choices,
        default=ConversationType.DIRECT,
        db_index=True,
    )
    direct_key = models.CharField(
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Deterministic key sorted(user1_uuid, user2_uuid) for 1-to-1 chats.",
    )
    group_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Display title for group conversations.",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_conversations",
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp of the most recently sent message in this conversation.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "conversations_conversation"
        ordering = ["-last_message_at", "-created_at"]
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self) -> str:
        if self.type == ConversationType.DIRECT:
            return f"Direct Conversation ({self.id})"
        return f"Group: {self.group_name} ({self.id})"

    @staticmethod
    def generate_direct_key(user1_id: uuid.UUID | str, user2_id: uuid.UUID | str) -> str:
        """
        Generate deterministic direct_key by sorting UUID strings.
        Ensures exactly one 1-to-1 conversation exists between any two users.
        """
        u1, u2 = sorted([str(user1_id), str(user2_id)])
        return f"{u1}:{u2}"

    def clean(self):
        super().clean()
        if self.type == ConversationType.DIRECT:
            if not self.direct_key:
                raise ValidationError("Direct conversation requires a deterministic direct_key.")
            if self.group_name:
                raise ValidationError("Direct conversation cannot have a group_name.")
        elif self.type == ConversationType.GROUP:
            if not self.group_name or not self.group_name.strip():
                raise ValidationError("Group conversation requires a group_name.")
            if self.direct_key:
                raise ValidationError("Group conversation cannot have a direct_key.")


class ConversationMember(models.Model):
    """
    Membership record linking a user to a conversation.
    Tracks group roles, join timestamps, and read message markers.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER,
    )
    joined_at = models.DateTimeField(
        default=timezone.now,
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_read_message_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the latest message marked as read by this user.",
    )
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    is_muted = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "conversations_conversationmember"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_user_membership",
            )
        ]
        indexes = [
            models.Index(fields=["user", "conversation"], name="idx_conv_member_user_conv"),
            models.Index(fields=["conversation", "user"], name="idx_conv_member_conv_user"),
        ]
        verbose_name = "Conversation Member"
        verbose_name_plural = "Conversation Members"

    def __str__(self) -> str:
        return f"Member: {self.user.username} in {self.conversation_id} ({self.role})"
