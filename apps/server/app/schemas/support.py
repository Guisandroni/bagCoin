"""Support contact schemas."""

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema


class SupportContactRequest(BaseSchema):
    subject: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=4000)

    @field_validator("subject", "message", mode="before")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class SupportContactResponse(BaseSchema):
    sent: bool = True
    message: str = "Mensagem enviada ao suporte."
