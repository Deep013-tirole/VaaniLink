import React, { useEffect, useRef, useState } from "react";
import styles from "./MessageTimeline.module.css";
import { UserAvatar } from "@/components/UserAvatar";
import { Message, MessageInfo, TypingUser } from "@/types";
import { submitTranslationFeedback } from "@/api/translation";
import { getMessageInfo } from "@/api/messages";

export interface MessageTimelineProps {
  messages: Message[];
  currentUserId: string;
  typingUsers?: TypingUser[];
  preferredChatLanguage?: string;
  onReplyMessage?: (message: Message) => void;
  onEditMessage?: (message: Message) => void;
  onDeleteMessage?: (messageId: string) => void;
}

const isRTLText = (lang?: string | null, script?: string | null): boolean => {
  if (!lang && !script) return false;
  const rtlLangs = ["ar", "ur", "fa", "he", "ps", "sd", "ug", "yi"];
  const rtlScripts = ["Arab", "Hebr", "Thaa", "Mand"];
  if (lang && rtlLangs.includes(lang.toLowerCase())) return true;
  if (script && rtlScripts.includes(script)) return true;
  return false;
};

export const MessageTimeline: React.FC<MessageTimelineProps> = ({
  messages,
  currentUserId,
  typingUsers = [],
  preferredChatLanguage = "en",
  onReplyMessage,
  onEditMessage,
  onDeleteMessage,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showOriginalMap, setShowOriginalMap] = useState<Record<string, boolean>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<string, 1 | -1>>({});

  // Message Info Modal State (Phase 7)
  const [messageInfo, setMessageInfo] = useState<MessageInfo | null>(null);
  const [infoLoading, setInfoLoading] = useState<boolean>(false);
  const [infoError, setInfoError] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingUsers]);

  const toggleShowOriginal = (msgId: string) => {
    setShowOriginalMap((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleFeedback = async (translationId: string, rating: 1 | -1) => {
    try {
      await submitTranslationFeedback(translationId, rating);
      setFeedbackMap((prev) => ({ ...prev, [translationId]: rating }));
    } catch {
      // Degraded feedback mode
    }
  };

  const handleOpenMessageInfo = async (msgId: string) => {
    setInfoLoading(true);
    setInfoError(null);
    try {
      const data = await getMessageInfo(msgId);
      setMessageInfo(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load message receipt details.";
      setInfoError(msg);
    } finally {
      setInfoLoading(false);
    }
  };

  const scrollToMessage = (msgId: string) => {
    const elem = document.getElementById(`msg-${msgId}`);
    if (elem) {
      elem.scrollIntoView({ behavior: "smooth", block: "center" });
      elem.style.transition = "background-color 0.3s ease";
      elem.style.backgroundColor = "rgba(59, 130, 246, 0.15)";
      setTimeout(() => {
        elem.style.backgroundColor = "";
      }, 1200);
    }
  };

  const handleDeleteClick = (msgId: string) => {
    if (window.confirm("Delete this message for everyone?")) {
      onDeleteMessage?.(msgId);
    }
  };

  const renderStatusIcon = (status: string, seq: number) => {
    if (status === "SEEN") {
      return (
        <span
          className={`${styles.statusIndicator} ${styles.statusSeen}`}
          title={`Status: Seen (Seq: ${seq})`}
        >
          ✓✓
        </span>
      );
    }
    if (status === "DELIVERED") {
      return (
        <span
          className={styles.statusIndicator}
          title={`Status: Delivered (Seq: ${seq})`}
        >
          ✓✓
        </span>
      );
    }
    return (
      <span
        className={styles.statusIndicator}
        title={`Status: Sent (Seq: ${seq})`}
      >
        ✓
      </span>
    );
  };

  const getLanguageLabel = (msg: Message): string => {
    if (msg.is_romanized && msg.detected_primary_language === "hi") {
      return "Hinglish";
    }
    if (msg.detected_primary_language === "hi") return "Hindi";
    if (msg.detected_primary_language === "en") return "English";
    if (msg.detected_primary_language === "gu") return "Gujarati";
    if (msg.detected_primary_language === "mr") return "Marathi";
    if (msg.detected_primary_language === "bn") return "Bengali";
    if (msg.detected_primary_language === "ur") return "Urdu";
    if (msg.detected_primary_language === "ar") return "Arabic";
    if (msg.detected_primary_language === "fa") return "Persian";
    return msg.detected_primary_language?.toUpperCase() || "";
  };

  return (
    <div className={styles.timelineContainer} role="log" aria-label="Message history">
      {messages.length === 0 ? (
        <div className={styles.emptyTimeline}>
          No messages yet. Send a message to start the conversation!
        </div>
      ) : (
        messages.map((msg) => {
          const isOutgoing = msg.sender.id === currentUserId;
          const isDeleted = Boolean(msg.deleted_at || msg.text === "This message was deleted.");
          const langLabel = getLanguageLabel(msg);

          // Find translation matching viewer's preferred chat language
          const targetCode = preferredChatLanguage.toLowerCase();
          const activeTranslation = !isDeleted
            ? msg.translations?.find((t) => t.target_language.toLowerCase() === targetCode)
            : undefined;

          const isTranslationAvailable =
            activeTranslation &&
            activeTranslation.status === "COMPLETED" &&
            activeTranslation.translated_text;

          const isShowingOriginal = showOriginalMap[msg.id] ?? false;

          // Determine display text:
          // If translation exists and user hasn't toggled to original -> show translated text!
          // Otherwise show original_text.
          const displayText = isDeleted
            ? "This message was deleted."
            : isTranslationAvailable && !isShowingOriginal
            ? activeTranslation.translated_text
            : msg.original_text;

          // RTL detection:
          const isRTL =
            !isDeleted &&
            (isTranslationAvailable && !isShowingOriginal
              ? isRTLText(activeTranslation.target_language)
              : isRTLText(msg.detected_primary_language, msg.detected_script));

          return (
            <div
              key={msg.id}
              id={`msg-${msg.id}`}
              className={`${styles.messageRow} ${
                isOutgoing ? styles.rowOutgoing : styles.rowIncoming
              }`}
            >
              {!isOutgoing && (
                <UserAvatar name={msg.sender.display_name} size="sm" />
              )}

              <div className={styles.messageWrapper}>
                {/* Floating Quick Action Buttons on Hover/Focus */}
                {!isDeleted && (
                  <div
                    className={styles.messageActions}
                    role="toolbar"
                    aria-label="Message actions"
                  >
                    <button
                      type="button"
                      className={styles.actionBtn}
                      onClick={() => onReplyMessage?.(msg)}
                      title="Reply"
                      aria-label="Reply to message"
                    >
                      ↩️
                    </button>
                    {isOutgoing && (
                      <>
                        <button
                          type="button"
                          className={styles.actionBtn}
                          onClick={() => onEditMessage?.(msg)}
                          title="Edit"
                          aria-label="Edit message"
                        >
                          ✏️
                        </button>
                        <button
                          type="button"
                          className={`${styles.actionBtn} ${styles.actionBtnDelete}`}
                          onClick={() => handleDeleteClick(msg.id)}
                          title="Delete for everyone"
                          aria-label="Delete message for everyone"
                        >
                          🗑️
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className={styles.actionBtn}
                      onClick={() => handleOpenMessageInfo(msg.id)}
                      title="Message info"
                      aria-label="View delivery and read receipts"
                    >
                      ℹ️
                    </button>
                  </div>
                )}

                <div
                  className={`${styles.bubble} ${
                    isOutgoing ? styles.bubbleOutgoing : styles.bubbleIncoming
                  } ${isDeleted ? styles.bubbleDeleted : ""}`}
                >
                  {!isOutgoing && !isDeleted && (
                    <span className={styles.senderName}>{msg.sender.display_name}</span>
                  )}

                  {/* Quoted Replying Preview Bubble */}
                  {msg.reply_to && !isDeleted && (
                    <div
                      className={styles.replyQuoteBox}
                      onClick={() => scrollToMessage(msg.reply_to!.id)}
                      role="button"
                      tabIndex={0}
                      title="Click to jump to quoted message"
                      aria-label={`Jump to replied message from ${msg.reply_to.sender_name}`}
                    >
                      <span className={styles.replySender}>{msg.reply_to.sender_name}</span>
                      <span className={styles.replySnippet}>{msg.reply_to.text}</span>
                    </div>
                  )}

                  {/* Message Content */}
                  {isDeleted ? (
                    <span className={styles.deletedText} aria-label="Deleted message">
                      🚫 <em>This message was deleted.</em>
                    </span>
                  ) : (
                    <span
                      className={`${styles.messageText} ${isRTL ? styles.rtlText : ""}`}
                      dir={isRTL ? "rtl" : "ltr"}
                    >
                      {displayText}
                    </span>
                  )}

                  {/* Translation banner & Show Original toggle (Section 13, 51) */}
                  {!isDeleted && isTranslationAvailable && (
                    <div
                      className={`${styles.translationBanner} ${
                        isOutgoing ? styles.translationBannerOutgoing : ""
                      }`}
                    >
                      <span className={styles.translationLabel}>
                        {!isShowingOriginal ? (
                          <>
                            <span>🌐 Translated ({activeTranslation.target_language.toUpperCase()})</span>
                            <span>·</span>
                            <button
                              type="button"
                              className={styles.translationToggleBtn}
                              onClick={() => toggleShowOriginal(msg.id)}
                            >
                              Show Original
                            </button>
                          </>
                        ) : (
                          <>
                            <span>Original ({msg.detected_primary_language?.toUpperCase() || "SRC"})</span>
                            <span>·</span>
                            <button
                              type="button"
                              className={styles.translationToggleBtn}
                              onClick={() => toggleShowOriginal(msg.id)}
                            >
                              Show Translation
                            </button>
                          </>
                        )}
                      </span>

                      {/* Feedback rating controls (Section 52) */}
                      <div className={styles.translationFeedbackGroup}>
                        <button
                          type="button"
                          className={`${styles.translationFeedbackBtn} ${
                            feedbackMap[activeTranslation.id] === 1
                              ? styles.translationFeedbackActive
                              : ""
                          }`}
                          title="Translation is accurate (+1)"
                          onClick={() => handleFeedback(activeTranslation.id, 1)}
                        >
                          👍
                        </button>
                        <button
                          type="button"
                          className={`${styles.translationFeedbackBtn} ${
                            feedbackMap[activeTranslation.id] === -1
                              ? styles.translationFeedbackActive
                              : ""
                          }`}
                          title="Translation is inaccurate (-1)"
                          onClick={() => handleFeedback(activeTranslation.id, -1)}
                        >
                          👎
                        </button>
                      </div>
                    </div>
                  )}

                  {/* NLP Intelligence Badges (Phase 5) */}
                  {!isDeleted && langLabel && (
                    <div className={styles.nlpBadgeRow}>
                      <span
                        className={`${styles.nlpPill} ${
                          isOutgoing ? styles.nlpPillOutgoing : styles.nlpPillIncoming
                        }`}
                        title={`Script: ${msg.detected_script || "Latn"}, Confidence: ${
                          msg.language_confidence
                            ? Math.round(msg.language_confidence * 100) + "%"
                            : "Auto"
                        }`}
                      >
                        {langLabel} · {msg.detected_script || "Latn"}
                      </span>
                      {msg.is_mixed_language && (
                        <span
                          className={`${styles.nlpPill} ${styles.nlpPillMixed}`}
                          title="Code-mixed multilingual structure detected"
                        >
                          Code-Mixed
                        </span>
                      )}
                    </div>
                  )}

                  <div
                    className={`${styles.metaRow} ${
                      isOutgoing ? styles.metaOutgoing : styles.metaIncoming
                    }`}
                  >
                    {!isDeleted && (msg.edited_at || (msg.version && msg.version > 1)) && (
                      <span className={styles.editedIndicator} title={`Edited at ${msg.edited_at || "recently"}`}>
                        (edited)
                      </span>
                    )}
                    <span>
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {isOutgoing && !isDeleted && renderStatusIcon(msg.status, msg.sequence_number)}
                  </div>
                </div>
              </div>
            </div>
          );
        })
      )}

      {/* Typing indicator */}
      {typingUsers.length > 0 && (
        <div className={styles.typingIndicatorRow} role="status" aria-live="polite">
          <span>
            {typingUsers.map((u) => u.display_name).join(", ")}{" "}
            {typingUsers.length === 1 ? "is" : "are"} typing
          </span>
          <span className={styles.typingDots} aria-hidden="true">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </div>
      )}

      {/* Message Info Modal (Phase 7: Per-member receipts & Message Info) */}
      {(messageInfo || infoLoading || infoError) && (
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="msg-info-title"
          onClick={() => {
            setMessageInfo(null);
            setInfoError(null);
          }}
        >
          <div
            className={styles.modalContainer}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3 id="msg-info-title" className={styles.modalTitle}>
                Message Info
              </h3>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => {
                  setMessageInfo(null);
                  setInfoError(null);
                }}
                aria-label="Close message info dialog"
              >
                ✕
              </button>
            </div>

            <div className={styles.modalBody}>
              {infoLoading && <div>Loading delivery and read receipts...</div>}
              {infoError && (
                <div style={{ color: "var(--color-danger)" }}>{infoError}</div>
              )}
              {messageInfo && (
                <>
                  <div className={styles.messageInfoSnippet}>
                    <div className={styles.messageInfoSnippetLabel}>
                      Original Message (Seq: #{messageInfo.sequence_number})
                    </div>
                    <div>"{messageInfo.original_text}"</div>
                  </div>

                  <div className={styles.receiptStatsGrid}>
                    <div className={styles.receiptStatCard}>
                      <div className={styles.receiptStatNum}>{messageInfo.read_count}</div>
                      <div className={styles.receiptStatLabel}>Read</div>
                    </div>
                    <div className={styles.receiptStatCard}>
                      <div className={styles.receiptStatNum}>{messageInfo.delivered_count}</div>
                      <div className={styles.receiptStatLabel}>Delivered</div>
                    </div>
                    <div className={styles.receiptStatCard}>
                      <div className={styles.receiptStatNum}>{messageInfo.pending_count}</div>
                      <div className={styles.receiptStatLabel}>Pending</div>
                    </div>
                  </div>

                  <div className={styles.receiptSection}>
                    <div className={styles.receiptSectionTitle}>
                      <span>Read By ({messageInfo.read_count})</span>
                    </div>
                    <div className={styles.receiptList}>
                      {messageInfo.read_by.length === 0 ? (
                        <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                          No members have read this message yet.
                        </div>
                      ) : (
                        messageInfo.read_by.map((item) => (
                          <div key={item.user.id} className={styles.receiptItem}>
                            <div className={styles.receiptUser}>
                              <UserAvatar name={item.user.display_name} size="sm" />
                              <div>
                                <div>{item.user.display_name}</div>
                                <div style={{ fontSize: "0.6875rem", color: "var(--color-text-muted)" }}>
                                  @{item.user.username}
                                </div>
                              </div>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <span className={`${styles.receiptStatusPill} ${styles.pillSeen}`}>
                                Read
                              </span>
                              <div className={styles.receiptTime}>
                                {new Date(item.seen_at).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  second: "2-digit",
                                })}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className={styles.receiptSection}>
                    <div className={styles.receiptSectionTitle}>
                      <span>Delivered To ({messageInfo.delivered_count})</span>
                    </div>
                    <div className={styles.receiptList}>
                      {messageInfo.delivered_to.length === 0 ? (
                        <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                          No pending delivery receipts.
                        </div>
                      ) : (
                        messageInfo.delivered_to.map((item) => (
                          <div key={item.user.id} className={styles.receiptItem}>
                            <div className={styles.receiptUser}>
                              <UserAvatar name={item.user.display_name} size="sm" />
                              <div>
                                <div>{item.user.display_name}</div>
                                <div style={{ fontSize: "0.6875rem", color: "var(--color-text-muted)" }}>
                                  @{item.user.username}
                                </div>
                              </div>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <span className={`${styles.receiptStatusPill} ${styles.pillDelivered}`}>
                                Delivered
                              </span>
                              <div className={styles.receiptTime}>
                                {new Date(item.delivered_at).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  second: "2-digit",
                                })}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
