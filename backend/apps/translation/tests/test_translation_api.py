"""
API integration tests for Translation endpoints.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.models import Conversation
from apps.languages.models import Language
from apps.messaging.models import Message
from apps.translation.models import MessageTranslation, TranslationStatus


@pytest.mark.django_db
class TestTranslationAPI:
    @pytest.fixture
    def setup_data(self):
        lang_en = Language.objects.create(
            code="en", name="English", native_name="English", script_code="Latn"
        )
        lang_hi = Language.objects.create(
            code="hi", name="Hindi", native_name="हिन्दी", script_code="Deva"
        )

        user_a = User.objects.create_user(
            username="user_a",
            email="a@example.com",
            password="Password123!",
            preferred_chat_language=lang_en,
        )
        user_b = User.objects.create_user(
            username="user_b",
            email="b@example.com",
            password="Password123!",
            preferred_chat_language=lang_hi,
        )
        user_intruder = User.objects.create_user(
            username="intruder",
            email="intruder@example.com",
            password="Password123!",
            preferred_chat_language=lang_en,
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
        )

        trans = MessageTranslation.objects.create(
            message=msg,
            source_language="en",
            target_language="hi",
            translated_text="क्या आप कल आ रहे हैं?",
            status=TranslationStatus.COMPLETED,
            provider="rule_based",
        )

        return {
            "user_a": user_a,
            "user_b": user_b,
            "user_intruder": user_intruder,
            "conv": conv,
            "msg": msg,
            "trans": trans,
        }

    def test_get_message_translations_authorized_vs_unauthorized(self, setup_data):
        client = APIClient()
        msg = setup_data["msg"]

        # 1. Unauthenticated request -> 401
        res_unauth = client.get(f"/api/v1/translations/message/{msg.id}/")
        assert res_unauth.status_code == 401

        # 2. Member request -> 200
        client.force_authenticate(user=setup_data["user_a"])
        res_member = client.get(f"/api/v1/translations/message/{msg.id}/")
        assert res_member.status_code == 200
        data = res_member.json()
        assert len(data) == 1
        assert data[0]["target_language"] == "hi"
        assert data[0]["translated_text"] == "क्या आप कल आ रहे हैं?"

        # 3. Non-member intruder request -> 403
        client.force_authenticate(user=setup_data["user_intruder"])
        res_intruder = client.get(f"/api/v1/translations/message/{msg.id}/")
        assert res_intruder.status_code == 403

    def test_direct_translate_endpoint(self):
        client = APIClient()
        payload = {
            "text": "Hello",
            "source_language": "en",
            "target_language": "hi",
        }
        res = client.post("/api/v1/translations/translate/", data=payload, format="json")
        assert res.status_code == 200
        data = res.json()
        assert data["translated_text"] == "नमस्ते"
        assert data["status"] == "COMPLETED"

    def test_translation_feedback_endpoint(self, setup_data):
        client = APIClient()
        client.force_authenticate(user=setup_data["user_b"])
        trans = setup_data["trans"]

        payload = {
            "rating": 1,
            "comment": "Accurate and natural phrasing.",
        }
        res = client.post(f"/api/v1/translations/{trans.id}/feedback/", data=payload, format="json")
        assert res.status_code == 201
        data = res.json()
        assert data["rating"] == 1
        assert data["comment"] == "Accurate and natural phrasing."
        assert data["translation_id"] == str(trans.id)

    def test_retry_translation_endpoint(self, setup_data):
        client = APIClient()
        client.force_authenticate(user=setup_data["user_b"])
        msg = setup_data["msg"]

        payload = {
            "target_language": "gu",
        }
        res = client.post(
            f"/api/v1/translations/message/{msg.id}/retry/", data=payload, format="json"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["target_language"] == "gu"
        assert data["translated_text"] == "શું તમે કાલે આવી રહ્યા છો?"
