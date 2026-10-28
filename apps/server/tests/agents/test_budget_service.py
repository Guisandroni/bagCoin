"""Unit tests for app.services.budget_service.

Covers Bug 4: _period_start must be tz-aware (UTC) to match
TIMESTAMPTZ columns across any session timezone.
"""

from datetime import UTC, datetime

import pytest

from app.services.budget_service import _period_start


# =====================================================================
# Bug 4 — _period_start must be tz-aware UTC
# =====================================================================


def test_period_start_monthly_is_tz_aware_utc():
    result = _period_start("monthly")
    assert result is not None
    assert result.tzinfo is not None
    assert result.utcoffset() == UTC.utcoffset(None)
    now = datetime.now(UTC)
    assert result.day == 1
    assert result.hour == 0
    assert result.month == now.month
    assert result.year == now.year


def test_period_start_daily_is_today_midnight_utc():
    result = _period_start("daily")
    assert result is not None
    assert result.tzinfo is not None
    now = datetime.now(UTC)
    assert result.date() == now.date()
    assert result.hour == 0


def test_period_start_weekly_is_monday_midnight_utc():
    result = _period_start("weekly")
    assert result is not None
    assert result.tzinfo is not None
    assert result.weekday() == 0
    assert result.hour == 0


def test_period_start_yearly_is_jan1_utc():
    result = _period_start("yearly")
    assert result is not None
    assert result.tzinfo is not None
    now = datetime.now(UTC)
    assert result.month == 1
    assert result.day == 1
    assert result.year == now.year


def test_period_start_unknown_returns_none():
    assert _period_start("bogus") is None
    assert _period_start("") is None


@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "yearly"])
def test_period_start_never_naive(period):
    """Regression guard — naive datetimes collide with TIMESTAMPTZ in non-UTC sessions."""
    result = _period_start(period)
    assert result is not None
    assert result.tzinfo is not None, f"{period} returned naive datetime"
