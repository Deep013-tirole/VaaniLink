# VaaniLink — Architecture Document

## 1. High-Level System Architecture

VaaniLink follows a decoupled, resilient architecture where messaging and translation are completely separated in execution.

```
+-------------------------------------------------------------+
|                      React + Vite SPA                       |
|           (TypeScript, CSS Modules, Modern Hooks)           |
+------------------------------+------------------------------+
                               |
            HTTP/REST (v1)     |     WebSockets (/ws/)
                               v
+-------------------------------------------------------------+
|                     ASGI Gateway (Daphne)                   |
+------------------------------+------------------------------+
                               |
         +---------------------+---------------------+
         |                                           |
         v                                           v
+-------------------------------+   +-------------------------------+
|    Django REST Framework      |   |    Django Channels Router     |
|   - Accounts, Languages       |   |   - Authenticated WS Consumer |
|   - Conversations, Messages   |   |   - Message/Receipt/Typing    |
|   - Privacy, Groups, Blocks   |   |   - Ephemeral Presence Events |
+---------------+---------------+   +---------------+---------------+
                |                                   |
                +-----------------+-----------------+
                                  |
                                  v
+-------------------------------------------------------------+
|                     Persistence Layer                       |
|  - PostgreSQL: Primary relational store (Source of Truth)   |
|  - Redis: Channels layer, presence state, ephemeral cache   |
+---------------------------------+---------------------------+
                                  |
                      Async Broker (Celery)
                                  v
+-------------------------------------------------------------+
|                     Background Workers                      |
|  - Modular NLP Pipeline (Detection, Segmentation)           |
|  - Translation Router (Local ML / External / Hybrid)        |
|  - Cache Persist & WebSocket Notification Broadcast         |
+-------------------------------------------------------------+
```

## 2. Core Architectural Principles
1. **Decoupled Domains:** `Messaging != NLP != Translation != Privacy`.
2. **Asynchronous Non-Blocking Translation:**
   - Message is saved -> `SENT` acknowledged -> Delivered to online recipients -> Dispatched to background queue for translation.
   - External translation delays never block immediate delivery of original text.
3. **Database As Source of Truth:** WebSockets are transport only; upon reconnection, clients sync state from PostgreSQL via cursor-based REST queries.
4. **Target Language Deduplication:** A group with 50 members sharing 3 target languages generates at most 3 translation records.

## 3. Technology Stack
- **Frontend:** React 19, TypeScript, Vite, CSS Modules.
- **Backend:** Python 3.14+, Django 5.x, Django REST Framework, Django Channels 4.x, ASGI (Daphne).
- **Database:** PostgreSQL.
- **Cache & Realtime:** Redis.
- **Worker / Queue:** Celery.
- **NLP / ML:** Python NLP pipeline with support for script detection, code-mixed classification, and transliteration normalization.
