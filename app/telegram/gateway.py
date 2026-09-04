from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from telethon import errors, utils
from telethon.tl.types import Channel, Chat, DocumentAttributeFilename, User

from app.core.errors import EntityNotFound, MediaNotFound, MediaTooLarge, RateLimited
from app.models import DialogInfo, EntityInfo, MessageInfo, SentMessage, UserInfo
from app.telegram.manager import TelegramClientManager
from app.telegram.serialization import media_info


@dataclass(slots=True)
class DownloadedMedia:
    path: Path
    media_type: str
    filename: str


class TelegramGateway:
    def __init__(self, manager: TelegramClientManager) -> None:
        self._manager = manager

    async def ensure_ready(self) -> None:
        await self._manager.require_authorized()

    async def get_me(self) -> UserInfo:
        client = await self._manager.require_authorized()
        me = await client.get_me()
        return UserInfo(
            id=me.id,
            first_name=me.first_name,
            last_name=me.last_name,
            username=me.username,
            is_bot=bool(me.bot),
            has_avatar=me.photo is not None,
        )

    async def list_dialogs(self, limit: int) -> list[DialogInfo]:
        client = await self._manager.require_authorized()
        result: list[DialogInfo] = []
        async for dialog in client.iter_dialogs(limit=limit):
            entity = dialog.entity
            result.append(
                DialogInfo(
                    id=utils.get_peer_id(entity),
                    title=self._title(entity),
                    username=getattr(entity, "username", None),
                    unread_count=dialog.unread_count,
                    kind=self._kind(entity),
                    has_avatar=getattr(entity, "photo", None) is not None,
                )
            )
        return result

    async def list_messages(self, reference: str, limit: int) -> list[MessageInfo]:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        result: list[MessageInfo] = []
        async for message in client.iter_messages(entity, limit=limit):
            sender = await message.get_sender()
            result.append(
                MessageInfo(
                    id=message.id,
                    text=message.text or "(медиа)",
                    sender_id=message.sender_id,
                    sender_name=self._title(sender),
                    sender_username=getattr(sender, "username", None),
                    sender_has_avatar=getattr(sender, "photo", None) is not None,
                    date=message.date,
                    outgoing=bool(message.out),
                    is_reply=bool(message.is_reply),
                    has_media=message.media is not None,
                    media=media_info(message),
                )
            )
        return result

    async def list_participants(self, reference: str, limit: int) -> list[UserInfo]:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        result: list[UserInfo] = []
        async for user in client.iter_participants(entity, limit=limit):
            result.append(
                UserInfo(
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    is_bot=bool(user.bot),
                    has_avatar=user.photo is not None,
                )
            )
        return result

    async def mark_read(self, reference: str) -> None:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        await client.send_read_acknowledge(entity)

    async def entity_info(self, reference: str) -> EntityInfo:
        entity = await self._resolve_entity(reference)
        return self._entity_info(entity)

    async def send_message(self, reference: str, text: str) -> SentMessage:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        message = await client.send_message(entity, text)
        return SentMessage(message_id=message.id, entity=self._entity_info(entity))

    async def send_file(
        self,
        reference: str,
        path: Path,
        *,
        filename: str,
        caption: str,
    ) -> int:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        message = await client.send_file(
            entity,
            str(path),
            caption=caption or None,
            attributes=[DocumentAttributeFilename(file_name=filename)],
        )
        return message.id

    async def download_avatar(self, reference: str) -> bytes:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        content = await client.download_profile_photo(entity, file=bytes)
        if not content:
            raise MediaNotFound()
        return content

    async def download_message_media(
        self,
        reference: str,
        message_id: int,
        destination_stem: Path,
        max_bytes: int,
    ) -> DownloadedMedia:
        client = await self._manager.require_authorized()
        entity = await self._resolve_entity(reference)
        message = await client.get_messages(entity, ids=message_id)
        if message is None:
            raise MediaNotFound()
        info = media_info(message)
        if info is None:
            raise MediaNotFound()
        if info.size is not None and info.size > max_bytes:
            raise MediaTooLarge(max_bytes)

        suffix = Path(info.filename).suffix or mimetypes.guess_extension(info.mime_type) or ".bin"
        destination = destination_stem.with_suffix(suffix[:16])
        downloaded = await client.download_media(message, file=str(destination))
        if not downloaded or not destination.is_file():
            raise MediaNotFound()
        if destination.stat().st_size > max_bytes:
            destination.unlink(missing_ok=True)
            raise MediaTooLarge(max_bytes)
        return DownloadedMedia(
            path=destination,
            media_type=info.mime_type,
            filename=info.filename,
        )

    async def _resolve_entity(self, reference: str) -> object:
        client = await self._manager.require_authorized()
        normalized: str | int = reference.strip()
        if normalized.lstrip("-").isdigit():
            normalized = int(normalized)
        try:
            return await client.get_entity(normalized)
        except (ValueError, TypeError) as exc:
            raise EntityNotFound(reference) from exc

    @staticmethod
    def _title(entity: object | None) -> str:
        if entity is None:
            return "Неизвестно"
        return (
            getattr(entity, "title", None)
            or " ".join(
                part
                for part in (
                    getattr(entity, "first_name", None),
                    getattr(entity, "last_name", None),
                )
                if part
            )
            or f"ID {getattr(entity, 'id', '—')}"
        )

    @staticmethod
    def _kind(entity: object) -> str:
        if isinstance(entity, User):
            return "user"
        if isinstance(entity, Chat) or (isinstance(entity, Channel) and entity.megagroup):
            return "group"
        return "channel"

    def _entity_info(self, entity: object) -> EntityInfo:
        return EntityInfo(
            id=utils.get_peer_id(entity),
            title=self._title(entity),
            username=getattr(entity, "username", None),
            kind=self._kind(entity),
        )

def translate_flood_wait(exc: errors.FloodWaitError) -> RateLimited:
    return RateLimited(exc.seconds)
