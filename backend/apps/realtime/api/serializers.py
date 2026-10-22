"""
Serializers for Presence resources.
"""

from rest_framework import serializers


class UserPresenceSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    last_seen_at = serializers.DateTimeField(read_only=True, allow_null=True)


class BulkPresenceRequestSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        required=True,
    )
