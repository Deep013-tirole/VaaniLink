"""
Unit tests for TranslationCache.
"""

from apps.translation.cache import TranslationCache


class TestTranslationCache:
    def test_cache_key_generation(self):
        k1 = TranslationCache.compute_cache_key("en", "hi", "Are you coming tomorrow?")
        k2 = TranslationCache.compute_cache_key("EN", "HI", "  Are you coming tomorrow?  ")
        assert k1 == k2
        assert k1.startswith("translation:en:hi:")

    def test_cache_set_and_get(self):
        source = "en"
        target = "fr"
        text = "Hello my friend"
        translated = "Bonjour mon ami"

        # Initially None
        assert TranslationCache.get(source, target, text) is None

        # Store
        TranslationCache.set(source, target, text, translated)

        # Retrieve
        cached = TranslationCache.get(source, target, text)
        assert cached == translated
