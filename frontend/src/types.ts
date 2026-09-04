export type AuthPhase = "idle" | "code_sent" | "password_required" | "authorized";

export interface UserInfo {
  id: number;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  is_bot: boolean;
  has_avatar: boolean;
}

export interface AuthStatus {
  connected: boolean;
  authenticated: boolean;
  phase: AuthPhase;
  user: UserInfo | null;
}

export interface AuthAction {
  phase: AuthPhase;
  message: string;
}

export interface DialogInfo {
  id: number;
  title: string;
  username: string | null;
  unread_count: number;
  kind: "user" | "group" | "channel";
  has_avatar: boolean;
}

export interface MediaInfo {
  kind: "photo" | "video" | "audio" | "voice" | "sticker" | "document";
  mime_type: string;
  filename: string;
  size: number | null;
}

export interface MessageInfo {
  id: number;
  text: string;
  sender_id: number | null;
  sender_name: string;
  sender_username: string | null;
  sender_has_avatar: boolean;
  date: string | null;
  outgoing: boolean;
  is_reply: boolean;
  has_media: boolean;
  media: MediaInfo | null;
}

export interface SentMessage {
  message_id: number;
}

export interface FileResult {
  message_id: number;
  filename: string;
  size: number;
}

export interface TelegramEvent {
  sequence: number;
  kind: "new_message" | "message_edited";
  message_id: number;
  chat_id: number | null;
  text: string;
  sender_id: number | null;
  sender_name: string;
  sender_username: string | null;
  sender_has_avatar: boolean;
  chat_title: string;
  date: string | null;
  outgoing: boolean;
  has_media: boolean;
  media: MediaInfo | null;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: number | null;
  has_more: boolean;
}

export interface ApiEnvelope<T> {
  ok: true;
  data: T;
}

export interface ApiErrorPayload {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
  };
}
