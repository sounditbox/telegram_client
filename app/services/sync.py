from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.events.broker import EventBroker
from app.models import EventRecord
from app.storage.repository import TelegramRepository
from app.telegram.gateway import TelegramGateway
from app.telegram.manager import TelegramClientManager


logger = logging.getLogger(__name__)


class PersistingEventPublisher:
    """Stores each Telegram event before exposing it to SSE subscribers."""

    def __init__(self, repository: TelegramRepository, broker: EventBroker) -> None:
        self._repository = repository
        self._broker = broker

    async def publish(self, **event: object) -> EventRecord:
        record = EventRecord(sequence=0, **event)
        await self._repository.store_event(record)
        return await self._broker.publish(**event)


class SynchronizationService:
    def __init__(
        self,
        settings: Settings,
        manager: TelegramClientManager,
        gateway: TelegramGateway,
        repository: TelegramRepository,
    ) -> None:
        self._settings = settings
        self._manager = manager
        self._gateway = gateway
        self._repository = repository
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await self._repository.initialize()
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="telegram-dialog-sync")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def refresh_dialogs(self) -> None:
        if not await self._manager.is_authorized():
            return
        dialogs = await self._gateway.list_dialogs(self._settings.sync_dialog_limit)
        await self._repository.store_dialogs(dialogs)

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.refresh_dialogs()
            except Exception:
                logger.warning("Background Telegram synchronization failed", exc_info=True)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._settings.sync_interval_seconds,
                )
            except TimeoutError:
                pass
