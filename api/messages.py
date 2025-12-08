import asyncio
import logging

from fastapi import APIRouter, HTTPException, Form

from models import SendMessageRequest, BroadcastRequest
from telegram import get_chat_messages, send_message_to, client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["messages"])


@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 20):
    """Получить сообщения из чата"""
    try:
        messages = await get_chat_messages(chat_id, limit=limit)
        return {"status": "success", "data": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-message")
async def send_message(request: SendMessageRequest):
    """Отправить сообщение в чат"""
    try:
        result = await send_message_to(request.chat_id, request.message)
        return {
            "status": "success",
            "message": "Сообщение отправлено",
            "message_id": result.get("message_id"),
            "entity_info": result.get("entity_info")
        }
    except ValueError as e:
        logger.warning(f"Ошибка валидации при отправке сообщения: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке сообщения: {str(e)}")


@router.post("/send-message-form")
async def send_message_form(chat_id: str = Form(...), message: str = Form(...)):
    """Отправить сообщение через форму"""
    try:
        result = await send_message_to(chat_id, message)
        return {
            "status": "success",
            "message": "Сообщение отправлено",
            "message_id": result.get("message_id")
        }
    except ValueError as e:
        logger.warning(f"Ошибка валидации при отправке сообщения: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке сообщения: {str(e)}")


@router.post("/broadcast")
async def broadcast(request: BroadcastRequest):
    """Рассылка сообщения нескольким чатам"""
    try:
        tasks = [client.send_message(chat_id, request.message) for chat_id in request.chat_ids]
        await asyncio.gather(*tasks)
        return {
            "status": "success",
            "message": "Рассылка завершена",
            "sent_to": len(request.chat_ids)
        }
    except Exception as e:
        logger.error(f"Ошибка при рассылке: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}")
async def get_entity_info(entity_id: str):
    """Получить информацию о сущности (чат, пользователь, канал)"""
    try:
        entity = await client.get_entity(entity_id)
        entity_info = {
            'id': entity.id,
            'title': getattr(entity, 'title', None),
            'first_name': getattr(entity, 'first_name', None),
            'last_name': getattr(entity, 'last_name', None),
            'username': getattr(entity, 'username', None),
            'is_channel': isinstance(entity, type(entity)) and hasattr(entity, 'broadcast'),
            'is_group': hasattr(entity, 'megagroup'),
        }
        return {"status": "success", "data": entity_info}
    except Exception as e:
        logger.error(f"Ошибка при получении информации о сущности: {e}")
        raise HTTPException(status_code=500, detail=str(e))
