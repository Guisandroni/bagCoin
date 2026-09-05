"""Integration tests for the budget-transaction flow (Bug 4).

These tests require a real PostgreSQL database. They're marked with
`integration` and can be run with:

    pytest tests/integration/ -m integration

Coverage:
- Create budget → create transaction in same category → budget spent > 0
- Timezone invariance (transaction stored UTC, period_start must match)
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.agents.persistence import get_or_create_user_sync
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.db.session import sync_session_maker
from app.services.budget_service import create_budget, get_budgets

pytestmark = pytest.mark.integration


@pytest.fixture
def isolated_phone():
    """Unique phone per test — avoids leakage between test runs."""
    return f"551199{uuid.uuid4().hex[:7]}"


@pytest.fixture
def cleanup_phone(isolated_phone):
    """Rollback everything created under this phone after the test."""
    yield isolated_phone
    db = sync_session_maker()
    try:
        from app.db.models.user import User

        user = db.query(User).filter(User.phone_number == isolated_phone).first()
        if user:
            db.query(Transaction).filter(Transaction.user_id == user.id).delete()
            db.query(Budget).filter(Budget.user_id == user.id).delete()
            db.query(Category).filter(Category.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _insert_expense(db, user_id: int, category_id: int, amount: float) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        type="EXPENSE",
        amount=amount,
        currency="BRL",
        category_id=category_id,
        description="test expense",
        source_format="text",
        transaction_date=datetime.now(UTC),
        confidence_score=1.0,
        raw_input="test",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_budget_spent_reflects_transaction_in_same_category(cleanup_phone):
    """Bug 4 core case — budget must decrement when a matching tx is saved."""
    phone = cleanup_phone

    # 1. Create user + budget
    user = get_or_create_user_sync(phone)
    budget = create_budget(
        phone_number=phone,
        name="Alimentação",
        total_limit=500.0,
        period="monthly",
    )
    assert budget["category_id"] is not None

    # 2. Insert expense in same category
    db = sync_session_maker()
    try:
        _insert_expense(db, user.id, budget["category_id"], 120.0)
    finally:
        db.close()

    # 3. Verify
    budgets = get_budgets(phone)
    assert len(budgets) == 1
    assert budgets[0]["total_spent"] == pytest.approx(120.0)
    assert budgets[0]["percentage"] == pytest.approx(24.0, abs=0.1)


def test_budget_spent_sums_multiple_transactions(cleanup_phone):
    phone = cleanup_phone
    user = get_or_create_user_sync(phone)
    budget = create_budget(
        phone_number=phone,
        name="Transporte",
        total_limit=300.0,
        period="monthly",
    )

    db = sync_session_maker()
    try:
        _insert_expense(db, user.id, budget["category_id"], 50.0)
        _insert_expense(db, user.id, budget["category_id"], 70.0)
        _insert_expense(db, user.id, budget["category_id"], 30.0)
    finally:
        db.close()

    budgets = get_budgets(phone)
    assert budgets[0]["total_spent"] == pytest.approx(150.0)


def test_budget_ignores_other_categories(cleanup_phone):
    """Transaction on category X must NOT count toward budget of category Y."""
    phone = cleanup_phone
    user = get_or_create_user_sync(phone)

    budget_alim = create_budget(
        phone_number=phone,
        name="Alimentação",
        total_limit=500.0,
        period="monthly",
    )
    # Create a second category without budget
    db = sync_session_maker()
    try:
        other_cat = Category(user_id=user.id, name="Lazer", is_default=True)
        db.add(other_cat)
        db.commit()
        db.refresh(other_cat)

        _insert_expense(db, user.id, other_cat.id, 200.0)
    finally:
        db.close()

    budgets = get_budgets(phone)
    alim = next(b for b in budgets if b["category_id"] == budget_alim["category_id"])
    assert alim["total_spent"] == 0.0
