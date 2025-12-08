import logging

from fastapi import APIRouter, HTTPException, Form

from telegram import client, setup_event_handlers, get_client_info, auth_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def get_auth_status():
    """Проверить статус авторизации"""
    try:
        if client.is_connected():
            me = await get_client_info()
            return {
                "status": "success",
                "authenticated": True,
                "user": me
            }
        else:
            return {
                "status": "success",
                "authenticated": False,
                "user": None
            }
    except Exception as e:
        return {
            "status": "success",
            "authenticated": False,
            "user": None,
            "error": str(e)
        }


@router.post("/send-code")
async def send_code(phone: str = Form(...), resend: bool = Form(False)):
    """Отправить код подтверждения на номер телефона"""
    try:
        if not client.is_connected():
            await client.connect()

        auth_state['phone'] = phone

        if resend and auth_state.get('phone_code_hash'):
            try:
                result = await client.resend_code_request(phone, auth_state['phone_code_hash'])
                auth_state['phone_code_hash'] = result.phone_code_hash
                return {
                    "status": "success",
                    "message": "Код отправлен повторно",
                    "phone_code_hash": result.phone_code_hash
                }
            except Exception as resend_error:
                logger.warning(f"Не удалось отправить код повторно: {resend_error}")

        # Отправляем код (обычная отправка или если повторная не удалась)
        result = await client.send_code_request(phone)
        auth_state['phone_code_hash'] = result.phone_code_hash

        return {
            "status": "success",
            "message": "Код отправлен",
            "phone_code_hash": result.phone_code_hash
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при отправке кода: {e}")

        if "all available options" in error_msg.lower() or "resend" in error_msg.lower():
            if auth_state.get('phone_code_hash'):
                return {
                    "status": "error",
                    "message": "Все варианты отправки кода использованы. Используйте повторную отправку.",
                    "can_resend": True,
                    "detail": error_msg
                }

        raise HTTPException(status_code=400, detail=f"Ошибка при отправке кода: {error_msg}")


@router.post("/sign-in")
async def sign_in(code: str = Form(...), password: str = Form(None)):
    """Войти с кодом подтверждения и паролем (если требуется)"""
    try:
        if not auth_state.get('phone') or not auth_state.get('phone_code_hash'):
            raise HTTPException(status_code=400, detail="Сначала отправьте код подтверждения")

        phone = auth_state['phone']
        phone_code_hash = auth_state['phone_code_hash']

        try:
            me = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

            auth_state['phone'] = None
            auth_state['phone_code_hash'] = None
            auth_state['needs_password'] = False

            setup_event_handlers()

            user_info = await get_client_info()

            return {
                "status": "success",
                "message": "Успешная авторизация",
                "user": user_info
            }

        except Exception as sign_in_error:
            error_msg = str(sign_in_error)

            if "PASSWORD_HASH_INVALID" in error_msg or "password" in error_msg.lower():
                auth_state['needs_password'] = True
                if password:
                    try:
                        if not client.is_connected():
                            await client.connect()

                        me = await client.sign_in(password=password)

                        auth_state['phone'] = None
                        auth_state['phone_code_hash'] = None
                        auth_state['needs_password'] = False

                        setup_event_handlers()

                        user_info = await get_client_info()

                        return {
                            "status": "success",
                            "message": "Успешная авторизация",
                            "user": user_info
                        }
                    except Exception as password_error:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Неверный пароль: {str(password_error)}"
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Требуется пароль двухфакторной аутентификации"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка авторизации: {error_msg}"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при авторизации: {str(e)}")


@router.get("/needs-password")
async def check_password_required():
    """Проверить, требуется ли пароль"""
    return {
        "status": "success",
        "needs_password": auth_state.get('needs_password', False)
    }
