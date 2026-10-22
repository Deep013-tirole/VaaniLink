"""
Language model definitions.
Provides database-driven language registry with capability flags.
"""

from django.db import models
from django.utils import timezone


class Language(models.Model):
    """
    Registry of supported languages and translation capability flags.
    Allows runtime configuration of language capabilities without hardcoding.
    """

    code = models.CharField(
        max_length=16,
        primary_key=True,
        help_text="Standard BCP 47 or ISO 639-1 language code (e.g. 'hi', 'en', 'gu', 'ar').",
    )
    name = models.CharField(
        max_length=100,
        help_text="English name of the language (e.g. 'Hindi', 'Gujarati').",
    )
    native_name = models.CharField(
        max_length=100,
        help_text="Native endonym of the language (e.g. 'हिन्दी', 'ગુજરાતી', 'العربية').",
    )
    script_code = models.CharField(
        max_length=10,
        help_text="ISO 15924 4-letter script code (e.g. 'Deva', 'Latn', 'Gujr', 'Arab').",
    )
    is_rtl = models.BooleanField(
        default=False,
        help_text="True if this language is written Right-to-Left (e.g. Arabic, Urdu, Persian).",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this language is enabled for display and selection.",
    )
    translation_enabled = models.BooleanField(
        default=True,
        help_text="Whether this language is enabled as a translation source/target.",
    )
    detection_enabled = models.BooleanField(
        default=True,
        help_text="Whether language detection supports identifying this language.",
    )
    transliteration_enabled = models.BooleanField(
        default=False,
        help_text="Whether transliteration between script and Latin is enabled.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Display priority order in language selectors (lower numbers first).",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "languages_language"
        ordering = ["sort_order", "name"]
        verbose_name = "Language"
        verbose_name_plural = "Languages"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
