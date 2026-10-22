"""
Views for Conversation endpoints and Group Chat management.
Conforms strictly to Section 10, Section 11, Section 46, and Section 47.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.api.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    ConversationMemberSerializer,
    DirectConversationCreateSerializer,
    GroupAddMembersSerializer,
    GroupConversationCreateSerializer,
    GroupMemberActionSerializer,
    GroupRenameSerializer,
)
from apps.conversations.services import ConversationService


class ConversationListView(APIView):
    """
    List conversations for the current user.
    GET /api/v1/conversations/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        conversations = ConversationService.get_user_conversations(request.user)
        serializer = ConversationListSerializer(
            conversations, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectConversationCreateView(APIView):
    """
    Create or retrieve existing deterministic direct conversation with target user.
    POST /api/v1/conversations/direct/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DirectConversationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data["target_user"]

        conversation, created = ConversationService.get_or_create_direct_conversation(
            request.user,
            target_user,
        )

        detail_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationDetailView(APIView):
    """
    Retrieve single conversation metadata and members.
    GET /api/v1/conversations/{id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        conversation = ConversationService.get_conversation_for_user(id, request.user)
        serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------------------------------------------------------
# Phase 7: Group Chat Management Views
# -----------------------------------------------------------------------------


class GroupConversationCreateView(APIView):
    """
    Create a new group conversation.
    POST /api/v1/conversations/group/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GroupConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = ConversationService.create_group(
            creator=request.user,
            group_name=serializer.validated_data["group_name"],
            member_ids=serializer.validated_data.get("member_ids"),
        )
        detail_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class GroupRenameView(APIView):
    """
    Rename a group conversation. (Owner / Admin only)
    PATCH /api/v1/conversations/{id}/rename/
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        serializer = GroupRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = ConversationService.rename_group(
            conversation_id=id,
            requester=request.user,
            new_name=serializer.validated_data["group_name"],
        )
        detail_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_200_OK)


class GroupAddMembersView(APIView):
    """
    Add members to a group. (Owner / Admin only)
    POST /api/v1/conversations/{id}/members/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        serializer = GroupAddMembersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        members = ConversationService.add_members(
            conversation_id=id,
            requester=request.user,
            user_ids=serializer.validated_data["user_ids"],
        )
        return Response(
            ConversationMemberSerializer(members, many=True).data,
            status=status.HTTP_200_OK,
        )


class GroupRemoveMemberView(APIView):
    """
    Remove a member from a group.
    DELETE /api/v1/conversations/{id}/members/{user_id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id, user_id, *args, **kwargs):
        ConversationService.remove_member(
            conversation_id=id,
            requester=request.user,
            target_user_id=user_id,
        )
        return Response({"success": True}, status=status.HTTP_200_OK)


class GroupPromoteAdminView(APIView):
    """
    Promote a member to Admin. (Owner only)
    POST /api/v1/conversations/{id}/promote/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        serializer = GroupMemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ConversationService.promote_to_admin(
            conversation_id=id,
            requester=request.user,
            target_user_id=serializer.validated_data["user_id"],
        )
        return Response(ConversationMemberSerializer(member).data, status=status.HTTP_200_OK)


class GroupDemoteAdminView(APIView):
    """
    Demote an Admin to Member. (Owner only)
    POST /api/v1/conversations/{id}/demote/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        serializer = GroupMemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ConversationService.demote_from_admin(
            conversation_id=id,
            requester=request.user,
            target_user_id=serializer.validated_data["user_id"],
        )
        return Response(ConversationMemberSerializer(member).data, status=status.HTTP_200_OK)


class GroupTransferOwnershipView(APIView):
    """
    Transfer group ownership to another member. (Owner only)
    POST /api/v1/conversations/{id}/transfer-ownership/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        serializer = GroupMemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = ConversationService.transfer_ownership(
            conversation_id=id,
            requester=request.user,
            target_user_id=serializer.validated_data["user_id"],
        )
        detail_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_200_OK)


class GroupLeaveView(APIView):
    """
    Leave a group conversation.
    POST /api/v1/conversations/{id}/leave/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        ConversationService.leave_group(conversation_id=id, requester=request.user)
        return Response({"left": True}, status=status.HTTP_200_OK)
