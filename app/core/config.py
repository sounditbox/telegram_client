from __future__ import annotations

from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    api_id: int = Field(validation_alias="API_ID")
    api_hash: SecretStr = Field(validation_alias="API_HASH")
    session_name: str = Field(default="telegram_client", validation_alias="SESSION_NAME")
    session_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "sessions",
        validation_alias="SESSION_DIR",
    )
    upload_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "uploads",
        validation_alias="UPLOAD_DIR",
    )
    media_cache_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "media-cache",
        validation_alias="MEDIA_CACHE_DIR",
    )
    database_path: Path = Field(
        default=PROJECT_ROOT / "data" / "telegram-cache.sqlite3",
        validation_alias="DATABASE_PATH",
    )
    access_token: SecretStr | None = Field(default=None, validation_alias="ACCESS_TOKEN")
    host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    port: int = Field(default=8000, ge=1, le=65535, validation_alias="APP_PORT")
    reload: bool = Field(default=False, validation_alias="APP_RELOAD")
    auth_attempt_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        validation_alias="AUTH_ATTEMPT_TTL_SECONDS",
    )
    max_upload_bytes: int = Field(
        default=32 * 1024 * 1024,
        ge=1024,
        le=2 * 1024 * 1024 * 1024,
        validation_alias="MAX_UPLOAD_BYTES",
    )
    max_media_bytes: int = Field(
        default=64 * 1024 * 1024,
        ge=1024,
        le=2 * 1024 * 1024 * 1024,
        validation_alias="MAX_MEDIA_BYTES",
    )
    sync_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        validation_alias="SYNC_INTERVAL_SECONDS",
    )
    sync_dialog_limit: int = Field(
        default=100,
        ge=1,
        le=500,
        validation_alias="SYNC_DIALOG_LIMIT",
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, value: str) -> str:
        value = value.removesuffix(".session").strip()
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value):
            raise ValueError("SESSION_NAME may contain only letters, digits, '_' and '-'")
        return value

    @model_validator(mode="after")
    def require_token_for_public_bind(self) -> "Settings":
        try:
            is_loopback = ip_address(self.host).is_loopback
        except ValueError:
            is_loopback = self.host.lower() == "localhost"
        if not is_loopback and self.access_token is None:
            raise ValueError("ACCESS_TOKEN is required when APP_HOST is not loopback")
        return self

    @property
    def session_path(self) -> Path:
        return self.session_dir.resolve() / self.session_name

    @property
    def frontend_dist(self) -> Path:
        return PROJECT_ROOT / "frontend" / "dist"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
