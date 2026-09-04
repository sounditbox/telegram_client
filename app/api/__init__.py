from fastapi import APIRouter, Depends

from app.api.dependencies import require_api_access
from app.api.routes import account, auth, dialogs, events, files, media, messages


api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_access)])
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(dialogs.router)
api_router.include_router(messages.router)
api_router.include_router(files.router)
api_router.include_router(media.router)
api_router.include_router(events.router)

__all__ = ["api_router"]
