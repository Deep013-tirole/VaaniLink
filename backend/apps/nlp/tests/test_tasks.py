"""
Tests for NLP Celery asynchronous tasks.
"""

import uuid

import pytest

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.messaging.models import Message
from apps.nlp.tasks import analyze_message_nlp


@pytest.mark.django_db
class TestNLPTasks:
    def test_analyze_message_nlp_task(self):
        u1 = User.objects.create_user(
            username="nlp_task_u1",
            email="nt1@example.com",
            display_name="NLP Task U1",
            password="Password123!",
        )
        u2 = User.objects.create_user(
            username="nlp_task_u2",
            email="nt2@example.com",
            display_name="NLP Task U2",
            password="Password123!",
        )
        conv, _ = ConversationService.get_or_create_direct_conversation(u1, u2)

        msg = Message.objects.create(
            conversation=conv,
            sender=u1,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="me kal nahi aaunga 😊",
        )

        assert msg.detected_primary_language is None

        # Execute task
        analyze_message_nlp(str(msg.id))

        msg.refresh_from_db()
        assert msg.detected_primary_language == "hi"
        assert msg.detected_script == "Latn"
        assert msg.is_romanized is True
        assert msg.language_confidence is not None
