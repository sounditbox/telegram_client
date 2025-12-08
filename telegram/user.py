import logging

from .client import client

logger = logging.getLogger(__name__)


async def get_client_info():
    """Получить информацию о текущем пользователе"""
    try:
        me = await client.get_me()
        return {
            'id': me.id,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'username': me.username,
            'phone': me.phone,
            'is_bot': me.bot
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о клиенте: {e}")
        return None
