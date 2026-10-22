"""
Custom User model and manager for VaaniLink.
Complies with Section 8 & Section 9:
- No profile photos
- UUID primary key
- Separate interface_language vs preferred_chat_language
- Initial-based avatar generation in UI
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Manager for custom User model with normalized email and username.
    """

    def create_user(self, username: str, email: str, password: str | None = None, **extra_fields):
        if not username:
            raise ValidationError("A username must be provided.")
        if not email:
            raise ValidationError("An email address must be provided.")

        username = username.strip().lower()
        email = self.normalize_email(email).lower()

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(
        self, username: str, email: str, password: str | None = None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for VaaniLink.
    Decouples interface language (UI menus) from preferred chat language (translations).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    username = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique public username handle (alphanumeric and underscores).",
    )
    email = models.EmailField(
        max_length=254,
        unique=True,
        db_index=True,
        help_text="User email address for account authentication and recovery.",
    )
    display_name = models.CharField(
        max_length=100,
        help_text="User display name used in chat interfaces and initial-based avatars.",
    )
    interface_language = models.ForeignKey(
        "languages.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interface_users",
        help_text="Language used for rendering application menus and UI text.",
    )
    preferred_chat_language = models.ForeignKey(
        "languages.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="chat_users",
        help_text="Language into which incoming messages are translated for this user.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether this user should be treated as active.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin site.",
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of user's last recorded online presence.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "display_name"]

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return f"{self.display_name} (@{self.username})"

    def clean(self):
        super().clean()
        if self.username:
            self.username = self.username.strip().lower()
        if self.email:
            self.email = self.email.strip().lower()
