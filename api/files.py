import logging
import os

from fastapi import APIRouter, HTTPException, Form, File, UploadFile

from telegram import validate_entity, client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["files"])


@router.post("/send-file")
async def send_file(
        chat_id: str = Form(...),
        caption: str = Form(""),
        file: UploadFile = File(...)
):
    """Отправить файл в чат"""
    try:
        # Проверяем существование entity перед отправкой
        await validate_entity(chat_id)

        # Сохраняем файл временно
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Отправляем файл
        await client.send_file(chat_id, file_path, caption=caption)

        # Удаляем временный файл
        os.remove(file_path)

        return {"status": "success", "message": "Файл отправлен"}
    except ValueError as e:
        logger.warning(f"Ошибка валидации при отправке файла: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        error_msg = str(e)
        if "Cannot find any entity" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось найти чат/пользователя '{chat_id}'. Проверьте правильность ID или username."
            )
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке файла: {error_msg}")
