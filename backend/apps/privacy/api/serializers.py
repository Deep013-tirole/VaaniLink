"""
Serializers for Privacy and Blocking endpoints.
"""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSearchSerializer
from apps.accounts.models import User
from apps.common.exceptions import ConflictError, NotFoundError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.privacy.models import PrivacySetting, UserBlock


class PrivacySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySetting
        fields = [
            "last_seen_visibility",
            "online_status_visibility",
            "read_receipts_enabled",
            "who_can_message_me",
            "who_can_add_me_to_groups",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class BlockedUserSerializer(serializers.ModelSerializer):
    user = UserSearchSerializer(source="blocked", read_only=True)
    blocked_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = UserBlock
        fields = ["id", "user", "blocked_at"]


class BlockUserActionSerializer(serializers.Serializer):
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
                message="Cannot block yourself.",
                code="CANNOT_BLOCK_SELF",
            )

        attrs["target_user"] = target_user
        return attrs
