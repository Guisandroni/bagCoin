"""BagCoin conversation REST endpoints for web frontend.

Reuses the existing PhoneConversation model and services
to manage bagcoin conversation history and pending transactions.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.db.models.conversation_message import ConversationMessage
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.transaction import Transaction

router = APIRouter(prefix="/bagcoin/conversations", tags=["bagcoin"])


@router.get("")
async def list_conversations(
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """List the last 50 bagcoin conversations for the user."""
    result = await db.execute(
        select(PhoneConversation)
        .where(PhoneConversation.user_id == current_user.id)
        .order_by(PhoneConversation.updated_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()
    rows = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conv.id,
            )
        )
        message_count = int(count_result.scalar() or 0)
        if message_count == 0:
            message_count = len(conv.message_history or [])
        rows.append({
            "id": conv.id,
            "channel": conv.channel,
            "last_intent": conv.last_intent,
            "message_count": message_count,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        })
    return rows


@router.get("/{conv_id}/messages")
async def get_conversation_messages(
    conv_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """Get messages from a specific bagcoin conversation."""
    result = await db.execute(
        select(PhoneConversation).where(
            PhoneConversation.id == conv_id,
            PhoneConversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv.id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
    )
    messages = messages_result.scalars().all()
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
    return conv.message_history or []


@router.get("/pending")
async def get_pending_messages(
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """List pending transactions (low confidence) that need confirmation."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.confidence_score < 0.7,
        )
        .order_by(Transaction.created_at.desc())
        .limit(50)
    )
    transactions = result.scalars().all()
    return [
        {
            "id": tx.id,
            "type": tx.type,
            "amount": tx.amount,
            "description": tx.description,
            "transaction_date": tx.transaction_date.isoformat()
            if tx.transaction_date
            else None,
            "source_format": tx.source_format,
            "raw_input": tx.raw_input,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }
        for tx in transactions
    ]


@router.patch("/{conv_id}/messages/{msg_id}/confirm")
async def confirm_message(
    conv_id: int,
    msg_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> Any:
    """Confirm a pending transaction by its ID.

    Sets confidence_score to 1.0 to confirm the transaction.
    The msg_id parameter is the transaction ID (as string).
    """
    try:
        tx_id = int(msg_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.user_id == current_user.id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.confidence_score = 1.0
    db.add(tx)
    await db.flush()
    await db.refresh(tx)

    return {
        "id": tx.id,
        "status": "confirmed",
        "message": "Transaction confirmed successfully",
    }
