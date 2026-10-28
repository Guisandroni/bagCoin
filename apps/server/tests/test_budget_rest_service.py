"""Tests for web budget REST service calculations."""

from types import SimpleNamespace

import pytest

from app.services.budget_rest import _budget_progress_payload


def _budget(total_limit: float):
    return SimpleNamespace(total_limit=total_limit)


def test_budget_progress_uses_absolute_spent_for_legacy_negative_expenses():
    progress = _budget_progress_payload(_budget(600), -404.1)

    assert progress["total_spent"] == 404.1
    assert progress["total_remaining"] == pytest.approx(195.9)
    assert progress["percentage"] == 67.3


def test_budget_progress_allows_over_budget_percentage():
    progress = _budget_progress_payload(_budget(500), 650)

    assert progress["total_spent"] == 650
    assert progress["total_remaining"] == -150
    assert progress["percentage"] == 130


def test_budget_progress_handles_zero_spend():
    progress = _budget_progress_payload(_budget(500), 0)

    assert progress["total_spent"] == 0
    assert progress["total_remaining"] == 500
    assert progress["percentage"] == 0
