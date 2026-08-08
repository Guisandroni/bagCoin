"""Shared fixtures for agent unit tests.

All tests here run without real DB or LLM — everything is mocked.
"""
import uuid
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_no_llm(monkeypatch):
    """Force deterministic path — patch get_llm to return None in all agent modules."""
    monkeypatch.setattr("app.agents.normalization.get_llm", lambda **kw: None)
    monkeypatch.setattr("app.agents.ingestion.get_llm", lambda **kw: None)


@pytest.fixture
def mock_llm_response(monkeypatch):
    """Factory: inject a fake JSON LLM response into timed_invoke."""

    def _factory(content_json: str):
        response = MagicMock()
        response.content = content_json
        monkeypatch.setattr(
            "app.agents.normalization.timed_invoke",
            lambda llm, msgs, operation="": (response, 200.0),
        )
        monkeypatch.setattr(
            "app.agents.ingestion.timed_invoke",
            lambda llm, msgs, operation="": (response, 200.0),
        )

    return _factory


@pytest.fixture
def mock_list_categories(monkeypatch):
    """Patch list_categories to return a controlled set (default + custom).

    Patches app.agents.persistence.list_categories because extract_transaction
    does a lazy import from that module.
    """

    def _factory(extra: list[str] | None = None):
        cats = [
            {"name": "Alimentação", "is_default": True},
            {"name": "Transporte", "is_default": True},
            {"name": "Saúde", "is_default": True},
            {"name": "Lazer", "is_default": True},
        ]
        for name in (extra or []):
            cats.append({"name": name, "is_default": False})

        import app.agents.persistence as persistence_module

        monkeypatch.setattr(persistence_module, "list_categories", lambda phone_number: cats)
        # Also patch get_conversation_history to avoid DB hits
        monkeypatch.setattr(
            persistence_module, "get_conversation_history", lambda phone_number, limit=6: ""
        )

    return _factory


@pytest.fixture
def base_state():
    """Minimal AgentState for normalization tests."""
    return {
        "phone_number": f"551199{uuid.uuid4().hex[:7]}",
        "message": "",
        "intent": None,
        "extracted_data": None,
        "context": {},
        "source_format": "text",
    }
