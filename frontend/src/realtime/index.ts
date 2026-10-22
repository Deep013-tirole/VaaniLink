/**
 * Realtime WebSocket connection configuration.
 */

export function resolveWsBaseUrl(): string {
  const envWsUrl = import.meta.env.VITE_WS_BASE_URL;
  if (envWsUrl && typeof envWsUrl === "string" && envWsUrl.trim()) {
    return envWsUrl.trim().replace(/\/+$/, "");
  }

  const envApiUrl = import.meta.env.VITE_API_BASE_URL;
  if (envApiUrl && typeof envApiUrl === "string" && envApiUrl.trim()) {
    const cleanApi = envApiUrl.trim().replace(/\/+$/, "");
    if (cleanApi.startsWith("https://")) {
      return cleanApi.replace(/^https:\/\//, "wss://");
    }
    if (cleanApi.startsWith("http://")) {
      return cleanApi.replace(/^http:\/\//, "ws://");
    }
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    if (
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ) {
      return `${protocol}//${host}`;
    }
  }

  return "ws://localhost:8000";
}

export const WS_BASE_URL = resolveWsBaseUrl();

export * from "./WebSocketManager";
