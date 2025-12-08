from typing import List
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    """Модель запроса на отправку сообщения"""
    chat_id: str
    message: str


class BroadcastRequest(BaseModel):
    """Модель запроса на рассылку сообщений"""
    message: str
    chat_ids: List[str]

