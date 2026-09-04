from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from telethon import errors

from app.core.config import Settings
from app.core.errors import ApplicationError, InvalidUpload
from app.events.broker import EventBroker
from app.models import (
    BroadcastRecipient,
    BroadcastResult,
    CursorPage,
    DialogInfo,
    EntityInfo,
    FileResult,
    MessageInfo,
    SentMessage,
    UserInfo,
)
from app.storage.repository import TelegramRepository
from app.telegram.gateway import TelegramGateway


class AccountService:
    def __init__(self, gateway: TelegramGateway) -> None:
        self._gateway = gateway

    async def current_user(self) -> UserInfo:
        return await self._gateway.get_me()


class DialogService:
    def __init__(self, gateway: TelegramGateway, repository: TelegramRepository) -> None:
        self._gateway = gateway
        self._repository = repository

    async def list(
        self,
        limit: int,
        *,
        cursor: int = 0,
        query: str | None = None,
        refresh: bool = False,
    ) -> CursorPage[DialogInfo]:
        if refresh and cursor == 0 and not query:
            dialogs = await self._gateway.list_dialogs(max(limit + 1, 100))
            await self._repository.store_dialogs(dialogs)

        cached = await self._repository.list_dialogs(
            limit + 1,
            cursor=cursor,
            query=query,
        )
        if len(cached) <= limit and not query:
            remote = await self._gateway.list_dialogs(cursor + limit + 1)
            await self._repository.store_dialogs(remote)
            cached = remote[cursor : cursor + limit + 1]

        items = cached[:limit]
        has_more = len(cached) > limit
        return CursorPage(
            items=items,
            has_more=has_more,
            next_cursor=cursor + len(items) if has_more else None,
        )

    async def messages(
        self,
        chat_id: str,
        limit: int,
        *,
        before_id: int | None = None,
        refresh: bool = False,
    ) -> CursorPage[MessageInfo]:
        cached = await self._repository.list_messages(
            chat_id,
            limit + 1,
            before_id=before_id,
        )
        if refresh or len(cached) <= limit:
            remote = await self._gateway.list_messages(
                chat_id,
                limit + 1,
                before_id=before_id,
            )
            await self._repository.store_messages(chat_id, remote)
            cached = remote

        items = cached[:limit]
        has_more = len(cached) > limit
        return CursorPage(
            items=items,
            has_more=has_more,
            next_cursor=items[-1].id if has_more and items else None,
        )

    async def participants(self, chat_id: str, limit: int) -> list[UserInfo]:
        return await self._gateway.list_participants(chat_id, limit)

    async def mark_read(self, chat_id: str) -> None:
        await self._gateway.mark_read(chat_id)


class MessagingService:
    def __init__(self, gateway: TelegramGateway) -> None:
        self._gateway = gateway

    async def send(self, chat_id: str, text: str) -> SentMessage:
        return await self._gateway.send_message(chat_id, text)

    async def entity(self, reference: str) -> EntityInfo:
        return await self._gateway.entity_info(reference)

    async def broadcast(self, chat_ids: list[str], text: str) -> BroadcastResult:
        await self._gateway.ensure_ready()
        results: list[BroadcastRecipient] = []
        for chat_id in chat_ids:
            try:
                sent = await self._gateway.send_message(chat_id, text)
                results.append(
                    BroadcastRecipient(
                        chat_id=chat_id,
                        sent=True,
                        message_id=sent.message_id,
                    )
                )
            except ApplicationError as exc:
                results.append(
                    BroadcastRecipient(chat_id=chat_id, sent=False, error=exc.message)
                )
            except errors.FloodWaitError as exc:
                results.append(
                    BroadcastRecipient(
                        chat_id=chat_id,
                        sent=False,
                        error=f"Лимит Telegram: повторите через {exc.seconds} сек.",
                    )
                )
            except errors.RPCError:
                results.append(
                    BroadcastRecipient(
                        chat_id=chat_id,
                        sent=False,
                        error="Telegram отклонил отправку",
                    )
                )

        sent_count = sum(item.sent for item in results)
        return BroadcastResult(
            total=len(results),
            sent=sent_count,
            failed=len(results) - sent_count,
            recipients=results,
        )


class FileService:
    _chunk_size = 1024 * 1024

    def __init__(self, settings: Settings, gateway: TelegramGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    async def send(
        self,
        chat_id: str,
        upload: UploadFile,
        *,
        caption: str,
    ) -> FileResult:
        filename = self._safe_filename(upload.filename)
        suffix = Path(filename).suffix[:16]
        self._settings.upload_dir.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="telegram-upload-",
            suffix=suffix,
            dir=self._settings.upload_dir,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        size = 0

        try:
            async with aiofiles.open(temporary_path, "wb") as target:
                while chunk := await upload.read(self._chunk_size):
                    size += len(chunk)
                    if size > self._settings.max_upload_bytes:
                        raise InvalidUpload(
                            f"Файл превышает лимит {self._settings.max_upload_bytes // (1024 * 1024)} МБ"
                        )
                    await target.write(chunk)

            if size == 0:
                raise InvalidUpload("Нельзя отправить пустой файл")

            message_id = await self._gateway.send_file(
                chat_id,
                temporary_path,
                filename=filename,
                caption=caption,
            )
            return FileResult(message_id=message_id, filename=filename, size=size)
        finally:
            await upload.close()
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        clean = Path(filename or "file").name
        clean = "".join(char for char in clean if char.isprintable() and char not in "<>:\"/\\|?*")
        return clean[:180] or "file"


class EventService:
    def __init__(self, broker: EventBroker) -> None:
        self._broker = broker

    def stream(self, after: int = 0) -> AsyncIterator[str]:
        return self._broker.stream(after)
