from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "application_error",
        status_code: int = 400,
        headers: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.headers = headers
        self.details = details


class AccessDenied(ApplicationError):
    def __init__(self, message: str = "Доступ запрещён") -> None:
        super().__init__(message, code="access_denied", status_code=401)


class NotAuthorized(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "Сначала авторизуйтесь в Telegram",
            code="telegram_not_authorized",
            status_code=401,
        )


class AuthFlowError(ApplicationError):
    def __init__(self, message: str, code: str = "auth_flow_error") -> None:
        super().__init__(message, code=code, status_code=400)


class EntityNotFound(ApplicationError):
    def __init__(self, reference: str) -> None:
        super().__init__(
            f"Чат или пользователь «{reference}» не найден",
            code="entity_not_found",
            status_code=404,
        )


class TelegramUnavailable(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "Telegram сейчас недоступен. Попробуйте ещё раз позже",
            code="telegram_unavailable",
            status_code=503,
        )


class RateLimited(ApplicationError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            f"Telegram ограничил частоту запросов. Повторите через {retry_after} сек.",
            code="rate_limited",
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            details={"retry_after": retry_after},
        )


class InvalidUpload(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_upload", status_code=413)


class MediaNotFound(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "Медиафайл не найден",
            code="media_not_found",
            status_code=404,
        )


class MediaTooLarge(ApplicationError):
    def __init__(self, limit_bytes: int) -> None:
        super().__init__(
            f"Медиафайл превышает лимит {limit_bytes // (1024 * 1024)} МБ",
            code="media_too_large",
            status_code=413,
        )
