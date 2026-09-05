"""Tests for transaction REST endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

ServiceMock = AsyncMock

from app.api.deps import get_current_user, get_db_session, get_redis
from app.core.config import settings
from app.main import app


class MockTransaction:
    """Mock transaction for testing."""

    def __init__(self, tx_id=1, user_id=None):
        self.id = tx_id
        self.user_id = user_id or 1
        self.user_id = None
        self.type = "EXPENSE"
        self.amount = 100.0
        self.currency = "BRL"
        self.category_id = None
        self.description = "Test transaction"
        self.source_format = "manual"
        self.transaction_date = datetime(2026, 5, 1, tzinfo=UTC)
        self.confidence_score = 1.0
        self.raw_input = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


class MockUser:
    """Mock authenticated user."""

    def __init__(self):
        self.id = 1
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.role = "user"
        self.phone_number = None
        self.google_id = None
        self.auth_provider = "email"
        self.avatar_url = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def mock_tx():
    return MockTransaction()


@pytest.fixture
async def client_with_auth(mock_user, mock_redis, mock_db_session):
    """Client with authenticated user override."""

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_transactions_empty(client_with_auth, mock_db_session):
    """Test listing transactions when empty."""
    from unittest.mock import AsyncMock, MagicMock

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])
    mock_db_session.scalar = AsyncMock(return_value=0)

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_list_transactions_requires_auth(client):
    """Test that unauthenticated requests are rejected."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/transactions")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_summary_requires_auth(client):
    """Test that summary requires auth."""
    response = await client.get(f"{settings.API_V1_STR}/bagcoin/transactions/summary")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_transaction_requires_auth(client):
    """Test that creating transaction requires auth."""
    response = await client.post(
        f"{settings.API_V1_STR}/bagcoin/transactions",
        json={
            "type": "EXPENSE",
            "amount": 50.0,
            "description": "Test",
        },
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_transaction_requires_auth(client):
    """Test that deleting transaction requires auth."""
    response = await client.delete(f"{settings.API_V1_STR}/bagcoin/transactions/1")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_google_login_endpoint_exists(client_with_auth):
    """Test that the Google login endpoint is registered."""
    mock_user_service = MagicMock()
    mock_user_service.google_auth = AsyncMock(
        return_value=mock_user_service.google_auth
    )

    from app.api.deps import get_user_service

    mock_user = MockUser()
    mock_user_service.google_auth = AsyncMock(return_value=mock_user)

    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/auth/google",
        json={"id_token": "valid-token"},
    )
    # The override for get_current_user is still active, but the endpoint
    # uses UserSvc which is now overridden
    assert response.status_code == 200


@pytest.mark.anyio
async def test_register_with_phone_field(client_with_auth):
    """Test that register accepts phone_number field."""
    mock_user_service = MagicMock()
    mock_user = MockUser()
    mock_user_service.register = AsyncMock(return_value=mock_user)

    from app.api.deps import get_user_service

    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "new@test.com",
            "password": "password123",
            "full_name": "New User",
            "phone_number": "+5511999999999",
        },
    )
    assert response.status_code == 201


# ==============================================================================
# List transactions
# ==============================================================================


def _mock_tx_rest_response(**kwargs) -> dict:
    """Return a mock transaction response dict matching TransactionRestResponse."""
    from datetime import UTC, datetime

    return {
        "id": kwargs.get("id", "1"),
        "type": kwargs.get("type", "EXPENSE"),
        "name": kwargs.get("name", "Test transaction"),
        "category": kwargs.get("category", "Test transaction"),
        "category_name": kwargs.get("category_name", kwargs.get("category", "Test transaction")),
        "amount": abs(kwargs.get("amount", 100.0)),
        "date": kwargs.get("date", "01 Mai"),
        "source": kwargs.get("source", "manual"),
        "status": kwargs.get("status", "confirmed"),
        "created_at": kwargs.get("created_at", datetime.now(UTC)).isoformat(),
        "updated_at": kwargs.get("updated_at", datetime.now(UTC)).isoformat(),
    }


@pytest.mark.anyio
async def test_list_transactions_with_data(client_with_auth):
    """Test listing transactions with data returns paginated response."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.list_for_user.return_value = {
        "items": [
            _mock_tx_rest_response(id="1", name="Supermercado", amount=-287.5, date="30 Abr"),
            _mock_tx_rest_response(id="2", name="Salário", amount=8500.0, date="28 Abr", source="auto"),
        ],
        "total": 2,
    }

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Supermercado"
    assert data["items"][0]["amount"] == 287.5
    assert data["items"][1]["name"] == "Salário"
    assert data["items"][1]["amount"] == 8500.0


@pytest.mark.anyio
async def test_list_transactions_filter_by_type(client_with_auth):
    """Test filtering transactions by type (EXPENSE/INCOME)."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.list_for_user.return_value = {"items": [], "total": 0}

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/transactions?type=EXPENSE"
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    # Verify the service was called with type_filter="EXPENSE"
    call_kwargs = mock_service.list_for_user.call_args.kwargs
    assert call_kwargs.get("type_filter") == "EXPENSE" or "EXPENSE" in str(mock_service.list_for_user.call_args)


@pytest.mark.anyio
async def test_list_transactions_search(client_with_auth):
    """Test searching transactions by description."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.list_for_user.return_value = {
        "items": [_mock_tx_rest_response(id="1", name="Mercado", amount=-200.0)],
        "total": 1,
    }

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/transactions?search=mercado"
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)


@pytest.mark.anyio
async def test_export_transactions_csv(client_with_auth):
    """Test CSV export endpoint for authenticated user."""
    from app.api.routes.v1.transactions import get_transaction_rest_service

    mock_service = AsyncMock()
    mock_service.export_csv_for_user.return_value = (
        "id,tipo,descricao,categoria,valor,data,origem,status,recorrente,frequencia_recorrencia\n"
        "1,INCOME,Freela,Salário,1200.00,2026-05-12,manual,confirmed,false,\n"
    )
    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions/export.csv")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"bagcoin-transacoes.csv\"" == response.headers.get("content-disposition")
    assert "Freela" in response.text


@pytest.mark.anyio
async def test_export_financial_csv_consolidated_endpoint(client_with_auth):
    """Test consolidated financial CSV endpoint for authenticated user."""
    from unittest.mock import patch

    csv_content = (
        "seção,id,data,nome,descrição,categoria,tipo,valor,status,origem,recorrente,frequência,"
        "valor atual,valor alvo,limite,gasto,restante,período,quantidade de transações,"
        "valor total de despesas,valor total de receitas,saldo da categoria\n"
        "Transações,1,12/05/2026,Freela,Freela,Salário,receita,\"1200,00\",confirmada,manual,não,,,,,,,,,,,\n"
        "Metas,2,31/10/2026,Notebook,,,,,ativa,,,,\"1000,00\",\"5000,00\",,,,,,,\n"
        "Orçamentos,3,01/05/2026,Mercado,,Mercado,orçamento,,,,,,,,\"900,00\",\"250,00\",\"650,00\",mensal,,,,\n"
        "Categorias mais utilizadas,,,Mercado,,Mercado,,,,,,,,,,,,,1,\"250,00\",\"0,00\",\"'-250,00\"\n"
    )

    with patch(
        "app.api.routes.v1.exports.export_financial_csv_for_user",
        new_callable=AsyncMock,
    ) as mock_export:
        mock_export.return_value = csv_content

        response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers.get("content-disposition") == 'attachment; filename="bagcoin-financeiro.csv"'
    assert "Transações" in response.text
    assert "Metas" in response.text
    assert "Orçamentos" in response.text
    assert "Categorias mais utilizadas" in response.text


@pytest.mark.anyio
async def test_list_transactions_pagination(client_with_auth):
    """Test pagination parameters are passed to the service."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.list_for_user.return_value = {"items": [], "total": 0}

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/bagcoin/transactions?skip=5&limit=10"
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    assert mock_service.list_for_user.call_count == 1
    _, kwargs = mock_service.list_for_user.call_args
    assert kwargs.get("skip") == 5
    assert kwargs.get("limit") == 10


# ==============================================================================
# Create transaction
# ==============================================================================


@pytest.mark.anyio
async def test_create_transaction_expense(client_with_auth):
    """Test creating an expense transaction returns 201."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.create_for_user.return_value = _mock_tx_rest_response(
        id="10", name="Supermercado", amount=-150.0, date="01 Mai"
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/transactions",
        json={
            "type": "EXPENSE",
            "amount": 150.0,
            "description": "Supermercado",
            "source": "manual",
            "status": "confirmed",
        },
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Supermercado"
    assert data["amount"] == 150.0


@pytest.mark.anyio
async def test_create_transaction_income(client_with_auth):
    """Test creating an income transaction returns 201."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.create_for_user.return_value = _mock_tx_rest_response(
        id="11", name="Salário", amount=8500.0, date="01 Mai"
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/transactions",
        json={
            "type": "INCOME",
            "amount": 8500.0,
            "description": "Salário",
            "source": "manual",
            "status": "confirmed",
        },
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "11"


@pytest.mark.anyio
async def test_create_transaction_invalid_data(client_with_auth):
    """Test creating a transaction with invalid data returns 422."""
    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/transactions",
        json={
            "type": "INVALID",
            "amount": -50,
            "description": "",
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_transaction_extra_fields_ignored(client_with_auth):
    """Test that extra fields in request body are ignored."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.create_for_user.return_value = _mock_tx_rest_response(
        id="12", name="Test", amount=-50.0
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/bagcoin/transactions",
        json={
            "type": "EXPENSE",
            "amount": 50.0,
            "description": "Test",
            "extra_field": "should be ignored",
            "source": "manual",
            "status": "confirmed",
        },
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 201


# ==============================================================================
# Get transaction
# ==============================================================================


@pytest.mark.anyio
async def test_get_transaction(client_with_auth, mock_user):
    """Test getting a specific transaction returns it."""
    from app.services.transaction_rest import _to_frontend_response
    from datetime import UTC, datetime

    # Create a mock transaction that _to_frontend_response can process
    mock_tx = MockTransaction(tx_id=5, user_id=mock_user.id)
    mock_tx.description = "Supermercado Pão de Açúcar"
    mock_tx.amount = 287.50
    mock_tx.type = "EXPENSE"
    mock_tx.source_format = "manual"
    mock_tx.confidence_score = 1.0
    mock_tx.transaction_date = datetime(2026, 4, 30, tzinfo=UTC)

    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.get_for_user.return_value = mock_tx

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions/5")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Supermercado Pão de Açúcar"
    assert data["amount"] == 287.5
    assert data["status"] == "confirmed"


@pytest.mark.anyio
async def test_get_transaction_not_found(client_with_auth):
    """Test getting a non-existent transaction returns 404."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from app.core.exceptions import NotFoundError
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.get_for_user.side_effect = NotFoundError(
        message="Transaction not found", details={"id": 999}
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions/999")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 404


# ==============================================================================
# Update transaction
# ==============================================================================


@pytest.mark.anyio
async def test_update_transaction(client_with_auth):
    """Test updating a transaction returns the updated data."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.update_for_user.return_value = _mock_tx_rest_response(
        id="3", name="Updated description", amount=-200.0
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/transactions/3",
        json={
            "description": "Updated description",
            "amount": 200.0,
        },
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated description"


@pytest.mark.anyio
async def test_update_transaction_not_found(client_with_auth):
    """Test updating a non-existent transaction returns 404."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from app.core.exceptions import NotFoundError
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.update_for_user.side_effect = NotFoundError(
        message="Transaction not found", details={"id": 999}
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/transactions/999",
        json={"description": "Updated"},
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_transaction_empty_body(client_with_auth):
    """Test updating with empty body is valid (all fields optional)."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.update_for_user.return_value = _mock_tx_rest_response(id="3", name="No changes")

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.patch(
        f"{settings.API_V1_STR}/bagcoin/transactions/3",
        json={},
    )

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200


# ==============================================================================
# Delete transaction
# ==============================================================================


@pytest.mark.anyio
async def test_delete_transaction(client_with_auth):
    """Test deleting a transaction returns 204."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.delete_for_user.return_value = None

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.delete(f"{settings.API_V1_STR}/bagcoin/transactions/7")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_transaction_not_found(client_with_auth):
    """Test deleting a non-existent transaction returns 404."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from app.core.exceptions import NotFoundError
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.delete_for_user.side_effect = NotFoundError(
        message="Transaction not found", details={"id": 999}
    )

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.delete(f"{settings.API_V1_STR}/bagcoin/transactions/999")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 404


# ==============================================================================
# Summary
# ==============================================================================


@pytest.mark.anyio
async def test_get_summary(client_with_auth):
    """Test getting transaction summary for dashboard."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.get_summary.return_value = {
        "balance": 3220.0,
        "total_income": 8500.0,
        "total_expenses": 5280.0,
        "transaction_count": 12,
        "categories": [
            {"name": "Alimentação", "amount": 1150.0, "color": "#ff6b35"},
            {"name": "Transporte", "amount": 380.0, "color": "#0052ff"},
        ],
        "recent_transactions": [
            _mock_tx_rest_response(id="1", name="Supermercado", amount=287.5, type="EXPENSE"),
            _mock_tx_rest_response(id="2", name="Salário", amount=8500.0, type="INCOME"),
        ],
    }

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions/summary")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 3220.0
    assert data["total_income"] == 8500.0
    assert data["total_expenses"] == 5280.0
    assert data["transaction_count"] == 12
    assert len(data["categories"]) == 2
    assert len(data["recent_transactions"]) == 2


@pytest.mark.anyio
async def test_get_summary_empty(client_with_auth):
    """Test getting summary when user has no transactions."""
    from app.api.routes.v1.transactions import get_transaction_rest_service
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.get_summary.return_value = {
        "balance": 0.0,
        "total_income": 0.0,
        "total_expenses": 0.0,
        "transaction_count": 0,
        "categories": [],
        "recent_transactions": [],
    }

    app.dependency_overrides[get_transaction_rest_service] = lambda: mock_service

    response = await client_with_auth.get(f"{settings.API_V1_STR}/bagcoin/transactions/summary")

    app.dependency_overrides.pop(get_transaction_rest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 0.0
    assert data["transaction_count"] == 0
    assert data["categories"] == []
    assert data["recent_transactions"] == []
