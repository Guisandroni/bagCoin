"""Agent memory and context helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.agent_memory_event import AgentMemoryEvent
from app.db.models.budget import Budget
from app.db.models.conversation_message import ConversationMessage
from app.db.models.goal import Goal
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.transaction import Transaction
from app.db.session import sync_session_maker

logger = logging.getLogger(__name__)


def add_memory_event(
    db,
    *,
    user_id: int,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    source: str = "agent",
    summary: str | None = None,
    payload: dict[str, Any] | None = None,
    conversation_id: int | None = None,
) -> AgentMemoryEvent:
    """Add a structured memory event to the provided sync or async session."""
    event = AgentMemoryEvent(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        source=source,
        summary=summary,
        payload=payload or {},
    )
    db.add(event)
    return event


def add_conversation_message(
    db,
    *,
    user_id: int,
    conversation_id: int | None,
    channel: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> ConversationMessage:
    """Add a full conversation message to the provided sync or async session."""
    message = ConversationMessage(
        user_id=user_id,
        conversation_id=conversation_id,
        channel=channel,
        role=role,
        content=content,
        message_metadata=metadata or {},
    )
    db.add(message)
    return message


def record_memory_event_for_phone(
    phone_number: str,
    *,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    source: str = "agent",
    summary: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Record an event for a chat user without leaking failures into the agent flow."""
    from app.agents.persistence import get_or_create_user

    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = _latest_conversation(db, user.id)
        add_memory_event(
            db,
            user_id=user.id,
            conversation_id=conv.id if conv else None,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
            summary=summary,
            payload=payload,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[agent_memory] failed to record event=%s", event_type)
    finally:
        db.close()


def build_agent_context_text(phone_number: str, *, message_limit: int = 8, event_limit: int = 12) -> str:
    """Build a compact, structured context block for LLM prompts."""
    from app.agents.persistence import get_or_create_user

    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = _latest_conversation(db, user.id)
        context = dict(conv.context_json or {}) if conv else {}
        parts: list[str] = []

        pending = context.get("pending_tool_action")
        if pending:
            parts.append(f"Ação pendente: {pending.get('action')} params={pending.get('params')}")

        wizard = context.get("wizard")
        if wizard:
            parts.append(
                f"Wizard ativo: {wizard.get('type')} "
                f"status={wizard.get('status')} dados={wizard.get('collected')}"
            )

        summary = context.get("conversation_summary")
        if summary:
            parts.append(f"Resumo da conversa: {summary}")

        messages = _recent_messages(db, user.id, limit=message_limit)
        if messages:
            lines = []
            for msg in messages:
                label = "Usuário" if msg.role == "user" else "BagCoin"
                lines.append(f"{label}: {msg.content[:240]}")
            parts.append("Últimas mensagens:\n" + "\n".join(lines))

        events = _recent_events(db, user.id, limit=event_limit)
        if events:
            lines = []
            for event in events:
                summary_text = event.summary or event.event_type
                lines.append(f"- {event.event_type}: {summary_text[:240]}")
            parts.append("Eventos financeiros recentes:\n" + "\n".join(lines))

        financial = _financial_snapshot(db, user.id)
        if financial:
            parts.append(financial)

        return "\n\n".join(parts)
    except Exception:
        logger.exception("[agent_memory] failed to build context")
        return ""
    finally:
        db.close()


def _latest_conversation(db, user_id: int) -> PhoneConversation | None:
    return (
        db.query(PhoneConversation)
        .filter(PhoneConversation.user_id == user_id)
        .order_by(PhoneConversation.updated_at.desc().nulls_last(), PhoneConversation.id.desc())
        .first()
    )


def _recent_messages(db, user_id: int, *, limit: int) -> list[ConversationMessage]:
    return list(
        reversed(
            db.query(ConversationMessage)
            .filter(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(limit)
            .all()
        )
    )


def _recent_events(db, user_id: int, *, limit: int) -> list[AgentMemoryEvent]:
    return list(
        reversed(
            db.query(AgentMemoryEvent)
            .filter(AgentMemoryEvent.user_id == user_id)
            .order_by(AgentMemoryEvent.created_at.desc(), AgentMemoryEvent.id.desc())
            .limit(limit)
            .all()
        )
    )


def _financial_snapshot(db, user_id: int) -> str:
    parts: list[str] = []
    txs = (
        db.query(Transaction)
        .options(selectinload(Transaction.category))
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc().nulls_last(), Transaction.id.desc())
        .limit(5)
        .all()
    )
    if txs:
        lines = []
        for tx in txs:
            cat = tx.category.name if tx.category else "Sem categoria"
            when = tx.transaction_date.strftime("%d/%m/%Y") if tx.transaction_date else "sem data"
            lines.append(f"- {tx.type} R$ {float(tx.amount):.2f} em {cat}: {tx.description or '-'} ({when})")
        parts.append("Últimas transações:\n" + "\n".join(lines))

    budgets = (
        db.query(Budget)
        .options(selectinload(Budget.category))
        .filter(Budget.user_id == user_id)
        .order_by(Budget.updated_at.desc().nulls_last(), Budget.id.desc())
        .limit(5)
        .all()
    )
    if budgets:
        lines = [f"- {b.name}: limite R$ {float(b.total_limit or 0):.2f} ({b.period})" for b in budgets]
        parts.append("Orçamentos recentes:\n" + "\n".join(lines))

    goals = (
        db.query(Goal)
        .filter(Goal.user_id == user_id)
        .order_by(Goal.updated_at.desc().nulls_last(), Goal.id.desc())
        .limit(5)
        .all()
    )
    if goals:
        lines = [
            f"- {g.title}: R$ {float(g.current_amount or 0):.2f} / R$ {float(g.target_amount or 0):.2f}"
            for g in goals
        ]
        parts.append("Metas recentes:\n" + "\n".join(lines))

    return "\n\n".join(parts)


async def add_memory_event_async(
    db,
    *,
    user_id: int,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    source: str = "web",
    summary: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AgentMemoryEvent:
    """Async-friendly event helper for REST services."""
    result = await db.execute(
        select(PhoneConversation)
        .where(PhoneConversation.user_id == user_id)
        .order_by(PhoneConversation.updated_at.desc().nulls_last(), PhoneConversation.id.desc())
    )
    conv = result.scalars().first()
    return add_memory_event(
        db,
        user_id=user_id,
        conversation_id=conv.id if conv else None,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        source=source,
        summary=summary,
        payload=payload,
    )
