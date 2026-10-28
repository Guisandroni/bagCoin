"""Timezone helpers for financial reports."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

REPORT_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def report_now(now: datetime | None = None) -> datetime:
    """Return a report timestamp in the product timezone."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(REPORT_TIMEZONE)
