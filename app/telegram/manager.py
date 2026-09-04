from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient

from app.core.config import Settings
from app.core.errors import NotAuthorized, TelegramUnavailable
from app.events.broker import EventBroker
from app.telegram.handlers import TelegramEventHandlers


logger = logging.getLogger(__name__)


class TelegramClientManager:
    def __init__(self, settings: Settings, broker: EventBroker) -> None:
        self._settings = settings
        self._broker = broker
        self._client: TelegramClient | None = None
        self._handlers: TelegramEventHandlers | None = None
        self._lifecycle_lock = asyncio.Lock()

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            raise TelegramUnavailable()
        return self._client

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    async def start(self) -> None:
        async with self._lifecycle_lock:
            if self._client is None:
                self._settings.session_dir.mkdir(parents=True, exist_ok=True)
                self._client = TelegramClient(
                    str(self._settings.session_path),
                    self._settings.api_id,
                    self._settings.api_hash.get_secret_value(),
                )
                self._handlers = TelegramEventHandlers(self._client, self._broker)
                self._handlers.register()

            if not self._client.is_connected():
                try:
                    await self._client.connect()
                except Exception:
                    logger.warning("Could not connect to Telegram during startup", exc_info=True)

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            if self._handlers is not None:
                self._handlers.unregister()
                self._handlers = None
            if self._client is not None and self._client.is_connected():
                await self._client.disconnect()
            self._client = None

    async def ensure_connected(self) -> TelegramClient:
        if self._client is None:
            await self.start()
        client = self.client
        if not client.is_connected():
            try:
                await client.connect()
            except Exception as exc:
                logger.warning("Could not connect to Telegram: %s", type(exc).__name__)
                raise TelegramUnavailable() from exc
        return client

    async def is_authorized(self) -> bool:
        client = await self.ensure_connected()
        try:
            return await client.is_user_authorized()
        except Exception as exc:
            raise TelegramUnavailable() from exc

    async def require_authorized(self) -> TelegramClient:
        client = await self.ensure_connected()
        if not await client.is_user_authorized():
            raise NotAuthorized()
        return client

    async def log_out_and_restart(self) -> None:
        async with self._lifecycle_lock:
            client = self._client
            handlers = self._handlers
            if handlers is not None:
                handlers.unregister()

            if client is not None:
                try:
                    if client.is_connected() and await client.is_user_authorized():
                        await client.log_out()
                    elif client.is_connected():
                        await client.disconnect()
                finally:
                    self._client = None
                    self._handlers = None

            self._remove_session_files()

        await self.start()

    def _remove_session_files(self) -> None:
        session_file = Path(f"{self._settings.session_path}.session")
        journal_file = Path(f"{session_file}-journal")
        session_file.unlink(missing_ok=True)
        journal_file.unlink(missing_ok=True)
