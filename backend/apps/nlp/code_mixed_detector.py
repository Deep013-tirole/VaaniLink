"""
Code-Mixed Language Analysis Stage.
Conforms to Section 16, Section 23, and docs/NLP_PIPELINE.md.
"""

import re

from apps.nlp.romanization_detector import RomanizationDetector
from apps.nlp.script_detector import ScriptDetector
from apps.nlp.types import TokenAnalysis


class CodeMixedDetector:
    """
    Performs token-level language classification to detect code-mixed sentences
    (e.g., sentences mixing English and Romanized Hindi).
    """

    # Extended common English vocabulary for code-mixing recognition
    COMMON_ENGLISH_WORDS = {
        "bro",
        "dude",
        "boss",
        "sir",
        "mam",
        "friend",
        "office",
        "meeting",
        "project",
        "client",
        "call",
        "email",
        "link",
        "team",
        "report",
        "file",
        "laptop",
        "pc",
        "computer",
        "phone",
        "message",
        "chat",
        "cancel",
        "plan",
        "time",
        "date",
        "morning",
        "evening",
        "night",
        "ready",
        "done",
        "okay",
        "ok",
        "fine",
        "cool",
        "super",
        "great",
        "congrats",
        "congratulations",
        "party",
        "car",
        "train",
        "flight",
        "hotel",
        "ticket",
        "urgent",
        "important",
        "issue",
        "problem",
        "bug",
        "submit",
        "start",
        "stop",
        "join",
        "leave",
        "send",
        "receive",
        "thanks",
        "thank",
        "you",
        "welcome",
        "please",
        "sorry",
        "bye",
        "hello",
        "hi",
        "hey",
        "good",
        "bad",
        "best",
        "worst",
        "yes",
        "no",
        "sure",
        "true",
        "false",
        "maybe",
        "why",
        "what",
        "where",
        "how",
        "who",
        "when",
        "can",
        "will",
        "would",
        "could",
        "should",
        "must",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "is",
        "are",
        "am",
        "was",
        "were",
        "i",
        "we",
        "they",
        "he",
        "she",
        "it",
        "my",
        "your",
        "our",
        "their",
        "his",
        "her",
        "its",
        "the",
        "a",
        "an",
        "this",
        "that",
        "dinner",
        "lunch",
        "breakfast",
        "presentation",
        "tomorrow",
        "coming",
        "quick",
        "brown",
        "fox",
        "jumps",
        "over",
        "lazy",
        "dog",
    }

    # Matches words, punctuation, numbers, and placeholders
    TOKEN_REGEX = re.compile(r"(__PROT_[A-Z]+_\d+__|[A-Za-z0-9\u0600-\u0D7F]+|[^\s\w])")

    @classmethod
    def analyze(cls, text: str) -> tuple[list[TokenAnalysis], bool, list[str]]:
        """
        Analyze text token-by-token.
        Returns:
            tokens: list of TokenAnalysis objects
            is_mixed: boolean indicating if sentence contains code-mixing
            languages_present: list of unique language codes detected
        """
        raw_tokens = cls.TOKEN_REGEX.findall(text)
        token_analyses: list[TokenAnalysis] = []

        # Identify unambiguous lexical markers across the whole string
        unambiguous_hinglish_set = (
            RomanizationDetector.HINGLISH_LEXICON - RomanizationDetector.ENGLISH_STOPS
        )
        has_unambiguous_hinglish = any(
            tok.lower() in unambiguous_hinglish_set
            or bool(RomanizationDetector.INDIC_VERBAL_ENDINGS.search(tok.lower()))
            for tok in raw_tokens
            if tok.isalnum()
        )

        lang_counts: dict[str, int] = {}

        for raw_tok in raw_tokens:
            # 1. Protected placeholders
            if raw_tok.startswith("__PROT_"):
                tok_type = "emoji" if "EMO" in raw_tok else "protected"
                token_analyses.append(TokenAnalysis(text=raw_tok, token_type=tok_type))
                continue

            # 2. Punctuation
            if not any(c.isalnum() for c in raw_tok):
                token_analyses.append(TokenAnalysis(text=raw_tok, token_type="punctuation"))
                continue

            # 3. Numeric tokens
            if raw_tok.isdigit():
                token_analyses.append(TokenAnalysis(text=raw_tok, token_type="number"))
                continue

            # 4. Word tokens - evaluate script and language
            script = ScriptDetector.detect_primary_script(raw_tok)
            lower_tok = raw_tok.lower()

            if script == "Latn":
                is_hinglish_hit = lower_tok in RomanizationDetector.HINGLISH_LEXICON or bool(
                    RomanizationDetector.INDIC_VERBAL_ENDINGS.search(lower_tok)
                )
                is_english_hit = (
                    lower_tok in cls.COMMON_ENGLISH_WORDS
                    or lower_tok in RomanizationDetector.ENGLISH_STOPS
                )

                if is_hinglish_hit and not is_english_hit:
                    lang = "hi"
                    is_rom = True
                elif is_english_hit and not is_hinglish_hit:
                    lang = "en"
                    is_rom = False
                elif is_hinglish_hit and is_english_hit:
                    # Ambiguous (e.g. "the", "me", "to", "so", "is")
                    if has_unambiguous_hinglish:
                        lang = "hi"
                        is_rom = True
                    else:
                        lang = "en"
                        is_rom = False
                else:
                    # Unknown Latin token
                    lang = None
                    is_rom = False

                token_analyses.append(
                    TokenAnalysis(
                        text=raw_tok,
                        token_type="word",
                        script=script,
                        language=lang,
                        is_romanized=is_rom,
                    )
                )
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

            elif script == "Deva":
                # Devanagari script defaults to Hindi
                lang = "hi"
                token_analyses.append(
                    TokenAnalysis(
                        text=raw_tok,
                        token_type="word",
                        script=script,
                        language=lang,
                        is_romanized=False,
                    )
                )
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            elif script == "Gujr":
                lang = "gu"
                token_analyses.append(
                    TokenAnalysis(
                        text=raw_tok,
                        token_type="word",
                        script=script,
                        language=lang,
                        is_romanized=False,
                    )
                )
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            elif script == "Arab":
                lang = "ur"
                token_analyses.append(
                    TokenAnalysis(
                        text=raw_tok,
                        token_type="word",
                        script=script,
                        language=lang,
                        is_romanized=False,
                    )
                )
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            else:
                token_analyses.append(
                    TokenAnalysis(
                        text=raw_tok,
                        token_type="word",
                        script=script,
                        language=None,
                        is_romanized=False,
                    )
                )

        # Code-mixed determination:
        # A sentence is code-mixed if at least 2 distinct languages are actively present,
        # and for Latin scripts, at least one unambiguous Hinglish token is present alongside English.
        active_langs = [lang for lang, count in lang_counts.items() if count >= 1]

        if "hi" in active_langs and "en" in active_langs:
            is_mixed = has_unambiguous_hinglish and lang_counts.get("en", 0) >= 1
        else:
            is_mixed = len(active_langs) >= 2

        # Mark code-mixed on individual tokens if sentence is mixed
        if is_mixed:
            for t in token_analyses:
                if t.token_type == "word" and t.language:
                    t.is_code_mixed = True

        return token_analyses, is_mixed, active_langs
