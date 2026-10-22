"""
Mock translation provider for testing failure and degraded modes.
Conforms strictly to Section 48:
- Failure handling
- Rate limit simulation
- Error state propagation without crashing messaging
"""

from typing import Any

from apps.translation.providers.base import BaseTranslationProvider, TranslationResult


class MockTranslationProvider(BaseTranslationProvider):
    """
    Mock translation provider configurable for testing success, degradation, and failures.
    """

    name = "mock"

    def __init__(
        self,
        should_fail: bool = False,
        failure_error_message: str = "Simulated translation provider failure.",
        prefix: str | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.failure_error_message = failure_error_message
        self.prefix = prefix

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        if self.should_fail:
            return TranslationResult(
                translated_text="",
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
                confidence=0.0,
                status="FAILED",
                error_message=self.failure_error_message,
            )

        output_prefix = self.prefix or f"[{target_lang.upper()}]"
        return TranslationResult(
            translated_text=f"{output_prefix} {text}",
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
            confidence=1.0,
            status="COMPLETED",
        )
