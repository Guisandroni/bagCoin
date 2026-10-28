"""add_transaction_recurring_reference

Revision ID: 7e9c2a4b8f11
Revises: 4f1a2b3c5d6e
Create Date: 2026-05-09 22:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7e9c2a4b8f11"
down_revision: Union[str, None] = "4f1a2b3c5d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("recurring_transaction_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "transactions_recurring_transaction_id_fkey",
        "transactions",
        "recurring_transactions",
        ["recurring_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("transactions_recurring_transaction_id_idx"),
        "transactions",
        ["recurring_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("transactions_recurring_transaction_id_idx"), table_name="transactions")
    op.drop_constraint("transactions_recurring_transaction_id_fkey", "transactions", type_="foreignkey")
    op.drop_column("transactions", "recurring_transaction_id")
