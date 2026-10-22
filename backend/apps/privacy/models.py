"""
Privacy and Blocking Models.
Conforms strictly to docs/PRIVACY.md and docs/DATABASE.md:
- PrivacySetting (last_seen_visibility, online_status_visibility, read_receipts_enabled, who_can_message_me, who_can_add_me_to_groups)
- UserBlock (directional block with unique_together and blocker != blocked constraint)
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PrivacyVisibility(models.TextChoices):
    EVERYONE = "EVERYONE", "Everyone"
    CONTACTS_ONLY = "CONTACTS_ONLY", "Contacts Only"
    NOBODY = "NOBODY", "Nobody"


class PrivacySetting(models.Model):
    """
    Per-user privacy configurations.
    Defaults conform strictly to docs/PRIVACY.md.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="privacy_settings",
        primary_key=True,
    )
    last_seen_visibility = models.CharField(
        max_length=20,
        choices=PrivacyVisibility.choices,
        default=PrivacyVisibility.EVERYONE,
    )
    online_status_visibility = models.CharField(
        max_length=20,
        choices=PrivacyVisibility.choices,
        default=PrivacyVisibility.EVERYONE,
    )
    read_receipts_enabled = models.BooleanField(
        default=True,
        help_text="If False, suppresses emission of read/seen receipts to others.",
    )
    who_can_message_me = models.CharField(
        max_length=20,
        choices=PrivacyVisibility.choices,
        default=PrivacyVisibility.EVERYONE,
    )
    who_can_add_me_to_groups = models.CharField(
        max_length=20,
        choices=PrivacyVisibility.choices,
        default=PrivacyVisibility.EVERYONE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Privacy Setting"
        verbose_name_plural = "Privacy Settings"

    def __str__(self):
        return f"PrivacySettings for {self.user.username}"


class UserBlock(models.Model):
    """
    Directional user blocking record.
    When blocker blocks blocked:
    - blocked cannot send direct messages or initiate direct chats with blocker.
    - blocked cannot view blocker's online status or last seen timestamp.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_users",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "User Block"
        verbose_name_plural = "User Blocks"
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_user_block",
            ),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F("blocked")),
                name="prevent_self_block",
            ),
        ]
        indexes = [
            models.Index(fields=["blocker", "blocked"]),
        ]

    def clean(self):
        if self.blocker_id and self.blocked_id and self.blocker_id == self.blocked_id:
            raise ValidationError("Users cannot block themselves.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"
