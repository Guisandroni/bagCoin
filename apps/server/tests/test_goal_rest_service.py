"""Tests for goal REST service normalization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.enums import GoalStatus
from app.schemas.goal import GoalUpdate
from app.services import goal_rest


def test_goal_response_serializes_status_enum_value():
    goal = SimpleNamespace(
        id=1,
        title="Notebook",
        target_amount=5000.0,
        current_amount=1000.0,
        deadline=None,
        status=GoalStatus.COMPLETED,
        created_at=None,
        updated_at=None,
    )

    response = goal_rest._goal_response(goal)

    assert response["status"] == "completed"


@pytest.mark.anyio
async def test_update_goal_persists_status_as_string(monkeypatch):
    goal = SimpleNamespace(
        id=1,
        user_id=10,
        title="Notebook",
        target_amount=5000.0,
        current_amount=1000.0,
        deadline=None,
        status="active",
        created_at=None,
        updated_at=None,
    )
    captured: dict = {}

    async def fake_update_goal(_db, *, db_goal, update_data):
        captured.update(update_data)
        for field, value in update_data.items():
            setattr(db_goal, field, value)
        return db_goal

    monkeypatch.setattr(goal_rest.goal_repo, "get_goal_by_id", AsyncMock(return_value=goal))
    monkeypatch.setattr(goal_rest.goal_repo, "update_goal", fake_update_goal)
    monkeypatch.setattr(goal_rest, "add_memory_event_async", AsyncMock())

    response = await goal_rest.update_goal(
        db=object(),
        goal_id=1,
        user_id=10,
        data=GoalUpdate(status=GoalStatus.CANCELLED),
    )

    assert captured["status"] == "cancelled"
    assert response["status"] == "cancelled"
