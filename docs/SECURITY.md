# VaaniLink — Security Specification

## 1. Authentication & Token Management
- **Password Hashing:** Argon2 / PBKDF2 with SHA-256 via Django's secure authentication framework.
- **JWT Architecture:**
  - Access Token: Short-lived (15 minutes), passed in Authorization header or query param for WebSocket handshake.
  - Refresh Token: Long-lived (7 days), stored securely with rotation on each use and automatic blacklisting upon logout.
- **Session Revocation:** Revoking a refresh token blacklists all associated child tokens.

---

## 2. Authorization & Invariant Enforcement
- **Conversation Authorization:** All message reads, writes, and history fetches verify that `request.user` is an active member of `conversation.members`.
- **Group Role Enforcement:**
  - `OWNER`: Full administrative controls, role promotion/demotion, member removals, ownership transfer.
  - `ADMIN`: Member management, group renaming. Cannot modify Owner or other Admins.
  - `MEMBER`: Standard message sending, reading, and leaving group.
- **Message Mutation Authorization:** Only the original `sender` can edit or soft-delete a message.
- **WebSocket Guards:** Connections authenticate via JWT on connect; events are validated against permissions before hitting domain services.

---

## 3. Data Protection & Translation Privacy
- **No False E2EE Claims:** Server-side translation requires plaintext processing. Documentation and UX transparently declare that translations are processed by secure server-side workers.
- **Minimal Translation Payload:** The translation engine receives only `(text, source_lang, target_lang)`. It never receives user credentials, tokens, or profile identifiers.
- **Sanitized Logging:** Never log passwords, tokens, API keys, or raw message payloads in application logs.
