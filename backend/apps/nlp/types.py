"""
Data types and schemas for the NLP Language Intelligence Pipeline.
Conforms to Section 14, 15, 16, 23, and docs/NLP_PIPELINE.md.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenAnalysis:
    """Analysis for an individual token within a sentence."""

    text: str
    token_type: str  # "word", "emoji", "protected", "punctuation", "number"
    script: str | None = None
    language: str | None = None
    is_romanized: bool = False
    is_code_mixed: bool = False


@dataclass
class NLPResult:
    """Complete result returned by the NLP intelligence pipeline."""

    raw_text: str
    cleaned_text: str
    detected_primary_language: str
    detected_script: str
    is_mixed_language: bool
    is_romanized: bool
    language_confidence: float
    detected_languages: list[dict[str, Any]] = field(default_factory=list)
    tokens: list[TokenAnalysis] = field(default_factory=list)
    protected_tokens: dict[str, str] = field(default_factory=dict)
    transliterated_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "detected_primary_language": self.detected_primary_language,
            "detected_script": self.detected_script,
            "is_mixed_language": self.is_mixed_language,
            "is_romanized": self.is_romanized,
            "language_confidence": round(self.language_confidence, 4),
            "detected_languages": self.detected_languages,
            "tokens": [
                {
                    "text": t.text,
                    "token_type": t.token_type,
                    "script": t.script,
                    "language": t.language,
                    "is_romanized": t.is_romanized,
                }
                for t in self.tokens
            ],
            "protected_tokens_count": len(self.protected_tokens),
            "transliterated_text": self.transliterated_text,
        }
