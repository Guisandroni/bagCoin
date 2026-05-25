"""Ingestion agent — intent classification for BagCoin.

Classifies using LLM as primary classifier with 8 macro-intents.
Fast-paths: wizard state, single-word, just-number.
"""

import logging
import re
import time
import unicodedata
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from app.schemas.enums import IntentType
from app.services.llm_service import get_llm, timed_invoke

logger = logging.getLogger(__name__)

# Mapeamento: macro-intent → IntentType
MACRO_TO_INTENT: dict[str, str] = {
    "register": IntentType.REGISTER_EXPENSE.value,
    "query": IntentType.QUERY_DATA.value,
    "manage": IntentType.CREATE_BUDGET.value,  # proxy — roteado downstream
    "report": IntentType.GENERATE_REPORT.value,
    "import_stmt": IntentType.IMPORT_STATEMENT.value,
    "chat": IntentType.CHAT.value,
    "recommend": IntentType.RECOMMENDATION.value,
    "research": IntentType.DEEP_RESEARCH.value,
}


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ASCII", "ignore").decode("ASCII")


def _looks_like_budget_or_goal_request(msg_norm: str) -> bool:
    """Detect messages that are clearly about creating a budget or goal, not a transaction."""
    if not msg_norm:
        return False
    has_budget_keyword = any(kw in msg_norm for kw in ("orcamento", "limite"))
    has_goal_keyword = "meta" in msg_norm and "orcamento" not in msg_norm
    if not (has_budget_keyword or has_goal_keyword):
        return False
    # Must have a numeric value
    has_value = bool(re.search(r"\d+", msg_norm))
    if not has_value:
        return False
    # Exclude if it looks like a spending report query
    report_markers = ("quanto", "como estao", "resumo", "relatorio", "saldo")
    if any(m in msg_norm for m in report_markers):
        return False
    return True


def _looks_like_report_summary_request(msg_norm: str) -> bool:
    """Detect broad financial summary requests that should generate a PDF report."""
    if not msg_norm:
        return False

    concept_markers = ("o que e", "como funciona", "pra que serve", "para que serve")
    if any(marker in msg_norm for marker in concept_markers):
        return False

    specific_query_markers = (
        "meta",
        "metas",
        "orcamento",
        "orcamentos",
        "categoria",
        "categorias",
        "transacao",
        "transacoes",
    )
    if any(marker in msg_norm for marker in specific_query_markers):
        return False

    report_markers = (
        "quanto ja gastei",
        "quanto gastei",
        "como estao minhas despesas",
        "como estao meus gastos",
        "como estao minhas receitas",
        "resumo das minhas financas",
        "resumo financeiro",
        "resumo do mes",
        "balanco",
        "qual meu saldo",
        "minhas despesas",
        "meus gastos",
        "minhas receitas",
    )
    return any(marker in msg_norm for marker in report_markers)


def _enrich_system_prompt(phone_number: str) -> str:
    from app.agents.prompts.classify_intent import build_classify_prompt

    history = ""
    try:
        from app.agents.persistence import get_conversation_history
        history = get_conversation_history(phone_number, limit=4)
    except Exception:
        pass
    return build_classify_prompt(history=history)


def classify_intent(state: dict[str, Any]) -> dict[str, Any]:
    """Classify usando LLM com 8 macro-intencoes + fast-paths."""
    start_time = time.time()
    message = state.get("message", "")
    phone_number = state.get("phone_number", "")
    msg_norm = _normalize(message)

    # =====================================================================
    # FAST-PATH 1: Wizard state (must be instant)
    # =====================================================================
    from app.agents.wizard import _clear_wizard_state, _is_wizard_intent, _load_wizard_state

    wizard_state = _load_wizard_state(phone_number)
    if wizard_state:
        wizard_type = wizard_state.get("type", "")
        wizard_status = wizard_state.get("status", "")

        cancel_words = ["cancelar", "cancela", "sair", "voltar", "esquece", "desistir"]
        if any(w in msg_norm for w in cancel_words):
            _clear_wizard_state(phone_number)
            logger.info("[classify_intent] Wizard cancelled by user")
        elif _is_wizard_intent(wizard_type) and wizard_status in ["collecting", "confirming"]:
            intent_map = {
                "create_budget": IntentType.CREATE_BUDGET.value,
                "create_goal": IntentType.CREATE_GOAL.value,
                "update_goal": IntentType.CONTRIBUTE_GOAL.value,
                "contribute_goal": IntentType.CONTRIBUTE_GOAL.value,
            }
            state["intent"] = intent_map.get(wizard_type, IntentType.UNKNOWN.value)
            state["confidence"] = 0.9
            state["wizard"] = wizard_state
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"[classify_intent] Wizard continuation: {elapsed:.0f}ms")
            return state

    # =====================================================================
    # FAST-PATH 2: Just a number — ask for clarification
    # =====================================================================
    only_number = re.match(
        r"^\s*(?:r\$|R\$)?\s*(\d+(?:[.,]\d{1,2})?)\s*(?:reais|real|pila|conto|pau)?\s*$",
        message,
    )
    if only_number:
        state["intent"] = IntentType.CHAT.value
        state["confidence"] = 1.0
        state["response"] = (
            "Só o valor não dá pra saber o que fazer! 😅\n"
            "Isso foi um gasto ou uma receita? E em qual categoria?\n"
            "Ex: 'Gastei R$ 52 no mercado' ou 'Recebi R$ 100 de freelas'"
        )
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[classify_intent] Fast-path: just number → chat ({elapsed:.0f}ms)")
        return state

    # =====================================================================
    # FAST-PATH 3: "orçamento"/"meta" with value → manage (not register)
    # =====================================================================
    if _looks_like_budget_or_goal_request(msg_norm):
        if "meta" in msg_norm and "orcamento" not in msg_norm:
            state["intent"] = IntentType.CREATE_GOAL.value
        else:
            state["intent"] = IntentType.CREATE_BUDGET.value
        state["macro_intent"] = "manage"
        state["confidence"] = 1.0
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[classify_intent] Fast-path: budget/goal manage ({elapsed:.0f}ms)")
        return state

    # =====================================================================
    # FAST-PATH 4: broad financial summary → PDF report
    # =====================================================================
    if _looks_like_report_summary_request(msg_norm):
        state["intent"] = IntentType.GENERATE_REPORT.value
        state["macro_intent"] = "report"
        state["confidence"] = 1.0
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"[classify_intent] Fast-path: summary report ({elapsed:.0f}ms)")
        return state

    # =====================================================================
    # LLM PRIMARY CLASSIFIER (8 macro-intencoes)
    # =====================================================================
    llm_start = time.time()
    llm = get_llm(temperature=0.1)

    if not llm:
        # Fallback sem LLM — pergunta pro usuario
        logger.warning("[classify_intent] No LLM — asking user to rephrase")
        state["intent"] = IntentType.CHAT.value
        state["confidence"] = 0.3
        state["response"] = (
            "Pode me explicar de outra forma? 😊\n"
            "Quer registrar um gasto, consultar algo, ou precisa de ajuda?"
        )
        return state

    system_prompt = _enrich_system_prompt(phone_number)
    llm_init_ms = (time.time() - llm_start) * 1000
    logger.info(f"[classify_intent] get_llm() init: {llm_init_ms:.0f}ms")

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Mensagem: {message}"),
        ]
        response, latency_ms = timed_invoke(llm, messages, operation="classify_intent")
        result = JsonOutputParser().parse(response.content)

        macro_intent = result.get("intent", "chat")
        confidence = result.get("confidence", 0.5)

        # Map macro-intent to IntentType
        intent_value = MACRO_TO_INTENT.get(macro_intent, IntentType.CHAT.value)
        state["intent"] = intent_value
        state["confidence"] = confidence

        # Store macro-intent for downstream routing
        state["macro_intent"] = macro_intent

        total_elapsed = (time.time() - start_time) * 1000
        logger.info(
            f"[classify_intent] macro={macro_intent} → intent={intent_value} "
            f"(LLM={latency_ms:.0f}ms, total={total_elapsed:.0f}ms)"
        )

    except Exception as e:
        total_elapsed = (time.time() - start_time) * 1000
        logger.error(f"[classify_intent] LLM error after {total_elapsed:.0f}ms: {e}")
        state["intent"] = IntentType.CHAT.value
        state["confidence"] = 0.0
        state["response"] = (
            "Pode repetir de outro jeito? Não entendi muito bem. 😊"
        )

    return state
