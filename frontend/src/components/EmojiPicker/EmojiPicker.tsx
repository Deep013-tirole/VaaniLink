import React, { useState, useRef, useEffect, useMemo } from "react";
import styles from "./EmojiPicker.module.css";

export interface EmojiPickerProps {
  onSelectEmoji: (emoji: string) => void;
  onClose: () => void;
}

interface EmojiCategory {
  id: string;
  name: string;
  icon: string;
  emojis: string[];
}

const EMOJI_CATEGORIES: EmojiCategory[] = [
  {
    id: "smileys",
    name: "Smileys & Emotion",
    icon: "😀",
    emojis: [
      "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "🥲", "🥹", "😊", "😇",
      "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😋", "😛", "😜", "🤪",
      "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🫡", "🤐", "🤨", "😐", "😑", "😶",
      "😏", "😒", "🙄", "😬", "🤥", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕",
      "🤢", "🤮", "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "🥸", "😎",
      "🤓", "🧐", "😕", "😟", "🙁", "😮", "😯", "😲", "😳", "🥺", "😦", "😧",
      "😨", "😰", "😥", "😢", "😭", "😱", "😖", "😣", "😞", "😓", "😩", "😫",
      "🥱", "😤", "😡", "😠", "🤬",
    ],
  },
  {
    id: "gestures",
    name: "Gestures & People",
    icon: "👋",
    emojis: [
      "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🫰", "🤟",
      "🤘", "🤙", "🫵", "👈", "👉", "👆", "👇", "☝️", "👍", "👎", "✊", "👊",
      "🤛", "🤜", "👏", "🙌", "🫶", "👐", "🤲", "🤝", "🙏", "✍️", "💪", "🫂",
    ],
  },
  {
    id: "hearts",
    name: "Hearts & Sparkles",
    icon: "❤️",
    emojis: [
      "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹",
      "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "✨", "🌟", "💫",
      "💥", "🔥", "🌈",
    ],
  },
  {
    id: "nature",
    name: "Animals & Nature",
    icon: "🐶",
    emojis: [
      "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
      "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🦆", "🦅", "🦉", "🦇", "🐺",
      "🦄", "🐝", "🐛", "🦋", "🐌", "🐞", "🌸", "🌺", "🌹", "🌻", "🌼", "🌷",
      "🌱", "🌲", "🌳", "🌴", "🍀", "🍁", "🍂",
    ],
  },
  {
    id: "food",
    name: "Food & Drink",
    icon: "🍕",
    emojis: [
      "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍒", "🍑",
      "🥭", "🍍", "🥥", "🥝", "🍅", "🥑", "🥦", "🌽", "🥕", "🍕", "🍔", "🍟",
      "🌭", "🍿", "🧈", "🥞", "🧇", "🧀", "🍗", "🍖", "🍜", "🍝", "🍣", "🍱",
      "🍛", "🍙", "🍚", "☕", "🍵", "🧋", "🥤",
    ],
  },
  {
    id: "travel",
    name: "Travel & Objects",
    icon: "🚗",
    emojis: [
      "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🚚", "🚜",
      "🛵", "🏍️", "🚲", "🛴", "✈️", "🛫", "🛬", "🚀", "🛸", "🚁", "⛵", "🚤",
      "🚢", "🏠", "🏡", "🏢", "🏣", "🏥", "🏦", "🏨", "🏛️", "🎉", "🎊", "🎈",
      "🎁", "🏆", "🥇", "⚽", "🏀", "🎯", "🎵", "🎶",
    ],
  },
  {
    id: "symbols",
    name: "Symbols & Status",
    icon: "✅",
    emojis: [
      "✅", "✔️", "❌", "❎", "❓", "❗", "‼️", "⁉️", "💯", "🔔", "🔕", "💡",
      "🔒", "🔓", "🔑", "🗝️", "💬", "💭", "📢", "📣", "⚠️", "⛔", "🚫", "ℹ️",
      "🆗", "🆙", "🆒", "🆕", "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
    ],
  },
];

export const EmojiPicker: React.FC<EmojiPickerProps> = ({ onSelectEmoji, onClose }) => {
  const [activeCategoryId, setActiveCategoryId] = useState<string>("smileys");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose]);

  const activeCategory = useMemo(() => {
    return EMOJI_CATEGORIES.find((c) => c.id === activeCategoryId) || EMOJI_CATEGORIES[0];
  }, [activeCategoryId]);

  const displayedEmojis = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return activeCategory.emojis;
    }
    // Search across all categories
    const matches: string[] = [];
    for (const cat of EMOJI_CATEGORIES) {
      for (const emoji of cat.emojis) {
        if (emoji.includes(query) || cat.name.toLowerCase().includes(query)) {
          if (!matches.includes(emoji)) {
            matches.push(emoji);
          }
        }
      }
    }
    return matches;
  }, [activeCategory, searchQuery]);

  return (
    <div
      ref={containerRef}
      className={styles.pickerContainer}
      role="dialog"
      aria-label="Emoji picker"
      aria-modal="false"
    >
      <div className={styles.header}>
        <span className={styles.title}>
          {searchQuery ? "Search Results" : activeCategory.name}
        </span>
        <button
          type="button"
          className={styles.closeButton}
          onClick={onClose}
          aria-label="Close emoji picker"
        >
          ✕
        </button>
      </div>

      <div className={styles.searchWrapper}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search emojis or categories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Filter emojis"
          autoFocus
        />
      </div>

      {!searchQuery && (
        <div className={styles.categoryTabs} role="tablist" aria-label="Emoji categories">
          {EMOJI_CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              role="tab"
              aria-selected={activeCategoryId === cat.id}
              className={`${styles.categoryTab} ${
                activeCategoryId === cat.id ? styles.activeTab : ""
              }`}
              title={cat.name}
              onClick={() => setActiveCategoryId(cat.id)}
            >
              {cat.icon}
            </button>
          ))}
        </div>
      )}

      <div className={styles.emojiGrid} role="listbox" aria-label="Available emojis">
        {displayedEmojis.length === 0 ? (
          <div className={styles.noResults}>No emojis found for "{searchQuery}"</div>
        ) : (
          displayedEmojis.map((emoji, index) => (
            <button
              key={`${emoji}-${index}`}
              type="button"
              className={styles.emojiButton}
              onClick={() => onSelectEmoji(emoji)}
              aria-label={`Insert emoji ${emoji}`}
            >
              {emoji}
            </button>
          ))
        )}
      </div>
    </div>
  );
};
