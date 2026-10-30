"""Remove the obsolete Telegram identifier from unified users.

Revision ID: 2a8cbf773ee9
Revises: 47ecb19df524
"""

import sqlalchemy as sa

from alembic import op

revision = "2a8cbf773ee9"
down_revision = "47ecb19df524"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "telegram_chat_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(50), nullable=True))
    op.create_unique_constraint("users_telegram_chat_id_key", "users", ["telegram_chat_id"])
    op.create_index("ix_users_telegram_chat_id", "users", ["telegram_chat_id"])
