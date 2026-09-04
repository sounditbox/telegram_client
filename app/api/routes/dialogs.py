from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import ServicesDep
from app.models import ApiEnvelope, CursorPage, DialogInfo, MessageInfo, UserInfo


router = APIRouter(prefix="/dialogs", tags=["dialogs"])


@router.get("", response_model=ApiEnvelope[CursorPage[DialogInfo]])
async def list_dialogs(
    services: ServicesDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
    cursor: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    refresh: bool = False,
) -> ApiEnvelope[CursorPage[DialogInfo]]:
    return ApiEnvelope(
        data=await services.dialogs.list(
            limit,
            cursor=cursor,
            query=query,
            refresh=refresh,
        )
    )


@router.get("/{chat_id}/messages", response_model=ApiEnvelope[CursorPage[MessageInfo]])
async def list_messages(
    chat_id: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
    cursor: Annotated[int | None, Query(gt=0)] = None,
    refresh: bool = False,
) -> ApiEnvelope[CursorPage[MessageInfo]]:
    return ApiEnvelope(
        data=await services.dialogs.messages(
            chat_id,
            limit,
            before_id=cursor,
            refresh=refresh,
        )
    )


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
