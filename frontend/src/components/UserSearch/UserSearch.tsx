import React, { useState, useEffect } from "react";
import styles from "./UserSearch.module.css";
import { UserAvatar } from "@/components/UserAvatar";
import { UserSearchResult } from "@/types";
import { searchUsers } from "@/api/users";

export interface UserSearchProps {
  onSelectUser: (user: UserSearchResult) => void;
  currentUserId?: string;
  placeholder?: string;
}

export const UserSearch: React.FC<UserSearchProps> = ({
  onSelectUser,
  currentUserId,
  placeholder = "Search people by username or name...",
}) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const users = await searchUsers(query);
        setResults(currentUserId ? users.filter((u) => u.id !== currentUserId) : users);
      } catch {
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, currentUserId]);

  return (
    <div className={styles.container}>
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {query.trim().length > 0 && (
        <div className={styles.resultList} role="region" aria-label="User search results">
          {isSearching ? (
            <div className={styles.emptyNote}>Searching...</div>
          ) : results.length > 0 ? (
            results.map((user) => (
              <div key={user.id} className={styles.userItem}>
                <div className={styles.userInfo}>
                  <UserAvatar name={user.display_name} size="sm" />
                  <div className={styles.nameBlock}>
                    <span className={styles.displayName}>{user.display_name}</span>
                    <span className={styles.username}>@{user.username}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={styles.chatBtn}
                  onClick={() => {
                    onSelectUser(user);
                    setQuery("");
                    setResults([]);
                  }}
                >
                  Message
                </button>
              </div>
            ))
          ) : (
            <div className={styles.emptyNote}>No users found.</div>
          )}
        </div>
      )}
    </div>
  );
};
