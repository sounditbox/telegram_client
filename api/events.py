import logging

from fastapi import APIRouter, HTTPException

from telegram import get_recent_events, remove_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def get_events():
    """Получить последние события"""
    try:
        events = get_recent_events()
        return {"status": "success", "data": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Ошибка при получении событий: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{message_id}")
async def delete_event(message_id: int):
    """Удалить событие по message_id"""
    try:
        success = remove_event(message_id)
        if success:
            return {"status": "success", "message": "Событие удалено"}
        else:
            return {"status": "error", "message": "Событие не найдено"}
    except Exception as e:
        logger.error(f"Ошибка при удалении события: {e}")
        raise HTTPException(status_code=500, detail=str(e))
