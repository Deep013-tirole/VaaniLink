"""
Tests for Language model.
"""

import pytest

from apps.languages.models import Language


@pytest.mark.django_db
class TestLanguageModel:
    def test_create_language(self):
        lang = Language.objects.create(
            code="hi",
            name="Hindi",
            native_name="हिन्दी",
            script_code="Deva",
            is_rtl=False,
            is_active=True,
            translation_enabled=True,
            detection_enabled=True,
            transliteration_enabled=True,
            sort_order=2,
        )
        assert str(lang) == "Hindi (hi)"
        assert lang.code == "hi"
        assert not lang.is_rtl
        assert lang.transliteration_enabled

    def test_rtl_language_properties(self):
        urdu = Language.objects.create(
            code="ur",
            name="Urdu",
            native_name="اردو",
            script_code="Arab",
            is_rtl=True,
            is_active=True,
            sort_order=8,
        )
        assert urdu.is_rtl
        assert urdu.script_code == "Arab"
