"""Translation providers package."""

from apps.translation.providers.base import BaseTranslationProvider, TranslationResult
from apps.translation.providers.google_cloud import GoogleCloudTranslationProvider
from apps.translation.providers.mock import MockTranslationProvider
from apps.translation.providers.registry import TranslationProviderRegistry
from apps.translation.providers.rule_based import RuleBasedTranslationProvider

__all__ = [
    "BaseTranslationProvider",
    "TranslationResult",
    "RuleBasedTranslationProvider",
    "GoogleCloudTranslationProvider",
    "MockTranslationProvider",
    "TranslationProviderRegistry",
]
