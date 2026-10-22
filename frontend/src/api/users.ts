import { apiClient } from "./client";
import { UserSearchResult } from "@/types";

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  if (!query.trim()) return [];
  const params = new URLSearchParams({ q: query.trim() });
  return apiClient<UserSearchResult[]>(`/api/v1/users/search/?${params.toString()}`);
}
