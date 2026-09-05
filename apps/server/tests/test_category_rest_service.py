"""Tests for web category REST helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.category import Category
from app.core.exceptions import ValidationError
from app.services.category_rest import (
    create_category_for_user,
    delete_category_for_user,
    list_categories_for_user,
)


def _result_one(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _result_many(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.anyio
async def test_create_category_for_web_user_creates_phone_profile_and_category():
    user = SimpleNamespace(
        id=10,
        phone_number="+5511999990001",
        full_name="Ana",
        email="ana@bagcoin.com",
    )
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result_one(None),
        _result_one(None),
        _result_one(None),
    ])
    db.add = MagicMock()

    response = await create_category_for_user(db, user, "Colecionáveis")

    assert response is not None
    assert response["name"] == "Colecionáveis"
    assert response["type"] == "despesa"
    assert db.add.call_count == 1


@pytest.mark.anyio
async def test_create_category_for_web_user_returns_none_for_duplicate():
    user = SimpleNamespace(id=10, phone_number="+5511999990001", full_name="Ana", email="ana")
    category = Category(id=20, user_id=10, name="Transporte", is_default=False)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result_many([category]),
    ])

    response = await create_category_for_user(db, user, "Transporte")

    assert response is None


@pytest.mark.anyio
async def test_list_categories_for_web_user_returns_authenticated_user_categories():
    user = SimpleNamespace(id=10, phone_number="+5511999990001", full_name="Ana", email="ana")
    categories = [
        Category(id=1, user_id=10, name="Alimentação", is_default=True),
        Category(id=2, user_id=10, name="Investimentos", is_default=False),
    ]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result_many(categories),
        _result_many(categories),
        _result_one(None),
        _result_one(None),
        _result_one(None),
        _result_one(None),
    ])
    db.add = MagicMock()

    response = await list_categories_for_user(db, user)

    assert [item["name"] for item in response] == ["Alimentação", "Investimentos"]
    assert response[1]["type"] == "investimento"
    assert response[0]["emoji"]
    assert response[0]["can_delete"] is False
    assert response[0]["is_user_created"] is False


@pytest.mark.anyio
async def test_delete_category_blocks_system_default():
    user = SimpleNamespace(id=10, phone_number="+5511999990001", full_name="Ana", email="ana")
    category = Category(id=1, user_id=10, name="Alimentação", is_default=True)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result_one(category),
    ])

    with pytest.raises(ValidationError):
        await delete_category_for_user(db, user, 1)
