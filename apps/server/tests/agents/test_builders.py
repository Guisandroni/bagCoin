"""Tests for individual response builders extracted from build_response_node.

Each builder is a function (AgentState) -> str that formats a response
for a specific intent. Tests verify the right text is produced for known inputs.
"""

import pytest
from typing import Any, cast

from app.agents.state import AgentState
from app.schemas.enums import IntentType


# ── Helpers ────────────────────────────────────────────────────────────────

def _state(**overrides: Any) -> AgentState:
    """Build a minimal AgentState with sensible defaults."""
    base: dict[str, Any] = {
        "phone_number": "5511999999999",
        "user_id": None,
        "message": "",
        "intent": None,
        "extracted_data": None,
        "query_result": None,
        "report_id": None,
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
        "response": None,
        "context": {},
        "error": None,
        "source_format": "text",
    }
    base.update(overrides)
    return cast(AgentState, base)


# ── build_transaction_response ──────────────────────────────────────────────

class TestBuildTransactionResponse:
    def test_expense_with_category(self, monkeypatch):
        from app.agents.builders import build_transaction_response

        state = _state(
            intent=IntentType.REGISTER_EXPENSE.value,
            extracted_data={
                "type": "EXPENSE",
                "amount": 50.0,
                "category": "Alimentação",
                "description": "Mercado",
            },
        )
        result = build_transaction_response(state)
        assert "R$ 50,00" in result
        assert "Alimentação" in result

    def test_expense_with_alerts_appends_alert_text(self):
        from app.agents.builders import build_transaction_response

        state = _state(
            intent=IntentType.REGISTER_EXPENSE.value,
            extracted_data={"type": "EXPENSE", "amount": 500.0, "category": "Alimentação"},
            alerts=[{"message": "⚠️ Você já gastou 80% do orçamento de Alimentação!"}],
        )
        result = build_transaction_response(state)
        assert "80%" in result

    def test_income_suggests_goals_when_active(self, monkeypatch):
        from app.agents.builders import build_transaction_response

        monkeypatch.setattr(
            "app.agents.builders.sync_session_maker",
            lambda: None,
        )
        monkeypatch.setattr(
            "app.agents.builders.get_or_create_user",
            lambda phone, db: type("U", (), {"name": "Ana"})(),
        )
        monkeypatch.setattr(
            "app.services.budget_service.get_goals",
            lambda phone: [{"title": "Viagem", "status": "active"}],
        )

        state = _state(
            intent=IntentType.REGISTER_INCOME.value,
            extracted_data={
                "type": "INCOME",
                "amount": 5000.0,
                "category": "Salário",
                "description": "Salário",
            },
        )
        result = build_transaction_response(state)
        assert "meta" in result.lower() or "Viagem" in result

    def test_income_no_active_goals_no_suggestion(self, monkeypatch):
        from app.agents.builders import build_transaction_response

        monkeypatch.setattr("app.agents.builders.sync_session_maker", lambda: None)
        monkeypatch.setattr(
            "app.agents.builders.get_or_create_user",
            lambda phone, db: type("U", (), {"name": "Ana"})(),
        )
        monkeypatch.setattr(
            "app.services.budget_service.get_goals",
            lambda phone: [],
        )

        state = _state(
            intent=IntentType.REGISTER_INCOME.value,
            extracted_data={"type": "INCOME", "amount": 5000.0, "category": "Salário"},
        )
        result = build_transaction_response(state)
        assert "meta" not in result.lower()


# ── build_query_response ────────────────────────────────────────────────────

class TestBuildQueryResponse:
    def test_returns_summary_when_present(self):
        from app.agents.builders import build_query_response

        state = _state(
            intent=IntentType.QUERY_DATA.value,
            query_result={"summary": "Você gastou R$ 1.200,00 este mês."},
        )
        result = build_query_response(state)
        assert "R$ 1.200,00" in result

    def test_fallback_when_no_summary(self):
        from app.agents.builders import build_query_response

        state = _state(intent=IntentType.QUERY_DATA.value, query_result={})
        result = build_query_response(state)
        assert "Não encontrei" in result


# ── build_report_response ───────────────────────────────────────────────────

class TestBuildReportResponse:
    def test_returns_summary(self):
        from app.agents.builders import build_report_response

        state = _state(
            intent=IntentType.GENERATE_REPORT.value,
            report_summary="Relatório de maio gerado.",
        )
        result = build_report_response(state)
        assert "maio" in result

    def test_default_message_when_no_summary(self):
        from app.agents.builders import build_report_response

        state = _state(intent=IntentType.GENERATE_REPORT.value)
        result = build_report_response(state)
        assert "Relatório" in result


# ── build_greeting_response ─────────────────────────────────────────────────

class TestBuildGreetingResponse:
    def test_greeting_includes_name(self, monkeypatch):
        from app.agents.builders import build_greeting_response

        monkeypatch.setattr("app.agents.builders.sync_session_maker", lambda: None)
        monkeypatch.setattr(
            "app.agents.builders.get_or_create_user",
            lambda phone, db: type("U", (), {"name": "Carlos"})(),
        )

        state = _state(intent=IntentType.GREETING.value)
        result = build_greeting_response(state)
        assert "Carlos" in result

    def test_greeting_without_name(self, monkeypatch):
        from app.agents.builders import build_greeting_response

        monkeypatch.setattr("app.agents.builders.sync_session_maker", lambda: None)
        # User without name
        monkeypatch.setattr(
            "app.agents.builders.get_or_create_user",
            lambda phone, db: type("U", (), {"name": None})(),
        )

        state = _state(intent=IntentType.GREETING.value)
        result = build_greeting_response(state)
        # Should still produce a greeting
        assert len(result) > 0


# ── build_help_response ─────────────────────────────────────────────────────

class TestBuildHelpResponse:
    def test_returns_help_menu(self):
        from app.agents.builders import build_help_response

        state = _state(intent=IntentType.HELP.value)
        result = build_help_response(state)
        assert len(result) > 0


# ── build_budget_prompt_response ────────────────────────────────────────────

class TestBuildBudgetPromptResponse:
    def test_returns_prompt_when_no_response(self):
        from app.agents.builders import build_budget_prompt_response

        state = _state(intent=IntentType.CREATE_BUDGET.value, response=None)
        result = build_budget_prompt_response(state)
        assert "orçamento" in result.lower()

    def test_returns_existing_response_unchanged(self):
        from app.agents.builders import build_budget_prompt_response

        state = _state(intent=IntentType.CREATE_BUDGET.value, response="Já criado!")
        result = build_budget_prompt_response(state)
        assert result == "Já criado!"


# ── build_goal_prompt_response ──────────────────────────────────────────────

class TestBuildGoalPromptResponse:
    def test_returns_prompt_when_no_response(self):
        from app.agents.builders import build_goal_prompt_response

        state = _state(intent=IntentType.CREATE_GOAL.value, response=None)
        result = build_goal_prompt_response(state)
        assert "meta" in result.lower()

    def test_returns_existing_response_unchanged(self):
        from app.agents.builders import build_goal_prompt_response

        state = _state(intent=IntentType.CREATE_GOAL.value, response="Meta criada!")
        result = build_goal_prompt_response(state)
        assert result == "Meta criada!"


# ── build_import_statement_response ─────────────────────────────────────────

class TestBuildImportStatementResponse:
    def test_returns_summary_when_present(self):
        from app.agents.builders import build_import_statement_response

        state = _state(
            intent=IntentType.IMPORT_STATEMENT.value,
            import_summary="12 transações importadas.",
        )
        result = build_import_statement_response(state)
        assert "12" in result

    def test_returns_prompt_when_no_summary(self):
        from app.agents.builders import build_import_statement_response

        state = _state(intent=IntentType.IMPORT_STATEMENT.value)
        result = build_import_statement_response(state)
        assert "extrato" in result.lower() or "PDF" in result


# ── build_fallback_response ─────────────────────────────────────────────────

class TestBuildFallbackResponse:
    def test_returns_unknown_intent_when_llm_disabled(self, monkeypatch):
        from app.agents.builders import build_fallback_response

        monkeypatch.setattr(
            "app.services.llm_service.get_llm", lambda **kw: None
        )

        state = _state(intent=IntentType.CHAT.value, message="blablabla")
        result = build_fallback_response(state)
        assert len(result) > 0


# ── build_response_node dispatcher ──────────────────────────────────────────

class TestBuildResponseNodeDispatcher:
    def test_bracket_message_passthrough(self, monkeypatch):
        from app.agents.orchestrator import build_response_node

        state = _state(message="[erro interno]", response=None)
        result = build_response_node(dict(state))
        assert result["response"] == "erro interno"

    def test_keeps_existing_response(self, monkeypatch):
        from app.agents.orchestrator import build_response_node

        state = _state(intent=IntentType.HELP.value, response="resposta pronta")
        result = build_response_node(dict(state))
        assert result["response"] == "resposta pronta"

    def test_error_uses_error_message(self, monkeypatch):
        from app.agents.orchestrator import build_response_node

        state = _state(error="media_failure:unknown", message="oi")
        result = build_response_node(dict(state))
        response = result.get("response") or ""
        assert "erro" in response.lower() or len(response) > 0

    def test_dispatches_to_intent_builder(self, monkeypatch):
        from app.agents.orchestrator import build_response_node

        state = _state(
            intent=IntentType.QUERY_DATA.value,
            query_result={"summary": "Você gastou R$ 50,00."},
        )
        result = build_response_node(dict(state))
        assert result["response"] == "Você gastou R$ 50,00."

    def test_import_summary_wins_for_unknown_intent(self, monkeypatch):
        """Old code: import_summary beat the LLM fallback for intents without a
        dedicated branch. The dispatcher must preserve that."""
        from app.agents.orchestrator import build_response_node

        state = _state(
            intent=IntentType.CHAT.value,
            import_summary="10 transações importadas.",
        )
        result = build_response_node(dict(state))
        assert result["response"] == "10 transações importadas."

    def test_import_statement_with_summary_uses_builder(self, monkeypatch):
        from app.agents.orchestrator import build_response_node

        state = _state(
            intent=IntentType.IMPORT_STATEMENT.value,
            import_summary="5 transações importadas.",
        )
        result = build_response_node(dict(state))
        assert result["response"] == "5 transações importadas."
