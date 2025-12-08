import logging

from fastapi import APIRouter, HTTPException

from telegram import get_client_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/me")
async def get_me():
    """Получить информацию о текущем пользователе"""
    try:
        info = await get_client_info()
        if info:
            return {"status": "success", "data": info}
        else:
            raise HTTPException(status_code=500, detail="Не удалось получить информацию о пользователе")
    except Exception as e:
        logger.error(f"Ошибка в /api/me: {e}")
        raise HTTPException(status_code=500, detail=str(e))
