import { apiClient } from "./client";
import { Language } from "@/types";

export async function getLanguages(
  activeOnly = true,
  search = ""
): Promise<Language[]> {
  const params = new URLSearchParams();
  if (activeOnly) params.set("active_only", "true");
  if (search) params.set("q", search);

  const query = params.toString() ? `?${params.toString()}` : "";
  return apiClient<Language[]>(`/api/v1/languages/${query}`);
}
