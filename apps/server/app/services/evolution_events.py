"""Conservative idempotency primitives; caller controls transaction commits."""

from secrets import token_hex

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.db.models.evolution_event import EvolutionEvent, EvolutionReply


def reserve_event(db: Session, instance: str, message_id: str) -> tuple[int, str] | None:
    """Reserve once; commit before invoking financial code. Duplicates are never retried."""
    if not instance or not instance.strip() or len(instance) > 100:
        raise ValueError("invalid instance")
    if not message_id or not message_id.strip() or len(message_id) > 255:
        raise ValueError("invalid message id")
    owner = token_hex(16)
    event_id = db.execute(
        insert(EvolutionEvent)
        .values(instance=instance, message_id=message_id, owner=owner, status="processing")
        .on_conflict_do_nothing(index_elements=["instance", "message_id"])
        .returning(EvolutionEvent.id)
    ).scalar_one_or_none()
    return (event_id, owner) if event_id is not None else None


def finish_event(db: Session, event_id: int, owner: str, replies: list[dict]) -> bool:
    """Store ordered replies and completion in the same transaction."""
    row = db.execute(
        update(EvolutionEvent)
        .where(EvolutionEvent.id == event_id, EvolutionEvent.owner == owner, EvolutionEvent.status == "processing")
        .values(status="completed")
        .returning(EvolutionEvent.id)
    ).scalar_one_or_none()
    if row is None:
        return False
    for position, payload in enumerate(replies):
        db.add(EvolutionReply(event_id=event_id, position=position, payload=payload, status="pending"))
    return True


def mark_event_uncertain(db: Session, event_id: int, owner: str) -> bool:
    """An uncertain invocation requires manual reconciliation, never automatic retry."""
    return db.execute(
        update(EvolutionEvent)
        .where(EvolutionEvent.id == event_id, EvolutionEvent.owner == owner, EvolutionEvent.status == "processing")
        .values(status="uncertain")
        .returning(EvolutionEvent.id)
    ).scalar_one_or_none() is not None


def claim_reply(db: Session, reply_id: int) -> bool:
    """Mark a pending reply as sending before network I/O; commit before sending."""
    reply = aliased(EvolutionReply)
    earlier = select(reply.id).where(
        reply.event_id == EvolutionReply.event_id,
        reply.position < EvolutionReply.position,
        reply.status != "sent",
    ).exists()
    return db.execute(
        update(EvolutionReply)
        .where(EvolutionReply.id == reply_id, EvolutionReply.status == "pending", ~earlier)
        .values(status="sending")
        .returning(EvolutionReply.id)
    ).scalar_one_or_none() is not None


def finish_reply(db: Session, reply_id: int, *, delivered: bool) -> bool:
    """A failed or ambiguous send remains uncertain and is not retried automatically."""
    return db.execute(
        update(EvolutionReply)
        .where(EvolutionReply.id == reply_id, EvolutionReply.status == "sending")
        .values(status="sent" if delivered else "uncertain")
        .returning(EvolutionReply.id)
    ).scalar_one_or_none() is not None
