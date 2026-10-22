import { apiClient, setAccessToken } from "./client";
import { AuthResponse, User } from "@/types";

export interface RegisterPayload {
  username: string;
  email: string;
  display_name: string;
  password: string;
  interface_language?: string;
  preferred_chat_language?: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface UserUpdatePayload {
  display_name?: string;
  interface_language?: string;
  preferred_chat_language?: string;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await apiClient<AuthResponse>("/api/v1/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setAccessToken(res.tokens.access);
  return res;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const res = await apiClient<AuthResponse>("/api/v1/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setAccessToken(res.tokens.access);
  return res;
}

export async function logout(refresh?: string): Promise<{ message: string }> {
  const res = await apiClient<{ message: string }>("/api/v1/auth/logout/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
  });
  setAccessToken(null);
  return res;
}

export async function getMe(): Promise<{ user: User }> {
  return apiClient<{ user: User }>("/api/v1/auth/me/");
}

export async function updateMe(payload: UserUpdatePayload): Promise<{ user: User }> {
  return apiClient<{ user: User }>("/api/v1/users/me/", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
