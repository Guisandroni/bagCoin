"""Budget tools for BagCoin chat agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agents import responses as resp
from app.agents.pending_actions import save_pending_action
from app.core.financial_categories import resolve_default_category_name
from app.services.budget_service import get_budgets


def create_budget_tools(phone_number: str, context: dict | None = None) -> list[BaseTool]:
    channel = str((context or {}).get("channel") or "whatsapp")

    @tool
    def prepare_create_budget(name: str, total_limit: float, period: str = "monthly") -> str:
        """Prepare a category budget for confirmation before creating it."""
        if total_limit <= 0:
            return "Qual e o limite do orcamento?"
        clean_name = resolve_default_category_name((name or "").strip() or "Outros")
        clean_period = "monthly"
        summary = resp.budget_confirmation(clean_name, float(total_limit), clean_period)
        return save_pending_action(
            phone_number,
            action="create_budget",
            params={
                "name": clean_name,
                "total_limit": float(total_limit),
                "period": clean_period,
                "budget_type": "category",
            },
            summary=summary,
            channel=channel,
        )

    @tool
    def list_budgets() -> str:
        """List active budgets with current usage."""
        return resp.budget_list(get_budgets(phone_number))

    @tool
    def prepare_update_budget(name: str, total_limit: float) -> str:
        """Prepare a budget limit update for confirmation."""
        if total_limit <= 0:
            return "Qual e o novo limite do orcamento?"
        return save_pending_action(
            phone_number,
            action="update_budget",
            params={"name": name, "total_limit": float(total_limit)},
            summary=f"Vou atualizar o orcamento {name} para R$ {float(total_limit):,.2f}.",
            channel=channel,
        )

    @tool
    def prepare_delete_budget(name: str) -> str:
        """Prepare budget deletion for confirmation."""
        return save_pending_action(
            phone_number,
            action="delete_budget",
            params={"name": name},
            summary=f"Vou remover o orcamento {name}.",
            channel=channel,
        )

    return [prepare_create_budget, list_budgets, prepare_update_budget, prepare_delete_budget]
