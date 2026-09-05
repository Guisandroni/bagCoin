"""Commands for recurring transactions."""

import asyncio

from app.commands import command, info, success


@command("materialize-recurring-transactions", help="Create due recurring transactions")
def materialize_recurring_transactions() -> None:
    """Create transactions for all due recurring rules."""

    async def _run() -> None:
        from app.db.session import get_db_context
        from app.services.recurring_transactions import materialize_due_recurring_transactions

        async with get_db_context() as db:
            created = await materialize_due_recurring_transactions(db)
            await db.commit()
            info(f"Created {created} recurring transaction(s).")

    asyncio.run(_run())
    success("Recurring transactions materialized.")
