import { apiClient } from "./client";
import { Message, MessageInfo } from "@/types";

export interface MessageSendPayload {
  client_message_id: string;
  text: string;
  reply_to_id?: string | null;
}

export async function getMessages(
  conversationId: string,
  limit = 50,
  beforeSeq?: number
): Promise<Message[]> {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (beforeSeq !== undefined) {
    params.set("before_seq", beforeSeq.toString());
  }
  return apiClient<Message[]>(
    `/api/v1/conversations/${conversationId}/messages/?${params.toString()}`
  );
}

export async function sendMessage(
  conversationId: string,
  payload: MessageSendPayload
): Promise<Message> {
  return apiClient<Message>(`/api/v1/conversations/${conversationId}/messages/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMessageInfo(messageId: string): Promise<MessageInfo> {
  return apiClient<MessageInfo>(`/api/v1/messages/${messageId}/info/`);
}

export async function editMessage(messageId: string, text: string): Promise<Message> {
  return apiClient<Message>(`/api/v1/messages/${messageId}/`, {
    method: "PATCH",
    body: JSON.stringify({ text }),
  });
}

export async function deleteMessage(messageId: string): Promise<{ message_id: string; deleted_at: string }> {
  return apiClient<{ message_id: string; deleted_at: string }>(`/api/v1/messages/${messageId}/`, {
    method: "DELETE",
  });
}
