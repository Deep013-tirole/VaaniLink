"""
ChatConsumer handling real-time WebSocket messaging, presence, receipts, and typing indicators.
Conforms strictly to Section 2, Section 5, Section 12, and docs/WEBSOCKET.md.
"""

import json
import uuid
from typing import Any

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from apps.common.exceptions import AppError
from apps.conversations.models import ConversationMember
from apps.messaging.services import MessageService
from apps.realtime.services import PresenceService


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Main WebSocket consumer mounted at `/ws/chat/`.
    """

    @classmethod
    async def encode_json(cls, content: Any) -> str:
        """Encode JSON payload using DjangoJSONEncoder to safely serialize UUIDs and datetimes."""
        return json.dumps(content, cls=DjangoJSONEncoder)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_group = None
        self.joined_conversations: set[str] = set()

    @database_sync_to_async
    def get_user_conversation_ids(self) -> list[str]:
        return [
            str(cid)
            for cid in ConversationMember.objects.filter(
                user=self.user,
                left_at__isnull=True,
            ).values_list("conversation_id", flat=True)
        ]

    @database_sync_to_async
    def is_conversation_member(self, conversation_id: uuid.UUID | str) -> bool:
        return ConversationMember.objects.filter(
            conversation_id=conversation_id,
            user=self.user,
            left_at__isnull=True,
        ).exists()

    @database_sync_to_async
    def check_presence_visibility(self, target_user_id: str) -> bool:
        from apps.accounts.models import User
        from apps.privacy.services import PrivacyService

        target = User.objects.filter(id=target_user_id).first()
        if not target:
            return False
        return PrivacyService.can_view_online_status(self.user, target)

    @database_sync_to_async
    def is_blocked_with(self, target_user_id: str) -> bool:
        from apps.accounts.models import User
        from apps.privacy.services import PrivacyService

        target = User.objects.filter(id=target_user_id).first()
        if not target:
            return False
        return PrivacyService.is_blocked_bidirectional(self.user, target)

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            # Reject unauthenticated connections with standard Close Code 4001
            await self.close(code=4001)
            return

        self.user = user
        self.user_group = f"user_{self.user.id}"

        await self.accept()

        # Join private personal notification group
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Auto-join all active conversations the user is a member of
        conv_ids = await self.get_user_conversation_ids()
        for conv_id in conv_ids:
            group_name = f"conversation_{conv_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.joined_conversations.add(conv_id)

        # Track presence
        is_first = await sync_to_async(PresenceService.add_user_connection)(self.user.id)
        if is_first:
            # Broadcast presence online to all user's conversation rooms
            presence_data = {
                "user_id": str(self.user.id),
                "is_online": True,
            }
            for conv_id in conv_ids:
                await self.channel_layer.group_send(
                    f"conversation_{conv_id}",
                    {
                        "type": "chat.presence_changed",
                        "data": presence_data,
                    },
                )

    async def disconnect(self, close_code):
        if self.user and self.user.is_authenticated:
            # Leave user group
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

            # Leave conversation groups
            for conv_id in self.joined_conversations:
                group_name = f"conversation_{conv_id}"
                await self.channel_layer.group_discard(group_name, self.channel_name)

            # Track presence update
            is_last = await sync_to_async(PresenceService.remove_user_connection)(self.user.id)
            if is_last:
                offline_data = {
                    "user_id": str(self.user.id),
                    "is_online": False,
                    "last_seen_at": timezone.now().isoformat(),
                }
                for conv_id in self.joined_conversations:
                    await self.channel_layer.group_send(
                        f"conversation_{conv_id}",
                        {
                            "type": "chat.presence_changed",
                            "data": offline_data,
                        },
                    )

    async def receive_json(self, content: dict[str, Any], **kwargs):
        event = content.get("event")
        request_id = content.get("request_id")
        data = content.get("data", {})

        if not event:
            await self.send_json(
                {
                    "event": "error",
                    "request_id": request_id,
                    "data": {
                        "code": "INVALID_FRAME",
                        "message": "Missing 'event' in frame envelope.",
                    },
                }
            )
            return

        # 1. Join Conversation Room
        if event == "conversation.join":
            conv_id = data.get("conversation_id")
            if not conv_id:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {
                            "code": "MISSING_CONVERSATION_ID",
                            "message": "conversation_id is required.",
                        },
                    }
                )
                return

            is_member = await self.is_conversation_member(conv_id)
            if not is_member:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {
                            "code": "NOT_A_CONVERSATION_MEMBER",
                            "message": "You are not a member of this conversation.",
                        },
                    }
                )
                return

            conv_id_str = str(conv_id)
            group_name = f"conversation_{conv_id_str}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.joined_conversations.add(conv_id_str)

            await self.send_json(
                {
                    "event": "conversation.joined",
                    "request_id": request_id,
                    "data": {"conversation_id": conv_id_str},
                }
            )

        # 2. Leave Conversation Room
        elif event == "conversation.leave":
            conv_id = data.get("conversation_id")
            if conv_id:
                conv_id_str = str(conv_id)
                group_name = f"conversation_{conv_id_str}"
                await self.channel_layer.group_discard(group_name, self.channel_name)
                self.joined_conversations.discard(conv_id_str)

        # 3. Send Message
        elif event == "message.send":
            conv_id = data.get("conversation_id")
            client_message_id = data.get("client_message_id")
            text = data.get("text", "")
            reply_to_id = data.get("reply_to_id")

            if not conv_id or not client_message_id:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {
                            "code": "INVALID_PAYLOAD",
                            "message": "Both conversation_id and client_message_id are required.",
                        },
                    }
                )
                return

            try:
                # MessageService atomically persists the message, assigns sequence,
                # creates receipts, and dispatches message.created to the conversation room.
                message = await sync_to_async(MessageService.send_message)(
                    conversation_id=conv_id,
                    sender=self.user,
                    client_message_id=client_message_id,
                    text=text,
                    reply_to_id=reply_to_id,
                )

                # Direct acknowledge to sender confirming persistence (SENT lifecycle)
                await self.send_json(
                    {
                        "event": "message.sent",
                        "request_id": request_id,
                        "data": {
                            "client_message_id": str(message.client_message_id),
                            "message_id": str(message.id),
                            "sequence_number": message.sequence_number,
                            "created_at": message.created_at.isoformat(),
                        },
                    }
                )
            except AppError as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": exc.code, "message": exc.message, "fields": exc.fields},
                    }
                )
            except Exception as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": "INTERNAL_ERROR", "message": str(exc)},
                    }
                )

        # 4. Message Delivered Acknowledgement
        elif event == "message.delivered":
            message_ids = data.get("message_ids", [])
            if message_ids:
                await sync_to_async(MessageService.mark_messages_delivered)(
                    user=self.user,
                    message_ids=message_ids,
                )

        # 5. Message Seen Acknowledgement
        elif event == "message.seen":
            conv_id = data.get("conversation_id")
            up_to_message_id = data.get("up_to_message_id")
            message_ids = data.get("message_ids")
            if conv_id:
                await sync_to_async(MessageService.mark_messages_seen)(
                    user=self.user,
                    conversation_id=conv_id,
                    up_to_message_id=up_to_message_id,
                    message_ids=message_ids,
                )

        # 6. Typing Started
        elif event == "typing.start":
            conv_id = data.get("conversation_id")
            if conv_id and str(conv_id) in self.joined_conversations:
                await self.channel_layer.group_send(
                    f"conversation_{conv_id}",
                    {
                        "type": "chat.typing_started",
                        "data": {
                            "conversation_id": str(conv_id),
                            "user_id": str(self.user.id),
                            "username": self.user.username,
                            "display_name": self.user.display_name,
                        },
                    },
                )

        # 7. Typing Stopped
        elif event == "typing.stop":
            conv_id = data.get("conversation_id")
            if conv_id and str(conv_id) in self.joined_conversations:
                await self.channel_layer.group_send(
                    f"conversation_{conv_id}",
                    {
                        "type": "chat.typing_stopped",
                        "data": {
                            "conversation_id": str(conv_id),
                            "user_id": str(self.user.id),
                        },
                    },
                )

        # 8. Edit Message
        elif event == "message.edit":
            msg_id = data.get("message_id")
            new_text = data.get("text", "")
            if not msg_id:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {
                            "code": "INVALID_PAYLOAD",
                            "message": "message_id is required.",
                        },
                    }
                )
                return
            try:
                edited = await sync_to_async(MessageService.edit_message)(
                    message_id=msg_id,
                    sender=self.user,
                    new_text=new_text,
                )
                await self.send_json(
                    {
                        "event": "message.edited_ack",
                        "request_id": request_id,
                        "data": {
                            "message_id": str(edited.id),
                            "version": edited.version,
                            "edited_at": edited.edited_at.isoformat() if edited.edited_at else None,
                        },
                    }
                )
            except AppError as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": exc.code, "message": exc.message, "fields": exc.fields},
                    }
                )
            except Exception as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": "INTERNAL_ERROR", "message": str(exc)},
                    }
                )

        # 9. Delete Message for Everyone
        elif event == "message.delete":
            msg_id = data.get("message_id")
            if not msg_id:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {
                            "code": "INVALID_PAYLOAD",
                            "message": "message_id is required.",
                        },
                    }
                )
                return
            try:
                deleted = await sync_to_async(MessageService.delete_message)(
                    message_id=msg_id,
                    sender=self.user,
                )
                await self.send_json(
                    {
                        "event": "message.deleted_ack",
                        "request_id": request_id,
                        "data": {
                            "message_id": str(deleted.id),
                            "deleted_at": deleted.deleted_at.isoformat()
                            if deleted.deleted_at
                            else None,
                        },
                    }
                )
            except AppError as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": exc.code, "message": exc.message, "fields": exc.fields},
                    }
                )
            except Exception as exc:
                await self.send_json(
                    {
                        "event": "error",
                        "request_id": request_id,
                        "data": {"code": "INTERNAL_ERROR", "message": str(exc)},
                    }
                )

    # -------------------------------------------------------------------------
    # Channel Layer Handlers (group_send dispatch)
    # -------------------------------------------------------------------------

    async def chat_event(self, event: dict[str, Any]):
        """General event pass-through handler."""
        await self.send_json(
            {
                "event": event["event"],
                "data": event["data"],
            }
        )

    async def chat_typing_started(self, event: dict[str, Any]):
        """Deliver typing.started to everyone in the room except the typing sender, respecting blocking."""
        sender_id = event["data"].get("user_id")
        if sender_id and sender_id != str(self.user.id):
            if not await self.is_blocked_with(sender_id):
                await self.send_json(
                    {
                        "event": "typing.started",
                        "data": event["data"],
                    }
                )

    async def chat_typing_stopped(self, event: dict[str, Any]):
        """Deliver typing.stopped to everyone in the room except the typing sender, respecting blocking."""
        sender_id = event["data"].get("user_id")
        if sender_id and sender_id != str(self.user.id):
            if not await self.is_blocked_with(sender_id):
                await self.send_json(
                    {
                        "event": "typing.stopped",
                        "data": event["data"],
                    }
                )

    async def chat_presence_changed(self, event: dict[str, Any]):
        """Deliver presence.changed to others in the room, respecting privacy settings."""
        target_uid = event["data"].get("user_id")
        if target_uid and target_uid != str(self.user.id):
            can_view = await self.check_presence_visibility(target_uid)
            if can_view:
                await self.send_json(
                    {
                        "event": "presence.changed",
                        "data": event["data"],
                    }
                )
