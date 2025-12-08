import logging

from fastapi import APIRouter, HTTPException

from telegram import get_dialogs, get_chat_participants, mark_chat_as_read

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dialogs"])


@router.get("/dialogs")
async def get_dialogs_endpoint(limit: int = 20):
    """Получить список диалогов"""
    try:
        dialogs = await get_dialogs(limit=limit)
        return {"status": "success", "data": dialogs, "count": len(dialogs)}
    except Exception as e:
        logger.error(f"Ошибка в /api/dialogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/participants")
async def get_participants(chat_id: str, limit: int = 100):
    """Получить участников чата"""
    try:
        participants = await get_chat_participants(chat_id, limit=limit)
        return {"status": "success", "data": participants, "count": len(participants)}
    except Exception as e:
        logger.error(f"Ошибка при получении участников: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/mark-read")
async def mark_read(chat_id: str):
    """Отметить все сообщения в чате как прочитанные"""
    try:
        success = await mark_chat_as_read(chat_id)
        if success:
            return {"status": "success", "message": "Сообщения отмечены как прочитанные"}
        else:
            raise HTTPException(status_code=500, detail="Не удалось отметить сообщения как прочитанные")
    except Exception as e:
        logger.error(f"Ошибка при отметке сообщений как прочитанных: {e}")
        raise HTTPException(status_code=500, detail=str(e))
