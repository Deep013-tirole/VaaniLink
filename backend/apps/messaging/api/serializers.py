"""
Serializers for Messaging resources.
"""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSearchSerializer
from apps.messaging.models import Message


class MessageSendSerializer(serializers.Serializer):
    """
    Payload for sending a new message.
    """

    client_message_id = serializers.UUIDField(required=True)
    text = serializers.CharField(max_length=5000, required=True, allow_blank=False)
    reply_to_id = serializers.UUIDField(required=False, allow_null=True)


class MessageEditSerializer(serializers.Serializer):
    """
    Payload for editing an existing message.
    """

    text = serializers.CharField(max_length=5000, required=True, allow_blank=False)


class MessageSerializer(serializers.ModelSerializer):
    """
    Public representation of a Message.
    Preserves original_text as the immutable source of truth.
    Computes lifecycle status.
    """

    sender = UserSearchSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    translations = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "sender",
            "client_message_id",
            "sequence_number",
            "text",
            "original_text",
            "status",
            "detected_primary_language",
            "detected_script",
            "is_mixed_language",
            "is_romanized",
            "language_confidence",
            "translations",
            "reply_to_message_id",
            "reply_to",
            "version",
            "edited_at",
            "deleted_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_reply_to(self, obj: Message) -> dict | None:
        """Return preview snippet of the replied-to message."""
        if not obj.reply_to_message_id:
            return None
        r = obj.reply_to_message
        if not r:
            return None
        sender_name = r.sender.display_name if r.sender else "User"
        snippet = (
            "This message was deleted."
            if r.is_deleted
            else (r.original_text[:120] + "..." if len(r.original_text) > 120 else r.original_text)
        )
        return {
            "id": str(r.id),
            "sender_name": sender_name,
            "text": snippet,
        }

    def get_translations(self, obj: Message) -> list[dict]:
        """Return list of serialized display-layer translations for this message."""
        translations = obj.translations.all()
        return [
            {
                "id": str(t.id),
                "source_language": t.source_language,
                "target_language": t.target_language,
                "translated_text": t.translated_text,
                "provider": t.provider,
                "status": t.status,
                "confidence": t.confidence,
                "error_message": t.error_message,
                "created_at": t.created_at.isoformat(),
            }
            for t in translations
        ]

    def get_text(self, obj: Message) -> str:
        """Return 'This message was deleted.' if soft-deleted, else original text."""
        if obj.is_deleted:
            return "This message was deleted."
        return obj.original_text

    def get_status(self, obj: Message) -> str:
        request = self.context.get("request")
        viewer_id = request.user.id if request else None
        return obj.get_status_for_user(viewer_id)


# Alias for explicit detail serializer naming
MessageDetailSerializer = MessageSerializer


class MessageDeliveredSerializer(serializers.Serializer):
    """
    Payload for acknowledging delivery of one or more messages.
    """

    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        required=True,
    )


class ConversationSeenSerializer(serializers.Serializer):
    """
    Payload for acknowledging reading messages in a conversation.
    """

    up_to_message_id = serializers.UUIDField(required=False, allow_null=True)
    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
