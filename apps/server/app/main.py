"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypedDict

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.clients.redis import RedisClient
from app.core.config import settings
from app.core.logfire_setup import instrument_app, setup_logfire
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware


class LifespanState(TypedDict, total=False):
    """Lifespan state - resources available via request.state."""

    redis: RedisClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
    # === Startup ===
    state: LifespanState = {}
    setup_logfire()
    from app.core.logfire_setup import instrument_asyncpg

    instrument_asyncpg()
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client

    # Bug 8.1 — multimodal readiness check
    try:
        from app.agents.multimodal import _configured_api_key

        groq_ok = _configured_api_key(settings.GROQ_API_KEY) is not None
        gemini_ok = _configured_api_key(settings.GEMINI_API_KEY) is not None
        if not groq_ok:
            msg = "GROQ_API_KEY not configured — audio (Whisper) and image (Llama-4-Scout) will be disabled"
            if settings.ENVIRONMENT == "production":
                logger.warning(msg)
            else:
                logger.info(msg)
        if not groq_ok and not gemini_ok:
            logger.warning(
                "Neither GROQ_API_KEY nor GEMINI_API_KEY configured — all image analysis disabled"
            )
    except Exception as exc:
        logger.warning(f"Could not verify multimodal API keys: {exc}")

    # Tables are managed by Alembic migrations (run via entrypoint.sh).
    # create_all is kept as fallback for environments without Alembic.
    try:
        from sqlalchemy import inspect

        import app.db.models  # noqa: F401 - register all models
        from app.db.base import Base
        from app.db.session import sync_engine

        if sync_engine is not None:
            inspector = inspect(sync_engine)
            existing = inspector.get_table_names()
            if not existing:
                Base.metadata.create_all(bind=sync_engine)
                logger.info("BagCoin tables created (fallback)")
            else:
                logger.info("BagCoin tables already exist, skipping create_all")
    except Exception as e:
        logger.warning(f"Could not verify/create BagCoin tables: {e}")

    yield state

    # === Shutdown ===
    if "redis" in state:
        await state["redis"].close()
    from app.db.session import close_db

    await close_db()


# Environments where API docs should be visible
SHOW_DOCS_ENVIRONMENTS = ("local", "staging", "development")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Only show docs in allowed environments (hide in production)
    show_docs = settings.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS or settings.ENABLE_API_DOCS
    openapi_url = f"{settings.API_V1_STR}/openapi.json" if show_docs else None
    docs_url = "/docs" if show_docs else None
    redoc_url = "/redoc" if show_docs else None

    # OpenAPI tags for better documentation organization
    openapi_tags = [
        {
            "name": "health",
            "description": "Health check endpoints for monitoring and Kubernetes probes",
        },
        {
            "name": "auth",
            "description": "Authentication endpoints - login, register, token refresh",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
        {
            "name": "conversations",
            "description": "AI conversation persistence - manage chat history",
        },
        {
            "name": "agent",
            "description": "AI agent WebSocket endpoint for real-time chat",
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time communication",
        },
    ]

    # PII redaction in logs (GDPR/compliance)
    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        summary="FastAPI application with Logfire observability",
        description="""
A FastAPI project

## Features
- **Authentication**: JWT-based authentication with refresh tokens
- **API Key**: Header-based API key authentication
- **Database**: Async database operations
- **Redis**: Caching and session storage
- **Observability**: Logfire integration for tracing and monitoring

## Documentation

- [Swagger UI](/docs) - Interactive API documentation
- [ReDoc](/redoc) - Alternative documentation view
        """.strip(),
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_tags=openapi_tags,
        contact={
            "name": "Your Name",
            "email": "your@email.com",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        lifespan=lifespan,
    )
    # Logfire instrumentation
    instrument_app(app)

    # Request ID middleware (for request correlation/debugging)
    app.add_middleware(RequestIDMiddleware)

    # Security hardening: protect against XSS, clickjacking, MIME sniffing
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRF protection disabled — JWT in Authorization header provides equivalent
    # protection for cross-domain architecture (Vercel frontend + VPS backend).
    # app.add_middleware(CSRFMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # CORS middleware
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # API Version Deprecation (uncomment when deprecating old versions)
    # Example: Mark v1 as deprecated when v2 is ready
    # from app.api.versioning import VersionDeprecationMiddleware
    # app.add_middleware(
    #     VersionDeprecationMiddleware,
    #     deprecated_versions={
    #         "v1": {
    #             "sunset": "2025-12-31",
    #             "link": "/docs/migration/v2",
    #             "message": "Please migrate to API v2",
    #         }
    #     },
    # )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Pagination
    add_pagination(app)

    from app.admin import setup_admin

    setup_admin(app)

    return app


app = create_app()
