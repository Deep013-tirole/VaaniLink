"""
Tests for UnicodeNormalizer.
"""

from apps.nlp.unicode_normalizer import UnicodeNormalizer


class TestUnicodeNormalizer:
    def test_nfkc_normalization(self):
        # Full-width latin characters normalized to standard ASCII
        text = "Ｈｅｌｌｏ Ｗｏｒｌｄ"
        result = UnicodeNormalizer.normalize(text)
        assert result == "Hello World"

    def test_zero_width_space_removal(self):
        # \u200b is zero-width space, \ufeff is BOM
        text = "Hello\u200b \ufeffWorld"
        result = UnicodeNormalizer.normalize(text)
        assert result == "Hello World"

    def test_control_character_sanitization(self):
        # ASCII 0x07 (bell), 0x08 (backspace), 0x1B (escape)
        text = "Hello\x07\x08 World\x1b!"
        result = UnicodeNormalizer.normalize(text)
        assert result == "Hello World!"

    def test_excessive_whitespace_collapsing(self):
        text = "  Too    many     spaces   here   "
        result = UnicodeNormalizer.normalize(text)
        assert result == "Too many spaces here"
