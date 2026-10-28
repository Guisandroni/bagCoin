"""Report repository (PostgreSQL async)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report


async def get_report_by_id(db: AsyncSession, report_id: int) -> Report | None:
    return await db.get(Report, report_id)


async def get_reports_by_user(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Report]:
    query = (
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_reports(db: AsyncSession, user_id: int) -> int:
    query = select(func.count(Report.id)).where(Report.user_id == user_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_report(
    db: AsyncSession,
    *,
    user_id: int,
    period_start,
    period_end,
    file_url: str | None = None,
) -> Report:
    report = Report(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        file_url=file_url,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def delete_report(db: AsyncSession, report_id: int) -> bool:
    report = await get_report_by_id(db, report_id)
    if report:
        await db.delete(report)
        await db.flush()
        return True
    return False
