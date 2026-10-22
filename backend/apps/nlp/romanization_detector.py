"""
Romanization and Hinglish Language Intelligence Detector.
Conforms strictly to Section 15, Section 24, and docs/NLP_PIPELINE.md.
Never assumes Latin script == English.
"""

import re
from typing import NamedTuple


class RomanizationResult(NamedTuple):
    is_romanized: bool
    detected_language: str
    confidence: float
    hinglish_score: float
    english_score: float


class RomanizationDetector:
    """
    Detects whether Latin-script text is Romanized Indic (e.g. Hinglish / Romanized Hindi)
    versus Standard English using combined dictionary hits, n-gram patterns, and phonetic markers.
    """

    # High-frequency Romanized Hindi / Hinglish lexical markers
    HINGLISH_LEXICON = {
        # Pronouns
        "me",
        "mai",
        "main",
        "hum",
        "tum",
        "aap",
        "mera",
        "meri",
        "mere",
        "tera",
        "teri",
        "tere",
        "apna",
        "apni",
        "apne",
        "uska",
        "uski",
        "unka",
        "unki",
        "mujhe",
        "tumhe",
        "aapko",
        "humein",
        "unhe",
        "is",
        "us",
        "ye",
        "yeh",
        "wo",
        "woh",
        # Auxiliary & Verbs
        "hai",
        "hain",
        "ho",
        "hoon",
        "hun",
        "tha",
        "thi",
        "the",
        "hoga",
        "hogi",
        "hoge",
        "kar",
        "karna",
        "karo",
        "karein",
        "kiya",
        "kiye",
        "karte",
        "karti",
        "karta",
        "raha",
        "rahi",
        "rahe",
        "gaya",
        "gayi",
        "gaye",
        "jana",
        "jao",
        "jaunga",
        "aaunga",
        "aunga",
        "aana",
        "aao",
        "aaye",
        "aaya",
        "aayi",
        "aate",
        "bol",
        "bolo",
        "bolna",
        "batao",
        "batana",
        "dekho",
        "dekh",
        "dekhna",
        "le",
        "lo",
        "lena",
        "de",
        "do",
        "dena",
        "milte",
        "milna",
        "milo",
        "samajh",
        "rakh",
        "rakho",
        "chal",
        "chalo",
        "chalna",
        "ruk",
        "ruko",
        "baitho",
        # Adverbs & Question words
        "kya",
        "kyun",
        "kyu",
        "kaise",
        "kaisa",
        "kaisi",
        "kab",
        "kahan",
        "kidhar",
        "kitna",
        "kitne",
        "kitni",
        "nahi",
        "nahin",
        "na",
        "mat",
        "kal",
        "aaj",
        "parso",
        "ab",
        "tab",
        "jab",
        "yahan",
        "wahan",
        "idhar",
        "udhar",
        # Conjunctions & Particles
        "aur",
        "ya",
        "lekin",
        "magar",
        "par",
        "bhi",
        "toh",
        "to",
        "hi",
        "sirf",
        "bas",
        "kuch",
        "sab",
        "bahut",
        "bohot",
        "zyada",
        "kam",
        "thora",
        "thoda",
        # Conversational fillers & honorifics
        "haan",
        "han",
        "achha",
        "accha",
        "theek",
        "bhai",
        "yaar",
        "ji",
        "sahab",
        "arre",
        "shukriya",
        "dhanyawad",
        "namaste",
        "pranam",
        "alvida",
        "suno",
        "sun",
    }

    # High-frequency Standard English stop words
    ENGLISH_STOPS = {
        "the",
        "be",
        "to",
        "of",
        "and",
        "a",
        "in",
        "that",
        "have",
        "i",
        "it",
        "for",
        "not",
        "on",
        "with",
        "he",
        "as",
        "you",
        "do",
        "at",
        "this",
        "but",
        "his",
        "by",
        "from",
        "they",
        "we",
        "say",
        "her",
        "she",
        "or",
        "an",
        "will",
        "my",
        "one",
        "all",
        "would",
        "there",
        "their",
        "what",
        "so",
        "up",
        "out",
        "if",
        "about",
        "who",
        "get",
        "which",
        "go",
        "me",
        "when",
        "make",
        "can",
        "like",
        "time",
        "no",
        "just",
        "him",
        "know",
        "take",
        "people",
        "into",
        "year",
        "your",
        "good",
        "some",
        "could",
        "them",
        "see",
        "other",
        "than",
        "then",
        "now",
        "look",
        "only",
        "come",
        "its",
        "over",
        "think",
        "also",
        "back",
        "after",
        "use",
        "two",
        "how",
        "our",
        "work",
        "first",
        "well",
        "way",
        "even",
        "new",
        "want",
        "because",
        "any",
        "these",
        "give",
        "day",
        "most",
        "us",
        "are",
        "is",
        "was",
        "were",
        "been",
        "being",
        "should",
    }

    # Characteristic Romanized Indic n-gram clusters and phonetic endings
    INDIC_NGRAM_PATTERNS = re.compile(
        r"(?:aa|ee|oo|chh|kh|gh|jh|th|dh|bh|sh|ng|aun|ein|aaye|gaya|karna|raha)",
        re.IGNORECASE,
    )
    INDIC_VERBAL_ENDINGS = re.compile(
        r"(?:unga|aunga|oonga|enge|aoge|ungi|raha|rahi|rahe|karna|karoge|karega)$",
        re.IGNORECASE,
    )

    TOKENIZER = re.compile(r"[A-Za-z]+")

    @classmethod
    def analyze(cls, text: str) -> RomanizationResult:
        """
        Analyze a Latin-script text string to differentiate between
        Romanized Hindi/Indic (Hinglish) and Standard English.
        """
        tokens = [t.lower() for t in cls.TOKENIZER.findall(text)]
        if not tokens:
            return RomanizationResult(
                is_romanized=False,
                detected_language="en",
                confidence=0.5,
                hinglish_score=0.0,
                english_score=0.0,
            )

        total_tokens = len(tokens)
        hinglish_hits = sum(1 for t in tokens if t in cls.HINGLISH_LEXICON)
        english_hits = sum(1 for t in tokens if t in cls.ENGLISH_STOPS)

        # Morphological & N-Gram pattern bonus
        pattern_hits = sum(
            1
            for t in tokens
            if cls.INDIC_VERBAL_ENDINGS.search(t) or cls.INDIC_NGRAM_PATTERNS.search(t)
        )

        hinglish_density = (hinglish_hits + (pattern_hits * 0.5)) / total_tokens
        english_density = english_hits / total_tokens

        # Disambiguation heuristics
        # If words like "kal", "hai", "nahi", "kya", "aunga", "aaunga" exist, strong Hinglish indicator
        decisive_hinglish_markers = {
            "hai",
            "nahi",
            "nahin",
            "kya",
            "aaunga",
            "aunga",
            "karna",
            "raha",
            "rahe",
            "hoga",
            "mujhe",
            "tumhe",
        }
        has_decisive_marker = any(t in decisive_hinglish_markers for t in tokens)

        if has_decisive_marker or hinglish_density > english_density:
            is_romanized = True
            detected_language = "hi"  # Primary language is Hindi rendered in Latin script
            confidence = min(0.98, max(0.65, 0.5 + hinglish_density * 0.5))
        elif english_density > 0:
            is_romanized = False
            detected_language = "en"
            confidence = min(0.98, max(0.65, 0.5 + english_density * 0.5))
        else:
            # Fallback when low stop-word count
            if pattern_hits > 0:
                is_romanized = True
                detected_language = "hi"
                confidence = 0.60
            else:
                is_romanized = False
                detected_language = "en"
                confidence = 0.55

        return RomanizationResult(
            is_romanized=is_romanized,
            detected_language=detected_language,
            confidence=confidence,
            hinglish_score=hinglish_density,
            english_score=english_density,
        )
