"""
Tests for PrivacyService domain logic.
"""

import pytest

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ValidationError
from apps.conversations.services import ConversationService
from apps.privacy.models import PrivacyVisibility
from apps.privacy.services import PrivacyService


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username="user_a",
        email="a@example.com",
        display_name="User A",
        password="Password123!",
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username="user_b",
        email="b@example.com",
        display_name="User B",
        password="Password123!",
    )


@pytest.fixture
def user_c(db):
    return User.objects.create_user(
        username="user_c",
        email="c@example.com",
        display_name="User C",
        password="Password123!",
    )


@pytest.mark.django_db
def test_privacy_settings_defaults_and_updates(user_a):
    settings = PrivacyService.get_or_create_settings(user_a)
    assert settings.last_seen_visibility == PrivacyVisibility.EVERYONE
    assert settings.online_status_visibility == PrivacyVisibility.EVERYONE
    assert settings.read_receipts_enabled is True
    assert settings.who_can_message_me == PrivacyVisibility.EVERYONE
    assert settings.who_can_add_me_to_groups == PrivacyVisibility.EVERYONE

    updated = PrivacyService.update_settings(
        user_a,
        {
            "last_seen_visibility": PrivacyVisibility.NOBODY,
            "read_receipts_enabled": False,
        },
    )
    assert updated.last_seen_visibility == PrivacyVisibility.NOBODY
    assert updated.read_receipts_enabled is False


@pytest.mark.django_db
def test_user_blocking_and_unblocking(user_a, user_b):
    # Cannot block self
    with pytest.raises(ValidationError) as exc:
        PrivacyService.block_user(user_a, user_a)
    assert exc.value.code == "CANNOT_BLOCK_SELF"

    # User A blocks User B
    block = PrivacyService.block_user(user_a, user_b)
    assert block.blocker == user_a
    assert block.blocked == user_b

    assert PrivacyService.is_blocked_by(user_a, user_b) is True
    assert PrivacyService.is_blocked_by(user_b, user_a) is False
    assert PrivacyService.is_blocked_bidirectional(user_a, user_b) is True
    assert PrivacyService.is_blocked_bidirectional(user_b, user_a) is True

    blocked_users = list(PrivacyService.get_blocked_users(user_a))
    assert user_b in blocked_users

    # Unblock
    PrivacyService.unblock_user(user_a, user_b)
    assert PrivacyService.is_blocked_by(user_a, user_b) is False
    assert PrivacyService.is_blocked_bidirectional(user_a, user_b) is False

    # Unblock non-blocked raises NotFoundError
    with pytest.raises(NotFoundError):
        PrivacyService.unblock_user(user_a, user_b)


@pytest.mark.django_db
def test_online_and_last_seen_visibility(user_a, user_b, user_c):
    # Self is always allowed
    assert PrivacyService.can_view_online_status(user_a, user_a) is True
    assert PrivacyService.can_view_last_seen(user_a, user_a) is True

    # Set visibility to CONTACTS_ONLY. No direct chat exists between A and B
    PrivacyService.update_settings(
        user_b,
        {
            "online_status_visibility": PrivacyVisibility.CONTACTS_ONLY,
            "last_seen_visibility": PrivacyVisibility.CONTACTS_ONLY,
        },
    )
    assert PrivacyService.can_view_online_status(user_a, user_b) is False
    assert PrivacyService.can_view_last_seen(user_a, user_b) is False

    # Establish direct chat -> now contacts
    ConversationService.get_or_create_direct_conversation(user_a, user_b)
    assert PrivacyService.can_view_online_status(user_a, user_b) is True
    assert PrivacyService.can_view_last_seen(user_a, user_b) is True

    # User C is not a contact
    assert PrivacyService.can_view_online_status(user_c, user_b) is False

    # Set user B online status to EVERYONE
    PrivacyService.update_settings(user_b, {"online_status_visibility": PrivacyVisibility.EVERYONE})
    assert PrivacyService.can_view_online_status(user_c, user_b) is True

    # Set user B last seen to NOBODY
    PrivacyService.update_settings(user_b, {"last_seen_visibility": PrivacyVisibility.NOBODY})
    assert PrivacyService.can_view_last_seen(user_a, user_b) is False

    # If blocked, always False even if set to EVERYONE
    PrivacyService.block_user(user_b, user_c)
    assert PrivacyService.can_view_online_status(user_c, user_b) is False


@pytest.mark.django_db
def test_messaging_and_group_invite_privacy(user_a, user_b, user_c):
    # Initially user B has who_can_message_me = EVERYONE
    assert PrivacyService.can_send_direct_message(user_a, user_b) is True

    # If user A is blocked by user B
    PrivacyService.block_user(user_b, user_a)
    assert PrivacyService.can_send_direct_message(user_a, user_b) is False
    assert PrivacyService.can_add_to_group(user_a, user_b) is False

    PrivacyService.unblock_user(user_b, user_a)

    # Restrict who_can_add_me_to_groups to CONTACTS_ONLY
    PrivacyService.update_settings(
        user_b, {"who_can_add_me_to_groups": PrivacyVisibility.CONTACTS_ONLY}
    )
    assert PrivacyService.can_add_to_group(user_a, user_b) is False

    ConversationService.get_or_create_direct_conversation(user_a, user_b)
    assert PrivacyService.can_add_to_group(user_a, user_b) is True

    # Restrict who_can_add_me_to_groups to NOBODY
    PrivacyService.update_settings(user_b, {"who_can_add_me_to_groups": PrivacyVisibility.NOBODY})
    assert PrivacyService.can_add_to_group(user_a, user_b) is False
