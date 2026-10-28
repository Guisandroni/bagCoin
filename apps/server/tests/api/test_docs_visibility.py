"""FastAPI docs visibility by environment and feature flag."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_docs_hidden_in_production_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_API_DOCS", False)
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/api/v1/openapi.json")).status_code == 404


@pytest.mark.anyio
async def test_docs_can_be_enabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_API_DOCS", True)
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/docs")).status_code == 200
        assert (await client.get("/api/v1/openapi.json")).status_code == 200
