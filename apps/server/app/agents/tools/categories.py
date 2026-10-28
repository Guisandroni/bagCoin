"""Category tools for BagCoin chat agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agents.pending_actions import save_pending_action
from app.agents.persistence import list_categories


def create_category_tools(phone_number: str, context: dict | None = None) -> list[BaseTool]:
    channel = str((context or {}).get("channel") or "whatsapp")

    @tool
    def list_user_categories() -> str:
        """List user categories."""
        cats = list_categories(phone_number)
        if not cats:
            return "Voce ainda nao tem categorias."
        default_cats = [c["name"] for c in cats if c["is_default"]]
        custom_cats = [c["name"] for c in cats if not c["is_default"]]
        parts = ["Categorias:"]
        if default_cats:
            parts.append("Padrao: " + ", ".join(default_cats))
        if custom_cats:
            parts.append("Personalizadas: " + ", ".join(custom_cats))
        return "\n".join(parts)

    @tool
    def prepare_create_category(name: str) -> str:
        """Prepare creating a custom category for confirmation."""
        return save_pending_action(
            phone_number,
            action="create_category",
            params={"name": name},
            summary=f"Vou criar a categoria {name}.",
            channel=channel,
        )

    @tool
    def prepare_rename_category(old_name: str, new_name: str) -> str:
        """Prepare renaming a custom category for confirmation."""
        return save_pending_action(
            phone_number,
            action="rename_category",
            params={"old_name": old_name, "new_name": new_name},
            summary=f"Vou renomear {old_name} para {new_name}.",
            channel=channel,
        )

    @tool
    def prepare_delete_category(name: str) -> str:
        """Prepare deleting a custom category for confirmation."""
        return save_pending_action(
            phone_number,
            action="delete_category",
            params={"name": name},
            summary=f"Vou remover a categoria {name}.",
            channel=channel,
        )

    return [
        list_user_categories,
        prepare_create_category,
        prepare_rename_category,
        prepare_delete_category,
    ]
