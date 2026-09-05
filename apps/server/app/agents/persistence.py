"""Persistence agent — sync database operations for BagCoin agents.

Uses sync_session_maker for compatibility with non-async agent code.
"""

import contextlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func

from app.agents.tenant_context import assert_valid_tenant_phone
from app.core.financial_categories import (
    category_color,
    category_emoji,
    category_type,
    default_category_names,
    resolve_default_category_name,
)
from app.db.models.agent_log import AgentLog
from app.db.models.agent_memory_event import AgentMemoryEvent
from app.db.models.category import Category
from app.db.models.conversation_message import ConversationMessage
from app.db.models.phone_conversation import PhoneConversation
from app.db.models.transaction import Transaction, TransactionType
from app.db.models.user import User
from app.db.session import sync_session_maker
from app.services.agent_memory_service import add_conversation_message, add_memory_event

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = default_category_names()


def ensure_default_categories_sync(db, user: User) -> None:
    """Ensure every user has the shared default taxonomy."""
    existing = {
        category.name.casefold(): category
        for category in db.query(Category).filter(Category.user_id == user.id).all()
    }
    for name in DEFAULT_CATEGORIES:
        key = name.casefold()
        if key in existing:
            existing[key].is_default = True
            continue
        db.add(Category(user_id=user.id, name=name, is_default=True))
    db.flush()


def get_or_create_user_sync(phone_number: str) -> User:
    """Get or create a user by phone number (sync)."""
    assert_valid_tenant_phone(phone_number)
    db = sync_session_maker()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            user = User(
                phone_number=phone_number,
                preferences={"language": "pt-BR", "currency": "BRL"},
                financial_profile={},
            )
            db.add(user)
            db.flush()
            db.refresh(user)
            logger.info(f"New user created: {phone_number}")
        ensure_default_categories_sync(db, user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def get_or_create_user(phone_number: str, db=None) -> User:
    """Get or create a user, optionally with an existing session."""
    if db:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            assert_valid_tenant_phone(phone_number)
            user = User(
                phone_number=phone_number,
                preferences={"language": "pt-BR", "currency": "BRL"},
                financial_profile={},
            )
            db.add(user)
            db.flush()
            db.refresh(user)
            logger.info(f"New user created: {phone_number}")
        ensure_default_categories_sync(db, user)
        return user
    return get_or_create_user_sync(phone_number)


def save_transaction(state: dict[str, Any]) -> dict[str, Any]:
    """Persist extracted transaction to database."""
    db = sync_session_maker()
    try:
        phone_number = state.get("phone_number")
        extracted = state.get("extracted_data", {})

        if not extracted or extracted.get("amount") is None:
            state["error"] = "Não foi possível identificar o valor da transação."
            return state

        user = get_or_create_user(phone_number, db)
        state["user_id"] = user.id

        category_name = resolve_default_category_name(extracted.get("category", "Outros"))
        category = (
            db.query(Category)
            .filter(Category.user_id == user.id, Category.name.ilike(category_name))
            .first()
        )
        if not category:
            category = Category(
                user_id=user.id,
                name=category_name,
                is_default=(category_name in DEFAULT_CATEGORIES),
            )
            db.add(category)
            db.flush()
            db.refresh(category)

        tx_date = datetime.now(UTC)
        if extracted.get("date"):
            try:
                tx_date = datetime.strptime(extracted["date"], "%Y-%m-%d")
            except ValueError:
                with contextlib.suppress(ValueError):
                    tx_date = datetime.strptime(extracted["date"], "%d/%m/%Y")

        tx_type = TransactionType.EXPENSE
        type_str = extracted.get("type", "EXPENSE").upper()
        if type_str == TransactionType.INCOME.value:
            tx_type = TransactionType.INCOME
        elif type_str == TransactionType.TRANSFER.value:
            tx_type = TransactionType.TRANSFER

        if not state.get("skip_dedup", False):
            try:
                from app.services.deduplication_service import is_duplicate
                if is_duplicate(
                    phone_number,
                    float(extracted["amount"]),
                    extracted.get("description", ""),
                    category_name,
                ):
                    state["response"] = (
                        f"Já registrei uma despesa similar de R$ {extracted['amount']:.2f} "
                        f"há pouco. Foi duplicado? Se não, envie de novo confirmando."
                    )
                    return state
            except Exception as e:
                logger.warning(f"Dedup check failed (non-blocking): {e}")

        transaction = Transaction(
            user_id=user.id,
            type=tx_type.value,
            amount=extracted["amount"],
            currency=extracted.get("currency", "BRL"),
            category_id=category.id,
            description=extracted.get("description", ""),
            source_format=state.get("source_format", "text"),
            transaction_date=tx_date,
            confidence_score=extracted.get("confidence", 0.8),
            raw_input=extracted.get("raw_text", ""),
        )
        db.add(transaction)
        db.flush()
        db.refresh(transaction)

        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )
        if not conv:
            conv = PhoneConversation(user_id=user.id, channel="whatsapp")
            db.add(conv)

        conv.last_intent = state.get("intent", "unknown")
        from sqlalchemy.orm.attributes import flag_modified
        existing_context = dict(conv.context_json or {})
        existing_context.update({
            "last_transaction_id": transaction.id,
            "last_category": category_name,
            "last_amount": extracted["amount"],
        })
        conv.context_json = existing_context
        flag_modified(conv, "context_json")

        agent_log = AgentLog(
            user_id=user.id,
            agent_name="persistence",
            request_payload=extracted,
            response_payload={"transaction_id": transaction.id, "status": "saved"},
            status="success",
        )
        db.add(agent_log)
        add_memory_event(
            db,
            user_id=user.id,
            conversation_id=conv.id if conv else None,
            event_type="transaction_created",
            entity_type="transaction",
            entity_id=transaction.id,
            source=state.get("source_format", "text"),
            summary=(
                f"{tx_type.value} R$ {float(transaction.amount):.2f} "
                f"em {category_name}: {transaction.description or 'Sem descricao'}"
            ),
            payload={
                "transaction_id": transaction.id,
                "type": tx_type.value,
                "amount": float(transaction.amount),
                "category": category_name,
                "description": transaction.description,
                "source_format": transaction.source_format,
                "transaction_date": tx_date.isoformat(),
            },
        )
        db.commit()

        state["transaction_id"] = transaction.id
        state["category_name"] = category_name
        state["category_id"] = category.id
        state["transaction_date"] = tx_date

        if extracted.get("is_recurring"):
            try:
                from app.services.recurring_transactions_sync import create_recurring_transaction_sync
                recurring = create_recurring_transaction_sync(
                    db,
                    user_id=user.id,
                    type=tx_type.value,
                    amount=extracted["amount"],
                    category_id=category.id,
                    description=extracted.get("description", ""),
                    frequency=extracted.get("recurrence_frequency") or "monthly",
                    start_date=tx_date,
                )
                transaction.recurring_transaction_id = recurring.id
                db.commit()
                state["recurring_transaction_id"] = recurring.id
            except Exception as e:
                logger.warning(f"Could not create recurring rule (non-blocking): {e}")

        logger.info(f"Transaction {transaction.id} saved for user {user.id}")

        with contextlib.suppress(Exception):
            update_financial_profile_sync(phone_number)

        try:
            from app.services.pattern_learning_service import learn_from_transaction
            learn_from_transaction(
                phone_number, float(extracted["amount"]), category_name, extracted.get("description", "")
            )
        except Exception:
            pass

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving transaction: {e}")
        state["error"] = f"Erro ao salvar no banco: {e!s}"
    finally:
        db.close()

    return state


def get_user_transactions(phone_number: str, limit: int = 50) -> list:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        return (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def delete_transaction_by_id(phone_number: str, transaction_id: int) -> bool:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        tx = db.query(Transaction).filter(
            Transaction.id == transaction_id, Transaction.user_id == user.id
        ).first()
        if not tx:
            return False
        add_memory_event(
            db,
            user_id=user.id,
            event_type="transaction_deleted",
            entity_type="transaction",
            entity_id=tx.id,
            source="agent",
            summary=f"Transação removida: R$ {float(tx.amount):.2f} - {tx.description or 'Sem descricao'}",
            payload={"transaction_id": tx.id},
        )
        db.delete(tx)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting transaction: {e}")
        raise
    finally:
        db.close()


def update_transaction(
    phone_number: str,
    transaction_id: int,
    amount: float | None = None,
    description: str | None = None,
    category_name: str | None = None,
) -> dict | None:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        tx = db.query(Transaction).filter(
            Transaction.id == transaction_id, Transaction.user_id == user.id
        ).first()
        if not tx:
            return None
        if amount is not None:
            tx.amount = amount
        if description is not None:
            tx.description = description
        if category_name is not None:
            category_name = resolve_default_category_name(category_name)
            category = db.query(Category).filter(
                Category.user_id == user.id, Category.name == category_name
            ).first()
            if not category:
                category = Category(
                    user_id=user.id, name=category_name, is_default=(category_name in DEFAULT_CATEGORIES)
                )
                db.add(category)
                db.flush()
                db.refresh(category)
            tx.category_id = category.id
        add_memory_event(
            db,
            user_id=user.id,
            event_type="transaction_updated",
            entity_type="transaction",
            entity_id=tx.id,
            source="agent",
            summary=f"Transação atualizada: R$ {float(tx.amount):.2f} - {tx.description or 'Sem descricao'}",
            payload={
                "transaction_id": tx.id,
                "amount": float(tx.amount),
                "description": tx.description,
                "category": category_name,
            },
        )
        db.commit()
        db.refresh(tx)
        return {
            "id": tx.id,
            "amount": tx.amount,
            "description": tx.description,
            "category": category_name or (db.query(Category).get(tx.category_id).name if tx.category_id else None),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating transaction: {e}")
        raise
    finally:
        db.close()


def save_message_to_history(phone_number: str, role: str, content: str):
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )
        if not conv:
            conv = PhoneConversation(user_id=user.id, channel="whatsapp")
            db.add(conv)
            db.flush()
        from sqlalchemy.orm.attributes import flag_modified
        add_conversation_message(
            db,
            user_id=user.id,
            conversation_id=conv.id,
            channel=conv.channel,
            role=role,
            content=content,
            metadata={"source": "agent"},
        )
        history = list(conv.message_history or [])
        history.append({"role": role, "content": content, "timestamp": datetime.now(UTC).isoformat()})
        conv.message_history = history[-50:]
        flag_modified(conv, "message_history")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving message history: {e}")
    finally:
        db.close()


def get_conversation_history(phone_number: str, limit: int = 10) -> str:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        conv = (
            db.query(PhoneConversation)
            .filter(PhoneConversation.user_id == user.id)
            .order_by(PhoneConversation.updated_at.desc())
            .first()
        )
        messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.user_id == user.id)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(limit)
            .all()
        )
        if messages:
            recent = list(reversed(messages))
        elif conv and conv.message_history:
            recent = list(conv.message_history or [])[-limit:]
        else:
            return ""
        lines = []
        for msg in recent:
            if isinstance(msg, ConversationMessage):
                role = msg.role
                content = msg.content
            else:
                role = msg.get("role", "user")
                content = msg.get("content", "")
            label = "Usuário" if role == "user" else "BagCoin"
            lines.append(f"{label}: {content[:200]}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return ""
    finally:
        db.close()


def save_user_name(phone_number: str, name: str):
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        user.full_name = name
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving user name: {e}")
    finally:
        db.close()


def create_category(phone_number: str, name: str) -> dict | None:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        clean_name = resolve_default_category_name(name)
        existing = db.query(Category).filter(
            Category.user_id == user.id, Category.name.ilike(clean_name)
        ).first()
        if existing:
            return None
        if clean_name in DEFAULT_CATEGORIES:
            return None
        cat = Category(user_id=user.id, name=clean_name, is_default=False)
        db.add(cat)
        db.flush()
        add_memory_event(
            db,
            user_id=user.id,
            event_type="category_created",
            entity_type="category",
            entity_id=cat.id,
            source="agent",
            summary=f"Categoria criada: {cat.name}",
            payload={"category_id": cat.id, "name": cat.name},
        )
        db.commit()
        db.refresh(cat)
        return {"id": cat.id, "name": cat.name}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating category: {e}")
        raise
    finally:
        db.close()


def delete_category(phone_number: str, name: str) -> bool:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        cat = db.query(Category).filter(
            Category.user_id == user.id, Category.name.ilike(name)
        ).first()
        if not cat or cat.is_default:
            return False
        add_memory_event(
            db,
            user_id=user.id,
            event_type="category_deleted",
            entity_type="category",
            entity_id=cat.id,
            source="agent",
            summary=f"Categoria removida: {cat.name}",
            payload={"category_id": cat.id, "name": cat.name},
        )
        db.delete(cat)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting category: {e}")
        raise
    finally:
        db.close()


def rename_category(phone_number: str, old_name: str, new_name: str) -> bool:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        cat = db.query(Category).filter(
            Category.user_id == user.id, Category.name.ilike(old_name)
        ).first()
        if not cat or cat.is_default:
            return False
        clean_name = resolve_default_category_name(new_name)
        if clean_name in DEFAULT_CATEGORIES:
            return False
        existing = db.query(Category).filter(
            Category.user_id == user.id, Category.name.ilike(clean_name), Category.id != cat.id
        ).first()
        if existing:
            return False
        old_name_value = cat.name
        cat.name = clean_name
        add_memory_event(
            db,
            user_id=user.id,
            event_type="category_updated",
            entity_type="category",
            entity_id=cat.id,
            source="agent",
            summary=f"Categoria renomeada: {old_name_value} -> {clean_name}",
            payload={"category_id": cat.id, "old_name": old_name_value, "new_name": clean_name},
        )
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error renaming category: {e}")
        raise
    finally:
        db.close()


def list_categories(phone_number: str) -> list[dict]:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        cats = db.query(Category).filter(Category.user_id == user.id).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "is_default": c.is_default,
                "emoji": category_emoji(c.name),
                "color": category_color(c.name),
                "type": category_type(c.name),
                "is_user_created": not c.is_default,
                "can_delete": not c.is_default,
            }
            for c in sorted(cats, key=lambda x: (not x.is_default, x.name))
        ]
    finally:
        db.close()


def update_financial_profile_sync(phone_number: str) -> dict:
    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        ninety_days_ago = datetime.now(UTC) - timedelta(days=90)

        cat_totals = (
            db.query(
                Category.name,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user.id,
                Transaction.type == "EXPENSE",
                Transaction.transaction_date >= ninety_days_ago,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        totals = (
            db.query(
                func.coalesce(func.sum(Transaction.amount).filter(Transaction.type == "INCOME"), 0).label("income"),
                func.coalesce(func.sum(Transaction.amount).filter(Transaction.type == "EXPENSE"), 0).label("expense"),
            )
            .filter(Transaction.user_id == user.id, Transaction.transaction_date >= ninety_days_ago)
            .first()
        )

        total_income = float(totals.income) if totals else 0
        total_expense = float(totals.expense) if totals else 0

        profile = {
            "top_categories": [
                {"name": cat.name, "total": float(cat.total), "count": cat.count}
                for cat in cat_totals[:5]
            ],
            "total_income_90d": total_income,
            "total_expense_90d": total_expense,
            "savings_rate": round((total_income - total_expense) / total_income * 100, 1) if total_income > 0 else 0,
            "average_monthly_spending": round(total_expense / 3, 2),
            "transaction_count_90d": sum(cat.count for cat in cat_totals),
            "last_updated": datetime.now(UTC).isoformat(),
        }

        from sqlalchemy.orm.attributes import flag_modified
        user.financial_profile = profile
        flag_modified(user, "financial_profile")
        db.commit()

        logger.info(f"Financial profile updated for {phone_number}: {len(cat_totals)} categories")
        return profile

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating financial profile: {e}")
        return {}
    finally:
        db.close()
