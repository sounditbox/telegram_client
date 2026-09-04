from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import ServicesDep


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream", response_class=StreamingResponse)
async def stream_events(
    services: ServicesDep,
    after: Annotated[int, Query(ge=0)] = 0,
) -> StreamingResponse:
    return StreamingResponse(
        services.events.stream(after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
