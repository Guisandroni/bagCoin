from langchain_core.tools import tool

from app.agents.ingestion import classify_intent
from app.agents.tool_agent import run_tool_agent
from app.schemas.enums import IntentType


def test_classify_delete_budget_is_manage_action(monkeypatch):
    monkeypatch.setattr("app.agents.wizard._load_wizard_state", lambda _phone: None)

    state = {
        "phone_number": "5511999999999",
        "message": "excluir orcamento compras",
    }

    result = classify_intent(state)

    assert result["intent"] == IntentType.DELETE_BUDGET.value
    assert result["macro_intent"] == "manage"


def test_classify_update_goal_is_manage_action(monkeypatch):
    monkeypatch.setattr("app.agents.wizard._load_wizard_state", lambda _phone: None)

    state = {
        "phone_number": "5511999999999",
        "message": "editar meta comprar carro para 6000",
    }

    result = classify_intent(state)

    assert result["intent"] == IntentType.UPDATE_GOAL.value
    assert result["macro_intent"] == "manage"


def test_classify_number_continues_update_budget_wizard(monkeypatch):
    monkeypatch.setattr(
        "app.agents.wizard._load_wizard_state",
        lambda _phone: {
            "type": "update_budget",
            "status": "collecting",
            "collected": {"name": "Combustível"},
            "missing": ["total_limit"],
        },
    )

    state = {
        "phone_number": "5511999999999",
        "message": "200",
    }

    result = classify_intent(state)

    assert result["intent"] == IntentType.UPDATE_BUDGET.value
    assert result["wizard"]["type"] == "update_budget"


def test_tool_agent_returns_prepare_tool_result_without_llm_rewrite():
    @tool
    def prepare_create_goal(title: str) -> str:
        """Prepare goal creation."""
        return f"Meta {title}. Confirma?"

    class FakeResponse:
        content = "Meta criada com sucesso."
        tool_calls = [
            {
                "id": "call-1",
                "name": "prepare_create_goal",
                "args": {"title": "Comprar carro"},
            }
        ]

    class FakeLlm:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return FakeResponse()

    result = run_tool_agent(
        llm=FakeLlm(),
        tools=[prepare_create_goal],
        system_prompt="Use tools.",
        user_message="criar meta comprar carro",
    )

    assert result == "Meta Comprar carro. Confirma?"
