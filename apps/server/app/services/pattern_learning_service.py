"""Pattern learning service — learns user habits from transaction patterns.

Stores learned preferences in User.preferences['learned_patterns'] JSON field.
"""

import logging
from collections import Counter
from datetime import datetime, UTC

from app.agents.persistence import get_user_transactions

logger = logging.getLogger(__name__)


def learn_from_transaction(
    phone_number: str,
    amount: float,
    category: str,
    description: str,
    current_hour: int | None = None,
):
    """Analyze recent transactions and update learned patterns.

    Called after each transaction save to build up user habit data:
    - Most used categories
    - Preferred spending hours
    - Common keywords in descriptions
    - Average transaction value
    """
    transactions = get_user_transactions(phone_number, limit=100)
    if not transactions:
        return

    cat_counter: Counter[str] = Counter()
    hour_counter: Counter[int] = Counter()
    keyword_counter: Counter[str] = Counter()
    total_amount = 0.0
    expense_count = 0

    for tx in transactions:
        tx_type = getattr(tx, "type", "")
        tx_amount = float(getattr(tx, "amount", 0) or 0)
        tx_cat = getattr(tx, "category_name", "") or "Outros"
        tx_desc = getattr(tx, "description", "") or ""

        cat_counter[tx_cat] += 1

        if tx_type == "EXPENSE":
            total_amount += tx_amount
            expense_count += 1

        tx_date = getattr(tx, "transaction_date", None)
        if tx_date and hasattr(tx_date, "hour"):
            hour_counter[tx_date.hour] += 1

        if tx_desc:
            words = [
                w for w in tx_desc.lower().split()
                if len(w) > 3 and w not in _STOP_WORDS
            ]
            keyword_counter.update(words)

    # Build patterns dict
    avg_ticket = round(total_amount / expense_count, 2) if expense_count > 0 else 0.0

    patterns = {
        "top_categories": [cat for cat, _ in cat_counter.most_common(5)],
        "preferred_hour": hour_counter.most_common(1)[0][0] if hour_counter else None,
        "preferred_period": _hour_to_period(
            hour_counter.most_common(1)[0][0]
        ) if hour_counter else None,
        "common_keywords": [kw for kw, _ in keyword_counter.most_common(10)],
        "total_transactions": len(transactions),
        "average_ticket": avg_ticket,
        "last_updated": datetime.now(UTC).isoformat(),
    }

    # Persist to User.preferences
    _save_patterns(phone_number, patterns)
    logger.info(
        f"Patterns learned for {phone_number}: "
        f"{len(patterns['top_categories'])} cats, "
        f"{len(patterns['common_keywords'])} keywords"
    )


_STOP_WORDS = {
    "com", "para", "que", "uma", "como", "mais", "mas",
    "por", "dos", "das", "aos", "nas", "nos", "são",
    "isso", "ela", "ele", "seu", "sua", "era", "vai",
}


def _hour_to_period(hour: int) -> str:
    if hour < 6:
        return "madrugada"
    elif hour < 12:
        return "manhã"
    elif hour < 18:
        return "tarde"
    return "noite"


def _save_patterns(phone_number: str, patterns: dict):
    """Persist learned patterns to User.preferences JSON field."""
    from sqlalchemy.orm.attributes import flag_modified

    from app.agents.persistence import get_or_create_user
    from app.db.session import sync_session_maker

    db = sync_session_maker()
    try:
        user = get_or_create_user(phone_number, db)
        prefs = dict(user.preferences or {})
        prefs["learned_patterns"] = patterns
        user.preferences = prefs
        flag_modified(user, "preferences")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving patterns for {phone_number}: {e}")
    finally:
        db.close()
