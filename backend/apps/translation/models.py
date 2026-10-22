"""
Translation models for VaaniLink.
Conforms strictly to Section 1, Section 4, Section 5, Section 13, Section 25, Section 26, Section 47, Section 48, and Section 52:
- Decoupled display layer preserving original_text as source of truth
- Caching and fan-out support (one translation per message per target language)
- Auditability, confidence scoring, provider tracking, and failure status
- Translation feedback tracking
"""

import uuid

from django.db import models
from django.utils import timezone


class TranslationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class MessageTranslation(models.Model):
    """
    Persisted display-layer translation for a specific Message and target language.
    Guarantees UNIQUE(message, target_language) for multi-recipient fan-out optimization.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    message = models.ForeignKey(
        "messaging.Message",
        on_delete=models.CASCADE,
        related_name="translations",
        help_text="Reference to the immutable original Message.",
    )
    source_language = models.CharField(
        max_length=16,
        db_index=True,
        help_text="Source ISO language code (e.g., 'en', 'hi', 'gu').",
    )
    target_language = models.CharField(
        max_length=16,
        db_index=True,
        help_text="Target ISO language code (e.g., 'hi', 'en', 'gu').",
    )
    translated_text = models.TextField(
        help_text="Translated message text for display layer.",
    )
    provider = models.CharField(
        max_length=64,
        default="rule_based",
        help_text="Translation provider identifier (e.g., 'rule_based', 'google_cloud').",
    )
    status = models.CharField(
        max_length=20,
        choices=TranslationStatus.choices,
        default=TranslationStatus.COMPLETED,
        db_index=True,
        help_text="Current translation lifecycle status.",
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Translation engine quality / confidence score between 0.0 and 1.0.",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if translation failed or degraded.",
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
        db_table = "message_translations"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "target_language"],
                name="unique_message_target_language",
            ),
        ]
        indexes = [
            models.Index(fields=["message", "target_language"]),
            models.Index(fields=["source_language", "target_language"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Translation[{self.source_language}->{self.target_language} for Message {self.message_id}]"


class TranslationFeedback(models.Model):
    """
    Translation quality feedback provided by end users (Section 52).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    translation = models.ForeignKey(
        MessageTranslation,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="translation_feedback",
    )
    rating = models.SmallIntegerField(
        help_text="Rating score: +1 for accurate/helpful, -1 for inaccurate/poor.",
    )
    comment = models.TextField(
        null=True,
        blank=True,
        help_text="Optional user comment regarding the translation quality.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    class Meta:
        db_table = "translation_feedback"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["translation", "user"],
                name="unique_translation_user_feedback",
            ),
        ]

    def __str__(self) -> str:
        return f"Feedback[{self.user_id} on {self.translation_id}: {self.rating}]"
