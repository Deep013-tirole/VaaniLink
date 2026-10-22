# VaaniLink — Translation Architecture & Engine Specification

## 1. Provider-Agnostic Translation Layer

The messaging system never interfaces directly with external or local translation engines. All translation requests flow through a unified service abstraction:

```
[Celery Background Task]
           │
           ▼
[TranslationService]
           │
           ▼
[TranslationRouter]
           │
  ┌────────┼────────┐
  ▼        ▼        ▼
[LocalML] [ExternalAPI] [HybridEngine]
```

---

## 2. Engine Interface (`TranslationEngine`)

Every translation engine implements a standard interface:

```python
class TranslationEngine(ABC):
    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[dict] = None
    ) -> TranslationResult:
        pass

    @abstractmethod
    def supports_pair(self, source_language: str, target_language: str) -> bool:
        pass
```

---

## 3. Translation Cache & Deduplication Rules

1. **Target-Language Centric Caching:**
   When a message is broadcast to a group of 50 members with:
   - 30 Hindi recipients
   - 15 English recipients
   - 5 Gujarati recipients
   The system generates at most **three** translation records:
   - `(message_id, "hi")`
   - `(message_id, "en")`
   - `(message_id, "gu")`
   No redundant translation queries are made for individual users sharing the same target language.

2. **Message Versioning & Invalidation:**
   - When a message is edited, its `version` increments (`version = 2`).
   - Prior translations are marked as `STALE`.
   - Re-translation is triggered asynchronously for the new version.
   - Clients reject any cached translation where `source_message_version != message.version`.

3. **Graceful Failure State:**
   - If a translation fails, `status = FAILED` is recorded.
   - The UI shows the original message text with a discreet badge: `"Translation unavailable"` and an optional retry action.
   - Chat transport is never interrupted.
