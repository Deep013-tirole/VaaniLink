# VaaniLink — Realtime WebSocket Specification

Path: `/ws/chat/`

Authentication: JWT Access Token supplied via query parameter (`/ws/chat/?token=<access_token>`) or `Sec-WebSocket-Protocol` header. Authenticated via custom ASGI middleware.

---

## 1. Frame Envelope

All frames transmitted over WebSocket adhere to a standard JSON envelope:

```json
{
  "event": "message.send",
  "request_id": "8f90a9cf-938b-4b2a-a92c-0eec9a79fa45",
  "data": {}
}
```

- `event`: String identifying the message action.
- `request_id`: UUID for correlating client requests with server responses.
- `data`: Typed payload specific to the event.

---

## 2. Client-to-Server Events

| Event | Description | Payload Data |
|---|---|---|
| `conversation.join` | Join conversation room channel | `{ "conversation_id": "UUID" }` |
| `conversation.leave` | Leave conversation room channel | `{ "conversation_id": "UUID" }` |
| `message.send` | Send a new message | `{ "conversation_id": "UUID", "client_message_id": "UUID", "text": "...", "reply_to_id": "UUID" \| null }` |
| `message.delivered` | Acknowledge delivery of messages | `{ "message_ids": ["UUID"] }` |
| `message.seen` | Acknowledge reading messages up to ID | `{ "conversation_id": "UUID", "up_to_message_id": "UUID" }` |
| `typing.start` | Emit typing signal | `{ "conversation_id": "UUID" }` |
| `typing.stop` | Emit typing stopped signal | `{ "conversation_id": "UUID" }` |

---

## 3. Server-to-Client Events

| Event | Description | Payload Data |
|---|---|---|
| `message.sent` | Correlated response to `message.send` confirming persistence | `{ "client_message_id": "UUID", "message_id": "UUID", "sequence_number": 12, "created_at": "..." }` |
| `message.created` | Broadcast of newly sent message | Complete message object |
| `message.updated` | Broadcast when a message is edited | Updated message object with new version |
| `message.deleted` | Broadcast when a message is soft-deleted | `{ "message_id": "UUID", "deleted_at": "..." }` |
| `receipt.delivered` | Broadcast delivery update | `{ "message_id": "UUID", "user_id": "UUID", "delivered_at": "..." }` |
| `receipt.seen` | Broadcast read update | `{ "conversation_id": "UUID", "user_id": "UUID", "seen_up_to_id": "UUID", "seen_at": "..." }` |
| `translation.processing` | Notification that translation has queued | `{ "message_id": "UUID", "target_language": "hi" }` |
| `translation.ready` | Translation completed and cached | `{ "message_id": "UUID", "target_language": "hi", "translated_text": "...", "version": 1 }` |
| `translation.failed` | Translation failed (fallback to original) | `{ "message_id": "UUID", "target_language": "hi", "error": "UNAVAILABLE" }` |
| `typing.started` | User is typing in conversation | `{ "conversation_id": "UUID", "user_id": "UUID", "username": "..." }` |
| `typing.stopped` | User stopped typing in conversation | `{ "conversation_id": "UUID", "user_id": "UUID" }` |
| `presence.changed` | User online/offline state changed | `{ "user_id": "UUID", "is_online": true, "last_seen_at": "..." }` |
| `error` | Error responding to request | `{ "code": "...", "message": "..." }` |
