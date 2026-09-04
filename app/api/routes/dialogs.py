from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import ServicesDep
from app.models import ApiEnvelope, DialogInfo, MessageInfo, UserInfo


router = APIRouter(prefix="/dialogs", tags=["dialogs"])


@router.get("", response_model=ApiEnvelope[list[DialogInfo]])
async def list_dialogs(
    services: ServicesDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApiEnvelope[list[DialogInfo]]:
    return ApiEnvelope(data=await services.dialogs.list(limit))


@router.get("/{chat_id}/messages", response_model=ApiEnvelope[list[MessageInfo]])
async def list_messages(
    chat_id: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApiEnvelope[list[MessageInfo]]:
    return ApiEnvelope(data=await services.dialogs.messages(chat_id, limit))


@router.get("/{chat_id}/participants", response_model=ApiEnvelope[list[UserInfo]])
async def list_participants(
    chat_id: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> ApiEnvelope[list[UserInfo]]:
    return ApiEnvelope(data=await services.dialogs.participants(chat_id, limit))


@router.post("/{chat_id}/read", response_model=ApiEnvelope[dict[str, bool]])
async def mark_read(
    chat_id: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
) -> ApiEnvelope[dict[str, bool]]:
    await services.dialogs.mark_read(chat_id)
    return ApiEnvelope(data={"read": True})
