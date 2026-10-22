"""
Base models for VaaniLink applications.
"""

from .base import SoftDeleteModel, TimeStampedModel, UUIDModel

__all__ = [
    "TimeStampedModel",
    "UUIDModel",
    "SoftDeleteModel",
]
