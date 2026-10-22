"""
Views for Presence endpoints.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError
from apps.realtime.api.serializers import BulkPresenceRequestSerializer
from apps.realtime.services import PresenceService


class UserPresenceView(APIView):
    """
    Get presence status for a single user.
    GET /api/v1/presence/users/{id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        user = User.objects.filter(id=id, is_active=True).first()
        if not user:
            raise NotFoundError(message="User not found.", code="USER_NOT_FOUND")

        data = PresenceService.get_user_presence(id, viewer=request.user)
        return Response(data, status=status.HTTP_200_OK)


class BulkUserPresenceView(APIView):
    """
    Query presence status for multiple users.
    POST /api/v1/presence/users/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = BulkPresenceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data["user_ids"]
        statuses = PresenceService.get_multiple_users_presence(user_ids, viewer=request.user)
        return Response({"statuses": statuses}, status=status.HTTP_200_OK)
