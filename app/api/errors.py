from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from telethon import errors

from app.core.errors import ApplicationError


logger = logging.getLogger(__name__)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        _request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": {
                    "code": "validation_error",
                    "message": "Проверьте введённые данные",
                    "details": {"issues": jsonable_encoder(exc.errors())},
                },
            },
        )

    @app.exception_handler(errors.FloodWaitError)
    async def flood_wait_handler(
        _request: Request,
        exc: errors.FloodWaitError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(exc.seconds)},
            content={
                "ok": False,
                "error": {
                    "code": "rate_limited",
                    "message": f"Повторите через {exc.seconds} сек.",
                    "details": {"retry_after": exc.seconds},
                },
            },
        )

    @app.exception_handler(errors.UnauthorizedError)
    async def telegram_unauthorized_handler(
        _request: Request,
        _exc: errors.UnauthorizedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": {
                    "code": "telegram_not_authorized",
                    "message": "Сессия Telegram больше не авторизована",
                },
            },
        )

    @app.exception_handler(errors.RPCError)
    async def telegram_rpc_error_handler(
        request: Request,
        exc: errors.RPCError,
    ) -> JSONResponse:
        logger.warning(
            "Telegram rejected %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "error": {
                    "code": "telegram_error",
                    "message": "Telegram отклонил операцию",
                },
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error during %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": "Внутренняя ошибка приложения",
                },
            },
        )
