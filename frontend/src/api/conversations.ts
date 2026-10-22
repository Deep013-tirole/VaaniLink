import { apiClient } from "./client";
import {
  Conversation,
  ConversationDetail,
  GroupConversationCreatePayload,
  GroupRenamePayload,
  GroupAddMembersPayload,
} from "@/types";

export interface DirectConversationCreatePayload {
  user_id?: string;
  username?: string;
}

export async function getConversations(): Promise<Conversation[]> {
  return apiClient<Conversation[]>("/api/v1/conversations/");
}

export async function createDirectConversation(
  payload: DirectConversationCreatePayload
): Promise<Conversation> {
  return apiClient<Conversation>("/api/v1/conversations/direct/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getConversation(id: string): Promise<Conversation> {
  return apiClient<Conversation>(`/api/v1/conversations/${id}/`);
}

export async function getConversationDetail(id: string): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(`/api/v1/conversations/${id}/`);
}

export async function createGroup(
  payload: GroupConversationCreatePayload
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>("/api/v1/conversations/group/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function renameGroup(
  id: string,
  payload: GroupRenamePayload
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(`/api/v1/conversations/${id}/rename/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addGroupMembers(
  id: string,
  payload: GroupAddMembersPayload
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(`/api/v1/conversations/${id}/members/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function removeGroupMember(
  id: string,
  userId: string
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(
    `/api/v1/conversations/${id}/members/${userId}/`,
    {
      method: "DELETE",
    }
  );
}

export async function promoteAdmin(
  id: string,
  userId: string
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(`/api/v1/conversations/${id}/promote/`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function demoteAdmin(
  id: string,
  userId: string
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(`/api/v1/conversations/${id}/demote/`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function transferOwnership(
  id: string,
  userId: string
): Promise<ConversationDetail> {
  return apiClient<ConversationDetail>(
    `/api/v1/conversations/${id}/transfer-ownership/`,
    {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }
  );
}

export async function leaveGroup(id: string): Promise<{ detail: string }> {
  return apiClient<{ detail: string }>(`/api/v1/conversations/${id}/leave/`, {
    method: "POST",
  });
}
