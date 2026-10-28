"""Unit tests for orchestrator final response persistence."""

from app.agents.nodes.chat import build_response_node, finalize_response_node
from app.schemas.enums import IntentType


def _state(response: str = "Resposta crua"):
    return {
        "phone_number": "5511999999999",
        "user_id": None,
        "message": "gastei 50 no mercado",
        "intent": IntentType.REGISTER_EXPENSE.value,
        "extracted_data": None,
        "query_result": None,
        "report_path": None,
        "report_summary": None,
        "import_summary": None,
        "imported_count": None,
        "skipped_count": None,
        "import_errors": None,
        "budget_data": None,
        "goal_data": None,
        "alerts": None,
        "wizard": None,
        "response": response,
        "context": {},
        "error": None,
        "source_format": "text",
    }


def test_finalize_response_saves_history_once(monkeypatch):
    calls = []
    monkeypatch.setattr("app.agents.nodes.chat.should_humanize", lambda state: False)
    monkeypatch.setattr(
        "app.agents.nodes.chat.save_message_to_history",
        lambda phone, role, content: calls.append((role, content)),
    )

    state = build_response_node(_state("Resposta final"))
    result = finalize_response_node(state)

    assert result["response"] == "Resposta final"
    assert calls == [
        ("user", "gastei 50 no mercado"),
        ("bot", "Resposta final"),
    ]


def test_finalize_response_saves_humanized_text(monkeypatch):
    calls = []
    monkeypatch.setattr("app.agents.nodes.chat.should_humanize", lambda state: True)
    monkeypatch.setattr(
        "app.agents.nodes.chat.humanize_safely",
        lambda raw, state: "Resposta humanizada",
    )
    monkeypatch.setattr(
        "app.agents.nodes.chat.save_message_to_history",
        lambda phone, role, content: calls.append((role, content)),
    )

    result = finalize_response_node(_state("Resposta crua"))

    assert result["response"] == "Resposta humanizada"
    assert calls[-1] == ("bot", "Resposta humanizada")
