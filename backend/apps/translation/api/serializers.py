"""
Serializers for Translation API conforming to Section 43 error envelope.
"""

from rest_framework import serializers

from apps.translation.models import MessageTranslation, TranslationFeedback


class MessageTranslationSerializer(serializers.ModelSerializer):
    """Serializer for persisted message translation display-layer entity."""

    message_id = serializers.UUIDField(source="message.id", read_only=True)

    class Meta:
        model = MessageTranslation
        fields = [
            "id",
            "message_id",
            "source_language",
            "target_language",
            "translated_text",
            "provider",
            "status",
            "confidence",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TranslationFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for translation feedback submissions."""

    user_id = serializers.UUIDField(source="user.id", read_only=True)
    translation_id = serializers.UUIDField(source="translation.id", read_only=True)

    class Meta:
        model = TranslationFeedback
        fields = [
            "id",
            "translation_id",
            "user_id",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "translation_id", "user_id", "created_at"]


class TranslationFeedbackInputSerializer(serializers.Serializer):
    """Input validation for submitting translation feedback."""

    rating = serializers.IntegerField(
        help_text="1 for positive/accurate, -1 for negative/inaccurate."
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        default="",
    )

    def validate_rating(self, value: int) -> int:
        if value not in [1, -1]:
            raise serializers.ValidationError(
                "Rating must be either 1 (accurate) or -1 (inaccurate)."
            )
        return value


class DirectTranslateRequestSerializer(serializers.Serializer):
    """Input validation for direct text translation sandbox/API."""

    text = serializers.CharField(max_length=5000)
    source_language = serializers.CharField(max_length=16, default="en", required=False)
    target_language = serializers.CharField(max_length=16, required=True)
    provider = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)


class DirectTranslateResponseSerializer(serializers.Serializer):
    """Response serializer for direct text translation."""

    translated_text = serializers.CharField()
    source_language = serializers.CharField()
    target_language = serializers.CharField()
    provider = serializers.CharField()
    confidence = serializers.FloatField()
    is_cached = serializers.BooleanField()
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True)
