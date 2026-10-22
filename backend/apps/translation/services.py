"""
Service layer for Translation engine, caching, and fan-out dispatch.
Conforms strictly to Section 1, Section 4, Section 5, Section 13, Section 25, Section 26, Section 47, Section 48, and Section 52:
- Fan-out optimization (translates once per unique target language per conversation)
- Redis + Database hybrid caching
- Decoupled real-time WebSocket broadcasting (`translation.available`)
- Resilient failure and degraded mode handling
"""

import uuid

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError
from apps.common.exceptions import ValidationError as AppValidationError
from apps.conversations.models import ConversationMember
from apps.messaging.models import Message
from apps.realtime.services import RealtimeNotifier
from apps.translation.cache import TranslationCache
from apps.translation.models import MessageTranslation, TranslationFeedback, TranslationStatus
from apps.translation.providers.base import TranslationResult
from apps.translation.providers.registry import TranslationProviderRegistry


class TranslationService:
    """Core translation orchestrator managing target resolution, caching, and dispatch."""

    @staticmethod
    def determine_target_languages(message: Message) -> set[str]:
        """
        Determine unique set of target languages required by active conversation recipients.
        Optimizes multi-recipient fan-out by collapsing duplicate preferred languages.
        """
        # Fetch active members excluding sender
        active_members = (
            ConversationMember.objects.filter(
                conversation=message.conversation,
                left_at__isnull=True,
            )
            .exclude(user=message.sender)
            .select_related("user__preferred_chat_language")
        )

        source_lang = (message.detected_primary_language or "en").lower()
        is_romanized = getattr(message, "is_romanized", False)

        targets: set[str] = set()
        for member in active_members:
            pref = member.user.preferred_chat_language
            if not pref:
                continue
            pref_code = pref.code.lower()

            # If recipient prefers Hindi and message is Romanized Hindi (Hinglish),
            # they should receive the normalized Devanagari translation display
            if pref_code == source_lang and not is_romanized:
                continue

            targets.add(pref_code)

        return targets

    @classmethod
    def translate_message(
        cls,
        message_id: str | uuid.UUID,
        target_langs: list[str] | set[str] | None = None,
        provider_name: str | None = None,
    ) -> list[MessageTranslation]:
        """
        Translate a message to all required target languages.
        Uses Redis cache first; calls provider on cache miss; persists to MessageTranslation;
        broadcasts `translation.available` to the conversation room.
        """
        message = (
            Message.objects.select_related("conversation", "sender").filter(id=message_id).first()
        )
        if not message:
            raise NotFoundError(
                message="Message not found for translation.",
                code="MESSAGE_NOT_FOUND",
            )

        # Soft-deleted messages should not be translated
        if message.deleted_at:
            return []

        # Determine target languages if not explicitly supplied
        if target_langs is None:
            resolved_targets = cls.determine_target_languages(message)
        else:
            resolved_targets = set(target_langs)

        if not resolved_targets:
            return []

        source_lang = (message.detected_primary_language or "en").lower()
        provider = TranslationProviderRegistry.get(provider_name)
        persisted_translations: list[MessageTranslation] = []

        for target_lang in resolved_targets:
            target_lang_code = target_lang.lower()

            # 1. Check existing database record
            existing_db = MessageTranslation.objects.filter(
                message=message,
                target_language=target_lang_code,
            ).first()

            if existing_db and existing_db.status == TranslationStatus.COMPLETED:
                persisted_translations.append(existing_db)
                continue

            # 2. Check Redis cache
            cached_text = TranslationCache.get(source_lang, target_lang_code, message.original_text)

            if cached_text:
                translation_obj, _ = MessageTranslation.objects.update_or_create(
                    message=message,
                    target_language=target_lang_code,
                    defaults={
                        "source_language": source_lang,
                        "translated_text": cached_text,
                        "provider": f"{provider.name}_cache",
                        "status": TranslationStatus.COMPLETED,
                        "confidence": 1.0,
                        "error_message": None,
                    },
                )
                persisted_translations.append(translation_obj)
                continue

            # 3. Call translation engine provider
            try:
                result: TranslationResult = provider.translate(
                    text=message.original_text,
                    source_lang=source_lang,
                    target_lang=target_lang_code,
                )

                status_val = (
                    TranslationStatus.COMPLETED
                    if result.status == "COMPLETED"
                    else TranslationStatus.FAILED
                )

                translation_obj, _ = MessageTranslation.objects.update_or_create(
                    message=message,
                    target_language=target_lang_code,
                    defaults={
                        "source_language": source_lang,
                        "translated_text": result.translated_text,
                        "provider": result.provider,
                        "status": status_val,
                        "confidence": result.confidence,
                        "error_message": result.error_message,
                    },
                )

                # Store in Redis cache if successfully completed
                if status_val == TranslationStatus.COMPLETED and result.translated_text:
                    TranslationCache.set(
                        source_lang,
                        target_lang_code,
                        message.original_text,
                        result.translated_text,
                    )

                persisted_translations.append(translation_obj)
            except Exception as exc:
                # Never crash messaging on translation failure (Section 5, Section 48)
                failed_obj, _ = MessageTranslation.objects.update_or_create(
                    message=message,
                    target_language=target_lang_code,
                    defaults={
                        "source_language": source_lang,
                        "translated_text": "",
                        "provider": provider.name,
                        "status": TranslationStatus.FAILED,
                        "confidence": 0.0,
                        "error_message": str(exc),
                    },
                )
                persisted_translations.append(failed_obj)

        # 4. Broadcast real-time `translation.available` event to conversation group
        if persisted_translations:
            payload = {
                "conversation_id": str(message.conversation_id),
                "message_id": str(message.id),
                "translations": [
                    {
                        "id": str(t.id),
                        "source_language": t.source_language,
                        "target_language": t.target_language,
                        "translated_text": t.translated_text,
                        "provider": t.provider,
                        "status": t.status,
                        "confidence": t.confidence,
                        "error_message": t.error_message,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in persisted_translations
                ],
            }
            RealtimeNotifier.send_to_conversation(
                message.conversation_id,
                "translation.available",
                payload,
            )

        return persisted_translations

    @classmethod
    def direct_translate(
        cls,
        text: str,
        source_lang: str,
        target_lang: str,
        provider_name: str | None = None,
    ) -> TranslationResult:
        """
        Direct translation endpoint for ad-hoc translation queries.
        Leverages Redis cache and configured provider.
        """
        s_lang = source_lang.strip().lower()
        t_lang = target_lang.strip().lower()
        clean_text = text.strip()

        if not clean_text:
            return TranslationResult(
                translated_text="",
                source_language=s_lang,
                target_language=t_lang,
                provider="none",
                confidence=1.0,
            )

        # Check cache
        cached = TranslationCache.get(s_lang, t_lang, clean_text)
        if cached:
            return TranslationResult(
                translated_text=cached,
                source_language=s_lang,
                target_language=t_lang,
                provider="cache",
                confidence=1.0,
                is_cached=True,
                status="COMPLETED",
            )

        provider = TranslationProviderRegistry.get(provider_name)
        result = provider.translate(clean_text, s_lang, t_lang)

        if result.status == "COMPLETED" and result.translated_text:
            TranslationCache.set(s_lang, t_lang, clean_text, result.translated_text)

        return result

    @staticmethod
    def submit_feedback(
        translation_id: str | uuid.UUID,
        user: User,
        rating: int,
        comment: str | None = None,
    ) -> TranslationFeedback:
        """
        Submit user feedback (+1 / -1) for translation accuracy (Section 52).
        """
        if rating not in [1, -1]:
            raise AppValidationError(
                message="Rating must be +1 (accurate) or -1 (inaccurate).",
                code="INVALID_RATING",
                fields={"rating": ["Rating must be either 1 or -1."]},
            )

        translation = MessageTranslation.objects.filter(id=translation_id).first()
        if not translation:
            raise NotFoundError(
                message="Translation not found.",
                code="TRANSLATION_NOT_FOUND",
            )

        feedback, _ = TranslationFeedback.objects.update_or_create(
            translation=translation,
            user=user,
            defaults={
                "rating": rating,
                "comment": comment or "",
            },
        )
        return feedback

    @classmethod
    def retry_translation(
        cls,
        message_id: str | uuid.UUID,
        target_lang: str,
        provider_name: str | None = None,
    ) -> MessageTranslation:
        """Retry a failed or degraded translation."""
        translations = cls.translate_message(
            message_id=message_id,
            target_langs=[target_lang],
            provider_name=provider_name,
        )
        if not translations:
            raise NotFoundError(
                message="Translation could not be retried.",
                code="TRANSLATION_RETRY_FAILED",
            )
        return translations[0]
