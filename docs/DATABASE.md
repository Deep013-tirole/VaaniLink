# VaaniLink — Database Design & Schema Specification

## 1. Entities & Relationships Overview

The persistence schema is built in PostgreSQL with strict constraints, deterministic ordering, and foreign key indexes.

### Core Tables:
1. `languages_language`: Registry of supported languages and translation capability flags.
2. `accounts_user`: Custom user model with `preferred_chat_language` and `interface_language`.
3. `privacy_privacysetting`: Per-user privacy configurations (last seen, online, read receipts, DM rules).
4. `privacy_userblock`: Directional blocking records.
5. `conversations_conversation`: DIRECT (with unique `direct_key`) or GROUP chats.
6. `conversations_conversationmember`: Membership, group roles (`OWNER`, `ADMIN`, `MEMBER`), and read markers.
7. `conversations_conversationevent`: Immutable audit log of group events.
8. `messaging_message`: Canonical message records preserving `original_text`, sequence numbers, and client UUID.
9. `messaging_messagelanguagesegment`: Granular token/span level language annotations.
10. `translation_messagetranslation`: Cached translations per target language and source version.
11. `messaging_messagereceipt`: Per-recipient message lifecycle tracking (`DELIVERED`, `SEEN`).
12. `translation_translationfeedback`: User feedback for translation quality auditing.

---

## 2. Invariants & Constraints

- **Direct Conversation Uniqueness:**
  Deterministic `direct_key` formatted as `{min(user1_uuid, user2_uuid)}:{max(user1_uuid, user2_uuid)}`.
  Enforced by `UNIQUE(direct_key)`.
- **Message Idempotency:**
  `UNIQUE(sender_id, client_message_id)` prevents duplicates during network retry spikes.
- **Deterministic Sequencing:**
  `UNIQUE(conversation_id, sequence_number)` ensures consistent timeline ordering.
- **Translation Caching:**
  `UNIQUE(message_id, target_language)` ensures single translation generation per target language.
- **Receipt Tracking:**
  `UNIQUE(message_id, user_id)` guarantees one lifecycle record per recipient.

---

## 3. Indexing Strategy
- `messaging_message`: `(conversation_id, created_at)`, `(sender_id)`, `(reply_to_message_id)`
- `conversations_conversationmember`: `(user_id, conversation_id)`, `(conversation_id, user_id)`
- `translation_messagetranslation`: `(message_id, target_language)`, `(status)`
- `messaging_messagereceipt`: `(message_id, user_id)`, `(user_id, seen_at)`
- `privacy_userblock`: `(blocker_id, blocked_id)`
- `accounts_user`: `(username)`, `(email)`
