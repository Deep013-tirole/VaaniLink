import { WebSocketFrame } from "@/types";

export type ConnectionStatus = "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "RECONNECTING";

type EventHandler = (data: unknown) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private status: ConnectionStatus = "DISCONNECTED";
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();
  private eventListeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private intentionalClose = false;
  private messageQueue: string[] = [];

  constructor() {
    this.handleMessage = this.handleMessage.bind(this);
    this.handleOpen = this.handleOpen.bind(this);
    this.handleClose = this.handleClose.bind(this);
    this.handleError = this.handleError.bind(this);
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  public onStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  private setStatus(newStatus: ConnectionStatus) {
    this.status = newStatus;
    this.statusListeners.forEach((cb) => cb(newStatus));
  }

  public connect(token: string) {
    if (this.ws && (this.status === "CONNECTED" || this.status === "CONNECTING")) {
      if (this.token === token) return;
      this.disconnect();
    }

    this.token = token;
    this.intentionalClose = false;
    this.setStatus("CONNECTING");

    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const wsBase = apiBase.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/ws/chat/?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = this.handleOpen;
      this.ws.onmessage = this.handleMessage;
      this.ws.onclose = this.handleClose;
      this.ws.onerror = this.handleError;
    } catch {
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.intentionalClose = true;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus("DISCONNECTED");
  }

  private handleOpen() {
    this.reconnectAttempts = 0;
    this.setStatus("CONNECTED");

    // Flush any queued messages
    while (this.messageQueue.length > 0) {
      const item = this.messageQueue.shift();
      if (item && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(item);
      }
    }
  }

  private handleMessage(event: MessageEvent) {
    try {
      const frame: WebSocketFrame<unknown> = JSON.parse(event.data);
      if (frame.event) {
        const handlers = this.eventListeners.get(frame.event);
        if (handlers) {
          handlers.forEach((handler) => handler(frame.data));
        }
      }
    } catch {
      // Discard invalid frames
    }
  }

  private handleClose(event: CloseEvent) {
    if (this.intentionalClose) {
      this.setStatus("DISCONNECTED");
      return;
    }

    // Auth error close code 4001: do not auto-reconnect
    if (event.code === 4001) {
      this.setStatus("DISCONNECTED");
      return;
    }

    this.scheduleReconnect();
  }

  private handleError() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }

  private scheduleReconnect() {
    if (this.intentionalClose || !this.token) return;

    this.setStatus("RECONNECTING");
    this.reconnectAttempts++;

    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000) + Math.random() * 500;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = window.setTimeout(() => {
      if (this.token && !this.intentionalClose) {
        this.connect(this.token);
      }
    }, delay);
  }

  public on(event: string, callback: EventHandler): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
    return () => {
      this.eventListeners.get(event)?.delete(callback);
    };
  }

  public off(event: string, callback: EventHandler) {
    this.eventListeners.get(event)?.delete(callback);
  }

  public emit<T = Record<string, unknown>>(event: string, data: T, requestId?: string) {
    const frame: WebSocketFrame<T> = {
      event,
      request_id: requestId || crypto.randomUUID?.() || undefined,
      data,
    };
    const payload = JSON.stringify(frame);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
    } else {
      this.messageQueue.push(payload);
    }
  }

  // Domain Helper Methods

  public joinConversation(conversationId: string) {
    this.emit("conversation.join", { conversation_id: conversationId });
  }

  public leaveConversation(conversationId: string) {
    this.emit("conversation.leave", { conversation_id: conversationId });
  }

  public startTyping(conversationId: string) {
    this.emit("typing.start", { conversation_id: conversationId });
  }

  public stopTyping(conversationId: string) {
    this.emit("typing.stop", { conversation_id: conversationId });
  }

  public sendDelivered(messageIds: string[]) {
    if (messageIds.length === 0) return;
    this.emit("message.delivered", { message_ids: messageIds });
  }

  public sendSeen(conversationId: string, upToMessageId?: string, messageIds?: string[]) {
    this.emit("message.seen", {
      conversation_id: conversationId,
      up_to_message_id: upToMessageId || null,
      message_ids: messageIds || [],
    });
  }

  public sendMessage(
    conversationId: string,
    clientMessageId: string,
    text: string,
    replyToId?: string | null
  ): Promise<{ message_id: string; sequence_number: number }> {
    return new Promise((resolve, reject) => {
      const requestId = crypto.randomUUID?.() || `req-${Date.now()}`;

      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error("Timeout awaiting message confirmation"));
      }, 8000);

      const handleSent = (data: unknown) => {
        const payload = data as { client_message_id: string; message_id: string; sequence_number: number };
        if (payload.client_message_id === clientMessageId) {
          cleanup();
          resolve(payload);
        }
      };

      const handleError = (data: unknown) => {
        const payload = data as { code: string; message: string };
        cleanup();
        reject(new Error(payload.message || "Message send failed"));
      };

      const cleanup = () => {
        window.clearTimeout(timeout);
        this.off("message.sent", handleSent);
        this.off("error", handleError);
      };

      this.on("message.sent", handleSent);
      this.on("error", handleError);

      this.emit(
        "message.send",
        {
          conversation_id: conversationId,
          client_message_id: clientMessageId,
          text,
          reply_to_id: replyToId || null,
        },
        requestId
      );
    });
  }

  public editMessage(
    messageId: string,
    text: string
  ): Promise<{ message_id: string; version: number }> {
    return new Promise((resolve, reject) => {
      const requestId = crypto.randomUUID?.() || `req-${Date.now()}`;
      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error("Timeout awaiting edit confirmation"));
      }, 8000);

      const handleAck = (data: unknown) => {
        const payload = data as { message_id: string; version: number };
        if (payload.message_id === messageId) {
          cleanup();
          resolve(payload);
        }
      };

      const handleError = (data: unknown) => {
        const payload = data as { code: string; message: string };
        cleanup();
        reject(new Error(payload.message || "Message edit failed"));
      };

      const cleanup = () => {
        window.clearTimeout(timeout);
        this.off("message.edited_ack", handleAck);
        this.off("error", handleError);
      };

      this.on("message.edited_ack", handleAck);
      this.on("error", handleError);

      this.emit("message.edit", { message_id: messageId, text }, requestId);
    });
  }

  public deleteMessage(
    messageId: string
  ): Promise<{ message_id: string }> {
    return new Promise((resolve, reject) => {
      const requestId = crypto.randomUUID?.() || `req-${Date.now()}`;
      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error("Timeout awaiting delete confirmation"));
      }, 8000);

      const handleAck = (data: unknown) => {
        const payload = data as { message_id: string };
        if (payload.message_id === messageId) {
          cleanup();
          resolve(payload);
        }
      };

      const handleError = (data: unknown) => {
        const payload = data as { code: string; message: string };
        cleanup();
        reject(new Error(payload.message || "Message delete failed"));
      };

      const cleanup = () => {
        window.clearTimeout(timeout);
        this.off("message.deleted_ack", handleAck);
        this.off("error", handleError);
      };

      this.on("message.deleted_ack", handleAck);
      this.on("error", handleError);

      this.emit("message.delete", { message_id: messageId }, requestId);
    });
  }
}

// Singleton client instance
export const wsManager = new WebSocketManager();
