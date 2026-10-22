"""
Views for message endpoints and receipt acknowledgements.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.services import ConversationService
from apps.messaging.api.serializers import (
    ConversationSeenSerializer,
    MessageDeliveredSerializer,
    MessageEditSerializer,
    MessageSendSerializer,
    MessageSerializer,
)
from apps.messaging.models import Message
from apps.messaging.services import MessageService


class ConversationMessageListCreateView(APIView):
    """
    List messages and send messages in a conversation.
    GET /api/v1/conversations/{id}/messages/
    POST /api/v1/conversations/{id}/messages/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        conversation = ConversationService.get_conversation_for_user(id, request.user)

        # Pagination parameters
        limit = min(int(request.query_params.get("limit", 50)), 100)
        before_seq = request.query_params.get("before_seq")

        messages = (
            Message.objects.filter(conversation=conversation)
            .select_related("sender", "reply_to_message", "reply_to_message__sender")
            .prefetch_related("translations", "receipts")
        )

        if before_seq:
            try:
                messages = messages.filter(sequence_number__lt=int(before_seq))
            except ValueError:
                pass

        # Return latest messages ordered chronologically
        message_list = list(messages.order_by("-sequence_number")[:limit])
        message_list.reverse()

        serializer = MessageSerializer(message_list, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, id, *args, **kwargs):
        serializer = MessageSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = MessageService.send_message(
            conversation_id=id,
            sender=request.user,
            client_message_id=serializer.validated_data["client_message_id"],
            text=serializer.validated_data["text"],
            reply_to_id=serializer.validated_data.get("reply_to_id"),
        )

        response_serializer = MessageSerializer(message, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MessageDeliveredView(APIView):
    """
    Acknowledge delivery of messages to the authenticated user.
    POST /api/v1/messages/delivered/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = MessageDeliveredSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = MessageService.mark_messages_delivered(
            user=request.user,
            message_ids=serializer.validated_data["message_ids"],
        )
        return Response({"delivered": updated}, status=status.HTTP_200_OK)


class ConversationSeenView(APIView):
    """
    Acknowledge reading messages in a conversation.
    POST /api/v1/conversations/{id}/seen/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        # Verify caller is a member of the conversation
        ConversationService.get_conversation_for_user(id, request.user)

        serializer = ConversationSeenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = MessageService.mark_messages_seen(
            user=request.user,
            conversation_id=id,
            up_to_message_id=serializer.validated_data.get("up_to_message_id"),
            message_ids=serializer.validated_data.get("message_ids"),
        )
        return Response({"seen": updated}, status=status.HTTP_200_OK)


class MessageInfoView(APIView):
    """
    Retrieve granular delivery and read receipts for all conversation members.
    GET /api/v1/messages/{id}/info/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        info = MessageService.get_message_info(id, request.user)
        return Response(info, status=status.HTTP_200_OK)


class MessageDetailView(APIView):
    """
    Manage specific message (edit or soft-delete).
    PATCH /api/v1/messages/{id}/
    DELETE /api/v1/messages/{id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        serializer = MessageEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = MessageService.edit_message(
            message_id=id,
            sender=request.user,
            new_text=serializer.validated_data["text"],
        )
        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id, *args, **kwargs):
        message = MessageService.delete_message(
            message_id=id,
            sender=request.user,
        )
        return Response(
            {
                "message_id": str(message.id),
                "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
            },
            status=status.HTTP_200_OK,
        )
