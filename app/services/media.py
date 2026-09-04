from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.telegram.gateway import TelegramGateway


@dataclass(frozen=True, slots=True)
class AvatarContent:
    content: bytes
    media_type: str = "image/jpeg"


@dataclass(frozen=True, slots=True)
class MediaFile:
    path: Path
    media_type: str
    filename: str


class MediaService:
    def __init__(self, settings: Settings, gateway: TelegramGateway) -> None:
        self._settings = settings
        self._gateway = gateway
        self._avatars: dict[str, AvatarContent] = {}
        self._files: dict[str, MediaFile] = {}
        self._avatar_lock = asyncio.Lock()
        self._file_lock = asyncio.Lock()

    async def avatar(self, entity_id: str) -> AvatarContent:
        cached = self._avatars.get(entity_id)
        if cached is not None:
            return cached
        async with self._avatar_lock:
            cached = self._avatars.get(entity_id)
            if cached is None:
                cached = AvatarContent(await self._gateway.download_avatar(entity_id))
                if len(self._avatars) >= 256:
                    self._avatars.pop(next(iter(self._avatars)))
                self._avatars[entity_id] = cached
            return cached

    async def message_media(self, chat_id: str, message_id: int) -> MediaFile:
        key = hashlib.sha256(f"{chat_id}:{message_id}".encode()).hexdigest()
        cached = self._files.get(key)
        if cached is not None and cached.path.is_file():
            return cached

        async with self._file_lock:
            cached = self._files.get(key)
            if cached is not None and cached.path.is_file():
                return cached
            self._settings.media_cache_dir.mkdir(parents=True, exist_ok=True)
            downloaded = await self._gateway.download_message_media(
                chat_id,
                message_id,
                self._settings.media_cache_dir / key,
                self._settings.max_media_bytes,
            )
            result = MediaFile(downloaded.path, downloaded.media_type, downloaded.filename)
            self._files[key] = result
            return result
