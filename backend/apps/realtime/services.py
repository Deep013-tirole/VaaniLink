"""
Presence and Realtime Notification services for VaaniLink.
Conforms strictly to Section 2, Section 5, and WEBSOCKET.md specifications.
"""

import uuid
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import User


class PresenceService:
    """
    Manages online/offline user presence tracking and last-seen updates.
    Resilient across RedisCache and in-memory test cache backends.
    """

    KEY_PREFIX = "presence:conns:"

    @classmethod
    def _conn_key(cls, user_id: uuid.UUID | str) -> str:
        return f"{cls.KEY_PREFIX}{user_id}"

    @classmethod
    def add_user_connection(cls, user_id: uuid.UUID | str) -> bool:
        """
        Register a newly opened WebSocket connection for a user.
        Returns True if the user transitioned from offline to online (first connection).
        """
        key = cls._conn_key(user_id)
        try:
            val = cache.get(key)
            if val is None or int(val) <= 0:
                cache.set(key, 1, timeout=86400)
                is_first = True
            else:
                cache.set(key, int(val) + 1, timeout=86400)
                is_first = False
        except Exception:
            is_first = True

        return is_first

    @classmethod
    def remove_user_connection(cls, user_id: uuid.UUID | str) -> bool:
        """
        Unregister a closed WebSocket connection.
        Returns True if the user transitioned from online to offline (no remaining connections).
        Updates `last_seen_at` on the User model when offline.
        """
        key = cls._conn_key(user_id)
        is_last = False
        try:
            val = cache.get(key)
            if val is None or int(val) <= 1:
                cache.delete(key)
                is_last = True
                User.objects.filter(id=user_id).update(last_seen_at=timezone.now())
            else:
                cache.set(key, int(val) - 1, timeout=86400)
                is_last = False
        except Exception:
            is_last = True
            User.objects.filter(id=user_id).update(last_seen_at=timezone.now())

        return is_last

    @classmethod
    def is_user_online(cls, user_id: uuid.UUID | str) -> bool:
        """Check whether a user has at least one active connection."""
        key = cls._conn_key(user_id)
        val = cache.get(key)
        return bool(val and int(val) > 0)

    @classmethod
    def get_user_presence(
        cls, user_id: uuid.UUID | str, viewer: User | None = None
    ) -> dict[str, Any]:
        """Return presence state dictionary for a single user, applying privacy masks if viewer is provided."""
        is_online = cls.is_user_online(user_id)
        user = User.objects.filter(id=user_id).only("id", "username", "last_seen_at").first()
        last_seen_at = user.last_seen_at.isoformat() if (user and user.last_seen_at) else None

        if viewer and user and str(viewer.id) != str(user.id):
            from apps.privacy.services import PrivacyService

            if not PrivacyService.can_view_online_status(viewer, user):
                is_online = False
            if not PrivacyService.can_view_last_seen(viewer, user):
                last_seen_at = None

        return {
            "user_id": str(user_id),
            "is_online": is_online,
            "last_seen_at": last_seen_at,
        }

    @classmethod
    def get_multiple_users_presence(
        cls, user_ids: list[uuid.UUID | str], viewer: User | None = None
    ) -> dict[str, dict[str, Any]]:
        """Return presence state dictionary for multiple users, applying privacy masks if viewer is provided."""
        users_map = {
            str(u.id): u
            for u in User.objects.filter(id__in=user_ids).only("id", "username", "last_seen_at")
        }
        result = {}
        for uid_raw in user_ids:
            uid = str(uid_raw)
            u = users_map.get(uid)
            is_online = cls.is_user_online(uid)
            last_seen_at = u.last_seen_at.isoformat() if (u and u.last_seen_at) else None

            if viewer and u and str(viewer.id) != str(u.id):
                from apps.privacy.services import PrivacyService

                if not PrivacyService.can_view_online_status(viewer, u):
                    is_online = False
                if not PrivacyService.can_view_last_seen(viewer, u):
                    last_seen_at = None

            result[uid] = {
                "user_id": uid,
                "is_online": is_online,
                "last_seen_at": last_seen_at,
            }
        return result


class RealtimeNotifier:
    """
    Dispatches events through the Django Channels channel layer.
    Can be invoked from REST views, Celery tasks, or WebSocket consumers.
    """

    @staticmethod
    def send_to_conversation(conversation_id: uuid.UUID | str, event: str, data: dict[str, Any]):
        """Broadcast an event to all members in a conversation room."""
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        group_name = f"conversation_{conversation_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat.event",
                "event": event,
                "data": data,
            },
        )

    @staticmethod
    def send_to_user(user_id: uuid.UUID | str, event: str, data: dict[str, Any]):
        """Dispatch a private event to a specific user's connected clients."""
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        group_name = f"user_{user_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "chat.event",
                "event": event,
                "data": data,
            },
        )
