from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.api.dependencies import ServicesDep
from app.models import ApiEnvelope, FileResult


router = APIRouter(tags=["files"])


@router.post("/files", response_model=ApiEnvelope[FileResult])
async def send_file(
    services: ServicesDep,
    chat_id: Annotated[str, Form(min_length=1, max_length=128)],
    file: Annotated[UploadFile, File()],
    caption: Annotated[str, Form(max_length=1024)] = "",
) -> ApiEnvelope[FileResult]:
    return ApiEnvelope(
        data=await services.files.send(chat_id, file, caption=caption)
    )
