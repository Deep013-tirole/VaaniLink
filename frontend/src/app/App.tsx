import React, { useState, useEffect, useCallback, useRef } from "react";
import styles from "./App.module.css";
import {
  UserAvatar,
  LanguageSelector,
  UserSearch,
  ConversationList,
  MessageTimeline,
  MessageComposer,
  EmojiPicker,
} from "@/components";
import {
  Language,
  User,
  ApiErrorPayload,
  Conversation,
  ConversationDetail,
  MemberRole,
  Message,
  UserSearchResult,
  TypingUser,
  UserPresence,
  ReceiptDeliveredEvent,
  ReceiptSeenEvent,
  NLPAnalyzeResult,
  DirectTranslateResult,
  TranslationAvailableEvent,
  PrivacySetting,
  PrivacyVisibility,
  BlockedUser,
} from "@/types";
import {
  getLanguages,
  register,
  login,
  logout,
  updateMe,
  getConversations,
  createDirectConversation,
  createGroup,
  getConversationDetail,
  renameGroup,
  addGroupMembers,
  removeGroupMember,
  promoteAdmin,
  demoteAdmin,
  transferOwnership,
  leaveGroup,
  getMessages,
  sendMessage,
  editMessage,
  deleteMessage,
  getAccessToken,
  analyzeText,
  transliterateText,
  translateDirect,
  getPrivacySettings,
  updatePrivacySettings,
  getBlockedUsers,
  blockUser,
  unblockUser,
} from "@/api";
import { wsManager, ConnectionStatus } from "@/realtime";

// Presets for NLP testing
const NLP_PRESETS = [
  { label: "Hinglish + Emoji", text: "me kal nahi aaunga 😊" },
  { label: "Hinglish Question", text: "kal meeting hai kya?" },
  { label: "Code-Mixed (En + Hi)", text: "Bro kal meeting kitne baje hai?" },
  { label: "Pure English", text: "Are you coming tomorrow?" },
  { label: "Hindi (Devanagari)", text: "मैं कल नहीं आऊँगा। ❤️" },
  { label: "Gujarati", text: "હું કાલે નહીં આવીશ." },
  { label: "Arabic (RTL)", text: "مرحبا كيف حالك" },
  { label: "Protected Entities", text: "Ping team@vaanilink.com or https://vaanilink.org! 🚀" },
];

// Presets for Translation & Caching testing (Phase 6)
const TRANSLATION_PRESETS = [
  { label: "English: Are you coming tomorrow?", text: "Are you coming tomorrow?", src: "en", tgt: "hi" },
  { label: "Hinglish: me kal nahi aaunga 😊", text: "me kal nahi aaunga 😊", src: "hi", tgt: "en" },
  { label: "Hinglish: kal meeting hai kya?", text: "kal meeting hai kya?", src: "hi", tgt: "en" },
  { label: "Code-Mixed: Bro kal meeting kitne baje hai?", text: "Bro kal meeting kitne baje hai?", src: "hi", tgt: "en" },
  { label: "Hindi -> English: मैं कल नहीं आऊँगा। ❤️", text: "मैं कल नहीं आऊँगा। ❤️", src: "hi", tgt: "en" },
  { label: "English -> Gujarati: Are you coming tomorrow?", text: "Are you coming tomorrow?", src: "en", tgt: "gu" },
  { label: "English -> Urdu (RTL): Are you coming tomorrow?", text: "Are you coming tomorrow?", src: "en", tgt: "ur" },
];

// Fallback seed list for frontend demonstration before backend connection
const FALLBACK_LANGUAGES: Language[] = [
  { code: "en", name: "English", native_name: "English", script_code: "Latn", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: false, sort_order: 1 },
  { code: "hi", name: "Hindi", native_name: "हिन्दी", script_code: "Deva", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: true, sort_order: 2 },
  { code: "gu", name: "Gujarati", native_name: "ગુજરાતી", script_code: "Gujr", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: true, sort_order: 3 },
  { code: "mr", name: "Marathi", native_name: "मराठी", script_code: "Deva", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: true, sort_order: 4 },
  { code: "bn", name: "Bengali", native_name: "বাংলা", script_code: "Beng", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: true, sort_order: 5 },
  { code: "ur", name: "Urdu", native_name: "اردو", script_code: "Arab", is_rtl: true, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: true, sort_order: 8 },
  { code: "ar", name: "Arabic", native_name: "العربية", script_code: "Arab", is_rtl: true, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: false, sort_order: 25 },
  { code: "fa", name: "Persian", native_name: "فارسی", script_code: "Arab", is_rtl: true, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: false, sort_order: 26 },
  { code: "es", name: "Spanish", native_name: "Español", script_code: "Latn", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: false, sort_order: 20 },
  { code: "fr", name: "French", native_name: "Français", script_code: "Latn", is_rtl: false, is_active: true, translation_enabled: true, detection_enabled: true, transliteration_enabled: false, sort_order: 21 },
];

type TabType = "avatars" | "languages" | "auth" | "chat" | "groups" | "privacy" | "nlp" | "translation" | "chat_ux";

function getInitialRoute(): { tab: TabType; authMode: "login" | "register" } {
  if (typeof window === "undefined") {
    return { tab: "chat", authMode: "register" };
  }
  const clean = window.location.pathname.toLowerCase().replace(/\/+$/, "");
  switch (clean) {
    case "/login":
      return { tab: "auth", authMode: "login" };
    case "/register":
      return { tab: "auth", authMode: "register" };
    case "/auth":
      return { tab: "auth", authMode: "login" };
    case "/groups":
      return { tab: "groups", authMode: "register" };
    case "/privacy":
      return { tab: "privacy", authMode: "register" };
    case "/settings":
    case "/languages":
      return { tab: "languages", authMode: "register" };
    case "/nlp":
      return { tab: "nlp", authMode: "register" };
    case "/translation":
      return { tab: "translation", authMode: "register" };
    case "/chat_ux":
    case "/ux":
      return { tab: "chat_ux", authMode: "register" };
    case "/avatars":
      return { tab: "avatars", authMode: "register" };
    case "/chats":
    case "/chat":
    case "":
    case "/":
    default:
      return { tab: "chat", authMode: "register" };
  }
}

function getPathForTab(tab: TabType, mode: "login" | "register"): string {
  switch (tab) {
    case "chat":
      return "/chats";
    case "auth":
      return mode === "login" ? "/login" : "/register";
    case "groups":
      return "/groups";
    case "privacy":
      return "/privacy";
    case "languages":
      return "/settings";
    case "nlp":
      return "/nlp";
    case "translation":
      return "/translation";
    case "chat_ux":
      return "/chat_ux";
    case "avatars":
      return "/avatars";
    default:
      return "/chats";
  }
}

export const App: React.FC = () => {
  const initialRoute = useRef(getInitialRoute()).current;
  const [activeTab, setActiveTabState] = useState<TabType>(initialRoute.tab);
  const [authMode, setAuthModeState] = useState<"login" | "register">(initialRoute.authMode);

  const setActiveTab = useCallback((tab: TabType) => {
    setActiveTabState(tab);
    if (typeof window !== "undefined") {
      const targetPath = getPathForTab(tab, authMode);
      if (window.location.pathname !== targetPath) {
        window.history.pushState(null, "", targetPath);
      }
    }
  }, [authMode]);

  const setAuthMode = useCallback((mode: "login" | "register") => {
    setAuthModeState(mode);
    if (typeof window !== "undefined" && activeTab === "auth") {
      const targetPath = getPathForTab("auth", mode);
      if (window.location.pathname !== targetPath) {
        window.history.pushState(null, "", targetPath);
      }
    }
  }, [activeTab]);

  useEffect(() => {
    const handlePopState = () => {
      const route = getInitialRoute();
      setActiveTabState(route.tab);
      setAuthModeState(route.authMode);
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const [languages, setLanguages] = useState<Language[]>(FALLBACK_LANGUAGES);

  // Avatar demo state
  const [demoName, setDemoName] = useState("Deepak Tirole");

  // Language demo state
  const [interfaceLang, setInterfaceLang] = useState<string>("en");
  const [preferredChatLang, setPreferredChatLang] = useState<string>("hi");

  // NLP Intelligence state (Phase 5)
  const [nlpInput, setNlpInput] = useState<string>("me kal nahi aaunga 😊");
  const [nlpResult, setNlpResult] = useState<NLPAnalyzeResult | null>(null);
  const [nlpLoading, setNlpLoading] = useState<boolean>(false);
  const [nlpError, setNlpError] = useState<string | null>(null);

  const [transliterateInput, setTransliterateInput] = useState<string>("kal milte hai");
  const [transliterateResult, setTransliterateResult] = useState<string | null>(null);
  const [transliterateLoading, setTransliterateLoading] = useState<boolean>(false);

  // Translation Demo state (Phase 6)
  const [transInput, setTransInput] = useState<string>("Are you coming tomorrow?");
  const [transSourceLang, setTransSourceLang] = useState<string>("en");
  const [transTargetLang, setTransTargetLang] = useState<string>("hi");
  const [transResult, setTransResult] = useState<DirectTranslateResult | null>(null);
  const [transLoading, setTransLoading] = useState<boolean>(false);
  const [transError, setTransError] = useState<string | null>(null);

  // Multi-recipient Simulator state (Section 1, Section 13)
  const [simShowOriginal, setSimShowOriginal] = useState<Record<string, boolean>>({
    user_hi: false,
    user_gu: false,
    user_ur: false,
    user_es: false,
  });

  const toggleSimOriginal = (userKey: string) => {
    setSimShowOriginal((prev) => ({ ...prev, [userKey]: !prev[userKey] }));
  };

  const handleTranslateDirect = async (overrideText?: string, overrideSrc?: string, overrideTgt?: string) => {
    const text = overrideText !== undefined ? overrideText : transInput;
    const src = overrideSrc !== undefined ? overrideSrc : transSourceLang;
    const tgt = overrideTgt !== undefined ? overrideTgt : transTargetLang;

    if (!text.trim()) return;
    setTransLoading(true);
    setTransError(null);
    try {
      const res = await translateDirect({
        text,
        source_language: src,
        target_language: tgt,
      });
      setTransResult(res);
    } catch (err: unknown) {
      setTransError((err as Error)?.message || "Translation failed.");
    } finally {
      setTransLoading(false);
    }
  };

  const handleTransPresetClick = (p: { text: string; src: string; tgt: string }) => {
    setTransInput(p.text);
    setTransSourceLang(p.src);
    setTransTargetLang(p.tgt);
    handleTranslateDirect(p.text, p.src, p.tgt);
  };

  useEffect(() => {
    if (activeTab === "translation" && !transResult) {
      handleTranslateDirect("Are you coming tomorrow?", "en", "hi");
    }
  }, [activeTab]);

  // Auth demo state
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [username, setUsername] = useState("deepak_tirole");
  const [email, setEmail] = useState("deepak@example.com");
  const [displayName, setDisplayName] = useState("Deepak Tirole");
  const [password, setPassword] = useState("Password123!");
  const [authError, setAuthError] = useState<ApiErrorPayload | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Direct Chat & Realtime state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const selectedConversationRef = useRef<Conversation | null>(null);
  selectedConversationRef.current = selectedConversation;

  const [messages, setMessages] = useState<Message[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  // Phase 7: Group Chat & Roles state
  const [showCreateGroupModal, setShowCreateGroupModal] = useState<boolean>(false);
  const [newGroupName, setNewGroupName] = useState<string>("");
  const [selectedGroupMembers, setSelectedGroupMembers] = useState<UserSearchResult[]>([]);
  const [isCreatingGroup, setIsCreatingGroup] = useState<boolean>(false);
  const [createGroupError, setCreateGroupError] = useState<string | null>(null);

  const [showGroupInfoModal, setShowGroupInfoModal] = useState<boolean>(false);
  const [detailedConversation, setDetailedConversation] = useState<ConversationDetail | null>(null);
  const [isLoadingGroupDetail, setIsLoadingGroupDetail] = useState<boolean>(false);
  const [groupActionError, setGroupActionError] = useState<string | null>(null);
  const [renameInput, setRenameInput] = useState<string>("");

  // Phase 8: Privacy & Blocking state
  const [privacySettings, setPrivacySettings] = useState<PrivacySetting | null>(null);
  const [isLoadingPrivacy, setIsLoadingPrivacy] = useState<boolean>(false);
  const [privacySuccess, setPrivacySuccess] = useState<string | null>(null);
  const [privacyError, setPrivacyError] = useState<string | null>(null);

  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [isLoadingBlocks, setIsLoadingBlocks] = useState<boolean>(false);
  const [blockActionError, setBlockActionError] = useState<string | null>(null);

  // Realtime WebSocket & Presence state (Phase 4)
  const [wsStatus, setWsStatus] = useState<ConnectionStatus>("DISCONNECTED");
  const [presenceMap, setPresenceMap] = useState<Record<string, UserPresence>>({});
  const [typingMap, setTypingMap] = useState<Record<string, TypingUser[]>>({});

  // Phase 9: Chat UX state (Replies, Edits, Deletes, Mobile layout)
  const [replyingTo, setReplyingTo] = useState<{ id: string; senderName: string; text: string } | null>(null);
  const [editingMessage, setEditingMessage] = useState<{ id: string; text: string } | null>(null);
  const [showMobileChatView, setShowMobileChatView] = useState<boolean>(false);

  // Phase 9: Interactive UX Showcase sandbox state
  const [uxEmojiSandbox, setUxEmojiSandbox] = useState<string>("Hello VaaniLink! ✨ Feel free to test emojis.");
  const [showUxEmojiPicker, setShowUxEmojiPicker] = useState<boolean>(false);
  const [uxDemoMessages, setUxDemoMessages] = useState<Message[]>([
    {
      id: "demo-1",
      conversation_id: "demo-conv",
      sender: { id: "u1", username: "priya_sharma", display_name: "Priya Sharma" },
      client_message_id: "client-1",
      sequence_number: 1,
      text: "Are you coming to the team lunch tomorrow?",
      original_text: "Are you coming to the team lunch tomorrow?",
      status: "SEEN",
      detected_primary_language: "en",
      detected_script: "Latn",
      reply_to_message_id: null,
      version: 1,
      edited_at: null,
      deleted_at: null,
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "demo-2",
      conversation_id: "demo-conv",
      sender: { id: "u2", username: "deepak_tirole", display_name: "Deepak Tirole" },
      client_message_id: "client-2",
      sequence_number: 2,
      text: "Haan bilkul, main 1 baje pahunchunga! 🎉",
      original_text: "Haan bilkul, main 1 baje pahunchunga! 🎉",
      status: "SEEN",
      detected_primary_language: "hi",
      detected_script: "Latn",
      is_romanized: true,
      is_mixed_language: true,
      reply_to_message_id: "demo-1",
      reply_to: {
        id: "demo-1",
        sender_name: "Priya Sharma",
        text: "Are you coming to the team lunch tomorrow?",
      },
      version: 2,
      edited_at: new Date(Date.now() - 1800000).toISOString(),
      deleted_at: null,
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: "demo-3",
      conversation_id: "demo-conv",
      sender: { id: "u3", username: "tariq_ahmad", display_name: "Tariq Ahmad" },
      client_message_id: "client-3",
      sequence_number: 3,
      text: "ان شاء اللہ، میں بھی وقت پر آؤں گا۔",
      original_text: "ان شاء اللہ، میں بھی وقت پر آؤں گا۔",
      status: "DELIVERED",
      detected_primary_language: "ur",
      detected_script: "Arab",
      reply_to_message_id: null,
      version: 1,
      edited_at: null,
      deleted_at: null,
      created_at: new Date(Date.now() - 900000).toISOString(),
    },
    {
      id: "demo-4",
      conversation_id: "demo-conv",
      sender: { id: "u2", username: "deepak_tirole", display_name: "Deepak Tirole" },
      client_message_id: "client-4",
      sequence_number: 4,
      text: "This message was deleted.",
      original_text: "Old message that was deleted",
      status: "SEEN",
      reply_to_message_id: null,
      version: 1,
      edited_at: null,
      deleted_at: new Date(Date.now() - 300000).toISOString(),
      created_at: new Date(Date.now() - 400000).toISOString(),
    },
  ]);

  // Track WS status
  useEffect(() => {
    return wsManager.onStatusChange((status) => {
      setWsStatus(status);
    });
  }, []);

  // Connect WebSocket when currentUser is set
  useEffect(() => {
    const token = getAccessToken();
    if (currentUser && token) {
      wsManager.connect(token);
    } else {
      wsManager.disconnect();
    }
  }, [currentUser]);

  // Load languages from backend on mount
  useEffect(() => {
    getLanguages()
      .then((data) => {
        if (data && data.length > 0) {
          setLanguages(data);
        }
      })
      .catch(() => {
        // Fallback to static seed data if backend is offline
      });
  }, []);

  // Fetch conversations whenever currentUser changes or user opens Chat tab
  const refreshConversations = useCallback(async () => {
    if (!currentUser) return;
    setIsLoadingConversations(true);
    setChatError(null);
    try {
      const convList = await getConversations();
      setConversations(convList);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || "Failed to load conversations");
    } finally {
      setIsLoadingConversations(false);
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser && activeTab === "chat") {
      refreshConversations();
    }
  }, [currentUser, activeTab, refreshConversations]);

  // Register Realtime WebSocket event listeners
  useEffect(() => {
    if (!currentUser) return;

    // 1. New message arrived via WebSocket broadcast
    const unbindMessageCreated = wsManager.on("message.created", (data) => {
      const newMsg = data as Message;

      // Update conversations list latest_message
      setConversations((prev) => {
        const found = prev.find((c) => c.id === newMsg.conversation_id);
        const updatedItem: Conversation = found
          ? {
              ...found,
              last_message_at: newMsg.created_at,
              latest_message: {
                id: newMsg.id,
                sender_id: newMsg.sender.id,
                sender_username: newMsg.sender.username,
                text_preview: newMsg.original_text.slice(0, 50),
                created_at: newMsg.created_at,
                sequence_number: newMsg.sequence_number,
              },
            }
          : {
              id: newMsg.conversation_id,
              type: "DIRECT",
              group_name: null,
              direct_user: newMsg.sender,
              latest_message: {
                id: newMsg.id,
                sender_id: newMsg.sender.id,
                sender_username: newMsg.sender.username,
                text_preview: newMsg.original_text.slice(0, 50),
                created_at: newMsg.created_at,
                sequence_number: newMsg.sequence_number,
              },
              last_message_at: newMsg.created_at,
              created_at: newMsg.created_at,
            };

        return [updatedItem, ...prev.filter((c) => c.id !== newMsg.conversation_id)];
      });

      // If message is in currently active conversation view
      if (selectedConversationRef.current?.id === newMsg.conversation_id) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id || m.client_message_id === newMsg.client_message_id)) {
            return prev;
          }
          return [...prev, newMsg];
        });

        // Acknowledge read if recipient is viewer
        if (newMsg.sender.id !== currentUser.id) {
          wsManager.sendDelivered([newMsg.id]);
          wsManager.sendSeen(newMsg.conversation_id, newMsg.id);
        }
      } else if (newMsg.sender.id !== currentUser.id) {
        // Acknowledge delivery even if not actively open
        wsManager.sendDelivered([newMsg.id]);
      }
    });

    // 2. Delivery Receipt arrived
    const unbindReceiptDelivered = wsManager.on("receipt.delivered", (data) => {
      const payload = data as ReceiptDeliveredEvent;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === payload.message_id && m.status === "SENT"
            ? { ...m, status: "DELIVERED" }
            : m
        )
      );
    });

    // 3. Seen Receipt arrived
    const unbindReceiptSeen = wsManager.on("receipt.seen", (data) => {
      const payload = data as ReceiptSeenEvent;
      setMessages((prev) =>
        prev.map((m) => {
          if (payload.seen_message_ids && payload.seen_message_ids.includes(m.id)) {
            return { ...m, status: "SEEN" };
          }
          return m;
        })
      );
    });

    // 4. Typing Started
    const unbindTypingStarted = wsManager.on("typing.started", (data) => {
      const payload = data as TypingUser;
      setTypingMap((prev) => {
        const currentList = prev[payload.conversation_id] || [];
        if (currentList.some((u) => u.user_id === payload.user_id)) {
          return prev;
        }
        return {
          ...prev,
          [payload.conversation_id]: [...currentList, payload],
        };
      });
    });

    // 5. Typing Stopped
    const unbindTypingStopped = wsManager.on("typing.stopped", (data) => {
      const payload = data as { conversation_id: string; user_id: string };
      setTypingMap((prev) => {
        const currentList = prev[payload.conversation_id] || [];
        return {
          ...prev,
          [payload.conversation_id]: currentList.filter((u) => u.user_id !== payload.user_id),
        };
      });
    });

    // 6. Presence Changed
    const unbindPresenceChanged = wsManager.on("presence.changed", (data) => {
      const payload = data as UserPresence;
      setPresenceMap((prev) => ({
        ...prev,
        [payload.user_id]: payload,
      }));
    });

    // 7. Message Updated (NLP detection arrived)
    const unbindMessageUpdated = wsManager.on("message.updated", (data) => {
      const payload = data as Message;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === payload.id
            ? {
                ...m,
                ...payload,
              }
            : m
        )
      );
    });

    // 8. Translation Available (Phase 6)
    const unbindTranslationAvailable = wsManager.on("translation.available", (data) => {
      const payload = data as TranslationAvailableEvent;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === payload.message_id
            ? {
                ...m,
                translations: payload.translations,
              }
            : m
        )
      );
    });

    // 9. Message Edited (Phase 9)
    const unbindMessageEdited = wsManager.on("message.edited", (data) => {
      const payload = data as Message;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === payload.id
            ? {
                ...m,
                ...payload,
                translations: payload.translations || [],
              }
            : m
        )
      );
    });

    // 10. Message Deleted (Phase 9)
    const unbindMessageDeleted = wsManager.on("message.deleted", (data) => {
      const payload = data as { message_id: string; conversation_id: string; deleted_at: string };
      setMessages((prev) =>
        prev.map((m) =>
          m.id === payload.message_id
            ? {
                ...m,
                text: "This message was deleted.",
                deleted_at: payload.deleted_at,
                translations: [],
              }
            : m
        )
      );
    });

    return () => {
      unbindMessageCreated();
      unbindReceiptDelivered();
      unbindReceiptSeen();
      unbindTypingStarted();
      unbindTypingStopped();
      unbindPresenceChanged();
      unbindMessageUpdated();
      unbindTranslationAvailable();
      unbindMessageEdited();
      unbindMessageDeleted();
    };
  }, [currentUser]);

  const loadMessagesForConversation = async (convId: string) => {
    setIsLoadingMessages(true);
    setChatError(null);
    try {
      const msgs = await getMessages(convId);
      setMessages(msgs);

      // Acknowledge read up to latest message for any unread incoming messages
      if (currentUser && msgs.length > 0) {
        const latestMsg = msgs[msgs.length - 1];
        if (latestMsg.sender.id !== currentUser.id) {
          wsManager.sendSeen(convId, latestMsg.id);
        }
      }
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || "Failed to load messages");
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const handleSelectConversation = (conv: Conversation) => {
    if (selectedConversation?.id) {
      wsManager.leaveConversation(selectedConversation.id);
    }
    setReplyingTo(null);
    setEditingMessage(null);
    setShowMobileChatView(true);
    setSelectedConversation(conv);
    wsManager.joinConversation(conv.id);
    loadMessagesForConversation(conv.id);
  };

  const handleSelectUserFromSearch = async (targetUser: UserSearchResult) => {
    setChatError(null);
    try {
      const conv = await createDirectConversation({ user_id: targetUser.id });
      setConversations((prev) => {
        const exists = prev.some((c) => c.id === conv.id);
        return exists ? prev : [conv, ...prev];
      });
      setReplyingTo(null);
      setEditingMessage(null);
      setShowMobileChatView(true);
      setSelectedConversation(conv);
      wsManager.joinConversation(conv.id);
      loadMessagesForConversation(conv.id);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || "Failed to initiate direct conversation");
    }
  };

  // Phase 7 Group Handlers
  const handleOpenCreateGroup = () => {
    setNewGroupName("");
    setSelectedGroupMembers([]);
    setCreateGroupError(null);
    setShowCreateGroupModal(true);
  };

  const handleToggleMemberSelection = (targetUser: UserSearchResult) => {
    setSelectedGroupMembers((prev) => {
      const exists = prev.some((u) => u.id === targetUser.id);
      if (exists) {
        return prev.filter((u) => u.id !== targetUser.id);
      }
      return [...prev, targetUser];
    });
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) {
      setCreateGroupError("Group name is required.");
      return;
    }
    setIsCreatingGroup(true);
    setCreateGroupError(null);
    try {
      const newGroup = await createGroup({
        group_name: newGroupName.trim(),
        member_ids: selectedGroupMembers.map((u) => u.id),
      });
      setConversations((prev) => [newGroup, ...prev]);
      handleSelectConversation(newGroup);
      setShowCreateGroupModal(false);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setCreateGroupError(apiErr.error?.message || "Failed to create group.");
    } finally {
      setIsCreatingGroup(false);
    }
  };

  const handleOpenGroupInfo = async () => {
    if (!selectedConversation || selectedConversation.type !== "GROUP") return;
    setIsLoadingGroupDetail(true);
    setGroupActionError(null);
    setShowGroupInfoModal(true);
    try {
      const detail = await getConversationDetail(selectedConversation.id);
      setDetailedConversation(detail);
      setRenameInput(detail.group_name || "");
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to load group details.");
    } finally {
      setIsLoadingGroupDetail(false);
    }
  };

  const handleRenameGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConversation || !renameInput.trim()) return;
    setGroupActionError(null);
    try {
      const updated = await renameGroup(selectedConversation.id, {
        group_name: renameInput.trim(),
      });
      setDetailedConversation(updated);
      setConversations((prev) =>
        prev.map((c) => (c.id === updated.id ? { ...c, group_name: updated.group_name } : c))
      );
      setSelectedConversation((prev) =>
        prev ? { ...prev, group_name: updated.group_name } : null
      );
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to rename group.");
    }
  };

  const handleAddMemberToGroup = async (targetUser: UserSearchResult) => {
    if (!selectedConversation) return;
    if (detailedConversation?.members.some((m) => m.user.id === targetUser.id)) {
      setGroupActionError(`${targetUser.display_name} is already a member of this group.`);
      return;
    }
    setGroupActionError(null);
    try {
      const updated = await addGroupMembers(selectedConversation.id, {
        user_ids: [targetUser.id],
      });
      setDetailedConversation(updated);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to add member to group.");
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedConversation) return;
    setGroupActionError(null);
    try {
      const updated = await removeGroupMember(selectedConversation.id, userId);
      setDetailedConversation(updated);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to remove member.");
    }
  };

  const handlePromoteAdmin = async (userId: string) => {
    if (!selectedConversation) return;
    setGroupActionError(null);
    try {
      const updated = await promoteAdmin(selectedConversation.id, userId);
      setDetailedConversation(updated);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to promote to admin.");
    }
  };

  const handleDemoteAdmin = async (userId: string) => {
    if (!selectedConversation) return;
    setGroupActionError(null);
    try {
      const updated = await demoteAdmin(selectedConversation.id, userId);
      setDetailedConversation(updated);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to demote from admin.");
    }
  };

  const handleTransferOwnership = async (userId: string) => {
    if (!selectedConversation) return;
    if (
      !window.confirm(
        "Are you sure you want to transfer ownership of this group? You will be demoted to Admin."
      )
    ) {
      return;
    }
    setGroupActionError(null);
    try {
      const updated = await transferOwnership(selectedConversation.id, userId);
      setDetailedConversation(updated);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to transfer ownership.");
    }
  };

  const handleLeaveGroup = async () => {
    if (!selectedConversation) return;
    if (!window.confirm("Are you sure you want to leave this group?")) {
      return;
    }
    setGroupActionError(null);
    try {
      await leaveGroup(selectedConversation.id);
      setShowGroupInfoModal(false);
      setSelectedConversation(null);
      setMessages([]);
      refreshConversations();
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setGroupActionError(apiErr.error?.message || "Failed to leave group.");
    }
  };

  // Phase 8: Privacy & Blocking Handlers
  const refreshPrivacyData = useCallback(async () => {
    if (!currentUser) return;
    setIsLoadingPrivacy(true);
    setIsLoadingBlocks(true);
    setPrivacyError(null);
    try {
      const [settings, blocks] = await Promise.all([
        getPrivacySettings(),
        getBlockedUsers(),
      ]);
      setPrivacySettings(settings);
      setBlockedUsers(blocks);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setPrivacyError(apiErr.error?.message || "Failed to load privacy settings.");
    } finally {
      setIsLoadingPrivacy(false);
      setIsLoadingBlocks(false);
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser && (activeTab === "privacy" || activeTab === "chat")) {
      refreshPrivacyData();
    }
  }, [currentUser, activeTab, refreshPrivacyData]);

  const handleUpdatePrivacy = async (field: keyof PrivacySetting, value: string | boolean) => {
    setPrivacyError(null);
    setPrivacySuccess(null);
    try {
      const updated = await updatePrivacySettings({ [field]: value });
      setPrivacySettings(updated);
      setPrivacySuccess("Privacy settings updated successfully.");
      setTimeout(() => setPrivacySuccess(null), 3000);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setPrivacyError(apiErr.error?.message || "Failed to update privacy setting.");
    }
  };

  const handleBlockUser = async (targetUser: UserSearchResult) => {
    setBlockActionError(null);
    try {
      await blockUser({ user_id: targetUser.id });
      await refreshPrivacyData();
      refreshConversations();
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setBlockActionError(apiErr.error?.message || "Failed to block user.");
    }
  };

  const handleUnblockUser = async (targetUserId: string) => {
    setBlockActionError(null);
    try {
      await unblockUser(targetUserId);
      await refreshPrivacyData();
      refreshConversations();
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setBlockActionError(apiErr.error?.message || "Failed to unblock user.");
    }
  };

  // Phase 9: Chat UX Action Handlers (Replies, Edits, Deletes)
  const handleReplyMessage = (msg: Message) => {
    setEditingMessage(null);
    setReplyingTo({
      id: msg.id,
      senderName: msg.sender.display_name || msg.sender.username,
      text: msg.deleted_at ? "This message was deleted." : (msg.text || msg.original_text).slice(0, 100),
    });
  };

  const handleCancelReply = () => {
    setReplyingTo(null);
  };

  const handleEditMessage = (msg: Message) => {
    setReplyingTo(null);
    setEditingMessage({
      id: msg.id,
      text: msg.original_text,
    });
  };

  const handleCancelEdit = () => {
    setEditingMessage(null);
  };

  const handleSaveEdit = async (messageId: string, newText: string) => {
    setChatError(null);
    try {
      if (wsStatus === "CONNECTED") {
        await wsManager.editMessage(messageId, newText);
      } else {
        const updated = await editMessage(messageId, newText);
        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, ...updated } : m))
        );
      }
      setEditingMessage(null);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || (err as Error).message || "Failed to edit message");
      throw err;
    }
  };

  const handleDeleteMessage = async (messageId: string) => {
    setChatError(null);
    try {
      if (wsStatus === "CONNECTED") {
        await wsManager.deleteMessage(messageId);
      } else {
        const res = await deleteMessage(messageId);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  text: "This message was deleted.",
                  deleted_at: res.deleted_at,
                  translations: [],
                }
              : m
          )
        );
      }
    } catch (err: unknown) {
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || (err as Error).message || "Failed to delete message");
    }
  };

  const handleSendMessage = async (text: string, clientMessageId: string, replyToId?: string | null) => {
    if (!selectedConversation) return;
    setChatError(null);

    // Optimistic pending message bubble in timeline
    const optimisticMsg: Message = {
      id: `pending-${clientMessageId}`,
      conversation_id: selectedConversation.id,
      sender: {
        id: currentUser!.id,
        username: currentUser!.username,
        display_name: currentUser!.display_name,
      },
      client_message_id: clientMessageId,
      sequence_number: messages.length + 1,
      text,
      original_text: text,
      status: "SENT",
      reply_to_message_id: replyToId || null,
      reply_to: replyingTo
        ? {
            id: replyingTo.id,
            sender_name: replyingTo.senderName,
            text: replyingTo.text,
          }
        : null,
      version: 1,
      edited_at: null,
      deleted_at: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      if (wsStatus === "CONNECTED") {
        // Send directly via WebSocket
        const sentAck = await wsManager.sendMessage(
          selectedConversation.id,
          clientMessageId,
          text,
          replyToId
        );
        setMessages((prev) =>
          prev.map((m) =>
            m.client_message_id === clientMessageId
              ? { ...m, id: sentAck.message_id, sequence_number: sentAck.sequence_number }
              : m
          )
        );
      } else {
        // Fallback to REST API
        const newMsg = await sendMessage(selectedConversation.id, {
          text,
          client_message_id: clientMessageId,
          reply_to_id: replyToId || null,
        });

        setMessages((prev) =>
          prev.map((m) => (m.client_message_id === clientMessageId ? newMsg : m))
        );
      }

      setReplyingTo(null);

      // Update latest message preview in conversations list
      setConversations((prev) =>
        prev.map((c) =>
          c.id === selectedConversation.id
            ? {
                ...c,
                last_message_at: new Date().toISOString(),
                latest_message: {
                  id: optimisticMsg.id,
                  sender_id: currentUser!.id,
                  sender_username: currentUser!.username,
                  text_preview: text.slice(0, 50),
                  created_at: new Date().toISOString(),
                  sequence_number: optimisticMsg.sequence_number,
                },
              }
            : c
        )
      );
    } catch (err: unknown) {
      // Revert optimistic message if send failed
      setMessages((prev) => prev.filter((m) => m.client_message_id !== clientMessageId));
      const apiErr = err as ApiErrorPayload;
      setChatError(apiErr.error?.message || (err as Error).message || "Failed to send message");
      throw err;
    }
  };

  const handleTypingStart = () => {
    if (selectedConversation) {
      wsManager.startTyping(selectedConversation.id);
    }
  };

  const handleTypingStop = () => {
    if (selectedConversation) {
      wsManager.stopTyping(selectedConversation.id);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const res = await register({
        username,
        email,
        display_name: displayName,
        password,
        interface_language: interfaceLang,
        preferred_chat_language: preferredChatLang,
      });
      setCurrentUser(res.user);
      setAuthSuccess(`Registered and authenticated successfully as @${res.user.username}`);
    } catch (err: unknown) {
      setAuthError(err as ApiErrorPayload);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const res = await login({ username, password });
      setCurrentUser(res.user);
      setAuthSuccess(`Logged in successfully as @${res.user.username}`);
    } catch (err: unknown) {
      setAuthError(err as ApiErrorPayload);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    wsManager.disconnect();
    await logout();
    setCurrentUser(null);
    setSelectedConversation(null);
    setMessages([]);
    setConversations([]);
    setPresenceMap({});
    setTypingMap({});
    setAuthSuccess("Logged out successfully.");
  };

  const handleUpdateLanguages = async (newInterface?: string, newChat?: string) => {
    if (!currentUser) return;
    try {
      const res = await updateMe({
        interface_language: newInterface || currentUser.interface_language?.code,
        preferred_chat_language: newChat || currentUser.preferred_chat_language?.code,
      });
      setCurrentUser(res.user);
      setAuthSuccess("User language preferences updated.");
    } catch (err: unknown) {
      setAuthError(err as ApiErrorPayload);
    }
  };

  const handleAnalyzeNlp = async (textToAnalyze?: string) => {
    const text = textToAnalyze !== undefined ? textToAnalyze : nlpInput;
    if (!text.trim()) return;
    setNlpLoading(true);
    setNlpError(null);
    try {
      const res = await analyzeText(text);
      setNlpResult(res);
    } catch (err: unknown) {
      setNlpError((err as Error)?.message || "Failed to analyze text");
    } finally {
      setNlpLoading(false);
    }
  };

  const handlePresetClick = (presetText: string) => {
    setNlpInput(presetText);
    handleAnalyzeNlp(presetText);
  };

  const handleTransliterate = async () => {
    if (!transliterateInput.trim()) return;
    setTransliterateLoading(true);
    try {
      const res = await transliterateText({
        text: transliterateInput,
        source_lang: "hi",
        target_script: "Deva",
      });
      setTransliterateResult(res.transliterated_text);
    } catch {
      setTransliterateResult(null);
    } finally {
      setTransliterateLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "nlp" && !nlpResult) {
      handleAnalyzeNlp("me kal nahi aaunga 😊");
    }
  }, [activeTab]);

  // Active peer presence in selected direct conversation
  const peerUserId = selectedConversation?.direct_user?.id;
  const isPeerOnline = peerUserId ? presenceMap[peerUserId]?.is_online : false;
  const peerLastSeen = peerUserId ? presenceMap[peerUserId]?.last_seen_at : null;

  return (
    <main className={styles.container}>
      <div className={styles.mainCard}>
        <header className={styles.header}>
          <div className={styles.logoBadge} aria-hidden="true">
            VL
          </div>
          <div className={styles.titleGroup} style={{ flex: 1 }}>
            <h1>VaaniLink</h1>
            <p className={styles.tagline}>
              Write in your language. Read in your language.
            </p>
          </div>

          {currentUser && (
            <div
              className={`${styles.realtimeBadge} ${
                wsStatus === "CONNECTED"
                  ? styles.badgeConnected
                  : wsStatus === "RECONNECTING"
                  ? styles.badgeReconnecting
                  : styles.badgeDisconnected
              }`}
            >
              <span className={styles.statusDot} aria-hidden="true" />
              <span>
                {wsStatus === "CONNECTED"
                  ? "Realtime Live"
                  : wsStatus === "RECONNECTING"
                  ? "Reconnecting..."
                  : "Offline"}
              </span>
            </div>
          )}
        </header>

        <nav className={styles.navTabs} aria-label="Feature navigation">
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "chat" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            4. Direct & Group Chat (Live)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "groups" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("groups")}
          >
            7. Group Chat & Roles (Phase 7)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "privacy" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("privacy")}
          >
            8. Privacy & Blocking (Phase 8)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "chat_ux" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("chat_ux")}
          >
            9. Chat UX & a11y (Phase 9)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "nlp" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("nlp")}
          >
            5. NLP Intelligence (Phase 5)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "translation" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("translation")}
          >
            6. Translation & Caching (Phase 6)
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "avatars" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("avatars")}
          >
            1. Initial Avatars
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "languages" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("languages")}
          >
            2. Language Registry & RTL
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeTab === "auth" ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab("auth")}
          >
            3. Accounts & Settings
          </button>
        </nav>

        {/* TAB 4: Direct Chat & Realtime (Phase 4) */}
        {activeTab === "chat" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Real-Time Messaging & Presence Lifecycle (Section 2, 5, 12, 46)
              </h2>
              <p className={styles.sectionSubtitle}>
                Bi-directional WebSocket streaming, delivery & seen acknowledgement lifecycle{" "}
                (<code>SENT ✓</code> &rarr; <code>DELIVERED ✓✓</code> &rarr; <code>SEEN ✓✓</code>), live typing indicators, and presence tracking.
              </p>
            </div>

            {chatError && (
              <div className={styles.errorBox} role="alert">
                {chatError}
              </div>
            )}

            {currentUser && wsStatus !== "CONNECTED" && (
              <div className={styles.connectionBanner} role="alert">
                <span>
                  {wsStatus === "RECONNECTING"
                    ? "⚠️ Connection lost. Automatically reconnecting to VaaniLink..."
                    : "⚠️ Disconnected from live server."}
                </span>
                <button
                  type="button"
                  className={styles.reconnectBtn}
                  onClick={() => {
                    const token = getAccessToken();
                    if (token) wsManager.connect(token);
                  }}
                >
                  Reconnect Now
                </button>
              </div>
            )}

            {!currentUser ? (
              <div className={styles.unauthNotice}>
                <p>
                  <strong>Authentication Required:</strong> Please log in or register an account
                  to test real-time direct messaging.
                </p>
                <button
                  type="button"
                  className={styles.submitBtn}
                  onClick={() => setActiveTab("auth")}
                >
                  Go to Accounts & Login
                </button>
              </div>
            ) : (
              <div className={styles.chatLayout}>
                {/* Left Column: Search & Conversations */}
                <div
                  className={`${styles.chatSidebar} ${
                    showMobileChatView ? styles.hideOnMobile : ""
                  }`}
                >
                  <div className={styles.sidebarHeader}>
                    <UserSearch
                      onSelectUser={handleSelectUserFromSearch}
                      currentUserId={currentUser.id}
                      placeholder="Search users to chat..."
                    />
                  </div>

                  {isLoadingConversations ? (
                    <div style={{ padding: "1rem", color: "var(--color-text-muted)" }}>
                      Loading chats...
                    </div>
                  ) : (
                    <ConversationList
                      conversations={conversations}
                      selectedConversationId={selectedConversation?.id || null}
                      onSelectConversation={handleSelectConversation}
                      presenceMap={presenceMap}
                      onCreateGroupClick={handleOpenCreateGroup}
                    />
                  )}
                </div>

                {/* Right Column: Chat Timeline & Composer */}
                <div
                  className={`${styles.chatMain} ${
                    !showMobileChatView ? styles.hideOnMobile : ""
                  }`}
                >
                  {selectedConversation ? (
                    <>
                      <div className={styles.chatHeader}>
                        <div className={styles.chatHeaderUser}>
                          {showMobileChatView && (
                            <button
                              type="button"
                              className={styles.mobileBackBtn}
                              onClick={() => setShowMobileChatView(false)}
                              title="Back to conversation list"
                              aria-label="Back to conversations list"
                            >
                              ←
                            </button>
                          )}
                          <UserAvatar
                            name={
                              selectedConversation.direct_user?.display_name ||
                              selectedConversation.group_name ||
                              "Chat"
                            }
                            size="md"
                            isOnline={
                              selectedConversation.type === "DIRECT" ? isPeerOnline : false
                            }
                          />
                          <div className={styles.chatHeaderMeta}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <span className={styles.chatHeaderTitle}>
                                {selectedConversation.direct_user?.display_name ||
                                  selectedConversation.group_name}
                              </span>
                              {selectedConversation.type === "GROUP" && (
                                <span className={styles.groupBadgeHeader}>Group</span>
                              )}
                            </div>
                            <div className={styles.peerPresenceRow}>
                              <span className={styles.chatHeaderSubtitle}>
                                {selectedConversation.type === "DIRECT"
                                  ? `@${selectedConversation.direct_user?.username || "direct"}`
                                  : "Multilingual Group Chat"}
                              </span>
                              {selectedConversation.direct_user && (
                                <span
                                  className={
                                    isPeerOnline
                                      ? styles.peerOnlineBadge
                                      : styles.peerOfflineBadge
                                  }
                                >
                                  {isPeerOnline
                                    ? "• Online"
                                    : peerLastSeen
                                    ? `• Last seen ${new Date(peerLastSeen).toLocaleTimeString([], {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      })}`
                                    : "• Offline"}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {selectedConversation.type === "GROUP" && (
                          <button
                            type="button"
                            className={styles.groupInfoBtn}
                            onClick={handleOpenGroupInfo}
                            title="View group members, roles, and settings"
                          >
                            <span>👥</span> Group Info
                          </button>
                        )}

                        {selectedConversation.type === "DIRECT" && selectedConversation.direct_user && (
                          <button
                            type="button"
                            className={styles.blockedHeaderAction}
                            onClick={() => {
                              const isBlocked = blockedUsers.some(
                                (b) => b.user.id === selectedConversation.direct_user?.id
                              );
                              if (isBlocked) {
                                handleUnblockUser(selectedConversation.direct_user!.id);
                              } else {
                                if (
                                  window.confirm(
                                    `Block ${selectedConversation.direct_user!.display_name}? Direct messaging will be restricted.`
                                  )
                                ) {
                                  handleBlockUser(selectedConversation.direct_user!);
                                }
                              }
                            }}
                            title={
                              blockedUsers.some(
                                (b) => b.user.id === selectedConversation.direct_user?.id
                              )
                                ? "Unblock this user"
                                : "Block this user"
                            }
                          >
                            {blockedUsers.some(
                              (b) => b.user.id === selectedConversation.direct_user?.id
                            )
                              ? "✓ Unblock"
                              : "🚫 Block"}
                          </button>
                        )}
                      </div>

                      {selectedConversation.type === "DIRECT" &&
                        selectedConversation.direct_user &&
                        blockedUsers.some(
                          (b) => b.user.id === selectedConversation.direct_user?.id
                        ) && (
                          <div className={styles.blockedBanner} role="alert">
                            <span>
                              🚫 You have blocked this user. Direct messages and presence are restricted.
                            </span>
                            <button
                              type="button"
                              className={styles.actionBtnSmall}
                              onClick={() => handleUnblockUser(selectedConversation.direct_user!.id)}
                            >
                              Unblock
                            </button>
                          </div>
                        )}

                      {isLoadingMessages ? (
                        <div className={styles.chatPlaceholder}>
                          <span>Loading messages...</span>
                        </div>
                      ) : (
                        <MessageTimeline
                          messages={messages}
                          currentUserId={currentUser.id}
                          typingUsers={
                            selectedConversation
                              ? typingMap[selectedConversation.id] || []
                              : []
                          }
                          preferredChatLanguage={
                            currentUser.preferred_chat_language?.code || preferredChatLang
                          }
                          onReplyMessage={handleReplyMessage}
                          onEditMessage={handleEditMessage}
                          onDeleteMessage={handleDeleteMessage}
                        />
                      )}

                      <MessageComposer
                        onSendMessage={handleSendMessage}
                        onTypingStart={handleTypingStart}
                        onTypingStop={handleTypingStop}
                        replyingTo={replyingTo}
                        onCancelReply={handleCancelReply}
                        editingMessage={editingMessage}
                        onCancelEdit={handleCancelEdit}
                        onSaveEdit={handleSaveEdit}
                      />
                    </>
                  ) : (
                    <div className={styles.chatPlaceholder}>
                      <span className={styles.chatPlaceholderIcon} aria-hidden="true">
                        💬
                      </span>
                      <p>Select an existing conversation or search for a user to start messaging.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Create Group Modal (Phase 7) */}
            {showCreateGroupModal && (
              <div
                className={styles.modalOverlay}
                role="dialog"
                aria-modal="true"
                aria-labelledby="create-group-title"
                onClick={() => setShowCreateGroupModal(false)}
              >
                <div
                  className={styles.modalContainer}
                  style={{ maxWidth: "480px" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className={styles.modalHeader}>
                    <h3 id="create-group-title" className={styles.modalTitle}>
                      Create Multilingual Group
                    </h3>
                    <button
                      type="button"
                      className={styles.modalCloseBtn}
                      onClick={() => setShowCreateGroupModal(false)}
                      aria-label="Close group creation"
                    >
                      ✕
                    </button>
                  </div>

                  <form onSubmit={handleCreateGroup} className={styles.modalBody}>
                    {createGroupError && (
                      <div className={styles.errorBox} role="alert">
                        {createGroupError}
                      </div>
                    )}

                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>Group Name *</label>
                      <input
                        type="text"
                        className={styles.formInput}
                        value={newGroupName}
                        onChange={(e) => setNewGroupName(e.target.value)}
                        placeholder="e.g. Project Orion / ग्लोबल टीम"
                        maxLength={150}
                        required
                        autoFocus
                      />
                    </div>

                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>
                        Add Initial Members ({selectedGroupMembers.length} selected)
                      </label>
                      <UserSearch
                        onSelectUser={handleToggleMemberSelection}
                        currentUserId={currentUser?.id}
                        placeholder="Search users to add..."
                      />

                      {selectedGroupMembers.length > 0 && (
                        <div className={styles.chipList}>
                          {selectedGroupMembers.map((u) => (
                            <span key={u.id} className={styles.selectedChip}>
                              <span>{u.display_name}</span>
                              <button
                                type="button"
                                className={styles.chipRemoveBtn}
                                onClick={() => handleToggleMemberSelection(u)}
                                aria-label={`Remove ${u.display_name}`}
                              >
                                ×
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: "8px",
                        marginTop: "1rem",
                      }}
                    >
                      <button
                        type="button"
                        className={styles.submitBtn}
                        style={{
                          backgroundColor: "transparent",
                          color: "var(--color-text-main)",
                          border: "1px solid var(--color-border)",
                        }}
                        onClick={() => setShowCreateGroupModal(false)}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className={styles.submitBtn}
                        disabled={isCreatingGroup || !newGroupName.trim()}
                      >
                        {isCreatingGroup ? "Creating..." : "Create Group"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* Group Info & Members Modal (Phase 7: Roles & Member Management) */}
            {showGroupInfoModal && detailedConversation && (
              <div
                className={styles.modalOverlay}
                role="dialog"
                aria-modal="true"
                aria-labelledby="group-info-modal-title"
                onClick={() => setShowGroupInfoModal(false)}
              >
                <div
                  className={styles.modalContainer}
                  style={{ maxWidth: "560px" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className={styles.modalHeader}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <h3 id="group-info-modal-title" className={styles.modalTitle}>
                        {detailedConversation.group_name}
                      </h3>
                      <span className={styles.groupBadgeHeader}>
                        {detailedConversation.members.length} Members
                      </span>
                    </div>
                    <button
                      type="button"
                      className={styles.modalCloseBtn}
                      onClick={() => setShowGroupInfoModal(false)}
                      aria-label="Close group details"
                    >
                      ✕
                    </button>
                  </div>

                  <div className={styles.modalBody}>
                    {isLoadingGroupDetail && <div>Loading group details...</div>}
                    {groupActionError && (
                      <div className={styles.errorBox} role="alert">
                        {groupActionError}
                      </div>
                    )}

                    {(() => {
                      const myMember = detailedConversation.members.find(
                        (m) => m.user.id === currentUser?.id
                      );
                      const myRole: MemberRole = myMember?.role || "MEMBER";
                      const isOwner = myRole === "OWNER";
                      const isAdmin = myRole === "ADMIN" || isOwner;

                      return (
                        <>
                          {/* Role Indicator Banner */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "0.5rem 0.75rem",
                              backgroundColor: "var(--color-bg-base)",
                              borderRadius: "var(--radius-md)",
                              border: "1px solid var(--color-border)",
                              fontSize: "0.8125rem",
                            }}
                          >
                            <span>Your Role in Group:</span>
                            <span
                              className={`${styles.roleBadge} ${
                                isOwner
                                  ? styles.roleOwner
                                  : isAdmin
                                  ? styles.roleAdmin
                                  : styles.roleMember
                              }`}
                            >
                              {myRole}
                            </span>
                          </div>

                          {/* Rename Group form (Owner or Admin only) */}
                          {isAdmin && (
                            <form onSubmit={handleRenameGroup} className={styles.groupRenameForm}>
                              <input
                                type="text"
                                value={renameInput}
                                onChange={(e) => setRenameInput(e.target.value)}
                                className={styles.groupRenameInput}
                                placeholder="Rename group..."
                                maxLength={150}
                              />
                              <button type="submit" className={styles.actionBtnSmall}>
                                Rename
                              </button>
                            </form>
                          )}

                          {/* Add Members section (Owner or Admin only) */}
                          {isAdmin && (
                            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                              <label
                                style={{
                                  fontSize: "0.75rem",
                                  fontWeight: 700,
                                  textTransform: "uppercase",
                                  color: "var(--color-text-muted)",
                                }}
                              >
                                Add Member to Group
                              </label>
                              <UserSearch
                                onSelectUser={handleAddMemberToGroup}
                                currentUserId={currentUser?.id}
                                placeholder="Search users to add..."
                              />
                            </div>
                          )}

                          {/* Member List */}
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                            <span
                              style={{
                                fontSize: "0.75rem",
                                fontWeight: 700,
                                textTransform: "uppercase",
                                color: "var(--color-text-muted)",
                              }}
                            >
                              Group Members ({detailedConversation.members.length})
                            </span>
                            <div className={styles.groupMemberList}>
                              {detailedConversation.members.map((member) => {
                                const isSelf = member.user.id === currentUser?.id;
                                const targetIsOwner = member.role === "OWNER";
                                const targetIsAdmin = member.role === "ADMIN";

                                return (
                                  <div key={member.id} className={styles.groupMemberItem}>
                                    <div className={styles.groupMemberMeta}>
                                      <UserAvatar name={member.user.display_name} size="sm" />
                                      <div className={styles.groupMemberInfo}>
                                        <span className={styles.groupMemberName}>
                                          {member.user.display_name} {isSelf && "(You)"}
                                        </span>
                                        <span className={styles.groupMemberUsername}>
                                          @{member.user.username}
                                        </span>
                                      </div>
                                    </div>

                                    <div className={styles.groupMemberActions}>
                                      <span
                                        className={`${styles.roleBadge} ${
                                          member.role === "OWNER"
                                            ? styles.roleOwner
                                            : member.role === "ADMIN"
                                            ? styles.roleAdmin
                                            : styles.roleMember
                                        }`}
                                      >
                                        {member.role}
                                      </span>

                                      {/* Role Action Controls */}
                                      {!isSelf && isOwner && (
                                        <>
                                          {targetIsAdmin ? (
                                            <button
                                              type="button"
                                              className={styles.actionBtnSmall}
                                              onClick={() => handleDemoteAdmin(member.user.id)}
                                              title="Demote admin to regular member"
                                            >
                                              Demote
                                            </button>
                                          ) : (
                                            <button
                                              type="button"
                                              className={styles.actionBtnSmall}
                                              onClick={() => handlePromoteAdmin(member.user.id)}
                                              title="Promote to admin"
                                            >
                                              Make Admin
                                            </button>
                                          )}
                                          <button
                                            type="button"
                                            className={styles.actionBtnSmall}
                                            onClick={() => handleTransferOwnership(member.user.id)}
                                            title="Transfer ownership to this member"
                                          >
                                            Transfer Owner
                                          </button>
                                          <button
                                            type="button"
                                            className={styles.actionBtnDangerSmall}
                                            onClick={() => handleRemoveMember(member.user.id)}
                                            title="Remove from group"
                                          >
                                            Remove
                                          </button>
                                        </>
                                      )}

                                      {!isSelf && !isOwner && isAdmin && !targetIsOwner && !targetIsAdmin && (
                                        <button
                                          type="button"
                                          className={styles.actionBtnDangerSmall}
                                          onClick={() => handleRemoveMember(member.user.id)}
                                          title="Remove ordinary member"
                                        >
                                          Remove
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          {/* Leave Group Action */}
                          <button
                            type="button"
                            className={styles.leaveGroupBtn}
                            onClick={handleLeaveGroup}
                          >
                            <span>🚪</span> Leave Group
                          </button>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* TAB 7: Group Chat & Roles (Phase 7) */}
        {activeTab === "groups" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Multilingual Group Chat, Roles & Message Receipts (Phase 7)
              </h2>
              <p className={styles.sectionSubtitle}>
                Section 11, Section 12, Section 46: Strict server-side role hierarchy (Owner, Admin,
                Member), per-recipient delivery &amp; read receipts (Message Info), and target-language
                deduplication across group members.
              </p>
            </div>

            {/* Role Hierarchy Matrix Card */}
            <div className={styles.profileCard}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
                    Group Role &amp; Permission Matrix (Section 11)
                  </h3>
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                    Every capability is authorized at the database and service level, never solely in the UI.
                  </p>
                </div>
                <button
                  type="button"
                  className={styles.submitBtn}
                  style={{ width: "auto", padding: "0.5rem 1rem", fontSize: "0.8125rem" }}
                  onClick={() => {
                    setActiveTab("chat");
                    setShowCreateGroupModal(true);
                  }}
                >
                  <span>👥</span> Create New Group in Live Chat
                </button>
              </div>

              <div className={styles.roleMatrixWrapper}>
                <table className={styles.roleMatrixTable}>
                  <thead>
                    <tr>
                      <th>Capability / Action</th>
                      <th>Owner</th>
                      <th>Admin</th>
                      <th>Member</th>
                      <th>Enforcement Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <strong>Rename Group</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Add Members</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Remove Ordinary Members</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Remove Admins</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Promote Member to Admin</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Demote Admin to Member</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (HTTP 403)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Transfer Group Ownership</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td className={styles.matrixDenied}>✗ Denied</td>
                      <td>Server (Atomic DB Transaction)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Leave Group</strong>
                      </td>
                      <td className={styles.matrixAllowed}>
                        ✓ Yes (Must transfer first if members exist)
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td>Server Validation (409 Conflict)</td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Send / Read / Reply Messages</strong>
                      </td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td className={styles.matrixAllowed}>✓ Yes</td>
                      <td>Active Membership Required</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Translation Deduplication & Fan-Out Card */}
            <div className={styles.profileCard}>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
                Target-Language Deduplication &amp; Multi-Recipient Fan-Out
              </h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                In group conversations, VaaniLink aggregates all active recipients'{" "}
                <code>preferred_chat_language</code> and translates <strong>exactly once per unique target language</strong>, avoiding redundant provider calls and maximizing cache hit rates.
              </p>

              <div className={styles.simContainer}>
                <div className={styles.simSenderBanner}>
                  <div>
                    <div className={styles.simSenderLabel}>Sender: Alice (@alice)</div>
                    <div className={styles.simSenderText}>"Are you all coming to the meeting?"</div>
                  </div>
                  <span className={styles.nlpChip}>Detected: English (Latn)</span>
                </div>

                <div className={styles.simRecipientGrid}>
                  {/* Recipient 1: Vikram (Hindi) */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>Vikram (Hindi)</span>
                      <span className={styles.simRecipientPref}>Pref: HI</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        क्या आप सब मीटिंग में आ रहे हैं?
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>🌐 Hindi Translation</span>
                        <span className={styles.matrixAllowed}>✓✓ Read 10:14 AM</span>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 2: Rahul (Hindi - Shares same translation!) */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>Rahul (Hindi)</span>
                      <span className={styles.simRecipientPref}>Pref: HI</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        क्या आप सब मीटिंग में आ रहे हैं?
                      </span>
                      <div className={styles.simToggleRow}>
                        <span style={{ color: "#059669", fontWeight: 700 }}>
                          ⚡ Shared Cache (0 ms)
                        </span>
                        <span className={styles.matrixAllowed}>✓✓ Read 10:15 AM</span>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 3: Priya (Gujarati) */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>Priya (Gujarati)</span>
                      <span className={styles.simRecipientPref}>Pref: GU</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        શું તમે બધા મીટિંગમાં આવી રહ્યા છો?
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>🌐 Gujarati Translation</span>
                        <span style={{ color: "#2563eb", fontWeight: 700 }}>
                          ✓✓ Delivered 10:14 AM
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 4: Tariq (Urdu RTL) */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>Tariq (Urdu RTL)</span>
                      <span className={styles.simRecipientPref}>Pref: UR (RTL)</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={`${styles.simBubbleText} ${styles.simRtlText}`}>
                        کیا آپ سب میٹنگ میں آ رہے ہیں؟
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>🌐 Urdu (RTL) Translation</span>
                        <span style={{ color: "#64748b" }}>⏳ Pending</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: "var(--color-bg-surface)",
                    padding: "0.75rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--color-border)",
                    fontSize: "0.8125rem",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <span>
                    <strong>Message Info Receipt Breakdown:</strong> 4 Total Recipients · 2 Read
                    (50%) · 1 Delivered (25%) · 1 Pending (25%)
                  </span>
                  <button
                    type="button"
                    className={styles.actionBtnSmall}
                    onClick={() => setActiveTab("chat")}
                  >
                    Open Live Timeline &amp; Test Message Info (ℹ️)
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* TAB 8: Privacy & Blocking (Phase 8) */}
        {activeTab === "privacy" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Privacy Controls &amp; User Blocking (Phase 8)
              </h2>
              <p className={styles.sectionSubtitle}>
                Section 2, Section 8, Section 38, docs/PRIVACY.md: Centralized server-side privacy policies,
                online presence and last seen masking, read receipt emission control, direct messaging and
                group invite permission rules, and bidirectional blocking with shared group isolation.
              </p>
            </div>

            {privacyError && (
              <div className={styles.errorBox} role="alert">
                {privacyError}
              </div>
            )}

            {privacySuccess && (
              <div
                style={{
                  backgroundColor: "#ecfdf5",
                  border: "1px solid #a7f3d0",
                  color: "#065f46",
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                }}
                role="status"
              >
                ✓ {privacySuccess}
              </div>
            )}

            {!currentUser ? (
              <div className={styles.unauthNotice}>
                <p>
                  <strong>Authentication Required:</strong> Please log in or register an account
                  to view and manage your privacy settings.
                </p>
                <button
                  type="button"
                  className={styles.submitBtn}
                  onClick={() => setActiveTab("auth")}
                >
                  Go to Accounts &amp; Login
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {/* Discrete Privacy Controls Card */}
                <div className={styles.profileCard}>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
                    Discrete Privacy Settings (docs/PRIVACY.md)
                  </h3>
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                    Control who can see your presence, message you, and invite you to groups. Changes take effect immediately across REST and WebSocket channels.
                  </p>

                  {isLoadingPrivacy ? (
                    <div>Loading privacy settings...</div>
                  ) : privacySettings ? (
                    <div className={styles.privacyGrid}>
                      {/* 1. Last Seen */}
                      <div className={styles.privacyRow}>
                        <div className={styles.privacyText}>
                          <span className={styles.privacyTitle}>Last Seen Visibility</span>
                          <span className={styles.privacyDesc}>
                            Who can view your last active timestamp. If restricted, unauthorized users see nothing.
                          </span>
                        </div>
                        <select
                          className={styles.privacySelect}
                          value={privacySettings.last_seen_visibility}
                          onChange={(e) =>
                            handleUpdatePrivacy("last_seen_visibility", e.target.value as PrivacyVisibility)
                          }
                        >
                          <option value="EVERYONE">Everyone</option>
                          <option value="CONTACTS_ONLY">Contacts Only ("People I Chat With")</option>
                          <option value="NOBODY">Nobody</option>
                        </select>
                      </div>

                      {/* 2. Online Status */}
                      <div className={styles.privacyRow}>
                        <div className={styles.privacyText}>
                          <span className={styles.privacyTitle}>Online Status Visibility</span>
                          <span className={styles.privacyDesc}>
                            Who can see when you are currently connected. Unauthorized users see you as offline.
                          </span>
                        </div>
                        <select
                          className={styles.privacySelect}
                          value={privacySettings.online_status_visibility}
                          onChange={(e) =>
                            handleUpdatePrivacy("online_status_visibility", e.target.value as PrivacyVisibility)
                          }
                        >
                          <option value="EVERYONE">Everyone</option>
                          <option value="CONTACTS_ONLY">Contacts Only ("People I Chat With")</option>
                          <option value="NOBODY">Nobody</option>
                        </select>
                      </div>

                      {/* 3. Read Receipts */}
                      <div className={styles.privacyRow}>
                        <div className={styles.privacyText}>
                          <span className={styles.privacyTitle}>Read Receipts (Seen Checks)</span>
                          <span className={styles.privacyDesc}>
                            If disabled, you will still acknowledge delivery (✓✓) but suppress public read (✓✓ blue) receipts.
                          </span>
                        </div>
                        <button
                          type="button"
                          className={`${styles.privacyToggleBtn} ${
                            privacySettings.read_receipts_enabled
                              ? styles.privacyToggleActive
                              : styles.privacyToggleInactive
                          }`}
                          onClick={() =>
                            handleUpdatePrivacy(
                              "read_receipts_enabled",
                              !privacySettings.read_receipts_enabled
                            )
                          }
                        >
                          {privacySettings.read_receipts_enabled ? "✓✓ Enabled" : "✓ Disabled"}
                        </button>
                      </div>

                      {/* 4. Who Can Message Me */}
                      <div className={styles.privacyRow}>
                        <div className={styles.privacyText}>
                          <span className={styles.privacyTitle}>Who Can Message Me Directly</span>
                          <span className={styles.privacyDesc}>
                            Prevents unauthorized users from initiating new direct 1-to-1 conversations with you.
                          </span>
                        </div>
                        <select
                          className={styles.privacySelect}
                          value={privacySettings.who_can_message_me}
                          onChange={(e) =>
                            handleUpdatePrivacy("who_can_message_me", e.target.value as PrivacyVisibility)
                          }
                        >
                          <option value="EVERYONE">Everyone</option>
                          <option value="CONTACTS_ONLY">Contacts Only</option>
                          <option value="NOBODY">Nobody</option>
                        </select>
                      </div>

                      {/* 5. Who Can Add Me to Groups */}
                      <div className={styles.privacyRow}>
                        <div className={styles.privacyText}>
                          <span className={styles.privacyTitle}>Who Can Add Me to Groups</span>
                          <span className={styles.privacyDesc}>
                            Controls who is allowed to invite you into group conversations.
                          </span>
                        </div>
                        <select
                          className={styles.privacySelect}
                          value={privacySettings.who_can_add_me_to_groups}
                          onChange={(e) =>
                            handleUpdatePrivacy("who_can_add_me_to_groups", e.target.value as PrivacyVisibility)
                          }
                        >
                          <option value="EVERYONE">Everyone</option>
                          <option value="CONTACTS_ONLY">Contacts Only</option>
                          <option value="NOBODY">Nobody</option>
                        </select>
                      </div>
                    </div>
                  ) : null}
                </div>

                {/* Blocked Users Management Card */}
                <div className={styles.profileCard}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                    <div>
                      <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
                        Blocked Users ({blockedUsers.length})
                      </h3>
                      <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                        Blocked users cannot initiate direct chats, send direct messages, or view your presence.
                      </p>
                    </div>
                  </div>

                  {blockActionError && (
                    <div className={styles.errorBox} role="alert">
                      {blockActionError}
                    </div>
                  )}

                  <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <label style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "var(--color-text-muted)" }}>
                      Block a User
                    </label>
                    <UserSearch
                      onSelectUser={handleBlockUser}
                      currentUserId={currentUser.id}
                      placeholder="Search users to block..."
                    />
                  </div>

                  {isLoadingBlocks ? (
                    <div style={{ marginTop: "1rem" }}>Loading blocked list...</div>
                  ) : blockedUsers.length === 0 ? (
                    <div style={{ marginTop: "1rem", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                      You have not blocked any users.
                    </div>
                  ) : (
                    <div className={styles.blockedList}>
                      {blockedUsers.map((item) => (
                        <div key={item.id} className={styles.blockedItem}>
                          <div className={styles.blockedMeta}>
                            <UserAvatar name={item.user.display_name} size="sm" />
                            <div>
                              <div style={{ fontSize: "0.875rem", fontWeight: 600 }}>
                                {item.user.display_name}
                              </div>
                              <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                                @{item.user.username} · Blocked {new Date(item.blocked_at).toLocaleDateString()}
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            className={styles.unblockBtn}
                            onClick={() => handleUnblockUser(item.user.id)}
                          >
                            Unblock
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Shared Group Isolation Architecture Card */}
                <div className={styles.profileCard}>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
                    Blocking Architecture &amp; Shared Group Isolation (docs/PRIVACY.md)
                  </h3>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                      gap: "1rem",
                      marginTop: "0.75rem",
                    }}
                  >
                    <div
                      style={{
                        padding: "0.75rem",
                        backgroundColor: "var(--color-bg-base)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <h4 style={{ fontSize: "0.8125rem", fontWeight: 700, marginBottom: "4px" }}>
                        🚫 1-to-1 Direct Isolation
                      </h4>
                      <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                        When User A blocks User B, direct conversation initiation and direct messaging are strictly rejected by the server with <code>USER_BLOCKED</code> (HTTP 403).
                      </p>
                    </div>

                    <div
                      style={{
                        padding: "0.75rem",
                        backgroundColor: "var(--color-bg-base)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <h4 style={{ fontSize: "0.8125rem", fontWeight: 700, marginBottom: "4px" }}>
                        👥 Shared Group Isolation
                      </h4>
                      <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                        Blocking does <strong>not</strong> silently kick users from shared groups. Group messaging continues, but direct communication and presence remain strictly blocked.
                      </p>
                    </div>

                    <div
                      style={{
                        padding: "0.75rem",
                        backgroundColor: "var(--color-bg-base)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <h4 style={{ fontSize: "0.8125rem", fontWeight: 700, marginBottom: "4px" }}>
                        ⚡ WebSocket &amp; Presence Masking
                      </h4>
                      <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                        Blocked users cannot view online presence or last-seen timestamps, and live typing indicators are suppressed bidirectionally.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* TAB 5: NLP Intelligence (Phase 5) */}
        {activeTab === "nlp" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Language Intelligence & Script Analysis (Section 14, 15, 16, 23, 24)
              </h2>
              <p className={styles.sectionSubtitle}>
                Latin Script &ne; English! Real-time Unicode normalization (NFKC), script detection,
                Romanized Hindi (Hinglish) identification, code-mixed sentence tagging, and phonetic transliteration.
              </p>
            </div>

            {nlpError && (
              <div className={styles.errorBox} role="alert">
                {nlpError}
              </div>
            )}

            {/* Interactive Analysis Sandbox Card */}
            <div className={styles.profileCard}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Message Analysis Sandbox</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Type any text or click a preset to test language detection, script identification, and Romanization tagging:
              </p>

              {/* Presets */}
              <div className={styles.nlpPresetRow}>
                {NLP_PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    className={styles.nlpPresetBtn}
                    onClick={() => handlePresetClick(p.text)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Input & Action */}
              <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  className={styles.nlpTextarea}
                  value={nlpInput}
                  onChange={(e) => setNlpInput(e.target.value)}
                  placeholder="Enter a message to analyze (e.g., 'me kal nahi aaunga 😊')..."
                  rows={3}
                />
                <button
                  type="button"
                  className={styles.submitBtn}
                  disabled={nlpLoading || !nlpInput.trim()}
                  onClick={() => handleAnalyzeNlp()}
                  style={{ alignSelf: "flex-start" }}
                >
                  {nlpLoading ? "Analyzing..." : "Analyze Language & Script"}
                </button>
              </div>

              {/* Results */}
              {nlpResult && (
                <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div className={styles.nlpStatGrid}>
                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Primary Language</span>
                      <span className={styles.nlpStatValue}>
                        {nlpResult.detected_primary_language.toUpperCase()}
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>ISO Script</span>
                      <span className={styles.nlpStatValue}>
                        {nlpResult.detected_script}
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Romanized / Hinglish</span>
                      <span
                        className={styles.nlpStatValue}
                        style={{ color: nlpResult.is_romanized ? "#d97706" : "var(--color-text-main)" }}
                      >
                        {nlpResult.is_romanized ? "YES (Hinglish)" : "NO"}
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Code-Mixed</span>
                      <span
                        className={styles.nlpStatValue}
                        style={{ color: nlpResult.is_mixed_language ? "#8b5cf6" : "var(--color-text-main)" }}
                      >
                        {nlpResult.is_mixed_language ? "YES (Multilingual)" : "NO"}
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Confidence</span>
                      <span className={styles.nlpStatValue}>
                        {Math.round(nlpResult.language_confidence * 100)}%
                      </span>
                      <div className={styles.confidenceTrack}>
                        <div
                          className={styles.confidenceFill}
                          style={{ width: `${Math.round(nlpResult.language_confidence * 100)}%` }}
                        />
                      </div>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Protected Tokens</span>
                      <span className={styles.nlpStatValue}>
                        {nlpResult.protected_tokens_count}
                      </span>
                    </div>
                  </div>

                  {/* Transliteration Preview if available */}
                  {nlpResult.transliterated_text && (
                    <div className={styles.nlpTransliterationBox}>
                      <span className={styles.nlpTransliterationLabel}>
                        Devanagari Transliteration Preview (Phonetic Indic Normalization):
                      </span>
                      <span className={styles.nlpTransliterationText}>
                        {nlpResult.transliterated_text}
                      </span>
                    </div>
                  )}

                  {/* Token breakdown table */}
                  {nlpResult.tokens && nlpResult.tokens.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>
                        Token-Level Analysis & Entity Protection
                      </h4>
                      <div className={styles.nlpTokensWrapper}>
                        <table className={styles.nlpTokensTable}>
                          <thead>
                            <tr>
                              <th>Token</th>
                              <th>Type</th>
                              <th>Script</th>
                              <th>Lang</th>
                              <th>Romanized</th>
                            </tr>
                          </thead>
                          <tbody>
                            {nlpResult.tokens.map((t, idx) => (
                              <tr key={idx}>
                                <td style={{ fontFamily: "var(--font-family-mono)", fontWeight: 500 }}>
                                  {t.text}
                                </td>
                                <td>
                                  <span className={styles.nlpChip}>
                                    {t.token_type}
                                  </span>
                                </td>
                                <td>{t.script || "—"}</td>
                                <td>{t.language ? t.language.toUpperCase() : "—"}</td>
                                <td>
                                  {t.is_romanized ? (
                                    <span className={`${styles.nlpChip} ${styles.nlpChipActive}`}>
                                      Hinglish
                                    </span>
                                  ) : (
                                    "—"
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Standalone Transliteration Tool */}
            <div className={styles.profileCard}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Phonetic Transliteration Tool (Latin &rarr; Devanagari)</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Converts Romanized Hindi / Hinglish into standard Devanagari script phonetically while preserving emojis and punctuation.
              </p>

              <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
                <input
                  type="text"
                  className={styles.textInput}
                  value={transliterateInput}
                  onChange={(e) => setTransliterateInput(e.target.value)}
                  placeholder="e.g. kal milte hai"
                  style={{ flex: 1, minWidth: "200px" }}
                />
                <button
                  type="button"
                  className={styles.submitBtn}
                  disabled={transliterateLoading || !transliterateInput.trim()}
                  onClick={handleTransliterate}
                >
                  {transliterateLoading ? "Converting..." : "Transliterate"}
                </button>
              </div>

              {transliterateResult && (
                <div className={styles.nlpTransliterationBox} style={{ marginTop: "0.75rem" }}>
                  <span className={styles.nlpTransliterationLabel}>Transliterated Output:</span>
                  <span className={styles.nlpTransliterationText}>{transliterateResult}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* TAB 6: Translation & Caching (Phase 6) */}
        {activeTab === "translation" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Translation Engine, Multi-Recipient Fan-Out & Show Original (Section 1, 4, 13, 25, 26, 47, 51)
              </h2>
              <p className={styles.sectionSubtitle}>
                Write in your language. Read in your language. The original message is always preserved as the immutable
                source of truth. Translations exist purely as a display layer with Redis caching, multi-recipient fan-out optimization,
                and user-controlled "Show Original / Show Translation" toggles.
              </p>
            </div>

            {transError && (
              <div className={styles.errorBox} role="alert">
                {transError}
              </div>
            )}

            {/* Multi-Recipient Fan-Out & Show Original Simulator */}
            <div className={styles.profileCard}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Multi-Recipient Fan-Out & Display-Layer Simulator</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Demonstration of Section 1 and Section 13: Sender sends once in English.
                The system fans out translations to Hindi, Gujarati, Urdu (RTL), and Spanish.
                Each recipient has independent control to switch between "Show Original" and "Show Translation".
              </p>

              <div className={styles.simContainer}>
                {/* Sender Banner */}
                <div className={styles.simSenderBanner}>
                  <div>
                    <span className={styles.simSenderLabel}>Sender: User B (@user_b · Preferred Chat Lang: English)</span>
                    <div className={styles.simSenderText}>"Are you coming tomorrow?"</div>
                  </div>
                  <span className={styles.nlpPill} style={{ backgroundColor: "#e0f2fe", color: "#0369a1" }}>
                    Source of Truth: Original Stored
                  </span>
                </div>

                {/* Recipient Cards Grid */}
                <div className={styles.simRecipientGrid}>
                  {/* Recipient 1: Hindi */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>User A</span>
                      <span className={styles.simRecipientPref}>Prefers Hindi (hi)</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        {simShowOriginal.user_hi ? "Are you coming tomorrow?" : "क्या आप कल आ रहे हैं?"}
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>
                          {simShowOriginal.user_hi ? "Original (EN)" : "Translated (HI)"}
                        </span>
                        <button
                          type="button"
                          className={styles.simToggleBtn}
                          onClick={() => toggleSimOriginal("user_hi")}
                        >
                          {simShowOriginal.user_hi ? "Show Translation" : "Show Original"}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 2: Gujarati */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>User C</span>
                      <span className={styles.simRecipientPref}>Prefers Gujarati (gu)</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        {simShowOriginal.user_gu ? "Are you coming tomorrow?" : "શું તમે કાલે આવી રહ્યા છો?"}
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>
                          {simShowOriginal.user_gu ? "Original (EN)" : "Translated (GU)"}
                        </span>
                        <button
                          type="button"
                          className={styles.simToggleBtn}
                          onClick={() => toggleSimOriginal("user_gu")}
                        >
                          {simShowOriginal.user_gu ? "Show Translation" : "Show Original"}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 3: Urdu (RTL) */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>User D</span>
                      <span className={styles.simRecipientPref}>Prefers Urdu (ur · RTL)</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span
                        className={`${styles.simBubbleText} ${
                          !simShowOriginal.user_ur ? styles.simRtlText : ""
                        }`}
                      >
                        {simShowOriginal.user_ur ? "Are you coming tomorrow?" : "کیا آپ کل آ رہے ہیں؟"}
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>
                          {simShowOriginal.user_ur ? "Original (EN)" : "Translated (UR)"}
                        </span>
                        <button
                          type="button"
                          className={styles.simToggleBtn}
                          onClick={() => toggleSimOriginal("user_ur")}
                        >
                          {simShowOriginal.user_ur ? "Show Translation" : "Show Original"}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Recipient 4: Spanish */}
                  <div className={styles.simRecipientCard}>
                    <div className={styles.simRecipientHeader}>
                      <span className={styles.simRecipientName}>User E</span>
                      <span className={styles.simRecipientPref}>Prefers Spanish (es)</span>
                    </div>
                    <div className={styles.simRecipientBubble}>
                      <span className={styles.simBubbleText}>
                        {simShowOriginal.user_es ? "Are you coming tomorrow?" : "¿Vienes mañana?"}
                      </span>
                      <div className={styles.simToggleRow}>
                        <span>
                          {simShowOriginal.user_es ? "Original (EN)" : "Translated (ES)"}
                        </span>
                        <button
                          type="button"
                          className={styles.simToggleBtn}
                          onClick={() => toggleSimOriginal("user_es")}
                        >
                          {simShowOriginal.user_es ? "Show Translation" : "Show Original"}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Direct Translation Playground & Cache Inspector */}
            <div className={styles.profileCard}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Translation Engine & Redis Cache Inspector</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Test any language pair or click a preset. The second time any text is translated, it resolves instantly from Redis cache.
              </p>

              {/* Presets */}
              <div className={styles.nlpPresetRow}>
                {TRANSLATION_PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    className={styles.nlpPresetBtn}
                    onClick={() => handleTransPresetClick(p)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Input, Source/Target selectors & Action */}
              <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  className={styles.nlpTextarea}
                  value={transInput}
                  onChange={(e) => setTransInput(e.target.value)}
                  placeholder="Enter text to translate..."
                  rows={2}
                />

                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>From:</span>
                    <select
                      className={styles.textInput}
                      value={transSourceLang}
                      onChange={(e) => setTransSourceLang(e.target.value)}
                      style={{ padding: "4px 8px", fontSize: "0.8125rem" }}
                    >
                      {languages.map((l) => (
                        <option key={l.code} value={l.code}>
                          {l.name} ({l.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>To:</span>
                    <select
                      className={styles.textInput}
                      value={transTargetLang}
                      onChange={(e) => setTransTargetLang(e.target.value)}
                      style={{ padding: "4px 8px", fontSize: "0.8125rem" }}
                    >
                      {languages.map((l) => (
                        <option key={l.code} value={l.code}>
                          {l.name} ({l.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <button
                    type="button"
                    className={styles.submitBtn}
                    disabled={transLoading || !transInput.trim()}
                    onClick={() => handleTranslateDirect()}
                    style={{ marginLeft: "auto" }}
                  >
                    {transLoading ? "Translating..." : "Translate Text"}
                  </button>
                </div>
              </div>

              {/* Result display */}
              {transResult && (
                <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div className={styles.nlpStatGrid}>
                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Cache Status</span>
                      <span className={styles.nlpStatValue}>
                        <span
                          className={`${styles.cacheBadge} ${
                            transResult.is_cached ? styles.cacheBadgeHit : styles.cacheBadgeMiss
                          }`}
                        >
                          {transResult.is_cached ? "⚡ CACHE HIT (Redis)" : "🌐 CACHE MISS (Provider)"}
                        </span>
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Engine Provider</span>
                      <span className={styles.nlpStatValue}>
                        {transResult.provider}
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Confidence</span>
                      <span className={styles.nlpStatValue}>
                        {Math.round(transResult.confidence * 100)}%
                      </span>
                    </div>

                    <div className={styles.nlpStatCard}>
                      <span className={styles.nlpStatLabel}>Pair</span>
                      <span className={styles.nlpStatValue}>
                        {transResult.source_language.toUpperCase()} &rarr; {transResult.target_language.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Output Box */}
                  <div className={styles.nlpTransliterationBox} style={{ backgroundColor: "#f8fafc", borderColor: "#cbd5e1" }}>
                    <span className={styles.nlpTransliterationLabel} style={{ color: "#334155" }}>
                      Translated Output ({transResult.target_language.toUpperCase()}):
                    </span>
                    <span
                      className={styles.nlpTransliterationText}
                      style={{
                        color: "#0f172a",
                        direction: ["ur", "ar", "fa"].includes(transResult.target_language.toLowerCase()) ? "rtl" : "ltr",
                        textAlign: ["ur", "ar", "fa"].includes(transResult.target_language.toLowerCase()) ? "right" : "left",
                      }}
                    >
                      {transResult.translated_text || "—"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* TAB 1: Initial Avatars */}
        {activeTab === "avatars" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>Initial-Based Avatars (Section 8)</h2>
              <p className={styles.sectionSubtitle}>
                No profile photos are permitted in VaaniLink. Initial-based avatars are
                generated deterministically from user display names with color hash mapping.
              </p>
            </div>

            <div className={styles.avatarRow}>
              <div className={styles.avatarDemoItem}>
                <UserAvatar name="Deepak Tirole" size="xl" isOnline={true} />
                <span className={styles.avatarCaption}>Deepak Tirole → DT (Online, XL)</span>
              </div>
              <div className={styles.avatarDemoItem}>
                <UserAvatar name="John Smith" size="lg" isOnline={false} />
                <span className={styles.avatarCaption}>John Smith → JS (Offline, LG)</span>
              </div>
              <div className={styles.avatarDemoItem}>
                <UserAvatar name="Meet Patel" size="md" isOnline={true} />
                <span className={styles.avatarCaption}>Meet Patel → MP (MD)</span>
              </div>
              <div className={styles.avatarDemoItem}>
                <UserAvatar name="Aarav Sharma" size="sm" isOnline={false} />
                <span className={styles.avatarCaption}>Aarav Sharma → AS (SM)</span>
              </div>
            </div>

            <div className={styles.inputGroup} style={{ maxWidth: 360 }}>
              <label className={styles.inputLabel}>Try Live Name Input:</label>
              <input
                type="text"
                className={styles.textInput}
                value={demoName}
                onChange={(e) => setDemoName(e.target.value)}
                placeholder="Enter any name..."
              />
              <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 12 }}>
                <UserAvatar name={demoName || "VL"} size="lg" isOnline={true} />
                <span>
                  Initials: <strong>{demoName ? demoName.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2) : "VL"}</strong>
                </span>
              </div>
            </div>
          </section>
        )}

        {/* TAB 2: Language Registry & RTL */}
        {activeTab === "languages" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Database-Driven Language Registry & RTL (Section 6 & 7)
              </h2>
              <p className={styles.sectionSubtitle}>
                VaaniLink separates Interface Language (UI menus) from Preferred Chat
                Language (message translations). Over 37 Indian and international languages
                are supported with complete script and RTL awareness.
              </p>
            </div>

            <div className={styles.formGrid}>
              <LanguageSelector
                label="Interface Language (Menu Navigation)"
                languages={languages}
                selectedCode={interfaceLang}
                onSelect={(lang) => {
                  setInterfaceLang(lang.code);
                  if (currentUser) handleUpdateLanguages(lang.code, undefined);
                }}
              />

              <LanguageSelector
                label="Preferred Chat Language (Incoming Translation)"
                languages={languages}
                selectedCode={preferredChatLang}
                onSelect={(lang) => {
                  setPreferredChatLang(lang.code);
                  if (currentUser) handleUpdateLanguages(undefined, lang.code);
                }}
              />
            </div>

            {/* RTL Demonstration Card */}
            {(() => {
              const selectedObj = languages.find((l) => l.code === preferredChatLang);
              const isRtl = selectedObj?.is_rtl || false;
              return (
                <div
                  style={{
                    backgroundColor: "var(--color-bg-base)",
                    padding: "var(--space-4)",
                    borderRadius: "var(--radius-lg)",
                    border: "1px solid var(--color-border)",
                    direction: isRtl ? "rtl" : "ltr",
                  }}
                >
                  <p style={{ fontWeight: 600, marginBottom: 4 }}>
                    Active Preferred Language: {selectedObj?.name} ({selectedObj?.native_name})
                  </p>
                  <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                    Script: {selectedObj?.script_code} | Direction: {isRtl ? "Right-to-Left (RTL)" : "Left-to-Right (LTR)"}
                  </p>
                  {isRtl && (
                    <p style={{ marginTop: 8, color: "var(--color-primary)", fontWeight: 500 }}>
                      مرحبا بكم في فاني لينك (Text aligns to the right automatically based on language metadata)
                    </p>
                  )}
                </div>
              );
            })()}
          </section>
        )}

        {/* TAB 3: Accounts & Settings */}
        {activeTab === "auth" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Authentication & Current User Profile (Section 8, 9, 37, 38)
              </h2>
              <p className={styles.sectionSubtitle}>
                Registration, Login, JWT tokens with rotation, and decoupled language settings.
              </p>
            </div>

            {authError && (
              <div className={styles.errorBox} role="alert">
                <strong>{authError.error.code}:</strong> {authError.error.message}
                {authError.error.fields && (
                  <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                    {Object.entries(authError.error.fields).map(([field, msgs]) => (
                      <li key={field}>{field}: {msgs.join(", ")}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {authSuccess && (
              <div className={styles.successBox} role="status">
                {authSuccess}
              </div>
            )}

            {currentUser ? (
              <div className={styles.profileCard}>
                <div className={styles.profileHeader}>
                  <UserAvatar name={currentUser.display_name} size="lg" isOnline={true} />
                  <div className={styles.profileMeta}>
                    <span className={styles.profileName}>{currentUser.display_name}</span>
                    <span className={styles.profileUsername}>@{currentUser.username} · {currentUser.email}</span>
                  </div>
                </div>

                <div className={styles.profileDetailsGrid}>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Interface Language</span>
                    <span className={styles.detailValue}>
                      {currentUser.interface_language?.name || "English"} ({currentUser.interface_language?.native_name || "English"})
                    </span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Preferred Chat Language</span>
                    <span className={styles.detailValue}>
                      {currentUser.preferred_chat_language?.name || "Hindi"} ({currentUser.preferred_chat_language?.native_name || "हिन्दी"})
                    </span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Account ID</span>
                    <span className={styles.detailValue} style={{ fontSize: "0.75rem", fontFamily: "var(--font-family-mono)" }}>
                      {currentUser.id}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  className={styles.submitBtn}
                  style={{ backgroundColor: "var(--color-danger)" }}
                  onClick={handleLogout}
                >
                  Log Out
                </button>
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
                  <button
                    type="button"
                    className={`${styles.tabBtn} ${authMode === "register" ? styles.tabBtnActive : ""}`}
                    onClick={() => setAuthMode("register")}
                  >
                    Register
                  </button>
                  <button
                    type="button"
                    className={`${styles.tabBtn} ${authMode === "login" ? styles.tabBtnActive : ""}`}
                    onClick={() => setAuthMode("login")}
                  >
                    Login
                  </button>
                </div>

                <form onSubmit={authMode === "register" ? handleRegister : handleLogin} className={styles.formGrid}>
                  <div className={styles.inputGroup}>
                    <label className={styles.inputLabel}>Username</label>
                    <input
                      type="text"
                      className={styles.textInput}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                    />
                  </div>

                  {authMode === "register" && (
                    <>
                      <div className={styles.inputGroup}>
                        <label className={styles.inputLabel}>Display Name</label>
                        <input
                          type="text"
                          className={styles.textInput}
                          value={displayName}
                          onChange={(e) => setDisplayName(e.target.value)}
                          required
                        />
                      </div>

                      <div className={styles.inputGroup}>
                        <label className={styles.inputLabel}>Email Address</label>
                        <input
                          type="email"
                          className={styles.textInput}
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          required
                        />
                      </div>
                    </>
                  )}

                  <div className={styles.inputGroup}>
                    <label className={styles.inputLabel}>Password</label>
                    <input
                      type="password"
                      className={styles.textInput}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>

                  <div style={{ gridColumn: "1 / -1", marginTop: 8 }}>
                    <button type="submit" className={styles.submitBtn} disabled={isLoading}>
                      {isLoading ? "Processing..." : authMode === "register" ? "Create Account" : "Log In"}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </section>
        )}

        {/* TAB 9: Chat UX, a11y & Lifecycle (Phase 9) */}
        {activeTab === "chat_ux" && (
          <section className={styles.section}>
            <div>
              <h2 className={styles.sectionTitle}>
                Chat UX, Accessibility, RTL & Lifecycle Enhancements (Phase 9)
              </h2>
              <p className={styles.sectionSubtitle}>
                Unicode emoji picker, quoted replies with smooth scroll, edit own messages with version tracking, soft-delete for everyone with tombstones, dynamic RTL text alignment, reconnection states, and WCAG a11y compliance.
              </p>
            </div>

            {/* Sub-section 1: Native Unicode Emoji Picker Sandbox */}
            <div className={styles.uxDemoCard}>
              <div className={styles.uxDemoHeader}>
                <span>1. Unicode Emoji Picker Sandbox</span>
                <button
                  type="button"
                  className={styles.uxActionBtn}
                  onClick={() => setShowUxEmojiPicker((prev) => !prev)}
                  aria-expanded={showUxEmojiPicker}
                  aria-label="Toggle emoji picker demo"
                >
                  😊 {showUxEmojiPicker ? "Close Emoji Picker" : "Open Emoji Picker"}
                </button>
              </div>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Lightweight, native Unicode emoji selector organized by 7 categories (Smileys, Gestures, Hearts, Animals, Food, Travel, Symbols) with fast category search and keyboard navigation.
              </p>

              <div style={{ position: "relative" }}>
                {showUxEmojiPicker && (
                  <EmojiPicker
                    onSelectEmoji={(emoji) => {
                      setUxEmojiSandbox((prev) => prev + " " + emoji);
                    }}
                    onClose={() => setShowUxEmojiPicker(false)}
                  />
                )}
                <textarea
                  className={styles.textInput}
                  rows={2}
                  value={uxEmojiSandbox}
                  onChange={(e) => setUxEmojiSandbox(e.target.value)}
                  placeholder="Type or click the emoji picker to insert emojis..."
                  aria-label="Emoji test sandbox"
                />
              </div>
            </div>

            {/* Sub-section 2: Message Lifecycle (Replies, Edits, Deletes) Interactive Timeline */}
            <div className={styles.uxDemoCard}>
              <div className={styles.uxDemoHeader}>
                <span>2. Message Lifecycle (Replies, Edits & Soft-Deletes)</span>
                <div className={styles.uxButtonGroup}>
                  <button
                    type="button"
                    className={styles.uxActionBtn}
                    onClick={() => {
                      setUxDemoMessages((prev) =>
                        prev.map((m) =>
                          m.id === "demo-2"
                            ? {
                                ...m,
                                original_text: "Haan bilkul, main 1:30 baje pahunchunga! ✨ (Edited)",
                                version: m.version + 1,
                                edited_at: new Date().toISOString(),
                              }
                            : m
                        )
                      );
                    }}
                  >
                    ✏️ Edit Message #2
                  </button>
                  <button
                    type="button"
                    className={styles.uxActionBtn}
                    onClick={() => {
                      setUxDemoMessages((prev) =>
                        prev.map((m) =>
                          m.id === "demo-2"
                            ? {
                                ...m,
                                text: "This message was deleted.",
                                deleted_at: new Date().toISOString(),
                              }
                            : m
                        )
                      );
                    }}
                  >
                    🗑️ Delete Message #2
                  </button>
                  <button
                    type="button"
                    className={styles.uxActionBtn}
                    onClick={() => {
                      setUxDemoMessages((prev) => [
                        ...prev,
                        {
                          id: `demo-${Date.now()}`,
                          conversation_id: "demo-conv",
                          sender: { id: "u1", username: "priya_sharma", display_name: "Priya Sharma" },
                          client_message_id: `client-${Date.now()}`,
                          sequence_number: prev.length + 1,
                          text: "Great! Looking forward to seeing everyone.",
                          original_text: "Great! Looking forward to seeing everyone.",
                          status: "DELIVERED",
                          detected_primary_language: "en",
                          detected_script: "Latn",
                          reply_to_message_id: "demo-2",
                          reply_to: {
                            id: "demo-2",
                            sender_name: "Deepak Tirole",
                            text: prev.find((m) => m.id === "demo-2")?.original_text || "Reply",
                          },
                          version: 1,
                          edited_at: null,
                          deleted_at: null,
                          created_at: new Date().toISOString(),
                        },
                      ]);
                    }}
                  >
                    ↩️ Add Reply to #2
                  </button>
                  <button
                    type="button"
                    className={styles.uxActionBtn}
                    onClick={() => {
                      setUxDemoMessages([
                        {
                          id: "demo-1",
                          conversation_id: "demo-conv",
                          sender: { id: "u1", username: "priya_sharma", display_name: "Priya Sharma" },
                          client_message_id: "client-1",
                          sequence_number: 1,
                          text: "Are you coming to the team lunch tomorrow?",
                          original_text: "Are you coming to the team lunch tomorrow?",
                          status: "SEEN",
                          detected_primary_language: "en",
                          detected_script: "Latn",
                          reply_to_message_id: null,
                          version: 1,
                          edited_at: null,
                          deleted_at: null,
                          created_at: new Date(Date.now() - 3600000).toISOString(),
                        },
                        {
                          id: "demo-2",
                          conversation_id: "demo-conv",
                          sender: { id: "u2", username: "deepak_tirole", display_name: "Deepak Tirole" },
                          client_message_id: "client-2",
                          sequence_number: 2,
                          text: "Haan bilkul, main 1 baje pahunchunga! 🎉",
                          original_text: "Haan bilkul, main 1 baje pahunchunga! 🎉",
                          status: "SEEN",
                          detected_primary_language: "hi",
                          detected_script: "Latn",
                          is_romanized: true,
                          is_mixed_language: true,
                          reply_to_message_id: "demo-1",
                          reply_to: {
                            id: "demo-1",
                            sender_name: "Priya Sharma",
                            text: "Are you coming to the team lunch tomorrow?",
                          },
                          version: 2,
                          edited_at: new Date(Date.now() - 1800000).toISOString(),
                          deleted_at: null,
                          created_at: new Date(Date.now() - 1800000).toISOString(),
                        },
                        {
                          id: "demo-3",
                          conversation_id: "demo-conv",
                          sender: { id: "u3", username: "tariq_ahmad", display_name: "Tariq Ahmad" },
                          client_message_id: "client-3",
                          sequence_number: 3,
                          text: "ان شاء اللہ، میں بھی وقت پر آؤں گا۔",
                          original_text: "ان شاء اللہ، میں بھی وقت پر آؤں گا۔",
                          status: "DELIVERED",
                          detected_primary_language: "ur",
                          detected_script: "Arab",
                          reply_to_message_id: null,
                          version: 1,
                          edited_at: null,
                          deleted_at: null,
                          created_at: new Date(Date.now() - 900000).toISOString(),
                        },
                        {
                          id: "demo-4",
                          conversation_id: "demo-conv",
                          sender: { id: "u2", username: "deepak_tirole", display_name: "Deepak Tirole" },
                          client_message_id: "client-4",
                          sequence_number: 4,
                          text: "This message was deleted.",
                          original_text: "Old message that was deleted",
                          status: "SEEN",
                          reply_to_message_id: null,
                          version: 1,
                          edited_at: null,
                          deleted_at: new Date(Date.now() - 300000).toISOString(),
                          created_at: new Date(Date.now() - 400000).toISOString(),
                        },
                      ]);
                    }}
                  >
                    🔄 Reset Demo
                  </button>
                </div>
              </div>

              {/* Render MessageTimeline inside showcase */}
              <div style={{ height: "340px", display: "flex", flexDirection: "column" }}>
                <MessageTimeline
                  messages={uxDemoMessages}
                  currentUserId="u2"
                  preferredChatLanguage="en"
                  onReplyMessage={(msg) => {
                    alert(`Reply triggered for message #${msg.sequence_number} from ${msg.sender.display_name}`);
                  }}
                  onEditMessage={(msg) => {
                    const newText = prompt("Edit message:", msg.original_text);
                    if (newText && newText.trim()) {
                      setUxDemoMessages((prev) =>
                        prev.map((m) =>
                          m.id === msg.id
                            ? {
                                ...m,
                                original_text: newText.trim(),
                                version: m.version + 1,
                                edited_at: new Date().toISOString(),
                              }
                            : m
                        )
                      );
                    }
                  }}
                  onDeleteMessage={(msgId) => {
                    setUxDemoMessages((prev) =>
                      prev.map((m) =>
                        m.id === msgId
                          ? {
                              ...m,
                              text: "This message was deleted.",
                              deleted_at: new Date().toISOString(),
                            }
                          : m
                      )
                    );
                  }}
                />
              </div>
            </div>

            {/* Sub-section 3: RTL Multilingual Direction Matrix */}
            <div className={styles.uxDemoCard}>
              <div className={styles.uxDemoHeader}>
                <span>3. Right-to-Left (RTL) Typography & Script Alignment</span>
              </div>
              <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                Conforms strictly to Section 7 & 48. When detected script is <code>Arab</code> or <code>Hebr</code>, message containers dynamically apply <code>dir="rtl"</code> with reversed punctuation and right-aligned reading direction.
              </p>

              <div className={styles.rtlCompareGrid}>
                <div className={styles.rtlCompareCard}>
                  <div className={styles.rtlCompareHeader}>
                    <span>Arabic (العربية)</span>
                    <span>dir="rtl" · Script: Arab</span>
                  </div>
                  <div className={styles.rtlSampleText} dir="rtl">
                    مرحباً بكم في فاني لينك! اكتب بلغتك، واقرأ بلغتك.
                  </div>
                </div>

                <div className={styles.rtlCompareCard}>
                  <div className={styles.rtlCompareHeader}>
                    <span>Urdu (اردو)</span>
                    <span>dir="rtl" · Script: Arab</span>
                  </div>
                  <div className={styles.rtlSampleText} dir="rtl">
                    وانی لنک میں خوش آمدید! اپنی زبان میں لکھیں، اپنی زبان میں پڑھیں۔
                  </div>
                </div>

                <div className={styles.rtlCompareCard}>
                  <div className={styles.rtlCompareHeader}>
                    <span>Persian (فارسی)</span>
                    <span>dir="rtl" · Script: Arab</span>
                  </div>
                  <div className={styles.rtlSampleText} dir="rtl">
                    به وانی‌لینک خوش آمدید! به زبان خود بنویسید، به زبان خود بخوانید.
                  </div>
                </div>

                <div className={styles.rtlCompareCard}>
                  <div className={styles.rtlCompareHeader}>
                    <span>Hindi (Devanagari)</span>
                    <span>dir="ltr" · Script: Deva</span>
                  </div>
                  <div className={styles.rtlSampleText} dir="ltr">
                    वाणीलिंक में आपका स्वागत है! अपनी भाषा में लिखें, अपनी भाषा में पढ़ें।
                  </div>
                </div>
              </div>
            </div>

            {/* Sub-section 4: Accessibility (a11y) Conformance Audit */}
            <div className={styles.uxDemoCard}>
              <div className={styles.uxDemoHeader}>
                <span>4. Accessibility (WCAG 2.1 AA) Conformance Highlights</span>
              </div>

              <div className={styles.a11yGrid}>
                <div className={styles.a11yCard}>
                  <span className={styles.a11yCardTitle}>
                    <span>♿</span> Semantic Landmarks
                  </span>
                  <span className={styles.a11yCardDesc}>
                    Message timeline uses <code>role="log"</code> with <code>aria-live="polite"</code> for screen reader live chat streaming.
                  </span>
                </div>

                <div className={styles.a11yCard}>
                  <span className={styles.a11yCardTitle}>
                    <span>⌨️</span> Keyboard Navigation
                  </span>
                  <span className={styles.a11yCardDesc}>
                    Press <code>Enter</code> to send, <code>Shift+Enter</code> for multiline, <code>Escape</code> to dismiss replies, edits, and emoji picker.
                  </span>
                </div>

                <div className={styles.a11yCard}>
                  <span className={styles.a11yCardTitle}>
                    <span>🏷️</span> Accessible Names
                  </span>
                  <span className={styles.a11yCardDesc}>
                    Explicit <code>aria-label</code> on all interactive controls including Send, Reply, Edit, Delete, Info, and Emoji category tabs.
                  </span>
                </div>

                <div className={styles.a11yCard}>
                  <span className={styles.a11yCardTitle}>
                    <span>🎯</span> Touch & Contrast Targets
                  </span>
                  <span className={styles.a11yCardDesc}>
                    Touch targets exceed minimum 40px dimensions with high contrast text ratios exceeding 4.5:1 on light and dark backgrounds.
                  </span>
                </div>
              </div>
            </div>
          </section>
        )}

        <footer className={styles.footer}>
          Phase 9 Complete: Chat UX, Native Emoji Picker, Replies, Edit & Soft-Delete Lifecycle, RTL Typography, Reconnecting States, Responsive Mobile Layout & WCAG a11y verified.
        </footer>
      </div>
    </main>
  );
};
