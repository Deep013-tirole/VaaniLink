# VaaniLink — REST API Specification

Base URL: `/api/v1/`

All API responses follow standard HTTP status codes. Errors adhere to a strict structured format.

---

## 1. Unified Error Envelope Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted payload is invalid.",
    "fields": {
      "username": [
        "This username is already in use."
      ]
    }
  }
}
```

---

## 2. Core Endpoints

### 2.1 System & Health
- `GET /api/v1/health/` — Health check status (database, redis, workers).

### 2.2 Authentication (`/api/v1/auth/`)
- `POST /api/v1/auth/register/` — Register new user account.
- `POST /api/v1/auth/login/` — Authenticate and receive access/refresh tokens.
- `POST /api/v1/auth/refresh/` — Rotate refresh token and issue new access token.
- `POST /api/v1/auth/logout/` — Blacklist/revoke current refresh token.
- `GET /api/v1/auth/me/` — Retrieve currently authenticated user profile.

### 2.3 Users (`/api/v1/users/`)
- `GET /api/v1/users/search/?q=` — Search users by username or display name (sanitized, non-sensitive).
- `PATCH /api/v1/users/me/` — Update display name, interface language, or preferred chat language.

### 2.4 Languages (`/api/v1/languages/`)
- `GET /api/v1/languages/` — List active supported languages and capability flags.

### 2.5 Conversations & Groups (`/api/v1/conversations/` & `/api/v1/groups/`)
- `GET /api/v1/conversations/` — Cursor-paginated conversation list with latest message preview.
- `POST /api/v1/conversations/direct/` — Retrieve or create direct conversation with target user.
- `POST /api/v1/groups/` — Create new group conversation.
- `GET /api/v1/groups/{id}/` — Get group metadata and member list.
- `PATCH /api/v1/groups/{id}/` — Rename group (Owner/Admin).
- `POST /api/v1/groups/{id}/members/` — Add members to group (Owner/Admin).
- `DELETE /api/v1/groups/{id}/members/{user_id}/` — Remove member (Owner/Admin).
- `PATCH /api/v1/groups/{id}/members/{user_id}/` — Update member role (Owner).
- `POST /api/v1/groups/{id}/leave/` — Leave group.

### 2.6 Messages (`/api/v1/conversations/{id}/messages/` & `/api/v1/messages/`)
- `GET /api/v1/conversations/{id}/messages/?cursor=` — Cursor-paginated message history.
- `POST /api/v1/conversations/{id}/messages/` — Fallback REST endpoint for message sending.
- `PATCH /api/v1/messages/{id}/` — Edit own message (increments message version).
- `DELETE /api/v1/messages/{id}/` — Soft-delete own message for everyone.
- `GET /api/v1/messages/{id}/info/` — Detailed acknowledgement info (`DELIVERED`, `SEEN` per user).
- `POST /api/v1/messages/{id}/translation/retry/` — Manually trigger translation retry.

### 2.7 Privacy & Blocking (`/api/v1/privacy/` & `/api/v1/blocks/`)
- `GET /api/v1/privacy/` — Get privacy settings.
- `PATCH /api/v1/privacy/` — Update privacy settings (last seen, online, read receipts, DM rules).
- `GET /api/v1/blocks/` — List blocked users.
- `POST /api/v1/blocks/` — Block user.
- `DELETE /api/v1/blocks/{user_id}/` — Unblock user.
