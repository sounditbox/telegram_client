import logging

from telethon import events

from .client import client
from .events import add_event

logger = logging.getLogger(__name__)


def setup_event_handlers():
    """Настройка обработчиков событий Telethon"""

    @client.on(events.NewMessage(incoming=True))
    async def new_message_handler(event):
        """Обработчик новых входящих сообщений"""
        try:
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Неизвестно') or 'Неизвестно'
            sender_username = getattr(sender, 'username', None)

            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Личные сообщения')

            event_data = {
                'type': 'new_message',
                'message_id': event.id,
                'text': event.text or '(медиа)',
                'sender_id': event.sender_id,
                'sender_name': sender_name,
                'sender_username': sender_username,
                'chat_title': chat_title,
                'date': event.date.isoformat() if event.date else None
            }

            add_event(event_data)
            logger.info(f"Новое сообщение от {sender_name} в {chat_title}: {event.text}")

            # Пример автоответа на ключевые слова
            if event.text and 'вопрос' in event.text.lower():
                await event.reply('Если у вас есть вопрос, задайте его нашему менеджеру.')

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")

    @client.on(events.MessageEdited(incoming=True))
    async def edited_message_handler(event):
        """Обработчик отредактированных сообщений"""
        try:
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Неизвестно') or 'Неизвестно'

            event_data = {
                'type': 'message_edited',
                'message_id': event.id,
                'text': event.text or '(медиа)',
                'sender_id': event.sender_id,
                'sender_name': sender_name,
                'date': event.date.isoformat() if event.date else None
            }

            add_event(event_data)
            logger.info(f"Сообщение отредактировано пользователем {sender_name}")
        except Exception as e:
            logger.error(f"Ошибка при обработке отредактированного сообщения: {e}")
