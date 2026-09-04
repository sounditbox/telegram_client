from typing import Annotated

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import ServicesDep


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream", response_class=StreamingResponse)
async def stream_events(
    services: ServicesDep,
    after: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[int | None, Header(alias="Last-Event-ID", ge=0)] = None,
) -> StreamingResponse:
    resume_after = max(after, last_event_id or 0)
    return StreamingResponse(
        services.events.stream(resume_after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
