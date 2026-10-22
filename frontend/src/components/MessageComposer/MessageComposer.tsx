import React, { useState, useRef, useEffect } from "react";
import styles from "./MessageComposer.module.css";
import { EmojiPicker } from "@/components/EmojiPicker";

export interface MessageComposerProps {
  onSendMessage: (text: string, clientMessageId: string, replyToId?: string | null) => Promise<void> | void;
  onTypingStart?: () => void;
  onTypingStop?: () => void;
  disabled?: boolean;
  placeholder?: string;
  replyingTo?: { id: string; senderName: string; text: string } | null;
  onCancelReply?: () => void;
  editingMessage?: { id: string; text: string } | null;
  onCancelEdit?: () => void;
  onSaveEdit?: (messageId: string, newText: string) => Promise<void> | void;
}

const generateUUID = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  onTypingStart,
  onTypingStop,
  disabled = false,
  placeholder = "Write a message... (Press Enter to send, Shift+Enter for new line)",
  replyingTo = null,
  onCancelReply,
  editingMessage = null,
  onCancelEdit,
  onSaveEdit,
}) => {
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimerRef = useRef<number | null>(null);

  // If entering edit mode, populate text
  useEffect(() => {
    if (editingMessage) {
      setText(editingMessage.text);
      textareaRef.current?.focus();
    }
  }, [editingMessage]);

  // If entering reply mode, focus textarea
  useEffect(() => {
    if (replyingTo) {
      textareaRef.current?.focus();
    }
  }, [replyingTo]);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        120
      )}px`;
    }
  }, [text]);

  // Clean up typing timer on unmount
  useEffect(() => {
    return () => {
      if (typingTimerRef.current) {
        window.clearTimeout(typingTimerRef.current);
      }
    };
  }, []);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);

    if (val.trim()) {
      onTypingStart?.();
      if (typingTimerRef.current) {
        window.clearTimeout(typingTimerRef.current);
      }
      typingTimerRef.current = window.setTimeout(() => {
        onTypingStop?.();
      }, 2000);
    } else {
      if (typingTimerRef.current) {
        window.clearTimeout(typingTimerRef.current);
      }
      onTypingStop?.();
    }
  };

  const handleSelectEmoji = (emoji: string) => {
    if (!textareaRef.current) {
      setText((prev) => prev + emoji);
      return;
    }
    const elem = textareaRef.current;
    const start = elem.selectionStart || text.length;
    const end = elem.selectionEnd || text.length;
    const newText = text.substring(0, start) + emoji + text.substring(end);
    setText(newText);

    // Keep focus and reposition cursor right after inserted emoji
    setTimeout(() => {
      elem.focus();
      const newPos = start + emoji.length;
      elem.setSelectionRange(newPos, newPos);
    }, 0);
  };

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (!trimmed || isSubmitting || disabled) {
      return;
    }

    if (typingTimerRef.current) {
      window.clearTimeout(typingTimerRef.current);
    }
    onTypingStop?.();
    setIsSubmitting(true);

    try {
      if (editingMessage && onSaveEdit) {
        await onSaveEdit(editingMessage.id, trimmed);
        setText("");
      } else {
        const clientMessageId = generateUUID();
        await onSendMessage(trimmed, clientMessageId, replyingTo?.id || null);
        setText("");
        onCancelReply?.();
      }
      setShowEmojiPicker(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") {
      if (showEmojiPicker) {
        setShowEmojiPicker(false);
      } else if (editingMessage) {
        onCancelEdit?.();
        setText("");
      } else if (replyingTo) {
        onCancelReply?.();
      }
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isEditing = Boolean(editingMessage);
  const isReplying = Boolean(replyingTo && !isEditing);

  return (
    <div className={styles.composerRoot}>
      {/* Reply Banner */}
      {isReplying && replyingTo && (
        <div className={styles.contextBanner} role="region" aria-label="Reply preview">
          <div className={styles.bannerContent}>
            <span className={styles.bannerIcon} aria-hidden="true">
              ↩️
            </span>
            <div className={styles.bannerTextWrapper}>
              <span className={styles.bannerTitle}>
                Replying to {replyingTo.senderName}
              </span>
              <span className={styles.bannerSnippet}>{replyingTo.text}</span>
            </div>
          </div>
          <button
            type="button"
            className={styles.bannerCloseBtn}
            onClick={onCancelReply}
            title="Cancel reply"
            aria-label="Cancel reply"
          >
            ✕
          </button>
        </div>
      )}

      {/* Edit Banner */}
      {isEditing && (
        <div className={styles.contextBanner} role="region" aria-label="Editing message">
          <div className={styles.bannerContent}>
            <span className={styles.bannerIcon} aria-hidden="true">
              ✏️
            </span>
            <div className={styles.bannerTextWrapper}>
              <span className={styles.bannerTitle}>Editing message</span>
              <span className={styles.bannerSnippet}>
                Press Enter to save, Esc to cancel
              </span>
            </div>
          </div>
          <button
            type="button"
            className={styles.bannerCloseBtn}
            onClick={() => {
              onCancelEdit?.();
              setText("");
            }}
            title="Cancel editing"
            aria-label="Cancel editing"
          >
            ✕
          </button>
        </div>
      )}

      <div className={styles.composerContainer}>
        {/* Emoji Picker Popup */}
        {showEmojiPicker && (
          <EmojiPicker
            onSelectEmoji={handleSelectEmoji}
            onClose={() => setShowEmojiPicker(false)}
          />
        )}

        <div className={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={
              isEditing
                ? "Edit your message..."
                : isReplying
                ? `Reply to ${replyingTo?.senderName}...`
                : placeholder
            }
            disabled={disabled || isSubmitting}
            rows={1}
            aria-label={isEditing ? "Edit message text" : "Type message"}
          />

          {/* Emoji Toggle Button */}
          <button
            type="button"
            className={`${styles.actionButton} ${
              showEmojiPicker ? styles.actionButtonActive : ""
            }`}
            onClick={() => setShowEmojiPicker((prev) => !prev)}
            title="Insert Unicode Emoji"
            aria-label="Toggle emoji picker"
            aria-expanded={showEmojiPicker}
          >
            😊
          </button>
        </div>

        <button
          type="button"
          className={`${styles.sendButton} ${isEditing ? styles.sendButtonSave : ""}`}
          onClick={handleSubmit}
          disabled={!text.trim() || disabled || isSubmitting}
          aria-label={isEditing ? "Save edited message" : "Send message"}
        >
          {isSubmitting ? "..." : isEditing ? "Save" : "Send"}
        </button>
      </div>
    </div>
  );
};
