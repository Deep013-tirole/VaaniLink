"""
Tests for PresenceService and presence API endpoints.
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.realtime.services import PresenceService


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestPresenceService:
    def test_add_and_remove_connections(self):
        user = User.objects.create_user(
            username="presence_user",
            email="presence@example.com",
            display_name="Presence User",
            password="Password123!",
        )

        assert not PresenceService.is_user_online(user.id)

        # First connection transitions user to online
        is_first = PresenceService.add_user_connection(user.id)
        assert is_first is True
        assert PresenceService.is_user_online(user.id) is True

        # Second connection retains online status without is_first
        is_first_2 = PresenceService.add_user_connection(user.id)
        assert is_first_2 is False
        assert PresenceService.is_user_online(user.id) is True

        # First disconnect leaves 1 connection
        is_last = PresenceService.remove_user_connection(user.id)
        assert is_last is False
        assert PresenceService.is_user_online(user.id) is True

        # Second disconnect transitions user to offline
        is_last_2 = PresenceService.remove_user_connection(user.id)
        assert is_last_2 is True
        assert PresenceService.is_user_online(user.id) is False

    def test_get_user_presence(self):
        user = User.objects.create_user(
            username="user_p2",
            email="p2@example.com",
            display_name="User P2",
            password="Password123!",
        )

        PresenceService.add_user_connection(user.id)
        presence = PresenceService.get_user_presence(user.id)
        assert presence["user_id"] == str(user.id)
        assert presence["is_online"] is True

        PresenceService.remove_user_connection(user.id)
        presence_offline = PresenceService.get_user_presence(user.id)
        assert presence_offline["is_online"] is False
        assert presence_offline["last_seen_at"] is not None


@pytest.mark.django_db
class TestPresenceAPI:
    def test_get_user_presence_endpoint(self):
        user1 = User.objects.create_user(
            username="api_user1",
            email="u1@example.com",
            display_name="API User 1",
            password="Password123!",
        )
        user2 = User.objects.create_user(
            username="api_user2",
            email="u2@example.com",
            display_name="API User 2",
            password="Password123!",
        )

        PresenceService.add_user_connection(user2.id)

        client = APIClient()
        client.force_authenticate(user=user1)

        res = client.get(f"/api/v1/presence/users/{user2.id}/")
        assert res.status_code == 200
        assert res.data["user_id"] == str(user2.id)
        assert res.data["is_online"] is True

    def test_bulk_presence_endpoint(self):
        user1 = User.objects.create_user(
            username="bulk_u1",
            email="b1@example.com",
            display_name="Bulk 1",
            password="Password123!",
        )
        user2 = User.objects.create_user(
            username="bulk_u2",
            email="b2@example.com",
            display_name="Bulk 2",
            password="Password123!",
        )

        PresenceService.add_user_connection(user2.id)

        client = APIClient()
        client.force_authenticate(user=user1)

        res = client.post(
            "/api/v1/presence/users/",
            {"user_ids": [str(user1.id), str(user2.id)]},
            format="json",
        )
        assert res.status_code == 200
        statuses = res.data["statuses"]
        assert statuses[str(user1.id)]["is_online"] is False
        assert statuses[str(user2.id)]["is_online"] is True
