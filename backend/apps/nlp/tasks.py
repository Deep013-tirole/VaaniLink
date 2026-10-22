"""
Celery asynchronous tasks for NLP language intelligence.
Conforms to Section 5, Section 23, and docs/NLP_PIPELINE.md.
"""

import uuid

from celery import shared_task
from django.utils import timezone


@shared_task(name="apps.nlp.tasks.analyze_message_nlp")
def analyze_message_nlp(message_id: str | uuid.UUID):
    """
    Asynchronously analyze message original text, detect language, script,
    romanization, and code-mixing, then persist to the Message model.
    """
    from apps.messaging.models import Message
    from apps.nlp.pipeline import NLPPipeline
    from apps.realtime.services import RealtimeNotifier

    message = Message.objects.filter(id=message_id).first()
    if not message:
        return None

    # Run NLP pipeline
    nlp_result = NLPPipeline.process(message.original_text)

    # Update Message model fields
    message.detected_primary_language = nlp_result.detected_primary_language
    message.detected_script = nlp_result.detected_script
    message.is_mixed_language = nlp_result.is_mixed_language
    message.is_romanized = nlp_result.is_romanized
    message.language_confidence = nlp_result.language_confidence
    message.updated_at = timezone.now()

    message.save(
        update_fields=[
            "detected_primary_language",
            "detected_script",
            "is_mixed_language",
            "is_romanized",
            "language_confidence",
            "updated_at",
        ]
    )

    # Broadcast real-time message.updated event to conversation room
    from apps.messaging.api.serializers import MessageDetailSerializer

    serialized_data = MessageDetailSerializer(message).data
    RealtimeNotifier.send_to_conversation(
        message.conversation_id,
        "message.updated",
        serialized_data,
    )

    # Trigger translation pipeline asynchronously (Section 5)
    try:
        from apps.translation.tasks import translate_message_task

        translate_message_task.delay(str(message.id))
    except Exception:
        try:
            from apps.translation.tasks import translate_message_task

            translate_message_task(str(message.id))
        except Exception:
            pass

    return nlp_result.to_dict()
