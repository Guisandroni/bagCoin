"""Tests for persistent agent memory and context helpers."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.agent_log import AgentLog
from app.db.models.agent_memory_event import AgentMemoryEvent
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.conversation_message import ConversationMessage
from app.db.models.goal import Goal
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.transaction import Transaction
from app.db.models.user import User


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            PhoneConversation.__table__,
            ConversationMessage.__table__,
            AgentMemoryEvent.__table__,
            AgentLog.__table__,
            Category.__table__,
            Transaction.__table__,
            Budget.__table__,
            Goal.__table__,
        ],
    )
    return sessionmaker(bind=engine)


def _patch_memory_db(monkeypatch):
    factory = _session_factory()
    import app.agents.persistence as persistence
    import app.services.agent_memory_service as memory_service

    monkeypatch.setattr(persistence, "sync_session_maker", factory)
    monkeypatch.setattr(memory_service, "sync_session_maker", factory)
    return factory


def test_conversation_messages_are_persisted_without_50_message_limit(monkeypatch):
    factory = _patch_memory_db(monkeypatch)
    from app.agents.persistence import get_conversation_history, save_message_to_history

    for index in range(60):
        save_message_to_history("5511999999999", "user", f"mensagem {index}")

    with factory() as db:
        assert db.query(ConversationMessage).count() == 60
        conv = db.query(PhoneConversation).one()
        assert len(conv.message_history) == 50

    history = get_conversation_history("5511999999999", limit=3)

    assert "mensagem 57" in history
    assert "mensagem 59" in history
    assert "mensagem 0" not in history


def test_save_transaction_records_memory_event(monkeypatch):
    factory = _patch_memory_db(monkeypatch)
    monkeypatch.setattr("app.services.deduplication_service.is_duplicate", lambda *_, **__: False)
    monkeypatch.setattr("app.services.pattern_learning_service.learn_from_transaction", lambda *_, **__: None)
    from app.agents.persistence import save_transaction

    result = save_transaction({
        "phone_number": "5511999999999",
        "source_format": "image",
        "extracted_data": {
            "type": "EXPENSE",
            "amount": 139.84,
            "category": "Supermercado",
            "description": "Nota fiscal Sao Roque",
            "date": "2026-05-24",
        },
    })
    assert not result.get("error")

    with factory() as db:
        event = db.query(AgentMemoryEvent).filter_by(event_type="transaction_created").one()
        assert event.source == "image"
        assert event.entity_type == "transaction"
        assert event.payload["amount"] == 139.84


def test_agent_context_includes_messages_events_and_financial_snapshot(monkeypatch):
    factory = _patch_memory_db(monkeypatch)
    from app.agents.persistence import get_or_create_user, save_message_to_history
    from app.services.agent_memory_service import add_memory_event, build_agent_context_text

    save_message_to_history("5511999999999", "user", "criei uma compra no mercado")
    with factory() as db:
        user = get_or_create_user("5511999999999", db)
        category = Category(user_id=user.id, name="Supermercado", is_default=True)
        db.add(category)
        db.flush()
        tx = Transaction(
            user_id=user.id,
            type="EXPENSE",
            amount=120,
            category_id=category.id,
            description="Mercado",
            source_format="text",
            transaction_date=datetime.now(UTC),
        )
        budget = Budget(
            user_id=user.id,
            category_id=category.id,
            name="Supermercado",
            period="monthly",
            total_limit=500,
        )
        goal = Goal(user_id=user.id, title="Viagem", target_amount=1000, current_amount=100)
        db.add_all([tx, budget, goal])
        db.flush()
        add_memory_event(
            db,
            user_id=user.id,
            event_type="document_import_processed",
            entity_type="document",
            summary="Documento importado com 1 transação.",
        )
        db.commit()

    context = build_agent_context_text("5511999999999")

    assert "Últimas mensagens" in context
    assert "Eventos financeiros recentes" in context
    assert "Últimas transações" in context
    assert "Orçamentos recentes" in context
    assert "Metas recentes" in context
