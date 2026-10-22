import { ApiErrorPayload } from "@/types";

export function resolveApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, "");
  }

  // If in browser and not on localhost, default to relative origin "" so proxy/CDN routes work
  if (
    typeof window !== "undefined" &&
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1"
  ) {
    return "";
  }

  return "http://localhost:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();

let currentAccessToken: string | null = null;

export function setAccessToken(token: string | null) {
  currentAccessToken = token;
}

export function getAccessToken(): string | null {
  return currentAccessToken;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (currentAccessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${currentAccessToken}`);
  }

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${cleanEndpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type");
  let data: unknown = null;

  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  }

  if (!response.ok) {
    const errorPayload: ApiErrorPayload = (data as ApiErrorPayload) || {
      error: {
        code: `HTTP_${response.status}`,
        message: response.statusText || "An unexpected error occurred.",
      },
    };
    throw errorPayload;
  }

  return data as T;
}
