"""
Tests for ProtectedTokenManager.
"""

from apps.nlp.protected_tokens import ProtectedTokenManager


class TestProtectedTokenManager:
    def test_url_protection_and_restoration(self):
        text = "Check out https://vaanilink.com/docs/api and www.google.com for info"
        masked, tokens = ProtectedTokenManager.protect(text)

        assert "https://vaanilink.com/docs/api" not in masked
        assert "www.google.com" not in masked
        assert len(tokens) == 2

        restored = ProtectedTokenManager.restore(masked, tokens)
        assert restored == text

    def test_email_protection_and_restoration(self):
        text = "Contact support@vaanilink.com or admin@example.org"
        masked, tokens = ProtectedTokenManager.protect(text)

        assert "support@vaanilink.com" not in masked
        assert len(tokens) == 2

        restored = ProtectedTokenManager.restore(masked, tokens)
        assert restored == text

    def test_social_mentions_and_hashtags(self):
        text = "Hello @deepak check #VaaniLink and #Multilingual"
        masked, tokens = ProtectedTokenManager.protect(text)

        assert "@deepak" not in masked
        assert "#VaaniLink" not in masked
        assert len(tokens) == 3

        restored = ProtectedTokenManager.restore(masked, tokens)
        assert restored == text

    def test_emoji_preservation(self):
        # Diverse emojis: simple, heart, multi-codepoint, skin tone, ZWJ family sequence
        text = "Kal milte hain 😊! बहुत बढ़िया ❤️ Congratulations 🎉🎉 👨‍👩‍👧‍👦"
        masked, tokens = ProtectedTokenManager.protect(text)

        # Ensure emojis are masked
        assert "😊" not in masked
        assert "❤️" not in masked
        assert "🎉" not in masked
        assert "👨‍👩‍👧‍👦" not in masked

        restored = ProtectedTokenManager.restore(masked, tokens)
        assert restored == text
