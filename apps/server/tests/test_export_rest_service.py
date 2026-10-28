"""Tests for consolidated financial CSV export."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import export_rest


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def scalars(self):
        return _ScalarResult(self._rows)

    def scalar(self):
        return self._scalar_value


@pytest.mark.anyio
async def test_export_financial_csv_for_user_includes_all_ptbr_sections():
    tx_income = SimpleNamespace(
        id=1,
        type="INCOME",
        amount=1200,
        description="Freela",
        category=SimpleNamespace(name="Salário"),
        recurring_transaction_id=None,
        recurring_transaction=None,
        transaction_date=datetime(2026, 5, 12, tzinfo=UTC),
        source_format="manual",
        confidence_score=1.0,
    )
    tx_expense = SimpleNamespace(
        id=2,
        type="EXPENSE",
        amount=-250.5,
        description="Mercado",
        category=SimpleNamespace(name="Mercado"),
        recurring_transaction_id=10,
        recurring_transaction=SimpleNamespace(frequency="monthly"),
        transaction_date=datetime(2026, 5, 13, tzinfo=UTC),
        source_format="image",
        confidence_score=0.6,
    )
    goal = SimpleNamespace(
        id=3,
        title="Notebook",
        current_amount=1000,
        target_amount=5000,
        deadline=datetime(2026, 10, 31, tzinfo=UTC),
        status="completed",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=None,
    )
    budget = SimpleNamespace(
        id=4,
        name="Mercado mensal",
        category=SimpleNamespace(name="Mercado"),
        category_id=8,
        user_id=1,
        total_limit=900,
        period="monthly",
        budget_type="category",
        budget_date=date(2026, 5, 1),
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    execute_results = [
        _ExecuteResult([tx_income, tx_expense]),
        _ExecuteResult([goal]),
        _ExecuteResult([budget]),
        _ExecuteResult(scalar_value=250.5),
    ]
    db = SimpleNamespace(execute=AsyncMock(side_effect=execute_results))

    csv_content = await export_rest.export_financial_csv_for_user(db, user_id=1)

    assert "seção,data,nome,descrição,categoria,tipo,valor" in csv_content
    assert "seção,id," not in csv_content
    assert "Transações,1," not in csv_content
    assert "Metas,3," not in csv_content
    assert "Orçamentos,4," not in csv_content
    assert "Transações,12/05/2026,Freela,Freela,Salário,receita,\"1200,00\",confirmada,manual" in csv_content
    assert "Transações,13/05/2026,Mercado,Mercado,Mercado,despesa,\"250,50\",pendente,imagem,sim,mensal" in csv_content
    assert "Metas,31/10/2026,Notebook,,,,,concluída" in csv_content
    assert "Orçamentos,01/05/2026,Mercado mensal,,Mercado,orçamento" in csv_content
    assert "Categorias mais utilizadas" in csv_content
    assert "Mercado" in csv_content
    assert "\"250,50\"" in csv_content
    assert "Salário" in csv_content
    assert "\"1200,00\"" in csv_content
