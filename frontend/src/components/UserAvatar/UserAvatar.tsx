import React, { useMemo } from "react";
import styles from "./UserAvatar.module.css";
import { getInitials } from "@/utils";

export interface UserAvatarProps {
  name: string;
  size?: "sm" | "md" | "lg" | "xl";
  isOnline?: boolean;
  className?: string;
  ariaLabel?: string;
}

// Accessible curated background palette for initial avatars
const PALETTE = [
  "#2563eb", // blue
  "#7c3aed", // violet
  "#db2777", // pink
  "#ea580c", // orange
  "#059669", // emerald
  "#0891b2", // cyan
  "#4f46e5", // indigo
  "#d97706", // amber
  "#dc2626", // red
  "#475569", // slate
];

function getPaletteColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % PALETTE.length;
  return PALETTE[index];
}

export const UserAvatar: React.FC<UserAvatarProps> = ({
  name,
  size = "md",
  isOnline,
  className = "",
  ariaLabel,
}) => {
  const initials = useMemo(() => getInitials(name), [name]);
  const backgroundColor = useMemo(() => getPaletteColor(name), [name]);

  const sizeClass = {
    sm: styles.sizeSm,
    md: styles.sizeMd,
    lg: styles.sizeLg,
    xl: styles.sizeXl,
  }[size];

  const dotSizeClass = {
    sm: styles.dotSm,
    md: styles.dotMd,
    lg: styles.dotLg,
    xl: styles.dotXl,
  }[size];

  return (
    <div
      className={`${styles.avatarContainer} ${className}`}
      aria-label={ariaLabel || `${name}'s avatar`}
      role="img"
    >
      <div
        className={`${styles.avatar} ${sizeClass}`}
        style={{ backgroundColor }}
      >
        <span>{initials}</span>
      </div>

      {isOnline !== undefined && (
        <span
          className={`${styles.statusDot} ${dotSizeClass} ${
            isOnline ? styles.statusDotOnline : styles.statusDotOffline
          }`}
          title={isOnline ? "Online" : "Offline"}
          aria-hidden="true"
        />
      )}
    </div>
  );
};
