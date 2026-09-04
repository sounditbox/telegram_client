import type {
  ApiEnvelope,
  ApiErrorPayload,
  AuthAction,
  AuthStatus,
  DialogInfo,
  FileResult,
  MessageInfo,
  SentMessage,
  TelegramEvent,
} from "./types";

const TOKEN_KEY = "telegram-desk-access-token";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
  }
}

export function saveAccessToken(token: string): void {
  if (token.trim()) {
    sessionStorage.setItem(TOKEN_KEY, token.trim());
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem(TOKEN_KEY);
  return token ? { "X-API-Key": token } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value));
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...init, headers });
  const payload = (await response.json()) as ApiEnvelope<T> | ApiErrorPayload;
  if (!response.ok || !payload.ok) {
    const error = !payload.ok ? payload.error : null;
    throw new ApiError(
      error?.message ?? "Не удалось выполнить запрос",
      response.status,
      error?.code ?? "request_failed",
    );
  }
  return payload.data;
}

export const api = {
  authStatus: () => request<AuthStatus>("/api/auth/status"),
  requestCode: (phone: string, resend = false) =>
    request<AuthAction>("/api/auth/code", {
      method: "POST",
      body: JSON.stringify({ phone, resend }),
    }),
  verifyCode: (code: string) =>
    request<AuthAction>("/api/auth/code/verify", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  verifyPassword: (password: string) =>
    request<AuthAction>("/api/auth/password/verify", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  resetAuth: () => request<AuthAction>("/api/auth/reset", { method: "POST" }),
  logout: () => request<AuthAction>("/api/auth/logout", { method: "POST" }),
  dialogs: () => request<DialogInfo[]>("/api/dialogs?limit=100"),
  messages: (chatId: number | string) =>
    request<MessageInfo[]>(`/api/dialogs/${encodeURIComponent(chatId)}/messages?limit=100`),
  markRead: (chatId: number | string) =>
    request<{ read: boolean }>(`/api/dialogs/${encodeURIComponent(chatId)}/read`, {
      method: "POST",
    }),
  sendMessage: (chatId: number | string, text: string) =>
    request<SentMessage>("/api/messages", {
      method: "POST",
      body: JSON.stringify({ chat_id: String(chatId), text }),
    }),
  sendFile: (chatId: number | string, file: File) => {
    const body = new FormData();
    body.append("chat_id", String(chatId));
    body.append("file", file);
    return request<FileResult>("/api/files", { method: "POST", body });
  },
  avatarUrl: (entityId: number | string) =>
    `/api/media/avatars/${encodeURIComponent(entityId)}`,
  messageMediaUrl: (chatId: number | string, messageId: number) =>
    `/api/media/dialogs/${encodeURIComponent(chatId)}/messages/${messageId}`,
};

export async function streamEvents(
  after: number,
  onEvent: (event: TelegramEvent) => void,
  signal: AbortSignal,
  onOpen?: () => void,
): Promise<void> {
  const response = await fetch(`/api/events/stream?after=${after}`, {
    headers: authHeaders(),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError("Поток событий недоступен", response.status, "event_stream_failed");
  }
  onOpen?.();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (!signal.aborted) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("\n");
      if (data) onEvent(JSON.parse(data) as TelegramEvent);
    }
  }
}
