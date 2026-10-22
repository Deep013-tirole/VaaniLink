"""
Registry and factory for translation engine providers.
Conforms strictly to Section 4, Section 25, and Section 47:
- Model/provider-independent translation architecture
- Pluggable provider selection via settings
- Extensible without altering messaging logic
"""

from django.conf import settings

from apps.translation.providers.base import BaseTranslationProvider
from apps.translation.providers.google_cloud import GoogleCloudTranslationProvider
from apps.translation.providers.mock import MockTranslationProvider
from apps.translation.providers.rule_based import RuleBasedTranslationProvider


class TranslationProviderRegistry:
    """Registry managing available translation engine providers."""

    _providers: dict[str, BaseTranslationProvider] = {}

    @classmethod
    def _initialize_defaults(cls) -> None:
        if not cls._providers:
            cls._providers["rule_based"] = RuleBasedTranslationProvider()
            cls._providers["google_cloud"] = GoogleCloudTranslationProvider()
            cls._providers["mock"] = MockTranslationProvider()

    @classmethod
    def register(cls, name: str, provider: BaseTranslationProvider) -> None:
        cls._initialize_defaults()
        cls._providers[name.lower()] = provider

    @classmethod
    def get(cls, name: str | None = None) -> BaseTranslationProvider:
        cls._initialize_defaults()
        provider_name = name or getattr(settings, "DEFAULT_TRANSLATION_PROVIDER", "rule_based")
        provider = cls._providers.get(provider_name.lower())
        if not provider:
            # Fall back safely to rule_based
            return cls._providers["rule_based"]
        return provider

    @classmethod
    def list_available(cls) -> list[str]:
        cls._initialize_defaults()
        return list(cls._providers.keys())
