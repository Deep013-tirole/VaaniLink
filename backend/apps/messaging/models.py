"""
Message and MessageReceipt models.
Conforms strictly to Section 12, Section 13, Section 25, Section 26, Section 51, and Section 52:
- Immutable original_text preservation
- Idempotency with UNIQUE(sender_id, client_message_id)
- Deterministic sequencing with UNIQUE(conversation_id, sequence_number)
- Granular per-recipient message receipts with UNIQUE(message_id, user_id)
"""

import uuid

from django.db import models
from django.utils import timezone


class Message(models.Model):
    """
    Core message entity preserving original text as the immutable source of truth.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    client_message_id = models.UUIDField(
        db_index=True,
        help_text="Client-generated UUID for deduplication and retry idempotency.",
    )
    sequence_number = models.PositiveIntegerField(
        db_index=True,
        help_text="Monotonically increasing sequence number per conversation.",
    )
    original_text = models.TextField(
        help_text="Immutable original message text entered by the sender.",
    )
    detected_primary_language = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        help_text="Detected ISO language code (e.g. 'hi', 'en', 'gu').",
    )
    detected_script = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Detected script code (e.g. 'Deva', 'Latn', 'Gujr').",
    )
    is_mixed_language = models.BooleanField(
        default=False,
        help_text="True if text contains code-mixing or multiple languages.",
    )
    is_romanized = models.BooleanField(
        default=False,
        help_text="True if text is Romanized vernacular (e.g. Hinglish).",
    )
    language_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score from 0.0 to 1.0 of the primary language detection.",
    )
    reply_to_message = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Message version, incremented when edited.",
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp of soft-deletion for everyone, or null if active.",
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
        db_table = "messaging_message"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "client_message_id"],
                name="unique_sender_client_message_id",
            ),
            models.UniqueConstraint(
                fields=["conversation", "sequence_number"],
                name="unique_conversation_sequence_number",
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="idx_msg_conv_created"),
            models.Index(fields=["sender"], name="idx_msg_sender"),
            models.Index(fields=["reply_to_message"], name="idx_msg_reply_to"),
        ]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self) -> str:
        return f"Message {self.id} (Seq: {self.sequence_number}) by {self.sender.username}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def get_status_for_user(self, viewer_id: uuid.UUID | str = None) -> str:
        """
        Compute high-level lifecycle status: PENDING -> SENT -> DELIVERED -> SEEN.
        Evaluates in-memory if receipts are prefetched, eliminating N+1 queries.
        """
        if (
            hasattr(self, "_prefetched_objects_cache")
            and "receipts" in self._prefetched_objects_cache
        ):
            receipts = [r for r in self.receipts.all() if str(r.user_id) != str(self.sender_id)]
            if not receipts:
                return "SENT"
            if any(r.seen_at for r in receipts):
                return "SEEN"
            if any(r.delivered_at for r in receipts):
                return "DELIVERED"
            return "SENT"

        receipts = self.receipts.exclude(user_id=self.sender_id)
        if not receipts.exists():
            return "SENT"

        # If any receipt has seen_at, it's SEEN (in direct chats or partially in groups)
        if receipts.filter(seen_at__isnull=False).exists():
            return "SEEN"
        if receipts.filter(delivered_at__isnull=False).exists():
            return "DELIVERED"
        return "SENT"


class MessageReceipt(models.Model):
    """
    Per-recipient acknowledgement tracking delivery and read timestamps.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="message_receipts",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    seen_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        default=timezone.now,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "messaging_messagereceipt"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_message_user_receipt",
            ),
        ]
        indexes = [
            models.Index(fields=["message", "user"], name="idx_receipt_msg_user"),
            models.Index(fields=["user", "seen_at"], name="idx_receipt_user_seen"),
        ]
        verbose_name = "Message Receipt"
        verbose_name_plural = "Message Receipts"

    def __str__(self) -> str:
        return f"Receipt for {self.user.username} on Msg {self.message_id}"
