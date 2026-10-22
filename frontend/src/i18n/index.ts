/**
 * Internationalization helpers and RTL detection metadata.
 */

export const RTL_LANGUAGES = new Set(["ar", "ur", "fa", "he", "ps", "sd"]);

export function isRtlLanguage(languageCode: string): boolean {
  if (!languageCode) return false;
  const normalized = languageCode.toLowerCase().split("-")[0];
  return RTL_LANGUAGES.has(normalized);
}
