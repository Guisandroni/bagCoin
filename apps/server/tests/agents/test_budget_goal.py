"""Unit tests for deadline guards in app.agents.budget_goal.

Covers Bug 5: goal deadline must never be in the past.
"""

from datetime import date

import pytest

from app.agents.budget_goal import _future_deadline


# =====================================================================
# _future_deadline: never returns a date <= today
# =====================================================================


def test_future_deadline_accepts_mm_yyyy_in_future():
    """'10/2027' in any future year stays as-is."""
    result = _future_deadline("10/2027")
    assert result is not None
    assert result >= date.today()
    assert result.month == 10
    assert result.year == 2027


def test_future_deadline_bumps_past_year():
    """'10/1990' must bump to next year."""
    result = _future_deadline("10/1990")
    assert result is not None
    assert result > date.today()


def test_future_deadline_accepts_dd_mm_yyyy():
    """'15/06/2030' → parsed correctly."""
    result = _future_deadline("15/06/2030")
    assert result is not None
    assert result.day == 15
    assert result.month == 6
    assert result.year == 2030


def test_future_deadline_returns_none_for_junk():
    assert _future_deadline("") is None
    assert _future_deadline(None) is None
    assert _future_deadline("banana") is None


def test_future_deadline_idempotent():
    """Calling twice doesn't double-bump."""
    first = _future_deadline("10/1990")
    second = _future_deadline(first.strftime("%m/%Y"))
    # Difference should be at most 1 year (not 2)
    assert second is not None
    assert (second.year - first.year) <= 1


@pytest.mark.parametrize(
    "raw",
    [
        "01/2000",
        "06/1999",
        "12/2010",
    ],
)
def test_past_dates_always_bumped(raw):
    result = _future_deadline(raw)
    assert result is not None
    assert result > date.today()
