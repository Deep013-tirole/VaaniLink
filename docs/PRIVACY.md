# VaaniLink — Privacy Architecture Specification

## 1. Centralized Privacy Service
All privacy evaluations must occur in a dedicated `PrivacyService` rather than scattered conditional checks throughout views and WebSocket consumers.

```python
class PrivacyService:
    @staticmethod
    def can_view_online_status(viewer: User, target: User) -> bool: ...

    @staticmethod
    def can_view_last_seen(viewer: User, target: User) -> bool: ...

    @staticmethod
    def should_emit_read_receipt(recipient: User, sender: User) -> bool: ...

    @staticmethod
    def can_send_direct_message(sender: User, recipient: User) -> bool: ...

    @staticmethod
    def can_add_to_group(inviter: User, target: User) -> bool: ...
```

---

## 2. Privacy Settings Matrix

Users configure five discrete privacy controls with values:
- `EVERYONE`
- `CONTACTS_ONLY` ("People I Chat With" — users with whom an active direct chat exists)
- `NOBODY`

| Setting | Default | Behavior when restricted |
|---|---|---|
| `last_seen_visibility` | `CONTACTS_ONLY` | Hidden (`null`) for unauthorized viewers |
| `online_status_visibility` | `CONTACTS_ONLY` | Reported as offline to unauthorized viewers |
| `read_receipts_enabled` | `True` (Boolean) | If `False`, recipient sends `DELIVERED` but suppresses public `SEEN` |
| `who_can_message_me` | `EVERYONE` | Prevents unauthorized users from initiating direct messages |
| `who_can_add_me_to_groups` | `CONTACTS_ONLY` | Non-contacts cannot add user to new groups |

---

## 3. Blocking Architecture

When User A blocks User B:
1. User B cannot initiate a direct conversation with User A.
2. User B cannot send direct messages to User A.
3. User B cannot view User A's online status or last seen timestamp.
4. **Shared Group Isolation:** Blocking does **not** silently remove either user from pre-existing shared groups. Group messaging continues, but direct communication remains strictly blocked.
