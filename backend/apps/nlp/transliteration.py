"""
Transliteration Engine Stage.
Conforms to Stage 7 of docs/NLP_PIPELINE.md and Section 4 & 15.
"""

from abc import ABC, abstractmethod


class BaseTransliterationEngine(ABC):
    """Abstract interface for transliteration engines."""

    @abstractmethod
    def transliterate(self, text: str, source_lang: str, target_script: str) -> str:
        """Transliterate text into target script."""
        pass


class RuleBasedIndicTransliterator(BaseTransliterationEngine):
    """
    High-frequency dictionary and phonetic rule-based transliterator
    for Romanized Indic (Hinglish) -> Devanagari.
    """

    # Common Hinglish token to Devanagari dictionary
    HINGLISH_TO_DEVA = {
        "me": "मैं",
        "mai": "मैं",
        "main": "मैं",
        "nahi": "नहीं",
        "nahin": "नहीं",
        "aaunga": "आऊँगा",
        "aunga": "आऊँगा",
        "kal": "कल",
        "aaj": "आज",
        "parso": "परसों",
        "milte": "मिलते",
        "milo": "मिलो",
        "hain": "हैं",
        "hai": "है",
        "ho": "हो",
        "hoon": "हूँ",
        "hun": "हूँ",
        "kya": "क्या",
        "kyun": "क्यों",
        "kyu": "क्यों",
        "kaise": "कैसे",
        "kaisa": "कैसा",
        "kab": "कब",
        "kahan": "कहाँ",
        "kidhar": "किधर",
        "kitne": "कितने",
        "kitna": "कितना",
        "bahut": "बहुत",
        "bohot": "बहुत",
        "accha": "अच्छा",
        "achha": "अच्छा",
        "theek": "ठीक",
        "bhai": "भाई",
        "yaar": "यार",
        "shukriya": "शुक्रिया",
        "dhanyawad": "धन्यवाद",
        "namaste": "नमस्ते",
        "karna": "करना",
        "kar": "कर",
        "karo": "करो",
        "karein": "करें",
        "raha": "रहा",
        "rahi": "रही",
        "rahe": "रहे",
        "hoga": "होगा",
        "hogi": "होगी",
        "mujhe": "मुझे",
        "tumhe": "तुम्हें",
        "aapko": "आपको",
        "hum": "हम",
        "tum": "तुम",
        "aap": "आप",
        "bolo": "बोलो",
        "bolna": "बोलना",
        "batao": "बताओ",
        "dekho": "देखो",
        "chalo": "चलो",
        "aur": "और",
        "lekin": "लेकिन",
        "bhi": "भी",
        "toh": "तो",
        "to": "तो",
        "sirf": "सिर्फ",
        "bas": "बस",
        "ab": "अब",
        "tab": "तब",
        "jab": "जब",
        "ye": "ये",
        "yeh": "यह",
        "wo": "वो",
        "woh": "वह",
        "haan": "हाँ",
        "han": "हाँ",
        "badhiya": "बढ़िया",
    }

    def transliterate(self, text: str, source_lang: str = "hi", target_script: str = "Deva") -> str:
        if not text:
            return ""

        words = text.split()
        converted_words = []

        for word in words:
            # Preserve placeholders, e.g. __PROT_EMO_0__
            if word.startswith("__PROT_"):
                converted_words.append(word)
                continue

            # Strip punctuation for lookup
            clean_word = word.lower().strip(".,!?;:\"'()[]{}")
            trailing_punct = word[len(clean_word) :] if word.lower().startswith(clean_word) else ""

            if clean_word in self.HINGLISH_TO_DEVA:
                converted_words.append(self.HINGLISH_TO_DEVA[clean_word] + trailing_punct)
            else:
                converted_words.append(word)

        return " ".join(converted_words)


class TransliterationService:
    """Service dispatcher for transliteration providers."""

    _engine: BaseTransliterationEngine = RuleBasedIndicTransliterator()

    @classmethod
    def set_engine(cls, engine: BaseTransliterationEngine):
        cls._engine = engine

    @classmethod
    def transliterate(cls, text: str, source_lang: str = "hi", target_script: str = "Deva") -> str:
        return cls._engine.transliterate(text, source_lang, target_script)
