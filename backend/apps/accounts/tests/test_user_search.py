"""
Tests for User Search API conforming to Section 38.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserSearchAPI:
    def setup_method(self):
        self.client = APIClient()
        self.me = User.objects.create_user(
            username="deepak",
            email="deepak@example.com",
            password="Password123!",
            display_name="Deepak Tirole",
        )
        self.other1 = User.objects.create_user(
            username="john_smith",
            email="john@example.com",
            password="Password123!",
            display_name="John Smith",
        )
        self.other2 = User.objects.create_user(
            username="meet_patel",
            email="meet@example.com",
            password="Password123!",
            display_name="Meet Patel",
        )
        self.inactive_user = User.objects.create_user(
            username="inactive_john",
            email="inactive@example.com",
            password="Password123!",
            display_name="Inactive John",
            is_active=False,
        )

        login_res = self.client.post(
            "/api/v1/auth/login/",
            {"username": "deepak", "password": "Password123!"},
            format="json",
        )
        self.token = login_res.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_search_by_username(self):
        response = self.client.get("/api/v1/users/search/?q=john")
        assert response.status_code == 200
        assert len(response.data) == 1
        result = response.data[0]
        assert result["username"] == "john_smith"
        assert result["display_name"] == "John Smith"

        # Verify private fields are NOT exposed (Section 38)
        assert "email" not in result
        assert "interface_language" not in result
        assert "preferred_chat_language" not in result
        assert "last_seen_at" not in result

    def test_search_by_display_name(self):
        response = self.client.get("/api/v1/users/search/?q=meet")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["username"] == "meet_patel"

    def test_search_excludes_self(self):
        response = self.client.get("/api/v1/users/search/?q=deepak")
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_search_excludes_inactive_users(self):
        response = self.client.get("/api/v1/users/search/?q=inactive")
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_empty_query_returns_empty_list(self):
        response = self.client.get("/api/v1/users/search/?q=")
        assert response.status_code == 200
        assert response.data == []
