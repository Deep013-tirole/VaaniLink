"""
Unicode normalization and text sanitization stage.
Conforms to Stage 1 of docs/NLP_PIPELINE.md.
"""

import re
import unicodedata


class UnicodeNormalizer:
    """
    Normalizes text into NFKC form, cleans control characters,
    and strips spurious zero-width characters while protecting ligatures.
    """

    # Unwanted invisible characters (Zero-width space, BOM, soft hyphen)
    STRIP_CHARS = re.compile(r"[\u200B\u200E\u200F\uFEFF\u00AD]")

    # Disallowed control characters (ASCII 0-8, 11-12, 14-31, 127)
    CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

    # Multiple horizontal whitespace characters into a single space
    MULTI_SPACE = re.compile(r"[ \t\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+")

    @classmethod
    def normalize(cls, text: str) -> str:
        if not text:
            return ""

        # 1. NFKC canonical decomposition and compatibility composition
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Remove dangerous control characters
        normalized = cls.CONTROL_CHARS.sub("", normalized)

        # 3. Remove zero-width spaces/BOM
        normalized = cls.STRIP_CHARS.sub("", normalized)

        # 4. Collapse consecutive spaces while keeping newlines intact
        lines = [cls.MULTI_SPACE.sub(" ", line).strip() for line in normalized.split("\n")]
        return "\n".join(lines).strip()
