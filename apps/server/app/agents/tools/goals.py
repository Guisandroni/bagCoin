"""Goal tools for BagCoin chat agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agents import responses as resp
from app.agents.pending_actions import save_pending_action
from app.services.budget_service import get_goals


def create_goal_tools(phone_number: str, context: dict | None = None) -> list[BaseTool]:
    channel = str((context or {}).get("channel") or "whatsapp")

    @tool
    def prepare_create_goal(title: str, target_amount: float, deadline: str | None = None) -> str:
        """Prepare a financial goal for confirmation before creating it."""
        if target_amount <= 0:
            return "Qual e o valor alvo da meta?"
        return save_pending_action(
            phone_number,
            action="create_goal",
            params={"title": title, "target_amount": float(target_amount), "deadline": deadline},
            summary=resp.goal_confirmation(title, float(target_amount), deadline),
            channel=channel,
        )

    @tool
    def list_goals() -> str:
        """List active goals with progress."""
        return resp.goal_list(get_goals(phone_number))

    @tool
    def prepare_contribute_goal(goal_identifier: str, amount: float) -> str:
        """Prepare adding money to a goal for confirmation."""
        if amount <= 0:
            return "Qual valor voce quer adicionar a meta?"
        return save_pending_action(
            phone_number,
            action="contribute_goal",
            params={"goal_identifier": goal_identifier, "amount": float(amount)},
            summary=resp.goal_contribution_confirmation(goal_identifier, float(amount)),
            channel=channel,
        )

    @tool
    def prepare_update_goal(
        goal_identifier: str,
        title: str | None = None,
        target_amount: float | None = None,
        deadline: str | None = None,
    ) -> str:
        """Prepare updating a goal for confirmation."""
        if not title and target_amount is None and not deadline:
            return "O que voce quer atualizar nessa meta?"
        return save_pending_action(
            phone_number,
            action="update_goal",
            params={
                "goal_identifier": goal_identifier,
                "title": title,
                "target_amount": target_amount,
                "deadline": deadline,
            },
            summary=resp.goal_update_confirmation(
                goal_identifier,
                title=title,
                target_amount=target_amount,
                deadline=deadline,
            ),
            channel=channel,
        )

    @tool
    def prepare_delete_goal(goal_identifier: str) -> str:
        """Prepare deleting a goal for confirmation."""
        return save_pending_action(
            phone_number,
            action="delete_goal",
            params={"goal_identifier": goal_identifier},
            summary=resp.goal_delete_confirmation(goal_identifier),
            channel=channel,
        )

    return [
        prepare_create_goal,
        list_goals,
        prepare_contribute_goal,
        prepare_update_goal,
        prepare_delete_goal,
    ]
