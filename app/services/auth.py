from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic

from telethon import errors

from app.core.config import Settings
from app.core.errors import AuthFlowError, RateLimited, TelegramUnavailable
from app.events.broker import EventBroker
from app.models import AuthAction, AuthStatus
from app.telegram.gateway import TelegramGateway
from app.telegram.manager import TelegramClientManager


class AuthPhase(StrEnum):
    IDLE = "idle"
    CODE_SENT = "code_sent"
    PASSWORD_REQUIRED = "password_required"
    AUTHORIZED = "authorized"


@dataclass(slots=True)
class AuthAttempt:
    phone: str
    phone_code_hash: str
    expires_at: float
    phase: AuthPhase = AuthPhase.CODE_SENT


class AuthService:
    def __init__(
        self,
        settings: Settings,
        manager: TelegramClientManager,
        gateway: TelegramGateway,
        broker: EventBroker,
    ) -> None:
        self._settings = settings
        self._manager = manager
        self._gateway = gateway
        self._broker = broker
        self._attempt: AuthAttempt | None = None
        self._lock = asyncio.Lock()

    async def status(self) -> AuthStatus:
        try:
            authenticated = await self._manager.is_authorized()
        except TelegramUnavailable:
            return AuthStatus(
                connected=False,
                authenticated=False,
                phase=self._current_phase(),
            )

        if authenticated:
            return AuthStatus(
                connected=True,
                authenticated=True,
                phase=AuthPhase.AUTHORIZED,
                user=await self._gateway.get_me(),
            )
        return AuthStatus(
            connected=self._manager.connected,
            authenticated=False,
            phase=self._current_phase(),
        )

    async def request_code(self, phone: str, *, resend: bool = False) -> AuthAction:
        async with self._lock:
            client = await self._manager.ensure_connected()
            if await client.is_user_authorized():
                return AuthAction(phase=AuthPhase.AUTHORIZED, message="Вы уже авторизованы")
            try:
                sent_code = await client.send_code_request(phone)
            except errors.PhoneNumberInvalidError as exc:
                raise AuthFlowError("Некорректный номер телефона", "invalid_phone") from exc
            except errors.FloodWaitError as exc:
                raise RateLimited(exc.seconds) from exc
            except errors.RPCError as exc:
                raise AuthFlowError("Telegram не смог отправить код", "code_send_failed") from exc

            self._attempt = AuthAttempt(
                phone=phone,
                phone_code_hash=sent_code.phone_code_hash,
                expires_at=monotonic() + self._settings.auth_attempt_ttl_seconds,
            )
            return AuthAction(
                phase=AuthPhase.CODE_SENT,
                message="Новый код отправлен" if resend else "Код отправлен",
            )

    async def verify_code(self, code: str) -> AuthAction:
        async with self._lock:
            attempt = self._require_attempt(AuthPhase.CODE_SENT)
            client = await self._manager.ensure_connected()
            try:
                await client.sign_in(
                    phone=attempt.phone,
                    code=code,
                    phone_code_hash=attempt.phone_code_hash,
                )
            except errors.SessionPasswordNeededError:
                attempt.phase = AuthPhase.PASSWORD_REQUIRED
                return AuthAction(
                    phase=AuthPhase.PASSWORD_REQUIRED,
                    message="Введите пароль двухфакторной аутентификации",
                )
            except errors.PhoneCodeInvalidError as exc:
                raise AuthFlowError("Неверный код подтверждения", "invalid_code") from exc
            except errors.PhoneCodeExpiredError as exc:
                self._attempt = None
                raise AuthFlowError("Код истёк. Запросите новый", "expired_code") from exc
            except errors.FloodWaitError as exc:
                raise RateLimited(exc.seconds) from exc
            except errors.RPCError as exc:
                raise AuthFlowError("Не удалось подтвердить код", "code_verification_failed") from exc

            self._attempt = None
            return AuthAction(phase=AuthPhase.AUTHORIZED, message="Авторизация завершена")

    async def verify_password(self, password: str) -> AuthAction:
        async with self._lock:
            self._require_attempt(AuthPhase.PASSWORD_REQUIRED)
            client = await self._manager.ensure_connected()
            try:
                await client.sign_in(password=password)
            except errors.PasswordHashInvalidError as exc:
                raise AuthFlowError("Неверный пароль", "invalid_password") from exc
            except errors.FloodWaitError as exc:
                raise RateLimited(exc.seconds) from exc
            except errors.RPCError as exc:
                raise AuthFlowError("Не удалось подтвердить пароль", "password_verification_failed") from exc

            self._attempt = None
            return AuthAction(phase=AuthPhase.AUTHORIZED, message="Авторизация завершена")

    async def reset(self) -> AuthAction:
        async with self._lock:
            self._attempt = None
        return AuthAction(phase=AuthPhase.IDLE, message="Вход начат заново")

    async def logout(self) -> AuthAction:
        async with self._lock:
            self._attempt = None
            await self._manager.log_out_and_restart()
            await self._broker.clear()
        return AuthAction(phase=AuthPhase.IDLE, message="Сессия Telegram удалена")

    def _current_phase(self) -> AuthPhase:
        if self._attempt is None:
            return AuthPhase.IDLE
        if self._attempt.expires_at <= monotonic():
            self._attempt = None
            return AuthPhase.IDLE
        return self._attempt.phase

    def _require_attempt(self, phase: AuthPhase) -> AuthAttempt:
        current_phase = self._current_phase()
        if self._attempt is None:
            raise AuthFlowError("Сначала запросите код подтверждения", "auth_attempt_missing")
        if current_phase != phase:
            raise AuthFlowError("Неверный шаг авторизации", "invalid_auth_phase")
        return self._attempt
