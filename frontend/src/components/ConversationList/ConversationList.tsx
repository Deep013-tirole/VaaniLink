import React from "react";
import styles from "./ConversationList.module.css";
import { UserAvatar } from "@/components/UserAvatar";
import { Conversation, UserPresence } from "@/types";

export interface ConversationListProps {
  conversations: Conversation[];
  selectedConversationId: string | null;
  onSelectConversation: (conversation: Conversation) => void;
  presenceMap?: Record<string, UserPresence>;
  onCreateGroupClick?: () => void;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  selectedConversationId,
  onSelectConversation,
  presenceMap = {},
  onCreateGroupClick,
}) => {
  return (
    <div className={styles.listContainer} role="navigation" aria-label="Chat conversations">
      <div className={styles.headerRow}>
        <span className={styles.headerTitle}>Chats ({conversations.length})</span>
        {onCreateGroupClick && (
          <button
            type="button"
            className={styles.newGroupBtn}
            onClick={onCreateGroupClick}
            title="Create a new multilingual group chat"
          >
            <span>👥</span> New Group
          </button>
        )}
      </div>

      {conversations.length === 0 ? (
        <div className={styles.emptyState}>
          No active conversations. Search for people above or create a group to start chatting!
        </div>
      ) : (
        conversations.map((conv) => {
          const isSelected = conv.id === selectedConversationId;
          const isGroup = conv.type === "GROUP";
          const title = conv.direct_user
            ? conv.direct_user.display_name
            : conv.group_name || "Group Conversation";

          const isOnline = conv.direct_user
            ? presenceMap[conv.direct_user.id]?.is_online || false
            : false;

          return (
            <button
              key={conv.id}
              type="button"
              className={`${styles.item} ${isSelected ? styles.itemActive : ""}`}
              onClick={() => onSelectConversation(conv)}
            >
              <UserAvatar name={title} size="md" isOnline={!isGroup ? isOnline : false} />
              <div className={styles.content}>
                <div className={styles.topRow}>
                  <div className={styles.titleGroup}>
                    <span className={styles.title}>{title}</span>
                    {isGroup && <span className={styles.groupBadge}>Group</span>}
                  </div>
                  {conv.latest_message && (
                    <span className={styles.timestamp}>
                      {new Date(conv.latest_message.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
                <span className={styles.preview}>
                  {conv.latest_message
                    ? conv.latest_message.text_preview
                    : "Start a conversation..."}
                </span>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
};
