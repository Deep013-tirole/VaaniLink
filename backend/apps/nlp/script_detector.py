"""
Script Detection Engine based on Unicode character block analysis.
Conforms to Stage 4 of docs/NLP_PIPELINE.md and ISO 15924.
"""

from collections import Counter


class ScriptDetector:
    """
    Identifies the writing scripts present in text by analyzing Unicode blocks.
    Returns standard ISO 15924 4-letter script codes.
    """

    # Unicode ranges mapping to ISO 15924 script codes
    SCRIPT_RANGES = [
        # Indic Scripts
        (0x0900, 0x097F, "Deva"),  # Devanagari (Hindi, Marathi, Sanskrit, Nepali, Maithili)
        (0xA8E0, 0xA8FF, "Deva"),  # Devanagari Extended
        (0x0980, 0x09FF, "Beng"),  # Bengali, Assamese
        (0x0A00, 0x0A7F, "Guru"),  # Gurmukhi (Punjabi)
        (0x0A80, 0x0AFF, "Gujr"),  # Gujarati
        (0x0B00, 0x0B7F, "Orya"),  # Odia (Oriya)
        (0x0B80, 0x0BFF, "Taml"),  # Tamil
        (0x0C00, 0x0C7F, "Telu"),  # Telugu
        (0x0C80, 0x0CFF, "Knda"),  # Kannada
        (0x0D00, 0x0D7F, "Mlym"),  # Malayalam
        # Right-to-Left Scripts
        (0x0600, 0x06FF, "Arab"),  # Arabic, Urdu, Persian
        (0x0750, 0x077F, "Arab"),  # Arabic Supplement
        (0x08A0, 0x08FF, "Arab"),  # Arabic Extended-A
        (0xFB50, 0xFDFF, "Arab"),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF, "Arab"),  # Arabic Presentation Forms-B
        # Latin
        (0x0041, 0x005A, "Latn"),  # Basic Latin uppercase
        (0x0061, 0x007A, "Latn"),  # Basic Latin lowercase
        (0x00C0, 0x024F, "Latn"),  # Latin-1 Supplement & Extended
        # Other International Scripts
        (0x0400, 0x04FF, "Cyrl"),  # Cyrillic (Russian, Ukrainian)
        (0x4E00, 0x9FFF, "Hani"),  # Han (Chinese)
        (0x3040, 0x309F, "Jpan"),  # Japanese Hiragana
        (0x30A0, 0x30FF, "Jpan"),  # Japanese Katakana
        (0xAC00, 0xD7AF, "Hang"),  # Korean Hangul
        (0x1100, 0x11FF, "Hang"),  # Korean Jamo
        (0x0E00, 0x0E7F, "Thai"),  # Thai
    ]

    @classmethod
    def get_char_script(cls, char: str) -> str | None:
        """Return ISO 15924 script for a single character or None if non-script symbol."""
        cp = ord(char)
        for start, end, script in cls.SCRIPT_RANGES:
            if start <= cp <= end:
                return script
        return None

    @classmethod
    def detect_scripts(cls, text: str) -> dict[str, float]:
        """
        Compute frequency distribution of scripts across all script-bearing characters.
        Returns dict mapping script code to percentage (0.0 to 1.0).
        """
        counts: Counter[str] = Counter()
        total_chars = 0

        for char in text:
            script = cls.get_char_script(char)
            if script:
                counts[script] += 1
                total_chars += 1

        if total_chars == 0:
            return {"Latn": 1.0}

        return {script: count / total_chars for script, count in counts.most_common()}

    @classmethod
    def detect_primary_script(cls, text: str) -> str:
        """
        Return the dominant script in the given text.
        Defaults to 'Latn' if no recognized script characters exist.
        """
        distribution = cls.detect_scripts(text)
        return next(iter(distribution.keys()), "Latn")
