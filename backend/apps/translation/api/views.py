"""
API Views for Translation endpoints.
Conforms strictly to Section 43 error envelope and permissions.
"""

import uuid

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import NotFoundError, PermissionDeniedError
from apps.conversations.models import ConversationMember
from apps.messaging.models import Message
from apps.translation.api.serializers import (
    DirectTranslateRequestSerializer,
    DirectTranslateResponseSerializer,
    MessageTranslationSerializer,
    TranslationFeedbackInputSerializer,
    TranslationFeedbackSerializer,
)
from apps.translation.services import TranslationService


class MessageTranslationsView(APIView):
    """
    GET /api/v1/translations/message/{message_id}/
    List all translations for a given message in a conversation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, message_id: uuid.UUID) -> Response:
        message = Message.objects.select_related("conversation").filter(id=message_id).first()
        if not message:
            raise NotFoundError(
                message="Message not found.",
                code="MESSAGE_NOT_FOUND",
            )

        # Verify caller is a member of the message conversation
        is_member = ConversationMember.objects.filter(
            conversation=message.conversation,
            user=request.user,
            left_at__isnull=True,
        ).exists()
        if not is_member:
            raise PermissionDeniedError(
                message="You are not authorized to view translations for this message.",
                code="NOT_A_CONVERSATION_MEMBER",
            )

        translations = message.translations.all().order_by("created_at")
        serializer = MessageTranslationSerializer(translations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectTranslateView(APIView):
    """
    POST /api/v1/translations/translate/
    Directly translates input text for playground/sandbox or ad-hoc translation.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = DirectTranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = TranslationService.direct_translate(
            text=data["text"],
            source_lang=data.get("source_language", "en"),
            target_lang=data["target_language"],
            provider_name=data.get("provider") or None,
        )

        resp_serializer = DirectTranslateResponseSerializer(result.to_dict())
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class TranslationFeedbackView(APIView):
    """
    POST /api/v1/translations/{translation_id}/feedback/
    Submit quality feedback on a specific message translation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, translation_id: uuid.UUID) -> Response:
        serializer = TranslationFeedbackInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        feedback = TranslationService.submit_feedback(
            translation_id=translation_id,
            user=request.user,
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(
            TranslationFeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED,
        )


class RetryTranslationView(APIView):
    """
    POST /api/v1/translations/message/{message_id}/retry/
    Retry failed translation for a message and target language.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, message_id: uuid.UUID) -> Response:
        target_lang = request.data.get("target_language")
        if not target_lang:
            return Response(
                {
                    "error": {
                        "code": "TARGET_LANGUAGE_REQUIRED",
                        "message": "target_language is required.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = Message.objects.filter(id=message_id).first()
        if not message:
            raise NotFoundError(message="Message not found.", code="MESSAGE_NOT_FOUND")

        # Verify caller is a conversation member
        is_member = ConversationMember.objects.filter(
            conversation=message.conversation,
            user=request.user,
            left_at__isnull=True,
        ).exists()
        if not is_member:
            raise PermissionDeniedError(
                message="You are not authorized to retry translation for this message.",
                code="NOT_A_CONVERSATION_MEMBER",
            )

        translation = TranslationService.retry_translation(
            message_id=message_id,
            target_lang=target_lang,
        )
        return Response(
            MessageTranslationSerializer(translation).data,
            status=status.HTTP_200_OK,
        )
