"""
Tests for Users API endpoints (PATCH /api/v1/users/me/).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.languages.models import Language


@pytest.mark.django_db
class TestUsersAPI:
    def setup_method(self):
        self.client = APIClient()
        self.en = Language.objects.create(
            code="en", name="English", native_name="English", script_code="Latn"
        )
        self.hi = Language.objects.create(
            code="hi", name="Hindi", native_name="हिन्दी", script_code="Deva"
        )
        self.gu = Language.objects.create(
            code="gu", name="Gujarati", native_name="ગુજરાતી", script_code="Gujr"
        )

        self.user = User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
            interface_language=self.en,
            preferred_chat_language=self.en,
        )

        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        self.access_token = login_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_update_display_name_and_chat_language(self):
        payload = {
            "display_name": "Deepak T.",
            "preferred_chat_language": "hi",
        }
        response = self.client.patch("/api/v1/users/me/", payload, format="json")

        assert response.status_code == 200
        user_data = response.data["user"]
        assert user_data["display_name"] == "Deepak T."
        assert user_data["preferred_chat_language"]["code"] == "hi"
        assert user_data["interface_language"]["code"] == "en"

        self.user.refresh_from_db()
        assert self.user.display_name == "Deepak T."
        assert self.user.preferred_chat_language.code == "hi"

    def test_update_interface_language_distinct_from_chat_language(self):
        payload = {
            "interface_language": "gu",
        }
        response = self.client.patch("/api/v1/users/me/", payload, format="json")

        assert response.status_code == 200
        user_data = response.data["user"]
        assert user_data["interface_language"]["code"] == "gu"
        assert user_data["preferred_chat_language"]["code"] == "en"

    def test_update_unauthenticated_forbidden(self):
        self.client.credentials()  # Clear auth headers
        response = self.client.patch("/api/v1/users/me/", {"display_name": "Anon"}, format="json")
        assert response.status_code == 401
