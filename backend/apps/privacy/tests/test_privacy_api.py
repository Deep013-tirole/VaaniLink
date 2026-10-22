"""
Integration tests for Privacy and Blocking REST APIs and cross-app enforcement.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.conversations.services import ConversationService
from apps.privacy.models import PrivacyVisibility
from apps.privacy.services import PrivacyService


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user1(db):
    return User.objects.create_user(
        username="privacy_alice",
        email="alice@example.com",
        display_name="Alice P",
        password="Password123!",
    )


@pytest.fixture
def user2(db):
    return User.objects.create_user(
        username="privacy_bob",
        email="bob@example.com",
        display_name="Bob P",
        password="Password123!",
    )


@pytest.fixture
def user3(db):
    return User.objects.create_user(
        username="privacy_carol",
        email="carol@example.com",
        display_name="Carol P",
        password="Password123!",
    )


@pytest.mark.django_db
def test_privacy_settings_api(client, user1):
    client.force_authenticate(user=user1)

    # 1. Get settings
    resp = client.get("/api/v1/privacy/")
    assert resp.status_code == 200
    assert resp.data["last_seen_visibility"] == PrivacyVisibility.EVERYONE
    assert resp.data["read_receipts_enabled"] is True

    # 2. Update settings
    patch_resp = client.patch(
        "/api/v1/privacy/",
        {
            "last_seen_visibility": PrivacyVisibility.NOBODY,
            "read_receipts_enabled": False,
            "who_can_message_me": PrivacyVisibility.CONTACTS_ONLY,
        },
        format="json",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.data["last_seen_visibility"] == PrivacyVisibility.NOBODY
    assert patch_resp.data["read_receipts_enabled"] is False
    assert patch_resp.data["who_can_message_me"] == PrivacyVisibility.CONTACTS_ONLY


@pytest.mark.django_db
def test_blocks_api(client, user1, user2):
    client.force_authenticate(user=user1)

    # 1. Block user by username
    resp = client.post("/api/v1/blocks/", {"username": user2.username}, format="json")
    assert resp.status_code == 201
    assert resp.data["user"]["id"] == str(user2.id)

    # 2. List blocks
    list_resp = client.get("/api/v1/blocks/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) == 1
    assert list_resp.data[0]["user"]["username"] == user2.username

    # 3. Unblock
    del_resp = client.delete(f"/api/v1/blocks/{user2.id}/")
    assert del_resp.status_code == 200

    # 4. Verify unblocked
    list_resp2 = client.get("/api/v1/blocks/")
    assert len(list_resp2.data) == 0


@pytest.mark.django_db
def test_direct_conversation_creation_blocked_enforcement(client, user1, user2):
    # User 2 blocks User 1
    PrivacyService.block_user(user2, user1)

    client.force_authenticate(user=user1)
    resp = client.post("/api/v1/conversations/direct/", {"user_id": str(user2.id)}, format="json")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "USER_BLOCKED"


@pytest.mark.django_db
def test_direct_conversation_creation_message_permission_enforcement(client, user1, user2):
    # User 2 sets who_can_message_me = NOBODY
    PrivacyService.update_settings(user2, {"who_can_message_me": PrivacyVisibility.NOBODY})

    client.force_authenticate(user=user1)
    resp = client.post("/api/v1/conversations/direct/", {"user_id": str(user2.id)}, format="json")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "DIRECT_MESSAGES_RESTRICTED"


@pytest.mark.django_db
def test_direct_messaging_blocked_enforcement(client, user1, user2):
    # Establish conversation first
    conv, _ = ConversationService.get_or_create_direct_conversation(user1, user2)

    # Now User 2 blocks User 1
    PrivacyService.block_user(user2, user1)

    client.force_authenticate(user=user1)
    resp = client.post(
        f"/api/v1/conversations/{conv.id}/messages/",
        {
            "client_message_id": str(uuid.uuid4()),
            "text": "Hello, can you hear me?",
        },
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "MESSAGE_SEND_RESTRICTED"


@pytest.mark.django_db
def test_group_add_members_privacy_enforcement(client, user1, user2):
    # User 2 restricts who_can_add_me_to_groups = NOBODY
    PrivacyService.update_settings(user2, {"who_can_add_me_to_groups": PrivacyVisibility.NOBODY})

    group = ConversationService.create_group(creator=user1, group_name="Dev Squad")

    client.force_authenticate(user=user1)
    resp = client.post(
        f"/api/v1/conversations/{group.id}/members/",
        {"user_ids": [str(user2.id)]},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "GROUP_INVITE_RESTRICTED"


@pytest.mark.django_db
def test_presence_api_privacy_masking(client, user1, user2):
    # User 2 sets both online and last seen to NOBODY
    PrivacyService.update_settings(
        user2,
        {
            "online_status_visibility": PrivacyVisibility.NOBODY,
            "last_seen_visibility": PrivacyVisibility.NOBODY,
        },
    )

    client.force_authenticate(user=user1)
    resp = client.get(f"/api/v1/presence/users/{user2.id}/")
    assert resp.status_code == 200
    assert resp.data["is_online"] is False
    assert resp.data["last_seen_at"] is None
