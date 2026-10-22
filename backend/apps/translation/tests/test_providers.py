"""
Unit tests for translation providers (RuleBased, Mock, GoogleCloud fallback, Registry).
"""

from apps.translation.providers.mock import MockTranslationProvider
from apps.translation.providers.registry import TranslationProviderRegistry
from apps.translation.providers.rule_based import RuleBasedTranslationProvider


class TestTranslationProviders:
    def test_rule_based_known_phrases(self):
        provider = RuleBasedTranslationProvider()

        # English to Hindi
        res_hi = provider.translate("Are you coming tomorrow?", source_lang="en", target_lang="hi")
        assert res_hi.status == "COMPLETED"
        assert res_hi.translated_text == "क्या आप कल आ रहे हैं?"
        assert res_hi.provider == "rule_based"

        # English to Gujarati
        res_gu = provider.translate("Are you coming tomorrow?", source_lang="en", target_lang="gu")
        assert res_gu.status == "COMPLETED"
        assert res_gu.translated_text == "શું તમે કાલે આવી રહ્યા છો?"

        # Hinglish to English
        res_hinglish = provider.translate("me kal nahi aaunga", source_lang="hi", target_lang="en")
        assert res_hinglish.status == "COMPLETED"
        assert "won't come tomorrow" in res_hinglish.translated_text

    def test_rule_based_emoji_preservation(self):
        provider = RuleBasedTranslationProvider()

        res = provider.translate("kal milte hain 😊", source_lang="hi", target_lang="en")
        assert res.status == "COMPLETED"
        assert "😊" in res.translated_text

        res_hi = provider.translate("hello ❤️", source_lang="en", target_lang="hi")
        assert res_hi.status == "COMPLETED"
        assert "❤️" in res_hi.translated_text
        assert "नमस्ते" in res_hi.translated_text

    def test_rule_based_same_language_identity(self):
        provider = RuleBasedTranslationProvider()
        res = provider.translate("Hello world", source_lang="en", target_lang="en")
        assert res.translated_text == "Hello world"
        assert res.confidence == 1.0

    def test_mock_provider_success_and_failure(self):
        success_mock = MockTranslationProvider()
        res_ok = success_mock.translate("Testing 123", source_lang="en", target_lang="es")
        assert res_ok.status == "COMPLETED"
        assert "[ES] Testing 123" == res_ok.translated_text

        failing_mock = MockTranslationProvider(
            should_fail=True, failure_error_message="Quota exceeded."
        )
        res_fail = failing_mock.translate("Testing 123", source_lang="en", target_lang="es")
        assert res_fail.status == "FAILED"
        assert res_fail.error_message == "Quota exceeded."

    def test_provider_registry(self):
        default_provider = TranslationProviderRegistry.get()
        assert default_provider.name == "rule_based"

        mock_provider = TranslationProviderRegistry.get("mock")
        assert mock_provider.name == "mock"

        # Unknown provider falls back safely to rule_based
        unknown = TranslationProviderRegistry.get("non_existent_engine")
        assert unknown.name == "rule_based"

        available = TranslationProviderRegistry.list_available()
        assert "rule_based" in available
        assert "mock" in available
        assert "google_cloud" in available
