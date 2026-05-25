"""User schemas."""

from enum import StrEnum

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, TimestampSchema


PASSWORD_COMPLEXITY_MESSAGE = "Senha deve conter letra maiúscula, letra minúscula e número"
PASSWORD_MIN_LENGTH_MESSAGE = "Senha tem que ter no mínimo 6 dígitos"


def _validate_password_complexity(value: str) -> str:
    if len(value) < 6:
        raise ValueError(PASSWORD_MIN_LENGTH_MESSAGE)
    if not any(char.islower() for char in value):
        raise ValueError(PASSWORD_COMPLEXITY_MESSAGE)
    if not any(char.isupper() for char in value):
        raise ValueError(PASSWORD_COMPLEXITY_MESSAGE)
    if not any(char.isdigit() for char in value):
        raise ValueError(PASSWORD_COMPLEXITY_MESSAGE)
    return value


class UserRole(StrEnum):
    """User role enumeration for API schemas."""

    ADMIN = "admin"
    USER = "user"


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class UserCreate(BaseSchema):
    """Schema for creating a user."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    role: UserRole = UserRole.USER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_complexity(value)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    role: UserRole | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return v.lower() if v is not None else None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_password_complexity(value)


class UserRead(UserBase, TimestampSchema):
    """Schema for reading a user."""

    id: int
    role: UserRole = UserRole.USER
    avatar_url: str | None = None
    auth_provider: str | None = "email"
    email_verified: bool = False


class UserInDB(UserRead):
    """User schema with hashed password (internal use)."""

    hashed_password: str


class GoogleLoginRequest(BaseSchema):
    """Schema for Google OAuth login."""

    id_token: str | None = Field(default=None, min_length=1, description="Google ID token from OAuth credential")
    access_token: str | None = Field(default=None, min_length=1, description="Google OAuth access token")

    @model_validator(mode="after")
    def require_google_token(self) -> "GoogleLoginRequest":
        if not self.id_token and not self.access_token:
            raise ValueError("É necessário informar o token do Google")
        return self
