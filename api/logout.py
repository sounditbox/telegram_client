import logging
import os

from fastapi import APIRouter, HTTPException

from config import SESSION_NAME
from telegram import client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/logout-telegram")
async def logout_telegram():
    """
    Разлогиниться из Telegram (удалить сессию)
    После этого потребуется авторизация заново
    """
    try:
        # Отключаем клиент
        if client.is_connected():
            await client.disconnect()
            logger.info("Telethon клиент отключен")

        # Удаляем файлы сессии
        session_file = f"{SESSION_NAME}.session"
        session_journal = f"{SESSION_NAME}.session-journal"

        deleted_files = []

        if os.path.exists(session_file):
            os.remove(session_file)
            deleted_files.append(session_file)
            logger.info(f"Удален файл сессии: {session_file}")

        if os.path.exists(session_journal):
            os.remove(session_journal)
            deleted_files.append(session_journal)
            logger.info(f"Удален файл журнала сессии: {session_journal}")

        return {
            "status": "success",
            "message": "Сессия удалена. Перезапустите приложение для авторизации под другим аккаунтом.",
            "deleted_files": deleted_files
        }
    except Exception as e:
        logger.error(f"Ошибка при разлогинивании: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при разлогинивании: {str(e)}")
