"""Async and sync PostgreSQL database sessions."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# === Lazy engine initialization (avoids import-time connection hang) ===

_async_engine: AsyncEngine | None = None
_sync_engine: object | None = None


def _get_config(use_sync: bool = False):
    cfg = {
        "echo": settings.DEBUG,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
    }
    # timeout is only valid for asyncpg, not psycopg2
    if not use_sync:
        cfg["connect_args"] = {"timeout": 5}
    return cfg


def _get_async_engine() -> AsyncEngine:
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(settings.DATABASE_URL, **_get_config())
    return _async_engine


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_get_config(use_sync=True))
    return _sync_engine


# Backward-compatible lazy module-level attributes via __getattr__
def __getattr__(name: str):
    if name == "engine":
        return _get_async_engine()
    if name == "sync_engine":
        return _get_sync_engine()
    if name == "async_session_maker":
        return async_sessionmaker(_get_async_engine(), class_=AsyncSession, expire_on_commit=False)
    if name == "sync_session_maker":
        return sessionmaker(bind=_get_sync_engine(), class_=Session, expire_on_commit=False)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for FastAPI dependency injection.

    Use this with FastAPI Depends().
    """
    sessionmaker = async_sessionmaker(
        _get_async_engine(), class_=AsyncSession, expire_on_commit=False
    )
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session as context manager.

    Use this with 'async with' for manual session management (e.g., WebSockets).
    """
    sessionmaker = async_sessionmaker(
        _get_async_engine(), class_=AsyncSession, expire_on_commit=False
    )
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_worker_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Get a short-lived async session for background operations.

    Creates a fresh engine with NullPool on every call so there are no
    cross-fork / cross-event-loop connection issues.  The engine is disposed
    automatically when the context manager exits.
    """
    from sqlalchemy.pool import NullPool

    worker_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(
        worker_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await worker_engine.dispose()


async def close_db() -> None:
    """Close database connections."""
    global _async_engine, _sync_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
