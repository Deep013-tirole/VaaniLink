"""
Unit and API tests for Message Info, group receipts, and group translation fan-out.
Conforms strictly to Section 11, 12, 26, 46, and 47.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.languages.models import Language
from apps.messaging.models import MessageReceipt
from apps.messaging.services import MessageService
from apps.translation.services import TranslationService


@pytest.mark.django_db
class TestMessageInfoAndGroupFanOut:
    @pytest.fixture
    def setup_group_environment(self):
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
            display_name="Sender",
            preferred_chat_language=lang_en,
        )
        rec_hi_1 = User.objects.create_user(
            username="rec_hi_1",
            email="hi1@example.com",
            password="Password123!",
            display_name="Hindi User 1",
            preferred_chat_language=lang_hi,
        )
        rec_hi_2 = User.objects.create_user(
            username="rec_hi_2",
            email="hi2@example.com",
            password="Password123!",
            display_name="Hindi User 2",
            preferred_chat_language=lang_hi,
        )
        rec_gu = User.objects.create_user(
            username="rec_gu",
            email="gu@example.com",
            password="Password123!",
            display_name="Gujarati User",
            preferred_chat_language=lang_gu,
        )
        outsider = User.objects.create_user(
            username="outsider",
            email="out@example.com",
            password="Password123!",
            display_name="Outsider",
        )

        conv = ConversationService.create_group(
            creator=sender,
            group_name="Global Operations",
            member_ids=[rec_hi_1.id, rec_hi_2.id, rec_gu.id],
        )

        return {
            "sender": sender,
            "rec_hi_1": rec_hi_1,
            "rec_hi_2": rec_hi_2,
            "rec_gu": rec_gu,
            "outsider": outsider,
            "conv": conv,
        }

    def test_group_message_receipt_generation_and_message_info(self, setup_group_environment):
        client = APIClient()
        conv = setup_group_environment["conv"]
        sender = setup_group_environment["sender"]
        rec_hi_1 = setup_group_environment["rec_hi_1"]
        rec_gu = setup_group_environment["rec_gu"]
        outsider = setup_group_environment["outsider"]

        # 1. Sender sends message
        msg = MessageService.send_message(
            conversation_id=conv.id,
            sender=sender,
            client_message_id=uuid.uuid4(),
            text="Are you coming tomorrow?",
        )

        # Confirm receipts were created for all 3 other members
        assert MessageReceipt.objects.filter(message=msg).count() == 3

        # 2. Initially all 3 are pending
        info_initial = MessageService.get_message_info(msg.id, sender)
        assert info_initial["total_recipients"] == 3
        assert info_initial["read_count"] == 0
        assert info_initial["delivered_count"] == 0
        assert info_initial["pending_count"] == 3

        # 3. Mark delivered for rec_hi_1
        MessageService.mark_messages_delivered(rec_hi_1, [msg.id])

        # 4. Mark seen for rec_gu
        MessageService.mark_messages_seen(rec_gu, conv.id, message_ids=[msg.id])

        # 5. Fetch Message Info via API
        client.force_authenticate(user=sender)
        res = client.get(f"/api/v1/messages/{msg.id}/info/")
        assert res.status_code == 200
        data = res.json()

        assert data["total_recipients"] == 3
        assert data["read_count"] == 1
        assert data["delivered_count"] == 1
        assert data["pending_count"] == 1

        assert len(data["read_by"]) == 1
        assert data["read_by"][0]["user"]["username"] == "rec_gu"

        assert len(data["delivered_to"]) == 1
        assert data["delivered_to"][0]["user"]["username"] == "rec_hi_1"

        assert len(data["pending"]) == 1
        assert data["pending"][0]["user"]["username"] == "rec_hi_2"

        # 6. Non-member gets 403
        client.force_authenticate(user=outsider)
        res_intruder = client.get(f"/api/v1/messages/{msg.id}/info/")
        assert res_intruder.status_code == 403

    def test_group_translation_once_per_unique_language(self, setup_group_environment):
        conv = setup_group_environment["conv"]
        sender = setup_group_environment["sender"]

        msg = MessageService.send_message(
            conversation_id=conv.id,
            sender=sender,
            client_message_id=uuid.uuid4(),
            text="Are you coming tomorrow?",
        )
        msg.detected_primary_language = "en"
        msg.save(update_fields=["detected_primary_language"])

        # Determine target languages for the group (2 Hindi, 1 Gujarati)
        targets = TranslationService.determine_target_languages(msg)
        assert targets == {"hi", "gu"}

        # Perform translation
        translations = TranslationService.translate_message(msg.id)
        # Exactly 2 translations generated: 1 for Hindi, 1 for Gujarati (Fan-out optimization)
        assert len(translations) == 2
        trans_targets = {t.target_language for t in translations}
        assert trans_targets == {"hi", "gu"}
