"""
Unit and integration tests for TranslationService.
"""

import uuid

import pytest

from apps.accounts.models import User
from apps.conversations.models import Conversation
from apps.languages.models import Language
from apps.messaging.models import Message
from apps.translation.models import MessageTranslation, TranslationStatus
from apps.translation.services import TranslationService


@pytest.mark.django_db
class TestTranslationService:
    @pytest.fixture
    def conversation_setup(self):
        lang_en = Language.objects.create(
            code="en", name="English", native_name="English", script_code="Latn"
        )
        lang_hi = Language.objects.create(
            code="hi", name="Hindi", native_name="हिन्दी", script_code="Deva"
        )
        lang_gu = Language.objects.create(
            code="gu", name="Gujarati", native_name="ગુજરાતી", script_code="Gujr"
        )

        sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="Password123!",
            preferred_chat_language=lang_en,
        )
        rec_hi_1 = User.objects.create_user(
            username="rec_hi_1",
            email="hi1@example.com",
            password="Password123!",
            preferred_chat_language=lang_hi,
        )
        rec_hi_2 = User.objects.create_user(
            username="rec_hi_2",
            email="hi2@example.com",
            password="Password123!",
            preferred_chat_language=lang_hi,
        )
        rec_gu = User.objects.create_user(
            username="rec_gu",
            email="gu@example.com",
            password="Password123!",
            preferred_chat_language=lang_gu,
        )

        conv = Conversation.objects.create(type="GROUP", group_name="Team Alpha")
        conv.members.create(user=sender)
        conv.members.create(user=rec_hi_1)
        conv.members.create(user=rec_hi_2)
        conv.members.create(user=rec_gu)

        return {
            "sender": sender,
            "rec_hi_1": rec_hi_1,
            "rec_hi_2": rec_hi_2,
            "rec_gu": rec_gu,
            "conv": conv,
        }

    def test_determine_target_languages_fan_out(self, conversation_setup):
        conv = conversation_setup["conv"]
        sender = conversation_setup["sender"]

        msg = Message.objects.create(
            conversation=conv,
            sender=sender,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Are you coming tomorrow?",
            detected_primary_language="en",
            detected_script="Latn",
        )

        targets = TranslationService.determine_target_languages(msg)
        # 2 users prefer hi, 1 user prefers gu -> unique targets should be {"hi", "gu"}
        assert targets == {"hi", "gu"}

    def test_translate_message_fan_out_and_persistence(self, conversation_setup):
        conv = conversation_setup["conv"]
        sender = conversation_setup["sender"]

        msg = Message.objects.create(
            conversation=conv,
            sender=sender,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Are you coming tomorrow?",
            detected_primary_language="en",
            detected_script="Latn",
        )

        translations = TranslationService.translate_message(msg.id)
        assert len(translations) == 2

        target_langs = {t.target_language for t in translations}
        assert target_langs == {"hi", "gu"}

        hi_trans = next(t for t in translations if t.target_language == "hi")
        assert hi_trans.translated_text == "क्या आप कल आ रहे हैं?"
        assert hi_trans.status == TranslationStatus.COMPLETED

        gu_trans = next(t for t in translations if t.target_language == "gu")
        assert gu_trans.translated_text == "શું તમે કાલે આવી રહ્યા છો?"
        assert gu_trans.status == TranslationStatus.COMPLETED

        # Verifying database records
        assert MessageTranslation.objects.filter(message=msg).count() == 2

    def test_translate_message_caches_and_reuses(self, conversation_setup):
        conv = conversation_setup["conv"]
        sender = conversation_setup["sender"]

        msg1 = Message.objects.create(
            conversation=conv,
            sender=sender,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Are you coming tomorrow?",
            detected_primary_language="en",
        )
        TranslationService.translate_message(msg1.id)

        # Send second message with identical text
        msg2 = Message.objects.create(
            conversation=conv,
            sender=sender,
            client_message_id=uuid.uuid4(),
            sequence_number=2,
            original_text="Are you coming tomorrow?",
            detected_primary_language="en",
        )
        translations_2 = TranslationService.translate_message(msg2.id)
        assert len(translations_2) == 2

        # One of them used cache
        for t in translations_2:
            assert t.status == TranslationStatus.COMPLETED
            assert "cache" in t.provider or "rule_based" in t.provider

    def test_direct_translate_and_feedback(self, conversation_setup):
        user = conversation_setup["sender"]

        res = TranslationService.direct_translate(
            "How are you?", source_lang="en", target_lang="hi"
        )
        assert res.status == "COMPLETED"
        assert res.translated_text == "आप कैसे हैं?"

        # Direct translate same string again should hit cache
        res_cached = TranslationService.direct_translate(
            "How are you?", source_lang="en", target_lang="hi"
        )
        assert res_cached.is_cached is True
        assert res_cached.translated_text == "आप कैसे हैं?"

        # Test feedback
        msg = Message.objects.create(
            conversation=conversation_setup["conv"],
            sender=user,
            client_message_id=uuid.uuid4(),
            sequence_number=1,
            original_text="Hello",
            detected_primary_language="en",
        )
        trans = MessageTranslation.objects.create(
            message=msg,
            source_language="en",
            target_language="hi",
            translated_text="नमस्ते",
            provider="rule_based",
        )

        fb = TranslationService.submit_feedback(
            trans.id, user, rating=1, comment="Great translation"
        )
        assert fb.rating == 1
        assert fb.comment == "Great translation"
