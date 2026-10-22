import { apiClient } from "./client";
import {
  DirectTranslatePayload,
  DirectTranslateResult,
  MessageTranslation,
  TranslationFeedback,
} from "@/types";

/**
 * Fetch all translations for a given message in a conversation.
 */
export async function getMessageTranslations(
  messageId: string
): Promise<MessageTranslation[]> {
  return apiClient<MessageTranslation[]>(
    `/api/v1/translations/message/${messageId}/`
  );
}

/**
 * Directly translate arbitrary text via the Translation API.
 */
export async function translateDirect(
  payload: DirectTranslatePayload
): Promise<DirectTranslateResult> {
  return apiClient<DirectTranslateResult>("/api/v1/translations/translate/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Submit user feedback (+1 or -1) on a translation.
 */
export async function submitTranslationFeedback(
  translationId: string,
  rating: 1 | -1,
  comment?: string
): Promise<TranslationFeedback> {
  return apiClient<TranslationFeedback>(
    `/api/v1/translations/${translationId}/feedback/`,
    {
      method: "POST",
      body: JSON.stringify({ rating, comment }),
    }
  );
}

/**
 * Retry a failed or degraded message translation.
 */
export async function retryTranslation(
  messageId: string,
  targetLanguage: string
): Promise<MessageTranslation> {
  return apiClient<MessageTranslation>(
    `/api/v1/translations/message/${messageId}/retry/`,
    {
      method: "POST",
      body: JSON.stringify({ target_language: targetLanguage }),
    }
  );
}
