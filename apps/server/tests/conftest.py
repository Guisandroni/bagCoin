"""Test configuration — ensures CSRF middleware is disabled during tests.

Sets DEBUG=true before FastAPI app is loaded so CSRFMiddleware skips validation.
"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure(config):
    """Set DEBUG=true before any test imports to disable CSRF middleware."""
    os.environ["DEBUG"] = "true"


@pytest.fixture
def api_key_headers():
    from app.core.config import settings

    return {settings.API_KEY_HEADER: settings.API_KEY}


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=None)
    redis.exists = AsyncMock(return_value=False)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def mock_db_session():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.scalar = AsyncMock(return_value=0)
    db.add = MagicMock()
    return db


@pytest.fixture
async def client(mock_redis, mock_db_session):
    from app.main import app
    from app.api.deps import get_db_session, get_redis

    previous_db = app.dependency_overrides.get(get_db_session)
    previous_redis = app.dependency_overrides.get(get_redis)
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    if previous_db is None:
        app.dependency_overrides.pop(get_db_session, None)
    else:
        app.dependency_overrides[get_db_session] = previous_db
    if previous_redis is None:
        app.dependency_overrides.pop(get_redis, None)
    else:
        app.dependency_overrides[get_redis] = previous_redis


@pytest.fixture(autouse=True)
def _isolate_legacy_agent_route_tests(monkeypatch, request):
    """Keep legacy agent route contract tests away from real DB/LLM services."""
    if request.node.fspath.basename != "test_agents.py":
        return

    from app.api.routes.v1 import categories as category_routes
    from app.api.routes.v1 import webhook

    monkeypatch.setattr(webhook, "get_or_create_user_sync", lambda phone_number: object())
    monkeypatch.setattr(webhook, "is_duplicate_message", lambda message_id: False)
    monkeypatch.setattr(
        webhook.orchestrator,
        "invoke",
        lambda state: {"response": "ok", **state},
    )
    monkeypatch.setattr(category_routes, "list_categories", lambda phone_number: [])
