# Telegram Desk

Локальный веб-клиент Telegram на Telethon, FastAPI и React. Приложение рассчитано на один Telegram-аккаунт в одном процессе: сессия хранится на компьютере, а интерфейс доступен локально.

## Запуск

Требуется Python 3.12–3.14, Node.js 22+ и установленное окружение проекта.

```powershell
# корень проекта: D:\_\Work\PyRush\M4PyRockstars\telegram-client
cd frontend
npm install
npm run build
cd ..
.\.venv\Scripts\python.exe run.py
```

После запуска откройте <http://127.0.0.1:8000/>.

Если проект устанавливается с нуля, используйте `uv sync`, который читает зафиксированный `uv.lock`. `requirements.txt` оставлен для pip-сценариев. Frontend собирается в `frontend/dist`; этот каталог не хранится в Git.

## Конфигурация

Скопируйте `.env.example` в `.env` и укажите `API_ID`, `API_HASH` и имя сессии.

По умолчанию сервер слушает только `127.0.0.1`. При внешнем `APP_HOST` обязательно задайте длинный случайный `ACCESS_TOKEN`; интерфейс попросит этот ключ при открытии.

Основные параметры: `APP_HOST`, `APP_PORT`, `APP_RELOAD`, `SESSION_DIR`, `UPLOAD_DIR`, `MEDIA_CACHE_DIR`, `DATABASE_PATH`, `MAX_UPLOAD_BYTES`, `MAX_MEDIA_BYTES`, `SYNC_INTERVAL_SECONDS`, `SYNC_DIALOG_LIMIT` и `AUTH_ATTEMPT_TTL_SECONDS`.

Сессионный файл содержит ключ авторизации Telegram. Не добавляйте его в Git и не публикуйте каталог `data/`.

## Архитектура

```text
FastAPI routes / React UI / SSE
              ↓
       application services
              ↓
 SQLite repositories ← sync service ← TelegramGateway ← Telethon

Telethon handlers → persistent event publisher → SQLite → EventBroker → SSE
```

- `app/main.py` создаёт приложение и управляет lifespan.
- `app/telegram/manager.py` — единственный владелец клиента, подключения и logout.
- `app/telegram/gateway.py` — адаптер Telethon: нормализует chat ID, сущности и сообщения.
- `app/services/` — use-case слой (`AuthService`, `MessagingService`, `DialogService`, `FileService`, `MediaService`, `SynchronizationService`).
- `app/storage/` — локальная SQLite-проекция диалогов и сообщений, используемая сервисным слоем.
- `app/services/sync.py` — фоновая синхронизация Telegram и сохранение событий перед SSE-публикацией.
- `app/api/routes/` — тонкие HTTP-роутеры без импорта Telethon и глобального состояния.
- `app/events/broker.py` — bounded event store и SSE-потоки с монотонным sequence ID.
- `frontend/src/` — React + TypeScript + Tailwind CSS 4 + Lucide; список диалогов и история имеют независимую прокрутку.

Новые сообщения приходят в интерфейс через SSE и сразу добавляются в открытый чат. Последовательность событий сохраняется в SQLite, а клиент передаёт `Last-Event-ID`, поэтому после переподключения или перезапуска сервера поток продолжается без дублей. После восстановления соединения frontend сверяет открытую историю и список диалогов с Telegram. Аватары и вложения загружаются лениво; файлы сообщений кэшируются в `MEDIA_CACHE_DIR` и ограничиваются `MAX_MEDIA_BYTES`.

Один процесс/worker обязателен для одной SQLite-сессии Telethon. Многопользовательский режим потребует отдельной сессии и хранилища на каждого пользователя.

## API

Все `/api/*`, кроме `/api/health`, возвращают единый контракт:

```json
{"ok": true, "data": {}}
```

Ошибки имеют вид `{"ok": false, "error": {"code": "...", "message": "..."}}`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/health` | Проверка процесса |
| `GET` | `/api/auth/status` | Статус Telegram-сессии |
| `POST` | `/api/auth/code` | Запросить код (`phone`, `resend`) |
| `POST` | `/api/auth/code/verify` | Подтвердить код |
| `POST` | `/api/auth/password/verify` | Подтвердить 2FA-пароль |
| `POST` | `/api/auth/logout` | Удалить Telegram-сессию |
| `GET` | `/api/dialogs` | Список диалогов |
| `GET` | `/api/dialogs/{chat_id}/messages` | История чата |
| `POST` | `/api/messages` | Отправить текст |
| `POST` | `/api/messages/broadcast` | Рассылка с результатом по каждому чату |
| `POST` | `/api/files` | Отправить файл с ограничением размера |
| `GET` | `/api/media/avatars/{entity_id}` | Аватар пользователя или диалога |
| `GET` | `/api/media/dialogs/{chat_id}/messages/{message_id}` | Вложение сообщения |
| `GET` | `/api/events/stream` | SSE-поток событий |

Списки диалогов и сообщений используют курсорную пагинацию: `cursor` передаётся из `next_cursor` предыдущего ответа. Для диалогов доступен локальный поиск через параметр `query`, а `refresh=true` принудительно обновляет первую страницу из Telegram.

## Проверки

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
cd frontend
npm run build
npx playwright install chromium  # один раз на новой машине
npm run test:e2e
```

Backend-тесты проверяют сервисный слой, SQLite-репозиторий, тонкость роутеров, авторизацию и 2FA, безопасность файлов, event broker, обработчики событий и медиакэш. Playwright-сценарии проверяют положение и прокрутку диалогов, курсорную историю и доставку сообщения через SSE. Оба набора используют тестовые реализации Telegram API и не требуют входа в Telegram.
