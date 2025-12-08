import logging

from telethon.tl.types import User, Channel, Chat

from .client import client

logger = logging.getLogger(__name__)


async def get_dialogs(limit=20):
    """Получить список чатов"""
    try:
        dialogs = []
        async for dialog in client.iter_dialogs(limit=limit):
            entity = dialog.entity
            title = getattr(entity, 'title', None) or getattr(entity, 'first_name', None) or f"ID: {entity.id}"
            dialog_info = {
                'id': entity.id,
                'title': title,
                'username': getattr(entity, 'username', None),
                'unread_count': dialog.unread_count,
                'is_channel': isinstance(entity, Channel),
                'is_group': isinstance(entity, Chat),
                'is_user': isinstance(entity, User)
            }
            dialogs.append(dialog_info)
        return dialogs
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {e}")
        return []


async def get_chat_participants(chat_id, limit=100):
    """Получить участников чата"""
    try:
        participants = []
        async for user in client.iter_participants(chat_id, limit=limit):
            participant_info = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'is_bot': user.bot,
                'is_admin': getattr(user, 'admin_rights', None) is not None
            }
            participants.append(participant_info)
        return participants
    except Exception as e:
        logger.error(f"Ошибка при получении участников: {e}")
        return []


async def mark_chat_as_read(chat_id):
    """Отметить все сообщения в чате как прочитанные"""
    try:
        entity = await client.get_entity(chat_id)
        await client.send_read_acknowledge(entity)
        logger.info(f"Сообщения в чате {chat_id} отмечены как прочитанные")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отметке сообщений как прочитанных: {e}")
        return False
