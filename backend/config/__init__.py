"""
VaaniLink Configuration Package.
Exposes Celery application so shared_task decorators will bind properly.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
