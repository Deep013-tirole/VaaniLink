"""
Reusable abstract base models.
"""

import uuid

from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """
    Abstract model providing a UUID primary key.
    Ensures non-enumerable, globally unique entity identifiers.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract model providing automatic created_at and updated_at timestamps.
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        help_text="Timestamp when this entity was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this entity was last updated.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(models.Model):
    """
    Abstract model providing soft-deletion capability.
    Entities preserve audit history without exposing deleted content to standard queries.
    """

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when this entity was soft-deleted, or null if active.",
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """Return True if the entity is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the entity as soft-deleted."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self) -> None:
        """Restore a soft-deleted entity."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])
