"""
Serializers for Conversation endpoints.
"""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSearchSerializer
from apps.accounts.models import User
from apps.common.exceptions import ConflictError, NotFoundError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.models import Conversation, ConversationMember, ConversationType


class ConversationMemberSerializer(serializers.ModelSerializer):
    user = UserSearchSerializer(read_only=True)

    class Meta:
        model = ConversationMember
        fields = ["id", "user", "role", "joined_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    direct_user = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "type",
            "group_name",
            "direct_user",
            "latest_message",
            "last_message_at",
            "created_at",
        ]

    def get_direct_user(self, obj: Conversation):
        """For DIRECT conversations, return the other participating user."""
        if obj.type != ConversationType.DIRECT:
            return None

        request = self.context.get("request")
        current_user_id = request.user.id if request else None

        for member in obj.members.all():
            if member.user_id != current_user_id:
                return UserSearchSerializer(member.user).data
        return None

    def get_latest_message(self, obj: Conversation):
        """Return preview snippet of the most recently sent message."""
        latest = obj.messages.order_by("-sequence_number").first()
        if not latest:
            return None

        return {
            "id": latest.id,
            "sender_id": latest.sender_id,
            "sender_username": latest.sender.username,
            "text_preview": (
                "This message was deleted." if latest.is_deleted else latest.original_text[:100]
            ),
            "created_at": latest.created_at,
            "sequence_number": latest.sequence_number,
        }


class ConversationDetailSerializer(serializers.ModelSerializer):
    members = ConversationMemberSerializer(many=True, read_only=True)
    direct_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "type",
            "group_name",
            "direct_key",
            "direct_user",
            "members",
            "last_message_at",
            "created_at",
        ]

    def get_direct_user(self, obj: Conversation):
        if obj.type != ConversationType.DIRECT:
            return None
        request = self.context.get("request")
        current_user_id = request.user.id if request else None
        for member in obj.members.all():
            if member.user_id != current_user_id:
                return UserSearchSerializer(member.user).data
        return None


class DirectConversationCreateSerializer(serializers.Serializer):
    """
    Payload for initiating or finding a direct 1-to-1 conversation.
    Accepts user_id (UUID) or username.
    """

    user_id = serializers.UUIDField(required=False)
    username = serializers.CharField(required=False)

    def validate(self, attrs: dict) -> dict:
        user_id = attrs.get("user_id")
        username = attrs.get("username")

        if not user_id and not username:
            raise AppValidationError(
                message="Either user_id or username must be provided.",
                code="TARGET_USER_REQUIRED",
            )

        target_user = None
        if user_id:
            target_user = User.objects.filter(id=user_id, is_active=True).first()
        elif username:
            target_user = User.objects.filter(
                username=username.strip().lower(), is_active=True
            ).first()

        if not target_user:
            raise NotFoundError(
                message="Target user does not exist or is inactive.",
                code="USER_NOT_FOUND",
            )

        request = self.context.get("request")
        if request and request.user.id == target_user.id:
            raise ConflictError(
                message="Cannot initiate a direct chat with yourself.",
                code="SELF_CONVERSATION_NOT_ALLOWED",
            )

        attrs["target_user"] = target_user
        return attrs


class GroupConversationCreateSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=150, min_length=1)
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class GroupRenameSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=150, min_length=1)


class GroupAddMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
    )


class GroupMemberActionSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True)
