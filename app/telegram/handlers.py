from __future__ import annotations

import logging
from typing import Protocol

from telethon import TelegramClient, events

from app.models import EventRecord
from app.telegram.serialization import media_info


logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    async def publish(self, **event: object) -> EventRecord: ...


class TelegramEventHandlers:
    def __init__(self, client: TelegramClient, broker: EventPublisher) -> None:
        self._client = client
        self._broker = broker
        self._registered = False
        self._new_message_callback = self._on_new_message
        self._edited_message_callback = self._on_edited_message

    def register(self) -> None:
        if self._registered:
            return
        self._client.add_event_handler(
            self._new_message_callback,
            events.NewMessage(incoming=True),
        )
        self._client.add_event_handler(
            self._edited_message_callback,
            events.MessageEdited(incoming=True),
        )
        self._registered = True

    def unregister(self) -> None:
        if not self._registered:
            return
        self._client.remove_event_handler(self._new_message_callback)
        self._client.remove_event_handler(self._edited_message_callback)
        self._registered = False

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        await self._publish(event, kind="new_message")

    async def _on_edited_message(self, event: events.MessageEdited.Event) -> None:
        await self._publish(event, kind="message_edited")

    async def _publish(self, event: object, *, kind: str) -> None:
        try:
            sender = await event.get_sender()
            chat = await event.get_chat()
            sender_name = (
                getattr(sender, "first_name", None)
                or getattr(sender, "title", None)
                or "Неизвестно"
            )
            chat_title = (
                getattr(chat, "title", None)
                or getattr(chat, "first_name", None)
                or sender_name
            )
            message_media = media_info(event.message)
            await self._broker.publish(
                kind=kind,
                message_id=event.id,
                chat_id=event.chat_id,
                text=event.text or "(медиа)",
                sender_id=event.sender_id,
                sender_name=sender_name,
                sender_username=getattr(sender, "username", None),
                sender_has_avatar=getattr(sender, "photo", None) is not None,
                chat_title=chat_title,
                date=event.date,
                outgoing=bool(event.message.out),
                has_media=message_media is not None,
                media=message_media,
            )
            logger.info(
                "Telegram event received: kind=%s chat_id=%s message_id=%s",
                kind,
                event.chat_id,
                event.id,
            )
        except Exception:
            logger.exception("Failed to process a Telegram event")
