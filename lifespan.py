import logging
import os
from contextlib import asynccontextmanager

from config import SESSION_NAME
from telegram import client, setup_event_handlers, get_client_info

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Управление жизненным циклом приложения"""
    try:
        session_file = f"{SESSION_NAME}.session"

        if os.path.exists(session_file):
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    logger.warning(
                        "Сессия найдена, но клиент не авторизован. Требуется авторизация через веб-интерфейс.")
                    await client.disconnect()
                else:
                    logger.info("Telethon клиент успешно подключен")
                    setup_event_handlers()
                    me = await get_client_info()
                    if me:
                        logger.info(
                            f"Вошли как: {me.get('first_name', 'Неизвестно')} (@{me.get('username', 'без username')})")
            except Exception as connect_error:
                logger.warning(f"Не удалось подключиться с существующей сессией: {connect_error}")
                logger.info("Требуется авторизация через веб-интерфейс")
        else:
            logger.info("Файл сессии не найден. Требуется авторизация через веб-интерфейс.")

    except Exception as e:
        logger.warning(f"Ошибка при инициализации клиента: {e}")
        logger.info("Требуется авторизация через веб-интерфейс")

    yield

    try:
        await client.disconnect()
        logger.info("Telethon клиент остановлен")
    except Exception as e:
        logger.error(f"Ошибка при остановке клиента: {e}")
