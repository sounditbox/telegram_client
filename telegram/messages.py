import logging

from telethon.tl.types import User, Channel, Chat

from .client import client

logger = logging.getLogger(__name__)


async def get_chat_messages(chat_id, limit=20):
    """Получить сообщения из чата"""
    try:
        messages = []
        async for message in client.iter_messages(chat_id, limit=limit):
            sender = await message.get_sender()
            sender_name = getattr(sender, 'first_name', None) or getattr(sender, 'title', 'Неизвестно')

            message_info = {
                'id': message.id,
                'text': message.text or '(медиа)',
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'sender_username': getattr(sender, 'username', None),
                'date': message.date.isoformat() if message.date else None,
                'is_reply': message.is_reply,
                'has_media': message.media is not None
            }
            messages.append(message_info)
        return messages
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        return []


async def validate_entity(chat_id: str):
    """
    Проверить существование и доступность entity перед отправкой сообщения
    
    Args:
        chat_id: ID или username чата/пользователя
        
    Returns:
        dict: Информация об entity или None если не найдено
        
    Raises:
        ValueError: Если entity не найдено или недоступно
    """
    try:
        entity = await client.get_entity(chat_id)

        entity_type = "пользователь" if isinstance(entity, User) else \
            "канал" if isinstance(entity, Channel) else \
                "группа" if isinstance(entity, Chat) else "чат"

        return {
            'id': entity.id,
            'type': entity_type,
            'title': getattr(entity, 'title', None) or \
                     getattr(entity, 'first_name', None) or \
                     f"ID: {entity.id}",
            'username': getattr(entity, 'username', None),
            'accessible': True
        }
    except ValueError as e:
        error_msg = str(e)
        if "Cannot find any entity" in error_msg or "No user has" in error_msg:
            raise ValueError(
                f"Не удалось найти чат/пользователя с ID '{chat_id}'. "
                f"Проверьте правильность ID или используйте username (например, @username). "
                f"Для групп используйте формат: -1001234567890"
            ) from e
        raise
    except Exception as e:
        raise ValueError(
            f"Ошибка при проверке чата '{chat_id}': {str(e)}"
        ) from e


async def send_message_to(chat_id: str, message: str):
    """
    Отправка сообщения с проверкой entity
    
    Args:
        chat_id: ID или username чата/пользователя
        message: Текст сообщения
        
    Returns:
        dict: Результат отправки
        
    Raises:
        ValueError: Если entity не найдено или сообщение не отправлено
    """
    try:
        entity_info = await validate_entity(chat_id)
        sent_message = await client.send_message(chat_id, message)

        return {
            'success': True,
            'message_id': sent_message.id,
            'entity_info': entity_info
        }
    except ValueError:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Cannot find any entity" in error_msg:
            raise ValueError(
                f"Не удалось найти чат/пользователя '{chat_id}'. "
                f"Проверьте правильность ID или username."
            ) from e
        raise ValueError(f"Ошибка при отправке сообщения: {error_msg}") from e
