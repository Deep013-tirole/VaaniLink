"""
Main NLP Intelligence Pipeline Orchestrator.
Conforms to docs/NLP_PIPELINE.md, Section 14, 15, 16, 23, and 24.
"""

from apps.nlp.code_mixed_detector import CodeMixedDetector
from apps.nlp.protected_tokens import ProtectedTokenManager
from apps.nlp.romanization_detector import RomanizationDetector
from apps.nlp.script_detector import ScriptDetector
from apps.nlp.transliteration import TransliterationService
from apps.nlp.types import NLPResult
from apps.nlp.unicode_normalizer import UnicodeNormalizer


class NLPPipeline:
    """
    End-to-end NLP Language Intelligence Pipeline.
    Orchestrates Unicode normalization, protected token isolation, script detection,
    romanization analysis, code-mixing detection, and transliteration preprocessing.
    """

    SCRIPT_TO_DEFAULT_LANG = {
        "Deva": "hi",  # Devanagari -> Hindi
        "Gujr": "gu",  # Gujarati -> Gujarati
        "Beng": "bn",  # Bengali -> Bengali
        "Arab": "ur",  # Arabic/Perso-Arabic -> Urdu
        "Guru": "pa",  # Gurmukhi -> Punjabi
        "Taml": "ta",  # Tamil -> Tamil
        "Telu": "te",  # Telugu -> Telugu
        "Knda": "kn",  # Kannada -> Kannada
        "Mlym": "ml",  # Malayalam -> Malayalam
        "Orya": "or",  # Odia -> Odia
        "Cyrl": "ru",  # Cyrillic -> Russian
        "Hani": "zh",  # Han -> Chinese
        "Jpan": "ja",  # Japanese
        "Hang": "ko",  # Korean
        "Thai": "th",  # Thai
    }

    @classmethod
    def process(cls, text: str) -> NLPResult:
        """
        Execute full pipeline on raw message text.
        """
        raw_text = text or ""

        # 1. Unicode Normalization (NFKC, zero-width cleanup)
        cleaned_text = UnicodeNormalizer.normalize(raw_text)
        if not cleaned_text:
            return NLPResult(
                raw_text=raw_text,
                cleaned_text="",
                detected_primary_language="en",
                detected_script="Latn",
                is_mixed_language=False,
                is_romanized=False,
                language_confidence=1.0,
            )

        # 2. Extract Protected Tokens (URLs, emails, mentions, hashtags, emojis)
        masked_text, protected_tokens = ProtectedTokenManager.protect(cleaned_text)

        # 3. Script Detection
        primary_script = ScriptDetector.detect_primary_script(masked_text)

        # 4. Token-level analysis and code-mixing detection
        tokens, is_mixed, active_langs = CodeMixedDetector.analyze(masked_text)

        # 5. Language Identification & Romanization Strategy
        if primary_script == "Latn":
            rom_res = RomanizationDetector.analyze(masked_text)
            detected_lang = rom_res.detected_language
            is_romanized = rom_res.is_romanized
            confidence = rom_res.confidence

            # Generate transliteration for Romanized Hindi
            if is_romanized and detected_lang == "hi":
                transliterated = TransliterationService.transliterate(
                    masked_text, source_lang="hi", target_script="Deva"
                )
                transliterated = ProtectedTokenManager.restore(transliterated, protected_tokens)
            else:
                transliterated = None

        else:
            # Native non-Latin script
            detected_lang = cls.SCRIPT_TO_DEFAULT_LANG.get(primary_script, "en")
            is_romanized = False
            confidence = 0.95
            transliterated = None

        # Build detected languages breakdown
        detected_languages_list = [
            {
                "language": detected_lang,
                "script": primary_script,
                "confidence": round(confidence, 4),
            }
        ]
        if is_mixed:
            for lang in active_langs:
                if lang != detected_lang:
                    detected_languages_list.append(
                        {
                            "language": lang,
                            "script": primary_script,
                            "confidence": round(confidence * 0.7, 4),
                        }
                    )

        return NLPResult(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            detected_primary_language=detected_lang,
            detected_script=primary_script,
            is_mixed_language=is_mixed,
            is_romanized=is_romanized,
            language_confidence=confidence,
            detected_languages=detected_languages_list,
            tokens=tokens,
            protected_tokens=protected_tokens,
            transliterated_text=transliterated,
        )
