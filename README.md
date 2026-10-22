# VaaniLink

> **"Write in your language. Read in your language."**

VaaniLink is a production-oriented, multilingual real-time text-chat platform where users communicate seamlessly across different languages, scripts, and dialects. 

Each participant selects their preferred chat language. Senders type naturally in their native language, script, or Romanized vernacular (such as Hinglish). VaaniLink preserves the original message as the immutable source of truth, detects its language and script structure, transliterates and translates where necessary, and delivers it to each recipient in their preferred language.

---

## Architecture & Core Tenets

```
                   ┌───────────────────────────────┐
                   │    React 19 + TypeScript      │
                   │ (Vite, CSS Modules, Lucide)   │
                   └──────────────┬────────────────┘
                                  │ (REST / WebSockets)
                                  ▼
                   ┌───────────────────────────────┐
                   │  Django 5 + Channels (Daphne) │
                   │  (SimpleJWT, DRF, Async ASGI) │
                   └───────┬──────────────┬────────┘
                           │              │
              ┌────────────┴──┐        ┌──┴─────────────┐
              ▼               ▼        ▼                ▼
       [ PostgreSQL 16 ]   [ Redis 7 Channel / Cache ]  [ Celery Workers ]
       (ACID Messaging)    (Presence & Pub/Sub)         (NLP & Translation)
```

1. **Original Message is the Immutable Source of Truth:** `original_text` is never overwritten. Translation is strictly a display layer.
2. **Domain Separation:** `Messaging != NLP != Translation != Privacy`. Messages are acknowledged and saved immediately; translation failure never drops or delays messaging delivery.
3. **Database-Driven Language Registry:** 37+ seeded world and Indic languages with individual capability flags (`translation_enabled`, `is_rtl`, `script_code`, `transliteration_enabled`).
4. **Code-Mixed & Romanized Intelligence:** Built-in modular NLP pipeline with Unicode NFKC normalization, script detection, Romanization detection, Hinglish code-mixed tagging, token protection (URLs, `@mentions`, `#hashtags`, emojis), and phonetic transliteration.
5. **Target-Language Fan-Out Optimization:** In group chats with $N$ members sharing $M$ distinct preferred languages, translation executes once per unique target language ($M \le N$), cached in Redis, and distributed across recipients.
6. **Deterministic Ordering & Idempotency:** Monotonic sequence numbers per conversation with database-level row locking and `(sender_id, client_message_id)` deduplication.
7. **Production Hardening:** Eliminates N+1 database queries on timelines ($O(1)$ constant query time via prefetching), enforces strict rate throttling, robust group role boundaries (OWNER, ADMIN, MEMBER), and Section 43 error format envelope.

---

## Feature Matrix

| Feature | Description |
|---|---|
| **Authentication** | Secure JWT authentication with automatic refresh token rotation and session management |
| **User Profile & Avatars** | Unique usernames, display names, initial-based dynamic avatars (no profile photos) |
| **Language Preferences** | Distinct Interface Language vs. Preferred Chat Language with searchable selector |
| **Direct & Group Chats** | Deterministic 1-on-1 conversations (`direct_key`) and group chats with OWNER, ADMIN, and MEMBER roles |
| **Real-Time Engine** | Bi-directional WebSockets (`/ws/chat/`) for live messaging, presence, and typing indicators |
| **Acknowledgement Lifecycle** | Real-time transitions: `PENDING` ➔ `SENT` ➔ `DELIVERED` ➔ `SEEN` |
| **Message Info** | Detailed per-member delivery and read timestamp breakdowns for group conversations |
| **Message Actions** | Quoted replies with smooth scroll, edit own messages with versioning, soft-delete for everyone with tombstones |
| **Rich Input** | Native 7-category Unicode emoji picker, Enter-to-send, and multi-line Shift+Enter |
| **Privacy & Blocking** | Online presence visibility, last-seen privacy, read receipt toggles, direct message permissions, and bidirectional blocking |
| **Internationalization & RTL** | Dynamic text direction (`dir="rtl"`) for Urdu, Arabic, Persian, Hebrew, and Sindhi |

---

## Quick Start with Docker Compose

Ensure Docker and Docker Compose are installed:

```bash
# 1. Clone repository
git clone https://github.com/your-username/vaanilink.git
cd vaanilink

# 2. Configure environment
cp .env.example .env

# 3. Build and launch all services
docker compose up --build -d

# 4. Access the application
# Frontend UI: http://localhost
# Backend API: http://localhost/api/
# API Health:  http://localhost/api/health/
```

To stop all services:
```bash
docker compose down
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+ (or 3.14)
- Node.js 20+ and npm
- PostgreSQL 16
- Redis 7

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt -r requirements-dev.txt

# Run migrations
python manage.py migrate

# Seed supported world languages
python manage.py seed_languages

# Run Daphne ASGI server
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

In a separate terminal, start the Celery worker:
```bash
cd backend
celery -A config worker --loglevel=info
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Vite dev server running at http://localhost:5173
```

---

## Running Automated Tests & Quality Checks

### Backend Test Suite (Pytest)
```bash
cd backend
python -m pytest
```
*180 comprehensive tests covering authentication, messaging, group governance, NLP pipelines, translation caching, privacy rules, query optimization, and WebSocket hardening.*

### Backend Linting & Formatting (Ruff)
```bash
cd backend
ruff check .
ruff format --check .
```

### Frontend Typechecking & Linting
```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

---

## Comprehensive Documentation

- [PRD & Core Concept](docs/PRD.md)
- [Architecture & Data Flow](docs/ARCHITECTURE.md)
- [API Specification](docs/API.md)
- [WebSocket Protocols & Events](docs/WEBSOCKET.md)
- [Database Schema & Integrity](docs/DATABASE.md)
- [NLP & Script Analysis Pipeline](docs/NLP_PIPELINE.md)
- [Translation Engine Architecture](docs/TRANSLATION.md)
- [Privacy & Security Framework](docs/SECURITY.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)
- [Local Development Guide](docs/DEVELOPMENT.md)

---

## License

MIT License. Designed and engineered for high-integrity multilingual communication.
