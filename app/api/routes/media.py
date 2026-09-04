from typing import Annotated

from fastapi import APIRouter, Path
from fastapi.responses import FileResponse, Response

from app.api.dependencies import ServicesDep


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/avatars/{entity_id}", response_class=Response)
async def avatar(
    entity_id: Annotated[str, Path(min_length=1, max_length=128)],
    services: ServicesDep,
) -> Response:
    result = await services.media.avatar(entity_id)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Cache-Control": "private, max-age=900"},
    )


@router.get("/dialogs/{chat_id}/messages/{message_id}", response_class=FileResponse)
async def message_media(
    chat_id: Annotated[str, Path(min_length=1, max_length=128)],
    message_id: Annotated[int, Path(gt=0)],
    services: ServicesDep,
) -> FileResponse:
    result = await services.media.message_media(chat_id, message_id)
    return FileResponse(
        result.path,
        media_type=result.media_type,
        filename=result.filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=86400"},
    )
