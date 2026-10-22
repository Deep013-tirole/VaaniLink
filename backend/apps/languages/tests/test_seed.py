"""
Tests for seed_languages management command.
"""

import pytest
from django.core.management import call_command

from apps.languages.models import Language


@pytest.mark.django_db
class TestSeedLanguagesCommand:
    def test_seed_command_populates_languages(self):
        # Run seed command
        call_command("seed_languages")

        # Verify key languages from Section 6 exist
        expected_codes = ["hi", "en", "gu", "mr", "bn", "ur", "ar", "es", "fr", "de", "zh", "ja"]
        for code in expected_codes:
            assert Language.objects.filter(code=code).exists(), (
                f"Language '{code}' missing from seed."
            )

        # Verify RTL flags
        assert Language.objects.get(code="ar").is_rtl
        assert Language.objects.get(code="ur").is_rtl
        assert Language.objects.get(code="fa").is_rtl
        assert not Language.objects.get(code="hi").is_rtl
        assert not Language.objects.get(code="en").is_rtl

        # Verify transliteration flags for Romanized Indic
        assert Language.objects.get(code="hi").transliteration_enabled
        assert Language.objects.get(code="gu").transliteration_enabled

    def test_seed_command_idempotency(self):
        call_command("seed_languages")
        first_count = Language.objects.count()

        call_command("seed_languages")
        second_count = Language.objects.count()

        assert first_count == second_count
