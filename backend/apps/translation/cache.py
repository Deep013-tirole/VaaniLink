"""
Translation caching layer using Redis / Django cache.
Conforms strictly to Section 26:
- Cache key strategy: `translation:{source_lang}:{target_lang}:{sha256(text)}`
- Configurable TTL (default 7 days)
- Invalidation support when messages are edited
"""

import hashlib
import uuid

from django.core.cache import cache

DEFAULT_TRANSLATION_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


class TranslationCache:
    """Manages translation caching in Redis to prevent duplicate translation requests."""

    @staticmethod
    def compute_cache_key(source_lang: str, target_lang: str, text: str) -> str:
        """
        Deterministic cache key for a source->target translation of specific text.
        Normalizes whitespace and computes SHA-256 digest.
        """
        normalized = " ".join(text.strip().split())
        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"translation:{source_lang.lower()}:{target_lang.lower()}:{text_hash}"

    @classmethod
    def get(cls, source_lang: str, target_lang: str, text: str) -> str | None:
        """Retrieve cached translated text, or None if miss."""
        key = cls.compute_cache_key(source_lang, target_lang, text)
        return cache.get(key)

    @classmethod
    def set(
        cls,
        source_lang: str,
        target_lang: str,
        text: str,
        translated_text: str,
        ttl: int = DEFAULT_TRANSLATION_CACHE_TTL,
    ) -> None:
        """Store translated text in cache with TTL."""
        key = cls.compute_cache_key(source_lang, target_lang, text)
        cache.set(key, translated_text, timeout=ttl)

    @classmethod
    def invalidate_message(cls, message_id: str | uuid.UUID) -> None:
        """
        Invalidate cached translations when a message is edited.
        Deletes database MessageTranslation entries for this message.
        """
        from apps.translation.models import MessageTranslation

        MessageTranslation.objects.filter(message_id=message_id).delete()
