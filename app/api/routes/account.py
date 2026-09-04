from fastapi import APIRouter

from app.api.dependencies import ServicesDep
from app.models import ApiEnvelope, UserInfo


router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=ApiEnvelope[UserInfo])
async def current_user(services: ServicesDep) -> ApiEnvelope[UserInfo]:
    return ApiEnvelope(data=await services.account.current_user())
