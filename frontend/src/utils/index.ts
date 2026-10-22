/**
 * Utility functions.
 */

/**
 * Generate 1-2 letter initials from a display name or group title.
 * Examples:
 *   "Deepak Tirole" -> "DT"
 *   "John Smith" -> "JS"
 *   "Project Beta" -> "PB"
 */
export function getInitials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "VL";

  const parts = trimmed.split(/\s+/);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  const first = parts[0][0] || "";
  const last = parts[parts.length - 1][0] || "";
  return (first + last).toUpperCase();
}
