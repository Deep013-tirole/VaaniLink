"""
Base interfaces and data structures for translation providers.
Conforms strictly to Section 4, Section 25, Section 47, and Section 48:
- Pluggable provider-independent interface
- Decoupled from messaging and storage
- Support for single and batch translation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TranslationResult:
    """Immutable result from a translation provider."""

    translated_text: str
    source_language: str
    target_language: str
    provider: str
    confidence: float = 1.0
    is_cached: bool = False
    status: str = "COMPLETED"
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "provider": self.provider,
            "confidence": self.confidence,
            "is_cached": self.is_cached,
            "status": self.status,
            "error_message": self.error_message,
        }


class BaseTranslationProvider(ABC):
    """
    Abstract contract for all translation engine implementations.
    Providers can be local rule-based models, external cloud APIs, or hybrid ensembles.
    """

    name: str = "base"

    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        """
        Translate input text from source_lang to target_lang.
        Must preserve protected tokens, emojis, and handle failures gracefully.
        """
        raise NotImplementedError

    def batch_translate(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        context: dict[str, Any] | None = None,
    ) -> list[TranslationResult]:
        """
        Translate multiple texts. Default implementation calls translate() sequentially.
        Specialized cloud or ML providers may override with batch network calls.
        """
        return [self.translate(text, source_lang, target_lang, context=context) for text in texts]

    def is_supported_pair(self, source_lang: str, target_lang: str) -> bool:
        """
        Returns True if the engine supports translating between source and target language.
        """
        return True
