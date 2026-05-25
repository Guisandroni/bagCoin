"""Application configuration using Pydantic BaseSettings."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for path in [current, current.parent]:
        env_file = path / ".env"
        if env_file.exists():
            return env_file
    return None


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    # === Project ===
    PROJECT_NAME: str = "bagcoin_api"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"
    ENABLE_API_DOCS: bool = False
    TIMEZONE: str = "UTC"  # IANA timezone (e.g. "UTC", "Europe/Warsaw", "America/New_York")
    MODELS_CACHE_DIR: Path = Path("./models_cache")
    MEDIA_DIR: Path = Path("./media")
    MAX_UPLOAD_SIZE_MB: int = 50  # Max file upload size in MB

    # === Logfire ===
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "bagcoin_api"
    LOGFIRE_ENVIRONMENT: str = "development"

    # === Database (PostgreSQL async) ===
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "bagcoin_api"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync PostgreSQL connection URL (for Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Pool configuration
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # === Auth (SECRET_KEY for JWT/Session/Admin) ===
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        # Get environment from values if available
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    # === JWT Settings ===
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # === Auth (API Key) ===
    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate API_KEY is set in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production" and env == "production":
            raise ValueError(
                "API_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Build Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # === Celery ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # === AI Agent (langgraph, openai) ===
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-5-mini"
    AI_TEMPERATURE: float = 0.7
    AI_AVAILABLE_MODELS: list[str] = [
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5",
        "gpt-5.1",
        "gpt-5.2",
        "o4-mini",
        "o3",
        "o3-mini",
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4.1-nano",
        "gpt-4o",
        "gpt-4o-mini",
    ]
    AI_FRAMEWORK: str = "langgraph"
    LLM_PROVIDER: str = "openai"
    HUMANIZE_RESPONSES: bool = False
    HUMANIZE_MAX_CHARS: int = 500
    HUMANIZE_ALLOWED_INTENTS_EXTRA: list[str] = []
    USE_TOOL_AGENTS: bool = True
    LLM_EXTRACT_TIMEOUT: float = 4.0
    IMAGE_STRUCTURED_EXTRACT: bool = True
    ECHO_AUDIO_TRANSCRIPTION: bool = False
    EXTRA_WHISPER_HALLUCINATIONS: list[str] = []

    # === BagCoin / LLM APIs ===
    GROQ_API_KEY: str = ""
    OPENCODE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    GEMINI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "deepseek-chat"  # v4-flash

    # === Google OAuth ===
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # === SMTP / Email Verification ===
    EMAIL_PROVIDER: str = "smtp"  # smtp | resend_api
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    RESEND_API_BASE_URL: str = "https://api.resend.com"
    EMAIL_VERIFICATION_TTL_SECONDS: int = 600
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = 5
    EMAIL_VERIFICATION_SEND_LIMIT_PER_HOUR: int = 5
    EMAIL_VERIFICATION_SEND_LIMIT_PER_IP_PER_HOUR: int = 20
    EMAIL_VERIFICATION_VERIFY_LIMIT_PER_10_MIN: int = 10
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TTL_SECONDS: int = 300
    PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS: int = 180
    PASSWORD_RESET_SEND_LIMIT_PER_HOUR: int = 5
    SUPPORT_EMAIL: str = ""

    # === WhatsApp Bridge ===
    WHATSAPP_BRIDGE_URL: str = "http://whatsapp-bridge:3001"
    WHATSAPP_API_KEY: str = "bagcoin_webhook_secret_123"

    # === Internal base URL used by bridges to fetch reports ===
    # Points to the backend service as seen from the bridges' network.
    # In Docker Compose this is typically http://app:8000.
    INTERNAL_API_BASE_URL: str = "http://app:8000"

    # === Bot deep links (web ↔ WhatsApp/Telegram pairing) ===
    BOT_WHATSAPP_NUMBER: str = ""  # E.164 digits only, e.g. 5511999999999
    BOT_TELEGRAM_USERNAME: str = ""  # without @
    INTEGRATION_LINK_TOKEN_TTL_SECONDS: int = 600

    # === LangSmith Observability ===
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "bagcoin_api"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Warn if CORS_ORIGINS is too permissive in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if "*" in v and env == "production":
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' in production! Specify explicit allowed origins."
            )
        return v


settings = Settings()
