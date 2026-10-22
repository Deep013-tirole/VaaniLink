"""
Service layer for messaging.
Guarantees:
- Idempotency via (sender, client_message_id)
- Monotonic sequence numbering per conversation
- Receipt generation per recipient
- Never alters original_text
- Dispatches delivery and seen lifecycle updates
"""

import uuid

from django.db import models, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, PermissionDeniedError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.models import Conversation, ConversationMember, ConversationType
from apps.messaging.models import Message, MessageReceipt
from apps.realtime.services import RealtimeNotifier


class MessageService:
    @staticmethod
    def send_message(
        conversation_id: uuid.UUID | str,
        sender: User,
        client_message_id: uuid.UUID | str,
        text: str,
        reply_to_id: uuid.UUID | str | None = None,
    ) -> Message:
        """
        Atomically persist an original message and create recipient receipts.
        If a message with (sender, client_message_id) already exists, returns it idempotently.
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            raise AppValidationError(
                message="Message text cannot be empty.",
                code="MESSAGE_TEXT_EMPTY",
                fields={"text": ["Message text cannot be empty."]},
            )

        if len(cleaned_text) > 5000:
            raise AppValidationError(
                message="Message text exceeds 5000 characters limit.",
                code="MESSAGE_TOO_LONG",
                fields={"text": ["Message exceeds 5000 characters limit."]},
            )

        # Idempotency check before lock
        existing_message = Message.objects.filter(
            sender=sender,
            client_message_id=client_message_id,
        ).first()
        if existing_message:
            return existing_message

        with transaction.atomic():
            try:
                conversation = Conversation.objects.select_for_update().get(id=conversation_id)
            except Conversation.DoesNotExist as exc:
                raise NotFoundError(
                    message="Conversation not found.",
                    code="CONVERSATION_NOT_FOUND",
                ) from exc

            # Verify membership
            is_member = ConversationMember.objects.filter(
                conversation=conversation,
                user=sender,
                left_at__isnull=True,
            ).exists()
            if not is_member:
                raise PermissionDeniedError(
                    message="You are not a member of this conversation.",
                    code="NOT_A_CONVERSATION_MEMBER",
                )

            # If DIRECT conversation, enforce direct message permissions and blocks
            if conversation.type == ConversationType.DIRECT:
                other_member = (
                    ConversationMember.objects.filter(conversation=conversation)
                    .exclude(user=sender)
                    .select_related("user")
                    .first()
                )
                if other_member:
                    from apps.privacy.services import PrivacyService

                    if not PrivacyService.can_send_direct_message(sender, other_member.user):
                        raise PermissionDeniedError(
                            message="Cannot send direct message to this recipient due to privacy or block restrictions.",
                            code="MESSAGE_SEND_RESTRICTED",
                        )

            # Re-check idempotency under lock
            existing_message = Message.objects.filter(
                sender=sender,
                client_message_id=client_message_id,
            ).first()
            if existing_message:
                return existing_message

            # Handle reply_to validation
            reply_to = None
            if reply_to_id:
                reply_to = Message.objects.filter(
                    id=reply_to_id,
                    conversation=conversation,
                ).first()
                if not reply_to:
                    raise NotFoundError(
                        message="Replied message was not found in this conversation.",
                        code="REPLIED_MESSAGE_NOT_FOUND",
                    )

            # Allocate monotonic sequence number safely under lock
            max_seq = (
                Message.objects.filter(conversation=conversation).aggregate(
                    m=models.Max("sequence_number")
                )["m"]
                or 0
            )
            sequence_number = max_seq + 1

            # Persist canonical Message record
            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                client_message_id=client_message_id,
                sequence_number=sequence_number,
                original_text=cleaned_text,
                reply_to_message=reply_to,
            )

            # Generate recipient receipt records for all other active members
            other_members = ConversationMember.objects.filter(
                conversation=conversation,
                left_at__isnull=True,
            ).exclude(user=sender)

            receipts = [
                MessageReceipt(
                    message=message,
                    user=member.user,
                )
                for member in other_members
            ]
            if receipts:
                MessageReceipt.objects.bulk_create(receipts)

            # Update conversation latest message timestamp
            conversation.last_message_at = message.created_at
            conversation.save(update_fields=["last_message_at", "updated_at"])

            # Broadcast real-time message.created event to conversation group
            from apps.messaging.api.serializers import MessageDetailSerializer

            serialized_msg = MessageDetailSerializer(message).data
            RealtimeNotifier.send_to_conversation(
                conversation.id,
                "message.created",
                serialized_msg,
            )

            # Trigger NLP intelligence pipeline asynchronously
            try:
                from apps.nlp.tasks import analyze_message_nlp

                analyze_message_nlp.delay(str(message.id))
            except Exception:
                try:
                    from apps.nlp.tasks import analyze_message_nlp

                    analyze_message_nlp(str(message.id))
                except Exception:
                    pass

            return message

    @staticmethod
    def edit_message(
        message_id: uuid.UUID | str,
        sender: User,
        new_text: str,
    ) -> Message:
        """
        Edit the original text of a message sent by the caller.
        Increments message version, updates edited_at, invalidates translations,
        re-triggers NLP intelligence pipeline, and broadcasts message.edited.
        """
        cleaned_text = new_text.strip()
        if not cleaned_text:
            raise AppValidationError(
                message="Message text cannot be empty.",
                code="MESSAGE_TEXT_EMPTY",
                fields={"text": ["Message text cannot be empty."]},
            )

        if len(cleaned_text) > 5000:
            raise AppValidationError(
                message="Message text exceeds 5000 characters limit.",
                code="MESSAGE_TOO_LONG",
                fields={"text": ["Message exceeds 5000 characters limit."]},
            )

        with transaction.atomic():
            message = Message.objects.select_for_update().filter(id=message_id).first()
            if not message:
                raise NotFoundError(
                    message="Message not found.",
                    code="MESSAGE_NOT_FOUND",
                )

            if message.sender_id != sender.id:
                raise PermissionDeniedError(
                    message="You can only edit your own messages.",
                    code="MESSAGE_EDIT_FORBIDDEN",
                )

            if message.is_deleted:
                raise AppValidationError(
                    message="Cannot edit a deleted message.",
                    code="CANNOT_EDIT_DELETED_MESSAGE",
                )

            message.original_text = cleaned_text
            message.version += 1
            message.edited_at = timezone.now()
            message.save(update_fields=["original_text", "version", "edited_at", "updated_at"])

            # Invalidate cached translations for this message
            try:
                from apps.translation.cache import TranslationCache

                TranslationCache.invalidate_message(message.id)
            except Exception:
                pass

            # Broadcast real-time message.edited event
            from apps.messaging.api.serializers import MessageDetailSerializer

            serialized_msg = MessageDetailSerializer(message).data
            RealtimeNotifier.send_to_conversation(
                message.conversation_id,
                "message.edited",
                serialized_msg,
            )

            # Re-trigger NLP intelligence pipeline asynchronously
            try:
                from apps.nlp.tasks import analyze_message_nlp

                analyze_message_nlp.delay(str(message.id))
            except Exception:
                try:
                    from apps.nlp.tasks import analyze_message_nlp

                    analyze_message_nlp(str(message.id))
                except Exception:
                    pass

            return message

    @staticmethod
    def delete_message(
        message_id: uuid.UUID | str,
        sender: User,
    ) -> Message:
        """
        Soft-delete a message for everyone if the caller is the message sender.
        Sets deleted_at, invalidates translations, and broadcasts message.deleted.
        """
        with transaction.atomic():
            message = Message.objects.select_for_update().filter(id=message_id).first()
            if not message:
                raise NotFoundError(
                    message="Message not found.",
                    code="MESSAGE_NOT_FOUND",
                )

            if message.sender_id != sender.id:
                raise PermissionDeniedError(
                    message="You can only delete your own messages.",
                    code="MESSAGE_DELETE_FORBIDDEN",
                )

            if not message.is_deleted:
                message.deleted_at = timezone.now()
                message.save(update_fields=["deleted_at", "updated_at"])

                # Invalidate cached translations for this message
                try:
                    from apps.translation.cache import TranslationCache

                    TranslationCache.invalidate_message(message.id)
                except Exception:
                    pass

                # Broadcast real-time message.deleted event
                RealtimeNotifier.send_to_conversation(
                    message.conversation_id,
                    "message.deleted",
                    {
                        "message_id": str(message.id),
                        "conversation_id": str(message.conversation_id),
                        "deleted_at": message.deleted_at.isoformat(),
                    },
                )

            return message

    @staticmethod
    def mark_messages_delivered(
        user: User,
        message_ids: list[uuid.UUID | str],
    ) -> list[dict]:
        """
        Mark message receipts as DELIVERED for the specified user.
        Dispatches real-time receipt.delivered notifications.
        """
        if not message_ids:
            return []

        now = timezone.now()
        receipts = list(
            MessageReceipt.objects.filter(
                user=user,
                message_id__in=message_ids,
                delivered_at__isnull=True,
            ).select_related("message")
        )

        if not receipts:
            return []

        updated = []
        conversation_ids = set()
        for r in receipts:
            r.delivered_at = now
            conversation_ids.add(r.message.conversation_id)
            updated.append(r)

        MessageReceipt.objects.bulk_update(updated, ["delivered_at"])

        # Broadcast real-time delivery update
        for conv_id in conversation_ids:
            conv_receipts = [r for r in updated if r.message.conversation_id == conv_id]
            for r in conv_receipts:
                RealtimeNotifier.send_to_conversation(
                    conv_id,
                    "receipt.delivered",
                    {
                        "conversation_id": str(conv_id),
                        "message_id": str(r.message_id),
                        "user_id": str(user.id),
                        "delivered_at": now.isoformat(),
                    },
                )

        return [
            {
                "message_id": str(r.message_id),
                "conversation_id": str(r.message.conversation_id),
                "delivered_at": now.isoformat(),
            }
            for r in updated
        ]

    @staticmethod
    def mark_messages_seen(
        user: User,
        conversation_id: uuid.UUID | str,
        up_to_message_id: uuid.UUID | str | None = None,
        message_ids: list[uuid.UUID | str] | None = None,
    ) -> list[dict]:
        """
        Mark message receipts as SEEN (and DELIVERED if not yet) for the specified user.
        Dispatches real-time receipt.seen notifications.
        """
        now = timezone.now()
        receipts_qs = MessageReceipt.objects.filter(
            user=user,
            message__conversation_id=conversation_id,
            seen_at__isnull=True,
        ).select_related("message")

        if up_to_message_id:
            target_msg = Message.objects.filter(
                id=up_to_message_id, conversation_id=conversation_id
            ).first()
            if target_msg:
                receipts_qs = receipts_qs.filter(
                    message__sequence_number__lte=target_msg.sequence_number
                )
        elif message_ids:
            receipts_qs = receipts_qs.filter(message_id__in=message_ids)

        receipts = list(receipts_qs)
        if not receipts:
            return []

        for r in receipts:
            r.seen_at = now
            if not r.delivered_at:
                r.delivered_at = now

        MessageReceipt.objects.bulk_update(receipts, ["seen_at", "delivered_at"])

        # Broadcast real-time seen update only if user has read receipts enabled (docs/PRIVACY.md)
        from apps.privacy.services import PrivacyService

        user_settings = PrivacyService.get_or_create_settings(user)
        if user_settings.read_receipts_enabled:
            RealtimeNotifier.send_to_conversation(
                conversation_id,
                "receipt.seen",
                {
                    "conversation_id": str(conversation_id),
                    "user_id": str(user.id),
                    "seen_up_to_id": str(up_to_message_id) if up_to_message_id else None,
                    "seen_message_ids": [str(r.message_id) for r in receipts],
                    "seen_at": now.isoformat(),
                },
            )

        return [
            {
                "message_id": str(r.message_id),
                "conversation_id": str(conversation_id),
                "seen_at": now.isoformat(),
            }
            for r in receipts
        ]

    @staticmethod
    def get_message_info(
        message_id: uuid.UUID | str,
        requester: User,
    ) -> dict:
        """
        Retrieve granular delivery and seen receipt breakdown for a message (Section 11, 12, 46).
        Accessible to active members of the conversation.
        """
        message = (
            Message.objects.select_related("conversation", "sender").filter(id=message_id).first()
        )
        if not message:
            raise NotFoundError(message="Message not found.", code="MESSAGE_NOT_FOUND")

        # Verify requester membership
        is_member = ConversationMember.objects.filter(
            conversation=message.conversation,
            user=requester,
            left_at__isnull=True,
        ).exists()
        if not is_member:
            raise PermissionDeniedError(
                message="You are not authorized to view message info.",
                code="NOT_A_CONVERSATION_MEMBER",
            )

        receipts = (
            MessageReceipt.objects.filter(message=message)
            .select_related("user")
            .order_by("created_at")
        )

        read_by = []
        delivered_to = []
        pending = []

        for r in receipts:
            user_data = {
                "id": str(r.user.id),
                "username": r.user.username,
                "display_name": r.user.display_name,
            }
            if r.seen_at:
                read_by.append(
                    {
                        "user": user_data,
                        "seen_at": r.seen_at.isoformat(),
                    }
                )
            elif r.delivered_at:
                delivered_to.append(
                    {
                        "user": user_data,
                        "delivered_at": r.delivered_at.isoformat(),
                    }
                )
            else:
                pending.append(
                    {
                        "user": user_data,
                    }
                )

        return {
            "message_id": str(message.id),
            "conversation_id": str(message.conversation.id),
            "original_text": message.original_text,
            "sequence_number": message.sequence_number,
            "created_at": message.created_at.isoformat(),
            "total_recipients": receipts.count(),
            "read_count": len(read_by),
            "delivered_count": len(delivered_to),
            "pending_count": len(pending),
            "read_by": read_by,
            "delivered_to": delivered_to,
            "pending": pending,
        }
