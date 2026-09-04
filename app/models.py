from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiEnvelope(BaseModel, Generic[T]):
    ok: Literal[True] = True
    data: T


class UserInfo(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    is_bot: bool = False
    has_avatar: bool = False


class AuthStatus(BaseModel):
    connected: bool
    authenticated: bool
    phase: Literal["idle", "code_sent", "password_required", "authorized"]
    user: UserInfo | None = None


class AuthAction(BaseModel):
    phase: Literal["idle", "code_sent", "password_required", "authorized"]
    message: str


class DialogInfo(BaseModel):
    id: int
    title: str
    username: str | None = None
    unread_count: int = 0
    kind: Literal["user", "group", "channel"]
    has_avatar: bool = False


class MediaInfo(BaseModel):
    kind: Literal["photo", "video", "audio", "voice", "sticker", "document"]
    mime_type: str
    filename: str
    size: int | None = None


class MessageInfo(BaseModel):
    id: int
    text: str
    sender_id: int | None = None
    sender_name: str
    sender_username: str | None = None
    sender_has_avatar: bool = False
    date: datetime | None = None
    outgoing: bool = False
    is_reply: bool = False
    has_media: bool = False
    media: MediaInfo | None = None


class EntityInfo(BaseModel):
    id: int
    title: str
    username: str | None = None
    kind: Literal["user", "group", "channel"]


class SentMessage(BaseModel):
    message_id: int
    entity: EntityInfo


class BroadcastRecipient(BaseModel):
    chat_id: str
    sent: bool
    message_id: int | None = None
    error: str | None = None


class BroadcastResult(BaseModel):
    total: int
    sent: int
    failed: int
    recipients: list[BroadcastRecipient]


class FileResult(BaseModel):
    message_id: int
    filename: str
    size: int


class EventRecord(BaseModel):
    sequence: int
    kind: Literal["new_message", "message_edited"]
    message_id: int
    chat_id: int | None = None
    text: str
    sender_id: int | None = None
    sender_name: str
    sender_username: str | None = None
    sender_has_avatar: bool = False
    chat_title: str
    date: datetime | None = None
    outgoing: bool = False
    has_media: bool = False
    media: MediaInfo | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    ok: Literal[False] = False
    error: ErrorBody


class HealthInfo(BaseModel):
    status: Literal["ok"] = "ok"
