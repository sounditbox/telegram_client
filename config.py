from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_ID: int = Field(
        ...,
        description="API ID приложения Telegram. Получите на https://my.telegram.org"
    )
    API_HASH: str = Field(
        ...,
        description="API Hash приложения Telegram. Получите на https://my.telegram.org"
    )

    SESSION_NAME: str = Field(
        default="telegram_client",
        description="Имя файла сессии Telethon (без расширения .session)"
    )

    BOT_TOKEN: Optional[str] = Field(
        default=None,
        description="Токен бота от @BotFather (опционально)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
    )


try:
    settings = Settings() # noqa
except Exception as e:
    raise ValueError(
        f"Ошибка загрузки конфигурации: {e}\n"
        "Убедитесь, что файл .env существует и содержит API_ID и API_HASH"
    ) from e

API_ID = settings.API_ID
API_HASH = settings.API_HASH
SESSION_NAME = settings.SESSION_NAME
