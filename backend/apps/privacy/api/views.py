"""
API Views for Privacy and Blocking endpoints.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError
from apps.privacy.api.serializers import (
    BlockedUserSerializer,
    BlockUserActionSerializer,
    PrivacySettingSerializer,
)
from apps.privacy.models import UserBlock
from apps.privacy.services import PrivacyService


class PrivacySettingView(APIView):
    """
    Get or update authenticated user's privacy settings.
    GET /api/v1/privacy/
    PATCH /api/v1/privacy/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        settings = PrivacyService.get_or_create_settings(request.user)
        serializer = PrivacySettingSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        settings = PrivacyService.get_or_create_settings(request.user)
        serializer = PrivacySettingSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = PrivacyService.update_settings(request.user, serializer.validated_data)
        return Response(PrivacySettingSerializer(updated).data, status=status.HTTP_200_OK)


class BlockedUserListCreateView(APIView):
    """
    List blocked users or block a new user.
    GET /api/v1/blocks/
    POST /api/v1/blocks/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        blocks = (
            UserBlock.objects.filter(blocker=request.user)
            .select_related("blocked")
            .order_by("-created_at")
        )
        serializer = BlockedUserSerializer(blocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = BlockUserActionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data["target_user"]

        block = PrivacyService.block_user(blocker=request.user, target_user=target_user)
        return Response(BlockedUserSerializer(block).data, status=status.HTTP_201_CREATED)


class BlockedUserDeleteView(APIView):
    """
    Unblock a previously blocked user.
    DELETE /api/v1/blocks/{user_id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, user_id, *args, **kwargs):
        target_user = User.objects.filter(id=user_id).first()
        if not target_user:
            raise NotFoundError(
                message="Target user does not exist.",
                code="USER_NOT_FOUND",
            )
        PrivacyService.unblock_user(blocker=request.user, target_user=target_user)
        return Response(
            {"detail": f"Unblocked {target_user.username} successfully."}, status=status.HTTP_200_OK
        )
