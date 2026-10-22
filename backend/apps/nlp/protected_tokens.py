"""
Protected Token and Emoji Preservation Stage.
Conforms to Stage 2 and Stage 3 of docs/NLP_PIPELINE.md and Section 14.
"""

import re


class ProtectedTokenManager:
    """
    Extracts non-translatable units (URLs, emails, @mentions, #hashtags, emojis)
    and replaces them with collision-resistant placeholders.
    Enables lossless restoration post-translation.
    """

    # URL Pattern (http, https, or bare www)
    URL_PATTERN = re.compile(
        r"(?:https?://|www\.)[^\s/$.?#].[^\s]*",
        re.IGNORECASE,
    )

    # Email Pattern
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    # Social Mentions & Hashtags
    MENTION_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_]{1,32}\b")
    HASHTAG_PATTERN = re.compile(r"(?<!\w)#[A-Za-z0-9_]{1,64}\b")

    # Comprehensive Unicode Emoji Pattern (including ZWJ sequences, skin tones, and variation selectors)
    EMOJI_BASE = (
        r"[\U0001F600-\U0001F64F"  # Emoticons
        r"\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
        r"\U0001F680-\U0001F6FF"  # Transport and Map
        r"\U0001F700-\U0001F77F"  # Alchemical Symbols
        r"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        r"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        r"\U0001FA00-\U0001FA6F"  # Chess Symbols
        r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        r"\U00002600-\U000026FF"  # Misc symbols (e.g. ☀️, ❤️)
        r"\U00002700-\U000027BF"  # Dingbats (e.g. ✨, ✈️)
        r"\U0001F1E6-\U0001F1FF"  # Regional indicator symbols (Flags)
        r"]"
    )
    MODIFIER = r"[\U0001F3FB-\U0001F3FF]"  # Skin tone modifiers
    ZWJ = r"\u200D"
    VARIATION = r"[\uFE0E\uFE0F]"

    # Compound emoji regex supporting ZWJ chains (e.g., 👨‍👩‍👧‍👦, 🏃🏽‍♀️)
    EMOJI_PATTERN = re.compile(
        rf"(?:{EMOJI_BASE}(?:{MODIFIER})?(?:{VARIATION})?)"
        rf"(?:{ZWJ}(?:{EMOJI_BASE}(?:{MODIFIER})?(?:{VARIATION})?))*"
    )

    @classmethod
    def protect(cls, text: str) -> tuple[str, dict[str, str]]:
        """
        Replace all protected tokens and emojis with unique placeholders.
        Returns:
            masked_text: string with placeholders
            tokens: mapping from placeholder to original token
        """
        if not text:
            return "", {}

        tokens: dict[str, str] = {}
        masked = text

        def replace_with_tag(match: re.Match, prefix: str) -> str:
            tag = f"__{prefix}_{len(tokens)}__"
            val = match.group(0)
            tokens[tag] = val
            return tag

        # 1. Protect URLs
        masked = cls.URL_PATTERN.sub(lambda m: replace_with_tag(m, "PROT_URL"), masked)

        # 2. Protect Emails
        masked = cls.EMAIL_PATTERN.sub(lambda m: replace_with_tag(m, "PROT_EMAIL"), masked)

        # 3. Protect Mentions
        masked = cls.MENTION_PATTERN.sub(lambda m: replace_with_tag(m, "PROT_MENT"), masked)

        # 4. Protect Hashtags
        masked = cls.HASHTAG_PATTERN.sub(lambda m: replace_with_tag(m, "PROT_TAG"), masked)

        # 5. Protect Emojis
        masked = cls.EMOJI_PATTERN.sub(lambda m: replace_with_tag(m, "PROT_EMO"), masked)

        return masked, tokens

    @classmethod
    def restore(cls, text: str, tokens: dict[str, str]) -> str:
        """
        Restore placeholders back to original protected content.
        """
        if not text or not tokens:
            return text

        restored = text
        for tag, original_val in tokens.items():
            restored = restored.replace(tag, original_val)

        return restored

    @classmethod
    def extract_emojis(cls, text: str) -> list[str]:
        """Return list of all emojis present in text."""
        return cls.EMOJI_PATTERN.findall(text)
