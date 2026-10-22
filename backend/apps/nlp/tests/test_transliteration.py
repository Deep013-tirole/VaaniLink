"""
Tests for TransliterationService.
"""

from apps.nlp.transliteration import TransliterationService


class TestTransliterationService:
    def test_transliterate_kal_milte_hain(self):
        text = "kal milte hain"
        result = TransliterationService.transliterate(text)
        assert result == "कल मिलते हैं"

    def test_transliterate_me_nahi_aaunga(self):
        text = "me nahi aaunga"
        result = TransliterationService.transliterate(text)
        assert result == "मैं नहीं आऊँगा"

    def test_preserves_placeholders(self):
        text = "kal milte hain __PROT_EMO_0__"
        result = TransliterationService.transliterate(text)
        assert result == "कल मिलते हैं __PROT_EMO_0__"
