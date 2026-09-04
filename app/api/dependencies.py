from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, Request, Response

from app.core.config import Settings
from app.core.errors import AccessDenied
from app.services.container import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


async def require_api_access(
    request: Request,
    response: Response,
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    settings = get_runtime_settings(request)
    expected = settings.access_token
    cookie_key = request.cookies.get("telegram_desk_access")
    supplied_key = x_api_key or cookie_key or ""
    if expected is not None and not secrets.compare_digest(
        supplied_key,
        expected.get_secret_value(),
    ):
        raise AccessDenied("Укажите корректный ключ доступа")
    if expected is not None and x_api_key:
        response.set_cookie(
            "telegram_desk_access",
            expected.get_secret_value(),
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=8 * 60 * 60,
        )

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
            raise AccessDenied("Межсайтовый запрос отклонён")


ServicesDep = Annotated[Services, Depends(get_services)]
