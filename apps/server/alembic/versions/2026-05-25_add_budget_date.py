"""add_budget_date

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-25 07:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("budget_date", sa.Date(), nullable=True, server_default=sa.text("CURRENT_DATE")),
    )
    op.execute("UPDATE budgets SET budget_date = COALESCE(created_at::date, CURRENT_DATE) WHERE budget_date IS NULL")
    op.alter_column("budgets", "budget_date", nullable=False)


def downgrade() -> None:
    op.drop_column("budgets", "budget_date")
