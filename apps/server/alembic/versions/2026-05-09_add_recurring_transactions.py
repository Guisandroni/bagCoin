"""add_recurring_transactions

Revision ID: 4f1a2b3c5d6e
Revises: 020638762158
Create Date: 2026-05-09 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4f1a2b3c5d6e"
down_revision: Union[str, None] = "020638762158"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_uuid"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("recurring_transactions_category_id_idx"), "recurring_transactions", ["category_id"], unique=False)
    op.create_index(op.f("recurring_transactions_user_uuid_idx"), "recurring_transactions", ["user_uuid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("recurring_transactions_user_uuid_idx"), table_name="recurring_transactions")
    op.drop_index(op.f("recurring_transactions_category_id_idx"), table_name="recurring_transactions")
    op.drop_table("recurring_transactions")
