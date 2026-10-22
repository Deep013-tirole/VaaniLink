"""
Google Cloud Translation provider adapter.
Conforms strictly to Section 4, Section 25, Section 47, and Section 48:
- External translation provider integration
- Graceful degraded fallback when API credentials are absent
- Protected token and emoji preservation
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

from apps.nlp.protected_tokens import ProtectedTokenManager
from apps.translation.providers.base import BaseTranslationProvider, TranslationResult
from apps.translation.providers.rule_based import RuleBasedTranslationProvider

logger = logging.getLogger(__name__)


class GoogleCloudTranslationProvider(BaseTranslationProvider):
    """
    Adapter for Google Cloud Translation API v2.
    Falls back gracefully to RuleBasedTranslationProvider if credentials are not configured.
    """

    name = "google_cloud"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "GOOGLE_TRANSLATE_API_KEY", None)
        self.fallback_provider = RuleBasedTranslationProvider()

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        if not text or not text.strip():
            return TranslationResult(
                translated_text="",
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
                confidence=1.0,
            )

        if source_lang == target_lang:
            return TranslationResult(
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
                confidence=1.0,
            )

        # If API key is missing, log warning and use fallback provider
        if not self.api_key:
            logger.warning(
                "GOOGLE_TRANSLATE_API_KEY is not configured; using RuleBasedTranslationProvider as fallback."
            )
            fallback_res = self.fallback_provider.translate(
                text, source_lang, target_lang, context=context
            )
            return TranslationResult(
                translated_text=fallback_res.translated_text,
                source_language=source_lang,
                target_language=target_lang,
                provider=f"{self.name}_fallback",
                confidence=fallback_res.confidence,
                status=fallback_res.status,
                error_message="Google Translate API key not set; used rule-based fallback.",
            )

        # Protect emojis & entities
        masked_text, token_map = ProtectedTokenManager.protect(text)

        # Prepare HTTP request to Google Cloud Translation API v2
        endpoint = f"https://translation.googleapis.com/language/translate/v2?key={self.api_key}"
        payload = json.dumps(
            {
                "q": masked_text,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                translated = data["data"]["translations"][0]["translatedText"]
                final_text = ProtectedTokenManager.restore(translated, token_map)
                return TranslationResult(
                    translated_text=final_text,
                    source_language=source_lang,
                    target_language=target_lang,
                    provider=self.name,
                    confidence=0.98,
                    status="COMPLETED",
                )
        except Exception as exc:
            logger.error("Google Cloud Translation API request failed: %s", exc)
            # Degraded mode fallback
            fallback_res = self.fallback_provider.translate(
                text, source_lang, target_lang, context=context
            )
            return TranslationResult(
                translated_text=fallback_res.translated_text,
                source_language=source_lang,
                target_language=target_lang,
                provider=f"{self.name}_degraded",
                confidence=0.5,
                status="COMPLETED",
                error_message=f"Google API error: {str(exc)}; used fallback.",
            )
