"""Shared deadline parsing for Meta-related tests and migrations."""

import re
from datetime import date


def _future_deadline(deadline_raw: str | None) -> date | None:
    """Parse a deadline and guarantee it is in the future.

    Accepts ``MM/YYYY`` or ``DD/MM/YYYY``. Past dates advance by whole years.
    """
    if not deadline_raw:
        return None

    parsed: date | None = None
    day_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(deadline_raw))
    if day_match:
        try:
            parsed = date(int(day_match.group(3)), int(day_match.group(2)), int(day_match.group(1)))
        except ValueError:
            parsed = None

    if not parsed:
        month_match = re.search(r"(\d{1,2})/(\d{4})", str(deadline_raw))
        if month_match:
            try:
                parsed = date(int(month_match.group(2)), int(month_match.group(1)), 1)
            except ValueError:
                parsed = None

    if not parsed:
        return None

    while parsed <= date.today():
        try:
            parsed = parsed.replace(year=parsed.year + 1)
        except ValueError:
            parsed = parsed.replace(year=parsed.year + 1, day=28)
    return parsed
