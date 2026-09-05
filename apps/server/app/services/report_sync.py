"""Sync helpers for Report model — for use inside agent nodes."""

from datetime import datetime

from app.db.models.report import Report


def create_report_sync(
    db,
    *,
    user_id: int,
    period_start: datetime,
    period_end: datetime,
    file_url: str | None,
) -> Report:
    """Create a Report row (sync, for agent nodes)."""
    report = Report(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        file_url=file_url,
    )
    db.add(report)
    db.flush()
    db.refresh(report)
    return report


def get_report_sync(db, report_id: int) -> Report | None:
    """Get a Report by id (sync)."""
    return db.query(Report).filter(Report.id == report_id).first()
