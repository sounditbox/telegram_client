from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencies import ServicesDep
from app.api.schemas import BroadcastRequest, SendMessageRequest
from app.models import ApiEnvelope, BroadcastResult, EntityInfo, SentMessage


router = APIRouter(tags=["messages"])


@router.post("/messages", response_model=ApiEnvelope[SentMessage])
async def send_message(
    payload: SendMessageRequest,
    services: ServicesDep,
) -> ApiEnvelope[SentMessage]:
    return ApiEnvelope(
        data=await services.messaging.send(payload.chat_id, payload.text)
    )


@router.post("/messages/broadcast", response_model=ApiEnvelope[BroadcastResult])
async def broadcast(
    payload: BroadcastRequest,
    services: ServicesDep,
) -> ApiEnvelope[BroadcastResult]:
    return ApiEnvelope(
        data=await services.messaging.broadcast(payload.chat_ids, payload.text)
    )


@router.get("/entities/{reference}", response_model=ApiEnvelope[EntityInfo])
async def entity_info(
    reference: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
) -> ApiEnvelope[EntityInfo]:
    return ApiEnvelope(data=await services.messaging.entity(reference))
