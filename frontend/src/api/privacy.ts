import { apiClient } from "./client";
import {
  BlockedUser,
  BlockUserPayload,
  PrivacySetting,
  UpdatePrivacyPayload,
} from "@/types";

export async function getPrivacySettings(): Promise<PrivacySetting> {
  return apiClient<PrivacySetting>("/api/v1/privacy/");
}

export async function updatePrivacySettings(
  payload: UpdatePrivacyPayload
): Promise<PrivacySetting> {
  return apiClient<PrivacySetting>("/api/v1/privacy/", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getBlockedUsers(): Promise<BlockedUser[]> {
  return apiClient<BlockedUser[]>("/api/v1/blocks/");
}

export async function blockUser(
  payload: BlockUserPayload
): Promise<BlockedUser> {
  return apiClient<BlockedUser>("/api/v1/blocks/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function unblockUser(
  userId: string
): Promise<{ detail: string }> {
  return apiClient<{ detail: string }>(`/api/v1/blocks/${userId}/`, {
    method: "DELETE",
  });
}
