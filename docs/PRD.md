# VaaniLink — Product Requirements Document (PRD)

## 1. Vision & Concept
**"Write in your language. Read in your language."**

VaaniLink is a multilingual real-time text-chat platform enabling users across linguistic boundaries to communicate seamlessly. Every user configures a preferred chat language alongside an interface language. Messages sent in any language (or code-mixed / Romanized script) are analyzed, translated on demand for recipients with differing language preferences, and displayed with immediate access to the original untranslated text ("Show Original" / "Show Translation").

Translation is strictly a display layer; the original message is always the immutable source of truth.

---

## 2. Target Persona & Use Cases
- **Multilingual Teams & Groups:** Members collaborate in diverse native languages (Hindi, English, Gujarati, Bengali, Marathi, etc.) without copy-pasting into external translation tools.
- **Vernacular / Code-Mixed Communicators:** Communicators who naturally write Romanized sentences (e.g., Hinglish: "me kal office nahi aaunga") receive accurate detection and translation instead of being misclassified as English.
- **Global & Cross-Regional Chat:** Broad language registry supporting RTL (Arabic, Urdu, Persian) and major international languages with complete Unicode emoji fidelity.

---

## 3. Scope Boundaries

### In Scope (V1)
- Authentication: Secure registration, login, logout, token refresh, session revocation.
- Profile: Display name, unique username, generated initial-based avatars, interface language, preferred chat language.
- Languages: Database-driven dynamic language registry with capability flags (`is_active`, `translation_enabled`, `detection_enabled`, `is_rtl`, etc.).
- Messaging: 1-to-1 direct chats (deterministic `direct_key`), group conversations (OWNER, ADMIN, MEMBER roles).
- Realtime: Django Channels WebSockets, typing indicators, presence tracking (Redis backed), message delivery receipts (`PENDING` -> `SENT` -> `DELIVERED` -> `SEEN`), group Message Info receipt breakdown.
- NLP & Translation: Modular pipeline preserving protected tokens and emojis; romanized & code-mixed detection; engine-agnostic translation router; target-language translation caching; translation versioning tied to message edits.
- Privacy & Controls: Last seen, online status, read receipt toggling, direct message and group invite permissions, user blocking.
- UX & Accessibility: Responsive desktop & mobile layouts, RTL direction support, Unicode emoji picker, reply quoting, edit message, soft delete for everyone.

### Out of Scope (V1)
- Profile photos, image/video/voice messages, calls, media files.
- Stories, status broadcasts, channels, communities, payments, location sharing.
- Message reactions, native mobile apps.
- False E2EE claims (NLP and translation occur server-side; message text must be accessible to translation services).

---

## 4. Key Metrics & Acceptance Criteria
- **Zero Data Overwrite:** `original_text` must never be altered or replaced by translations.
- **Cache Efficiency:** Translations are generated exactly once per target language per message version, irrespective of recipient count.
- **Fail-Safe Messaging:** Core chat transport operates even when translation engines encounter rate limits or network failures.
- **Idempotency:** Reconnecting clients sending identical `(sender_id, client_message_id)` cause zero duplicate records.
