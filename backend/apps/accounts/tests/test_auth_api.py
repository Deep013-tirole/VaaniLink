"""
Tests for Authentication API endpoints conforming to Section 37 & Section 43.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.languages.models import Language


@pytest.mark.django_db
class TestAuthAPI:
    def setup_method(self):
        self.client = APIClient()
        self.en = Language.objects.create(
            code="en", name="English", native_name="English", script_code="Latn"
        )
        self.hi = Language.objects.create(
            code="hi", name="Hindi", native_name="हिन्दी", script_code="Deva"
        )

    def test_register_success(self):
        payload = {
            "username": "deepak_tirole",
            "email": "deepak@example.com",
            "display_name": "Deepak Tirole",
            "password": "Password123!",
            "interface_language": "en",
            "preferred_chat_language": "hi",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")

        assert response.status_code == 201
        assert "user" in response.data
        assert "tokens" in response.data
        user_data = response.data["user"]
        assert user_data["username"] == "deepak_tirole"
        assert user_data["display_name"] == "Deepak Tirole"
        assert user_data["interface_language"]["code"] == "en"
        assert user_data["preferred_chat_language"]["code"] == "hi"
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    def test_register_duplicate_username_returns_section43_error(self):
        User.objects.create_user(
            username="deepak",
            email="existing@example.com",
            password="Password123!",
            display_name="Deepak First",
        )
        payload = {
            "username": "deepak",
            "email": "new@example.com",
            "display_name": "Deepak Second",
            "password": "Password123!",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")

        assert response.status_code == 409
        assert "error" in response.data
        error = response.data["error"]
        assert error["code"] == "USERNAME_ALREADY_EXISTS"
        assert "username" in error["fields"]

    def test_register_duplicate_email_returns_section43_error(self):
        User.objects.create_user(
            username="user_one",
            email="common@example.com",
            password="Password123!",
            display_name="User One",
        )
        payload = {
            "username": "user_two",
            "email": "common@example.com",
            "display_name": "User Two",
            "password": "Password123!",
        }
        response = self.client.post("/api/v1/auth/register/", payload, format="json")

        assert response.status_code == 409
        assert "error" in response.data
        error = response.data["error"]
        assert error["code"] == "EMAIL_ALREADY_EXISTS"
        assert "email" in error["fields"]

    def test_login_success_by_username(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        payload = {"username": "deepak", "password": "Password123!"}
        response = self.client.post("/api/v1/auth/login/", payload, format="json")

        assert response.status_code == 200
        assert "tokens" in response.data
        assert response.data["user"]["username"] == "deepak"

    def test_login_success_by_email(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        payload = {"username": "deepak@example.com", "password": "Password123!"}
        response = self.client.post("/api/v1/auth/login/", payload, format="json")

        assert response.status_code == 200
        assert response.data["user"]["username"] == "deepak"

    def test_login_invalid_password_returns_401(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        payload = {"username": "deepak", "password": "WrongPassword"}
        response = self.client.post("/api/v1/auth/login/", payload, format="json")

        assert response.status_code == 401
        assert response.data["error"]["code"] == "INVALID_CREDENTIALS"

    def test_me_endpoint_requires_auth(self):
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == 401

    def test_me_endpoint_with_valid_jwt(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
            interface_language=self.en,
            preferred_chat_language=self.hi,
        )
        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        access_token = login_res.data["tokens"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get("/api/v1/auth/me/")

        assert response.status_code == 200
        assert response.data["user"]["username"] == "deepak"
        assert response.data["user"]["preferred_chat_language"]["code"] == "hi"

    def test_token_refresh_lifecycle(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        refresh_token = login_res.data["tokens"]["refresh"]

        refresh_res = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json"
        )
        assert refresh_res.status_code == 200
        assert "access" in refresh_res.data["tokens"]

    def test_logout_endpoint(self):
        User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        login_res = self.client.post(
            "/api/v1/auth/login/", {"username": "deepak", "password": "Password123!"}, format="json"
        )
        refresh_token = login_res.data["tokens"]["refresh"]

        logout_res = self.client.post(
            "/api/v1/auth/logout/", {"refresh": refresh_token}, format="json"
        )
        assert logout_res.status_code == 200
        assert logout_res.data["message"] == "Successfully logged out."
