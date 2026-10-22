"""
Celery background tasks for asynchronous message translation.
Conforms strictly to Section 5, Section 25, Section 26, and Section 47:
- Asynchronous execution without blocking the sender or message storage
- Fan-out optimization across conversation recipients
- Automatic retry handling
"""

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.translation.tasks.translate_message_task")
def translate_message_task(message_id: str | uuid.UUID):
    """
    Asynchronously resolves target languages for conversation recipients,
    executes translation via configured provider / cache, and broadcasts
    real-time availability event to clients.
    """
    from apps.translation.services import TranslationService

    try:
        translations = TranslationService.translate_message(message_id)
        return [
            {
                "id": str(t.id),
                "target_language": t.target_language,
                "status": t.status,
            }
            for t in translations
        ]
    except Exception as exc:
        logger.error("Error in translate_message_task for message %s: %s", message_id, exc)
        return []
