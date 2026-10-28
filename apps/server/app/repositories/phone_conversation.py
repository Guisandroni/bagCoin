"""PhoneConversation repository (PostgreSQL async).

Tracks WhatsApp/Telegram conversation context for BagCoin agents.
"""

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.phone_conversation import PhoneConversation
from app.db.models.conversation_message import ConversationMessage


async def get_by_id(db: AsyncSession, conv_id: int) -> PhoneConversation | None:
    """Get conversation by ID."""
    return await db.get(PhoneConversation, conv_id)


async def get_last_by_user(
    db: AsyncSession,
    user_id: int,
) -> PhoneConversation | None:
    """Get the most recent conversation for a user."""
    result = await db.execute(
        select(PhoneConversation)
        .where(PhoneConversation.user_id == user_id)
        .order_by(PhoneConversation.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_or_create(
    db: AsyncSession,
    *,
    user_id: int,
    channel: str = "whatsapp",
) -> PhoneConversation:
    """Get the latest conversation or create a new one."""
    existing = await get_last_by_user(db, user_id)
    if existing:
        return existing

    conv = PhoneConversation(
        user_id=user_id,
        channel=channel,
        context_json={},
        message_history=[],
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    channel: str = "whatsapp",
    last_intent: str | None = None,
    context_json: dict | None = None,
    message_history: list | None = None,
) -> PhoneConversation:
    """Create a new conversation record."""
    conv = PhoneConversation(
        user_id=user_id,
        channel=channel,
        last_intent=last_intent,
        context_json=context_json or {},
        message_history=message_history or [],
    )
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def update_context(
    db: AsyncSession,
    conv_id: int,
    context_updates: dict[str, Any],
) -> PhoneConversation | None:
    """Update conversation context (partial merge with flag_modified)."""
    conv = await get_by_id(db, conv_id)
    if not conv:
        return None

    existing = dict(conv.context_json or {})
    existing.update(context_updates)
    conv.context_json = existing
    flag_modified(conv, "context_json")
    await db.flush()
    await db.refresh(conv)
    return conv


async def save_message(
    db: AsyncSession,
    conv: PhoneConversation,
    role: str,
    content: str,
    max_history: int = 50,
) -> PhoneConversation:
    """Append a message to the conversation history."""
    history = list(conv.message_history or [])
    history.append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    conv.message_history = history[-max_history:]
    flag_modified(conv, "message_history")
    db.add(
        ConversationMessage(
            conversation_id=conv.id,
            user_id=conv.user_id,
            channel=conv.channel,
            role=role,
            content=content,
            message_metadata={"source": "repository"},
        )
    )
    await db.flush()
    await db.refresh(conv)
    return conv


async def get_message_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> list[dict]:
    """Get recent message history for a user."""
    conv = await get_last_by_user(db, user_id)
    if not conv:
        return []
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv.id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    if messages:
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "metadata": msg.message_metadata or {},
            }
            for msg in messages
        ]
    return (conv.message_history or [])[-limit:]


async def update_intent(
    db: AsyncSession,
    conv_id: int,
    intent: str,
) -> PhoneConversation | None:
    """Update the last intent of a conversation."""
    conv = await get_by_id(db, conv_id)
    if not conv:
        return None
    conv.last_intent = intent
    await db.flush()
    await db.refresh(conv)
    return conv
