from fastapi import APIRouter

from app.api.dependencies import ServicesDep
from app.api.schemas import CodeRequest, PasswordRequest, PhoneRequest
from app.models import ApiEnvelope, AuthAction, AuthStatus


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=ApiEnvelope[AuthStatus])
async def status(services: ServicesDep) -> ApiEnvelope[AuthStatus]:
    return ApiEnvelope(data=await services.auth.status())


@router.post("/code", response_model=ApiEnvelope[AuthAction])
async def request_code(
    payload: PhoneRequest,
    services: ServicesDep,
) -> ApiEnvelope[AuthAction]:
    return ApiEnvelope(
        data=await services.auth.request_code(payload.phone, resend=payload.resend)
    )


@router.post("/code/verify", response_model=ApiEnvelope[AuthAction])
async def verify_code(
    payload: CodeRequest,
    services: ServicesDep,
) -> ApiEnvelope[AuthAction]:
    return ApiEnvelope(data=await services.auth.verify_code(payload.code))


@router.post("/password/verify", response_model=ApiEnvelope[AuthAction])
async def verify_password(
    payload: PasswordRequest,
    services: ServicesDep,
) -> ApiEnvelope[AuthAction]:
    return ApiEnvelope(data=await services.auth.verify_password(payload.password))


@router.post("/reset", response_model=ApiEnvelope[AuthAction])
async def reset(services: ServicesDep) -> ApiEnvelope[AuthAction]:
    return ApiEnvelope(data=await services.auth.reset())


@router.post("/logout", response_model=ApiEnvelope[AuthAction])
async def logout(services: ServicesDep) -> ApiEnvelope[AuthAction]:
    return ApiEnvelope(data=await services.auth.logout())
