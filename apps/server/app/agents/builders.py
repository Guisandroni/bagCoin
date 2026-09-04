"""Intent-specific response builders.

Each builder is a function (AgentState) -> str that formats the response
for one or more intents. They are pure functions — they take state and return
a string. The build_response_node dispatches to them via intent mapping.

Builders that need database access (greeting for user name, income for goal
suggestions) open their own short-lived DB sessions.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.agents import responses as resp
from app.agents.persistence import get_or_create_user
from app.agents.state import AgentState
from app.db.session import sync_session_maker
from app.schemas.enums import IntentType

logger = logging.getLogger(__name__)


# ── Transaction ─────────────────────────────────────────────────────────────

def build_transaction_response(state: AgentState) -> str:
    """Response for REGISTER_EXPENSE and REGISTER_INCOME."""
    extracted = state.get("extracted_data") or {}
    tx_type = extracted.get("type", "EXPENSE")
    amount = extracted.get("amount", 0)
    category = state.get("category_name") or extracted.get("category", "Outros")
    desc = extracted.get("description", "")
    tx_date = (
        state.get("transaction_date")
        or extracted.get("date")
        or extracted.get("transaction_date")
    )

    text = resp.transaction_registered(tx_type, amount, category, desc, tx_date)

    alerts = state.get("alerts") or []
    if alerts:
        alert_texts = [a["message"] for a in alerts]
        text += "\n\n" + "\n".join(alert_texts)

    if tx_type == "INCOME":
        db = sync_session_maker()
        try:
            user = get_or_create_user(state.get("phone_number", ""), db)
            from app.services.budget_service import get_goals

            goals = get_goals(state.get("phone_number", ""))
            active_goals = [g for g in goals if g.get("status") == "active"]
            if active_goals:
                goal_names = ", ".join([g["title"] for g in active_goals[:3]])
                text += (
                    f"\n\nQuer direcionar parte para alguma meta? Você tem: {goal_names}"
                )
        except Exception:
            pass
        finally:
            db.close()

    return text


# ── Query ───────────────────────────────────────────────────────────────────

def build_query_response(state: AgentState) -> str:
    """Response for QUERY_DATA."""
    query_result = state.get("query_result") or {}
    if query_result.get("summary"):
        return query_result["summary"]
    return "Não encontrei dados para sua consulta."


# ── Report ──────────────────────────────────────────────────────────────────

def build_report_response(state: AgentState) -> str:
    """Response for GENERATE_REPORT."""
    return state.get("report_summary") or "Relatório gerado com sucesso!"


# ── Greeting ────────────────────────────────────────────────────────────────

def build_greeting_response(state: AgentState) -> str:
    """Response for GREETING."""
    db = sync_session_maker()
    try:
        user = get_or_create_user(state.get("phone_number", ""), db)
        name = user.name if hasattr(user, "name") and user.name else None
    except Exception:
        name = None
    finally:
        db.close()

    hour = datetime.now(UTC).hour
    if hour < 12:
        greeting_time = "Bom dia"
    elif hour < 18:
        greeting_time = "Boa tarde"
    else:
        greeting_time = "Boa noite"

    return resp.greeting(name=name, greeting_time=greeting_time)


# ── Help ────────────────────────────────────────────────────────────────────

def build_help_response(state: AgentState) -> str:
    """Response for HELP."""
    return resp.help_menu()


# ── Budget prompt ───────────────────────────────────────────────────────────

def build_budget_prompt_response(state: AgentState) -> str:
    """Response for CREATE_BUDGET when no response is already set."""
    if state.get("response"):
        return state["response"]
    return (
        "Para criar um orçamento, me diga algo como:\n"
        "• Orçamento de R$ 3000 para alimentação\n"
        "• Limite de R$ 800 para transporte"
    )


# ── Goal prompt ─────────────────────────────────────────────────────────────

def build_goal_prompt_response(state: AgentState) -> str:
    """Response for CREATE_GOAL when no response is already set."""
    if state.get("response"):
        return state["response"]
    return (
        "Para criar uma meta, me diga algo como:\n"
        "• Quero guardar R$ 5000 para viagem\n"
        "• Meta de reserva de emergência: R$ 10000"
    )


# ── Import statement ────────────────────────────────────────────────────────

def build_import_statement_response(state: AgentState) -> str:
    """Response for IMPORT_STATEMENT."""
    summary = state.get("import_summary")
    if summary:
        return summary
    return (
        "Para importar seu extrato, envie o arquivo diretamente aqui:\n"
        "• PDF do banco\n"
        "• CSV (Excel)\n"
        "• Arquivo OFX\n\n"
        "Suporto extratos do Nubank, Itaú, Bradesco, Caixa e outros.\n"
        "Assim que enviar, mostro uma prévia e peço confirmação antes de importar."
    )


# ── Fallback ────────────────────────────────────────────────────────────────

def build_fallback_response(state: AgentState) -> str:
    """Fallback response for unknown intents. Uses LLM if available."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.services.llm_service import get_llm, timed_invoke

    message = state.get("message", "")
    llm = get_llm(temperature=0.7)
    if llm:
        try:
            msgs = [
                SystemMessage(
                    content="Você é o BagCoin, assistente financeiro. Responda de forma breve e útil."
                ),
                HumanMessage(content=message),
            ]
            r, _ = timed_invoke(llm, msgs, operation="build_response")
            response_text = r.content[:500]

            _bad_llm_patterns = [
                "sorry, i couldn't", "i couldn't process",
                "i'm sorry", "i am sorry", "sorry, i can't",
                "i cannot", "i'm unable", "i am unable",
                "as an ai", "as a language model",
            ]
            if any(p in response_text.lower() for p in _bad_llm_patterns):
                logger.warning(
                    f"[build_response] LLM returned generic error: {response_text[:100]}"
                )
                return resp.unknown_intent()
            return response_text
        except Exception:
            return resp.unknown_intent()
    return resp.unknown_intent()


# ── Dispatcher ──────────────────────────────────────────────────────────────

_BUILDERS: dict[str | None, Callable[[AgentState], str]] = {
    IntentType.REGISTER_EXPENSE.value: build_transaction_response,
    IntentType.REGISTER_INCOME.value: build_transaction_response,
    IntentType.QUERY_DATA.value: build_query_response,
    IntentType.GENERATE_REPORT.value: build_report_response,
    IntentType.GREETING.value: build_greeting_response,
    IntentType.HELP.value: build_help_response,
    IntentType.CREATE_BUDGET.value: build_budget_prompt_response,
    IntentType.CREATE_GOAL.value: build_goal_prompt_response,
    IntentType.IMPORT_STATEMENT.value: build_import_statement_response,
}
