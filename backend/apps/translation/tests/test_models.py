"""
Unit tests for Translation models (MessageTranslation, TranslationFeedback).
"""

import uuid

import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.conversations.models import Conversation
from apps.languages.models import Language
from apps.messaging.models import Message
from apps.translation.models import MessageTranslation, TranslationFeedback, TranslationStatus


@pytest.mark.django_db
class TestTranslationModels:
    @pytest.fixture
    def setup_entities(self):
        lang_en = Language.objects.create(
            code="en", name="English", native_name="English", script_code="Latn"
        )
        lang_hi = Language.objects.create(
            code="hi", name="Hindi", native_name="हिन्दी", script_code="Deva"
        )

        user_a = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="Password123!",
            preferred_chat_language=lang_en,
        )
        user_b = User.objects.create_user(
            username="receiver",
            email="receiver@example.com",
            password="Password123!",
            preferred_chat_language=lang_hi,
        )

        conv = Conversation.objects.create(type="DIRECT")
        conv.members.create(user=user_a)
        conv.members.create(user=user_b)

        msg = Message.objects.create(
            conversation=conv,
            sender=user_a,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Are you coming tomorrow?",
            detected_primary_language="en",
            detected_script="Latn",
        )
        return {
            "user_a": user_a,
            "user_b": user_b,
            "message": msg,
        }

    def test_message_translation_creation_and_uniqueness(self, setup_entities):
        msg = setup_entities["message"]

        t1 = MessageTranslation.objects.create(
            message=msg,
            source_language="en",
            target_language="hi",
            translated_text="क्या आप कल आ रहे हैं?",
            provider="rule_based",
            status=TranslationStatus.COMPLETED,
            confidence=0.95,
        )
        assert t1.id is not None
        assert t1.translated_text == "क्या आप कल आ रहे हैं?"
        assert t1.status == "COMPLETED"

        # Unique constraint on (message, target_language) prevents duplicates
        with pytest.raises(IntegrityError):
            MessageTranslation.objects.create(
                message=msg,
                source_language="en",
                target_language="hi",
                translated_text="क्या आप कल आ रहे हैं? (duplicate)",
            )

    def test_translation_feedback_creation_and_uniqueness(self, setup_entities):
        msg = setup_entities["message"]
        user_b = setup_entities["user_b"]

        trans = MessageTranslation.objects.create(
            message=msg,
            source_language="en",
            target_language="hi",
            translated_text="क्या आप कल आ रहे हैं?",
            provider="rule_based",
        )

        fb1 = TranslationFeedback.objects.create(
            translation=trans,
            user=user_b,
            rating=1,
            comment="Accurate translation!",
        )
        assert fb1.id is not None
        assert fb1.rating == 1

        # Unique constraint on (translation, user) prevents duplicate feedback rows
        with pytest.raises(IntegrityError):
            TranslationFeedback.objects.create(
                translation=trans,
                user=user_b,
                rating=-1,
                comment="Changed mind",
            )
