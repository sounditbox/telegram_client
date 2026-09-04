from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


ChatReference = Annotated[str, Field(min_length=1, max_length=128)]


class PhoneRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    resend: bool = False


class CodeRequest(BaseModel):
    code: str = Field(min_length=3, max_length=10)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.replace(" ", "").replace("-", "")
        if not normalized.isdigit():
            raise ValueError("code must contain only digits")
        return normalized


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class SendMessageRequest(BaseModel):
    chat_id: ChatReference
    text: str = Field(min_length=1, max_length=4096)


class BroadcastRequest(BaseModel):
    chat_ids: list[ChatReference] = Field(min_length=1, max_length=25)
    text: str = Field(min_length=1, max_length=4096)

    @field_validator("chat_ids")
    @classmethod
    def unique_chat_ids(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values))
