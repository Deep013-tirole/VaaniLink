/**
 * Global API Error Envelope interface matching Section 43 specification.
 */
export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}

/**
 * Supported Directionality for RTL / LTR layout switching.
 */
export type TextDirection = "ltr" | "rtl";

/**
 * Message Lifecycle Statuses.
 */
export type MessageStatus = "PENDING" | "SENT" | "DELIVERED" | "SEEN" | "FAILED";

/**
 * Language Registry Entity matching Section 6 & Section 45.
 */
export interface Language {
  code: string;
  name: string;
  native_name: string;
  script_code: string;
  is_rtl: boolean;
  is_active: boolean;
  translation_enabled: boolean;
  detection_enabled: boolean;
  transliteration_enabled: boolean;
  sort_order: number;
}

/**
 * User Entity matching Section 8 & Section 9.
 * Note: Profile photos are explicitly omitted; avatars are generated from initials.
 */
export interface User {
  id: string;
  username: string;
  display_name: string;
  email: string;
  interface_language: Language | null;
  preferred_chat_language: Language | null;
  is_active: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * JWT Authentication Tokens.
 */
export interface AuthTokens {
  access: string;
  refresh: string;
}

/**
 * Authentication Response from register or login.
 */
export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

/**
 * Public User profile for search and member lists (Section 38).
 */
export interface UserSearchResult {
  id: string;
  username: string;
  display_name: string;
}

/**
 * Conversation Types.
 */
export type ConversationType = "DIRECT" | "GROUP";

/**
 * Conversation Member Roles.
 */
export type MemberRole = "OWNER" | "ADMIN" | "MEMBER";

/**
 * Conversation Member entity matching backend ConversationMemberSerializer.
 */
export interface ConversationMember {
  id: string;
  user: UserSearchResult;
  role: MemberRole;
  joined_at: string;
}

/**
 * Message Reply Preview for nested quotes.
 */
export interface MessageReplyPreview {
  id: string;
  sender_name: string;
  text: string;
}

/**
 * Message Entity (Section 12 & 13).
 */
export interface Message {
  id: string;
  conversation_id: string;
  sender: UserSearchResult;
  client_message_id: string;
  sequence_number: number;
  text: string;
  original_text: string;
  status: MessageStatus;
  detected_primary_language?: string | null;
  detected_script?: string | null;
  is_mixed_language?: boolean;
  is_romanized?: boolean;
  language_confidence?: number | null;
  translations?: MessageTranslation[];
  reply_to_message_id: string | null;
  reply_to?: MessageReplyPreview | null;
  version: number;
  edited_at: string | null;
  deleted_at: string | null;
  created_at: string;
}

/**
 * Conversation Entity (Section 46).
 */
export interface Conversation {
  id: string;
  type: ConversationType;
  group_name: string | null;
  direct_user: UserSearchResult | null;
  latest_message: {
    id: string;
    sender_id: string;
    sender_username: string;
    text_preview: string;
    created_at: string;
    sequence_number: number;
  } | null;
  last_message_at: string | null;
  created_at: string;
}

/**
 * Detailed Conversation Entity with member hierarchy and roles.
 */
export interface ConversationDetail extends Conversation {
  direct_key?: string | null;
  members: ConversationMember[];
}

/**
 * Granular Message Info Receipts breakdown (Section 2, Section 11, Section 46).
 */
export interface MessageInfoRecipient {
  user: UserSearchResult;
  delivered_at?: string;
  seen_at?: string;
}

export interface MessageInfo {
  message_id: string;
  conversation_id: string;
  original_text: string;
  sequence_number: number;
  created_at: string;
  total_recipients: number;
  read_count: number;
  delivered_count: number;
  pending_count: number;
  read_by: Array<{ user: UserSearchResult; seen_at: string }>;
  delivered_to: Array<{ user: UserSearchResult; delivered_at: string }>;
  pending: Array<{ user: UserSearchResult }>;
}

/**
 * Group Management Payloads (Phase 7).
 */
export interface GroupConversationCreatePayload {
  group_name: string;
  member_ids?: string[];
}

export interface GroupRenamePayload {
  group_name: string;
}

export interface GroupAddMembersPayload {
  user_ids: string[];
}

export interface GroupMemberActionPayload {
  user_id: string;
}


/**
 * Realtime WebSocket Message Frame Envelope (docs/WEBSOCKET.md).
 */
export interface WebSocketFrame<T = Record<string, unknown>> {
  event: string;
  request_id?: string;
  data: T;
}

/**
 * Typing state payload.
 */
export interface TypingUser {
  conversation_id: string;
  user_id: string;
  username: string;
  display_name: string;
}

/**
 * User presence state.
 */
export interface UserPresence {
  user_id: string;
  is_online: boolean;
  last_seen_at: string | null;
}

/**
 * Message delivery acknowledgement payload.
 */
export interface ReceiptDeliveredEvent {
  conversation_id: string;
  message_id: string;
  user_id: string;
  delivered_at: string;
}

/**
 * Message read/seen acknowledgement payload.
 */
export interface ReceiptSeenEvent {
  conversation_id: string;
  user_id: string;
  seen_up_to_id: string | null;
  seen_message_ids: string[];
  seen_at: string;
}

/**
 * NLP Language Intelligence Analysis Result.
 */
export interface NLPTokenAnalysis {
  text: string;
  token_type: string;
  script: string | null;
  language: string | null;
  is_romanized: boolean;
}

export interface NLPAnalyzeResult {
  raw_text: string;
  cleaned_text: string;
  detected_primary_language: string;
  detected_script: string;
  is_mixed_language: boolean;
  is_romanized: boolean;
  language_confidence: number;
  detected_languages: Array<{
    language: string;
    script: string;
    confidence: number;
  }>;
  tokens: NLPTokenAnalysis[];
  protected_tokens_count: number;
  transliterated_text: string | null;
}

/**
 * Persisted Message Translation Entity (Phase 6).
 */
export interface MessageTranslation {
  id: string;
  message_id: string;
  source_language: string;
  target_language: string;
  translated_text: string;
  provider: string;
  status: "PENDING" | "COMPLETED" | "FAILED";
  confidence: number | null;
  error_message: string | null;
  created_at: string;
  updated_at?: string;
}

/**
 * User Translation Quality Feedback (Section 52).
 */
export interface TranslationFeedback {
  id: string;
  translation_id: string;
  user_id: string;
  rating: 1 | -1;
  comment: string | null;
  created_at: string;
}

/**
 * Direct text translation request and response structures.
 */
export interface DirectTranslatePayload {
  text: string;
  source_language?: string;
  target_language: string;
  provider?: string;
}

export interface DirectTranslateResult {
  translated_text: string;
  source_language: string;
  target_language: string;
  provider: string;
  confidence: number;
  is_cached: boolean;
  status: string;
  error_message: string | null;
}

/**
 * Realtime WebSocket event for new translations.
 */
export interface TranslationAvailableEvent {
  conversation_id: string;
  message_id: string;
  translations: MessageTranslation[];
}

/**
 * Privacy Policy Visibility Levels (Phase 8, docs/PRIVACY.md).
 */
export type PrivacyVisibility = "EVERYONE" | "CONTACTS_ONLY" | "NOBODY";

/**
 * User Privacy Configuration (Phase 8, docs/PRIVACY.md).
 */
export interface PrivacySetting {
  last_seen_visibility: PrivacyVisibility;
  online_status_visibility: PrivacyVisibility;
  read_receipts_enabled: boolean;
  who_can_message_me: PrivacyVisibility;
  who_can_add_me_to_groups: PrivacyVisibility;
  updated_at: string;
}

/**
 * Directional Blocked User record (Phase 8).
 */
export interface BlockedUser {
  id: string;
  user: UserSearchResult;
  blocked_at: string;
}

export type UpdatePrivacyPayload = Partial<Omit<PrivacySetting, "updated_at">>;

export interface BlockUserPayload {
  user_id?: string;
  username?: string;
}
