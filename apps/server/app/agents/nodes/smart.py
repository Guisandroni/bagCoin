"""Tool-agent node handlers for financial queries and management."""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.agents import responses as resp
from app.agents.nodes.chat import wizard_handler_node
from app.agents.nodes.tool_context import tool_history
from app.agents.pending_actions import save_pending_action
from app.agents.routing import (
    _is_account_or_card_request,
    _is_budget_create_request,
    _msg_norm,
)
from app.agents.state import AgentState
from app.schemas.enums import IntentType
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


def smart_query_node(state: AgentState) -> AgentState:
    """Tool-based query agent for financial questions."""
    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import create_query_tools

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    llm = get_llm(temperature=0.2)
    if not llm:
        state["response"] = "Não consegui consultar seus dados agora. Tente novamente!"
        return state

    system_prompt = """Voce e o consultor financeiro do BagCoin.

Use as tools para consultar dados reais do usuario antes de responder.
Nao invente valores. Se a tool nao trouxer a informacao, diga isso.
Responda em portugues, curto e claro para WhatsApp."""

    try:
        state["response"] = run_tool_agent(
            llm=llm,
            tools=create_query_tools(phone_number),
            system_prompt=system_prompt,
            user_message=message,
            history=tool_history(phone_number, limit=4),
            max_iterations=3,
        )
    except Exception as exc:
        logger.warning("[smart_query] tool flow failed: %s", exc)
        state["response"] = "Ops, não consegui consultar. Tente de novo!"
    return state


def smart_manage_node(state: AgentState) -> AgentState:
    """Tool-based management agent for budgets, goals, categories and edits."""
    from app.agents.tool_agent import run_tool_agent
    from app.agents.tools import (
        create_budget_tools,
        create_category_tools,
        create_financial_tools,
        create_goal_tools,
    )

    phone_number = state.get("phone_number", "")
    message = state.get("message", "")
    msg_norm = _msg_norm(message)

    if _is_account_or_card_request(msg_norm):
        state["response"] = (
            "Por enquanto eu não crio contas, saldos ou cartões pelo chat. "
            "Posso criar um orçamento por categoria, por exemplo: "
            "'criar orçamento de R$ 500 para Supermercado'."
        )
        return state

    for deterministic_handler in (
        _prepare_budget_delete,
        _prepare_budget_update,
        _prepare_goal_delete,
        _prepare_goal_update,
    ):
        handled_state = deterministic_handler(state)
        if handled_state is not None:
            return handled_state

    from app.agents.wizard import _load_wizard_state

    wizard = _load_wizard_state(phone_number)
    if wizard and wizard.get("status") in ["collecting", "confirming"]:
        return wizard_handler_node(state)

    if _is_budget_create_request(msg_norm):
        budget_params = _extract_budget_request(message)
        if budget_params:
            state["response"] = save_pending_action(
                phone_number,
                action="create_budget",
                params=budget_params,
                summary=resp.budget_confirmation(
                    budget_params["name"],
                    float(budget_params["total_limit"]),
                    "monthly",
                ),
                channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
            )
            return state
        wizard_state = dict(state)
        wizard_state["intent"] = IntentType.CREATE_BUDGET.value
        return wizard_handler_node(AgentState(**wizard_state))

    llm = get_llm(temperature=0.1)
    if not llm:
        state["response"] = (
            "Nao consegui gerenciar isso com seguranca agora. "
            "Pode tentar novamente em instantes?"
        )
        return state

    context = state.get("context") or {}
    tools = [
        *create_budget_tools(phone_number, context),
        *create_goal_tools(phone_number, context),
        *create_financial_tools(phone_number, context),
        *create_category_tools(phone_number, context),
    ]
    system_prompt = """Voce e o gerenciador financeiro do BagCoin.

Objetivo: interpretar o que o usuario quer gerenciar e chamar a tool correta.

Regras:
- Use tools para orcamentos, metas, categorias, correcoes e exclusoes.
- Toda criacao, edicao ou exclusao deve ser preparada para confirmacao pela tool.
- Metas tambem devem ser sempre preparadas pela tool; nunca responda como se a meta ja tivesse sido salva antes da confirmacao.
- Orcamento precisa apenas de categoria e valor. Nunca peca descricao para orcamento.
- Se o usuario disser so "criar orcamento", peca categoria e valor em uma frase.
- Nao crie contas bancarias, saldos ou cartoes de credito.
- Orcamentos sao sempre por categoria, mensais, a cada 30 dias.
- Para consultas simples de categorias/metas/orcamentos, pode listar direto.
- Quando uma tool retornar dados reais, nao invente estado diferente do resultado da tool.
- Responda em portugues, breve e natural para WhatsApp."""

    try:
        state["response"] = run_tool_agent(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            user_message=message,
            history=tool_history(phone_number, limit=6),
            max_iterations=4,
        )
    except Exception as exc:
        logger.warning("[smart_manage_tool] tool flow failed: %s", exc)
        state["response"] = (
            "Nao consegui preparar essa acao com seguranca agora. "
            "Pode tentar novamente com mais detalhes?"
        )
    return state


def _extract_budget_request(message: str) -> dict[str, Any] | None:
    amount_match = re.search(
        r"(?:r\$?\s*)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)",
        message,
        flags=re.IGNORECASE,
    )
    if not amount_match:
        return None
    raw_amount = amount_match.group(1)
    normalized_amount = raw_amount.replace(".", "").replace(",", ".")
    try:
        total_limit = float(normalized_amount)
    except ValueError:
        return None

    category_text = message[: amount_match.start()] + " " + message[amount_match.end() :]
    category_text = _msg_norm(category_text)
    category_text = re.sub(
        r"\b(criar|crie|quero|novo|nova|definir|defina|adicionar|um|uma|de|do|da|para|pra|em|na|no|categoria|orcamento|orcamentos|limite|mensal|mes|por|r)\b",
        " ",
        category_text,
    )
    category_text = re.sub(r"\s+", " ", category_text).strip(" .,!?\n\t")
    if not category_text:
        return None

    from app.core.financial_categories import resolve_default_category_name

    return {
        "name": resolve_default_category_name(category_text),
        "total_limit": total_limit,
        "period": "monthly",
        "budget_type": "category",
    }


def _extract_money_amount(message: str) -> float | None:
    amount_match = re.search(
        r"(?:r\$?\s*)?(\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?)",
        message,
        flags=re.IGNORECASE,
    )
    if not amount_match:
        return None
    try:
        return float(amount_match.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _strip_management_words(text: str, *, target: str) -> str:
    msg = _msg_norm(text)
    msg = re.sub(r"(?:r\$?\s*)?\d{1,3}(?:[.,]\d{3})*[.,]\d{1,2}|\d+(?:[.,]\d{1,2})?", " ", msg)
    words = [
        "quero",
        "queria",
        "pode",
        "por favor",
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "para",
        "pra",
        "por",
        "em",
        "na",
        "no",
        "meu",
        "minha",
        "meus",
        "minhas",
        target,
        f"{target}s",
    ]
    action_words = [
        "excluir",
        "deletar",
        "apagar",
        "remover",
        "editar",
        "alterar",
        "atualizar",
        "mudar",
        "trocar",
        "aumentar",
        "diminuir",
        "novo",
        "nova",
        "limite",
        "valor",
        "reais",
        "real",
    ]
    pattern = r"\b(" + "|".join(re.escape(w) for w in words + action_words) + r")\b"
    msg = re.sub(pattern, " ", msg)
    return re.sub(r"\s+", " ", msg).strip(" .,!?\n\t")


def _prepare_budget_delete(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "orcamento" not in msg_norm or not any(w in msg_norm for w in ("excluir", "deletar", "apagar", "remover")):
        return None
    phone_number = state.get("phone_number", "")
    name = _strip_management_words(state.get("message", ""), target="orcamento")
    from app.core.financial_categories import resolve_default_category_name

    name = resolve_default_category_name(name) if name else ""
    if not name:
        from app.services.budget_service import get_budgets

        budgets = get_budgets(phone_number)
        state["response"] = (
            "Qual orçamento você quer excluir? " + ", ".join(b["name"] for b in budgets)
            if budgets
            else "Você não tem orçamentos para excluir."
        )
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="delete_budget",
        params={"name": name},
        summary=f"Vou remover o orçamento {name}.",
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_budget_update(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "orcamento" not in msg_norm or not any(w in msg_norm for w in ("editar", "alterar", "atualizar", "mudar", "trocar", "aumentar", "diminuir")):
        return None
    phone_number = state.get("phone_number", "")
    amount = _extract_money_amount(state.get("message", ""))
    name = _strip_management_words(state.get("message", ""), target="orcamento")
    from app.agents.wizard import _save_wizard_state
    from app.core.financial_categories import resolve_default_category_name

    name = resolve_default_category_name(name) if name else ""
    if not name:
        from app.services.budget_service import get_budgets

        budgets = get_budgets(phone_number)
        if not budgets:
            state["response"] = "Você não tem orçamentos para atualizar."
            return state
        _save_wizard_state(
            phone_number,
            {
                "type": "update_budget",
                "status": "collecting",
                "collected": {},
                "missing": ["name", "total_limit"],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        state["response"] = "Qual orçamento você quer atualizar? " + ", ".join(
            b["name"] for b in budgets
        )
        return state
    if amount is None:
        _save_wizard_state(
            phone_number,
            {
                "type": "update_budget",
                "status": "collecting",
                "collected": {"name": name},
                "missing": ["total_limit"],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        state["response"] = f"Qual é o novo limite do orçamento {name}?"
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="update_budget",
        params={"name": name, "total_limit": amount},
        summary=f"Vou atualizar o orçamento {name} para R$ {amount:,.2f}.",
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_goal_delete(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "meta" not in msg_norm or not any(w in msg_norm for w in ("excluir", "deletar", "apagar", "remover")):
        return None
    phone_number = state.get("phone_number", "")
    identifier = _strip_management_words(state.get("message", ""), target="meta")
    if not identifier:
        from app.services.budget_service import get_goals

        goals = get_goals(phone_number)
        state["response"] = (
            "Qual meta você quer excluir? " + ", ".join(g["title"] for g in goals)
            if goals
            else "Você não tem metas para excluir."
        )
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="delete_goal",
        params={"goal_identifier": identifier},
        summary=resp.goal_delete_confirmation(identifier),
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state


def _prepare_goal_update(state: AgentState) -> AgentState | None:
    msg_norm = _msg_norm(state.get("message", ""))
    if "meta" not in msg_norm or not any(w in msg_norm for w in ("editar", "alterar", "atualizar", "mudar", "trocar", "aumentar", "diminuir")):
        return None
    phone_number = state.get("phone_number", "")
    amount = _extract_money_amount(state.get("message", ""))
    identifier = _strip_management_words(state.get("message", ""), target="meta")
    if not identifier:
        from app.services.budget_service import get_goals

        goals = get_goals(phone_number)
        state["response"] = (
            "Qual meta você quer atualizar? " + ", ".join(g["title"] for g in goals)
            if goals
            else "Você não tem metas para atualizar."
        )
        return state
    if amount is None:
        state["response"] = f"O que você quer atualizar na meta {identifier}?"
        return state
    state["response"] = save_pending_action(
        phone_number,
        action="update_goal",
        params={"goal_identifier": identifier, "target_amount": amount},
        summary=resp.goal_update_confirmation(identifier, target_amount=amount),
        channel=str((state.get("context") or {}).get("channel") or "whatsapp"),
    )
    return state
