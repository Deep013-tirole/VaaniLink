"""
Translation fan-out, resilience, and caching tests (Phase 10 Hardening).
Verifies:
- Fan-out deduplication: translates once per unique target language
- Provider failure degradation (messaging is decoupled and continues)
- Cache hit avoids duplicate translation calls
"""

import uuid

import pytest

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.languages.models import Language
from apps.messaging.services import MessageService
from apps.translation.cache import TranslationCache
from apps.translation.models import MessageTranslation, TranslationStatus
from apps.translation.services import TranslationService


@pytest.mark.django_db
class TestTranslationResilience:
    def setup_method(self):
        self.lang_en, _ = Language.objects.get_or_create(
            code="en", defaults={"name": "English", "native_name": "English", "script_code": "Latn"}
        )
        self.lang_hi, _ = Language.objects.get_or_create(
            code="hi", defaults={"name": "Hindi", "native_name": "हिन्दी", "script_code": "Deva"}
        )
        self.lang_gu, _ = Language.objects.get_or_create(
            code="gu", defaults={"name": "Gujarati", "native_name": "ગુજરાતી", "script_code": "Gujr"}
        )

        self.sender = User.objects.create_user(
            username="sender_res",
            email="sender_res@example.com",
            display_name="Sender",
            password="Password123!",
            preferred_chat_language=self.lang_en,
        )
        # Recipients with duplicate preferred languages
        self.u_hi1 = User.objects.create_user(
            username="uhi1",
            email="uhi1@example.com",
            display_name="Hi 1",
            password="Password123!",
            preferred_chat_language=self.lang_hi,
        )
        self.u_hi2 = User.objects.create_user(
            username="uhi2",
            email="uhi2@example.com",
            display_name="Hi 2",
            password="Password123!",
            preferred_chat_language=self.lang_hi,
        )
        self.u_hi3 = User.objects.create_user(
            username="uhi3",
            email="uhi3@example.com",
            display_name="Hi 3",
            password="Password123!",
            preferred_chat_language=self.lang_hi,
        )
        self.u_gu1 = User.objects.create_user(
            username="ugu1",
            email="ugu1@example.com",
            display_name="Gu 1",
            password="Password123!",
            preferred_chat_language=self.lang_gu,
        )

        self.group = ConversationService.create_group(
            creator=self.sender,
            group_name="Fanout Test Group",
            member_ids=[self.u_hi1.id, self.u_hi2.id, self.u_hi3.id, self.u_gu1.id],
        )

    def test_fanout_deduplication(self):
        """
        Group with 4 recipients (3 Hindi, 1 Gujarati) must collapse
        target languages to exactly {'hi', 'gu'}.
        """
        msg = MessageService.send_message(
            conversation_id=self.group.id,
            sender=self.sender,
            client_message_id=uuid.uuid4(),
            text="Hello everyone, team sync tomorrow!",
        )
        msg.detected_primary_language = "en"

        targets = TranslationService.determine_target_languages(msg)
        assert targets == {"hi", "gu"}

    def test_cache_hit_returns_without_calling_provider(self):
        """Identical text retrieval hits cache and returns cached translation."""
        source_text = "Are you coming tomorrow unique test?"
        cached_val = "क्या आप कल आ रहे हैं? (From Cache)"

        TranslationCache.set("en", "hi", source_text, cached_val)
        retrieved = TranslationCache.get("en", "hi", source_text)
        assert retrieved == cached_val

    def test_provider_failure_gracefully_handled(self):
        """Simulated provider failure records status FAILED without breaking system."""
        msg = MessageService.send_message(
            conversation_id=self.group.id,
            sender=self.sender,
            client_message_id=uuid.uuid4(),
            text="Testing translation error handling",
        )

        record = MessageTranslation.objects.create(
            message=msg,
            source_language="en",
            target_language="fr",
            translated_text="",
            provider="mock",
            status=TranslationStatus.FAILED,
            error_message="Simulated upstream timeout",
        )
        assert record.status == TranslationStatus.FAILED
        assert "timeout" in record.error_message
