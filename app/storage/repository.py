from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models import DialogInfo, EventRecord, MediaInfo, MessageInfo


_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS dialogs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    username TEXT,
    unread_count INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL,
    has_avatar INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    chat_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    sender_id INTEGER,
    sender_name TEXT NOT NULL,
    sender_username TEXT,
    sender_has_avatar INTEGER NOT NULL DEFAULT 0,
    date TEXT,
    outgoing INTEGER NOT NULL DEFAULT 0,
    is_reply INTEGER NOT NULL DEFAULT 0,
    has_media INTEGER NOT NULL DEFAULT 0,
    media_json TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_dialogs_position ON dialogs(position, id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_message
    ON messages(chat_id, message_id DESC);
"""


class TelegramRepository:
    """SQLite-backed local projection of Telegram dialogs and messages."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._write_lock = asyncio.Lock()

    async def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._initialize_sync)

    async def store_dialogs(self, dialogs: Iterable[DialogInfo]) -> None:
        values = list(dialogs)
        if not values:
            return
        async with self._write_lock:
            await asyncio.to_thread(self._store_dialogs_sync, values)

    async def list_dialogs(
        self,
        limit: int,
        *,
        cursor: int = 0,
        query: str | None = None,
    ) -> list[DialogInfo]:
        rows = await asyncio.to_thread(self._query_dialogs_sync, limit, cursor, query)
        return [
            DialogInfo(
                id=row["id"],
                title=row["title"],
                username=row["username"],
                unread_count=row["unread_count"],
                kind=row["kind"],
                has_avatar=bool(row["has_avatar"]),
            )
            for row in rows
        ]

    async def store_messages(self, chat_id: str | int, messages: Iterable[MessageInfo]) -> None:
        values = list(messages)
        if not values:
            return
        async with self._write_lock:
            await asyncio.to_thread(self._store_messages_sync, str(chat_id), values)

    async def store_event(self, event: EventRecord) -> None:
        if event.chat_id is None:
            return
        message = MessageInfo(
            id=event.message_id,
            text=event.text,
            sender_id=event.sender_id,
            sender_name=event.sender_name,
            sender_username=event.sender_username,
            sender_has_avatar=event.sender_has_avatar,
            date=event.date,
            outgoing=event.outgoing,
            has_media=event.has_media,
            media=event.media,
        )
        await self.store_messages(event.chat_id, [message])

    async def list_messages(
        self,
        chat_id: str | int,
        limit: int,
        *,
        before_id: int | None = None,
    ) -> list[MessageInfo]:
        rows = await asyncio.to_thread(
            self._query_messages_sync,
            str(chat_id),
            limit,
            before_id,
        )
        return [self._message_from_row(row) for row in rows]

    async def clear(self) -> None:
        if not self._database_path.exists():
            return
        async with self._write_lock:
            await asyncio.to_thread(self._clear_sync)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize_sync(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(_SCHEMA)

    def _store_dialogs_sync(self, dialogs: list[DialogInfo]) -> None:
        timestamp = datetime.now(UTC).isoformat()
        rows = [
            (
                dialog.id,
                dialog.title,
                dialog.username,
                dialog.unread_count,
                dialog.kind,
                int(dialog.has_avatar),
                position,
                timestamp,
            )
            for position, dialog in enumerate(dialogs)
        ]
        with closing(self._connect()) as connection:
            connection.executemany(
                """
                INSERT INTO dialogs (
                    id, title, username, unread_count, kind, has_avatar, position, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    username=excluded.username,
                    unread_count=excluded.unread_count,
                    kind=excluded.kind,
                    has_avatar=excluded.has_avatar,
                    position=excluded.position,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
            connection.commit()

    def _query_dialogs_sync(
        self,
        limit: int,
        cursor: int,
        query: str | None,
    ) -> list[sqlite3.Row]:
        statement = "SELECT * FROM dialogs"
        params: list[Any] = []
        if query:
            statement += " WHERE title LIKE ? ESCAPE '\\' OR username LIKE ? ESCAPE '\\'"
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            params.extend([pattern, pattern])
        statement += " ORDER BY position, id LIMIT ? OFFSET ?"
        params.extend([limit, cursor])
        with closing(self._connect()) as connection:
            return connection.execute(statement, params).fetchall()

    def _store_messages_sync(self, chat_id: str, messages: list[MessageInfo]) -> None:
        timestamp = datetime.now(UTC).isoformat()
        rows = [self._message_row(chat_id, message, timestamp) for message in messages]
        with closing(self._connect()) as connection:
            connection.executemany(
                """
                INSERT INTO messages (
                    chat_id, message_id, text, sender_id, sender_name, sender_username,
                    sender_has_avatar, date, outgoing, is_reply, has_media, media_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    text=excluded.text,
                    sender_id=excluded.sender_id,
                    sender_name=excluded.sender_name,
                    sender_username=excluded.sender_username,
                    sender_has_avatar=excluded.sender_has_avatar,
                    date=excluded.date,
                    outgoing=excluded.outgoing,
                    is_reply=excluded.is_reply,
                    has_media=excluded.has_media,
                    media_json=excluded.media_json,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
            connection.commit()

    def _query_messages_sync(
        self,
        chat_id: str,
        limit: int,
        before_id: int | None,
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM messages WHERE chat_id = ?"
        params: list[Any] = [chat_id]
        if before_id is not None:
            query += " AND message_id < ?"
            params.append(before_id)
        query += " ORDER BY message_id DESC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as connection:
            return connection.execute(query, params).fetchall()

    def _clear_sync(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM messages")
            connection.execute("DELETE FROM dialogs")
            connection.commit()

    @staticmethod
    def _message_row(
        chat_id: str,
        message: MessageInfo,
        timestamp: str,
    ) -> tuple[Any, ...]:
        media_json = (
            json.dumps(message.media.model_dump(mode="json"), ensure_ascii=False)
            if message.media is not None
            else None
        )
        return (
            chat_id,
            message.id,
            message.text,
            message.sender_id,
            message.sender_name,
            message.sender_username,
            int(message.sender_has_avatar),
            message.date.isoformat() if message.date else None,
            int(message.outgoing),
            int(message.is_reply),
            int(message.has_media),
            media_json,
            timestamp,
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> MessageInfo:
        media = MediaInfo.model_validate(json.loads(row["media_json"])) if row["media_json"] else None
        return MessageInfo(
            id=row["message_id"],
            text=row["text"],
            sender_id=row["sender_id"],
            sender_name=row["sender_name"],
            sender_username=row["sender_username"],
            sender_has_avatar=bool(row["sender_has_avatar"]),
            date=row["date"],
            outgoing=bool(row["outgoing"]),
            is_reply=bool(row["is_reply"]),
            has_media=bool(row["has_media"]),
            media=media,
        )
