import {
  ArrowLeft,
  CheckCheck,
  FileText,
  Hash,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  MessageCircle,
  Paperclip,
  Phone,
  Radio,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  UserRound,
  UsersRound,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import {
  type ChangeEvent,
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, api, saveAccessToken, streamEvents } from "./api";
import type { AuthAction, AuthStatus, DialogInfo, MediaInfo, MessageInfo, TelegramEvent } from "./types";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Что-то пошло не так";
}

function initials(value: string): string {
  return value
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function formatTime(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("ru", { hour: "2-digit", minute: "2-digit" }).format(
    new Date(value),
  );
}

function App() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [locked, setLocked] = useState(false);
  const [startupError, setStartupError] = useState("");

  const refreshAuth = useCallback(async () => {
    try {
      setStartupError("");
      setAuth(await api.authStatus());
      setLocked(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && error.code === "access_denied") {
        setLocked(true);
        return;
      }
      setStartupError(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void refreshAuth();
  }, [refreshAuth]);

  if (locked) {
    return <AccessGate onUnlock={refreshAuth} />;
  }

  if (!auth) {
    return <LoadingScreen error={startupError} onRetry={refreshAuth} />;
  }

  if (!auth.authenticated || !auth.user) {
    return <AuthScreen status={auth} onChanged={refreshAuth} />;
  }

  return <Messenger status={auth} onLoggedOut={refreshAuth} />;
}

function LoadingScreen({ error, onRetry }: { error: string; onRetry: () => Promise<void> }) {
  return (
    <PageBackdrop>
      <div className="surface-card flex w-full max-w-md flex-col items-center px-8 py-12 text-center">
        <BrandMark />
        {error ? (
          <>
            <h1 className="mt-7 text-2xl font-semibold text-white">Не удалось запустить клиент</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">{error}</p>
            <button className="primary-button mt-7" onClick={() => void onRetry()}>
              <RefreshCw size={17} /> Повторить
            </button>
          </>
        ) : (
          <>
            <LoaderCircle className="mt-8 animate-spin text-cyan-300" size={28} />
            <p className="mt-4 text-sm text-slate-400">Подключаем защищённую сессию…</p>
          </>
        )}
      </div>
    </PageBackdrop>
  );
}

function AccessGate({ onUnlock }: { onUnlock: () => Promise<void> }) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    saveAccessToken(token);
    try {
      await onUnlock();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageBackdrop>
      <form className="surface-card w-full max-w-md px-8 py-9" onSubmit={submit}>
        <BrandMark />
        <div className="mt-8 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-400/10 text-amber-300">
          <LockKeyhole size={23} />
        </div>
        <h1 className="mt-5 text-2xl font-semibold text-white">Закрытый доступ</h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          Сервер защищён. Введите значение <span className="font-mono text-slate-300">ACCESS_TOKEN</span>.
        </p>
        <label className="field-label mt-7" htmlFor="access-token">Ключ доступа</label>
        <input
          id="access-token"
          className="text-field mt-2"
          type="password"
          autoComplete="current-password"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          required
        />
        {error && <ErrorCallout message={error} />}
        <button className="primary-button mt-5 w-full" disabled={busy}>
          {busy ? <LoaderCircle className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
          Открыть клиент
        </button>
      </form>
    </PageBackdrop>
  );
}

function AuthScreen({ status, onChanged }: { status: AuthStatus; onChanged: () => Promise<void> }) {
  const [phase, setPhase] = useState(status.phase);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function perform(action: () => Promise<AuthAction>) {
    setBusy(true);
    setError("");
    try {
      const result = await action();
      setPhase(result.phase);
      setNotice(result.message);
      if (result.phase === "authorized") await onChanged();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function goBack() {
    await perform(api.resetAuth);
    setCode("");
    setPassword("");
  }

  return (
    <PageBackdrop>
      <main className="grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/10 bg-[#0d1424]/90 shadow-2xl shadow-black/40 backdrop-blur-xl md:grid-cols-[1.05fr_0.95fr]">
        <section className="relative hidden min-h-[650px] overflow-hidden border-r border-white/10 p-12 md:flex md:flex-col">
          <div className="absolute -left-28 top-16 h-80 w-80 rounded-full bg-cyan-400/15 blur-[90px]" />
          <div className="absolute -bottom-28 right-0 h-96 w-96 rounded-full bg-indigo-500/20 blur-[100px]" />
          <BrandMark />
          <div className="relative mt-auto mb-6">
            <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-3xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200">
              <MessageCircle size={30} />
            </div>
            <h1 className="max-w-md text-4xl leading-tight font-semibold tracking-tight text-white">
              Ваш Telegram.<br />Спокойно и локально.
            </h1>
            <p className="mt-5 max-w-md text-base leading-7 text-slate-400">
              Сессия хранится только на этом компьютере. Клиент не отправляет историю сторонним сервисам.
            </p>
            <div className="mt-8 flex items-center gap-3 text-sm text-slate-400">
              <span className={`status-dot ${status.connected ? "online" : "offline"}`} />
              {status.connected ? "Telegram доступен" : "Ожидаем соединение с Telegram"}
            </div>
          </div>
        </section>

        <section className="flex min-h-[620px] flex-col justify-center px-7 py-10 sm:px-12 md:min-h-[650px]">
          <div className="md:hidden"><BrandMark /></div>
          <div className="mx-auto w-full max-w-sm">
            <p className="eyebrow">Безопасный вход</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">
              {phase === "idle" && "Введите номер"}
              {phase === "code_sent" && "Подтвердите вход"}
              {phase === "password_required" && "Защита 2FA"}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {phase === "idle" && "Мы запросим одноразовый код у Telegram."}
              {phase === "code_sent" && "Код придёт в приложение Telegram или по SMS."}
              {phase === "password_required" && "Введите облачный пароль Telegram."}
            </p>

            {phase === "idle" && (
              <form className="mt-8" onSubmit={(event) => { event.preventDefault(); void perform(() => api.requestCode(phone)); }}>
                <label className="field-label" htmlFor="phone">Телефон</label>
                <div className="field-with-icon mt-2">
                  <Phone size={18} />
                  <input
                    id="phone"
                    type="tel"
                    placeholder="+995 555 00 00 00"
                    value={phone}
                    onChange={(event) => setPhone(event.target.value.replace(/\s/g, ""))}
                    pattern="\+[1-9][0-9]{7,14}"
                    autoComplete="tel"
                    required
                  />
                </div>
                <SubmitButton busy={busy} label="Получить код" />
              </form>
            )}

            {phase === "code_sent" && (
              <form className="mt-8" onSubmit={(event) => { event.preventDefault(); void perform(() => api.verifyCode(code)); }}>
                <label className="field-label" htmlFor="code">Код подтверждения</label>
                <div className="field-with-icon mt-2">
                  <Hash size={18} />
                  <input
                    id="code"
                    className="tracking-[0.35em]"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="12345"
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
                    required
                    autoFocus
                  />
                </div>
                <SubmitButton busy={busy} label="Подтвердить" />
                <button className="secondary-button mt-3 w-full" type="button" disabled={busy} onClick={() => void perform(() => api.requestCode(phone, true))}>
                  <RefreshCw size={16} /> Отправить новый код
                </button>
              </form>
            )}

            {phase === "password_required" && (
              <form className="mt-8" onSubmit={(event) => { event.preventDefault(); void perform(() => api.verifyPassword(password)); }}>
                <label className="field-label" htmlFor="password">Облачный пароль</label>
                <div className="field-with-icon mt-2">
                  <KeyRound size={18} />
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <SubmitButton busy={busy} label="Войти" />
              </form>
            )}

            {notice && !error && <SuccessCallout message={notice} />}
            {error && <ErrorCallout message={error} />}
            {phase !== "idle" && (
              <button className="mt-5 flex items-center gap-2 text-sm text-slate-400 transition hover:text-white" onClick={() => void goBack()} disabled={busy}>
                <ArrowLeft size={16} /> Начать заново
              </button>
            )}
          </div>
        </section>
      </main>
    </PageBackdrop>
  );
}

function Messenger({ status, onLoggedOut }: { status: AuthStatus; onLoggedOut: () => Promise<void> }) {
  const user = status.user!;
  const [dialogs, setDialogs] = useState<DialogInfo[]>([]);
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [selected, setSelected] = useState<DialogInfo | null>(null);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState("");
  const [loadingDialogs, setLoadingDialogs] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [liveConnected, setLiveConnected] = useState(false);
  const [toasts, setToasts] = useState<TelegramEvent[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);
  const messagePane = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<DialogInfo | null>(null);
  const lastSequence = useRef(0);
  const messageRequest = useRef(0);

  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  const loadDialogs = useCallback(async () => {
    setLoadingDialogs(true);
    try {
      setDialogs(await api.dialogs());
    } finally {
      setLoadingDialogs(false);
    }
  }, []);

  const loadMessages = useCallback(async (dialog: DialogInfo, silent = false) => {
    const requestId = ++messageRequest.current;
    if (!silent) setLoadingMessages(true);
    try {
      const nextMessages = [...(await api.messages(dialog.id))].reverse();
      if (requestId === messageRequest.current) setMessages(nextMessages);
    } finally {
      if (!silent && requestId === messageRequest.current) setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    void loadDialogs();
  }, [loadDialogs]);

  useEffect(() => {
    const pane = messagePane.current;
    if (pane) pane.scrollTop = pane.scrollHeight;
  }, [messages, selected]);

  useEffect(() => {
    const controller = new AbortController();
    async function connect() {
      while (!controller.signal.aborted) {
        try {
          await streamEvents(
            lastSequence.current,
            (event) => {
              lastSequence.current = event.sequence;
              setToasts((current) => [...current.slice(-3), event]);
              window.setTimeout(
                () => setToasts((current) => current.filter((item) => item.sequence !== event.sequence)),
                5500,
              );
              void loadDialogs();
              if (selectedRef.current?.id === event.chat_id) {
                setMessages((current) => {
                  if (current.some((message) => message.id === event.message_id)) return current;
                  return [...current, {
                    id: event.message_id,
                    text: event.text,
                    sender_id: event.sender_id,
                    sender_name: event.sender_name,
                    sender_username: event.sender_username,
                    sender_has_avatar: event.sender_has_avatar,
                    date: event.date,
                    outgoing: false,
                    is_reply: false,
                    has_media: event.text === "(медиа)",
                    media: null,
                  }];
                });
                void loadMessages(selectedRef.current, true);
              }
            },
            controller.signal,
            () => setLiveConnected(true),
          );
        } catch {
          if (!controller.signal.aborted) {
            setLiveConnected(false);
            await new Promise((resolve) => window.setTimeout(resolve, 1500));
          }
        }
      }
    }
    void connect();
    return () => controller.abort();
  }, [loadDialogs, loadMessages]);

  const filteredDialogs = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("ru");
    if (!query) return dialogs;
    return dialogs.filter((dialog) =>
      `${dialog.title} ${dialog.username ?? ""}`.toLocaleLowerCase("ru").includes(query),
    );
  }, [dialogs, search]);

  async function chooseDialog(dialog: DialogInfo) {
    setSelected(dialog);
    setMessages([]);
    await Promise.allSettled([loadMessages(dialog), api.markRead(dialog.id)]);
    setDialogs((current) =>
      current.map((item) => (item.id === dialog.id ? { ...item, unread_count: 0 } : item)),
    );
  }

  async function sendMessage() {
    const text = draft.trim();
    if (!selected || !text || sending) return;
    setSending(true);
    try {
      await api.sendMessage(selected.id, text);
      setDraft("");
      await loadMessages(selected);
    } catch (error) {
      window.alert(errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!selected || !file) return;
    setSending(true);
    try {
      await api.sendFile(selected.id, file);
      await loadMessages(selected);
    } catch (error) {
      window.alert(errorMessage(error));
    } finally {
      setSending(false);
      event.target.value = "";
    }
  }

  async function logout() {
    if (!window.confirm("Удалить локальную Telegram-сессию и выйти?")) return;
    await api.logout();
    await onLoggedOut();
  }

  return (
    <div className="h-dvh overflow-hidden bg-[#080d1a] text-slate-100">
      <div className="app-glow" />
      <header className="relative z-20 flex h-[60px] items-center justify-between border-b border-white/8 bg-[#0b1120]/85 px-4 backdrop-blur-xl sm:px-5">
        <BrandMark compact />
        <div className="flex items-center gap-3">
          <div className={`hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs sm:flex ${liveConnected ? "border-emerald-300/10 bg-emerald-400/8 text-emerald-300" : "border-amber-300/10 bg-amber-400/8 text-amber-300"}`}>
            {liveConnected ? <Wifi size={13} /> : <WifiOff size={13} />}
            {liveConnected ? "Автообновление включено" : "Переподключение…"}
          </div>
          <Avatar entityId={user.id} title={`${user.first_name ?? ""} ${user.last_name ?? ""}`} hasImage={user.has_avatar} className="h-9 w-9 text-xs" />
          <div className="hidden leading-tight sm:block">
            <p className="max-w-40 truncate text-sm font-medium text-white">{[user.first_name, user.last_name].filter(Boolean).join(" ")}</p>
            <p className="text-xs text-slate-500">{user.username ? `@${user.username}` : "Telegram"}</p>
          </div>
          <button className="icon-button ml-1" title="Выйти" onClick={() => void logout()}>
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="relative z-10 mx-auto grid h-[calc(100dvh-60px)] min-h-0 max-w-[1600px] overflow-hidden lg:grid-cols-[360px_1fr]">
        <aside className={`${selected ? "hidden lg:flex" : "flex"} min-h-0 min-w-0 flex-col overflow-hidden border-r border-white/8 bg-[#0b1120]/70`}>
          <div className="shrink-0 border-b border-white/8 px-3 py-2.5">
            <div className="flex items-center justify-between">
              <p className="pl-1 text-xs font-medium text-slate-400">{dialogs.length} диалогов</p>
              <button className="icon-button h-8! w-8!" title="Обновить" onClick={() => void loadDialogs()}>
                <RefreshCw className={loadingDialogs ? "animate-spin" : ""} size={15} />
              </button>
            </div>
            <div className="search-field mt-2">
              <Search size={17} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск" />
              {search && <button onClick={() => setSearch("")}><X size={15} /></button>}
            </div>
          </div>

          <div className="scrollbar min-h-0 flex-1 overflow-y-scroll overscroll-contain p-2">
            {loadingDialogs && dialogs.length === 0 ? (
              <ListSkeleton />
            ) : filteredDialogs.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center px-8 text-center text-slate-500">
                <Search size={28} strokeWidth={1.4} />
                <p className="mt-3 text-sm">Диалоги не найдены</p>
              </div>
            ) : (
              filteredDialogs.map((dialog) => (
                <button
                  key={`${dialog.kind}-${dialog.id}`}
                  className={`dialog-row ${selected?.id === dialog.id ? "selected" : ""}`}
                  onClick={() => void chooseDialog(dialog)}
                >
                  <Avatar entityId={dialog.id} title={dialog.title} hasImage={dialog.has_avatar} className="h-11 w-11 shrink-0 text-sm" />
                  <div className="min-w-0 flex-1 text-left">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-slate-100">{dialog.title}</p>
                      {dialog.unread_count > 0 && <span className="unread-badge">{dialog.unread_count > 99 ? "99+" : dialog.unread_count}</span>}
                    </div>
                    <p className="mt-1 flex items-center gap-1.5 truncate text-xs text-slate-500">
                      {dialog.kind === "user" ? <UserRound size={12} /> : dialog.kind === "group" ? <UsersRound size={12} /> : <Radio size={12} />}
                      {dialog.username ? `@${dialog.username}` : dialog.kind === "user" ? "Личный чат" : dialog.kind === "group" ? "Группа" : "Канал"}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className={`${selected ? "flex" : "hidden lg:flex"} min-h-0 min-w-0 flex-col overflow-hidden bg-[#080d1a]/65`}>
          {selected ? (
            <>
              <div className="flex h-[60px] shrink-0 items-center gap-3 border-b border-white/8 bg-[#0d1424]/55 px-4 backdrop-blur-lg sm:px-6">
                <button className="icon-button lg:hidden" onClick={() => setSelected(null)}><ArrowLeft size={19} /></button>
                <Avatar entityId={selected.id} title={selected.title} hasImage={selected.has_avatar} className="h-10 w-10 text-xs" />
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-semibold text-white">{selected.title}</h2>
                  <p className="mt-0.5 text-xs text-slate-500">{selected.username ? `@${selected.username}` : selected.kind === "user" ? "Личный чат" : selected.kind === "group" ? "Группа" : "Канал"}</p>
                </div>
              </div>

              <div ref={messagePane} className="scrollbar relative min-h-0 flex-1 overflow-y-scroll overscroll-contain px-4 py-7 sm:px-8">
                <div className="mx-auto flex min-h-full max-w-4xl flex-col justify-end gap-2">
                  {loadingMessages ? <MessageSkeleton /> : messages.length === 0 ? (
                    <div className="m-auto flex flex-col items-center text-center text-slate-500">
                      <MessageCircle size={34} strokeWidth={1.3} />
                      <p className="mt-3 text-sm">В этом диалоге пока нет сообщений</p>
                    </div>
                  ) : messages.map((message) => <MessageBubble key={message.id} message={message} chatId={selected.id} />)}
                </div>
              </div>

              <div className="border-t border-white/8 bg-[#0b1120]/80 p-3 backdrop-blur-xl sm:p-5">
                <div className="mx-auto flex max-w-4xl items-end gap-2 rounded-2xl border border-white/10 bg-white/[0.045] p-2 focus-within:border-cyan-300/30 focus-within:bg-white/[0.06]">
                  <input ref={fileInput} className="hidden" type="file" onChange={(event) => void uploadFile(event)} />
                  <button className="composer-button" title="Прикрепить файл" disabled={sending} onClick={() => fileInput.current?.click()}>
                    <Paperclip size={19} />
                  </button>
                  <textarea
                    className="scrollbar max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600"
                    rows={1}
                    placeholder="Напишите сообщение…"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void sendMessage();
                      }
                    }}
                  />
                  <button className="send-button" title="Отправить" disabled={!draft.trim() || sending} onClick={() => void sendMessage()}>
                    {sending ? <LoaderCircle className="animate-spin" size={18} /> : <Send size={18} />}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center p-8 text-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-[2rem] border border-cyan-300/15 bg-cyan-300/8 text-cyan-300 shadow-xl shadow-cyan-950/20">
                <MessageCircle size={34} strokeWidth={1.5} />
              </div>
              <h2 className="mt-6 text-xl font-semibold text-white">Выберите диалог</h2>
              <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Откройте беседу слева, чтобы прочитать историю или отправить сообщение.</p>
            </div>
          )}
        </section>
      </main>

      <div className="fixed right-4 bottom-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
        {toasts.map((event) => (
          <div key={event.sequence} className="toast-card">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-300">
              {event.kind === "message_edited" ? <RefreshCw size={16} /> : <MessageCircle size={16} />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">{event.chat_title}</p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">{event.text}</p>
            </div>
            <button className="text-slate-600 hover:text-white" onClick={() => setToasts((items) => items.filter((item) => item.sequence !== event.sequence))}><X size={15} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

function Avatar({
  entityId,
  title,
  hasImage,
  className,
}: {
  entityId: number | string;
  title: string;
  hasImage: boolean;
  className: string;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`avatar relative overflow-hidden ${className}`}>
      {hasImage && !failed ? (
        <img
          className="h-full w-full object-cover"
          src={api.avatarUrl(entityId)}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        initials(title) || "T"
      )}
    </div>
  );
}

function MessageMediaView({
  media,
  chatId,
  messageId,
}: {
  media: MediaInfo;
  chatId: number | string;
  messageId: number;
}) {
  const source = api.messageMediaUrl(chatId, messageId);
  if (media.kind === "photo" || media.kind === "sticker") {
    return (
      <a href={source} target="_blank" rel="noreferrer">
        <img
          className={`mb-2 max-h-[420px] w-auto max-w-full rounded-xl object-contain ${media.kind === "sticker" ? "max-h-48" : ""}`}
          src={source}
          alt={media.filename}
          loading="lazy"
        />
      </a>
    );
  }
  if (media.kind === "video") {
    return <video className="mb-2 max-h-[420px] max-w-full rounded-xl bg-black/30" src={source} controls preload="metadata" />;
  }
  if (media.kind === "audio" || media.kind === "voice") {
    return <audio className="mb-2 h-10 max-w-full" src={source} controls preload="metadata" />;
  }
  return (
    <a className="mb-2 flex items-center gap-3 rounded-xl border border-white/10 bg-black/10 p-3 transition hover:bg-white/5" href={source} download={media.filename}>
      <FileText className="shrink-0 text-cyan-300" size={22} />
      <span className="min-w-0">
        <span className="block truncate text-xs font-medium">{media.filename}</span>
        {media.size !== null && <span className="mt-0.5 block text-[10px] opacity-55">{formatBytes(media.size)}</span>}
      </span>
    </a>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function MessageBubble({ message, chatId }: { message: MessageInfo; chatId: number | string }) {
  return (
    <div className={`flex ${message.outgoing ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[88%] items-end gap-2 sm:max-w-[78%] ${message.outgoing ? "flex-row-reverse" : ""}`}>
        {!message.outgoing && message.sender_id && (
          <Avatar entityId={message.sender_id} title={message.sender_name} hasImage={message.sender_has_avatar} className="mb-0.5 h-7 w-7 shrink-0 text-[9px]" />
        )}
        <div className={`message-bubble max-w-full! ${message.outgoing ? "outgoing" : "incoming"}`}>
          {!message.outgoing && <p className="mb-1 text-xs font-semibold text-cyan-300">{message.sender_name}</p>}
          {message.media && <MessageMediaView media={message.media} chatId={chatId} messageId={message.id} />}
          {message.text !== "(медиа)" && <p className="whitespace-pre-wrap break-words text-sm leading-6">{message.text}</p>}
          <div className={`mt-1 flex items-center justify-end gap-1 text-[10px] ${message.outgoing ? "text-cyan-100/60" : "text-slate-500"}`}>
            {formatTime(message.date)}
            {message.outgoing && <CheckCheck size={13} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function SubmitButton({ busy, label }: { busy: boolean; label: string }) {
  return (
    <button className="primary-button mt-5 w-full" disabled={busy}>
      {busy ? <LoaderCircle className="animate-spin" size={18} /> : <ArrowLeft className="rotate-180" size={18} />}
      {label}
    </button>
  );
}

function ErrorCallout({ message }: { message: string }) {
  return <div className="mt-5 rounded-xl border border-rose-400/15 bg-rose-400/8 px-4 py-3 text-sm text-rose-200">{message}</div>;
}

function SuccessCallout({ message }: { message: string }) {
  return <div className="mt-5 rounded-xl border border-emerald-400/15 bg-emerald-400/8 px-4 py-3 text-sm text-emerald-200">{message}</div>;
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="relative flex items-center gap-3">
      <div className={`${compact ? "h-9 w-9 rounded-xl" : "h-11 w-11 rounded-2xl"} flex items-center justify-center bg-gradient-to-br from-cyan-300 to-indigo-400 text-[#07111d] shadow-lg shadow-cyan-500/15`}>
        <Send size={compact ? 17 : 20} fill="currentColor" />
      </div>
      <div>
        <p className={`${compact ? "text-sm" : "text-base"} font-semibold tracking-tight text-white`}>Telegram Desk</p>
        {!compact && <p className="mt-0.5 text-[11px] tracking-[0.18em] text-slate-500 uppercase">Local client</p>}
      </div>
    </div>
  );
}

function PageBackdrop({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-[#080d1a] p-4 sm:p-8">
      <div className="absolute -top-40 -left-40 h-[34rem] w-[34rem] rounded-full bg-indigo-500/15 blur-[120px]" />
      <div className="absolute -right-52 -bottom-52 h-[38rem] w-[38rem] rounded-full bg-cyan-400/10 blur-[130px]" />
      <div className="relative z-10 flex w-full justify-center">{children}</div>
    </div>
  );
}

function ListSkeleton() {
  return <>{[1, 2, 3, 4, 5].map((item) => <div key={item} className="mb-2 flex animate-pulse items-center gap-3 rounded-2xl px-3 py-3"><div className="h-11 w-11 rounded-2xl bg-white/6" /><div className="flex-1"><div className="h-3 w-2/3 rounded bg-white/7" /><div className="mt-2 h-2.5 w-1/3 rounded bg-white/5" /></div></div>)}</>;
}

function MessageSkeleton() {
  return <div className="flex animate-pulse flex-col gap-3"><div className="h-16 w-2/5 rounded-2xl bg-white/5" /><div className="ml-auto h-20 w-1/2 rounded-2xl bg-cyan-300/7" /><div className="h-14 w-1/3 rounded-2xl bg-white/5" /></div>;
}

export default App;
