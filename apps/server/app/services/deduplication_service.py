"""Deduplication service — fuzzy matching to prevent duplicate transactions."""

import logging
from datetime import datetime, UTC, timedelta
from difflib import SequenceMatcher

from app.agents.persistence import get_user_transactions

logger = logging.getLogger(__name__)

# Similarity threshold (0.0 to 1.0) — 85% is conservative
SIMILARITY_THRESHOLD = 0.85
# Time window in minutes for recent duplicates
TIME_WINDOW_MINUTES = 5


def is_duplicate(
    phone_number: str,
    amount: float,
    description: str,
    category: str = "",
) -> bool:
    """Check if a similar transaction exists within the time window.

    Returns True if a likely duplicate is found (same amount + similar
    description within the last N minutes).
    """
    recent = get_user_transactions(phone_number, limit=20)
    cutoff = datetime.now(UTC) - timedelta(minutes=TIME_WINDOW_MINUTES)

    for tx in recent:
        # Must be same amount (within R$ 0.01 tolerance)
        if abs(float(tx.amount) - float(amount)) > 0.01:
            continue

        # Must be within time window
        tx_date = tx.transaction_date
        if tx_date and isinstance(tx_date, datetime):
            if tx_date.tzinfo is None:
                tx_date = tx_date.replace(tzinfo=UTC)
            else:
                tx_date = tx_date.astimezone(UTC)
            if tx_date < cutoff:
                continue
        elif tx_date:
            # Could be a date object without time — skip time check
            pass

        # Description must be similar (fuzzy match)
        tx_desc = tx.description or ""
        if description and tx_desc:
            ratio = SequenceMatcher(
                None,
                description.lower().strip(),
                tx_desc.lower().strip(),
            ).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                logger.info(
                    f"Duplicate detected for {phone_number}: "
                    f"'{description}' ~= '{tx_desc}' (ratio={ratio:.2f})"
                )
                return True

    return False
